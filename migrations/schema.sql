-- Enable the pgcrypto extension to generate UUIDs (Run once per database)
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Sequence for generating unique anonymous usernames (Still needed)
CREATE SEQUENCE IF NOT EXISTS anonymous_user_seq START 1;

-- Drop existing table and related objects if they exist (to apply new PK type)
-- WARNING: THIS WILL DELETE ALL DATA IN THE drop_note TABLE
DROP TRIGGER IF EXISTS update_drop_note_updated_at ON drop_note;
DROP FUNCTION IF EXISTS update_updated_at_column(); -- Drop function if exists
DROP TABLE IF EXISTS drop_note;
-- Sequence anonymous_user_seq is kept

-- Table definition for drop_note project notes with UUID primary key
CREATE TABLE drop_note (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- Use UUID with default generator
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    username TEXT NOT NULL,
    tags TEXT[] CHECK (array_length(tags, 1) <= 10),
    visibility TEXT NOT NULL CHECK (visibility IN ('public', 'private')),
    modification_code TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Optional: Add an index for faster lookups by modification code
CREATE INDEX IF NOT EXISTS idx_drop_note_modification_code ON drop_note (modification_code);

-- Optional: Add an index for filtering public notes by tags (using GIN index for array)
CREATE INDEX IF NOT EXISTS idx_drop_note_tags ON drop_note USING GIN (tags) WHERE visibility = 'public';

-- Trigger function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = NOW();
   RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to execute the function before any update on the drop_note table
CREATE TRIGGER update_drop_note_updated_at
BEFORE UPDATE ON drop_note
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();
