import asyncio
import logging
import httpx
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

# Judge0 language IDs for common languages
LANGUAGE_IDS = {
    "python":     71,   # Python 3.8
    "javascript": 63,   # Node.js 12
    "typescript": 74,   # TypeScript 3.7
    "java":       62,   # Java 13
    "cpp":        54,   # C++ 17
    "c":          50,   # C (GCC 9.2)
    "go":         60,   # Go 1.13
    "rust":       73,   # Rust 1.40
    "csharp":     51,   # C# Mono 6.6
    "ruby":       72,   # Ruby 2.7
}


class CodeExecutionService:
    """
    Executes code via Judge0 CE (Community Edition) API.
    Uses the free public instance at judge0-ce.p.rapidapi.com
    or a self-hosted instance configured via JUDGE0_URL in settings.
    """

    def __init__(self):
        self.base_url = getattr(settings, "JUDGE0_URL", "https://judge0-ce.p.rapidapi.com")
        self.api_key = getattr(settings, "JUDGE0_API_KEY", "")
        self.headers = {
            "Content-Type": "application/json",
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "judge0-ce.p.rapidapi.com",
        }

    async def execute(
        self,
        source_code: str,
        language: str = "python",
        stdin: str = "",
        time_limit: float = 5.0,
        memory_limit: int = 128000,
    ) -> dict:
        """
        Submit code to Judge0, poll until done, return structured result.
        Returns: { status, stdout, stderr, time, memory, compile_output }
        """
        lang_id = LANGUAGE_IDS.get(language.lower(), 71)

        payload = {
            "source_code": source_code,
            "language_id": lang_id,
            "stdin": stdin,
            "cpu_time_limit": time_limit,
            "memory_limit": memory_limit,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # 1. Submit
                submit_resp = await client.post(
                    f"{self.base_url}/submissions?base64_encoded=false&wait=false",
                    json=payload,
                    headers=self.headers,
                )
                submit_resp.raise_for_status()
                token = submit_resp.json().get("token")
                if not token:
                    return self._error("Submission failed: no token returned")

                # 2. Poll until status is not queued/processing (max 15s)
                for _ in range(15):
                    await asyncio.sleep(1)
                    result_resp = await client.get(
                        f"{self.base_url}/submissions/{token}?base64_encoded=false",
                        headers=self.headers,
                    )
                    result_resp.raise_for_status()
                    data = result_resp.json()
                    status_id = data.get("status", {}).get("id", 0)
                    # 1=In Queue, 2=Processing — keep polling
                    if status_id not in (1, 2):
                        return self._format(data)

                return self._error("Execution timed out (15s polling limit)")

        except httpx.HTTPStatusError as e:
            logger.error(f"Judge0 HTTP error: {e}")
            return self._error(f"Judge0 API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Code execution error: {e}")
            return self._error(str(e))

    def _format(self, data: dict) -> dict:
        status_desc = data.get("status", {}).get("description", "Unknown")
        return {
            "status": status_desc,
            "stdout": data.get("stdout") or "",
            "stderr": data.get("stderr") or "",
            "compile_output": data.get("compile_output") or "",
            "time": data.get("time"),        # seconds as string e.g. "0.042"
            "memory": data.get("memory"),    # KB
            "passed": status_desc == "Accepted",
        }

    def _error(self, msg: str) -> dict:
        return {
            "status": "Error",
            "stdout": "",
            "stderr": msg,
            "compile_output": "",
            "time": None,
            "memory": None,
            "passed": False,
        }


code_execution_service = CodeExecutionService()
