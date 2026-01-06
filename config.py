import os
import yaml
from dotenv import load_dotenv

load_dotenv()

# --- Simulation Configuration ---
TICKERS = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN"]
INITIAL_CASH = 100000
SIMULATION_DAYS = 7  # Reduced to 7 days (1 week) as requested

# --- FIX: Use a fixed end date to avoid system clock issues ---
EVALUATION_END_DATE = "2024-05-01" 

# --- API Keys ---
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPEN_ROUTER_KEY = os.getenv("OPEN_ROUTER_KEY")

# --- LLM Provider Configuration ---
LLM_PROVIDER = "gemini" 

# --- Development Configuration ---
DEV_MODE = os.getenv("DEV_MODE", "False").lower() in ('true', '1', 't')

# --- YAML Model Configuration ---
OPENROUTER_MODELS = []
YAML_CONFIG_ERROR = None

try:
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    with open(config_path, 'r') as f:
        yaml_config = yaml.safe_load(f)
        if yaml_config and 'openrouter_models' in yaml_config:
            OPENROUTER_MODELS = yaml_config['openrouter_models']
except FileNotFoundError:
    YAML_CONFIG_ERROR = f"config.yaml not found at '{config_path}'."
except Exception as e:
    YAML_CONFIG_ERROR = f"Error loading or parsing config.yaml: {e}"
