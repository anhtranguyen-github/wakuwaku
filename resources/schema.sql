-- Hanachan Hanachan WaniKani API Database Schema (Standalone)

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    username TEXT,
    email TEXT,
    level INTEGER DEFAULT 1,
    max_level_granted INTEGER DEFAULT 60,
    subscription_type TEXT DEFAULT 'free',
    subscription_ends_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Subjects table (radicals, kanji, vocabulary)
CREATE TABLE IF NOT EXISTS subjects (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    type TEXT NOT NULL, -- radical, kanji, vocabulary, kana_vocabulary
    slug TEXT NOT NULL,
    level INTEGER NOT NULL,
    meaning_mnemonic TEXT,
    reading_mnemonic TEXT,
    meaning_hint TEXT,
    reading_hint TEXT,
    characters TEXT,
    meanings JSONB DEFAULT '[]',
    readings JSONB DEFAULT '[]',
    auxiliary_meanings JSONB DEFAULT '[]',
    component_subject_ids INTEGER[] DEFAULT '{}',
    amalgamation_subject_ids INTEGER[] DEFAULT '{}',
    visually_similar_subject_ids INTEGER[] DEFAULT '{}',
    context_sentences JSONB DEFAULT '[]',
    pronunciation_audios JSONB DEFAULT '[]',
    character_images JSONB DEFAULT '[]',
    parts_of_speech TEXT[] DEFAULT '{}',
    document_url TEXT,
    spaced_repetition_system_id INTEGER DEFAULT 1,
    lesson_position INTEGER DEFAULT 0,
    hidden_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Assignments table
CREATE TABLE IF NOT EXISTS assignments (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    subject_id INTEGER REFERENCES subjects(id) ON DELETE CASCADE,
    subject_type TEXT NOT NULL,
    level INTEGER NOT NULL,
    srs_stage INTEGER DEFAULT 0,
    unlocked_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    passed_at TIMESTAMPTZ,
    burned_at TIMESTAMPTZ,
    available_at TIMESTAMPTZ,
    resurrected_at TIMESTAMPTZ,
    hidden BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Reviews table
CREATE TABLE IF NOT EXISTS reviews (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    assignment_id INTEGER REFERENCES assignments(id) ON DELETE CASCADE,
    subject_id INTEGER REFERENCES subjects(id) ON DELETE CASCADE,
    spaced_repetition_system_id INTEGER NOT NULL,
    starting_srs_stage INTEGER NOT NULL,
    ending_srs_stage INTEGER NOT NULL,
    incorrect_meaning_answers INTEGER DEFAULT 0,
    incorrect_reading_answers INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Review Statistics table
CREATE TABLE IF NOT EXISTS review_statistics (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    subject_id INTEGER REFERENCES subjects(id) ON DELETE CASCADE,
    subject_type TEXT NOT NULL,
    meaning_correct INTEGER DEFAULT 0,
    meaning_incorrect INTEGER DEFAULT 0,
    meaning_current_streak INTEGER DEFAULT 0,
    meaning_max_streak INTEGER DEFAULT 0,
    reading_correct INTEGER DEFAULT 0,
    reading_incorrect INTEGER DEFAULT 0,
    reading_current_streak INTEGER DEFAULT 0,
    reading_max_streak INTEGER DEFAULT 0,
    percentage_correct FLOAT DEFAULT 0,
    hidden BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Study Materials table
CREATE TABLE IF NOT EXISTS study_materials (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    subject_id INTEGER REFERENCES subjects(id) ON DELETE CASCADE,
    subject_type TEXT NOT NULL,
    meaning_note TEXT,
    reading_note TEXT,
    meaning_synonyms TEXT[] DEFAULT '{}',
    hidden BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Level Progressions table
CREATE TABLE IF NOT EXISTS level_progressions (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    level INTEGER NOT NULL,
    unlocked_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    passed_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    abandoned_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Resets table
CREATE TABLE IF NOT EXISTS resets (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    original_level INTEGER NOT NULL,
    target_level INTEGER NOT NULL,
    confirmed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Spaced Repetition Systems table
CREATE TABLE IF NOT EXISTS spaced_repetition_systems (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    unlocking_stage_position INTEGER DEFAULT 0,
    starting_stage_position INTEGER DEFAULT 1,
    passing_stage_position INTEGER DEFAULT 5,
    burning_stage_position INTEGER DEFAULT 9,
    stages JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default SRS
INSERT INTO spaced_repetition_systems (id, name, description, unlocking_stage_position, starting_stage_position, passing_stage_position, burning_stage_position, stages) VALUES
(1, 'Hanachan WaniKani SRS', 'Default Hanachan WaniKani Spaced Repetition System', 0, 1, 5, 9, '[
  {"position": 0, "interval": null, "interval_unit": null},
  {"position": 1, "interval": 0, "interval_unit": "seconds"},
  {"position": 2, "interval": 14400, "interval_unit": "seconds"},
  {"position": 3, "interval": 86400, "interval_unit": "seconds"},
  {"position": 4, "interval": 259200, "interval_unit": "seconds"},
  {"position": 5, "interval": 604800, "interval_unit": "seconds"},
  {"position": 6, "interval": 1209600, "interval_unit": "seconds"},
  {"position": 7, "interval": 2592000, "interval_unit": "seconds"},
  {"position": 8, "interval": 7776000, "interval_unit": "seconds"},
  {"position": 9, "interval": null, "interval_unit": null}
]')
ON CONFLICT (id) DO NOTHING;

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_assignments_user_id ON assignments(user_id);
CREATE INDEX IF NOT EXISTS idx_assignments_subject_id ON assignments(subject_id);
CREATE INDEX IF NOT EXISTS idx_reviews_user_id ON reviews(user_id);
CREATE INDEX IF NOT EXISTS idx_reviews_assignment_id ON reviews(assignment_id);
CREATE INDEX IF NOT EXISTS idx_review_statistics_user_id ON review_statistics(user_id);
CREATE INDEX IF NOT EXISTS idx_review_statistics_subject_id ON review_statistics(subject_id);
CREATE INDEX IF NOT EXISTS idx_study_materials_user_id ON study_materials(user_id);
CREATE INDEX IF NOT EXISTS idx_study_materials_subject_id ON study_materials(subject_id);
CREATE INDEX IF NOT EXISTS idx_level_progressions_user_id ON level_progressions(user_id);
CREATE INDEX IF NOT EXISTS idx_resets_user_id ON resets(user_id);
CREATE INDEX IF NOT EXISTS idx_subjects_user_id ON subjects(user_id);
CREATE INDEX IF NOT EXISTS idx_subjects_type ON subjects(type);
CREATE INDEX IF NOT EXISTS idx_subjects_level ON subjects(level);

-- Create test user
INSERT INTO users (id, username, email, level, max_level_granted, subscription_type) 
VALUES ('550e8400-e29b-41d4-a716-446655440000', 'testuser', 'test@example.com', 1, 60, 'free');

-- Create sample subjects (radical, kanji, vocabulary)
INSERT INTO subjects (id, user_id, type, slug, level, meaning_mnemonic, reading_mnemonic, characters, meanings, readings) VALUES
(1, '550e8400-e29b-41d4-a716-446655440000', 'radical', 'water', 1, 'Water is like the symbol for water', NULL, '水', '[{"meaning": "water", "primary": true, "accepted_answer": true}]', '[]'),
(2, '550e8400-e29b-41d4-a716-446655440000', 'kanji', 'water', 1, 'Water meaning', 'みず, すい', '水', '[{"meaning": "water", "primary": true, "accepted_answer": true}]', '[{"reading": "みず", "primary": true, "accepted_answer": true}, {"reading": "すい", "primary": false, "accepted_answer": true}]'),
(3, '550e8400-e29b-41d4-a716-446655440000', 'vocabulary', 'water', 1, 'Water meaning', 'みず', '水', '[{"meaning": "water", "primary": true, "accepted_answer": true}]', '[{"reading": "みず", "primary": true, "accepted_answer": true}]');

-- Create sample assignments
INSERT INTO assignments (id, user_id, subject_id, subject_type, level, srs_stage, unlocked_at, available_at) VALUES
(1, '550e8400-e29b-41d4-a716-446655440000', 1, 'radical', 1, 0, NOW(), NOW()),
(2, '550e8400-e29b-41d4-a716-446655440000', 2, 'kanji', 1, 0, NOW(), NOW()),
(3, '550e8400-e29b-41d4-a716-446655440000', 3, 'vocabulary', 1, 1, NOW(), NOW() - interval '1 day');

-- Create level progression
INSERT INTO level_progressions (id, user_id, level, unlocked_at, started_at) VALUES
(1, '550e8400-e29b-41d4-a716-446655440000', 1, NOW(), NOW());

-- Create review statistics
INSERT INTO review_statistics (id, user_id, subject_id, subject_type, meaning_correct, meaning_incorrect, reading_correct, reading_incorrect, percentage_correct) VALUES
(1, '550e8400-e29b-41d4-a716-446655440000', 1, 'radical', 5, 1, 0, 0, 83.3),
(2, '550e8400-e29b-41d4-a716-446655440000', 2, 'kanji', 3, 2, 2, 1, 62.5);
