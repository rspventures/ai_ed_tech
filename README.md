# AI Tutor Platform 🎓

An AI-powered educational platform for K-12 students (Grades 1-12) featuring personalized learning, adaptive assessments, gamification, RAG-based document Q&A, and AI-generated visual explanations. Built with complete CBSE/NCERT aligned curriculum.

## ✨ Features

### Core Learning
- 🤖 **AI Question Generation** - Generates unique, grade-appropriate questions
- 📊 **Multiple Assessment Types** - Practice, Tests, Assessments, and Exams
- 🎮 **Gamification** - XP, streaks, levels, and achievements
- 📈 **Progress Tracking** - Detailed analytics and mastery levels
- 🔄 **Batch Pre-fetching** - Fast question delivery in practice mode
- 💬 **AI Feedback** - Personalized feedback after each assessment

### Document & RAG Features (Phase 2)
- 📄 **Document Upload** - Upload PDFs and study materials
- 🔍 **RAG-Powered Q&A** - Chat with your documents using AI
- 📝 **Quiz Generation** - Auto-generate quizzes from uploaded documents
- ✅ **Document Validation** - AI validates grade-appropriateness of uploads

### Visual Learning (Phase 2C)
- 🎨 **Visual Explainer** - Generate educational illustrations using DALL-E 3
- 🛡️ **Content Guardrails** - Multi-layer safety for student-appropriate content
- 📚 **Grade-Appropriate Styling** - Images styled for specific grade levels

### Parent Dashboard
- 👨‍👩‍👧 **Child Progress Monitoring** - Track children's learning journey
- 📊 **Performance Analytics** - View scores, time spent, and mastery levels
- 🎯 **AI Insights** - AI-generated recommendations

---

## 🚀 Quick Start with Docker (Recommended)

### Prerequisites
- Docker Desktop installed and running
- Git
- OpenAI API Key (required for AI features)

### Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/AITutorPlatform.git
   cd AITutorPlatform
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   ```

3. **Add your OpenAI API key** to `.env`:
   ```env
   OPENAI_API_KEY=your_openai_key_here
   ```

4. **Start the application**
   ```bash
   docker-compose up -d --build
   ```

   > **Note:** On first startup:
   > - Database migrations run automatically (via `/docker-entrypoint-initdb.d/`)
   > - CBSE curriculum is auto-seeded when the database is empty
   > - pgvector extension is enabled for RAG features

5. **Access the app**
   - 🌐 Frontend: http://localhost:3000
   - 🔌 Backend API: http://localhost:8000
   - 📖 API Docs: http://localhost:8000/docs
   - 🔍 Jaeger Tracing: http://localhost:16686

### Stopping
```bash
docker-compose down
```

### Reset Database (Fresh Start)
```bash
docker-compose down -v  # Removes all data
docker-compose up -d --build
```

---

## 💻 Running from IDE (Development)

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL 16+ with pgvector extension
- Redis

### Backend Setup

1. **Navigate to backend**
   ```bash
   cd backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Mac/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set environment variables** (create `.env` in backend folder):
   ```bash
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ai_tutor
   REDIS_URL=redis://localhost:6379
   OPENAI_API_KEY=your_key_here
   SECRET_KEY=your-secret-key
   ```

5. **Run database migrations**
   ```bash
   # Run all SQL migrations in order
   psql -U postgres -d ai_tutor -f migrations/gamification_migration.sql
   psql -U postgres -d ai_tutor -f migrations/phase2_rag_documents.sql
   psql -U postgres -d ai_tutor -f migrations/phase2e_document_validation.sql
   psql -U postgres -d ai_tutor -f migrations/phase3_migration.sql
   psql -U postgres -d ai_tutor -f migrations/english_curriculum.sql
   ```

6. **Seed the database** (full CBSE curriculum)
   ```bash
   python -m app.scripts.seed_curriculum_cbse_full
   ```

7. **Start the server**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Frontend Setup

1. **Navigate to frontend**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Start development server**
   ```bash
   npm run dev
   ```

4. **Access at** http://localhost:3000

---

## 📁 Project Structure

```
AITutorPlatform/
├── backend/
│   ├── app/
│   │   ├── ai/              # AI agents and LLM integration
│   │   │   ├── agents/      # Specialized agents
│   │   │   │   ├── examiner.py      # Question generation
│   │   │   │   ├── feedback.py      # Assessment feedback
│   │   │   │   ├── rag.py           # Document Q&A
│   │   │   │   ├── image_agent.py   # Visual generation (DALL-E)
│   │   │   │   └── document_validator.py  # Content validation
│   │   │   └── core/        # LLM client and utilities
│   │   ├── api/v1/          # API endpoints
│   │   │   ├── auth.py      # Authentication
│   │   │   ├── curriculum.py # Subjects/Topics/Subtopics
│   │   │   ├── practice.py  # Practice sessions
│   │   │   ├── documents.py # RAG & Document upload
│   │   │   └── visuals.py   # Image generation
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # Business logic
│   │   └── scripts/         # Database seeders
│   ├── migrations/          # SQL migrations (auto-run by Docker)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/           # React pages
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── DocumentsPage.tsx   # RAG interface
│   │   │   ├── VisualsPage.tsx     # Image generation
│   │   │   └── ...
│   │   ├── components/      # Reusable components
│   │   ├── services/        # API services
│   │   └── stores/          # Zustand state management
│   └── package.json
├── docker-compose.yml
└── README.md
```

---

## 🔧 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key (for GPT-4 & DALL-E) | Yes |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `REDIS_URL` | Redis connection string | Yes |
| `SECRET_KEY` | JWT secret key | Yes |
| `LLM_PROVIDER` | AI provider: "openai" or "anthropic" | No (default: openai) |
| `LLM_TIMEOUT_SECONDS` | Timeout for AI requests | No (default: 60) |

---

## 🔗 Key API Endpoints

### Authentication
| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/auth/register` | Register new user |
| `POST /api/v1/auth/login` | Login |
| `GET /api/v1/auth/profile` | Get user profile |

### Learning
| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/curriculum/subjects` | List subjects |
| `POST /api/v1/practice/start` | Start practice session |
| `POST /api/v1/tests/start` | Start a test |
| `POST /api/v1/exams/start` | Start an exam |

### Documents & RAG
| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/documents/upload` | Upload document |
| `POST /api/v1/documents/{id}/chat` | Chat with document |
| `POST /api/v1/documents/{id}/quiz` | Generate quiz |

### Visuals
| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/visuals/explain` | Generate visual explanation |
| `GET /api/v1/visuals/` | List generated visuals |
| `DELETE /api/v1/visuals/{id}` | Delete visual |

### Gamification
| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/gamification/profile` | Get XP and achievements |

---

## 🛡️ Content Safety

The platform includes comprehensive content guardrails:

### Image Generation Guardrails
1. **Blocked Terms List** - Instantly rejects violence, romance, drugs, horror
2. **Educational Whitelist** - Validates against educational topic categories
3. **LLM Validation** - AI evaluates if content is grade-appropriate

### Document Validation
- Validates uploaded documents for grade-appropriateness
- Blocks professional resumes, inappropriate content
- Ensures educational relevance

---

## 📚 Curriculum

Complete CBSE/NCERT aligned curriculum:

| Subject | Grades | Topics | Description |
|---------|--------|--------|-------------|
| Mathematics | 1-12 | 50+ | Numbers, Algebra, Geometry, Trigonometry, Calculus |
| Science | 1-12 | 60+ | Physics, Chemistry, Biology, Environmental Science |
| English | 1-12 | 45+ | Grammar, Vocabulary, Reading, Writing Skills |

All topics include multiple subtopics with difficulty levels (easy, medium, hard) for adaptive learning.

---

## 🔍 Troubleshooting

### Docker Issues

**Container won't start:**
```bash
docker-compose down
docker-compose up -d --build
```

**Check logs:**
```bash
docker logs ai_tutor_backend
docker logs ai_tutor_frontend
```

**Backend errors:**
```bash
docker exec -it ai_tutor_backend bash
# Then check logs or run commands
```

### Database Issues

**Reset database:**
```bash
docker-compose down -v  # Removes volumes
docker-compose up -d --build
```

**Re-run migrations (if needed):**
```bash
docker exec -it ai_tutor_backend python -c "
from app.db.session import engine
from app.models import *
import asyncio
asyncio.run(Base.metadata.create_all(bind=engine))
"
```

### No Subjects Showing

Run the curriculum seeder:
```bash
docker exec -it ai_tutor_backend python -m app.scripts.seed_curriculum_cbse_full
```

### Image Generation Failing

1. Check OpenAI API key is set correctly
2. Ensure sufficient API credits
3. Check if prompt is being blocked by guardrails (educational content only)

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

MIT License - see LICENSE file for details.

---

## 🙏 Acknowledgments

- OpenAI for GPT-4 and DALL-E 3
- FastAPI for the backend framework
- React and Vite for the frontend
- PostgreSQL with pgvector for vector storage
