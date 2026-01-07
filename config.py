import os
import yaml
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# --- Simulation Configuration ---
TICKERS = ["^NDX", "AAPL", "MSFT", "NVDA", "TSLA", "AMZN"]
TARGET_TICKER = "^NDX"
CONTEXT_TICKERS = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN"]

INITIAL_CASH = 100000
SIMULATION_DAYS = 30

# --- Futures Trading Configuration ---
TRADING_MODE = 'futures' # 'spot' or 'futures'
FUTURES_CONFIG = {
    'ticker': 'MNQ',
    'contract_name': 'Micro E-mini Nasdaq-100',
    'margin_per_contract': 2000,
    'point_multiplier': 2.0,
    'tick_size': 0.25,
    'tick_value': 0.50
}

# --- Dynamic Date Configuration ---
USE_DYNAMIC_DATES = True

if USE_DYNAMIC_DATES:
    EVALUATION_END_DATE = datetime.now().strftime("%Y-%m-%d")
else:
    # --- FIX: Use a fixed end date to avoid system clock issues ---
    EVALUATION_END_DATE = "2024-05-01" 

# --- API Keys ---
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPEN_ROUTER_KEY = os.getenv("OPEN_ROUTER_KEY")

# --- LLM Provider Configuration ---
# Set to 'openrouter' to use Xiaomi Mimo V2 Flash
LLM_PROVIDER = "openrouter"

# --- Development Configuration ---
# Set to False to enable real API calls
DEV_MODE = False

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
