"""Database initialization and utilities for the Team Brainstorming Study application."""
import sqlite3
from config import DATABASE_NAME


def get_db_connection():
    """Create and return a database connection."""
    return sqlite3.connect(DATABASE_NAME)


def init_db():
    """Initialize the database with all required tables."""
    conn = get_db_connection()
    c = conn.cursor()

    # Teams table - stores team session information and metrics
    c.execute('''
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id TEXT NOT NULL,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            final_idea TEXT,
            submitted BOOLEAN DEFAULT 0,
            submit_time TIMESTAMP,
            p1_title_keystroke_count INTEGER DEFAULT 0,
            p1_title_active_typing_seconds REAL DEFAULT 0,
            p1_title_first_edit_time TIMESTAMP,
            p1_title_last_edit_time TIMESTAMP,
            p1_description_keystroke_count INTEGER DEFAULT 0,
            p1_description_active_typing_seconds REAL DEFAULT 0,
            p1_description_first_edit_time TIMESTAMP,
            p1_description_last_edit_time TIMESTAMP,
            p2_title_keystroke_count INTEGER DEFAULT 0,
            p2_title_active_typing_seconds REAL DEFAULT 0,
            p2_title_first_edit_time TIMESTAMP,
            p2_title_last_edit_time TIMESTAMP,
            p2_description_keystroke_count INTEGER DEFAULT 0,
            p2_description_active_typing_seconds REAL DEFAULT 0,
            p2_description_first_edit_time TIMESTAMP,
            p2_description_last_edit_time TIMESTAMP,
            total_title_keystroke_count INTEGER DEFAULT 0,
            total_title_active_typing_seconds REAL DEFAULT 0,
            title_first_edit_time TIMESTAMP,
            title_last_edit_time TIMESTAMP,
            total_description_keystroke_count INTEGER DEFAULT 0,
            total_description_active_typing_seconds REAL DEFAULT 0,
            description_first_edit_time TIMESTAMP,
            description_last_edit_time TIMESTAMP,
            UNIQUE(team_id)
        )
    ''')

    # Messages table - stores all chat messages between participants and AI
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id TEXT NOT NULL,
            participant_id TEXT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tokens_used INTEGER
        )
    ''')

    # Ideas table - stores individual ideas submitted by participants
    c.execute('''
        CREATE TABLE IF NOT EXISTS ideas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id TEXT NOT NULL,
            participant_id TEXT NOT NULL,
            idea_text TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Survey page 1 - team collaboration questions
    c.execute('''
        CREATE TABLE IF NOT EXISTS survey_page1 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id TEXT NOT NULL,
            participant_id TEXT NOT NULL,
            q1 TEXT,
            q2 TEXT,
            q3 TEXT,
            q4 TEXT,
            q5 TEXT,
            q6 TEXT,
            q7 TEXT,
            q8 TEXT,
            q9 TEXT,
            q10 TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Survey page 2 - demographic information
    c.execute('''
        CREATE TABLE IF NOT EXISTS survey_page2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id TEXT NOT NULL,
            participant_id TEXT NOT NULL,
            employment_status TEXT,
            major_field TEXT,
            major_other TEXT,
            age INTEGER,
            gender TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Survey page 3 - contact information for gift card
    c.execute('''
        CREATE TABLE IF NOT EXISTS survey_page3 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id TEXT NOT NULL,
            participant_id TEXT NOT NULL,
            first_last_name TEXT,
            address_line1 TEXT,
            address_line2 TEXT,
            city TEXT,
            state TEXT,
            postal_code TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
