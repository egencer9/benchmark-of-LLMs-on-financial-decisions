import os
import yaml
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# --- Simulation Configuration ---
# BIST30 constituents (yfinance uses .IS suffix for Borsa Istanbul)
TICKERS = [
    "AKBNK.IS", "ARCLK.IS", "ASELS.IS", "BIMAS.IS", "CCOLA.IS",
    "DOHOL.IS", "EKGYO.IS", "EREGL.IS", "FROTO.IS", "GARAN.IS",
    "HALKB.IS", "ISCTR.IS", "KCHOL.IS", "KRDMD.IS", "MGROS.IS",
    "OTKAR.IS", "PETKM.IS", "PGSUS.IS", "SAHOL.IS", "SASA.IS",
    "SISE.IS", "SOKM.IS", "TAVHL.IS", "TCELL.IS", "THYAO.IS",
    "TKFEN.IS", "TOASO.IS", "TUPRS.IS", "VAKBN.IS", "YKBNK.IS"
]

# Company names used for news search queries (BIST tickers don't match news well)
COMPANY_NAMES = {
    "AKBNK.IS": "Akbank",
    "ARCLK.IS": "Arcelik",
    "ASELS.IS": "Aselsan",
    "BIMAS.IS": "BIM Birlesik Magazalar",
    "CCOLA.IS": "Coca-Cola Icecek",
    "DOHOL.IS": "Dogan Holding",
    "EKGYO.IS": "Emlak Konut",
    "EREGL.IS": "Eregli Demir Celik",
    "FROTO.IS": "Ford Otosan",
    "GARAN.IS": "Garanti BBVA",
    "HALKB.IS": "Halkbank",
    "ISCTR.IS": "Is Bankasi",
    "KCHOL.IS": "Koc Holding",
    "KRDMD.IS": "Kardemir",
    "MGROS.IS": "Migros",
    "OTKAR.IS": "Otokar",
    "PETKM.IS": "Petkim",
    "PGSUS.IS": "Pegasus Airlines",
    "SAHOL.IS": "Sabanci Holding",
    "SASA.IS": "SASA Polyester",
    "SISE.IS": "Sisecam",
    "SOKM.IS": "Sok Marketler",
    "TAVHL.IS": "TAV Airports",
    "TCELL.IS": "Turkcell",
    "THYAO.IS": "Turkish Airlines",
    "TKFEN.IS": "Tekfen Holding",
    "TOASO.IS": "Tofas",
    "TUPRS.IS": "Tupras",
    "VAKBN.IS": "Vakifbank",
    "YKBNK.IS": "Yapi Kredi",
}

INITIAL_CASH = 1000000  # 1 milyon TRY
SIMULATION_DAYS = 30

# --- Trading Configuration ---
TRADING_MODE = 'spot'  # BIST30 icin spot trading

# --- Dynamic Date Configuration ---
USE_DYNAMIC_DATES = True

if USE_DYNAMIC_DATES:
    EVALUATION_END_DATE = datetime.now().strftime("%Y-%m-%d")
else:
    EVALUATION_END_DATE = "2024-05-01"

# --- API Keys ---
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPEN_ROUTER_KEY = os.getenv("OPEN_ROUTER_KEY")

# --- LLM Provider Configuration ---
LLM_PROVIDER = "openrouter"

# --- Development Configuration ---
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
