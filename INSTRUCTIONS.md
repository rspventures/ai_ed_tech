# AI Tutor Platform - Development Instructions

> **CRITICAL**: This document contains mandatory requirements that MUST be followed for ALL implementations.
> Read this document carefully before making any changes to the codebase.

---

## 🧪 Test Accounts

| Role | Email | Password | Notes |
|------|-------|----------|-------|
| **Admin** | `admintest1@gmail.com` | `Admintest1@` | For testing Admin dashboard, Grades, Assignments |
| **Student** | `testuser1@gmail.com` | `Testuser1@` | Grade 4 student for testing student features |

---

## 🗄️ Database Connection

| Parameter | Value | Notes |
|-----------|-------|-------|
| **Container** | `ai_tutor_db` | Docker container name |
| **Database** | `ai_tutor` | Main application database |
| **User** | `postgres` | Database user |
| **Host** | `localhost` / `ai_tutor_db` (inside Docker) | Connection host |
| **Port** | `5432` | PostgreSQL default port |

### Running Migrations
```bash
docker exec -i ai_tutor_db psql -U postgres -d ai_tutor < backend/migrations/your_migration.sql
```

---

## 🏗️ 1. Project Architecture (FUNDAMENTAL)

This project follows the **Agentic AI Architecture** pattern. Every new AI feature should be implemented using this pattern.

### Core Principles:
- **Agents extend `BaseAgent`** - All AI agents inherit from `app.ai.agents.base.BaseAgent`
- **Plan-Execute Pattern** - Agents have `plan()` and `execute()` methods
- **Safety by Default** - BaseAgent automatically applies Safety Pipeline
- **Tracing by Default** - BaseAgent automatically creates telemetry spans

### When to Use Agentic Pattern:
- ✅ New AI features with LLM calls
- ✅ Features requiring multi-step reasoning
- ✅ Features needing conversation memory
- ❌ Simple utility functions (don't overdo it)
- ❌ Database CRUD operations

### Agent File Structure:
```
backend/app/ai/agents/
├── base.py           # BaseAgent - DO NOT MODIFY without review
├── tutor.py          # Main tutoring agent
├── examiner.py       # Question generation
├── grader.py         # Answer evaluation
├── feedback.py       # Feedback generation
├── lesson.py         # Lesson content generation
├── reviewer.py       # Spaced repetition
├── image_agent.py    # Image generation
├── entity_extractor.py # Entity extraction for Graph RAG
└── ...
```

### LangGraph Orchestration (Phase 7+):

For complex multi-step workflows with conditional branching, retries, or loops, use **LangGraph graphs** alongside agents.

```
backend/app/ai/graphs/
├── __init__.py         # Module exports
├── base.py             # GraphState, utilities
├── document_graph.py   # Document processing pipeline
└── rag_graph.py        # Corrective RAG with self-correction
```

#### When to Use LangGraph vs BaseAgent:
| Use Case | Use |
|----------|-----|
| Simple LLM call with safety | BaseAgent |
| Multi-step with fixed sequence | BaseAgent |
| Conditional branching (if/else) | LangGraph |
| Retry loops with state | LangGraph |
| Complex workflows with checkpoints | LangGraph |

#### LangGraph Pattern:
```python
from langgraph.graph import StateGraph, END

class MyGraph:
    def __init__(self):
        workflow = StateGraph(MyState)
        workflow.add_node("step1", self._step1)
        workflow.add_node("step2", self._step2)
        workflow.set_entry_point("step1")
        workflow.add_conditional_edges("step1", self._route, {...})
        self._graph = workflow.compile()
    
    async def run(self, input_data):
        return await self._graph.ainvoke(input_data)
```

> **Note:** LangGraph graphs should work alongside BaseAgent. Agents handle individual steps, graphs orchestrate the flow.

---

## 🛡️ 2. Safety Pipeline (MANDATORY)

Every feature that processes user input or generates AI output MUST use the Safety Pipeline.

### For User Input:
```python
from app.ai.core.safety_pipeline import get_safety_pipeline, SafetyAction

async def process_user_input(text: str, grade: int = 5):
    pipeline = get_safety_pipeline()
    result = await pipeline.validate_input(text, grade=grade)
    
    if result.action == SafetyAction.BLOCK:
        return {"error": result.block_reason}
    
    safe_text = result.processed_text  # PII redacted, sanitized
```

### For AI Output:
```python
async def validate_ai_response(output: str, question: str, grade: int = 5):
    pipeline = get_safety_pipeline()
    result = await pipeline.validate_output(output, question, grade=grade)
    
    return result.validated_output  # Safe, validated output
```

### What the Pipeline Checks:
- **PII Detection & Redaction** - Names, emails, phone numbers, addresses
- **Injection Attack Detection** - Prompt injection attempts
- **Content Moderation** - Age-appropriate content filtering (grade-aware)
- **Output Validation** - Self-critique and refinement pattern

> **Note:** If your agent extends `BaseAgent`, safety is applied automatically in the `run()` method.

---

## 📊 3. Observability (MANDATORY)

Every AI interaction MUST be traced for monitoring, debugging, and cost tracking.

### Dual Observability Systems:
| System | Purpose | Dashboard |
|--------|---------|-----------|
| **OpenTelemetry → Jaeger** | Distributed tracing | `http://localhost:16686` |
| **Langfuse** | LLM-specific analytics | `http://localhost:3001` |

### Adding Traces:
```python
from app.ai.core.observability import get_observer

async def ai_operation(request_data):
    observer = get_observer()
    trace = observer.create_trace(
        name="operation_name",
        user_id=user.id,
        metadata={"feature": "voice", "grade": grade}
    )
    
    with trace.span("llm_call") as span:
        response = await llm.generate(...)
        span.update(output=response)
    
    return response
```

### What to Trace:
- All LLM API calls (input, output, latency, tokens)
- Agent decisions (plan, actions, tool calls)
- Safety pipeline results (blocked content, PII detection)
- Voice/Vision feature usage
- Error events

---

## 📚 4. Curriculum & Data Seeding

### Full Curriculum Seeding Script:
The complete CBSE curriculum (Grades 1-7, all subjects) is seeded using:

```bash
# From backend container
python -c "import asyncio; from app.scripts.seed_curriculum_cbse_full import seed_all; asyncio.run(seed_all())"
```

**File:** `backend/app/scripts/seed_curriculum_cbse_full.py`

### ⚠️ IMPORTANT:
1. **DO NOT run redundant seeding scripts** - The full script covers everything
2. **DO NOT create new curriculum SQL migrations** - Use the Python script instead
3. **Check if data exists before seeding** - The script is idempotent

### Other Seeding Scripts:
| Script | Purpose | Status |
|--------|---------|--------|
| `seed_curriculum_cbse_full.py` | Complete CBSE curriculum | ✅ PRIMARY |
| `seed_curriculum.py` | Legacy/demo curriculum | ⚠️ DEPRECATED |
| `expand_subtopics.py` | AI-powered subtopic expansion | UTILITY |

---

## 🗄️ 5. Database & Migrations

### Before Writing Any Migration:

1. **Check existing schema** - Run `\d+ table_name` in psql
2. **Check existing migrations** - Look in `backend/migrations/`
3. **Check if column/table exists** - Avoid duplicate migrations

### Migration File Naming:
```
migrations/
├── 00_init_vector.sql          # Vector extension
├── 00_create_langfuse_db.sql   # Langfuse database
├── phase2_rag_documents.sql    # RAG feature
├── phase3_migration.sql        # Phase 3 features
└── ...
```

### Disabled Migrations:
Files ending in `.disabled` have already been applied. **DO NOT re-run them.**

### Fresh Setup (First Pull from GitHub):
For **fresh setups**, migrations run **automatically** via `docker-entrypoint-initdb.d`:
1. The `backend/migrations/` folder is mounted to PostgreSQL's init directory
2. SQL files are executed **alphabetically** on first DB initialization
3. Use numeric prefixes for ordering: `00_init.sql`, `01_users.sql`, `04_phase4.sql`
4. Files with `.disabled` suffix are ignored by PostgreSQL

> **Important**: This only runs when the DB volume is **empty** (first `docker-compose up`).
> For **existing databases**, run migrations manually:
> ```bash
> docker exec -i ai_tutor_db psql -U postgres -d ai_tutor -f /docker-entrypoint-initdb.d/04_phase4_teacher_suite.sql
> ```

### Migration Best Practices:
```sql
-- ✅ GOOD: Idempotent migration
CREATE TABLE IF NOT EXISTS my_table (...);
ALTER TABLE my_table ADD COLUMN IF NOT EXISTS new_column TEXT;

-- ❌ BAD: Will fail if already exists
CREATE TABLE my_table (...);
ALTER TABLE my_table ADD COLUMN new_column TEXT;
```

### Common Tables (Already Exist):
- `users`, `students`, `students_parents`
- `subjects`, `topics`, `subtopics`
- `progress`, `generated_lessons`, `student_lesson_progress`
- `questions`, `assessments`, `assessment_questions`
- `documents`, `document_chunks`
- `gamification_profiles`, `achievements`, `student_achievements`
- `schools`, `classes`, `class_enrollments` (Phase 4)
- `assignments`, `assignment_submissions`, `class_announcements` (Phase 4)

---

## 🎨 6. Feature Implementation Checklist

Before marking any AI feature as complete, verify:

- [ ] **Extends BaseAgent** (or has explicit safety/telemetry)
- [ ] **Safety Pipeline** - Input validation with `validate_input()`
- [ ] **Safety Pipeline** - Output validation with `validate_output()`
- [ ] **Observability** - Traces created (BaseAgent does this automatically)
- [ ] **Error Handling** - Graceful fallbacks for safety blocks
- [ ] **Logging** - Appropriate log levels (INFO, WARNING, ERROR)
- [ ] **Testing** - Unit tests for happy path and edge cases
- [ ] **Documentation** - Updated this file if adding new patterns

---

## 🔌 7. Integration Points

### Features Requiring Safety + Observability:

| Feature | Input Safety | Output Safety | Observability |
|---------|--------------|---------------|---------------|
| TutorChat (Text) | ✅ Required | ✅ Required | ✅ Required |
| TutorChat (Vision) | ✅ Required | ✅ Required | ✅ Required |
| Voice Mode | ✅ Required* | ✅ Required* | ✅ Required |
| Quiz Generation | - | ✅ Required | ✅ Required |
| Image Generation | ✅ Required | ✅ Required | ✅ Required |
| Document Processing | ✅ Required | - | ✅ Required |
| Lesson Generation | - | ✅ Required | ✅ Required |
| Answer Evaluation | ✅ Required | ✅ Required | ✅ Required |

*Voice input/output safety applies to transcribed text

---

## ⚠️ 8. Common Mistakes to Avoid

### Architecture:
1. **Bypassing BaseAgent** - Don't create standalone agents without safety hooks
2. **Over-engineering** - Not everything needs to be an agent (use judgment)
3. **Direct LLM calls** - Always go through agents or instrumented clients

### Data:
4. **Running redundant seeds** - Use `seed_curriculum_cbse_full.py` only
5. **Duplicate migrations** - Check existing schema before adding ALTER statements
6. **Missing IF NOT EXISTS** - Always use idempotent SQL

### Security:
7. **Hardcoded API keys** - Use `settings.OPENAI_API_KEY` from config
8. **No user context** - Always pass user_id to traces for debugging
9. **Logging PII** - Never log raw user input, use redacted version

---

## 📝 9. Code Review Checklist

Before merging any PR involving AI features:

1. Does it use `SafetyPipeline` for all user inputs?
2. Does it validate AI outputs before returning to user?
3. Are traces created with meaningful names?
4. Are errors logged with appropriate context?
5. Is PII properly redacted in logs?
6. Does it extend BaseAgent (if applicable)?
7. Are there any redundant database migrations?

---

## 🔧 10. Development Commands

### Start Services:
```bash
docker-compose up -d --build
```

### View Logs:
```bash
docker logs ai_tutor_backend -f
docker logs ai_tutor_frontend -f
```

### Access Dashboards:
- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000/docs
- **Langfuse:** http://localhost:3001
- **Jaeger:** http://localhost:16686

### Run Migrations:
```bash
docker exec -it ai_tutor_backend psql -U tutor -d ai_tutor -f /app/migrations/new_migration.sql
```

### Seed Curriculum:
```bash
docker exec -it ai_tutor_backend python -c "import asyncio; from app.scripts.seed_curriculum_cbse_full import seed_all; asyncio.run(seed_all())"
```

---

## 📁 11. Key File Locations

| Purpose | Location |
|---------|----------|
| Agents | `backend/app/ai/agents/` |
| Safety Pipeline | `backend/app/ai/core/safety_pipeline.py` |
| Observability | `backend/app/ai/core/observability.py` |
| API Endpoints | `backend/app/api/v1/` |
| Database Models | `backend/app/models/` |
| Migrations | `backend/migrations/` |
| Curriculum Scripts | `backend/app/scripts/` |
| Frontend Components | `frontend/src/components/` |
| Frontend Pages | `frontend/src/pages/` |
| **Documentation** | `README.md`, `INSTRUCTIONS.md` |
| **Docker Config** | `docker-compose.yml` |

---

## 🌐 11.5. Frontend Development Guidelines (MANDATORY)

> **All frontend changes MUST be implemented for BOTH web and mobile platforms.**

### Key Requirements:
1. **Responsive Design** - All UI components must work on desktop and mobile viewports
2. **Touch-Friendly** - Buttons and interactive elements must have adequate touch targets (min 44px)
3. **Test Both** - Verify changes on both desktop (Chrome) and mobile (Chrome DevTools mobile emulation)
4. **Shared Components** - Use shared components in `frontend/src/components/` for consistency

### Mobile Testing Checklist:
- [ ] UI renders correctly at 375px width (iPhone SE)
- [ ] UI renders correctly at 414px width (iPhone 12 Pro)
- [ ] Touch targets are at least 44x44px
- [ ] No horizontal scrolling on mobile
- [ ] Forms are usable with mobile keyboard

---

## 📖 12. Documentation Requirements (MANDATORY)

### Files to Update When Making Changes:

| Change Type | Update Required |
|-------------|-----------------|
| New feature or endpoint | `README.md` (Features section) |
| New environment variable | `README.md` + `.env.example` |
| Docker/service change | `docker-compose.yml` + `README.md` |
| New development pattern | `INSTRUCTIONS.md` |
| New API endpoint | `README.md` (API section) |
| Database schema change | `INSTRUCTIONS.md` (Tables section) |
| New dependency | `requirements.txt` + `README.md` (if major) |

### README.md Sections to Maintain:
- Features list
- Environment variables
- Setup instructions
- API documentation
- Troubleshooting

### INSTRUCTIONS.md Sections to Maintain:
- Architecture patterns
- Safety/Observability requirements
- Database tables list
- Common mistakes to avoid
- Development commands

---

## 🔐 13. Git & Security Guidelines (CRITICAL)

### Before Every Git Push:

> ⚠️ **NEVER commit `.env` files to the repository!**

```bash
# Check if .env is being tracked
git status

# If .env shows up, remove it from staging
git reset HEAD .env
git reset HEAD backend/.env
git reset HEAD frontend/.env

# Ensure .env is in .gitignore
echo ".env" >> .gitignore
echo "*.env" >> .gitignore
```

### Safe Git Push Workflow:
```bash
# 1. Check what's being committed
git status
git diff --cached

# 2. Verify no secrets
git diff --cached | grep -i "api_key\|secret\|password" 

# 3. Only then push
git add .
git commit -m "Your message"
git push origin main
```

### Files That Should NEVER Be Committed:
```
.env                    # Root environment file
backend/.env            # Backend secrets
frontend/.env           # Frontend secrets
*.env.local             # Local overrides
.env.production         # Production secrets
__pycache__/            # Python cache
node_modules/           # Node dependencies
*.pyc                   # Compiled Python
.DS_Store               # macOS files
```

### Verify .gitignore Contains:
```gitignore
# Environment files
.env
*.env
.env.*
!.env.example

# Secrets
*.pem
*.key
secrets/
```

### If You Accidentally Committed .env:
```bash
# Remove from git history (but keeps local file)
git rm --cached .env
git commit -m "Remove .env from tracking"

# Add to .gitignore
echo ".env" >> .gitignore
git add .gitignore
git commit -m "Add .env to gitignore"
```

---

## 🔄 14. Before Pushing to GitHub Checklist

- [ ] No `.env` files in staging (`git status`)
- [ ] No API keys or secrets in code (`grep -r "sk-" .`)
- [ ] `README.md` updated if adding features
- [ ] `INSTRUCTIONS.md` updated if adding patterns
- [ ] `docker-compose.yml` updated if changing services
- [ ] All tests passing
- [ ] Documentation reflects current state

---

## 📝 15. Planning & Artifact Files (IMPORTANT)

> ⚠️ **DO NOT create new planning files.** Use ONLY these existing files.

### Location
`C:\Users\pranaldongare\.gemini\antigravity\brain\efb10914-ee46-485a-89d7-5f1b35018871\`

### Files to Use

| File | Purpose | When to Update |
|------|---------|----------------|
| **roadmap.md** | All pending enhancements (single source of truth) | When adding/completing features |
| **implementation_plan.md** | Current enhancement plan | When starting new enhancement |
| **task.md** | Task checklist for work tracking | During implementation |
| **walkthrough.md** | Documentation of completed work | After completing features |

### Rules
1. **Never create new phase/enhancement files** (e.g., NO `implementation_plan_phase7.md`)
2. **Always update existing files** instead of creating new ones
3. **roadmap.md** is the ONLY source for pending enhancements
4. **implementation_plan.md** should always reflect the CURRENT work item

---

*Last Updated: December 21, 2025*
