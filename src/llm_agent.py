import google.generativeai as genai
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
    genai.configure(api_key=config.GEMINI_API_KEY)
    clients['gemini'] = genai.GenerativeModel('gemini-2.5-flash-lite')
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

# --- Main Function ---
def get_llm_decision(prompt, available_tickers, model_config=None):
    """
    Gets a trading decision from the configured LLM provider.
    """
    provider = config.LLM_PROVIDER
    if provider not in clients:
        msg = f"LLM Provider '{provider}' is not initialized. Please verify your API key or connection."
        log.error(msg)
        raise RuntimeError(msg)

    try:
        result = None
        if provider == 'gemini':
            result = _get_gemini_decision(prompt)
        elif provider == 'openai':
            result = _get_openai_decision(prompt)
        elif provider == 'openrouter':
            active_model = model_config or (config.OPENROUTER_MODELS[0] if config.OPENROUTER_MODELS else None)
            if active_model:
                log.info(f"Calling model: {active_model['alias']}")
                result = _get_openrouter_decision(prompt, active_model)
            else:
                msg = "OpenRouter is selected, but no models are configured in config.yaml."
                log.error(msg)
                raise RuntimeError(msg)

        log.info("Sleeping for 10 seconds to respect API rate limits...")
        time.sleep(10)

        return result

    except Exception as e:
        log.error(f"An unexpected error occurred during API call for {provider}: {e}", exc_info=True)
        raise RuntimeError(
            f"Failed to communicate with LLM provider '{provider}': {e}. "
            f"Please verify your API key, check your internet connection/VPN, and retry the simulation."
        )

# --- Provider-Specific Functions with Retry Logic ---
def _api_call_with_retry(api_function, provider_name):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return api_function()
        except Exception as e:
            if "429" in str(e):
                wait_time = 10 + (attempt * 10)
                log.warning(f"Rate limit exceeded for {provider_name}. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                log.error(f"Error calling {provider_name} API: {e}", exc_info=True)
                raise e
    raise Exception(f"API call to {provider_name} failed after {max_retries} retries.")

def _get_gemini_decision(prompt):
    def api_call():
        return clients['gemini'].generate_content(prompt).text
    return _api_call_with_retry(api_call, 'gemini')

def _get_openai_decision(prompt):
    def api_call():
        response = clients['openai'].chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are a JSON-only API endpoint."}, {"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    return _api_call_with_retry(api_call, 'openai')

def _get_openrouter_decision(prompt, model_config):
    alias = model_config['alias']
    def api_call():
        payload = {
            "model": model_config['model_name'],
            "messages": [{"role": "user", "content": prompt}],
        }
        
        response = clients['openrouter']['session'].post(
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

def construct_master_prompt(portfolio, market_data, news_summaries, exchange="BIST30"):
    log.debug(f"Constructing {exchange} master prompt...")

    exch_config = config.EXCHANGES.get(exchange, config.EXCHANGES["BIST30"])
    currency = exch_config["currency"]
    currency_symbol = exch_config["currency_symbol"]

    # Separate components and index
    index_ticker = "^NDX" if exchange == "NASDAQ" else "XU030.IS"
    index_price = market_data.get(index_ticker, {}).get('price', 0.0)
    macro_news = news_summaries.get(index_ticker, "No macroeconomic news.")

    stocks_str = ""
    for ticker, data in market_data.items():
        if ticker == index_ticker:
            continue
        company = exch_config.get("companies", {}).get(ticker, ticker)
        news = news_summaries.get(ticker, "No recent news.")
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
- Contract Value: (Index Price / 1000) * 100 TL = Index Price * 0.1 TL (e.g. index at 120,000 = contract value of 12,000 TL).
- Multiplier: 0.1 (1 index point change represents ₺0.1 profit or loss per contract).
- Margin: 10% of the contract value (e.g. ₺1,200 margin for a 12,000 TL contract).
- LONG: You profit when the BIST 30 Index rises.
- SHORT: You profit when the BIST 30 Index falls. No borrowing required — you simply sell the contract.
- FLAT: Exits all positions, holding cash only.
- HOLD: Maintains the current position.
- Worked Example: BIST30 at 120,000. You LONG 10 contracts. Index rises 2,000 points to 122,000. Profit = 2,000 points × 0.1 × 10 contracts = ₺2,000."""

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

**Macroeconomic News & Context:**
- {macro_news}

**Individual Stock Component Data (FOR DIRECTIONAL BIAS ONLY - DO NOT TRADE STOCKS):**
{stocks_str}

**INSTRUCTIONS:**
1. Analyze the macroeconomic news and the individual stock headlines to form a single daily directional bias.
2. Determine whether to go/stay LONG, go/stay SHORT, go FLAT (hold cash), or HOLD (keep current position).
3. Assign a confidence score from 0 to 100 (where 100 is maximum confidence and 0 is none). Your confidence score will scale the risk (number of contracts traded). Higher confidence = larger position size.
4. Output a single valid JSON object containing exactly the keys: "decision", "confidence", and "reasoning". Do not include any markdown fences or conversational filler.

**JSON SCHEMA:**
{{
  "decision": "LONG | SHORT | FLAT | HOLD",
  "confidence": <integer between 0 and 100>,
  "reasoning": "brief description of macro bias and stock sentiment analysis"
}}

YOUR RESPONSE (JSON ONLY):
"""
    return prompt
