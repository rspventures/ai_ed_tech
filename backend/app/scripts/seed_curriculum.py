"""
AI Tutor Platform - Curriculum Seeder
Seeds the database with Mathematics and English curriculum for grades 1-3
"""
import asyncio
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.config import settings
from app.models.curriculum import Subject, Topic, Subtopic, DifficultyLevel


# Curriculum data for seeding
CURRICULUM_DATA = {
    "mathematics": {
        "name": "Mathematics",
        "description": "Build strong math foundations with fun, interactive lessons",
        "icon": "calculator",
        "color": "#6366f1",
        "topics": {
            "counting": {
                "name": "Counting & Numbers",
                "description": "Learn to count and recognize numbers",
                "grade_level": 1,
                "learning_objectives": ["Count from 1-100", "Recognize number patterns"],
                "subtopics": [
                    {"name": "Counting 1-10", "difficulty": "easy"},
                    {"name": "Counting 11-20", "difficulty": "easy"},
                    {"name": "Counting to 50", "difficulty": "medium"},
                    {"name": "Counting to 100", "difficulty": "medium"},
                    {"name": "Skip Counting by 2s", "difficulty": "medium"},
                    {"name": "Skip Counting by 5s", "difficulty": "medium"},
                    {"name": "Skip Counting by 10s", "difficulty": "easy"},
                ]
            },
            "addition": {
                "name": "Addition",
                "description": "Learn to add numbers together",
                "grade_level": 1,
                "learning_objectives": ["Add single digits", "Add with carrying"],
                "subtopics": [
                    {"name": "Adding Single Digits", "difficulty": "easy"},
                    {"name": "Adding to 10", "difficulty": "easy"},
                    {"name": "Adding to 20", "difficulty": "medium"},
                    {"name": "Adding Two-Digit Numbers", "difficulty": "medium"},
                    {"name": "Adding with Carrying", "difficulty": "hard"},
                    {"name": "Word Problems - Addition", "difficulty": "hard"},
                ]
            },
            "subtraction": {
                "name": "Subtraction",
                "description": "Learn to subtract numbers",
                "grade_level": 1,
                "learning_objectives": ["Subtract single digits", "Subtract with borrowing"],
                "subtopics": [
                    {"name": "Subtracting Single Digits", "difficulty": "easy"},
                    {"name": "Subtracting from 10", "difficulty": "easy"},
                    {"name": "Subtracting from 20", "difficulty": "medium"},
                    {"name": "Subtracting Two-Digit Numbers", "difficulty": "medium"},
                    {"name": "Subtracting with Borrowing", "difficulty": "hard"},
                    {"name": "Word Problems - Subtraction", "difficulty": "hard"},
                ]
            },
            "multiplication": {
                "name": "Multiplication",
                "description": "Learn multiplication tables and concepts",
                "grade_level": 2,
                "learning_objectives": ["Understand multiplication", "Learn times tables"],
                "subtopics": [
                    {"name": "Introduction to Multiplication", "difficulty": "easy"},
                    {"name": "Times Table - 2s", "difficulty": "easy"},
                    {"name": "Times Table - 5s", "difficulty": "easy"},
                    {"name": "Times Table - 10s", "difficulty": "easy"},
                    {"name": "Times Table - 3s", "difficulty": "medium"},
                    {"name": "Times Table - 4s", "difficulty": "medium"},
                    {"name": "Word Problems - Multiplication", "difficulty": "hard"},
                ]
            },
            "shapes": {
                "name": "Shapes & Geometry",
                "description": "Learn about shapes and spatial reasoning",
                "grade_level": 1,
                "learning_objectives": ["Identify shapes", "Understand properties"],
                "subtopics": [
                    {"name": "Circles", "difficulty": "easy"},
                    {"name": "Squares and Rectangles", "difficulty": "easy"},
                    {"name": "Triangles", "difficulty": "easy"},
                    {"name": "3D Shapes", "difficulty": "medium"},
                    {"name": "Symmetry", "difficulty": "medium"},
                    {"name": "Patterns with Shapes", "difficulty": "medium"},
                ]
            },
        }
    },
    "english": {
        "name": "English",
        "description": "Develop reading, writing, and language skills",
        "icon": "book-open",
        "color": "#10b981",
        "topics": {
            "alphabet": {
                "name": "Alphabet & Letters",
                "description": "Learn the alphabet and letter recognition",
                "grade_level": 1,
                "learning_objectives": ["Recognize all letters", "Write letters"],
                "subtopics": [
                    {"name": "Uppercase Letters A-M", "difficulty": "easy"},
                    {"name": "Uppercase Letters N-Z", "difficulty": "easy"},
                    {"name": "Lowercase Letters a-m", "difficulty": "easy"},
                    {"name": "Lowercase Letters n-z", "difficulty": "easy"},
                    {"name": "Letter Matching", "difficulty": "easy"},
                    {"name": "Alphabetical Order", "difficulty": "medium"},
                ]
            },
            "phonics": {
                "name": "Phonics",
                "description": "Learn letter sounds and blending",
                "grade_level": 1,
                "learning_objectives": ["Sound out letters", "Blend sounds"],
                "subtopics": [
                    {"name": "Beginning Sounds", "difficulty": "easy"},
                    {"name": "Ending Sounds", "difficulty": "easy"},
                    {"name": "Short Vowels", "difficulty": "medium"},
                    {"name": "Long Vowels", "difficulty": "medium"},
                    {"name": "Consonant Blends", "difficulty": "medium"},
                    {"name": "Digraphs (sh, ch, th)", "difficulty": "hard"},
                ]
            },
            "reading": {
                "name": "Reading Comprehension",
                "description": "Understand and analyze text",
                "grade_level": 2,
                "learning_objectives": ["Read with fluency", "Understand main ideas"],
                "subtopics": [
                    {"name": "Sight Words", "difficulty": "easy"},
                    {"name": "Simple Sentences", "difficulty": "easy"},
                    {"name": "Short Paragraphs", "difficulty": "medium"},
                    {"name": "Story Elements", "difficulty": "medium"},
                    {"name": "Making Predictions", "difficulty": "hard"},
                    {"name": "Drawing Conclusions", "difficulty": "hard"},
                ]
            },
            "vocabulary": {
                "name": "Vocabulary",
                "description": "Expand word knowledge",
                "grade_level": 2,
                "learning_objectives": ["Learn new words", "Use context clues"],
                "subtopics": [
                    {"name": "Common Nouns", "difficulty": "easy"},
                    {"name": "Action Verbs", "difficulty": "easy"},
                    {"name": "Describing Words", "difficulty": "medium"},
                    {"name": "Opposites (Antonyms)", "difficulty": "medium"},
                    {"name": "Similar Words (Synonyms)", "difficulty": "medium"},
                    {"name": "Compound Words", "difficulty": "hard"},
                ]
            },
            "grammar": {
                "name": "Grammar & Writing",
                "description": "Learn grammar rules and writing",
                "grade_level": 2,
                "learning_objectives": ["Use proper grammar", "Write sentences"],
                "subtopics": [
                    {"name": "Capital Letters", "difficulty": "easy"},
                    {"name": "Periods and Question Marks", "difficulty": "easy"},
                    {"name": "Singular and Plural", "difficulty": "medium"},
                    {"name": "Subject and Verb", "difficulty": "medium"},
                    {"name": "Complete Sentences", "difficulty": "medium"},
                    {"name": "Simple Paragraphs", "difficulty": "hard"},
                ]
            },
        }
    }
}


def slugify(text: str) -> str:
    """Convert text to slug format."""
    return text.lower().replace(" ", "-").replace("&", "and").replace("(", "").replace(")", "").replace(",", "")


async def seed_curriculum():
    """Seed the database with curriculum data."""
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        for subject_order, (subject_slug, subject_data) in enumerate(CURRICULUM_DATA.items(), 1):
            # Check if subject exists
            result = await session.execute(
                select(Subject).where(Subject.slug == subject_slug)
            )
            existing_subject = result.scalar_one_or_none()
            
            if existing_subject:
                print(f"Subject '{subject_data['name']}' already exists, skipping...")
                continue
            
            # Create subject
            subject = Subject(
                id=uuid4(),
                name=subject_data["name"],
                slug=subject_slug,
                description=subject_data["description"],
                icon=subject_data["icon"],
                color=subject_data["color"],
                is_active=True,
                display_order=subject_order,
            )
            session.add(subject)
            await session.flush()
            print(f"Created subject: {subject.name}")
            
            # Create topics
            for topic_order, (topic_slug, topic_data) in enumerate(subject_data["topics"].items(), 1):
                topic = Topic(
                    id=uuid4(),
                    subject_id=subject.id,
                    name=topic_data["name"],
                    slug=topic_slug,
                    description=topic_data["description"],
                    grade_level=topic_data["grade_level"],
                    learning_objectives=topic_data["learning_objectives"],
                    estimated_duration_minutes=30,
                    is_active=True,
                    display_order=topic_order,
                )
                session.add(topic)
                await session.flush()
                print(f"  Created topic: {topic.name}")
                
                # Create subtopics
                for subtopic_order, subtopic_data in enumerate(topic_data["subtopics"], 1):
                    difficulty = DifficultyLevel(subtopic_data["difficulty"])
                    subtopic = Subtopic(
                        id=uuid4(),
                        topic_id=topic.id,
                        name=subtopic_data["name"],
                        slug=slugify(subtopic_data["name"]),
                        difficulty=difficulty,
                        is_active=True,
                        display_order=subtopic_order,
                    )
                    session.add(subtopic)
                    print(f"    Created subtopic: {subtopic.name}")
        
        await session.commit()
        print("\n✅ Curriculum seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed_curriculum())
