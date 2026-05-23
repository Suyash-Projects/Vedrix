# Technical Documentation Workflow

**Purpose:** Provide a repeatable process for creating, updating, and maintaining technical documentation across the Vedrix project.

---

## Overview

This workflow defines how to create and maintain five types of technical documentation, following the principles of writing for the reader, showing not telling, and keeping content current.

```
                    ┌─────────────────────┐
                    │  Identify Need       │
                    │  (New feature, bug,  │
                    │   onboarding, etc.)  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Select Document     │
                    │  Type                │
                    └──────────┬──────────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
                    ▼                     ▼
         ┌─────────────────┐   ┌─────────────────┐
         │ New Document    │   │ Update Existing │
         └────────┬────────┘   └────────┬────────┘
                  │                     │
                  ▼                     ▼
         ┌─────────────────┐   ┌─────────────────┐
         │ Research &      │   │ Audit Current   │
         │ Gather Info     │   │ Content         │
         └────────┬────────┘   └────────┬────────┘
                  │                     │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │  Draft & Format     │
                  │  (Follow template)  │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │  Review & Validate  │
                  │  (Accuracy, clarity,│
                  │   completeness)     │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │  Publish & Link     │
                  │  (Commit to repo,   │
                  │   update index)     │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │  Maintain           │
                  │  (Review quarterly, │
                  │   update on changes)│
                  └─────────────────────┘
```

---

## Document Types

### 1. README

**Purpose:** First impression. Helps users understand what the project is and get started quickly.

**When to create/update:**
- New project or significant feature
- Major version changes
- Setup instructions change

**Template:**

```markdown
# Project Name

[One-paragraph description of what this is and why it exists.]

## Quick Start
```bash
[command that works in < 5 minutes]
```
```

**Sections required:**
- What this is and why it exists
- Quick start (< 5 minutes to first success)
- Configuration and usage
- Contributing guide
- Badges (CI, coverage, version)

**Checklist:**
- [ ] Does the first paragraph describe what this is and why it exists?
- [ ] Can a new user go from zero to running in under 5 minutes?
- [ ] Are all commands copy-paste ready (including setup)?
- [ ] Are configuration steps documented?
- [ ] Is there a link to contributing guidelines?

---

### 2. API Documentation

**Purpose:** Enable developers to integrate with the API without reading source code.

**When to create/update:**
- New endpoint added
- Existing endpoint behavior changes
- Request/response schema changes

**Template structure:**
- Authentication section (how to auth, token format, expiry)
- Common patterns (pagination, errors, headers)
- Endpoint reference (grouped by resource)
- Error codes table
- Rate limits table
- SDK examples (curl, Python, JavaScript)

**Per-endpoint checklist:**
- [ ] HTTP method and path
- [ ] Authentication requirements
- [ ] Request body schema (with types and constraints)
- [ ] Response body schema (200 and error responses)
- [ ] Query parameters (with defaults and limits)
- [ ] Status codes and their meanings
- [ ] Rate limits specific to this endpoint

**Key principle:** "Show, don't tell" — include a complete request/response example for every endpoint.

---

### 3. Runbook

**Purpose:** Enable on-call engineers to diagnose and resolve issues under time pressure.

**When to create/update:**
- New operational procedure identified
- After an incident that revealed a gap
- Infrastructure changes

**Template structure:**
- When to use this runbook (clear triggering conditions)
- Prerequisites and access needed
- Step-by-step numbered procedure
- Expected state at each step
- Rollback steps
- Escalation path

**Per-procedure checklist:**
- [ ] Clear triggering conditions at the top ("When to Use")
- [ ] All steps are numbered and actionable
- [ ] Each step includes expected output
- [ ] Commands are copy-paste ready
- [ ] Rollback steps are documented
- [ ] Escalation contact and expected response time
- [ ] Severity classification

**Key principle:** "Start with the most useful information" — the most critical runbooks should be first.

---

### 4. Architecture Documentation

**Purpose:** Help engineers understand system design, make informed decisions, and onboard to complex components.

**When to create/update:**
- New system components added
- Architecture decisions changed
- Major refactoring completed

**Template structure:**
- Context and goals
- High-level design (with ASCII or Mermaid diagram)
- Key decisions and trade-offs (with alternatives considered)
- Data flow diagrams
- Integration points
- Security architecture
- Deployment topology

**Per-section checklist:**
- [ ] Context explains why this architecture was chosen
- [ ] Diagram shows all major components and their connections
- [ ] Key decisions document what was decided, why, and what was rejected
- [ ] Data flow shows request lifecycle end-to-end
- [ ] Integration points document external dependencies
- [ ] Security architecture shows defense layers

**Key principle:** "Link, don't duplicate" — reference detailed docs (API ref, runbook) instead of copying them.

---

### 5. Onboarding Guide

**Purpose:** Get new developers productive within their first week.

**When to create/update:**
- New team member joins
- Development environment changes
- Tools or processes change

**Template structure:**
- Week 1 checklist
- Prerequisites (software, access)
- Environment setup (step-by-step)
- Key systems and how they connect
- Common developer tasks with walkthroughs
- Who to ask for what (responsibility matrix)

**Checklist:**
- [ ] Can a new developer set up their environment in < 2 hours?
- [ ] Are all required access permissions documented?
- [ ] Are there 3-5 common task walkthroughs?
- [ ] Is there a "who to ask for what" table?
- [ ] Are there links to all other key documentation?
- [ ] Does it include a first-week plan?

**Key principle:** "Write for the reader" — this is for new developers who are anxious to contribute quickly.

---

## Maintenance Cadence

| Document | Review Frequency | Trigger for Unscheduled Update |
|----------|-----------------|-------------------------------|
| README | Quarterly | New feature, setup change |
| API Reference | Per release | New/modified endpoint |
| Runbook | Quarterly | Post-incident, infrastructure change |
| Architecture | Bi-annual | System redesign, new component |
| Onboarding | Quarterly | Tool/process change, feedback from new hires |

### Review Process

1. **Schedule quarterly review** — Set calendar reminder for each document
2. **Audit for accuracy** — Verify commands, screenshots, examples, links
3. **Update for changes** — Reflect any changes since last review
4. **Gather feedback** — Ask team members if anything is unclear
5. **Publish updates** — Commit changes and notify the team

---

## Quality Standards

### Writing Guidelines

| Principle | What It Means |
|-----------|---------------|
| Write for the reader | Know your audience (developer, on-call engineer, new hire) |
| Start with the useful info | Put the most important information first |
| Show, don't tell | Use examples, screenshots, and code snippets |
| Keep it current | Schedule regular reviews; update immediately when things change |
| Link, don't duplicate | One source of truth; reference other docs |

### Style Guide

- **Titles:** Sentence case ("Getting started" not "Getting Started")
- **Code:** Use fenced code blocks with language specifiers
- **Bold:** For UI elements, labels, and key terms
- **Italic:** For emphasis
- **Lists:** Use numbered lists for sequential steps, bullet lists for options
- **Tables:** For comparisons, parameter lists, and status codes
- **Links:** Use relative paths within the project, absolute URLs for external resources

### Validation Checklist

Before publishing any documentation:

- [ ] All links work (internal and external)
- [ ] All code examples are correct and tested
- [ ] All commands are copy-paste ready
- [ ] No placeholder text (e.g., `TODO`, `FIXME`)
- [ ] Consistent formatting throughout
- [ ] Suitable for the target audience
- [ ] No sensitive information (API keys, passwords, internal URLs)
- [ ] Reviewed by at least one other person

---

## Automation

### Git Hooks (Recommended)

```bash
# pre-commit hook to check for stale docs
# .git/hooks/pre-commit
#!/bin/sh
echo "Checking for documentation that needs updating..."
# Add custom checks here
```

### CI Checks (Optional)

Consider adding to CI pipeline:
- Link checker (verify all internal and external links)
- Spell checker (catch typos in documentation)
- Format linter (ensure consistent markdown formatting)
- Stale doc warnings (flag documents not updated in 90+ days)

### Tools

| Tool | Purpose | When to Use |
|------|---------|-------------|
| Mermaid | Architecture diagrams | Creating or updating architecture docs |
| markdownlint | Formatting consistency | Before committing docs |
| prettier | Markdown formatting | Before committing docs |
| link-checker | Link validation | In CI pipeline |
| spell-check | Typos and misspellings | Before PR submission |

---

## Document Index

All project documentation should be indexed in the main README and kept up to date.

### Current Documentation Map

```
Vedrix/
├── README.md                              # Project overview
├── CONTRIBUTING.md                        # Contribution guidelines
├── WORKFLOW.md                            # Documentation workflow (this file)
├── Vedrix/
│   ├── DEPLOYMENT.md                      # Deployment guide
│   ├── backend/
│   │   ├── API_REFERENCE.md              # API reference (original)
│   │   └── app/services/
│   │       └── interview_engine/
│   │           └── ARCHITECTURE.md        # Interview engine internals
│   └── docs/
│       ├── getting-started.md             # Quick start guide
│       ├── architecture.md                # System architecture
│       ├── api-reference.md               # Comprehensive API docs
│       ├── onboarding.md                  # Developer onboarding
│       └── runbook.md                     # Operations runbook
```

---

## Quick Reference

### "I need to..."

| Situation | Action |
|-----------|--------|
| Document a new feature | Create/update API ref → Update README → Update architecture |
| Fix a bug | Update runbook if needed → Document in changelog |
| Onboard a new developer | Review onboarding guide → Update for any changes |
| Respond to an incident | Update runbook with new procedure → Post-mortem |
| Release a new version | Review all docs → Update version numbers → Update API ref |
| Deprecate a feature | Update API ref (deprecation notice) → Update architecture |
| Change a process | Update onboarding → Update runbook → Notify team |

### Document Ownership

| Document | Primary Owner | Reviewers |
|----------|--------------|-----------|
| README | Engineering lead | Team |
| API Reference | Backend team | Frontend team |
| Runbook | DevOps/Platform team | On-call engineers |
| Architecture | System architect | Engineering lead |
| Onboarding | Team lead | Newest team member |

---

*Last updated: May 2026*

*This document should be reviewed quarterly alongside all other documentation.*
