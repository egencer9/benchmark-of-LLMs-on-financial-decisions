import google.generativeai as genai
import requests
import json
import time
from openai import OpenAI
import config
from src.logger import log

# --- Configuration & Client Initialization ---
log.info(f"LLM provider configured: {config.LLM_PROVIDER.upper()}")
if config.DEV_MODE:
    log.warning("DEV_MODE is enabled. All LLM calls will return dummy responses.")

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
    model_config: a dict with 'alias' and 'model_name' keys (OpenRouter only).
                  If None, falls back to the first model in config.yaml.
    """
    if config.DEV_MODE:
        log.warning("DEV_MODE is ON. Returning a dummy response.")
        return _get_dummy_response(available_tickers)

    provider = config.LLM_PROVIDER
    if provider not in clients:
        log.error(f"Provider '{provider}' is not initialized. Check API key. Returning dummy response.")
        return _get_dummy_response(available_tickers)

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
                log.error("OpenRouter is selected, but no models are configured in config.yaml.")
                result = _get_dummy_response(available_tickers)

        log.info("Sleeping for 10 seconds to respect API rate limits...")
        time.sleep(10)

        return result

    except Exception as e:
        log.error(f"An unexpected error occurred during API call for {provider}: {e}", exc_info=True)
        return _get_dummy_response(available_tickers)

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

def _get_dummy_response(tickers):
    import random
    log.info(f"Generating dummy trading response for {len(tickers)} tickers")
    dummy_decisions = {}
    for ticker in tickers:
        # 40% HOLD, 35% BUY, 25% SELL
        decision = random.choices(["BUY", "SELL", "HOLD"], weights=[35, 25, 40], k=1)[0]
        confidence = round(random.uniform(0.6, 0.95), 2) if decision != "HOLD" else 0.5
        reasoning = f"Simulated {decision} signal for {ticker} based on mock technical indicators."
        dummy_decisions[ticker] = {
            "decision": decision,
            "reasoning": reasoning,
            "confidence": confidence
        }
    return json.dumps(dummy_decisions, indent=2)

def construct_master_prompt(portfolio, market_data, news_summaries, exchange="BIST30"):
    log.debug(f"Constructing {exchange} master prompt...")

    exch_config = config.EXCHANGES.get(exchange, config.EXCHANGES["BIST30"])
    currency = exch_config["currency"]
    currency_symbol = exch_config["currency_symbol"]

    stocks_str = ""
    for ticker, data in market_data.items():
        company = exch_config.get("companies", {}).get(ticker, ticker)
        news = news_summaries.get(ticker, "No recent news.")
        stocks_str += f"- **{ticker}** ({company}): {currency_symbol}{data['price']:.2f} {currency} | News: {news}\n"

    tickers_list = list(market_data.keys())

    prompt = f"""You are a financial trading agent operating on {exchange}.
You are trading SPOT stocks. All prices and cash are in {currency} ({currency_symbol}).

**Current Portfolio:**
- Cash: {currency_symbol}{portfolio['cash']:,.2f} {currency}
- Holdings: {portfolio['holdings']}

**{exchange} Market Data:**
{stocks_str}

**INSTRUCTIONS:**
1. Analyze each stock's price and news to determine a trading signal.
2. For each stock, output BUY, SELL, or HOLD with a confidence score (0.0-1.0) and brief reasoning.
3. Be decisive — do not default to HOLD unless there is genuinely no signal.
4. Output a valid JSON object where each key is a ticker symbol and value contains "decision", "reasoning", and "confidence".

**EXAMPLE RESPONSE FORMAT:**
{{
  "{tickers_list[0] if tickers_list else 'TICKER'}": {{"decision": "BUY", "reasoning": "Strong quarterly performance and positive sentiment.", "confidence": 0.85}},
  "{tickers_list[1] if len(tickers_list) > 1 else 'TICKER2'}": {{"decision": "HOLD", "reasoning": "Awaiting earnings report.", "confidence": 0.50}}
}}

**Available tickers (respond for each one):** {tickers_list}

YOUR RESPONSE (JSON ONLY):
"""
    return prompt
