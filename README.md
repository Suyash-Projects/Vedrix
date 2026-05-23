# Vedrix AI Interview System

**High-fidelity, agentic AI interview platform with LangGraph orchestration**

Vedrix is a full-stack AI-powered interview system designed for both candidates (B2C) and recruiters/HR teams (B2B). Built with FastAPI, React, SQLite/PostgreSQL, and LangGraph, it provides realistic interview experiences with AI-driven evaluation and feedback.

## 🚀 Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd Vedrix

# Start development environment
python run_dev.py
```

The script will:
- Auto-allocate free ports for backend (8000+) and frontend (5173+)
- Start both services concurrently
- Generate frontend environment file with correct API URL
- Display actual URLs in console output

**Access the application:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## 📚 Documentation

- [Getting Started Guide](./docs/getting-started.md)
- [API Reference](./docs/api-reference.md)
- [Architecture Overview](./docs/architecture.md)
- [Deployment Guide](./Vedrix/DEPLOYMENT.md)
- [Onboarding Guide](./docs/onboarding.md)
- [Contributing Guidelines](./CONTRIBUTING.md)

## 🛠️ Development Commands

| Command | Purpose |
|---------|---------|
| `python Vedrix/run_dev.py` | Full stack development (both services) |
| `cd Vedrix/backend && python -m pytest` | Run backend tests |
| `cd Vedrix/frontend && npm run lint` | ESLint check |
| `cd Vedrix/frontend && npm run build` | Production build |
| `docker-compose -f Vedrix/docker-compose.yml up` | PostgreSQL + Redis services |
| `make docker-up` | Start all services via Docker |
| `make db-backup` | Backup database |
| `make deploy-staging` | Deploy to staging |
| `make deploy-prod` | Deploy to production |

## 🏗️ Architecture

Vedrix follows a modern microservices-inspired architecture:

- **Backend**: FastAPI with async-first design
- **Frontend**: React with Zustand state management and React Query
- **Database**: SQLite (dev) / PostgreSQL (prod) with SQLModel ORM
- **AI Engine**: LangGraph-based interview orchestration
- **Real-time Communication**: WebSocket connections for live interviews
- **Caching**: Redis for session management and rate limiting
- **Styling**: Tailwind CSS v4 with `@tailwindcss/vite`

Key components:
- Authentication & Authorization system
- Interview Engine (LangGraph powered)
- Candidate & Recruiter dashboards
- Admin panel for platform management
- AI service integrations (Groq, DeepSeek, OpenRouter)

## 🔧 Configuration

Environment variables are managed through:
- `Vedrix/backend/.env` - Backend configuration
- `Vedrix/frontend/.env.development.local` - Frontend API URL (auto-generated)

See the [Deployment Guide](./Vedrix/DEPLOYMENT.md) for production configuration details.

## 🧪 Testing

```bash
# Backend tests
cd Vedrix/backend
python -m pytest

# Frontend tests
cd Vedrix/frontend
npm test

# Linting
cd Vedrix/frontend
npm run lint
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](./CONTRIBUTING.md) for details on:
- Code style and standards
- Pull request process
- Issue reporting
- Development workflow

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 💬 Support

For questions and support:
- GitHub Issues: [link-to-issues]
- Documentation: [link-to-docs]
- Email: support@vedrix.com

---

*Built with ❤️ for transforming the interview experience*