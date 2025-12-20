# AI Tutor Platform 🎓

An AI-powered educational platform for K-12 students (Grades 1-7) featuring personalized learning, adaptive assessments, and gamification. Built with complete CBSE/NCERT aligned curriculum.

## Features

- 🤖 **AI Question Generation** - Generates unique, grade-appropriate questions
- 📊 **Multiple Assessment Types** - Practice, Tests, Assessments, and Exams
- 🎮 **Gamification** - XP, streaks, and achievements
- 📈 **Progress Tracking** - Detailed analytics and mastery levels
- 🔄 **Batch Pre-fetching** - Fast question delivery in practice mode
- 💬 **AI Feedback** - Personalized feedback after each assessment

## Quick Start with Docker (Recommended)

### Prerequisites
- Docker Desktop installed and running
- Git

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

3. **Add your API keys** to `.env`:
   ```env
   OPENAI_API_KEY=your_openai_key_here
   # OR
   ANTHROPIC_API_KEY=your_anthropic_key_here
   ```

4. **Start the application**
   ```bash
   docker-compose up -d --build
   ```

   > **Note:** On first startup, the backend automatically seeds the complete CBSE 
   > curriculum (Mathematics, Science, English for Grades 1-7) when the database 
   > is empty. Subsequent restarts skip this since data already exists.

5. **Access the app**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Stopping
```bash
docker-compose down
```

---

## Running from IDE (Development)

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL 15+
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

4. **Set environment variables**
   ```bash
   # Create .env in backend folder or set in terminal
   export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ai_tutor
   export REDIS_URL=redis://localhost:6379
   export OPENAI_API_KEY=your_key_here
   ```

5. **Run database migrations**
   ```bash
   alembic upgrade head
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

## Project Structure

```
AITutorPlatform/
├── backend/
│   ├── app/
│   │   ├── ai/              # AI agents and LLM integration
│   │   │   ├── agents/      # Specialized agents (Examiner, Feedback, etc.)
│   │   │   └── core/        # LLM client and utilities
│   │   ├── api/v1/          # API endpoints
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   └── services/        # Business logic
│   ├── alembic/             # Database migrations
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/           # React pages
│   │   ├── components/      # Reusable components
│   │   └── services/        # API services
│   └── package.json
├── docker-compose.yml
└── README.md
```

---

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key | Yes* |
| `ANTHROPIC_API_KEY` | Anthropic API key | Yes* |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `REDIS_URL` | Redis connection string | Yes |
| `SECRET_KEY` | JWT secret key | Yes |

*At least one AI provider key is required.

---

## API Documentation

When running, access the interactive API docs at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/auth/register` | Register new user |
| `POST /api/v1/auth/login` | Login |
| `GET /api/v1/curriculum/subjects` | List subjects |
| `POST /api/v1/practice/start` | Start practice session |
| `POST /api/v1/tests/start` | Start a test |
| `POST /api/v1/exams/start` | Start an exam |
| `GET /api/v1/gamification/profile` | Get XP and achievements |

---

## Troubleshooting

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

### Database Issues

**Reset database:**
```bash
docker-compose down -v  # Removes volumes
docker-compose up -d --build
```

### LLM Timeout Issues

If questions take too long to generate, check your API key and network connection.

### No Subjects Showing

If no subjects appear in the app, the curriculum may not have been seeded. Run:
```bash
docker exec -it ai_tutor_backend python -m app.scripts.seed_curriculum_cbse_full
```

---

## Curriculum

The platform includes a complete CBSE/NCERT aligned curriculum:

| Subject | Grades | Topics | Description |
|---------|--------|--------|-------------|
| Mathematics | 1-7 | 46+ | Numbers, Operations, Fractions, Geometry, Algebra, Data Handling |
| Science | 1-7 | 56+ | Plants, Animals, Human Body, Matter, Energy, Environment |
| English | 1-7 | 42+ | Grammar, Vocabulary, Reading Comprehension, Writing Skills |

All topics include multiple subtopics with difficulty levels (easy, medium, hard) for adaptive learning.

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## License

MIT License - see LICENSE file for details.
