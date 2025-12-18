"""
AI Tutor Platform - CBSE Curriculum Subtopic Expansion
Adds comprehensive subtopics to existing curriculum (Grades 1-7)
This script updates existing topics with missing subtopics.
"""
import asyncio
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import settings
# Import all models to ensure relationships are registered
from app.models.curriculum import Subject, Topic, Subtopic, DifficultyLevel
from app.models import user, lesson, assessment  # noqa: F401


def slugify(text: str) -> str:
    """Convert text to slug format."""
    return text.lower().replace(" ", "-").replace("&", "and").replace("(", "").replace(")", "").replace(",", "").replace("'", "").replace(":", "")


# =============================================================================
# COMPREHENSIVE SUBTOPICS - EXPANDED FOR CBSE CURRICULUM
# Key: topic_slug -> list of (subtopic_name, difficulty) tuples
# =============================================================================

EXPANDED_SUBTOPICS = {
    # ==========================================================================
    # MATHEMATICS - GRADE 1
    # ==========================================================================
    "numbers-1-to-9": [
        ("Counting Objects 1-5", "easy"),
        ("Counting Objects 6-9", "easy"),
        ("Writing Numerals 1-9", "easy"),
        ("Number Names One to Nine", "easy"),
        ("Comparing Numbers", "medium"),
        ("Ordering Numbers", "medium"),
        ("Before and After", "easy"),
        ("Between Numbers", "medium"),
    ],
    "numbers-10-to-20": [
        ("Counting 10-15", "easy"),
        ("Counting 16-20", "easy"),
        ("Tens and Ones Concept", "medium"),
        ("Place Value Introduction", "medium"),
        ("Number Names Ten to Twenty", "easy"),
        ("Comparing Numbers 10-20", "medium"),
        ("Ordering Numbers 10-20", "medium"),
    ],
    "addition-grade1": [
        ("Adding Using Objects", "easy"),
        ("Addition Facts to 5", "easy"),
        ("Addition Facts to 10", "medium"),
        ("Addition Facts to 20", "medium"),
        ("Adding Zero", "easy"),
        ("Addition Stories", "medium"),
        ("Word Problems Addition", "hard"),
    ],
    "subtraction-grade1": [
        ("Taking Away Objects", "easy"),
        ("Subtraction Facts to 5", "easy"),
        ("Subtraction Facts to 10", "medium"),
        ("Subtraction Facts to 20", "medium"),
        ("Subtracting Zero", "easy"),
        ("Subtraction Stories", "medium"),
        ("Word Problems Subtraction", "hard"),
    ],
    "shapes-grade1": [
        ("Circles", "easy"),
        ("Squares", "easy"),
        ("Triangles", "easy"),
        ("Rectangles", "easy"),
        ("Ovals", "easy"),
        ("3D Shapes Introduction", "medium"),
        ("Shapes in Daily Life", "easy"),
    ],
    "patterns-grade1": [
        ("Color Patterns", "easy"),
        ("Shape Patterns", "easy"),
        ("Number Patterns", "medium"),
        ("Repeating Patterns", "easy"),
        ("Growing Patterns", "medium"),
        ("Creating Patterns", "medium"),
    ],
    "measurement-grade1": [
        ("Long and Short", "easy"),
        ("Tall and Short", "easy"),
        ("Big and Small", "easy"),
        ("Heavy and Light", "easy"),
        ("More and Less", "medium"),
        ("Full and Empty", "easy"),
    ],

    # ==========================================================================
    # MATHEMATICS - GRADE 2
    # ==========================================================================
    "numbers-to-100": [
        ("Counting by 1s to 50", "easy"),
        ("Counting by 1s to 100", "easy"),
        ("Skip Counting by 2s", "medium"),
        ("Skip Counting by 5s", "medium"),
        ("Skip Counting by 10s", "easy"),
        ("Place Value Tens and Ones", "medium"),
        ("Comparing Numbers to 100", "medium"),
        ("Ordering Numbers to 100", "medium"),
        ("Number Names to 100", "medium"),
        ("Even and Odd Numbers", "medium"),
    ],
    "addition-grade2": [
        ("Adding Tens", "easy"),
        ("Adding without Regrouping", "medium"),
        ("Adding with Regrouping", "hard"),
        ("Adding Three Numbers", "hard"),
        ("Mental Addition Strategies", "medium"),
        ("Addition Word Problems", "hard"),
        ("Checking with Subtraction", "hard"),
    ],
    "subtraction-grade2": [
        ("Subtracting Tens", "easy"),
        ("Subtracting without Borrowing", "medium"),
        ("Subtracting with Borrowing", "hard"),
        ("Mental Subtraction Strategies", "medium"),
        ("Subtraction Word Problems", "hard"),
        ("Checking with Addition", "hard"),
    ],
    "multiplication-intro": [
        ("Repeated Addition", "easy"),
        ("Groups of Objects", "easy"),
        ("Times Table of 2", "medium"),
        ("Times Table of 5", "medium"),
        ("Times Table of 10", "easy"),
        ("Multiplication Arrays", "medium"),
        ("Multiplication Word Problems", "hard"),
    ],
    "shapes-grade2": [
        ("2D Shape Properties", "easy"),
        ("Sides and Corners", "easy"),
        ("3D Shapes Cube Cuboid", "medium"),
        ("3D Shapes Sphere Cylinder Cone", "medium"),
        ("Edges Faces and Vertices", "medium"),
        ("Straight and Curved Lines", "easy"),
        ("Patterns with Shapes", "medium"),
    ],
    "measurement-grade2": [
        ("Measuring Length Non-Standard Units", "easy"),
        ("Measuring Length Standard Units", "medium"),
        ("Using a Ruler", "medium"),
        ("Comparing Weights", "easy"),
        ("Capacity Introduction", "medium"),
        ("Estimation", "hard"),
    ],
    "time-grade2": [
        ("Reading Clock Hours", "easy"),
        ("Reading Clock Half Hours", "medium"),
        ("Reading Clock Quarter Hours", "hard"),
        ("Days of the Week", "easy"),
        ("Months of the Year", "easy"),
        ("Reading a Calendar", "medium"),
        ("Sequences of Events", "medium"),
    ],
    "money-grade2": [
        ("Coins Recognition", "easy"),
        ("Notes Recognition", "easy"),
        ("Adding Money", "medium"),
        ("Subtracting Money", "medium"),
        ("Making Change", "hard"),
        ("Money Word Problems", "hard"),
    ],

    # ==========================================================================
    # MATHEMATICS - GRADE 3
    # ==========================================================================
    "numbers-to-1000": [
        ("Reading 3-Digit Numbers", "easy"),
        ("Writing 3-Digit Numbers", "easy"),
        ("Place Value HTU", "medium"),
        ("Expanded Form", "medium"),
        ("Comparing 3-Digit Numbers", "medium"),
        ("Ordering Numbers to 1000", "medium"),
        ("Rounding to Nearest 10", "hard"),
        ("Rounding to Nearest 100", "hard"),
        ("Number Patterns", "medium"),
    ],
    "addition-grade3": [
        ("Adding 3-Digit Numbers Without Carry", "medium"),
        ("Adding 3-Digit Numbers With Carry", "hard"),
        ("Adding 4-Digit Numbers", "hard"),
        ("Adding Multiple Numbers", "hard"),
        ("Estimation in Addition", "medium"),
        ("Word Problems Multi-Step", "hard"),
    ],
    "subtraction-grade3": [
        ("Subtracting 3-Digit Numbers Without Borrow", "medium"),
        ("Subtracting 3-Digit Numbers With Borrow", "hard"),
        ("Subtracting 4-Digit Numbers", "hard"),
        ("Multiple Borrowing", "hard"),
        ("Checking Answers", "medium"),
        ("Word Problems Multi-Step", "hard"),
    ],
    "multiplication-grade3": [
        ("Times Tables 2 3 4", "easy"),
        ("Times Tables 5 6 7", "medium"),
        ("Times Tables 8 9 10", "medium"),
        ("Properties of Multiplication", "medium"),
        ("Multiplying 2-Digit by 1-Digit", "hard"),
        ("Word Problems Multiplication", "hard"),
    ],
    "division-grade3": [
        ("Equal Sharing", "easy"),
        ("Division as Grouping", "easy"),
        ("Dividing by 2 5 10", "medium"),
        ("Division Facts", "medium"),
        ("Relationship with Multiplication", "medium"),
        ("Word Problems Division", "hard"),
        ("Division with Remainder", "hard"),
    ],
    "fractions-grade3": [
        ("Understanding Half", "easy"),
        ("Understanding Quarter", "easy"),
        ("Understanding Third", "medium"),
        ("Fractions of a Whole", "medium"),
        ("Fractions of Shapes", "medium"),
        ("Comparing Simple Fractions", "medium"),
        ("Equivalent Fractions Introduction", "hard"),
    ],
    "geometry-grade3": [
        ("Shape Properties", "easy"),
        ("Lines of Symmetry", "medium"),
        ("Perimeter Introduction", "medium"),
        ("Calculating Perimeter Simple", "medium"),
        ("Right Angles", "medium"),
        ("Tangrams and Puzzles", "medium"),
    ],

    # ==========================================================================
    # MATHEMATICS - GRADE 4
    # ==========================================================================
    "large-numbers-4": [
        ("Reading 5-6 Digit Numbers", "easy"),
        ("Indian Place Value System", "medium"),
        ("International Place Value", "medium"),
        ("Comparing Large Numbers", "medium"),
        ("Ordering Large Numbers", "medium"),
        ("Rounding Large Numbers", "medium"),
        ("Roman Numerals I to L", "hard"),
        ("Roman Numerals L to C", "hard"),
    ],
    "operations-grade4": [
        ("Multiplication 2-Digit by 2-Digit", "medium"),
        ("Multiplication 3-Digit by 2-Digit", "hard"),
        ("Division with 2-Digit Divisor", "hard"),
        ("Division with Remainders", "medium"),
        ("BODMAS Introduction", "hard"),
        ("Mixed Operations", "hard"),
        ("Word Problems Complex", "hard"),
    ],
    "factors-multiples-4": [
        ("Understanding Factors", "easy"),
        ("Finding All Factors", "medium"),
        ("Understanding Multiples", "easy"),
        ("Common Factors", "medium"),
        ("Common Multiples", "medium"),
        ("Prime Numbers Introduction", "hard"),
        ("Composite Numbers", "hard"),
    ],
    "fractions-grade4": [
        ("Equivalent Fractions", "medium"),
        ("Comparing Unlike Fractions", "medium"),
        ("Adding Like Fractions", "medium"),
        ("Subtracting Like Fractions", "medium"),
        ("Mixed Numbers", "hard"),
        ("Improper Fractions", "hard"),
        ("Fractions Word Problems", "hard"),
    ],
    "decimals-grade4": [
        ("Understanding Tenths", "easy"),
        ("Understanding Hundredths", "medium"),
        ("Reading and Writing Decimals", "medium"),
        ("Decimals and Money", "easy"),
        ("Comparing Decimals", "medium"),
        ("Adding Decimals", "hard"),
        ("Decimals on Number Line", "medium"),
    ],
    "geometry-grade4": [
        ("Types of Angles", "easy"),
        ("Measuring Angles Protractor", "medium"),
        ("Types of Triangles", "medium"),
        ("Types of Quadrilaterals", "medium"),
        ("Symmetry", "medium"),
        ("Tessellations", "hard"),
        ("Nets of 3D Shapes", "hard"),
    ],
    "perimeter-area-4": [
        ("Perimeter of Rectangles", "easy"),
        ("Perimeter of Squares", "easy"),
        ("Perimeter of Irregular Shapes", "medium"),
        ("Area Concept", "medium"),
        ("Area of Rectangles", "medium"),
        ("Area of Squares", "medium"),
        ("Word Problems Perimeter Area", "hard"),
    ],

    # ==========================================================================
    # MATHEMATICS - GRADE 5
    # ==========================================================================
    "large-numbers-5": [
        ("Indian System Lakhs and Crores", "medium"),
        ("International System Millions", "medium"),
        ("Comparing Indian and International", "hard"),
        ("Roman Numerals to 1000", "medium"),
        ("Estimation of Large Numbers", "medium"),
        ("Rounding to Nearest Lakh", "hard"),
    ],
    "operations-grade5": [
        ("BODMAS Rule", "medium"),
        ("Order of Operations", "medium"),
        ("Long Division Large Numbers", "hard"),
        ("Division by 2-Digit Numbers", "hard"),
        ("Multi-Step Word Problems", "hard"),
        ("Estimation Strategies", "medium"),
    ],
    "factors-multiples-5": [
        ("Prime Factorization", "medium"),
        ("Prime Factorization Tree Method", "medium"),
        ("Finding HCF", "medium"),
        ("Finding LCM", "medium"),
        ("HCF LCM Word Problems", "hard"),
        ("Divisibility Rules 2 3 5", "medium"),
        ("Divisibility Rules 4 6 9", "hard"),
    ],
    "fractions-grade5": [
        ("Adding Unlike Fractions", "medium"),
        ("Subtracting Unlike Fractions", "medium"),
        ("Multiplying Fractions", "hard"),
        ("Dividing Fractions", "hard"),
        ("Mixed Operations with Fractions", "hard"),
        ("Fraction Word Problems", "hard"),
    ],
    "decimals-grade5": [
        ("Adding Decimals", "easy"),
        ("Subtracting Decimals", "easy"),
        ("Multiplying Decimals", "medium"),
        ("Multiplying by 10 100 1000", "medium"),
        ("Dividing Decimals", "hard"),
        ("Decimals to Fractions", "medium"),
        ("Fractions to Decimals", "medium"),
    ],
    "geometry-grade5": [
        ("Parallel Lines", "easy"),
        ("Perpendicular Lines", "easy"),
        ("Angle Pairs Complementary", "medium"),
        ("Angle Pairs Supplementary", "medium"),
        ("Triangle Properties", "medium"),
        ("Quadrilateral Properties", "medium"),
        ("Angle Sum of Triangle", "hard"),
    ],
    "mensuration-grade5": [
        ("Area of Triangles", "medium"),
        ("Area of Parallelograms", "medium"),
        ("Composite Shapes Area", "hard"),
        ("Volume of Cubes", "medium"),
        ("Volume of Cuboids", "medium"),
        ("Word Problems Volume", "hard"),
    ],

    # ==========================================================================
    # MATHEMATICS - GRADE 6
    # ==========================================================================
    "number-system-6": [
        ("Whole Number Properties", "easy"),
        ("Number Line", "easy"),
        ("Introduction to Negative Numbers", "medium"),
        ("Integers on Number Line", "medium"),
        ("Adding Integers", "medium"),
        ("Subtracting Integers", "medium"),
        ("Comparing Integers", "medium"),
    ],
    "fractions-decimals-6": [
        ("Complex Fractions", "medium"),
        ("Operations with Decimals", "medium"),
        ("Converting Fractions to Decimals", "medium"),
        ("Converting Decimals to Fractions", "medium"),
        ("Word Problems Mixed", "hard"),
        ("Percentages Introduction", "hard"),
    ],
    "algebra-intro-6": [
        ("Understanding Variables", "easy"),
        ("Forming Expressions", "medium"),
        ("Simplifying Expressions", "medium"),
        ("Equation Basics", "medium"),
        ("Solving Simple Linear Equations", "medium"),
        ("Word Problems to Equations", "hard"),
    ],
    "ratio-proportion-6": [
        ("Understanding Ratios", "easy"),
        ("Simplifying Ratios", "medium"),
        ("Equivalent Ratios", "medium"),
        ("Proportion", "medium"),
        ("Unitary Method", "medium"),
        ("Word Problems Ratio", "hard"),
    ],
    "geometry-6": [
        ("Points Lines Rays", "easy"),
        ("Line Segments", "easy"),
        ("Types of Angles", "medium"),
        ("Triangle Classification", "medium"),
        ("Quadrilateral Classification", "medium"),
        ("Circle Parts", "medium"),
        ("Constructions Basic", "hard"),
    ],
    "mensuration-6": [
        ("Perimeter Formulas", "easy"),
        ("Area of Rectangle", "easy"),
        ("Area of Square", "easy"),
        ("Area of Parallelogram", "medium"),
        ("Area of Triangle", "medium"),
        ("Circumference of Circle", "hard"),
    ],
    "data-handling-6": [
        ("Pictographs", "easy"),
        ("Bar Graphs", "easy"),
        ("Reading and Interpreting Data", "medium"),
        ("Collecting Data", "medium"),
        ("Organizing Data", "medium"),
        ("Mean Introduction", "hard"),
    ],

    # ==========================================================================
    # MATHEMATICS - GRADE 7
    # ==========================================================================
    "integers-7": [
        ("Adding Integers", "easy"),
        ("Subtracting Integers", "easy"),
        ("Multiplying Integers", "medium"),
        ("Dividing Integers", "medium"),
        ("Properties of Integer Operations", "medium"),
        ("Word Problems Integers", "hard"),
        ("Order of Operations with Integers", "hard"),
    ],
    "fractions-decimals-7": [
        ("Multiplying Fractions", "medium"),
        ("Dividing Fractions", "medium"),
        ("Decimal Multiplication", "medium"),
        ("Decimal Division", "hard"),
        ("Mixed Numbers Operations", "hard"),
        ("Word Problems Advanced", "hard"),
    ],
    "rational-numbers-7": [
        ("What are Rational Numbers", "easy"),
        ("Rational Numbers on Number Line", "medium"),
        ("Comparing Rational Numbers", "medium"),
        ("Adding Rational Numbers", "medium"),
        ("Subtracting Rational Numbers", "medium"),
        ("Multiplying Rational Numbers", "hard"),
        ("Word Problems Rational", "hard"),
    ],
    "exponents-7": [
        ("Understanding Powers", "easy"),
        ("Reading and Writing Exponents", "easy"),
        ("Laws of Exponents Multiplication", "medium"),
        ("Laws of Exponents Division", "medium"),
        ("Power of a Power", "medium"),
        ("Negative Exponents", "hard"),
        ("Scientific Notation", "hard"),
    ],
    "algebraic-expressions-7": [
        ("Terms and Factors", "easy"),
        ("Coefficients and Constants", "easy"),
        ("Like and Unlike Terms", "easy"),
        ("Adding Expressions", "medium"),
        ("Subtracting Expressions", "medium"),
        ("Multiplying Expressions", "hard"),
        ("Simplifying Complex Expressions", "hard"),
    ],
    "simple-equations-7": [
        ("Balancing Equations", "easy"),
        ("Solving One-Step Equations", "easy"),
        ("Solving Two-Step Equations", "medium"),
        ("Equations with Variables Both Sides", "hard"),
        ("Word Problems to Equations", "medium"),
        ("Complex Word Problems", "hard"),
    ],
    "comparing-quantities-7": [
        ("Percentage Basics", "easy"),
        ("Finding Percentage of a Number", "medium"),
        ("Percentage Increase Decrease", "medium"),
        ("Profit and Loss", "medium"),
        ("Simple Interest", "hard"),
        ("Discount Calculations", "medium"),
        ("Tax Calculations", "hard"),
    ],
    "lines-angles-7": [
        ("Complementary Angles", "easy"),
        ("Supplementary Angles", "easy"),
        ("Adjacent Angles", "medium"),
        ("Vertically Opposite Angles", "medium"),
        ("Transversal and Parallel Lines", "medium"),
        ("Alternate Angles", "hard"),
        ("Corresponding Angles", "hard"),
    ],
    "triangles-7": [
        ("Angle Sum Property", "easy"),
        ("Exterior Angle Property", "medium"),
        ("Types of Triangles by Sides", "easy"),
        ("Types of Triangles by Angles", "easy"),
        ("Congruence of Triangles", "hard"),
        ("Congruence Rules SSS SAS ASA", "hard"),
        ("Pythagoras Theorem Introduction", "hard"),
    ],
    "mensuration-7": [
        ("Review of Perimeter Formulas", "easy"),
        ("Area of Parallelogram", "medium"),
        ("Area of Rhombus", "medium"),
        ("Area of Circle", "medium"),
        ("Circumference of Circle", "medium"),
        ("Composite Shapes", "hard"),
        ("Word Problems Comprehensive", "hard"),
    ],
    "data-handling-7": [
        ("Mean", "easy"),
        ("Median", "medium"),
        ("Mode", "easy"),
        ("Range", "easy"),
        ("Probability Introduction", "medium"),
        ("Chance and Outcomes", "medium"),
        ("Probability Experiments", "hard"),
    ],

    # ==========================================================================
    # SCIENCE - GRADE 1 (EVS)
    # ==========================================================================
    "my-body-1": [
        ("Head and Face Parts", "easy"),
        ("Hands and Fingers", "easy"),
        ("Legs and Feet", "easy"),
        ("Eyes and Seeing", "easy"),
        ("Ears and Hearing", "easy"),
        ("Nose and Smelling", "easy"),
        ("Tongue and Tasting", "easy"),
        ("Skin and Touching", "easy"),
        ("Keeping Clean", "easy"),
        ("Healthy Habits", "easy"),
    ],
    "plants-1": [
        ("Parts of a Plant", "easy"),
        ("Roots", "easy"),
        ("Stem", "easy"),
        ("Leaves", "easy"),
        ("Flowers", "easy"),
        ("Plants Need Water", "easy"),
        ("Plants Need Sunlight", "easy"),
        ("Caring for Plants", "easy"),
    ],
    "animals-1": [
        ("Pet Animals Dog Cat", "easy"),
        ("Farm Animals Cow Goat", "easy"),
        ("Wild Animals Lion Tiger", "easy"),
        ("Birds Around Us", "easy"),
        ("Animal Sounds", "easy"),
        ("Animal Homes", "easy"),
        ("What Animals Eat", "easy"),
        ("Baby Animals", "easy"),
    ],
    "food-1": [
        ("Fruits We Eat", "easy"),
        ("Vegetables We Eat", "easy"),
        ("Food from Plants", "easy"),
        ("Food from Animals", "easy"),
        ("Healthy Foods", "easy"),
        ("Unhealthy Foods", "easy"),
        ("Breakfast Lunch Dinner", "easy"),
    ],
    "air-water-1": [
        ("Air is Everywhere", "easy"),
        ("Uses of Air", "easy"),
        ("Uses of Water", "easy"),
        ("Drinking Water", "easy"),
        ("Saving Water", "easy"),
        ("Clean and Dirty Water", "easy"),
    ],
    "weather-1": [
        ("Sunny Days", "easy"),
        ("Rainy Days", "easy"),
        ("Cloudy Days", "easy"),
        ("Windy Days", "easy"),
        ("Hot Weather Clothes", "easy"),
        ("Cold Weather Clothes", "easy"),
        ("Rainy Weather Clothes", "easy"),
    ],

    # ==========================================================================
    # SCIENCE - GRADE 2 (EVS)
    # ==========================================================================
    "plants-2": [
        ("How Seeds Grow", "easy"),
        ("Parts of a Seed", "medium"),
        ("Germination", "medium"),
        ("Types of Plants Trees Shrubs Herbs", "easy"),
        ("Parts of a Flower", "medium"),
        ("Plants Give Us Food", "easy"),
        ("Plants Give Us Medicine", "medium"),
        ("Caring for Plants", "easy"),
    ],
    "animals-2": [
        ("Animal Habitats Land", "easy"),
        ("Animal Habitats Water", "easy"),
        ("Herbivores", "easy"),
        ("Carnivores", "easy"),
        ("Omnivores", "medium"),
        ("Insects", "medium"),
        ("Birds Migration", "medium"),
        ("Animal Babies", "easy"),
    ],
    "human-body-2": [
        ("Major Organs Introduction", "medium"),
        ("Bones in Our Body", "medium"),
        ("Muscles", "medium"),
        ("Keeping Our Body Clean", "easy"),
        ("Importance of Exercise", "easy"),
        ("Importance of Rest", "easy"),
        ("Sleep and Health", "easy"),
    ],
    "food-nutrition-2": [
        ("Food Groups", "easy"),
        ("Energy Giving Foods", "medium"),
        ("Body Building Foods", "medium"),
        ("Protective Foods", "medium"),
        ("Balanced Diet", "medium"),
        ("Junk Food Effects", "easy"),
        ("Food Hygiene", "easy"),
    ],
    "air-water-2": [
        ("Air is Everywhere Proof", "easy"),
        ("Air Takes Space", "medium"),
        ("Moving Air Wind", "easy"),
        ("Water Sources", "easy"),
        ("Water Cycle Simple", "medium"),
        ("Water Pollution Introduction", "medium"),
        ("Saving Water Ways", "medium"),
    ],

    # ==========================================================================
    # SCIENCE - GRADE 3 (EVS)
    # ==========================================================================
    "plant-life-3": [
        ("How Plants Make Food", "medium"),
        ("Sunlight and Plants", "medium"),
        ("Role of Leaves", "medium"),
        ("Role of Roots", "easy"),
        ("Role of Stem", "easy"),
        ("Seed Dispersal Methods", "medium"),
        ("Useful Plants Food", "easy"),
        ("Useful Plants Medicine", "medium"),
    ],
    "animal-life-3": [
        ("Animal Homes Nests Burrows", "easy"),
        ("Desert Animal Adaptations", "medium"),
        ("Water Animal Adaptations", "medium"),
        ("Life Cycle of Butterfly", "medium"),
        ("Life Cycle of Frog", "medium"),
        ("Endangered Animals", "medium"),
        ("Protecting Animals", "medium"),
    ],
    "human-body-3": [
        ("Digestive System Introduction", "medium"),
        ("Mouth and Teeth", "easy"),
        ("Stomach and Intestines", "medium"),
        ("Bones and Skeleton", "medium"),
        ("Types of Joints", "medium"),
        ("Muscles and Movement", "medium"),
        ("Breathing Introduction", "medium"),
    ],
    "matter-3": [
        ("What is Matter", "easy"),
        ("Properties of Solids", "easy"),
        ("Properties of Liquids", "easy"),
        ("Properties of Gases", "easy"),
        ("Melting", "medium"),
        ("Freezing", "medium"),
        ("Evaporation", "medium"),
    ],
    "light-sound-3": [
        ("Natural Light Sources", "easy"),
        ("Artificial Light Sources", "easy"),
        ("How We See Things", "medium"),
        ("Shadows", "easy"),
        ("Sources of Sound", "easy"),
        ("Loud and Soft Sounds", "easy"),
        ("High and Low Pitch", "medium"),
        ("Musical Instruments", "easy"),
    ],
    "earth-3": [
        ("Types of Rocks", "easy"),
        ("Uses of Rocks", "easy"),
        ("What is Soil", "easy"),
        ("Types of Soil", "medium"),
        ("Mountains and Hills", "easy"),
        ("Rivers and Lakes", "easy"),
        ("Maps and Globes", "medium"),
    ],

    # ==========================================================================
    # SCIENCE - GRADE 4 (EVS)
    # ==========================================================================
    "plants-4": [
        ("Photosynthesis Process", "medium"),
        ("Chlorophyll and Green Color", "medium"),
        ("Plants in Deserts Cactus", "medium"),
        ("Plants in Water Lotus", "medium"),
        ("Insectivorous Plants Venus Flytrap", "hard"),
        ("Pitcher Plant", "hard"),
        ("How Plants Reproduce", "medium"),
        ("Seed Formation", "medium"),
    ],
    "animals-4": [
        ("Desert Animal Adaptations Camel", "medium"),
        ("Polar Animal Adaptations Penguin", "medium"),
        ("Aquatic Animal Adaptations Fish", "medium"),
        ("Bird Migration", "medium"),
        ("Why Animals Migrate", "medium"),
        ("Hibernation Bear", "medium"),
        ("Camouflage Chameleon", "medium"),
        ("Protective Coloration", "medium"),
    ],
    "human-body-4": [
        ("Types of Teeth Incisors Canines", "easy"),
        ("Molars and Premolars", "easy"),
        ("Tooth Decay and Care", "easy"),
        ("Digestive System Overview", "medium"),
        ("Mouth and Chewing", "easy"),
        ("Food Pipe Oesophagus", "medium"),
        ("Stomach Function", "medium"),
        ("Small and Large Intestine", "medium"),
        ("Absorption of Food", "medium"),
        ("Healthy Eating Habits", "easy"),
        ("Common Digestive Diseases", "medium"),
    ],
    "matter-4": [
        ("Properties of Solids Detailed", "easy"),
        ("Properties of Liquids Detailed", "easy"),
        ("Properties of Gases Detailed", "medium"),
        ("Melting and Boiling", "medium"),
        ("Freezing Point", "medium"),
        ("Evaporation Process", "medium"),
        ("Condensation Process", "medium"),
        ("Water Cycle Complete", "hard"),
    ],
    "force-energy-4": [
        ("What is Force", "easy"),
        ("Push Force", "easy"),
        ("Pull Force", "easy"),
        ("Gravity Introduction", "easy"),
        ("Friction", "medium"),
        ("Useful Friction", "medium"),
        ("Harmful Friction", "medium"),
        ("Simple Machines Lever", "medium"),
        ("Simple Machines Pulley", "medium"),
        ("Forms of Energy", "medium"),
    ],
    "environment-4": [
        ("What is an Ecosystem", "medium"),
        ("Living and Non-living Things", "easy"),
        ("Food Chain", "medium"),
        ("Food Web", "hard"),
        ("Producers Consumers Decomposers", "medium"),
        ("Air Pollution", "medium"),
        ("Water Pollution", "medium"),
        ("Conservation of Environment", "medium"),
    ],
    "universe-4": [
        ("The Sun Star", "easy"),
        ("The Moon Satellite", "easy"),
        ("Phases of Moon", "medium"),
        ("Planets in Solar System", "medium"),
        ("Inner Planets", "medium"),
        ("Outer Planets", "medium"),
        ("Day and Night Rotation", "easy"),
        ("Seasons Revolution", "medium"),
    ],

    # ==========================================================================
    # SCIENCE - GRADE 5 (EVS)
    # ==========================================================================
    "super-senses-5": [
        ("How Animals Hear", "medium"),
        ("Dogs Hearing Ability", "medium"),
        ("How Animals See", "medium"),
        ("Nocturnal Animals Eyes", "medium"),
        ("How Animals Smell", "medium"),
        ("Dogs Sense of Smell", "medium"),
        ("Animal Communication Sounds", "medium"),
        ("Animal Communication Body Language", "medium"),
        ("Comparing Human and Animal Senses", "medium"),
    ],
    "living-things-5": [
        ("Adaptation in Desert Animals", "medium"),
        ("Adaptation in Aquatic Animals", "medium"),
        ("Adaptation in Plants", "medium"),
        ("Migration in Birds", "medium"),
        ("Migration in Fish Salmon", "medium"),
        ("Food Web Interdependence", "medium"),
        ("Ecosystem Balance", "medium"),
    ],
    "food-and-health-5": [
        ("Complete Digestive System", "medium"),
        ("Carbohydrates", "medium"),
        ("Proteins", "medium"),
        ("Fats", "medium"),
        ("Vitamins and Minerals", "medium"),
        ("Food Preservation Methods", "medium"),
        ("Food Adulteration", "medium"),
        ("Effects of Adulteration", "hard"),
        ("Balanced Diet Pyramid", "easy"),
    ],
    "water-5": [
        ("States of Water", "easy"),
        ("Water Cycle Evaporation", "medium"),
        ("Water Cycle Condensation", "medium"),
        ("Water Cycle Precipitation", "medium"),
        ("Sources of Water", "easy"),
        ("Water Scarcity Causes", "medium"),
        ("Water Purification Methods", "medium"),
        ("Conservation of Water", "medium"),
    ],
    "natural-resources-5": [
        ("What are Natural Resources", "easy"),
        ("Renewable Resources", "medium"),
        ("Non-renewable Resources", "medium"),
        ("Fossil Fuels", "medium"),
        ("Solar Energy", "medium"),
        ("Wind Energy", "medium"),
        ("Conservation of Resources", "medium"),
        ("3Rs Reduce Reuse Recycle", "easy"),
    ],
    "forests-5": [
        ("What is a Forest", "easy"),
        ("Types of Forests Tropical", "medium"),
        ("Types of Forests Temperate", "medium"),
        ("Forest Ecosystem", "medium"),
        ("Products from Forests", "easy"),
        ("Deforestation Causes", "medium"),
        ("Effects of Deforestation", "medium"),
        ("Forest Conservation", "medium"),
    ],

    # ==========================================================================
    # SCIENCE - GRADE 6
    # ==========================================================================
    "food-sources-6": [
        ("Food from Plants Parts", "easy"),
        ("Food from Animals", "easy"),
        ("Carbohydrates Sources", "medium"),
        ("Protein Sources", "medium"),
        ("Fats and Oils", "medium"),
        ("Testing for Starch", "medium"),
        ("Testing for Protein", "medium"),
        ("Balanced Diet", "medium"),
        ("Diseases from Poor Nutrition", "hard"),
    ],
    "materials-6": [
        ("Properties of Materials", "easy"),
        ("Appearance of Materials", "easy"),
        ("Hardness of Materials", "easy"),
        ("Solubility", "medium"),
        ("Transparency", "easy"),
        ("Grouping Materials by Properties", "easy"),
        ("Separation by Handpicking", "easy"),
        ("Separation by Sieving", "medium"),
        ("Separation by Filtration", "medium"),
        ("Separation by Evaporation", "medium"),
    ],
    "living-world-6": [
        ("What is Habitat", "easy"),
        ("Terrestrial Habitats", "easy"),
        ("Aquatic Habitats", "easy"),
        ("Adaptation to Habitat", "medium"),
        ("Parts of Plants Detailed", "easy"),
        ("Flower Parts", "medium"),
        ("Human Body Movements", "medium"),
        ("Types of Joints Ball Socket", "medium"),
        ("Types of Joints Hinge", "medium"),
        ("Types of Joints Pivot", "medium"),
    ],
    "motion-measurement-6": [
        ("What is Measurement", "easy"),
        ("Standard Units of Length", "easy"),
        ("Using Ruler and Tape", "easy"),
        ("Curved Line Measurement", "medium"),
        ("What is Motion", "medium"),
        ("Types of Motion Rectilinear", "medium"),
        ("Types of Motion Circular", "medium"),
        ("Types of Motion Rotational", "medium"),
        ("Periodic Motion", "medium"),
    ],
    "light-shadows-6": [
        ("Luminous Objects", "easy"),
        ("Non-luminous Objects", "easy"),
        ("Transparent Materials", "easy"),
        ("Opaque Materials", "easy"),
        ("Translucent Materials", "easy"),
        ("How Shadows Form", "medium"),
        ("Umbra and Penumbra", "hard"),
        ("Mirrors Plane", "medium"),
        ("Image in Plane Mirror", "medium"),
    ],
    "electricity-magnets-6": [
        ("Electric Cell", "easy"),
        ("Parts of Electric Cell", "easy"),
        ("Electric Circuit Simple", "medium"),
        ("Open and Closed Circuits", "medium"),
        ("Conductors of Electricity", "medium"),
        ("Insulators of Electricity", "medium"),
        ("Natural Magnets", "easy"),
        ("Artificial Magnets", "easy"),
        ("Magnetic and Non-magnetic", "easy"),
        ("Poles of Magnet", "medium"),
        ("Compass and Direction", "medium"),
    ],
    "water-6": [
        ("Water Cycle Stages", "medium"),
        ("Evaporation in Water Cycle", "medium"),
        ("Condensation Clouds", "medium"),
        ("Precipitation Rain", "medium"),
        ("Sources of Water", "easy"),
        ("Groundwater", "medium"),
        ("Rainwater Harvesting", "medium"),
        ("Water Scarcity", "medium"),
        ("Water Conservation Methods", "medium"),
    ],
    "air-6": [
        ("Composition of Air", "medium"),
        ("Nitrogen in Air", "easy"),
        ("Oxygen in Air", "easy"),
        ("Carbon Dioxide in Air", "easy"),
        ("Water Vapour in Air", "medium"),
        ("Dust and Smoke in Air", "easy"),
        ("Air Pollution Causes", "medium"),
        ("Effects of Air Pollution", "medium"),
        ("How We Breathe", "medium"),
    ],
    "waste-6": [
        ("What is Waste", "easy"),
        ("Biodegradable Waste", "medium"),
        ("Non-biodegradable Waste", "medium"),
        ("Vermicomposting", "medium"),
        ("Composting Process", "medium"),
        ("Recycling Paper", "medium"),
        ("Recycling Plastic", "medium"),
        ("Reducing Waste", "easy"),
        ("Proper Waste Disposal", "medium"),
    ],

    # ==========================================================================
    # SCIENCE - GRADE 7
    # ==========================================================================
    "nutrition-plants-7": [
        ("Autotrophic Nutrition", "medium"),
        ("Photosynthesis Process Detailed", "medium"),
        ("Raw Materials for Photosynthesis", "medium"),
        ("Products of Photosynthesis", "medium"),
        ("Factors Affecting Photosynthesis", "hard"),
        ("Stomata and Gas Exchange", "hard"),
        ("Heterotrophic Nutrition in Plants", "medium"),
        ("Parasitic Plants Cuscuta", "medium"),
        ("Insectivorous Plants Detailed", "hard"),
        ("Saprophytic Plants", "medium"),
        ("Symbiotic Relationship Lichens", "hard"),
    ],
    "nutrition-animals-7": [
        ("Types of Nutrition", "medium"),
        ("Human Digestive System", "medium"),
        ("Mouth Teeth Tongue", "easy"),
        ("Salivary Glands", "medium"),
        ("Oesophagus", "medium"),
        ("Stomach", "medium"),
        ("Small Intestine Digestion", "medium"),
        ("Absorption in Small Intestine", "medium"),
        ("Large Intestine", "medium"),
        ("Digestion in Grass-eating Animals", "hard"),
        ("Digestion in Amoeba", "hard"),
    ],
    "fibre-fabric-7": [
        ("Types of Fibres Natural", "easy"),
        ("Types of Fibres Synthetic", "easy"),
        ("Wool from Sheep", "easy"),
        ("Wool Processing Steps", "medium"),
        ("Silk from Silkworm", "medium"),
        ("Life Cycle of Silkworm", "medium"),
        ("Sericulture", "hard"),
        ("Sorting and Grading Wool", "medium"),
        ("Diseases from Wool Processing", "medium"),
    ],
    "heat-7": [
        ("Hot and Cold Objects", "easy"),
        ("Temperature Measurement", "easy"),
        ("Laboratory Thermometer", "easy"),
        ("Clinical Thermometer", "easy"),
        ("Heat Transfer", "medium"),
        ("Conduction", "medium"),
        ("Convection", "medium"),
        ("Radiation", "medium"),
        ("Conductors of Heat", "medium"),
        ("Insulators of Heat", "medium"),
        ("Woolen Clothes in Winter", "medium"),
    ],
    "acids-bases-7": [
        ("What are Acids", "easy"),
        ("Examples of Acids", "easy"),
        ("What are Bases", "easy"),
        ("Examples of Bases", "easy"),
        ("Natural Indicators", "medium"),
        ("Litmus Paper Test", "medium"),
        ("Turmeric as Indicator", "medium"),
        ("Neutralization Reaction", "medium"),
        ("Salts Formation", "medium"),
        ("pH Scale Introduction", "hard"),
        ("Everyday Neutralization", "medium"),
    ],
    "physical-chemical-7": [
        ("What are Physical Changes", "easy"),
        ("Examples of Physical Changes", "easy"),
        ("What are Chemical Changes", "easy"),
        ("Examples of Chemical Changes", "easy"),
        ("Differences Physical vs Chemical", "medium"),
        ("Rusting of Iron", "medium"),
        ("Conditions for Rusting", "medium"),
        ("Prevention of Rusting", "medium"),
        ("Crystallization", "medium"),
        ("Chemical Reactions Types", "hard"),
    ],
    "weather-climate-7": [
        ("Weather Elements", "easy"),
        ("Temperature", "easy"),
        ("Humidity", "medium"),
        ("Rainfall", "medium"),
        ("Wind", "easy"),
        ("Measuring Weather", "medium"),
        ("Weather vs Climate", "medium"),
        ("Climate Zones", "medium"),
        ("Polar Region Adaptations", "medium"),
        ("Tropical Region Adaptations", "medium"),
        ("Temperate Region Features", "medium"),
    ],
    "winds-storms-7": [
        ("What is Air Pressure", "medium"),
        ("High and Low Pressure", "medium"),
        ("How Winds Form", "medium"),
        ("Uneven Heating of Earth", "hard"),
        ("Thunderstorms", "medium"),
        ("How Thunderstorms Form", "medium"),
        ("Cyclones", "hard"),
        ("Structure of Cyclone", "hard"),
        ("Cyclone Safety Measures", "easy"),
        ("Tornado", "hard"),
    ],
    "soil-7": [
        ("Soil Formation Process", "medium"),
        ("Weathering of Rocks", "medium"),
        ("Soil Profile Layers", "medium"),
        ("Types of Soil Sandy", "medium"),
        ("Types of Soil Clayey", "medium"),
        ("Types of Soil Loamy", "medium"),
        ("Soil Properties", "medium"),
        ("Soil and Crops", "medium"),
        ("Soil Erosion Causes", "medium"),
        ("Soil Conservation Methods", "medium"),
    ],
    "respiration-7": [
        ("Difference Breathing and Respiration", "medium"),
        ("Human Respiratory System", "medium"),
        ("Nose and Nostrils", "easy"),
        ("Trachea", "medium"),
        ("Lungs", "medium"),
        ("Diaphragm", "medium"),
        ("Inhalation and Exhalation", "medium"),
        ("Breathing in Fish Gills", "medium"),
        ("Breathing in Earthworm", "medium"),
        ("Breathing in Plants Stomata", "hard"),
        ("Aerobic Respiration", "hard"),
        ("Anaerobic Respiration", "hard"),
    ],
    "transport-7": [
        ("Circulatory System", "medium"),
        ("Blood Components", "medium"),
        ("Red Blood Cells", "medium"),
        ("White Blood Cells", "medium"),
        ("Platelets", "medium"),
        ("Blood Plasma", "medium"),
        ("Heart Structure", "medium"),
        ("Blood Vessels Arteries", "medium"),
        ("Blood Vessels Veins", "medium"),
        ("Blood Vessels Capillaries", "medium"),
        ("Transport in Plants Xylem", "medium"),
        ("Transport in Plants Phloem", "hard"),
        ("Transpiration", "hard"),
    ],
    "reproduction-plants-7": [
        ("Modes of Reproduction", "easy"),
        ("Vegetative Propagation", "medium"),
        ("Vegetative Propagation Stem", "medium"),
        ("Vegetative Propagation Root", "medium"),
        ("Vegetative Propagation Leaf", "medium"),
        ("Sexual Reproduction in Plants", "medium"),
        ("Parts of Flower Detailed", "easy"),
        ("Pollination Types", "medium"),
        ("Self Pollination", "medium"),
        ("Cross Pollination", "medium"),
        ("Fertilization in Plants", "hard"),
        ("Seed Dispersal Methods", "medium"),
    ],
    "motion-time-7": [
        ("What is Speed", "medium"),
        ("Calculating Speed", "medium"),
        ("Units of Speed", "easy"),
        ("Average Speed", "medium"),
        ("Distance Time Graphs", "hard"),
        ("What is Oscillation", "medium"),
        ("Simple Pendulum", "medium"),
        ("Time Period", "medium"),
        ("Frequency", "hard"),
    ],
    "electric-current-7": [
        ("Review of Electric Circuit", "easy"),
        ("Heating Effect of Current", "medium"),
        ("Electric Fuse", "medium"),
        ("Electric Bulb Working", "medium"),
        ("Magnetic Effect of Current", "medium"),
        ("Electromagnet", "medium"),
        ("Making an Electromagnet", "medium"),
        ("Uses of Electromagnet", "medium"),
        ("Electric Bell Working", "hard"),
        ("Electrical Safety Rules", "easy"),
    ],
    "light-7": [
        ("Rectilinear Propagation", "medium"),
        ("Reflection of Light", "medium"),
        ("Laws of Reflection", "medium"),
        ("Regular Reflection", "medium"),
        ("Diffused Reflection", "medium"),
        ("Plane Mirror Images", "medium"),
        ("Concave Mirror", "hard"),
        ("Convex Mirror", "hard"),
        ("Uses of Concave Mirrors", "hard"),
        ("Uses of Convex Mirrors", "hard"),
        ("Lens Introduction Convex Concave", "hard"),
    ],
    "water-resources-7": [
        ("Distribution of Water on Earth", "easy"),
        ("Freshwater Sources", "easy"),
        ("Groundwater", "medium"),
        ("Water Table", "medium"),
        ("Depletion of Water Table", "medium"),
        ("Effect of Water Scarcity", "medium"),
        ("Water Management", "medium"),
        ("Rainwater Harvesting Methods", "medium"),
        ("Drip Irrigation", "medium"),
    ],
    "forests-lifeline-7": [
        ("Forest Ecosystem", "medium"),
        ("Canopy", "easy"),
        ("Understory", "easy"),
        ("Forest Floor", "easy"),
        ("Producers in Forest", "medium"),
        ("Consumers in Forest", "medium"),
        ("Decomposers in Forest", "medium"),
        ("Products from Forests", "easy"),
        ("Deforestation Causes", "medium"),
        ("Effects of Deforestation", "medium"),
        ("Afforestation", "medium"),
        ("Forest Conservation", "medium"),
    ],
    "wastewater-7": [
        ("What is Wastewater", "easy"),
        ("Types of Wastewater", "easy"),
        ("Sewage", "easy"),
        ("Sewerage System", "medium"),
        ("Wastewater Treatment Steps", "medium"),
        ("Primary Treatment", "medium"),
        ("Secondary Treatment", "hard"),
        ("Sludge Treatment", "hard"),
        ("Clean Water Release", "medium"),
        ("Importance of Sanitation", "easy"),
        ("Personal Hygiene", "easy"),
    ],
}


async def expand_subtopics():
    """Add expanded subtopics to existing curriculum topics."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    added_count = 0
    skipped_count = 0
    
    async with async_session() as session:
        for topic_slug, subtopics_data in EXPANDED_SUBTOPICS.items():
            # Find the topic
            result = await session.execute(
                select(Topic).where(Topic.slug == topic_slug)
            )
            topic = result.scalar_one_or_none()
            
            if not topic:
                print(f"⚠️ Topic not found: {topic_slug}")
                continue
            
            # Get existing subtopics for this topic
            result = await session.execute(
                select(Subtopic).where(Subtopic.topic_id == topic.id)
            )
            existing_subtopics = {st.slug for st in result.scalars().all()}
            
            # Get max display order
            result = await session.execute(
                select(Subtopic.display_order)
                .where(Subtopic.topic_id == topic.id)
                .order_by(Subtopic.display_order.desc())
                .limit(1)
            )
            max_order = result.scalar() or 0
            
            # Add new subtopics
            new_count = 0
            for sub_order, (sub_name, sub_diff) in enumerate(subtopics_data, 1):
                sub_slug = slugify(sub_name)
                
                if sub_slug in existing_subtopics:
                    skipped_count += 1
                    continue
                
                subtopic = Subtopic(
                    id=uuid4(),
                    topic_id=topic.id,
                    name=sub_name,
                    slug=sub_slug,
                    difficulty=DifficultyLevel(sub_diff),
                    is_active=True,
                    display_order=max_order + sub_order
                )
                session.add(subtopic)
                new_count += 1
                added_count += 1
            
            if new_count > 0:
                print(f"  ✅ {topic.name}: +{new_count} subtopics")
            else:
                print(f"  ℹ️ {topic.name}: already complete")
        
        await session.commit()
        
    print("\n" + "="*60)
    print("🎉 Subtopic Expansion Complete!")
    print(f"   ✅ Added: {added_count} new subtopics")
    print(f"   ⏭️ Skipped: {skipped_count} existing subtopics")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(expand_subtopics())
