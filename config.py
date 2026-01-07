import os
import yaml
from dotenv import load_dotenv

load_dotenv()

# --- Simulation Configuration ---
TICKERS = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN"]
INITIAL_CASH = 100000
SIMULATION_DAYS = 7


# --- API Keys ---
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPEN_ROUTER_KEY = os.getenv("OPEN_ROUTER_KEY")

# --- Development Configuration ---
DEV_MODE = os.getenv("DEV_MODE", "False").lower() in ('true', '1', 't')

# --- YAML Model Configuration & Active Providers ---
OPENROUTER_MODELS = []
ACTIVE_PROVIDERS = [] # List of active model aliases
YAML_CONFIG_ERROR = None
API_CALL_INTERVAL = 3 # Default value

try:
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    with open(config_path, 'r') as f:
        yaml_config = yaml.safe_load(f)
        if yaml_config:
            if 'api_call_interval' in yaml_config:
                API_CALL_INTERVAL = yaml_config['api_call_interval']
                
            if 'openrouter_models' in yaml_config:
                # Filter only active models
                OPENROUTER_MODELS = [m for m in yaml_config['openrouter_models'] if m.get('active', False)]
                
                # Add their aliases to the active providers list
                for model in OPENROUTER_MODELS:
                    ACTIVE_PROVIDERS.append(model['alias'])
                
except FileNotFoundError:
    YAML_CONFIG_ERROR = f"config.yaml not found at '{config_path}'."
except Exception as e:
    YAML_CONFIG_ERROR = f"Error loading or parsing config.yaml: {e}"

# If Gemini or OpenAI keys are present, we could add them as active providers too,
# but for now, let's focus on the OpenRouter models as requested.
# if GEMINI_API_KEY: ACTIVE_PROVIDERS.append('gemini')
