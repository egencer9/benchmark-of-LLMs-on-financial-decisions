import os
from dotenv import load_dotenv

load_dotenv()

# --- API Keys ---
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- LLM Configuration ---
# The LLM provider to use. Can be "gemini" or "openai".
# Set this in your .env file. Defaults to "gemini".
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()

# --- Development Configuration ---
# Set to "True" to use dummy LLM responses and avoid API costs during testing.
# Defaults to False.
DEV_MODE = os.getenv("DEV_MODE", "False").lower() in ('true', '1', 't')
