# Phase 3 Implementation: Student Settings & Personalization

## 🎯 Phase Goals
**Phase 3.1:** Student Settings & Profile Management ("Make it Mine")

This phase builds the "Student Profile" foundation required for future Gamification (Phase 3.2).

---

## ⚙️ Phase 3.1: Student Settings & Profile

### Feature: Unified Settings Page

#### Backend Implementation

**1. Database Migration**
*   **Table:** `students`
*   **Change:** Add `preferences` column (Type: `JSONB`, Default: `{}`)
*   **Purpose:** To store flexible user settings like `avatar_id`, `theme`, `curriculum_focus`.
*   **Schema Update:** Ensure `grade_level` is editable.

**2. API Updates: `backend/app/api/v1/students.py`**
| Method | Endpoint | Description |
|--------|----------|-------------|
| PATCH | `/students/me` | Update profile (grade, name, preferences) |
| GET | `/students/me/settings` | Get current settings (if not in /me) |

**3. Schemas: `backend/app/schemas/student.py`**
```python
class StudentUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    grade_level: Optional[int] = None
    preferences: Optional[Dict[str, Any]] = None  # JSONB bucket
```

#### Frontend Implementation

**1. New Page: `frontend/src/pages/SettingsPage.tsx`**
*   **Section 1: Academic Profile**
    *   `GradeLevelPicker`: Dropdown (1-12)
    *   `SubjectFocus`: Multi-select toggle (Math, Science, etc.)
*   **Section 2: Personalization**
    *   `AvatarSelector`: Grid of 4-6 preset avatars (Owl, Robot, Fox, Cat, etc.)
    *   `DisplayNameInput`: Simple text field
*   **Section 3: Account**
    *   Password Reset Button (Link to reset flow)

**2. New Components:**
*   `frontend/src/components/settings/AvatarGrid.tsx`
*   `frontend/src/components/settings/GradeSelector.tsx`

**3. Integration:**
*   Add `/settings` route in `App.tsx`
*   Add "Settings" link in `DashboardPage` User Menu

---

## 🛠️ Execution Order

### Week 3: Settings & Profile ✅ COMPLETE
- [x] 3.1.1 Add `preferences` column to `Student` model (Backend)
- [x] 3.1.2 Update `StudentUpdate` schema & API endpoint (Backend)
- [x] 3.1.3 Create `SettingsPage.tsx` layout (Frontend)
- [x] 3.1.4 Implement Avatar & Grade Selectors (Frontend)
- [x] 3.1.5 Wire up API integration & State updates (Frontend)
- [x] 3.1.6 Add Navigation and Verify (Frontend)

### Week 3: Smart Review (SRS) ✅ COMPLETE
- [x] 3.3.1 Add `next_review_at` and `review_interval_days` to Progress model
- [x] 3.3.2 Create `ReviewAgent` with LangChain (Agentic Architecture)
- [x] 3.3.3 Create Review API endpoints (`/review/daily`, `/review/complete`)
- [x] 3.3.4 Create `SmartReviewCard.tsx` component (Frontend)
