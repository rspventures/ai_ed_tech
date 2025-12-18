-- English Curriculum Migration for AI Tutor Platform
-- Topics and Subtopics for Grades 1-7 (CBSE/NCERT Aligned)

-- First, get the English subject ID
DO $$
DECLARE
    english_id UUID;
    topic_id UUID;
BEGIN
    -- Get English subject ID
    SELECT id INTO english_id FROM subjects WHERE slug = 'english';
    
    IF english_id IS NULL THEN
        RAISE NOTICE 'English subject not found. Please ensure subjects are seeded first.';
        RETURN;
    END IF;
    
    RAISE NOTICE 'Found English subject with ID: %', english_id;
    
    -- =====================================================
    -- GRADE 1 TOPICS
    -- =====================================================
    
    -- Topic: Alphabet and Letters
    INSERT INTO topics (id, subject_id, name, slug, description, grade_level, learning_objectives, is_active, display_order)
    VALUES (gen_random_uuid(), english_id, 'Alphabet and Letters', 'alphabet-letters-grade1', 
        'Learn the English alphabet and letter recognition', 1,
        ARRAY['Recognize all 26 letters', 'Identify uppercase and lowercase', 'Write letters correctly'],
        true, 1)
    RETURNING id INTO topic_id;
    
    INSERT INTO subtopics (id, topic_id, name, slug, description, difficulty, is_active, display_order) VALUES
    (gen_random_uuid(), topic_id, 'Letters A-F', 'letters-a-f', 'Learn letters A through F', 'easy', true, 1),
    (gen_random_uuid(), topic_id, 'Letters G-L', 'letters-g-l', 'Learn letters G through L', 'easy', true, 2),
    (gen_random_uuid(), topic_id, 'Letters M-R', 'letters-m-r', 'Learn letters M through R', 'easy', true, 3),
    (gen_random_uuid(), topic_id, 'Letters S-Z', 'letters-s-z', 'Learn letters S through Z', 'easy', true, 4),
    (gen_random_uuid(), topic_id, 'Uppercase vs Lowercase', 'uppercase-lowercase', 'Compare big and small letters', 'medium', true, 5);
    
    -- Topic: Phonics Basics
    INSERT INTO topics (id, subject_id, name, slug, description, grade_level, learning_objectives, is_active, display_order)
    VALUES (gen_random_uuid(), english_id, 'Phonics Basics', 'phonics-basics-grade1', 
        'Learn letter sounds and basic phonics', 1,
        ARRAY['Associate letters with sounds', 'Blend simple sounds', 'Recognize rhyming words'],
        true, 2)
    RETURNING id INTO topic_id;
    
    INSERT INTO subtopics (id, topic_id, name, slug, description, difficulty, is_active, display_order) VALUES
    (gen_random_uuid(), topic_id, 'Consonant Sounds', 'consonant-sounds', 'Learn sounds of consonants', 'easy', true, 1),
    (gen_random_uuid(), topic_id, 'Vowel Sounds', 'vowel-sounds', 'Learn short vowel sounds', 'easy', true, 2),
    (gen_random_uuid(), topic_id, 'Rhyming Words', 'rhyming-words', 'Find words that rhyme', 'medium', true, 3),
    (gen_random_uuid(), topic_id, 'Beginning Sounds', 'beginning-sounds', 'Identify first sounds in words', 'easy', true, 4);
    
    -- Topic: Simple Words
    INSERT INTO topics (id, subject_id, name, slug, description, grade_level, learning_objectives, is_active, display_order)
    VALUES (gen_random_uuid(), english_id, 'Simple Words', 'simple-words-grade1', 
        'Learn to read and write simple words', 1,
        ARRAY['Read CVC words', 'Sight words recognition', 'Spell simple words'],
        true, 3)
    RETURNING id INTO topic_id;
    
    INSERT INTO subtopics (id, topic_id, name, slug, description, difficulty, is_active, display_order) VALUES
    (gen_random_uuid(), topic_id, 'Three Letter Words', 'three-letter-words', 'Read and write 3-letter words', 'easy', true, 1),
    (gen_random_uuid(), topic_id, 'Sight Words Set 1', 'sight-words-1', 'Common words: the, a, is, it', 'easy', true, 2),
    (gen_random_uuid(), topic_id, 'Action Words', 'action-words-1', 'Simple verbs: run, sit, jump', 'medium', true, 3),
    (gen_random_uuid(), topic_id, 'Naming Words', 'naming-words-1', 'Simple nouns: cat, dog, ball', 'medium', true, 4);
    
    -- =====================================================
    -- GRADE 2 TOPICS
    -- =====================================================
    
    -- Topic: Reading Skills
    INSERT INTO topics (id, subject_id, name, slug, description, grade_level, learning_objectives, is_active, display_order)
    VALUES (gen_random_uuid(), english_id, 'Reading Skills', 'reading-skills-grade2', 
        'Develop reading fluency and comprehension', 2,
        ARRAY['Read simple sentences', 'Understand story sequence', 'Answer questions about text'],
        true, 4)
    RETURNING id INTO topic_id;
    
    INSERT INTO subtopics (id, topic_id, name, slug, description, difficulty, is_active, display_order) VALUES
    (gen_random_uuid(), topic_id, 'Reading Sentences', 'reading-sentences', 'Read and understand sentences', 'easy', true, 1),
    (gen_random_uuid(), topic_id, 'Story Comprehension', 'story-comprehension', 'Understand short stories', 'medium', true, 2),
    (gen_random_uuid(), topic_id, 'Picture Reading', 'picture-reading', 'Describe pictures in words', 'easy', true, 3),
    (gen_random_uuid(), topic_id, 'Following Instructions', 'following-instructions', 'Read and follow simple directions', 'medium', true, 4);
    
    -- Topic: Grammar Basics
    INSERT INTO topics (id, subject_id, name, slug, description, grade_level, learning_objectives, is_active, display_order)
    VALUES (gen_random_uuid(), english_id, 'Grammar Basics', 'grammar-basics-grade2', 
        'Introduction to basic grammar concepts', 2,
        ARRAY['Identify nouns and verbs', 'Use singular and plural', 'Form simple sentences'],
        true, 5)
    RETURNING id INTO topic_id;
    
    INSERT INTO subtopics (id, topic_id, name, slug, description, difficulty, is_active, display_order) VALUES
    (gen_random_uuid(), topic_id, 'Nouns', 'nouns-intro', 'Words that name people, places, things', 'easy', true, 1),
    (gen_random_uuid(), topic_id, 'Verbs', 'verbs-intro', 'Words that show action', 'easy', true, 2),
    (gen_random_uuid(), topic_id, 'Singular and Plural', 'singular-plural', 'One and many', 'medium', true, 3),
    (gen_random_uuid(), topic_id, 'Simple Sentences', 'simple-sentences', 'Building complete sentences', 'medium', true, 4),
    (gen_random_uuid(), topic_id, 'Pronouns Intro', 'pronouns-intro', 'He, she, it, they', 'medium', true, 5);
    
    -- Topic: Writing
    INSERT INTO topics (id, subject_id, name, slug, description, grade_level, learning_objectives, is_active, display_order)
    VALUES (gen_random_uuid(), english_id, 'Writing', 'writing-grade2', 
        'Develop basic writing skills', 2,
        ARRAY['Write complete sentences', 'Use capital letters', 'Use punctuation marks'],
        true, 6)
    RETURNING id INTO topic_id;
    
    INSERT INTO subtopics (id, topic_id, name, slug, description, difficulty, is_active, display_order) VALUES
    (gen_random_uuid(), topic_id, 'Capital Letters', 'capital-letters', 'When to use uppercase', 'easy', true, 1),
    (gen_random_uuid(), topic_id, 'Full Stops', 'full-stops', 'Using periods correctly', 'easy', true, 2),
    (gen_random_uuid(), topic_id, 'Question Marks', 'question-marks', 'Punctuating questions', 'medium', true, 3),
    (gen_random_uuid(), topic_id, 'Writing Sentences', 'writing-sentences', 'Compose complete sentences', 'medium', true, 4);
    
    -- =====================================================
    -- GRADE 3 TOPICS
    -- =====================================================
    
    -- Topic: Parts of Speech
    INSERT INTO topics (id, subject_id, name, slug, description, grade_level, learning_objectives, is_active, display_order)
    VALUES (gen_random_uuid(), english_id, 'Parts of Speech', 'parts-of-speech-grade3', 
        'Learn different types of words', 3,
        ARRAY['Identify adjectives', 'Use pronouns correctly', 'Understand articles'],
        true, 7)
    RETURNING id INTO topic_id;
    
    INSERT INTO subtopics (id, topic_id, name, slug, description, difficulty, is_active, display_order) VALUES
    (gen_random_uuid(), topic_id, 'Adjectives', 'adjectives-intro', 'Words that describe nouns', 'easy', true, 1),
    (gen_random_uuid(), topic_id, 'Pronouns', 'pronouns-grade3', 'Using pronouns correctly', 'medium', true, 2),
    (gen_random_uuid(), topic_id, 'Articles', 'articles-a-an-the', 'Using a, an, the correctly', 'medium', true, 3),
    (gen_random_uuid(), topic_id, 'Prepositions', 'prepositions-intro', 'Words that show position', 'medium', true, 4),
    (gen_random_uuid(), topic_id, 'Conjunctions', 'conjunctions-intro', 'Words that join: and, but, or', 'hard', true, 5);
    
    -- Topic: Tenses
    INSERT INTO topics (id, subject_id, name, slug, description, grade_level, learning_objectives, is_active, display_order)
    VALUES (gen_random_uuid(), english_id, 'Tenses', 'tenses-grade3', 
        'Learn about past, present and future', 3,
        ARRAY['Use present tense', 'Use past tense', 'Use future tense'],
        true, 8)
    RETURNING id INTO topic_id;
    
    INSERT INTO subtopics (id, topic_id, name, slug, description, difficulty, is_active, display_order) VALUES
    (gen_random_uuid(), topic_id, 'Present Tense', 'present-tense', 'Actions happening now', 'easy', true, 1),
    (gen_random_uuid(), topic_id, 'Past Tense', 'past-tense', 'Actions that already happened', 'medium', true, 2),
    (gen_random_uuid(), topic_id, 'Future Tense', 'future-tense', 'Actions that will happen', 'medium', true, 3),
    (gen_random_uuid(), topic_id, 'Irregular Verbs', 'irregular-verbs', 'Verbs with special past forms', 'hard', true, 4);
    
    -- Topic: Vocabulary Building
    INSERT INTO topics (id, subject_id, name, slug, description, grade_level, learning_objectives, is_active, display_order)
    VALUES (gen_random_uuid(), english_id, 'Vocabulary Building', 'vocabulary-grade3', 
        'Expand word knowledge', 3,
        ARRAY['Learn synonyms', 'Learn antonyms', 'Use new words correctly'],
        true, 9)
    RETURNING id INTO topic_id;
    
    INSERT INTO subtopics (id, topic_id, name, slug, description, difficulty, is_active, display_order) VALUES
    (gen_random_uuid(), topic_id, 'Synonyms', 'synonyms', 'Words with similar meanings', 'medium', true, 1),
    (gen_random_uuid(), topic_id, 'Antonyms', 'antonyms', 'Words with opposite meanings', 'medium', true, 2),
    (gen_random_uuid(), topic_id, 'Homophones', 'homophones', 'Words that sound the same', 'hard', true, 3),
    (gen_random_uuid(), topic_id, 'Compound Words', 'compound-words', 'Two words joined together', 'medium', true, 4);
    
    -- =====================================================
    -- GRADE 4 TOPICS
    -- =====================================================
    
    -- Topic: Advanced Grammar
    INSERT INTO topics (id, subject_id, name, slug, description, grade_level, learning_objectives, is_active, display_order)
    VALUES (gen_random_uuid(), english_id, 'Advanced Grammar', 'advanced-grammar-grade4', 
        'Master advanced grammar concepts', 4,
        ARRAY['Use adverbs', 'Understand subject-verb agreement', 'Form different sentence types'],
        true, 10)
    RETURNING id INTO topic_id;
    
    INSERT INTO subtopics (id, topic_id, name, slug, description, difficulty, is_active, display_order) VALUES
    (gen_random_uuid(), topic_id, 'Adverbs', 'adverbs', 'Words that describe verbs', 'medium', true, 1),
    (gen_random_uuid(), topic_id, 'Subject-Verb Agreement', 'subject-verb-agreement', 'Matching subjects with verbs', 'medium', true, 2),
    (gen_random_uuid(), topic_id, 'Types of Sentences', 'sentence-types', 'Declarative, interrogative, exclamatory', 'medium', true, 3),
    (gen_random_uuid(), topic_id, 'Direct and Indirect Speech', 'direct-indirect-speech', 'Reporting what someone said', 'hard', true, 4);
    
    -- Topic: Reading Comprehension
    INSERT INTO topics (id, subject_id, name, slug, description, grade_level, learning_objectives, is_active, display_order)
    VALUES (gen_random_uuid(), english_id, 'Reading Comprehension', 'reading-comprehension-grade4', 
        'Develop deeper reading understanding', 4,
        ARRAY['Identify main idea', 'Draw conclusions', 'Make inferences'],
        true, 11)
    RETURNING id INTO topic_id;
    
    INSERT INTO subtopics (id, topic_id, name, slug, description, difficulty, is_active, display_order) VALUES
    (gen_random_uuid(), topic_id, 'Finding Main Idea', 'main-idea', 'What is the text about', 'medium', true, 1),
    (gen_random_uuid(), topic_id, 'Supporting Details', 'supporting-details', 'Facts that support main idea', 'medium', true, 2),
    (gen_random_uuid(), topic_id, 'Making Inferences', 'inferences', 'Reading between the lines', 'hard', true, 3),
    (gen_random_uuid(), topic_id, 'Story Elements', 'story-elements', 'Characters, setting, plot', 'medium', true, 4);
    
    -- Topic: Creative Writing
    INSERT INTO topics (id, subject_id, name, slug, description, grade_level, learning_objectives, is_active, display_order)
    VALUES (gen_random_uuid(), english_id, 'Creative Writing', 'creative-writing-grade4', 
        'Express ideas through creative writing', 4,
        ARRAY['Write paragraphs', 'Use descriptive language', 'Create stories'],
        true, 12)
    RETURNING id INTO topic_id;
    
    INSERT INTO subtopics (id, topic_id, name, slug, description, difficulty, is_active, display_order) VALUES
    (gen_random_uuid(), topic_id, 'Writing Paragraphs', 'writing-paragraphs', 'Organize ideas in paragraphs', 'medium', true, 1),
    (gen_random_uuid(), topic_id, 'Descriptive Writing', 'descriptive-writing', 'Using adjectives and adverbs', 'medium', true, 2),
    (gen_random_uuid(), topic_id, 'Story Writing', 'story-writing', 'Creating short stories', 'hard', true, 3),
    (gen_random_uuid(), topic_id, 'Letter Writing', 'letter-writing', 'Writing informal letters', 'medium', true, 4);
    
    -- =====================================================
    -- GRADE 5 TOPICS
    -- =====================================================
    
    -- Topic: Complex Sentences
    INSERT INTO topics (id, subject_id, name, slug, description, grade_level, learning_objectives, is_active, display_order)
    VALUES (gen_random_uuid(), english_id, 'Complex Sentences', 'complex-sentences-grade5', 
        'Build and analyze complex sentences', 5,
        ARRAY['Identify clauses', 'Use complex conjunctions', 'Combine sentences'],
        true, 13)
    RETURNING id INTO topic_id;
    
    INSERT INTO subtopics (id, topic_id, name, slug, description, difficulty, is_active, display_order) VALUES
    (gen_random_uuid(), topic_id, 'Independent Clauses', 'independent-clauses', 'Complete thoughts that stand alone', 'medium', true, 1),
    (gen_random_uuid(), topic_id, 'Dependent Clauses', 'dependent-clauses', 'Clauses that need support', 'hard', true, 2),
    (gen_random_uuid(), topic_id, 'Combining Sentences', 'combining-sentences', 'Joining sentences effectively', 'medium', true, 3),
    (gen_random_uuid(), topic_id, 'Punctuation in Complex Sentences', 'complex-punctuation', 'Using commas correctly', 'hard', true, 4);
    
    -- Topic: Advanced Vocabulary
    INSERT INTO topics (id, subject_id, name, slug, description, grade_level, learning_objectives, is_active, display_order)
    VALUES (gen_random_uuid(), english_id, 'Advanced Vocabulary', 'advanced-vocabulary-grade5', 
        'Expand vocabulary with prefixes and suffixes', 5,
        ARRAY['Use prefixes', 'Use suffixes', 'Understand word roots'],
        true, 14)
    RETURNING id INTO topic_id;
    
    INSERT INTO subtopics (id, topic_id, name, slug, description, difficulty, is_active, display_order) VALUES
    (gen_random_uuid(), topic_id, 'Common Prefixes', 'prefixes', 'un-, re-, pre-, dis-', 'medium', true, 1),
    (gen_random_uuid(), topic_id, 'Common Suffixes', 'suffixes', '-ful, -less, -tion, -ness', 'medium', true, 2),
    (gen_random_uuid(), topic_id, 'Word Roots', 'word-roots', 'Understanding word origins', 'hard', true, 3),
    (gen_random_uuid(), topic_id, 'Context Clues', 'context-clues', 'Finding word meaning from context', 'medium', true, 4);
    
    -- =====================================================
    -- GRADE 6 TOPICS
    -- =====================================================
    
    -- Topic: Writing Essays
    INSERT INTO topics (id, subject_id, name, slug, description, grade_level, learning_objectives, is_active, display_order)
    VALUES (gen_random_uuid(), english_id, 'Essay Writing', 'essay-writing-grade6', 
        'Learn to write structured essays', 6,
        ARRAY['Write introduction', 'Develop body paragraphs', 'Write conclusion'],
        true, 15)
    RETURNING id INTO topic_id;
    
    INSERT INTO subtopics (id, topic_id, name, slug, description, difficulty, is_active, display_order) VALUES
    (gen_random_uuid(), topic_id, 'Essay Structure', 'essay-structure', 'Introduction, body, conclusion', 'medium', true, 1),
    (gen_random_uuid(), topic_id, 'Topic Sentences', 'topic-sentences', 'Starting paragraphs effectively', 'medium', true, 2),
    (gen_random_uuid(), topic_id, 'Supporting Arguments', 'supporting-arguments', 'Building your case', 'hard', true, 3),
    (gen_random_uuid(), topic_id, 'Conclusions', 'conclusions', 'Ending essays effectively', 'medium', true, 4);
    
    -- Topic: Active and Passive Voice
    INSERT INTO topics (id, subject_id, name, slug, description, grade_level, learning_objectives, is_active, display_order)
    VALUES (gen_random_uuid(), english_id, 'Active and Passive Voice', 'voice-grade6', 
        'Understand and use different voices', 6,
        ARRAY['Identify active voice', 'Identify passive voice', 'Convert between voices'],
        true, 16)
    RETURNING id INTO topic_id;
    
    INSERT INTO subtopics (id, topic_id, name, slug, description, difficulty, is_active, display_order) VALUES
    (gen_random_uuid(), topic_id, 'Active Voice', 'active-voice', 'Subject does the action', 'medium', true, 1),
    (gen_random_uuid(), topic_id, 'Passive Voice', 'passive-voice', 'Subject receives the action', 'medium', true, 2),
    (gen_random_uuid(), topic_id, 'Converting Voice', 'converting-voice', 'Changing active to passive', 'hard', true, 3),
    (gen_random_uuid(), topic_id, 'When to Use Each', 'voice-usage', 'Choosing the right voice', 'hard', true, 4);
    
    -- =====================================================
    -- GRADE 7 TOPICS
    -- =====================================================
    
    -- Topic: Literary Devices
    INSERT INTO topics (id, subject_id, name, slug, description, grade_level, learning_objectives, is_active, display_order)
    VALUES (gen_random_uuid(), english_id, 'Literary Devices', 'literary-devices-grade7', 
        'Understand literary techniques', 7,
        ARRAY['Identify similes and metaphors', 'Recognize personification', 'Understand alliteration'],
        true, 17)
    RETURNING id INTO topic_id;
    
    INSERT INTO subtopics (id, topic_id, name, slug, description, difficulty, is_active, display_order) VALUES
    (gen_random_uuid(), topic_id, 'Similes', 'similes', 'Comparisons using like or as', 'medium', true, 1),
    (gen_random_uuid(), topic_id, 'Metaphors', 'metaphors', 'Direct comparisons', 'medium', true, 2),
    (gen_random_uuid(), topic_id, 'Personification', 'personification', 'Giving human qualities to objects', 'medium', true, 3),
    (gen_random_uuid(), topic_id, 'Alliteration', 'alliteration', 'Repeating initial sounds', 'easy', true, 4),
    (gen_random_uuid(), topic_id, 'Hyperbole', 'hyperbole', 'Extreme exaggeration', 'medium', true, 5);
    
    -- Topic: Formal Writing
    INSERT INTO topics (id, subject_id, name, slug, description, grade_level, learning_objectives, is_active, display_order)
    VALUES (gen_random_uuid(), english_id, 'Formal Writing', 'formal-writing-grade7', 
        'Write formal letters and applications', 7,
        ARRAY['Write formal letters', 'Write applications', 'Use formal language'],
        true, 18)
    RETURNING id INTO topic_id;
    
    INSERT INTO subtopics (id, topic_id, name, slug, description, difficulty, is_active, display_order) VALUES
    (gen_random_uuid(), topic_id, 'Formal Letter Format', 'formal-letter-format', 'Structure of formal letters', 'medium', true, 1),
    (gen_random_uuid(), topic_id, 'Application Writing', 'application-writing', 'Writing applications', 'medium', true, 2),
    (gen_random_uuid(), topic_id, 'Formal vs Informal', 'formal-vs-informal', 'Choosing appropriate language', 'hard', true, 3),
    (gen_random_uuid(), topic_id, 'Email Etiquette', 'email-etiquette', 'Writing professional emails', 'medium', true, 4);
    
    RAISE NOTICE 'English curriculum seeded successfully!';
    
END $$;
