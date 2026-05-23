# Contributing to Vedrix AI Interview System

**Thank you for considering contributing to Vedrix!** We welcome contributions of all kinds: bug fixes, new features, documentation improvements, and more.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)
- [Feature Requests](#feature-requests)
- [Documentation](#documentation)

---

## Code of Conduct

By participating in this project, you agree to maintain a welcoming, inclusive, and harassment-free environment for everyone. 

**Our standards:**
- Use welcoming and inclusive language
- Be respectful of differing viewpoints and experiences
- Gracefully accept constructive criticism
- Focus on what is best for the community
- Show empathy towards other community members

---

## How to Contribute

### For First-Time Contributors

1. **Find a good first issue** — Look for issues tagged `good-first-issue` or `help-wanted`
2. **Comment on the issue** — Let us know you're working on it
3. **Fork the repository** — Create your own copy
4. **Make your changes** — Follow our coding standards
5. **Submit a pull request** — See [Pull Request Process](#pull-request-process)

### Types of Contributions

| Type | Description | Tag |
|------|-------------|-----|
| Bug fix | Fixes an existing bug | `bug` |
| Feature | New functionality | `enhancement` |
| Refactoring | Code quality improvement | `refactor` |
| Documentation | Docs, comments, README | `documentation` |
| Tests | Adding or improving tests | `tests` |
| Performance | Speed or memory optimization | `performance` |

---

## Development Setup

See the [Getting Started Guide](./Vedrix/docs/getting-started.md) for detailed setup instructions.

Quick start:

```bash
# Clone and start development
git clone <repository-url>
cd Vedrix
python run_dev.py
```

This starts both the backend and frontend with hot reload enabled.

---

## Coding Standards

### Backend (Python)

- **Python 3.12+** — Use modern features (type hints, async/await, pattern matching)
- **Async-first** — All I/O operations must be async (database, HTTP calls, AI APIs)
- **Type hints** — Required for all function signatures
- **Docstrings** — Google-style docstrings for all public functions and classes

```python
# Good example
async def get_user_interviews(
    user_id: UUID,
    db: AsyncSession,
    skip: int = 0,
    limit: int = 50
) -> list[InterviewSession]:
    """Get paginated interview sessions for a user.

    Args:
        user_id: The UUID of the user.
        db: Database session.
        skip: Number of records to skip (default: 0).
        limit: Maximum records to return (default: 50, max: 100).

    Returns:
        A list of InterviewSession objects.

    Raises:
        ValueError: If limit exceeds 100.
    """
    if limit > 100:
        raise ValueError("Limit cannot exceed 100")
    # ... implementation
```

**Naming conventions:**
- `snake_case` for functions, variables, and file names
- `PascalCase` for classes
- `UPPER_CASE` for constants
- Prefix private functions/methods with `_`

### Frontend (JavaScript/React)

- **JavaScript (JSX)** — All source files use `.jsx` extension
- **Functional components** — Use React hooks, avoid class components
- **One component per file** — Named exports preferred

```jsx
// Good example
import { useState } from 'react';
import { apiClient } from '../services/api';

export function InterviewList({ userId }) {
  const [interviews, setInterviews] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchInterviews = async () => {
      try {
        const response = await apiClient.get(`/student/interviews`);
        setInterviews(response.data);
      } finally {
        setLoading(false);
      }
    };
    fetchInterviews();
  }, [userId]);

  if (loading) return <div>Loading...</div>;
  return (
    <div className="space-y-4">
      {interviews.map(interview => (
        <InterviewCard key={interview.id} interview={interview} />
      ))}
    </div>
  );
}
```

**Styling:** Use Tailwind CSS utility classes. Prefer inline utility classes over `@apply` directives.

### Git Commit Messages

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: A new feature
- `fix`: A bug fix
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `docs`: Documentation only changes
- `test`: Adding or fixing tests
- `chore`: Build process or tooling changes
- `perf`: Performance improvements
- `style`: Code style changes (formatting, missing semicolons)

**Examples:**
```
feat(interview): add video recording support
fix(auth): handle token refresh race condition
docs(api): update rate limit documentation
refactor(engine): simplify question generation logic
test(hr): add tests for bulk invite endpoint
```

---

## Testing

### Backend Tests

```bash
cd Vedrix/backend

# Run all tests
python -m pytest

# With coverage
python -m pytest --cov=app --cov-report=term-missing

# Specific test file
python -m pytest tests/test_auth.py

# By keyword
python -m pytest -k "interview"

# Parallel execution
python -m pytest -n auto
```

**Test writing guidelines:**
- Use `pytest` with `pytest-asyncio` for async tests
- Use `httpx.AsyncClient` for API endpoint testing
- Use SQLite in-memory database for test isolation
- Mock external services (AI providers, Redis, email)

```python
# Good test example
@pytest.mark.asyncio
async def test_login_success(async_client, test_db):
    """Test successful login returns cookies and token."""
    response = await async_client.post(
        "/api/v1/auth/login",
        data={"username": "testuser", "password": "TestP@ss1"}
    )
    assert response.status_code == 200
    assert "access_token" in response.cookies
    assert "csrf_token" in response.cookies
```

### Frontend Tests

```bash
cd Vedrix/frontend

# Run all tests
npm test

# Watch mode
npm test -- --watch

# Specific component
npm test -- --grep "InterviewRoom"
```

### Pre-submission Checklist

- [ ] All existing tests pass
- [ ] New tests cover your changes
- [ ] No linting errors (`npm run lint` for frontend)
- [ ] Code builds successfully
- [ ] Manual testing performed

---

## Pull Request Process

### Step-by-Step

1. **Create a branch**
   ```bash
   git checkout -b feat/your-feature-name
   # or fix/your-bug-fix, docs/your-docs-update, etc.
   ```

2. **Make your changes**
   - Write clean, well-documented code
   - Add tests for new functionality
   - Update documentation if needed

3. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat(scope): clear description of changes"
   ```

4. **Keep your branch up to date**
   ```bash
   git fetch origin
   git rebase origin/main
   ```

5. **Push and create a PR**
   ```bash
   git push origin feat/your-feature-name
   ```
   Then open a pull request on GitHub.

### PR Requirements

- **Title:** Clear, descriptive, follows commit message format
- **Description:** Include what changed, why, and how to test
- **Related issues:** Link any related issues (e.g., "Closes #123")
- **Screenshots:** For UI changes, include before/after screenshots
- **Tests:** New functionality must include tests
- **Documentation:** Update relevant docs

### PR Review Process

1. **Automated checks** — CI must pass (lint, test, build)
2. **Code review** — At least one maintainer reviews
3. **Address feedback** — Make requested changes
4. **Approval** — PR is approved
5. **Merge** — Squash-merge into main

### What We Look For in Reviews

- **Correctness:** Does the code do what it claims?
- **Security:** Are there any vulnerabilities?
- **Performance:** Will this scale?
- **Maintainability:** Is the code readable and well-structured?
- **Testing:** Is there adequate test coverage?
- **Consistency:** Does it follow project conventions?

---

## Issue Reporting

### Bug Reports

When reporting a bug, please include:

1. **Title** — Clear, descriptive summary
2. **Environment** — Browser/version, OS, deployment (local/prod)
3. **Steps to reproduce** — Minimal, complete, verifiable steps
4. **Expected behavior** — What should happen
5. **Actual behavior** — What actually happens
6. **Screenshots/logs** — If applicable
7. **Additional context** — Anything else relevant

**Bug report template:**

```
**Title:** [Short description]

**Environment:**
- Browser: Chrome 124
- OS: Windows 11
- Deployment: Local development

**Steps to reproduce:**
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

**Expected behavior:**
A clear and concise description of what you expected to happen.

**Actual behavior:**
A clear and concise description of what actually happened.

**Screenshots:**
If applicable, add screenshots to help explain your problem.

**Additional context:**
Add any other context about the problem here.
```

### Feature Requests

When requesting a feature, please include:

1. **Problem statement** — What problem does this solve?
2. **Proposed solution** — How would you like it to work?
3. **Alternatives considered** — What else have you considered?
4. **Use case** — How would you use this feature?

---

## Feature Requests

We use GitHub Issues for feature requests. Please use the `enhancement` label.

Feature requests are evaluated based on:
- **Alignment** with project goals
- **Impact** on user experience
- **Maintenance** cost
- **Complexity** of implementation

---

## Documentation

Good documentation is as important as good code.

### When to Update Docs

- Adding a new feature
- Changing existing behavior
- Fixing a bug that was documented differently
- Finding something unclear or incorrect

### Documentation Guidelines

See our [Technical Documentation Workflow](./WORKFLOW.md) for a structured approach to creating and maintaining documentation.

Key principles:
1. **Write for the reader** — Who is reading this and what do they need?
2. **Start with the most useful information** — Don't bury the lede
3. **Show, don't tell** — Code examples, commands, screenshots
4. **Keep it current** — Outdated docs are worse than no docs
5. **Link, don't duplicate** — Reference other docs instead of copying

### Documentation Index

| Document | Location | Audience |
|----------|----------|----------|
| README | `README.md` | All users |
| Getting Started | `Vedrix/docs/getting-started.md` | New users |
| Architecture | `Vedrix/docs/architecture.md` | Engineers |
| API Reference | `Vedrix/docs/api-reference.md` | Developers |
| Deployment | `Vedrix/DEPLOYMENT.md` | DevOps |
| Onboarding | `Vedrix/docs/onboarding.md` | New developers |
| Runbook | `Vedrix/docs/runbook.md` | On-call engineers |
| Interview Engine | `Vedrix/backend/app/services/interview_engine/ARCHITECTURE.md` | AI/ML engineers |

---

## Questions?

If you have questions about contributing:

- **GitHub Discussions** — For general questions and ideas
- **Issue Tracker** — For specific bugs and feature requests
- **Team Contact** — Reach out to the maintainers via GitHub

---

*Thank you for helping make Vedrix better for everyone!* 🚀
