"""
AI Tutor Platform - CBSE Curriculum Seeder (Grades 1-7)
Complete Mathematics and Science curriculum aligned with NCERT/CBSE
"""
import asyncio
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import settings
# Import all models to ensure relationships are registered
from app.models.curriculum import Subject, Topic, Subtopic, DifficultyLevel
from app.models import user, lesson, assessment  # noqa: F401 - needed for relationship registration


def slugify(text: str) -> str:
    """Convert text to slug format."""
    return text.lower().replace(" ", "-").replace("&", "and").replace("(", "").replace(")", "").replace(",", "").replace("'", "")


# =============================================================================
# MATHEMATICS CURRICULUM - GRADES 1-7 (CBSE/NCERT Aligned)
# =============================================================================
MATH_TOPICS = {
    # GRADE 1
    "numbers-1-to-9": {"name": "Numbers 1-9", "grade": 1, "desc": "Learn numbers from 1 to 9",
        "objectives": ["Count objects 1-9", "Recognize numerals", "Write numbers"],
        "subtopics": [("Counting 1-5", "easy"), ("Counting 6-9", "easy"), ("Writing Numbers 1-9", "easy"), 
                      ("Comparing Numbers", "medium"), ("Ordering Numbers", "medium")]},
    "numbers-10-to-20": {"name": "Numbers 10-20", "grade": 1, "desc": "Explore numbers from 10 to 20",
        "objectives": ["Count to 20", "Understand place value basics"],
        "subtopics": [("Counting 10-15", "easy"), ("Counting 16-20", "easy"), ("Tens and Ones", "medium"),
                      ("Comparing 10-20", "medium"), ("Number Names", "easy")]},
    "addition-grade1": {"name": "Addition Basics", "grade": 1, "desc": "Learn to add numbers",
        "objectives": ["Add single digits", "Add using objects"],
        "subtopics": [("Adding with Objects", "easy"), ("Adding to 5", "easy"), ("Adding to 10", "medium"),
                      ("Adding to 20", "medium"), ("Word Problems", "hard")]},
    "subtraction-grade1": {"name": "Subtraction Basics", "grade": 1, "desc": "Learn to subtract",
        "objectives": ["Subtract single digits", "Take away concept"],
        "subtopics": [("Taking Away Objects", "easy"), ("Subtract from 5", "easy"), ("Subtract from 10", "medium"),
                      ("Subtract from 20", "medium"), ("Word Problems", "hard")]},
    "shapes-grade1": {"name": "Shapes Around Us", "grade": 1, "desc": "Identify basic shapes",
        "objectives": ["Recognize 2D shapes", "Identify 3D objects"],
        "subtopics": [("Circles", "easy"), ("Squares", "easy"), ("Triangles", "easy"), 
                      ("Rectangles", "easy"), ("3D Shapes Intro", "medium")]},
    "patterns-grade1": {"name": "Patterns", "grade": 1, "desc": "Identify and create patterns",
        "objectives": ["Recognize patterns", "Extend patterns"],
        "subtopics": [("Color Patterns", "easy"), ("Shape Patterns", "easy"), ("Number Patterns", "medium"),
                      ("Creating Patterns", "medium")]},
    "measurement-grade1": {"name": "Measurement Basics", "grade": 1, "desc": "Compare objects",
        "objectives": ["Compare lengths", "Compare weights"],
        "subtopics": [("Long and Short", "easy"), ("Tall and Short", "easy"), ("Heavy and Light", "easy"),
                      ("More and Less", "medium")]},
    
    # GRADE 2
    "numbers-to-100": {"name": "Numbers to 100", "grade": 2, "desc": "Master numbers up to 100",
        "objectives": ["Count to 100", "Understand place value"],
        "subtopics": [("Counting by 1s to 50", "easy"), ("Counting by 1s to 100", "easy"), 
                      ("Skip Counting by 2s", "medium"), ("Skip Counting by 5s", "medium"),
                      ("Skip Counting by 10s", "easy"), ("Place Value", "medium"), ("Comparing Numbers", "medium")]},
    "addition-grade2": {"name": "Addition (2-digit)", "grade": 2, "desc": "Add two-digit numbers",
        "objectives": ["Add without regrouping", "Add with regrouping"],
        "subtopics": [("Adding Tens", "easy"), ("Adding without Carrying", "medium"), 
                      ("Adding with Carrying", "hard"), ("Adding Three Numbers", "hard"), ("Word Problems", "hard")]},
    "subtraction-grade2": {"name": "Subtraction (2-digit)", "grade": 2, "desc": "Subtract two-digit numbers",
        "objectives": ["Subtract without borrowing", "Subtract with borrowing"],
        "subtopics": [("Subtracting Tens", "easy"), ("Without Borrowing", "medium"), 
                      ("With Borrowing", "hard"), ("Word Problems", "hard")]},
    "multiplication-intro": {"name": "Introduction to Multiplication", "grade": 2, "desc": "Learn multiplication basics",
        "objectives": ["Understand repeated addition", "Learn times tables 2,5,10"],
        "subtopics": [("Repeated Addition", "easy"), ("Groups of Objects", "easy"), ("Times Table 2", "medium"),
                      ("Times Table 5", "medium"), ("Times Table 10", "easy"), ("Word Problems", "hard")]},
    "shapes-grade2": {"name": "Shapes and Lines", "grade": 2, "desc": "Explore shapes and lines",
        "objectives": ["Identify 2D and 3D shapes", "Understand lines"],
        "subtopics": [("2D Shape Properties", "easy"), ("3D Shapes", "medium"), ("Straight Lines", "easy"),
                      ("Curved Lines", "easy"), ("Corners and Sides", "medium")]},
    "measurement-grade2": {"name": "Measurement", "grade": 2, "desc": "Measure length, weight, capacity",
        "objectives": ["Use non-standard units", "Introduce standard units"],
        "subtopics": [("Measuring Length", "easy"), ("Comparing Weights", "easy"), ("Capacity", "medium"),
                      ("Using Rulers", "medium"), ("Estimation", "hard")]},
    "time-grade2": {"name": "Time", "grade": 2, "desc": "Learn to tell time",
        "objectives": ["Read clock", "Understand calendar"],
        "subtopics": [("Hours on Clock", "easy"), ("Half Hours", "medium"), ("Days of Week", "easy"),
                      ("Months of Year", "easy"), ("Reading Calendar", "medium")]},
    "money-grade2": {"name": "Money", "grade": 2, "desc": "Learn about money",
        "objectives": ["Identify coins and notes", "Simple transactions"],
        "subtopics": [("Coins Recognition", "easy"), ("Notes Recognition", "easy"), ("Adding Money", "medium"),
                      ("Making Change", "hard"), ("Word Problems", "hard")]},
    
    # GRADE 3
    "numbers-to-1000": {"name": "Numbers to 1000", "grade": 3, "desc": "Work with 3-digit numbers",
        "objectives": ["Read and write 3-digit numbers", "Master place value"],
        "subtopics": [("3-Digit Numbers", "easy"), ("Place Value HTU", "medium"), ("Comparing Numbers", "medium"),
                      ("Ordering Numbers", "medium"), ("Rounding to 10s", "hard"), ("Number Patterns", "medium")]},
    "addition-grade3": {"name": "Addition (3-4 digits)", "grade": 3, "desc": "Add larger numbers",
        "objectives": ["Add 3-4 digit numbers", "Solve word problems"],
        "subtopics": [("Adding 3-digit Numbers", "medium"), ("Adding 4-digit Numbers", "hard"),
                      ("Adding Multiple Numbers", "hard"), ("Estimation", "medium"), ("Word Problems", "hard")]},
    "subtraction-grade3": {"name": "Subtraction (3-4 digits)", "grade": 3, "desc": "Subtract larger numbers",
        "objectives": ["Subtract 3-4 digit numbers", "Check by addition"],
        "subtopics": [("Subtracting 3-digit", "medium"), ("Subtracting 4-digit", "hard"),
                      ("With Multiple Borrowing", "hard"), ("Checking Answers", "medium"), ("Word Problems", "hard")]},
    "multiplication-grade3": {"name": "Multiplication Tables", "grade": 3, "desc": "Master times tables",
        "objectives": ["Learn tables 2-10", "Multiply 2-digit by 1-digit"],
        "subtopics": [("Tables 2,3,4", "easy"), ("Tables 5,6,7", "medium"), ("Tables 8,9,10", "medium"),
                      ("2-digit × 1-digit", "hard"), ("Word Problems", "hard")]},
    "division-grade3": {"name": "Division Basics", "grade": 3, "desc": "Introduction to division",
        "objectives": ["Understand equal sharing", "Divide using tables"],
        "subtopics": [("Equal Sharing", "easy"), ("Division as Grouping", "easy"), ("Dividing by 2,5,10", "medium"),
                      ("Division Facts", "medium"), ("Word Problems", "hard")]},
    "fractions-grade3": {"name": "Fractions Introduction", "grade": 3, "desc": "Learn about fractions",
        "objectives": ["Understand half, quarter, third", "Compare simple fractions"],
        "subtopics": [("Half", "easy"), ("Quarter", "easy"), ("Third", "medium"), 
                      ("Comparing Fractions", "medium"), ("Fractions of Shapes", "medium")]},
    "geometry-grade3": {"name": "Geometry", "grade": 3, "desc": "Shapes and symmetry",
        "objectives": ["Shape properties", "Identify symmetry"],
        "subtopics": [("Shape Properties", "easy"), ("Lines of Symmetry", "medium"), ("Perimeter Intro", "medium"),
                      ("Angles Intro", "medium"), ("Tangrams", "medium")]},
    
    # GRADE 4
    "large-numbers-4": {"name": "Large Numbers", "grade": 4, "desc": "Numbers up to lakhs",
        "objectives": ["Read numbers to lakhs", "Indian number system"],
        "subtopics": [("5-6 Digit Numbers", "easy"), ("Indian Place Value", "medium"), ("Comparing Large Numbers", "medium"),
                      ("Rounding Off", "medium"), ("Roman Numerals Intro", "hard")]},
    "operations-grade4": {"name": "Four Operations", "grade": 4, "desc": "Master all operations",
        "objectives": ["All four operations", "Multi-step problems"],
        "subtopics": [("Multiplication 2×2 digit", "medium"), ("Division with Remainders", "medium"),
                      ("Mixed Operations", "hard"), ("BODMAS Intro", "hard"), ("Word Problems", "hard")]},
    "factors-multiples-4": {"name": "Factors and Multiples", "grade": 4, "desc": "Explore factors and multiples",
        "objectives": ["Find factors", "Identify multiples"],
        "subtopics": [("Understanding Factors", "easy"), ("Finding Multiples", "easy"), ("Common Factors", "medium"),
                      ("Common Multiples", "medium"), ("Prime Numbers Intro", "hard")]},
    "fractions-grade4": {"name": "Fractions", "grade": 4, "desc": "Work with fractions",
        "objectives": ["Equivalent fractions", "Add and subtract fractions"],
        "subtopics": [("Equivalent Fractions", "medium"), ("Comparing Fractions", "medium"), 
                      ("Adding Like Fractions", "medium"), ("Subtracting Like Fractions", "medium"), ("Mixed Numbers", "hard")]},
    "decimals-grade4": {"name": "Decimals Introduction", "grade": 4, "desc": "Learn about decimals",
        "objectives": ["Understand tenths", "Connect to money"],
        "subtopics": [("Tenths", "easy"), ("Hundredths", "medium"), ("Decimals and Money", "easy"),
                      ("Comparing Decimals", "medium"), ("Adding Decimals", "hard")]},
    "geometry-grade4": {"name": "Geometry and Angles", "grade": 4, "desc": "Angles and shapes",
        "objectives": ["Measure angles", "Classify triangles"],
        "subtopics": [("Types of Angles", "easy"), ("Measuring Angles", "medium"), ("Triangles", "medium"),
                      ("Quadrilaterals", "medium"), ("Symmetry", "medium"), ("Tessellations", "hard")]},
    "perimeter-area-4": {"name": "Perimeter and Area", "grade": 4, "desc": "Calculate perimeter and area",
        "objectives": ["Find perimeter", "Calculate area"],
        "subtopics": [("Perimeter of Rectangles", "easy"), ("Perimeter of Squares", "easy"),
                      ("Area of Rectangles", "medium"), ("Area of Squares", "medium"), ("Word Problems", "hard")]},
    
    # GRADE 5
    "large-numbers-5": {"name": "Large Numbers (Crores)", "grade": 5, "desc": "Numbers up to crores",
        "objectives": ["Indian and International systems", "Compare large numbers"],
        "subtopics": [("Indian System to Crores", "medium"), ("International System", "medium"),
                      ("Comparing Systems", "hard"), ("Roman Numerals", "medium"), ("Estimation", "medium")]},
    "operations-grade5": {"name": "Operations and BODMAS", "grade": 5, "desc": "Complex calculations",
        "objectives": ["Apply BODMAS", "Solve multi-step problems"],
        "subtopics": [("BODMAS Rule", "medium"), ("Order of Operations", "medium"), ("Long Division", "hard"),
                      ("Multi-step Problems", "hard"), ("Estimation Strategies", "medium")]},
    "factors-multiples-5": {"name": "HCF and LCM", "grade": 5, "desc": "Find HCF and LCM",
        "objectives": ["Calculate HCF", "Calculate LCM"],
        "subtopics": [("Prime Factorization", "medium"), ("Finding HCF", "medium"), ("Finding LCM", "medium"),
                      ("HCF and LCM Problems", "hard"), ("Divisibility Rules", "medium")]},
    "fractions-grade5": {"name": "Fractions Operations", "grade": 5, "desc": "All fraction operations",
        "objectives": ["All four operations with fractions"],
        "subtopics": [("Unlike Fractions Addition", "medium"), ("Unlike Fractions Subtraction", "medium"),
                      ("Multiplying Fractions", "hard"), ("Dividing Fractions", "hard"), ("Word Problems", "hard")]},
    "decimals-grade5": {"name": "Decimals Operations", "grade": 5, "desc": "Work with decimals",
        "objectives": ["All decimal operations"],
        "subtopics": [("Adding Decimals", "easy"), ("Subtracting Decimals", "easy"), ("Multiplying Decimals", "medium"),
                      ("Dividing Decimals", "hard"), ("Decimals to Fractions", "medium")]},
    "geometry-grade5": {"name": "Lines and Angles", "grade": 5, "desc": "Properties of lines and angles",
        "objectives": ["Types of lines", "Angle relationships"],
        "subtopics": [("Parallel Lines", "easy"), ("Perpendicular Lines", "easy"), ("Angle Pairs", "medium"),
                      ("Triangle Properties", "medium"), ("Quadrilateral Properties", "medium")]},
    "mensuration-grade5": {"name": "Area and Volume", "grade": 5, "desc": "Area of complex shapes, volume",
        "objectives": ["Composite shapes", "Volume of cubes"],
        "subtopics": [("Area of Triangles", "medium"), ("Composite Shapes", "hard"), ("Volume of Cubes", "medium"),
                      ("Volume of Cuboids", "medium"), ("Word Problems", "hard")]},
    
    # GRADE 6
    "number-system-6": {"name": "Number System", "grade": 6, "desc": "Whole numbers and integers",
        "objectives": ["Properties of whole numbers", "Introduction to integers"],
        "subtopics": [("Whole Number Properties", "easy"), ("Number Line", "easy"), ("Negative Numbers", "medium"),
                      ("Integer Operations", "medium"), ("Comparing Integers", "medium")]},
    "fractions-decimals-6": {"name": "Fractions and Decimals", "grade": 6, "desc": "Advanced operations",
        "objectives": ["Complex fraction operations", "Decimal conversions"],
        "subtopics": [("Complex Fractions", "medium"), ("Decimal Operations", "medium"), ("Fraction to Decimal", "medium"),
                      ("Decimal to Fraction", "medium"), ("Word Problems", "hard")]},
    "algebra-intro-6": {"name": "Introduction to Algebra", "grade": 6, "desc": "Variables and expressions",
        "objectives": ["Understand variables", "Form expressions"],
        "subtopics": [("Variables", "easy"), ("Expressions", "medium"), ("Equation Basics", "medium"),
                      ("Solving Simple Equations", "medium"), ("Word Problems", "hard")]},
    "ratio-proportion-6": {"name": "Ratio and Proportion", "grade": 6, "desc": "Compare using ratios",
        "objectives": ["Form ratios", "Solve proportions"],
        "subtopics": [("Understanding Ratios", "easy"), ("Equivalent Ratios", "medium"), ("Proportion", "medium"),
                      ("Unitary Method", "medium"), ("Word Problems", "hard")]},
    "geometry-6": {"name": "Basic Geometry", "grade": 6, "desc": "Points, lines, shapes",
        "objectives": ["Geometric concepts", "Shape properties"],
        "subtopics": [("Points and Lines", "easy"), ("Rays and Segments", "easy"), ("Angles", "medium"),
                      ("Triangles", "medium"), ("Quadrilaterals", "medium"), ("Circles", "medium")]},
    "symmetry-6": {"name": "Symmetry", "grade": 6, "desc": "Understanding symmetry",
        "objectives": ["Identify lines of symmetry"],
        "subtopics": [("Making Symmetric Figures", "easy"), ("Lines of Symmetry", "medium"), ("Reflection and Symmetry", "medium")]},
    "practical-geometry-6": {"name": "Practical Geometry", "grade": 6, "desc": "Constructing shapes",
        "objectives": ["Use compass and ruler"],
        "subtopics": [("Circle Construction", "easy"), ("Line Segment Construction", "medium"), ("Perpendiculars", "hard"),
                      ("Angle Construction", "hard")]},
    "mensuration-6": {"name": "Mensuration", "grade": 6, "desc": "Perimeter and area",
        "objectives": ["Perimeter and area formulas"],
        "subtopics": [("Perimeter Formulas", "easy"), ("Area of Rectangle", "easy"), ("Area of Square", "easy"),
                      ("Area of Parallelogram", "medium"), ("Area of Triangle", "medium")]},
    "data-handling-6": {"name": "Data Handling", "grade": 6, "desc": "Organize and interpret data",
        "objectives": ["Create and read graphs"],
        "subtopics": [("Pictographs", "easy"), ("Bar Graphs", "easy"), ("Reading Data", "medium"),
                      ("Collecting Data", "medium"), ("Mean", "hard")]},
    
    # GRADE 7
    "integers-7": {"name": "Integers", "grade": 7, "desc": "Integer operations and properties",
        "objectives": ["All integer operations", "Properties"],
        "subtopics": [("Adding Integers", "easy"), ("Subtracting Integers", "easy"), ("Multiplying Integers", "medium"),
                      ("Dividing Integers", "medium"), ("Properties", "medium"), ("Word Problems", "hard")]},
    "fractions-decimals-7": {"name": "Fractions and Decimals", "grade": 7, "desc": "Advanced operations",
        "objectives": ["Multiply and divide fractions/decimals"],
        "subtopics": [("Multiplying Fractions", "medium"), ("Dividing Fractions", "medium"), 
                      ("Decimal Multiplication", "medium"), ("Decimal Division", "hard"), ("Word Problems", "hard")]},
    "rational-numbers-7": {"name": "Rational Numbers", "grade": 7, "desc": "Work with rational numbers",
        "objectives": ["Understand rational numbers", "Operations"],
        "subtopics": [("What are Rational Numbers", "easy"), ("Number Line", "medium"), ("Comparing", "medium"),
                      ("Operations", "hard"), ("Word Problems", "hard")]},
    "exponents-7": {"name": "Exponents and Powers", "grade": 7, "desc": "Laws of exponents",
        "objectives": ["Understand exponents", "Apply laws"],
        "subtopics": [("Understanding Powers", "easy"), ("Laws of Exponents", "medium"), ("Multiplying Powers", "medium"),
                      ("Dividing Powers", "medium"), ("Negative Exponents", "hard")]},
    "algebraic-expressions-7": {"name": "Algebraic Expressions", "grade": 7, "desc": "Form and simplify expressions",
        "objectives": ["Form expressions", "Simplify expressions"],
        "subtopics": [("Terms and Factors", "easy"), ("Like and Unlike Terms", "easy"), ("Adding Expressions", "medium"),
                      ("Subtracting Expressions", "medium"), ("Multiplying Expressions", "hard")]},
    "simple-equations-7": {"name": "Simple Equations", "grade": 7, "desc": "Solve linear equations",
        "objectives": ["Solve equations", "Form equations from word problems"],
        "subtopics": [("Balancing Equations", "easy"), ("Solving One-Step", "easy"), ("Solving Two-Step", "medium"),
                      ("Word to Equation", "medium"), ("Complex Equations", "hard")]},
    "comparing-quantities-7": {"name": "Comparing Quantities", "grade": 7, "desc": "Percentage, profit, loss",
        "objectives": ["Calculate percentages", "Profit and loss"],
        "subtopics": [("Percentage Basics", "easy"), ("Percentage of Number", "medium"), ("Profit and Loss", "medium"),
                      ("Simple Interest", "hard"), ("Discount", "medium")]},
    "lines-angles-7": {"name": "Lines and Angles", "grade": 7, "desc": "Parallel lines, transversals",
        "objectives": ["Angle relationships", "Parallel line properties"],
        "subtopics": [("Complementary Angles", "easy"), ("Supplementary Angles", "easy"), ("Vertically Opposite", "medium"),
                      ("Transversal", "medium"), ("Parallel Lines Properties", "hard")]},
    "triangles-7": {"name": "Triangles", "grade": 7, "desc": "Triangle properties and congruence",
        "objectives": ["Triangle properties", "Congruence"],
        "subtopics": [("Angle Sum Property", "easy"), ("Exterior Angle", "medium"), ("Types of Triangles", "easy"),
                      ("Congruence Rules", "hard"), ("Pythagoras Intro", "hard")]},
    "practical-geometry-7": {"name": "Practical Geometry", "grade": 7, "desc": "Constructing triangles",
        "objectives": ["Construct parallel lines", "Construct triangles"],
        "subtopics": [("Parallel Lines", "medium"), ("SSS Construction", "hard"), ("SAS Construction", "hard"),
                      ("ASA Construction", "hard"), ("RHS Construction", "hard")]},
    "mensuration-7": {"name": "Perimeter and Area", "grade": 7, "desc": "All shapes including circles",
        "objectives": ["Area of all shapes", "Circumference"],
        "subtopics": [("Review Formulas", "easy"), ("Area of Parallelogram", "medium"), ("Area of Circle", "medium"),
                      ("Circumference", "medium"), ("Composite Shapes", "hard")]},
    "visualizing-solids-7": {"name": "Visualising Solid Shapes", "grade": 7, "desc": "3D shapes and nets",
        "objectives": ["Identify 3D shapes", "Nets"],
        "subtopics": [("Faces, Edges, Vertices", "easy"), ("Nets of Solids", "medium"), ("Drawing Solids", "medium"),
                      ("Cross Sections", "hard")]},
    "data-handling-7": {"name": "Data Handling", "grade": 7, "desc": "Mean, median, mode, probability",
        "objectives": ["Central tendency", "Basic probability"],
        "subtopics": [("Mean", "easy"), ("Median", "medium"), ("Mode", "easy"), ("Range", "easy"),
                      ("Probability Intro", "medium"), ("Chance and Outcomes", "medium")]},
}


# =============================================================================
# SCIENCE CURRICULUM - GRADES 1-7 (CBSE/NCERT Aligned)
# =============================================================================
SCIENCE_TOPICS = {
    # GRADE 1 (EVS - Science)
    "my-body-1": {"name": "My Body", "grade": 1, "desc": "Learn about body parts",
        "objectives": ["Identify body parts", "Understand senses"],
        "subtopics": [("Body Parts", "easy"), ("Sense Organs", "easy"), ("Taking Care of Body", "easy"),
                      ("Healthy Habits", "easy")]},
    "plants-1": {"name": "Plants Around Us", "grade": 1, "desc": "Introduction to plants",
        "objectives": ["Identify plant parts", "Understand plant needs"],
        "subtopics": [("Parts of a Plant", "easy"), ("What Plants Need", "easy"), ("Trees and Plants", "easy"),
                      ("Taking Care of Plants", "easy")]},
    "animals-1": {"name": "Animals Around Us", "grade": 1, "desc": "Learn about animals",
        "objectives": ["Identify animals", "Animal homes and food"],
        "subtopics": [("Pet Animals", "easy"), ("Farm Animals", "easy"), ("Wild Animals", "easy"),
                      ("Animal Sounds", "easy"), ("Where Animals Live", "easy")]},
    "food-1": {"name": "Food We Eat", "grade": 1, "desc": "Introduction to food",
        "objectives": ["Identify food types", "Healthy eating"],
        "subtopics": [("Fruits", "easy"), ("Vegetables", "easy"), ("Healthy Food", "easy"),
                      ("Food from Plants", "easy"), ("Food from Animals", "easy")]},
    "air-water-1": {"name": "Air and Water", "grade": 1, "desc": "Basics of air and water",
        "objectives": ["Importance of air and water"],
        "subtopics": [("Uses of Water", "easy"), ("Uses of Air", "easy"), ("Saving Water", "easy"),
                      ("Clean Water", "easy")]},
    "weather-1": {"name": "Weather and Seasons", "grade": 1, "desc": "Learn about weather",
        "objectives": ["Identify seasons", "Weather types"],
        "subtopics": [("Sunny Days", "easy"), ("Rainy Days", "easy"), ("Cold Weather", "easy"),
                      ("Hot Weather", "easy"), ("What We Wear", "easy")]},
    
    # GRADE 2 (EVS - Science)
    "plants-2": {"name": "Plant Life", "grade": 2, "desc": "More about plants",
        "objectives": ["Plant growth", "Types of plants"],
        "subtopics": [("How Plants Grow", "easy"), ("Seeds", "easy"), ("Types of Plants", "easy"),
                      ("Plant Uses", "medium"), ("Parts of Flower", "medium")]},
    "animals-2": {"name": "Animal World", "grade": 2, "desc": "Animal characteristics",
        "objectives": ["Animal habitats", "Animal food"],
        "subtopics": [("Animal Habitats", "easy"), ("What Animals Eat", "easy"), ("Animal Babies", "easy"),
                      ("Insects", "medium"), ("Birds", "medium")]},
    "human-body-2": {"name": "Human Body", "grade": 2, "desc": "Our body systems",
        "objectives": ["Major organs", "Staying healthy"],
        "subtopics": [("Internal Organs", "medium"), ("Bones and Muscles", "medium"), ("Keeping Clean", "easy"),
                      ("Exercise", "easy"), ("Rest and Sleep", "easy")]},
    "food-nutrition-2": {"name": "Food and Nutrition", "grade": 2, "desc": "Balanced diet",
        "objectives": ["Food groups", "Balanced diet"],
        "subtopics": [("Food Groups", "easy"), ("Balanced Diet", "medium"), ("Junk Food", "easy"),
                      ("Cooking Food", "easy"), ("Food Hygiene", "easy")]},
    "air-water-2": {"name": "Air and Water", "grade": 2, "desc": "Properties of air and water",
        "objectives": ["Properties", "Uses"],
        "subtopics": [("Air is Everywhere", "easy"), ("Air has Weight", "medium"), ("Water Sources", "easy"),
                      ("Water Cycle Intro", "medium"), ("Pollution", "medium")]},
    
    # GRADE 3 (EVS - Science)
    "plant-life-3": {"name": "Plant Life", "grade": 3, "desc": "Plant processes",
        "objectives": ["How plants make food", "Plant reproduction"],
        "subtopics": [("Leaves and Food Making", "medium"), ("Roots and Stems", "easy"), ("Seed Dispersal", "medium"),
                      ("Plant Reproduction", "medium"), ("Useful Plants", "easy")]},
    "animal-life-3": {"name": "Animal Life", "grade": 3, "desc": "Animal adaptations",
        "objectives": ["Adaptations", "Life cycles"],
        "subtopics": [("Animal Adaptations", "medium"), ("Life Cycle of Butterfly", "medium"), 
                      ("Life Cycle of Frog", "medium"), ("Endangered Animals", "medium"), ("Animal Shelters", "easy")]},
    "human-body-3": {"name": "Human Body Systems", "grade": 3, "desc": "Body systems",
        "objectives": ["Digestive system", "Skeletal system"],
        "subtopics": [("Digestive System", "medium"), ("Skeletal System", "medium"), ("Muscular System", "medium"),
                      ("Respiratory System Intro", "medium"), ("Good Posture", "easy")]},
    "matter-3": {"name": "Matter Around Us", "grade": 3, "desc": "States of matter",
        "objectives": ["Solids, liquids, gases"],
        "subtopics": [("Solids", "easy"), ("Liquids", "easy"), ("Gases", "easy"),
                      ("Changing States", "medium"), ("Properties of Matter", "medium")]},
    "light-sound-3": {"name": "Light and Sound", "grade": 3, "desc": "Basics of light and sound",
        "objectives": ["Sources of light and sound", "Properties"],
        "subtopics": [("Sources of Light", "easy"), ("Shadows", "easy"), ("Sources of Sound", "easy"),
                      ("Loud and Soft Sounds", "easy"), ("Musical Instruments", "easy")]},
    "earth-3": {"name": "Our Earth", "grade": 3, "desc": "Earth and its features",
        "objectives": ["Rocks and soil", "Earth features"],
        "subtopics": [("Rocks", "easy"), ("Soil", "easy"), ("Mountains", "easy"),
                      ("Rivers", "easy"), ("Globe and Maps", "medium")]},
    
    # GRADE 4 (EVS - Science)
    "plants-4": {"name": "Plants: Growth and Adaptation", "grade": 4, "desc": "Advanced plant concepts",
        "objectives": ["Plant adaptations", "Photosynthesis basics"],
        "subtopics": [("Photosynthesis Basics", "medium"), ("Plants in Different Places", "medium"),
                      ("Insectivorous Plants", "hard"), ("Plant Adaptations", "medium"), ("Plant Reproduction", "medium")]},
    "animals-4": {"name": "Animals: Adaptation and Survival", "grade": 4, "desc": "Animal survival strategies",
        "objectives": ["Adaptations", "Migration"],
        "subtopics": [("Desert Animals", "medium"), ("Aquatic Animals", "medium"), ("Migration", "medium"),
                      ("Hibernation", "medium"), ("Camouflage", "medium")]},
    "human-body-4": {"name": "Human Body: Digestion", "grade": 4, "desc": "Digestive system in detail",
        "objectives": ["Digestion process", "Teeth and care"],
        "subtopics": [("Types of Teeth", "easy"), ("Digestion Process", "medium"), ("Digestive Organs", "medium"),
                      ("Healthy Eating", "easy"), ("Common Diseases", "medium")]},
    "matter-4": {"name": "Matter and Materials", "grade": 4, "desc": "Properties of materials",
        "objectives": ["Material properties", "Changes in materials"],
        "subtopics": [("Properties of Solids", "easy"), ("Properties of Liquids", "easy"), ("Melting and Freezing", "medium"),
                      ("Evaporation", "medium"), ("Condensation", "medium")]},
    "force-energy-4": {"name": "Force and Energy", "grade": 4, "desc": "Types of forces and energy",
        "objectives": ["Forces", "Simple machines"],
        "subtopics": [("Push and Pull", "easy"), ("Gravity", "easy"), ("Friction", "medium"),
                      ("Simple Machines", "medium"), ("Energy Sources", "medium")]},
    "environment-4": {"name": "Our Environment", "grade": 4, "desc": "Ecosystems and conservation",
        "objectives": ["Ecosystems", "Conservation"],
        "subtopics": [("Ecosystem Basics", "medium"), ("Food Chain", "medium"), ("Food Web", "hard"),
                      ("Conservation", "medium"), ("Pollution", "medium")]},
    "universe-4": {"name": "Our Universe", "grade": 4, "desc": "Solar system basics",
        "objectives": ["Planets", "Sun and Moon"],
        "subtopics": [("The Sun", "easy"), ("The Moon", "easy"), ("Planets", "medium"),
                      ("Day and Night", "easy"), ("Seasons", "medium")]},
    
    # GRADE 5 (EVS - Science)
    "super-senses-5": {"name": "Super Senses", "grade": 5, "desc": "Animal senses and communication",
        "objectives": ["Animal senses", "Animal communication"],
        "subtopics": [("Animal Hearing", "medium"), ("Animal Sight", "medium"), ("Animal Smell", "medium"),
                      ("Animal Communication", "medium"), ("Human vs Animal Senses", "medium")]},
    "living-things-5": {"name": "How Living Things Survive", "grade": 5, "desc": "Adaptation and survival",
        "objectives": ["Survival strategies", "Interdependence"],
        "subtopics": [("Adaptation in Animals", "medium"), ("Adaptation in Plants", "medium"),
                      ("Migration Patterns", "medium"), ("Interdependence", "medium"), ("Ecosystems", "medium")]},
    "food-and-health-5": {"name": "Food and Health", "grade": 5, "desc": "Digestion and preservation",
        "objectives": ["Digestion", "Food preservation"],
        "subtopics": [("Complete Digestion Process", "medium"), ("Nutrients", "medium"), ("Food Preservation", "medium"),
                      ("Adulteration", "medium"), ("Balanced Diet", "easy")]},
    "water-5": {"name": "Water: A Precious Resource", "grade": 5, "desc": "Water cycle and conservation",
        "objectives": ["Water cycle", "Conservation"],
        "subtopics": [("Water Cycle", "medium"), ("Water Sources", "easy"), ("Water Scarcity", "medium"),
                      ("Water Purification", "medium"), ("Conservation Methods", "medium")]},
    "natural-resources-5": {"name": "Natural Resources", "grade": 5, "desc": "Resources and conservation",
        "objectives": ["Types of resources", "Sustainable use"],
        "subtopics": [("Renewable Resources", "medium"), ("Non-renewable Resources", "medium"),
                      ("Conservation", "medium"), ("Reduce Reuse Recycle", "easy"), ("Sustainable Living", "medium")]},
    "forests-5": {"name": "Forests: Our Lifeline", "grade": 5, "desc": "Forest ecosystems",
        "objectives": ["Forest importance", "Deforestation effects"],
        "subtopics": [("Forest Ecosystem", "medium"), ("Types of Forests", "medium"), ("Forest Products", "easy"),
                      ("Deforestation", "medium"), ("Conservation", "medium")]},
    
    # GRADE 6 (Separate Science Subject)
    "food-sources-6": {"name": "Food: Where It Comes From", "grade": 6, "desc": "Food sources and components",
        "objectives": ["Food sources", "Food components"],
        "subtopics": [("Plant Food Sources", "easy"), ("Animal Food Sources", "easy"), ("Components of Food", "medium"),
                      ("Testing for Nutrients", "medium"), ("Balanced Diet", "medium")]},
    "materials-6": {"name": "Sorting Materials", "grade": 6, "desc": "Properties and separation",
        "objectives": ["Material properties", "Separation methods"],
        "subtopics": [("Material Properties", "easy"), ("Grouping Materials", "easy"), 
                      ("Separation Methods", "medium"), ("Filtration", "medium"), ("Evaporation", "medium")]},
    "living-world-6": {"name": "Living World", "grade": 6, "desc": "Organisms and their surroundings",
        "objectives": ["Habitats", "Body movements"],
        "subtopics": [("Habitats", "easy"), ("Adaptation", "medium"), ("Parts of Plants", "easy"),
                      ("Body Movements", "medium"), ("Types of Joints", "medium")]},
    "motion-measurement-6": {"name": "Motion and Measurement", "grade": 6, "desc": "Length and motion basics",
        "objectives": ["Measurement", "Types of motion"],
        "subtopics": [("Measuring Length", "easy"), ("Standard Units", "easy"), ("Types of Motion", "medium"),
                      ("Circular Motion", "medium"), ("Periodic Motion", "medium")]},
    "light-shadows-6": {"name": "Light, Shadows, Reflections", "grade": 6, "desc": "Light properties",
        "objectives": ["Light sources", "Shadow formation"],
        "subtopics": [("Light Sources", "easy"), ("Transparent Objects", "easy"), ("Shadow Formation", "medium"),
                      ("Mirrors", "medium"), ("Reflection", "medium")]},
    "electricity-magnets-6": {"name": "Electricity and Magnets", "grade": 6, "desc": "Circuits and magnets",
        "objectives": ["Electric circuits", "Magnet properties"],
        "subtopics": [("Electric Cells", "easy"), ("Circuits", "medium"), ("Conductors and Insulators", "medium"),
                      ("Magnets", "easy"), ("Magnetic Materials", "easy"), ("Compass", "medium")]},
    "water-6": {"name": "Water", "grade": 6, "desc": "Water importance and conservation",
        "objectives": ["Water cycle", "Water conservation"],
        "subtopics": [("Water Cycle", "medium"), ("Water Sources", "easy"), ("Rainwater Harvesting", "medium"),
                      ("Water Scarcity", "medium"), ("Conservation", "medium")]},
    "air-6": {"name": "Air Around Us", "grade": 6, "desc": "Air composition and importance",
        "objectives": ["Air composition", "Importance"],
        "subtopics": [("Air Composition", "medium"), ("Oxygen", "easy"), ("Carbon Dioxide", "easy"),
                      ("Air Pollution", "medium"), ("Breathing", "medium")]},
    "waste-6": {"name": "Waste Management", "grade": 6, "desc": "Garbage and recycling",
        "objectives": ["Waste types", "Recycling"],
        "subtopics": [("Types of Waste", "easy"), ("Biodegradable Waste", "medium"), ("Non-biodegradable", "medium"),
                      ("Composting", "medium"), ("Recycling", "medium")]},
    "plants-6": {"name": "Getting to Know Plants", "grade": 6, "desc": "Plant systems and parts",
        "objectives": ["Herbs, shrubs, trees", "Parts of plant"],
        "subtopics": [("Herbs Shrubs Trees", "easy"), ("Stem Functions", "medium"), ("Leaf Structure", "medium"),
                      ("Root Types", "medium"), ("Flower Parts", "hard")]},
    "changes-6": {"name": "Changes Around Us", "grade": 6, "desc": "Reversible and irreversible changes",
        "objectives": ["Identify changes"],
        "subtopics": [("Reversible Changes", "easy"), ("Irreversible Changes", "easy"), ("Expansion and Contraction", "medium"),
                      ("Burning", "medium"), ("Changes in State", "medium")]},
    
    # GRADE 7 (Separate Science Subject)
    "nutrition-plants-7": {"name": "Nutrition in Plants", "grade": 7, "desc": "How plants make food",
        "objectives": ["Photosynthesis", "Other modes of nutrition"],
        "subtopics": [("Photosynthesis", "medium"), ("Factors Affecting Photosynthesis", "hard"),
                      ("Parasitic Plants", "medium"), ("Insectivorous Plants", "hard"), ("Saprophytes", "medium")]},
    "nutrition-animals-7": {"name": "Nutrition in Animals", "grade": 7, "desc": "Animal digestion",
        "objectives": ["Digestion in humans", "Digestion in animals"],
        "subtopics": [("Human Digestive System", "medium"), ("Digestion Process", "medium"),
                      ("Absorption", "medium"), ("Digestion in Ruminants", "hard"), ("Amoeba Nutrition", "hard")]},
    "fibre-fabric-7": {"name": "Fibre to Fabric", "grade": 7, "desc": "Wool and silk production",
        "objectives": ["Animal fibres", "Fabric making"],
        "subtopics": [("Wool Sources", "easy"), ("Wool Processing", "medium"), ("Silk Production", "medium"),
                      ("Sericulture", "hard"), ("Fabric Types", "easy")]},
    "heat-7": {"name": "Heat", "grade": 7, "desc": "Heat transfer and effects",
        "objectives": ["Heat transfer", "Temperature"],
        "subtopics": [("Temperature", "easy"), ("Clinical Thermometer", "easy"), ("Conduction", "medium"),
                      ("Convection", "medium"), ("Radiation", "medium"), ("Conductors and Insulators", "medium")]},
    "acids-bases-7": {"name": "Acids, Bases, and Salts", "grade": 7, "desc": "Chemical properties",
        "objectives": ["Identify acids and bases", "Neutralization"],
        "subtopics": [("Acids", "easy"), ("Bases", "easy"), ("Indicators", "medium"),
                      ("Neutralization", "medium"), ("Salts", "medium"), ("pH Scale Intro", "hard")]},
    "physical-chemical-7": {"name": "Physical and Chemical Changes", "grade": 7, "desc": "Types of changes",
        "objectives": ["Distinguish changes", "Identify examples"],
        "subtopics": [("Physical Changes", "easy"), ("Chemical Changes", "easy"), ("Rusting", "medium"),
                      ("Crystallization", "medium"), ("Chemical Reactions", "hard")]},
    "weather-climate-7": {"name": "Weather and Climate", "grade": 7, "desc": "Weather patterns and adaptation",
        "objectives": ["Weather vs climate", "Animal adaptations"],
        "subtopics": [("Weather Elements", "easy"), ("Measuring Weather", "medium"), ("Climate Zones", "medium"),
                      ("Adaptation to Climate", "medium"), ("Polar Regions", "medium"), ("Tropical Regions", "medium")]},
    "winds-storms-7": {"name": "Winds, Storms, Cyclones", "grade": 7, "desc": "Wind and storm formation",
        "objectives": ["Wind formation", "Cyclone safety"],
        "subtopics": [("Air Pressure", "medium"), ("Wind Formation", "medium"), ("Thunderstorms", "medium"),
                      ("Cyclones", "hard"), ("Safety Measures", "easy")]},
    "soil-7": {"name": "Soil", "grade": 7, "desc": "Soil composition and types",
        "objectives": ["Soil formation", "Soil types"],
        "subtopics": [("Soil Formation", "medium"), ("Soil Profile", "medium"), ("Soil Types", "medium"),
                      ("Soil Erosion", "medium"), ("Soil Conservation", "medium")]},
    "respiration-7": {"name": "Respiration in Organisms", "grade": 7, "desc": "Breathing and cellular respiration",
        "objectives": ["Breathing mechanism", "Cellular respiration"],
        "subtopics": [("Breathing vs Respiration", "medium"), ("Human Respiratory System", "medium"),
                      ("Breathing in Animals", "medium"), ("Breathing in Plants", "hard"), ("Aerobic Respiration", "hard")]},
    "transport-7": {"name": "Transportation in Animals and Plants", "grade": 7, "desc": "Circulatory systems",
        "objectives": ["Blood circulation", "Water transport in plants"],
        "subtopics": [("Human Circulatory System", "medium"), ("Blood Components", "medium"), ("Heart", "medium"),
                      ("Transport in Plants", "medium"), ("Transpiration", "hard")]},
    "reproduction-plants-7": {"name": "Reproduction in Plants", "grade": 7, "desc": "Plant reproduction methods",
        "objectives": ["Types of reproduction", "Seed dispersal"],
        "subtopics": [("Vegetative Propagation", "medium"), ("Sexual Reproduction", "medium"),
                      ("Parts of Flower", "easy"), ("Pollination", "medium"), ("Seed Dispersal", "medium")]},
    "motion-time-7": {"name": "Motion and Time", "grade": 7, "desc": "Speed and time measurement",
        "objectives": ["Speed calculation", "Time measurement"],
        "subtopics": [("Speed", "medium"), ("Speed Calculation", "medium"), ("Distance-Time Graphs", "hard"),
                      ("Oscillation", "medium"), ("Simple Pendulum", "medium")]},
    "electric-current-7": {"name": "Electric Current and Effects", "grade": 7, "desc": "Current electricity",
        "objectives": ["Electric current effects", "Safety"],
        "subtopics": [("Heating Effect", "medium"), ("Magnetic Effect", "medium"), ("Electromagnets", "medium"),
                      ("Electric Bell", "hard"), ("Electrical Safety", "easy")]},
    "light-7": {"name": "Light", "grade": 7, "desc": "Reflection and images",
        "objectives": ["Reflection laws", "Image formation"],
        "subtopics": [("Reflection", "medium"), ("Types of Reflection", "medium"), ("Plane Mirrors", "medium"),
                      ("Concave Mirrors", "hard"), ("Convex Mirrors", "hard"), ("Lens Intro", "hard")]},
    "water-resources-7": {"name": "Water: A Precious Resource", "grade": 7, "desc": "Water conservation",
        "objectives": ["Water management", "Conservation"],
        "subtopics": [("Water Distribution", "easy"), ("Groundwater", "medium"), ("Depletion", "medium"),
                      ("Water Management", "medium"), ("Rainwater Harvesting", "medium")]},
    "forests-lifeline-7": {"name": "Forests: Our Lifeline", "grade": 7, "desc": "Forest ecosystem",
        "objectives": ["Forest ecosystem", "Conservation"],
        "subtopics": [("Forest Ecosystem", "medium"), ("Products from Forests", "easy"), ("Deforestation", "medium"),
                      ("Afforestation", "medium"), ("Forest Conservation", "medium")]},
    "wastewater-7": {"name": "Wastewater Story", "grade": 7, "desc": "Wastewater treatment",
        "objectives": ["Wastewater treatment", "Sanitation"],
        "subtopics": [("Wastewater", "easy"), ("Sewage Treatment", "medium"), ("Treatment Plants", "hard"),
                      ("Sanitation", "easy"), ("Clean Water", "easy")]},
}


# =============================================================================
# ENGLISH CURRICULUM - GRADES 1-7 (CBSE/NCERT Aligned)
# =============================================================================
ENGLISH_TOPICS = {
    # GRADE 1
    "alphabet-grade1": {"name": "The Alphabet", "grade": 1, "desc": "Master the alphabet and sounds",
        "objectives": ["Recognize letters", "Phonics basics"],
        "subtopics": [("Capital Letters", "easy"), ("Small Letters", "easy"), ("Vowels and Consonants", "easy"), 
                      ("Phonics Sounds", "medium"), ("Alphabetical Order", "medium")]},
    "naming-words-grade1": {"name": "Naming Words (Nouns)", "grade": 1, "desc": "Learn about names of things",
        "objectives": ["Identify naming words", "Common and proper nouns"],
        "subtopics": [("Names of People", "easy"), ("Names of Places", "easy"), ("Names of Animals", "easy"), 
                      ("Names of Things", "easy"), ("One and Many", "medium")]},
    "pronouns-grade1": {"name": "Use of He, She, It", "grade": 1, "desc": "Introduction to pronouns",
        "objectives": ["Use simple pronouns correctly"],
        "subtopics": [("He and She", "easy"), ("It for Things", "easy"), ("I, You, We", "medium"),
                      ("They and Them", "medium")]},
    "describing-words-grade1": {"name": "Describing Words (Adjectives)", "grade": 1, "desc": "Words that describe",
        "objectives": ["Identify describing words", "Colors and Numbers"],
        "subtopics": [("Colors", "easy"), ("Sizes (Big/Small)", "easy"), ("Feelings (Happy/Sad)", "medium"),
                      ("Numbers as Adjectives", "medium")]},
    "action-words-grade1": {"name": "Doing Words (Verbs)", "grade": 1, "desc": "Words that show action",
        "objectives": ["Identify actions", "Use 'ing' words"],
        "subtopics": [("Daily Actions", "easy"), ("Animal Movements", "easy"), ("Is, Am, Are", "medium"),
                      ("Adding -ing", "medium")]},
    "sentences-grade1": {"name": "Sentences", "grade": 1, "desc": "Forming simple sentences",
        "objectives": ["Capital letters", "Full stops"],
        "subtopics": [("Starting with Capitals", "easy"), ("Ending with Full Stop", "easy"), ("This and That", "medium"),
                      ("These and Those", "medium")]},
    "prepositions-grade1": {"name": "Position Words", "grade": 1, "desc": "Where things are",
        "objectives": ["Use in, on, under"],
        "subtopics": [("In and On", "easy"), ("Under and Over", "medium"), ("Near and Far", "medium"),
                      ("Up and Down", "easy")]},

    # GRADE 2
    "nouns-grade2": {"name": "Nouns and Pronouns", "grade": 2, "desc": "Deeper dive into naming words",
        "objectives": ["Gender", "Plurals"],
        "subtopics": [("Common vs Proper Nouns", "medium"), ("Male and Female (Gender)", "medium"), 
                      ("Singular and Plural (-es)", "medium"), ("Countable/Uncountable Intro", "hard")]},
    "adjectives-grade2": {"name": "Adjectives", "grade": 2, "desc": "Describing words in detail",
        "objectives": ["Describe objects", "Comparisons"],
        "subtopics": [("Describing Quality", "medium"), ("Opposites", "easy"), ("Comparisons (er/est)", "hard"),
                      ("Demonstrative (This/That)", "medium")]},
    "verbs-grade2": {"name": "Verbs and Tenses", "grade": 2, "desc": "Actions and time",
        "objectives": ["Past and Present", "Has/Have"],
        "subtopics": [("Was and Were", "medium"), ("Has and Have", "medium"), ("Had", "medium"), 
                      ("Go/Goes/Went", "hard"), ("Simple Past", "hard")]},
    "prepositions-grade2": {"name": "Prepositions", "grade": 2, "desc": "Position and place awareness",
        "objectives": ["Correct usage of positions"],
        "subtopics": [("Behind and In Front", "medium"), ("Between", "medium"), ("Above and Below", "medium"),
                      ("Review In/On/Under", "easy")]},
    "conjunctions-grade2": {"name": "Joining Words", "grade": 2, "desc": "Connecting ideas",
        "objectives": ["Use and, but, or"],
        "subtopics": [("Use of And", "easy"), ("Use of But", "medium"), ("Use of Or", "medium"),
                      ("Because (Intro)", "hard")]},
    "writing-grade2": {"name": "Composition", "grade": 2, "desc": "Writing skills",
        "objectives": ["Picture composition", "Short paragraphs"],
        "subtopics": [("Picture Composition", "medium"), ("My Self", "easy"), ("My Family", "easy"),
                      ("My School", "easy"), ("Story Retelling", "hard")]},

    # GRADE 3
    "sentences-grade3": {"name": "The Sentence", "grade": 3, "desc": "Types and parts of sentences",
        "objectives": ["Identify subject/predicate", "Types of sentences"],
        "subtopics": [("Subject and Predicate", "medium"), ("Statements", "easy"), ("Questions", "easy"),
                      ("Commands", "medium"), ("Exclamations", "medium")]},
    "nouns-grade3": {"name": "Nouns: Number and Gender", "grade": 3, "desc": "Advanced noun concepts",
        "objectives": ["Plural rules", "Gender types"],
        "subtopics": [("Irregular Plurals", "hard"), ("Neuter Gender", "medium"), ("Material Nouns", "medium"),
                      ("Collective Nouns", "medium"), ("Possessive Nouns ('s)", "medium")]},
    "articles-grade3": {"name": "Articles", "grade": 3, "desc": "A, An, The",
        "objectives": ["Definite and Indefinite articles"],
        "subtopics": [("Use of A vs An", "easy"), ("Use of The", "medium"), ("Omission of Articles", "hard"),
                      ("Vowel Sounds", "medium")]},
    "adjectives-grade3": {"name": "Adjectives", "grade": 3, "desc": "Degrees of composition",
        "objectives": ["Degrees of comparison", "Types"],
        "subtopics": [("Quality, Quantity, Number", "medium"), ("Positive Degree", "easy"), 
                      ("Comparative Degree", "medium"), ("Superlative Degree", "medium")]},
    "verbs-grade3": {"name": "Verbs", "grade": 3, "desc": "Main and Helping verbs",
        "objectives": ["Identify verbs", "Forms of verbs"],
        "subtopics": [("Helping Verbs", "medium"), ("Main Verbs", "medium"), ("Forms of Verbs (V1, V2, V3)", "hard"),
                      ("Subject-Verb Agreement Intro", "hard")]},
    "comprehension-grade3": {"name": "Reading Comprehension", "grade": 3, "desc": "Understanding texts",
        "objectives": ["Read passages", "Answer questions"],
        "subtopics": [("Unseen Passage 1", "medium"), ("Unseen Passage 2", "medium"), ("Poem Comprehension", "hard"),
                      ("Vocabulary from Context", "hard")]},

    # GRADE 4
    "nouns-grade4": {"name": "Nouns", "grade": 4, "desc": "Kinds of nouns",
        "objectives": ["Concrete vs Abstract", "Countable vs Uncountable"],
        "subtopics": [("Abstract Nouns", "medium"), ("Concrete Nouns", "easy"), ("Countable Nouns", "medium"),
                      ("Uncountable Nouns", "medium"), ("Collective Nouns Review", "easy")]},
    "pronouns-grade4": {"name": "Pronouns", "grade": 4, "desc": "Kinds of pronouns",
        "objectives": ["Personal, Demonstrative, Interrogative"],
        "subtopics": [("Personal Pronouns", "easy"), ("Reflexive Pronouns", "medium"), 
                      ("Demonstrative Pronouns", "medium"), ("Interrogative Pronouns", "medium")]},
    "adverbs-grade4": {"name": "Adverbs", "grade": 4, "desc": "Modifying verbs",
        "objectives": ["Kinds of adverbs", "Formation"],
        "subtopics": [("Adverbs of Manner", "medium"), ("Adverbs of Place", "medium"), ("Adverbs of Time", "medium"),
                      ("Adverbs of Frequency", "hard"), ("Formation (ly)", "easy")]},
    "tenses-grade4": {"name": "Tenses", "grade": 4, "desc": "Simple and Continuous",
        "objectives": ["Present, Past, Future Continuous"],
        "subtopics": [("Simple Present", "easy"), ("Present Continuous", "medium"), ("Simple Past", "medium"),
                      ("Past Continuous", "medium"), ("Future Time", "medium")]},
    "punctuation-grade4": {"name": "Punctuation", "grade": 4, "desc": "Writing correctly",
        "objectives": ["Capitalization", "Marks"],
        "subtopics": [("Capital Letters", "easy"), ("Comma Usage", "medium"), ("Exclamation Mark", "easy"),
                      ("Inverted Commas", "hard")]},
    "writing-grade4": {"name": "Writing Skills", "grade": 4, "desc": "Creative writing",
        "objectives": ["Paragraphs", "Letters"],
        "subtopics": [("Paragraph Writing", "medium"), ("Informal Letters", "medium"), ("Story Writing", "hard"),
                      ("Diary Entry Intro", "medium")]},

    # GRADE 5
    "sentences-grade5": {"name": "The Sentence", "grade": 5, "desc": "Deep dive into structure",
        "objectives": ["Phrase vs Clause", "Types"],
        "subtopics": [("The Phrase", "medium"), ("The Clause (Intro)", "hard"), ("Subject and Predicate", "medium"),
                      ("Negative Sentences", "medium"), ("Interrogative Sentences", "medium")]},
    "nouns-advanced-grade5": {"name": "Nouns: Advanced", "grade": 5, "desc": "Complex noun forms",
        "objectives": ["Gender change", "Foreign plurals"],
        "subtopics": [("Masculine/Feminine Rules", "medium"), ("Compound Nouns", "medium"), 
                      ("Singular/Plural Rules", "hard"), ("Possessive Case", "medium")]},
    "adjectives-grade5": {"name": "Adjectives", "grade": 5, "desc": "Order and position",
        "objectives": ["Order of adjectives", "Formation"],
        "subtopics": [("Adjectives of Quantity", "medium"), ("Adjectives of Number", "medium"), 
                      ("Formation of Adjectives", "hard"), ("Degrees of Comparison", "medium")]},
    "verbs-tenses-grade5": {"name": "Verbs and Perfect Tenses", "grade": 5, "desc": "Perfect tenses",
        "objectives": ["Present/Past Perfect"],
        "subtopics": [("Present Perfect", "hard"), ("Past Perfect", "hard"), ("Future Perfect", "hard"),
                      ("Regular vs Irregular Verbs", "medium")]},
    "grammar-grade5": {"name": "Functional Grammar", "grade": 5, "desc": "Active/Passive and Speech",
        "objectives": ["Intro to Voice and Speech"],
        "subtopics": [("Active and Passive Voice (Simple)", "hard"), ("Direct and Indirect Speech (Simple)", "hard"),
                      ("Prepositions of Motion", "medium"), ("Conjunctions Pairs", "medium")]},
    "vocabulary-grade5": {"name": "Vocabulary", "grade": 5, "desc": "Enriching language",
        "objectives": ["Idioms", "Homonyms"],
        "subtopics": [("Idioms and Phrases", "hard"), ("Homophones", "medium"), ("Homonyms", "medium"),
                      ("One Word Substitution", "medium"), ("Prefix and Suffix", "medium")]},

    # GRADE 6
    "sentences-grade6": {"name": "Sentences: Analysis", "grade": 6, "desc": "Complex structures",
        "objectives": ["Simple, Compound, Complex"],
        "subtopics": [("Simple Sentences", "easy"), ("Compound Sentences", "hard"), ("Complex Sentences (Intro)", "hard"),
                      ("Transformation of Sentences", "hard")]},
    "nouns-pronouns-grade6": {"name": "Nouns and Pronouns", "grade": 6, "desc": "Case and Type",
        "objectives": ["Nominative, Objective, Possessive cases"],
        "subtopics": [("Noun Cases", "hard"), ("Relative Pronouns", "medium"), ("Distributive Pronouns", "medium"),
                      ("Indefinite Pronouns", "medium")]},
    "verbs-grade6": {"name": "Verbs: Finite and Non-Finite", "grade": 6, "desc": "Verb types",
        "objectives": ["Transitive/Intransitive", "Infinitives"],
        "subtopics": [("Transitive Verbs", "medium"), ("Intransitive Verbs", "medium"), ("Infinitives", "hard"),
                      ("Gerunds Intro", "hard"), ("Participles Intro", "hard")]},
    "tenses-grade6": {"name": "Integrated Tenses", "grade": 6, "desc": "All tense forms",
        "objectives": ["Perfect Continuous"],
        "subtopics": [("Present Perfect Continuous", "hard"), ("Past Perfect Continuous", "hard"), 
                      ("Future Perfect Continuous", "hard"), ("Tense Consistency", "hard")]},
    "modals-grade6": {"name": "Modals", "grade": 6, "desc": "Auxiliary verbs",
        "objectives": ["Can, Could, May, Might, etc."],
        "subtopics": [("Can, Could, May, Might", "medium"), ("Shall, Should, Will, Would", "medium"), 
                      ("Must, Ought to", "medium"), ("Permission / Ability", "medium"), ("Obligation", "medium")]},
    "writing-grade6": {"name": "Advanced Writing", "grade": 6, "desc": "Formal compositions",
        "objectives": ["Notice, Message, Diary"],
        "subtopics": [("Notice Writing", "medium"), ("Message Writing", "medium"), ("Diary Entry", "medium"),
                      ("Formal Letters", "hard"), ("Article Writing", "hard")]},

    # GRADE 7
    "sentences-grade7": {"name": "Sentence Synthesis", "grade": 7, "desc": "Combining sentences",
        "objectives": ["Synthesis", "Clauses"],
        "subtopics": [("Noun Clauses", "hard"), ("Adjective Clauses", "hard"), ("Adverb Clauses", "hard"),
                      ("Conditional Sentences (If clause)", "hard"), ("Synthesis of Sentences", "hard")]},
    "voice-grade7": {"name": "Active and Passive Voice", "grade": 7, "desc": "Advanced voice",
        "objectives": ["Voice in all tenses"],
        "subtopics": [("Passive of Continuous Tenses", "hard"), ("Passive of Perfect Tenses", "hard"), 
                      ("Passive of Modals", "hard"), ("Imperative Sentences", "medium")]},
    "speech-grade7": {"name": "Direct and Indirect Speech", "grade": 7, "desc": "Reported speech",
        "objectives": ["Reporting statements, questions, commands"],
        "subtopics": [("Rules for Change of Tense", "hard"), ("Change of Pronouns", "medium"), 
                      ("Reporting Questions", "hard"), ("Reporting Commands", "hard"), ("Reporting Exclamations", "hard")]},
    "determiners-grade7": {"name": "Determiners", "grade": 7, "desc": "Qantifiers and articles",
        "objectives": ["Usage of determiners"],
        "subtopics": [("Articles Review", "easy"), ("Demonstratives", "medium"), ("Possessives", "medium"),
                      ("Quantifiers (Some, any, much, many)", "medium"), ("Distributives (Each, every)", "medium")]},
    "vocabulary-grade7": {"name": "Advanced Vocabulary", "grade": 7, "desc": "Literary language",
        "objectives": ["Figures of speech", "Collocations"],
        "subtopics": [("Similes and Metaphors", "medium"), ("Personification", "medium"), ("Alliteration", "easy"),
                      ("Hyperbole", "medium"), ("Phrasal Verbs", "hard"), ("Collocations", "hard")]},
    "writing-grade7": {"name": "Professional Writing", "grade": 7, "desc": "Formal communication",
        "objectives": ["Email, Reports, Speeches"],
        "subtopics": [("Email Writing", "medium"), ("Report Writing", "hard"), ("Speech Writing", "hard"),
                      ("Debate Writing", "hard"), ("Story Writing with Outlines", "medium")]},
}


async def seed_full_curriculum():
    """Seed database with complete CBSE curriculum for grades 1-7."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # =====================================================================
        # CREATE MATHEMATICS SUBJECT
        # =====================================================================
        result = await session.execute(select(Subject).where(Subject.slug == "mathematics"))
        math_subject = result.scalar_one_or_none()
        
        if not math_subject:
            math_subject = Subject(
                id=uuid4(), name="Mathematics", slug="mathematics",
                description="Build strong math foundations with fun, interactive lessons (Grades 1-7 CBSE)",
                icon="calculator", color="#6366f1", is_active=True, display_order=1
            )
            session.add(math_subject)
            await session.flush()
            print(f"✅ Created subject: Mathematics")
        else:
            print(f"ℹ️ Mathematics already exists")
        
        # Add Math Topics
        topic_order = 1
        for topic_slug, topic_data in MATH_TOPICS.items():
            result = await session.execute(
                select(Topic).where(Topic.slug == topic_slug, Topic.subject_id == math_subject.id)
            )
            if result.scalar_one_or_none():
                continue
                
            topic = Topic(
                id=uuid4(), subject_id=math_subject.id, name=topic_data["name"], slug=topic_slug,
                description=topic_data["desc"], grade_level=topic_data["grade"],
                learning_objectives=topic_data["objectives"], estimated_duration_minutes=30,
                is_active=True, display_order=topic_order
            )
            session.add(topic)
            await session.flush()
            
            for sub_order, (sub_name, sub_diff) in enumerate(topic_data["subtopics"], 1):
                subtopic = Subtopic(
                    id=uuid4(), topic_id=topic.id, name=sub_name, slug=slugify(sub_name),
                    difficulty=DifficultyLevel(sub_diff), is_active=True, display_order=sub_order
                )
                session.add(subtopic)
            
            topic_order += 1
            print(f"  📚 Grade {topic_data['grade']}: {topic_data['name']}")
        
        # =====================================================================
        # CREATE SCIENCE SUBJECT
        # =====================================================================
        result = await session.execute(select(Subject).where(Subject.slug == "science"))
        science_subject = result.scalar_one_or_none()
        
        if not science_subject:
            science_subject = Subject(
                id=uuid4(), name="Science", slug="science",
                description="Explore the wonders of science with hands-on experiments (Grades 1-7 CBSE)",
                icon="flask", color="#10b981", is_active=True, display_order=2
            )
            session.add(science_subject)
            await session.flush()
            print(f"\n✅ Created subject: Science")
        else:
            print(f"\nℹ️ Science already exists")
        
        # Add Science Topics
        topic_order = 1
        for topic_slug, topic_data in SCIENCE_TOPICS.items():
            result = await session.execute(
                select(Topic).where(Topic.slug == topic_slug, Topic.subject_id == science_subject.id)
            )
            if result.scalar_one_or_none():
                continue
                
            topic = Topic(
                id=uuid4(), subject_id=science_subject.id, name=topic_data["name"], slug=topic_slug,
                description=topic_data["desc"], grade_level=topic_data["grade"],
                learning_objectives=topic_data["objectives"], estimated_duration_minutes=30,
                is_active=True, display_order=topic_order
            )
            session.add(topic)
            await session.flush()
            
            for sub_order, (sub_name, sub_diff) in enumerate(topic_data["subtopics"], 1):
                subtopic = Subtopic(
                    id=uuid4(), topic_id=topic.id, name=sub_name, slug=slugify(sub_name),
                    difficulty=DifficultyLevel(sub_diff), is_active=True, display_order=sub_order
                )
                session.add(subtopic)
            
            topic_order += 1
            print(f"  🔬 Grade {topic_data['grade']}: {topic_data['name']}")
        
        # =====================================================================
        # CREATE ENGLISH SUBJECT
        # =====================================================================
        result = await session.execute(select(Subject).where(Subject.slug == "english"))
        english_subject = result.scalar_one_or_none()
        
        if not english_subject:
            english_subject = Subject(
                id=uuid4(), name="English", slug="english",
                description="Master reading, writing, and grammar skills (Grades 1-7 CBSE)",
                icon="book-open", color="#ec4899", is_active=True, display_order=3
            )
            session.add(english_subject)
            await session.flush()
            print(f"\n✅ Created subject: English")
        else:
            print(f"\nℹ️ English already exists")
        
        # Add English Topics
        topic_order = 1
        for topic_slug, topic_data in ENGLISH_TOPICS.items():
            result = await session.execute(
                select(Topic).where(Topic.slug == topic_slug, Topic.subject_id == english_subject.id)
            )
            if result.scalar_one_or_none():
                continue
                
            topic = Topic(
                id=uuid4(), subject_id=english_subject.id, name=topic_data["name"], slug=topic_slug,
                description=topic_data["desc"], grade_level=topic_data["grade"],
                learning_objectives=topic_data["objectives"], estimated_duration_minutes=30,
                is_active=True, display_order=topic_order
            )
            session.add(topic)
            await session.flush()
            
            for sub_order, (sub_name, sub_diff) in enumerate(topic_data["subtopics"], 1):
                subtopic = Subtopic(
                    id=uuid4(), topic_id=topic.id, name=sub_name, slug=slugify(sub_name),
                    difficulty=DifficultyLevel(sub_diff), is_active=True, display_order=sub_order
                )
                session.add(subtopic)
            
            topic_order += 1
            print(f"  📖 Grade {topic_data['grade']}: {topic_data['name']}")

        await session.commit()
        print("\n" + "="*60)
        print("🎉 CBSE Curriculum Seeding Complete!")
        print(f"   📊 Mathematics: {len(MATH_TOPICS)} topics")
        print(f"   🔬 Science: {len(SCIENCE_TOPICS)} topics")
        print(f"   📖 English: {len(ENGLISH_TOPICS)} topics")
        print("="*60)


if __name__ == "__main__":
    asyncio.run(seed_full_curriculum())
