"""Application settings"""
import os
from datetime import timedelta

# Database settings
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///bot_database.db')
TEST_DATABASE_URL = 'sqlite:///test_bot_database.db'

# Reminder settings
DEFAULT_REMINDER_TIME = timedelta(minutes=15)
MAX_REMINDERS_PER_USER = 10

# LLM settings
LLM_API_BASE = os.getenv('LLM_API_BASE', 'http://172.18.0.3:4000/v1')
LLM_MODEL_NAME = os.getenv('LLM_MODEL_NAME', 'Claude')
MAX_TOKENS = 4096

# Character settings
DEFAULT_CHARACTER = 'default'
AVAILABLE_CHARACTERS = ['default', 'cyber', 'sassy']

# History settings
MAX_HISTORY_LENGTH = 10
DEFAULT_CONTEXT_LENGTH = 5