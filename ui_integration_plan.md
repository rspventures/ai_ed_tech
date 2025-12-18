# UI Integration Plan: Adaptive Learning Flow 🚀

## 🎯 Objective
Integrate the new AI Tutor (`/study`) engine into the main user experience. The goal is to shift from a "Toolbox" interface (pick a quiz) to a "Journey" interface (follow the path).

## 👶 Design Philosophy (Grades 1-3)
1.  **"The Hero's Journey":** Learning is an adventure, not a todo list.
2.  **Visual Queues:** Use icons (📚, 🎮, 🏆) instead of complex text to indicate what's next.
3.  **Positive Reinforcement:** Every button click is a step forward.
4.  **Smart Defaults:** Don't ask "What do you want to do?". Show "This is what you should do next!"

---

## 🗺️ Phase 1: Topic Interaction (Subject Page)

Currently, the Subject Page lists topics with separate "Practice" and "Assess" buttons. This is overwhelming and bypasses the AI Tutor logic.

### 🆕 The New Design: "Topic Cards 2.0"
Each Topic Card will become a "Mission Control" for that subject.

1.  **Dynamic Action Button:**
    *   One big, colorful button per topic: **"Start Learning"** or **"Continue"**.
    *   **Action:** Links directly to `/study/:topicSlug`. The AI decides if they see a Lesson, Quiz, or Test.

2.  **Smart Badges (The "Why"):**
    *   Displays a badge showing *current* status:
        *   🔵 **New:** "Ready to Learn" (Needs Lesson)
        *   🟢 **Practicing:** "Sharpen Skills" (Needs Practice)
        *   🟡 **Mastering:** "Prove It!" (Needs Assessment)
        *   🏆 **Mastered:** "Expert!" (Topic Complete)

3.  **Progress Bar:**
    *   A simple visual bar showing "Mastery" (0-100%) directly on the card.

---

## 🏠 Phase 2: Dashboard "Smart Suggestions"

The Dashboard currently lists generic "Recent Assessments". We will upgrade this to a **"Up Next"** personalized feed.

### 🆕 The "Recommended for You" Card
A prominent card at the top of the Dashboard.
*   **Logic:** Finds the most recent active topic or the next unlocked topic.
*   **Visual:** "Hi [Name]! Ready to become a math wizard?"
*   **Content:**
    *   "Topic: Addition"
    *   "Mission: Learn about adding apples!" (Derived from the next AI Lesson title)
    *   **Button:** "Let's Go! 🚀" -> Links to `/study/addition`.

---

## 🧭 Phase 3: Navigation Updates

*   **Sidebar/Menu:**
    *   Rename "Practice" to **"Study"** or **"Learn"**.
    *   The "Assessments" tab remains for "Test History", but taking new assessments should happen through the Study flow.

---

## 🎨 Component Updates (Technical)

### 1. `SubjectPage.tsx`
*   **Remove:** Separate `handlePractice` and `handleAssessment` buttons.
*   **Add:** `LearningPathService` integration to fetch status for *each* topic.
*   **Add:** `TopicCard` component that creates the "Smart Badge" logic.

### 2. `DashboardPage.tsx`
*   **Add:** `RecommendedActionCard` component.
*   **Logic:** Fetch the user's active learning path on mount.

### 3. `TopicCard.tsx` (New Component)
*   Encapsulates the logic of "What does this topic look like for THIS student?" based on API data.

---

## 📝 User Flow Example

1.  **Dashboard:** Max sees "Up Next: Shapes". He clicks "Start".
2.  **Study Page:** Max is taken to the AI Tutor.
3.  **AI Logic:** Max has 0% mastery. AI shows a **Lesson** about "Triangles and Squares".
4.  **Completion:** Max finishes the lesson.
5.  **Subject Page:** Max goes back. The "Shapes" card now says "Practice Mode" (Green).
6.  **Next Day:** Max clicks "Shapes" again. It takes him directly to **Practice Questions**.

This creates a seamless, guided loop without Max ever having to guess "Am I ready for a quiz?".
