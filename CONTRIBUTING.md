# Contributing to AI Tutor Platform

Thank you for your interest in contributing! This guide will help you get started.

## 🚀 Getting Started

### 1. Clone the Repository
```bash
git clone https://github.com/rspventures/ai_ed_tech.git
cd ai_ed_tech
```

### 2. Set Up Your Environment

**Option A: Docker (Recommended for full stack)**
```bash
cp .env.example .env
# Add your OPENAI_API_KEY to .env
docker-compose up -d --build
```

**Option B: Local Development**
See [README.md](README.md) for detailed setup of each component.

---

## 📁 Project Structure Overview

| Folder | Technology | Purpose |
|--------|------------|---------|
| `backend/` | Python FastAPI | REST API, AI agents, database |
| `frontend/` | React + Vite | Web application |
| `mobile-app/` | React Native + Expo | Mobile application |

---

## 🔧 Development Workflow

### Creating a New Feature

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** (see component guides below)

3. **Test locally**
   ```bash
   # Backend tests
   cd backend && pytest
   
   # Frontend type check
   cd frontend && npm run build
   
   # Mobile type check
   cd mobile-app && npx tsc --noEmit
   ```

4. **Commit with conventional commits**
   ```bash
   git commit -m "feat: add new feature"
   git commit -m "fix: resolve bug in X"
   git commit -m "docs: update README"
   ```

5. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

---

## 🐍 Backend Development

### Adding a New API Endpoint

1. Create endpoint in `backend/app/api/v1/your_feature.py`
2. Add Pydantic schemas in `backend/app/schemas/`
3. Add SQLAlchemy models in `backend/app/models/` (if needed)
4. Register router in `backend/app/api/v1/__init__.py`

### Adding a New AI Agent

1. Create agent in `backend/app/ai/agents/your_agent.py`
2. Extend `BaseAgent` from `backend/app/ai/agents/base.py`
3. Add to agent registry if needed

### Database Migrations

Create SQL migration files in `backend/migrations/`:
```sql
-- backend/migrations/your_migration.sql
ALTER TABLE your_table ADD COLUMN new_column TEXT;
```

---

## ⚛️ Frontend Development

### Adding a New Page

1. Create page in `frontend/src/pages/YourPage.tsx`
2. Add route in `frontend/src/App.tsx`
3. Create API service in `frontend/src/services/`

### State Management

- Use **Zustand** for global state (`frontend/src/stores/`)
- Keep component state local when possible

---

## 📱 Mobile App Development

### Adding a New Screen

1. Create screen in `mobile-app/app/your-feature/[id].tsx`
2. Expo Router automatically handles routing

### Adding a New Service

1. Create service in `mobile-app/src/services/your_service.ts`
2. Add types in `mobile-app/src/types/index.ts`

### API Configuration

Update base URL in `mobile-app/src/api/client.ts`:
```typescript
// Android Emulator
baseURL: 'http://10.0.2.2:8000/api/v1'

// iOS / Physical Device
baseURL: 'http://YOUR_IP:8000/api/v1'
```

---

## 🧪 Testing

### Backend
```bash
cd backend
pytest                    # Run all tests
pytest -v                 # Verbose output
pytest tests/test_auth.py # Specific file
```

### Frontend
```bash
cd frontend
npm run build    # Type check + build
npm run lint     # ESLint
```

### Mobile
```bash
cd mobile-app
npx tsc --noEmit   # Type check
npx expo start     # Run dev server
```

---

## 📝 Code Style

- **Python**: Follow PEP 8, use Black formatter
- **TypeScript**: Use ESLint + Prettier
- **React**: Functional components, hooks
- **React Native**: Same as React, use StyleSheet

---

## 🔗 Useful Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f backend

# Restart a service
docker-compose restart backend

# Reset database
docker-compose down -v
docker-compose up -d --build

# Seed curriculum
docker exec -it ai_tutor_backend python -m app.scripts.seed_curriculum_cbse_full
```

---

## 📚 Key Files Reference

| What | Where |
|------|-------|
| API endpoints | `backend/app/api/v1/` |
| AI agents | `backend/app/ai/agents/` |
| Database models | `backend/app/models/` |
| Web pages | `frontend/src/pages/` |
| Mobile screens | `mobile-app/app/` |
| API services | `*/services/*.ts` |

---

## ❓ Need Help?

- Check existing code for patterns
- Review the [README.md](README.md) for setup details
- Look at similar features for implementation guidance

Happy coding! 🎉
