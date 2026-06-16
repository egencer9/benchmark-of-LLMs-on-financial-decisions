from abc import ABC, abstractmethod
from google import genai
import requests
import json
import time
import re
from openai import OpenAI
import config
from src.logger import log

# --- Configuration & Client Initialization ---
log.info(f"LLM provider configured: {config.LLM_PROVIDER.upper()}")

clients = {}
if config.LLM_PROVIDER == 'gemini' and config.GEMINI_API_KEY:
    _gemini_client = genai.Client(api_key=config.GEMINI_API_KEY)
    clients['gemini'] = _gemini_client
    log.info("Gemini client initialized.")
elif config.LLM_PROVIDER == 'openai' and config.OPENAI_API_KEY:
    clients['openai'] = OpenAI(api_key=config.OPENAI_API_KEY)
    log.info("OpenAI client initialized.")
elif config.LLM_PROVIDER == 'openrouter' and config.OPEN_ROUTER_KEY:
    clients['openrouter'] = {'session': requests.Session()}
    if not config.YAML_CONFIG_ERROR and config.OPENROUTER_MODELS:
        log.info(f"OpenRouter client initialized for {len(config.OPENROUTER_MODELS)} models.")
    else:
        log.warning(f"OpenRouter client initialized, but config.yaml has issues: {config.YAML_CONFIG_ERROR}")

# --- SOLID Provider Classes ---

class LLMProvider(ABC):
    @abstractmethod
    def get_decision(self, prompt: str, model_config: dict = None) -> str:
        """Fetches trading decision from provider's API."""
        pass

class GeminiProvider(LLMProvider):
    def __init__(self, client):
        self.client = client

    def get_decision(self, prompt: str, model_config: dict = None) -> str:
        if not self.client:
            raise RuntimeError("Gemini client is not initialized.")
        def api_call():
            response = self.client.models.generate_content(
                model='gemini-2.5-flash-lite-preview-06-17',
                contents=prompt
            )
            return response.text
        return _api_call_with_retry(api_call, 'gemini')

class OpenAIProvider(LLMProvider):
    def __init__(self, client):
        self.client = client

    def get_decision(self, prompt: str, model_config: dict = None) -> str:
        if not self.client:
            raise RuntimeError("OpenAI client is not initialized.")
        def api_call():
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a JSON-only API endpoint."},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content
        return _api_call_with_retry(api_call, 'openai')

class OpenRouterProvider(LLMProvider):
    def __init__(self, session):
        self.session = session

    def get_decision(self, prompt: str, model_config: dict = None) -> str:
        if not self.session:
            raise RuntimeError("OpenRouter session is not initialized.")
        
        active_model = model_config or (config.OPENROUTER_MODELS[0] if config.OPENROUTER_MODELS else None)
        if not active_model:
            msg = "OpenRouter is selected, but no models are configured in config.yaml."
            log.error(msg)
            raise RuntimeError(msg)
        
        alias = active_model['alias']
        log.info(f"Calling model: {alias}")

        def api_call():
            payload = {
                "model": active_model['model_name'],
                "messages": [{"role": "user", "content": prompt}],
            }
            response = self.session.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {config.OPEN_ROUTER_KEY}",
                    "Content-Type": "application/json"
                },
                data=json.dumps(payload)
            )
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        return _api_call_with_retry(api_call, alias)

class LLMProviderFactory:
    _providers = {}

    @classmethod
    def get_provider(cls, provider_name: str) -> LLMProvider:
        provider_name = provider_name.lower()
        if provider_name not in cls._providers:
            if provider_name == 'gemini':
                cls._providers[provider_name] = GeminiProvider(clients.get('gemini'))
            elif provider_name == 'openai':
                cls._providers[provider_name] = OpenAIProvider(clients.get('openai'))
            elif provider_name == 'openrouter':
                router_client = clients.get('openrouter')
                session = router_client.get('session') if isinstance(router_client, dict) else None
                cls._providers[provider_name] = OpenRouterProvider(session)
            else:
                raise ValueError(f"Unsupported LLM provider: {provider_name}")
        return cls._providers[provider_name]

# --- Main Function ---
def get_llm_decision(prompt, available_tickers, model_config=None):
    """
    Gets a trading decision from the configured LLM provider.
    Returns None on total failure (backtester will treat as HOLD and continue).
    """
    provider_name = config.LLM_PROVIDER
    if provider_name not in clients:
        log.error(f"LLM Provider '{provider_name}' is not initialized. Check your API key.")
        return None  # Backtester will default to HOLD

    try:
        provider = LLMProviderFactory.get_provider(provider_name)
        result = provider.get_decision(prompt, model_config)

        log.info("Sleeping for 1 second to respect API rate limits...")
        time.sleep(1)

        return result

    except Exception as e:
        # Log but do NOT crash the backtest — return None so the day is treated as HOLD
        log.error(f"[LLM FAILURE] Provider '{provider_name}' failed entirely: {e}. Defaulting to HOLD for this day.", exc_info=True)
        return None

# --- Provider-Specific Functions with Retry Logic ---
def _api_call_with_retry(api_function, provider_name):
    import random
    max_retries = 6
    for attempt in range(max_retries):
        try:
            return api_function()
        except Exception as e:
            err_msg = str(e).lower()
            if "429" in err_msg or "rate limit" in err_msg or "too many requests" in err_msg:
                # Exponential backoff: 9s, 18s, 36s, 72s, 144s, 288s + jitter
                wait_time = (2 ** attempt) * 9 + random.uniform(1, 5)
                log.warning(
                    f"[Rate Limit] {provider_name} (Attempt {attempt + 1}/{max_retries}). "
                    f"Waiting {wait_time:.1f}s before retry..."
                )
                time.sleep(wait_time)
            else:
                log.error(f"[API Error] {provider_name}: {e}", exc_info=True)
                # Non-rate-limit errors: don't retry, return None so backtest can HOLD and continue
                return None
    log.error(f"[API Error] {provider_name} failed after {max_retries} retries (rate limit). Returning None → HOLD.")
    return None

# --- Sanity and Parsing Functions ---
def parse_llm_response(response_str):
    """
    Parses and sanitizes the LLM response string to match the required schema:
    { "decision": "LONG|SHORT|FLAT|HOLD", "confidence": 0-100, "reasoning": "string" }
    """
    if not response_str:
        return {"decision": "HOLD", "confidence": 50, "reasoning": "Empty response received."}
    
    clean_str = response_str.strip()
    # Strip markdown json code block fences if present
    if clean_str.startswith("```"):
        clean_str = re.sub(r"^```(?:json)?\n", "", clean_str)
        clean_str = re.sub(r"\n```$", "", clean_str)
        clean_str = clean_str.strip()

    try:
        data = json.loads(clean_str)
    except Exception as e:
        log.warning(f"JSON decode failed for LLM response: {e}. Raw response: {response_str}")
        return {"decision": "HOLD", "confidence": 50, "reasoning": f"Failed to parse JSON: {e}"}

    # Validate decision
    decision = str(data.get("decision", "HOLD")).upper().strip()
    if decision not in ["LONG", "SHORT", "FLAT", "HOLD"]:
        log.warning(f"Invalid decision '{decision}' returned by LLM. Defaulting to HOLD.")
        decision = "HOLD"

    # Validate confidence (integer between 0 and 100)
    try:
        confidence = int(float(data.get("confidence", 50)))
        if not (0 <= confidence <= 100):
            raise ValueError("Confidence out of 0-100 range")
    except Exception as e:
        log.warning(f"Invalid confidence value returned: {e}. Defaulting to 50.")
        confidence = 50

    reasoning = data.get("reasoning", "")
    if not isinstance(reasoning, str):
        reasoning = str(reasoning)

    return {
        "decision": decision,
        "confidence": confidence,
        "reasoning": reasoning
    }

# Dummy response generator removed to enforce strict real-data production runs.

def construct_master_prompt(portfolio, market_data, news_summaries, exchange="BIST30", trading_approach="Balanced", ta_market_data=None, current_date=None):
    log.debug(f"Constructing {exchange} master prompt with approach {trading_approach}...")

    exch_config = config.EXCHANGES.get(exchange, config.EXCHANGES["BIST30"])
    currency = exch_config["currency"]
    currency_symbol = exch_config["currency_symbol"]

    # Separate components and index
    index_ticker = "^NDX" if exchange == "NASDAQ" else "XU030.IS"
    index_price = market_data.get(index_ticker, {}).get('price', 0.0)
    macro_news = news_summaries.get(index_ticker, "No macroeconomic news.")

    # --- Technical Analysis block (only for TechnicalAnalysis approach) ---
    is_ta_mode = trading_approach.lower().strip() == "technicalanalysis" and ta_market_data is not None and current_date is not None
    ta_index_block = ""
    if is_ta_mode:
        from src.technical_indicators import get_index_ta_summary, get_stock_ta_brief
        ta_index_block = get_index_ta_summary(ta_market_data, index_ticker, current_date, currency_symbol)
        log.info(f"[TA Mode] Index technical summary injected into prompt.")

    stocks_str = ""
    for ticker, data in market_data.items():
        if ticker == index_ticker:
            continue
        company = exch_config.get("companies", {}).get(ticker, ticker)
        news = news_summaries.get(ticker, "No recent news.")
        # In TA mode, append stock-level TA brief (5D%, RSI)
        if is_ta_mode:
            ta_brief = get_stock_ta_brief(ta_market_data, ticker, current_date)
            stocks_str += f"- **{ticker}** ({company}): {currency_symbol}{data['price']:.2f} {currency} | {ta_brief} | News: {news}\n"
        else:
            stocks_str += f"- **{ticker}** ({company}): {currency_symbol}{data['price']:.2f} {currency} | News: {news}\n"

    # Define contract mechanics text
    if exchange == "NASDAQ":
        mechanics_text = """**NASDAQ Futures (MNQ) Mechanics:**
- Asset: Micro E-mini NASDAQ-100 Futures (MNQ) contracts.
- Multiplier: $2 per index point. A 100-point move represents $200 per contract profit or loss.
- Margin: Approximately $2,000 per contract. This is required collateral, not the full contract notional value.
- LONG: You profit when the NASDAQ-100 Index rises.
- SHORT: You profit when the NASDAQ-100 Index falls. No borrowing required — you simply sell the contract.
- FLAT: Exits all positions, holding cash only.
- HOLD: Maintains the current position.
- Worked Example: NASDAQ at 18,000. You SHORT 3 contracts. Index drops 150 points to 17,850. Profit = 150 points × $2/point × 3 contracts = $900."""
    else:
        mechanics_text = """**BIST30 Futures (VIOP) Mechanics:**
- Asset: VIOP BIST30 Index Futures contracts (XU030.IS).
- Contract Value: Index Price * 10 TL (e.g. index at 15,000 = contract value of 150,000 TL).
- Multiplier: 10 (1 index point change represents ₺10 profit or loss per contract).
- Margin: 10% of the contract value (which equals the BIST30 index price, e.g. ₺15,000 margin for a 150,000 TL contract).
- LONG: You profit when the BIST 30 Index rises.
- SHORT: You profit when the BIST 30 Index falls. No borrowing required — you simply sell the contract.
- FLAT: Exits all positions, holding cash only.
- HOLD: Maintains the current position.
- Worked Example: BIST30 at 15,000. You LONG 10 contracts. Index rises 200 points to 15,200. Profit = 200 points × 10 × 10 contracts = ₺20,000."""

    from src.trading_approach import TradingApproachFactory
    approach = TradingApproachFactory.get_approach(trading_approach)
    approach_instructions = approach.adjust_prompt_instructions()

    if approach_instructions:
        instructions_text = f"""4. Trading Stance: {approach_instructions}
5. Output a single valid JSON object containing exactly the keys: "decision", "confidence", and "reasoning". Do not include any markdown fences or conversational filler."""
    else:
        instructions_text = """4. Output a single valid JSON object containing exactly the keys: "decision", "confidence", and "reasoning". Do not include any markdown fences or conversational filler."""

    # Build the TA section for the prompt (only in TA mode)
    ta_section = ""
    if is_ta_mode and ta_index_block:
        ta_section = f"""
**Technical Analysis Indicators ({index_ticker}):**
{ta_index_block}
"""

    # Build instruction line 1 based on mode
    if is_ta_mode:
        analysis_instruction = "1. Analyze the technical indicators as your PRIMARY signal, then cross-reference with macroeconomic news and individual stock headlines."
    else:
        analysis_instruction = "1. Analyze the macroeconomic news and the individual stock headlines to form a single daily directional bias."

    prompt = f"""You are a financial trading agent operating on {exchange}.
You are benchmarked against other AI models. You trade index futures contracts only.
Individual stock news and prices are provided purely to build your daily directional bias. You NEVER trade individual stocks directly.

{mechanics_text}

**Current Portfolio & Account State:**
- Cash: {currency_symbol}{portfolio['cash']:,.2f} {currency} (cash not posted as margin)
- Total Account Equity: {currency_symbol}{portfolio.get('equity', portfolio['cash']):,.2f} {currency}
- Available Cash for Margin: {currency_symbol}{portfolio.get('available_cash', portfolio['cash']):,.2f} {currency}
- Current Position Type: {portfolio.get('position_type', 'FLAT')} (LONG / SHORT / FLAT)
- Number of Contracts Held: {portfolio.get('contracts', 0)}
- Entry Price: {currency_symbol}{portfolio.get('entry_price', 0.0):,.2f} {currency}
- Open Unrealized PnL: {currency_symbol}{portfolio.get('unrealized_pnl', 0.0):,.2f} {currency}

**{exchange} Index Price Today:**
- {index_ticker}: {currency_symbol}{index_price:,.2f} {currency}
{ta_section}
**Macroeconomic News & Context:**
- {macro_news}

**Individual Stock Component Data (FOR DIRECTIONAL BIAS ONLY - DO NOT TRADE STOCKS):**
{stocks_str}

**INSTRUCTIONS:**
{analysis_instruction}
2. Determine whether to go/stay LONG, go/stay SHORT, go FLAT (hold cash), or HOLD (keep current position).
3. Assign a confidence score from 0 to 100 (where 100 is maximum confidence and 0 is none). Your confidence score will scale the risk (number of contracts traded). Higher confidence = larger position size.
{instructions_text}

**JSON SCHEMA:**
{{
  "decision": "LONG | SHORT | FLAT | HOLD",
  "confidence": <integer between 0 and 100>,
  "reasoning": "brief description of macro bias and stock sentiment analysis"
}}

YOUR RESPONSE (JSON ONLY):
"""
    return prompt


