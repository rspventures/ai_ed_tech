# Implementation Plan: Adaptive Learning & AI Lesson Generation

## 🎯 Objective
Transform the platform from a "Quiz App" into an **Intelligent Tutor** by implementing:
1.  **Adaptive Learning Paths:** Dynamically guiding students through content based on their mastery level.
2.  **AI Lesson Generation:** creating personalized, grade-appropriate educational content (lessons) on the fly using Agentic AI.

---

## 🏗️ Architecture: The Agentic Approach

We will move beyond simple CRUD and implement two specialized AI Agents:

### 1. The Curriculum Agent (The Brain) 🧠
*   **Role:** Analyzes user data to decide *what* the student should do next.
*   **Logic:**
    *   **Mastery < 40%:** "Introduce Concept" -> Triggers **Lesson Generation**.
    *   **Mastery 40-70%:** "Reinforce" -> Triggers **Practice Questions** (Easy/Medium).
    *   **Mastery > 70%:** "Challenge" -> Triggers **Assessment** or **Next Topic**.
*   **Data Source:** `Progress` table, `AssessmentResult` history.

### 2. The Lesson Designer Agent (The Creator) 🎨
*   **Role:** Generates rich, engaging lesson content for a specific subtopic.
*   **Capabilities:**
    *   Explain complex topics in simple, grade-appropriate terms.
    *   Generate real-world examples (e.g., "Math with Apples").
    *   Structure content into: "Hook", "Explanation", "Example", "Summary".
*   **Output:** Structured Markdown/JSON content.

---

## 💾 Phase 1: Database Schema & Models

We need to store generated content (to avoid re-generating expensive AI lessons) and track if a student has studied them.

### New Model: `GeneratedLesson` (`backend/app/models/lesson.py`)
| Field | Type | Purpose |
|-------|------|---------|
| `id` | UUID | Primary Key |
| `subtopic_id` | UUID | Link to curriculum |
| `grade_level` | Integer | Targeted grade |
| `title` | String | Engaging title (e.g., "The Magic of Addition") |
| `content` | JSONB | Sections: { "intro": "...", "sections": [...], "summary": "..." } |
| `generated_by` | String | AI Model Version (e.g. "gpt-4o") |

### New Model: `StudentLessonProgress` (`backend/app/models/lesson.py`)
| Field | Type | Purpose |
|-------|------|---------|
| `student_id` | UUID | The student |
| `lesson_id` | UUID | The lesson studied |
| `completed_at` | DateTime | When they finished reading |

---

## 🧠 Phase 2: AI Services

### 2.1 `LessonGenerator` (LangChain)
*   **Context:** `backend/app/ai/lesson_generator.py`
*   **Prompt Strategy:** Persona-based ("You are a friendly primary school teacher...").
*   **Output Parser:** `JsonOutputParser` for structured frontend rendering.

### 2.2 `LearningPathService` (The Logic Layer)
*   **Context:** `backend/app/services/learning_path.py`
*   **Method:** `get_next_step(student_id, topic_id)`
    *   Fetches User Progress.
    *   Calculates `mastery_score`.
    *   Returns Action Object: `{ type: 'LESSON' | 'PRACTICE', resource_id: ..., reason: "You need to learn the basics first!" }`

---

## 🔌 Phase 3: Backend API Endpoints

### New Router: `backend/app/api/v1/study.py`

| Method | Endpoint | Description |
|--------|----------|-------------|
| **GET** | `/study/next-step?topic_id=...` | Returns the recommended action (Lesson/Practice) |
| **GET** | `/study/lesson/{subtopic_id}` | Gets existing lesson or **triggers generation** if missing |
| **POST** | `/study/lesson/{lesson_id}/complete` | Marks lesson as read, updates stats |

---

## 💻 Phase 4: Frontend Implementation

### 4.1 UI Components
*   **`LessonView.tsx`:**
    *   Rich text renderer for the AI lesson.
    *   "I Understand" button to complete the lesson.
    *   "Too Hard? Simplify" button (future scope).

*   **`StudyPage.tsx`:**
    *   The main container that manages the flow.
    *   Switches between `LessonView` and `PracticeSession` based on the API response.

### 4.2 Dashboard Integration
*   Replace static "Practice" button with **"Start Learning Path"**.
*   Add a "Next Up" card showing the recommended activity.

---

## 🚀 Execution Order

1.  **Define Models:** Create `lesson.py` and run migration locally/docker.
2.  **Build AI Generator:** Implement `LessonGenerator` with LangChain.
3.  **Build Logic:** Implement `LearningPathService` to route students.
4.  **Backend API:** Create endpoints.
5.  **Frontend:** Build the UI to consume the tailored content.
