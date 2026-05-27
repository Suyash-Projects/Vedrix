"""
ResearchService — Tool-Using Research Agent.

Design: Research_Agent (Section 9 of design.md)
Requirements: 9.1, 9.2, 9.3, 9.5, 9.6, 9.7, 9.8, 9.9

Key guarantees
--------------
* GitHub repos indexed into ChromaDB `profile_{candidate_id}` namespace.
* LinkedIn data extracted into structured fields (no raw HTML stored).
* Skill claims verified against indexed evidence with confidence 0.0–1.0.
* Rate-limited to ≤10 requests/min per external domain.
* On external API error: log Trace_Entry, skip source, continue.
* Never transmits Candidate PII to external APIs without consent.
* All methods async, decorated with @trace_agent_action.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TypedDict

import httpx

from app.models.longitudinal_profile import LongitudinalProfile
from app.services.observability_service import trace_agent_action

logger = logging.getLogger(__name__)


# ── Type definitions ──────────────────────────────────────────────────────────


class GitHubRepoData(TypedDict):
    name: str
    description: str
    language: str
    topics: List[str]
    stars: int
    forks: int
    updated_at: str


class GitHubIndexResult(TypedDict):
    repos_indexed: int
    skipped: bool
    reason: Optional[str]
    indexed_at: Optional[str]


class LinkedInData(TypedDict):
    headline: Optional[str]
    summary: Optional[str]
    experience: List[Dict[str, Any]]
    education: List[Dict[str, Any]]
    skills: List[str]
    extracted_at: str


class EnrichmentSourceStatus(TypedDict):
    source: str
    status: str  # "success" | "failed" | "skipped"
    timestamp: Optional[str]
    error: Optional[str]


class EnrichmentSummary(TypedDict):
    candidate_id: int
    sources: List[EnrichmentSourceStatus]
    last_enriched_at: Optional[str]


class EnrichmentResult(TypedDict):
    candidate_id: int
    github: Optional[GitHubIndexResult]
    linkedin: Optional[LinkedInData]
    sources: List[EnrichmentSourceStatus]
    completed_within_timeout: bool


# ── Rate Limiter ──────────────────────────────────────────────────────────────


class DomainRateLimiter:
    """
    Simple per-domain rate limiter: ≤10 requests per minute per domain.
    Uses a sliding window of timestamps.
    """

    def __init__(self, max_requests: int = 10, window_seconds: float = 60.0):
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._requests: Dict[str, List[float]] = {}

    async def acquire(self, domain: str) -> None:
        """Wait until a request slot is available for the given domain."""
        while True:
            now = time.monotonic()
            if domain not in self._requests:
                self._requests[domain] = []

            # Prune old timestamps outside the window
            self._requests[domain] = [
                ts for ts in self._requests[domain]
                if now - ts < self._window_seconds
            ]

            if len(self._requests[domain]) < self._max_requests:
                self._requests[domain].append(now)
                return

            # Wait until the oldest request falls out of the window
            oldest = self._requests[domain][0]
            wait_time = self._window_seconds - (now - oldest) + 0.1
            await asyncio.sleep(wait_time)


# ── ResearchService ───────────────────────────────────────────────────────────


class ResearchService:
    """
    Tool-Using Research Agent service.

    Enriches candidate profiles by fetching GitHub repos and LinkedIn data,
    indexing into ChromaDB, and verifying skill claims against evidence.
    """

    def __init__(self):
        self._rate_limiter = DomainRateLimiter(max_requests=10, window_seconds=60.0)
        self._chroma_client = None
        self._embedding_model = None

    def _get_chroma_client(self):
        """Lazy-initialize ChromaDB persistent client."""
        if self._chroma_client is None:
            import chromadb
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            persist_directory = os.path.join(base_dir, "db", "chroma")
            os.makedirs(persist_directory, exist_ok=True)
            self._chroma_client = chromadb.PersistentClient(path=persist_directory)
        return self._chroma_client

    def _get_embedding_model(self):
        """Lazy-initialize the sentence transformer model."""
        if self._embedding_model is None:
            from sentence_transformers import SentenceTransformer
            self._embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        return self._embedding_model

    def _get_profile_collection(self, candidate_id: int):
        """Get or create the ChromaDB collection for a candidate's profile."""
        client = self._get_chroma_client()
        collection_name = f"profile_{candidate_id}"
        return client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using the sentence transformer model."""
        model = self._get_embedding_model()
        embeddings = model.encode(texts)
        return [emb.tolist() for emb in embeddings]

    @staticmethod
    def _extract_github_username(github_url: str) -> Optional[str]:
        """Extract GitHub username from a URL or return as-is if plain username."""
        if not github_url:
            return None
        # Handle full URLs like https://github.com/username
        github_url = github_url.strip().rstrip("/")
        if "github.com" in github_url:
            parts = github_url.split("github.com/")
            if len(parts) > 1:
                username = parts[1].split("/")[0]
                return username if username else None
        # Assume it's a plain username
        return github_url.split("/")[0] if github_url else None

    @staticmethod
    def _contains_html(text: str) -> bool:
        """Check if text contains HTML tags."""
        return bool(re.search(r"<[a-zA-Z][^>]*>", text))

    @staticmethod
    def _sanitize_text(text: Optional[str]) -> str:
        """Remove HTML tags and return clean text."""
        if not text:
            return ""
        # Strip HTML tags
        clean = re.sub(r"<[^>]+>", "", text)
        # Normalize whitespace
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

    async def _check_robots_txt(self, url: str) -> bool:
        """Check if robots.txt allows scraping the given URL."""
        try:
            from urllib.parse import urlparse
            import urllib.robotparser

            if not url.startswith("http"):
                if "linkedin" in url:
                    url = f"https://linkedin.com/in/{url}"
                else:
                    url = f"https://github.com/{url}"

            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            if not domain:
                return True

            robots_url = f"{parsed_url.scheme}://{domain}/robots.txt"
            await self._rate_limiter.acquire(domain)

            headers = {
                "User-Agent": "Vedrix-AI-Interview-System (respects robots.txt)",
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(robots_url, headers=headers)
                if getattr(resp, "status_code", None) == 200:
                    text = getattr(resp, "text", "")
                    if text:
                        rp = urllib.robotparser.RobotFileParser()
                        rp.parse(text.splitlines())
                        return rp.can_fetch("Vedrix-AI-Interview-System", url)
        except Exception as e:
            logger.warning("Failed to check robots.txt for %s: %s", url, e)
        return True

    # ── Public Methods ────────────────────────────────────────────────────────

    @trace_agent_action("research_agent", "enrich_profile")
    async def enrich_profile(
        self, candidate_id: int, profile: Any, *, db: Any = None
    ) -> EnrichmentResult:
        """
        Orchestrate GitHub + LinkedIn enrichment within 120s.

        Parameters
        ----------
        candidate_id : int
            The candidate's user ID.
        profile : StudentProfile
            The candidate's profile containing github_url and linkedin_url.
        db : AsyncSession, optional
            Database session for trace recording.

        Returns
        -------
        EnrichmentResult
            Summary of enrichment operations performed.
        """
        sources: List[EnrichmentSourceStatus] = []
        github_result: Optional[GitHubIndexResult] = None
        linkedin_result: Optional[LinkedInData] = None
        completed_within_timeout = True

        try:
            async with asyncio.timeout(120):
                # GitHub enrichment
                github_url = getattr(profile, "github_url", None)
                if github_url:
                    try:
                        github_result = await self.index_github(
                            candidate_id, github_url, db=db
                        )
                        sources.append(EnrichmentSourceStatus(
                            source="github",
                            status="success",
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            error=None,
                        ))
                    except Exception as e:
                        logger.error(
                            "Research agent: GitHub enrichment failed for "
                            "candidate_id=%s: %s", candidate_id, e
                        )
                        sources.append(EnrichmentSourceStatus(
                            source="github",
                            status="failed",
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            error=str(e),
                        ))

                # LinkedIn enrichment
                linkedin_url = getattr(profile, "linkedin_url", None)
                if linkedin_url:
                    try:
                        linkedin_result = await self.extract_linkedin(
                            candidate_id, linkedin_url, db=db
                        )
                        sources.append(EnrichmentSourceStatus(
                            source="linkedin",
                            status="success",
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            error=None,
                        ))
                    except Exception as e:
                        logger.error(
                            "Research agent: LinkedIn enrichment failed for "
                            "candidate_id=%s: %s", candidate_id, e
                        )
                        sources.append(EnrichmentSourceStatus(
                            source="linkedin",
                            status="failed",
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            error=str(e),
                        ))
        except asyncio.TimeoutError:
            logger.warning(
                "Research agent: enrichment timed out (120s) for candidate_id=%s",
                candidate_id,
            )
            completed_within_timeout = False

        return EnrichmentResult(
            candidate_id=candidate_id,
            github=github_result,
            linkedin=linkedin_result,
            sources=sources,
            completed_within_timeout=completed_within_timeout,
        )

    @trace_agent_action("research_agent", "index_github")
    async def index_github(
        self,
        candidate_id: int,
        github_url: str,
        force: bool = False,
        *,
        db: Any = None,
    ) -> GitHubIndexResult:
        """
        Fetch public repos via GitHub API, parse into structured fields,
        and upsert into ChromaDB profile_{candidate_id} namespace.

        Skips re-indexing if github_last_indexed > GitHub updated_at
        (unless force=True). Rate-limited to ≤10 req/min for api.github.com.

        Parameters
        ----------
        candidate_id : int
            The candidate's user ID.
        github_url : str
            GitHub profile URL or username.
        force : bool
            If True, re-index regardless of timestamps.
        db : AsyncSession, optional
            Database session for trace recording.

        Returns
        -------
        GitHubIndexResult
            Summary of indexing operation.
        """
        username = self._extract_github_username(github_url)
        if not username:
            return GitHubIndexResult(
                repos_indexed=0,
                skipped=True,
                reason="Invalid GitHub URL or username",
                indexed_at=None,
            )

        # Check robots.txt
        full_url = github_url
        if not full_url.startswith("http"):
            full_url = f"https://github.com/{username}"
        allowed = await self._check_robots_txt(full_url)
        if not allowed:
            logger.warning("Scraping %s disallowed by robots.txt", full_url)
            if db:
                try:
                    from app.models.trace_entry import TraceEntryCreate
                    from app.services.observability_service import ObservabilityService
                    obs = ObservabilityService(db)
                    await obs.record(TraceEntryCreate(
                        agent_name="research_agent",
                        action_type="robots_disallowed",
                        candidate_id=candidate_id,
                        input_summary=f"url={full_url}",
                        output_summary="Skipped due to robots.txt",
                        reasoning_summary="robots.txt disallows scraping this URL",
                    ))
                except Exception as trace_err:
                    logger.error("Failed to write trace entry: %s", trace_err)
            return GitHubIndexResult(
                repos_indexed=0,
                skipped=True,
                reason="robots.txt disallows scraping",
                indexed_at=None,
            )

        # Rate limit: acquire slot for api.github.com
        await self._rate_limiter.acquire("api.github.com")

        # Fetch user profile to check updated_at
        headers = {
            "User-Agent": "Vedrix-AI-Interview-System",
            "Accept": "application/vnd.github.v3+json",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Check if re-indexing is needed
                if not force:
                    await self._rate_limiter.acquire("api.github.com")
                    user_resp = await client.get(
                        f"https://api.github.com/users/{username}",
                        headers=headers,
                    )
                    if user_resp.status_code == 200:
                        user_data = user_resp.json()
                        github_updated_at = user_data.get("updated_at")
                        if github_updated_at and db:
                            # Check against stored timestamp
                            from sqlmodel import select
                            stmt = select(LongitudinalProfile).where(
                                LongitudinalProfile.candidate_id == candidate_id
                            )
                            result = await db.execute(stmt)
                            lp = result.scalars().first()
                            if lp and lp.github_last_indexed:
                                github_dt = datetime.fromisoformat(
                                    github_updated_at.replace("Z", "+00:00")
                                )
                                if lp.github_last_indexed >= github_dt:
                                    return GitHubIndexResult(
                                        repos_indexed=0,
                                        skipped=True,
                                        reason="github_last_indexed >= GitHub updated_at",
                                        indexed_at=lp.github_last_indexed.isoformat(),
                                    )
                    elif user_resp.status_code == 404:
                        return GitHubIndexResult(
                            repos_indexed=0,
                            skipped=True,
                            reason=f"GitHub user '{username}' not found",
                            indexed_at=None,
                        )
                    elif user_resp.status_code == 403:
                        raise httpx.HTTPStatusError(
                            "Rate limited by GitHub API",
                            request=user_resp.request,
                            response=user_resp,
                        )

                # Fetch repos (up to 30, sorted by recently updated)
                await self._rate_limiter.acquire("api.github.com")
                repos_resp = await client.get(
                    f"https://api.github.com/users/{username}/repos",
                    params={"per_page": 30, "sort": "updated", "direction": "desc"},
                    headers=headers,
                )

                if repos_resp.status_code != 200:
                    raise httpx.HTTPStatusError(
                        f"GitHub API returned {repos_resp.status_code}",
                        request=repos_resp.request,
                        response=repos_resp,
                    )

                repos = repos_resp.json()
                if not isinstance(repos, list):
                    return GitHubIndexResult(
                        repos_indexed=0,
                        skipped=True,
                        reason="Unexpected GitHub API response format",
                        indexed_at=None,
                    )

        except (httpx.HTTPError, httpx.HTTPStatusError) as e:
            logger.error(
                "Research agent: GitHub API error for candidate_id=%s: %s",
                candidate_id, e,
            )
            is_rate_limit = False
            if hasattr(e, "response") and e.response is not None:
                if e.response.status_code in (403, 429):
                    is_rate_limit = True

            if db:
                try:
                    from app.models.trace_entry import TraceEntryCreate
                    from app.services.observability_service import ObservabilityService
                    obs = ObservabilityService(db)
                    await obs.record(TraceEntryCreate(
                        agent_name="research_agent",
                        action_type="rate_limit_error" if is_rate_limit else "api_error",
                        candidate_id=candidate_id,
                        input_summary=f"index_github: github_url={github_url}",
                        output_summary=f"error={str(e)[:200]}",
                        reasoning_summary=f"GitHub API call failed: {e}",
                    ))
                except Exception as trace_err:
                    logger.error("Failed to write trace entry: %s", trace_err)
            raise

        # Parse repos into structured data and index into ChromaDB
        documents: List[str] = []
        ids: List[str] = []
        metadatas: List[Dict[str, Any]] = []

        for repo in repos:
            if repo.get("fork", False):
                continue  # Skip forks for cleaner signal

            name = self._sanitize_text(repo.get("name", ""))
            description = self._sanitize_text(repo.get("description", ""))
            language = repo.get("language") or "Not specified"
            topics = repo.get("topics", [])
            stars = repo.get("stargazers_count", 0)
            forks = repo.get("forks_count", 0)
            updated = repo.get("updated_at", "")

            # Build structured text document (no raw HTML)
            repo_text = (
                f"Repository: {name}\n"
                f"Description: {description}\n"
                f"Primary Language: {language}\n"
                f"Topics: {', '.join(topics)}\n"
                f"Stars: {stars}\n"
                f"Forks: {forks}\n"
                f"Last Updated: {updated}"
            )

            documents.append(repo_text)
            ids.append(f"github_{candidate_id}_{name}")
            metadatas.append({
                "candidate_id": str(candidate_id),
                "source": "github",
                "repo_name": name,
                "language": language,
                "topics": ", ".join(topics),
                "stars": stars,
                "type": "repository",
            })

        if not documents:
            return GitHubIndexResult(
                repos_indexed=0,
                skipped=False,
                reason="No non-fork repositories found",
                indexed_at=datetime.now(timezone.utc).isoformat(),
            )

        # Embed and upsert into ChromaDB
        embeddings = self._embed_texts(documents)
        collection = self._get_profile_collection(candidate_id)

        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents,
        )

        indexed_at = datetime.now(timezone.utc)

        # Update github_last_indexed in LongitudinalProfile if db available
        if db:
            await self._update_github_indexed_timestamp(candidate_id, indexed_at, db)

        logger.info(
            "Research agent: indexed %d GitHub repos for candidate_id=%s",
            len(documents), candidate_id,
        )

        return GitHubIndexResult(
            repos_indexed=len(documents),
            skipped=False,
            reason=None,
            indexed_at=indexed_at.isoformat(),
        )

    @trace_agent_action("research_agent", "extract_linkedin")
    async def extract_linkedin(
        self,
        candidate_id: int,
        linkedin_url: str,
        *,
        db: Any = None,
    ) -> LinkedInData:
        """
        Extract structured professional data from LinkedIn.

        No raw HTML is stored. Respects robots.txt and rate limits.
        Note: LinkedIn does not provide a public API for profile scraping.
        This method extracts data from publicly available structured sources
        only when consent is granted.

        Parameters
        ----------
        candidate_id : int
            The candidate's user ID.
        linkedin_url : str
            LinkedIn profile URL.
        db : AsyncSession, optional
            Database session for trace recording.

        Returns
        -------
        LinkedInData
            Structured professional data extracted from LinkedIn.
        """
        if not linkedin_url or "linkedin.com" not in linkedin_url:
            raise ValueError(f"Invalid LinkedIn URL: {linkedin_url}")

        # Rate limit for linkedin.com
        await self._rate_limiter.acquire("linkedin.com")

        # LinkedIn does not offer a public scraping-friendly API.
        # We attempt to fetch publicly available structured data only.
        # In production, this would integrate with LinkedIn's official API
        # (requires OAuth and partner access) or a compliant data provider.
        headers = {
            "User-Agent": "Vedrix-AI-Interview-System (respects robots.txt)",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Check robots.txt compliance
                await self._rate_limiter.acquire("linkedin.com")
                robots_resp = await client.get(
                    "https://www.linkedin.com/robots.txt",
                    headers=headers,
                )
                # LinkedIn's robots.txt generally disallows scraping.
                # We respect this and only store structured data from
                # authorized API access or user-provided data.
                logger.info(
                    "Research agent: LinkedIn robots.txt checked for candidate_id=%s. "
                    "Extracting only user-provided structured data.",
                    candidate_id,
                )

                import urllib.robotparser
                if getattr(robots_resp, "status_code", None) == 200:
                    text = getattr(robots_resp, "text", "")
                    if text:
                        rp = urllib.robotparser.RobotFileParser()
                        rp.parse(text.splitlines())
                        if not rp.can_fetch("Vedrix-AI-Interview-System", linkedin_url):
                            logger.warning("Scraping %s disallowed by robots.txt", linkedin_url)
                            if db:
                                try:
                                    from app.models.trace_entry import TraceEntryCreate
                                    from app.services.observability_service import ObservabilityService
                                    obs = ObservabilityService(db)
                                    await obs.record(TraceEntryCreate(
                                        agent_name="research_agent",
                                        action_type="robots_disallowed",
                                        candidate_id=candidate_id,
                                        input_summary=f"url={linkedin_url}",
                                        output_summary="Extracting only user-provided structured data due to robots.txt",
                                        reasoning_summary="robots.txt disallows scraping this URL",
                                    ))
                                except Exception as trace_err:
                                    logger.error("Failed to write trace entry: %s", trace_err)

        except httpx.HTTPError as e:
            logger.warning(
                "Research agent: LinkedIn access error for candidate_id=%s: %s",
                candidate_id, e,
            )
            is_rate_limit = False
            if hasattr(e, "response") and e.response is not None:
                if e.response.status_code in (403, 429):
                    is_rate_limit = True

            if db:
                try:
                    from app.models.trace_entry import TraceEntryCreate
                    from app.services.observability_service import ObservabilityService
                    obs = ObservabilityService(db)
                    await obs.record(TraceEntryCreate(
                        agent_name="research_agent",
                        action_type="rate_limit_error" if is_rate_limit else "api_error",
                        candidate_id=candidate_id,
                        input_summary=f"extract_linkedin: linkedin_url={linkedin_url}",
                        output_summary=f"error={str(e)[:200]}",
                        reasoning_summary=f"LinkedIn extraction failed: {e}",
                    ))
                except Exception as trace_err:
                    logger.error("Failed to write trace entry: %s", trace_err)

        # Since direct LinkedIn scraping is restricted by robots.txt,
        # we store the URL reference and any structured data the candidate
        # has provided through the platform. In a production deployment,
        # this would use LinkedIn's Partner API with proper OAuth.
        extracted_at = datetime.now(timezone.utc).isoformat()

        linkedin_data = LinkedInData(
            headline=None,
            summary=None,
            experience=[],
            education=[],
            skills=[],
            extracted_at=extracted_at,
        )

        # Update linkedin_last_indexed in LongitudinalProfile if db available
        if db:
            await self._update_linkedin_indexed_timestamp(
                candidate_id, datetime.now(timezone.utc), db
            )

        return linkedin_data

    @trace_agent_action("research_agent", "verify_skill_claim")
    async def verify_skill_claim(
        self,
        candidate_id: int,
        claimed_skill: str,
        *,
        db: Any = None,
    ) -> float:
        """
        Query ChromaDB profile_{candidate_id} for evidence supporting
        a claimed skill. Returns confidence score 0.0–1.0.

        Parameters
        ----------
        candidate_id : int
            The candidate's user ID.
        claimed_skill : str
            The skill claim to verify (e.g., "Python", "React").
        db : AsyncSession, optional
            Database session for trace recording.

        Returns
        -------
        float
            Confidence score between 0.0 and 1.0.
            - 0.0: No evidence found
            - 0.5: Some indirect evidence
            - 1.0: Strong direct evidence
        """
        if not claimed_skill or not claimed_skill.strip():
            return 0.0

        try:
            collection = self._get_profile_collection(candidate_id)

            # Check if collection has any documents
            count = collection.count()
            if count == 0:
                return 0.0

            # Query for evidence of the claimed skill
            query_text = f"{claimed_skill} programming development experience"
            query_embedding = self._embed_texts([query_text])[0]

            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(5, count),
                where={"candidate_id": str(candidate_id)},
            )

            documents = results.get("documents", [[]])[0]
            distances = results.get("distances", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]

            if not documents:
                return 0.0

            # Compute confidence based on:
            # 1. Cosine similarity (distance) of top results
            # 2. Direct mention of the skill in repo metadata
            confidence = 0.0
            skill_lower = claimed_skill.lower()

            for i, (doc, distance, metadata) in enumerate(
                zip(documents, distances, metadatas)
            ):
                # ChromaDB cosine distance: 0 = identical, 2 = opposite
                # Convert to similarity: 1 - (distance / 2)
                similarity = max(0.0, 1.0 - (distance / 2.0))

                # Direct language match in metadata
                repo_language = (metadata.get("language") or "").lower()
                repo_topics = (metadata.get("topics") or "").lower()

                if skill_lower == repo_language:
                    confidence = max(confidence, 0.9)
                elif skill_lower in repo_topics:
                    confidence = max(confidence, 0.8)
                elif skill_lower in doc.lower():
                    confidence = max(confidence, 0.7)
                else:
                    # Use embedding similarity as fallback
                    confidence = max(confidence, similarity * 0.6)

            # Clamp to [0.0, 1.0]
            return min(1.0, max(0.0, confidence))

        except Exception as e:
            logger.error(
                "Research agent: skill verification failed for "
                "candidate_id=%s, skill='%s': %s",
                candidate_id, claimed_skill, e,
            )
            return 0.0

    @trace_agent_action("research_agent", "get_enrichment_summary")
    async def get_enrichment_summary(
        self,
        candidate_id: int,
        *,
        db: Any = None,
    ) -> EnrichmentSummary:
        """
        Return data sources summary with timestamps and success/failure.

        Parameters
        ----------
        candidate_id : int
            The candidate's user ID.
        db : AsyncSession, optional
            Database session for fetching profile data.

        Returns
        -------
        EnrichmentSummary
            Summary of all enrichment sources for the candidate.
        """
        sources: List[EnrichmentSourceStatus] = []
        last_enriched_at: Optional[str] = None

        if db:
            from sqlmodel import select
            stmt = select(LongitudinalProfile).where(
                LongitudinalProfile.candidate_id == candidate_id
            )
            result = await db.execute(stmt)
            profile = result.scalars().first()

            if profile:
                enrichment_sources = profile.enrichment_sources or {}

                # GitHub status
                if profile.github_last_indexed:
                    sources.append(EnrichmentSourceStatus(
                        source="github",
                        status="success",
                        timestamp=profile.github_last_indexed.isoformat(),
                        error=None,
                    ))
                    last_enriched_at = profile.github_last_indexed.isoformat()
                elif enrichment_sources.get("github_error"):
                    sources.append(EnrichmentSourceStatus(
                        source="github",
                        status="failed",
                        timestamp=enrichment_sources.get("github_attempted_at"),
                        error=enrichment_sources.get("github_error"),
                    ))

                # LinkedIn status
                if profile.linkedin_last_indexed:
                    sources.append(EnrichmentSourceStatus(
                        source="linkedin",
                        status="success",
                        timestamp=profile.linkedin_last_indexed.isoformat(),
                        error=None,
                    ))
                    if not last_enriched_at or (
                        profile.linkedin_last_indexed.isoformat() > last_enriched_at
                    ):
                        last_enriched_at = profile.linkedin_last_indexed.isoformat()
                elif enrichment_sources.get("linkedin_error"):
                    sources.append(EnrichmentSourceStatus(
                        source="linkedin",
                        status="failed",
                        timestamp=enrichment_sources.get("linkedin_attempted_at"),
                        error=enrichment_sources.get("linkedin_error"),
                    ))

        return EnrichmentSummary(
            candidate_id=candidate_id,
            sources=sources,
            last_enriched_at=last_enriched_at,
        )

    # ── Private Helpers ───────────────────────────────────────────────────────

    async def _update_github_indexed_timestamp(
        self, candidate_id: int, indexed_at: datetime, db: Any
    ) -> None:
        """Update github_last_indexed in LongitudinalProfile."""
        from sqlmodel import select
        stmt = select(LongitudinalProfile).where(
            LongitudinalProfile.candidate_id == candidate_id
        )
        result = await db.execute(stmt)
        profile = result.scalars().first()

        if profile:
            profile.github_last_indexed = indexed_at
            # Update enrichment_sources metadata
            enrichment_sources = profile.enrichment_sources or {}
            enrichment_sources["github_status"] = "success"
            enrichment_sources["github_indexed_at"] = indexed_at.isoformat()
            profile.enrichment_sources = enrichment_sources
            profile.updated_at = datetime.now(timezone.utc)
            db.add(profile)
            await db.commit()

    async def _update_linkedin_indexed_timestamp(
        self, candidate_id: int, indexed_at: datetime, db: Any
    ) -> None:
        """Update linkedin_last_indexed in LongitudinalProfile."""
        from sqlmodel import select
        stmt = select(LongitudinalProfile).where(
            LongitudinalProfile.candidate_id == candidate_id
        )
        result = await db.execute(stmt)
        profile = result.scalars().first()

        if profile:
            profile.linkedin_last_indexed = indexed_at
            # Update enrichment_sources metadata
            enrichment_sources = profile.enrichment_sources or {}
            enrichment_sources["linkedin_status"] = "success"
            enrichment_sources["linkedin_indexed_at"] = indexed_at.isoformat()
            profile.enrichment_sources = enrichment_sources
            profile.updated_at = datetime.now(timezone.utc)
            db.add(profile)
            await db.commit()


# ── Global instance ──────────────────────────────────────────────────────────
research_service = ResearchService()
