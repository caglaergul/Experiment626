"""Configuration settings for the Team Brainstorming Study application."""
import os

# OpenAI Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', 'your-api-key-here')
OPENAI_MODEL = "gpt-4o"
OPENAI_TEMPERATURE = 0.7
OPENAI_MAX_TOKENS = 1000

# Database Configuration
DATABASE_NAME = 'study_data.db'

# Session Configuration
SESSION_DURATION_MINUTES = 30
HEARTBEAT_TIMEOUT_SECONDS = 5

# Application Configuration
DEBUG = True
HOST = '0.0.0.0'
PORT = 5000
