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
def get_llm_decision(prompt, available_tickers):
    """
    Gets a trading decision from the single configured LLM provider.
    """
    if config.DEV_MODE:
        log.warning("DEV_MODE is ON. Returning a dummy response.")
        return _get_dummy_response(available_tickers)

    provider = config.LLM_PROVIDER
    if provider not in clients:
        log.error(f"Provider '{provider}' is not initialized. Check API key. Returning dummy response.")
        return _get_dummy_response(available_tickers)

    try:
        # --- DEBUG: Log the prompt to see what data is being sent ---
        log.info(f"Sending PROMPT to {provider}:\n{prompt}")
        
        result = None
        if provider == 'gemini':
            result = _get_gemini_decision(prompt)
        elif provider == 'openai':
            result = _get_openai_decision(prompt)
        elif provider == 'openrouter':
            if config.OPENROUTER_MODELS:
                model_config = config.OPENROUTER_MODELS[0]
                result = _get_openrouter_decision(prompt, model_config)
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
        # --- FIX: Add reasoning parameter to match curl request ---
        payload = {
            "model": model_config['model_name'],
            "messages": [{"role": "user", "content": prompt}],
            "reasoning": {"enabled": True}
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
    # Ignore the input tickers list (which might contain everything)
    # Output only for the target ticker as NDX
    target_output_key = "NDX"
    log.info(f"Generating dynamic dummy response for {target_output_key}")
    
    dummy_decisions = {
        target_output_key: {"decision": "HOLD", "reasoning": "Dummy response due to API failure.", "confidence": 0.5}
    }
    return json.dumps(dummy_decisions, indent=2)

def construct_master_prompt(portfolio, market_data, news_summaries):
    log.debug("Constructing prompt for NDX trading...")
    
    target_ticker = config.TARGET_TICKER
    context_tickers = config.CONTEXT_TICKERS
    
    # --- Format Target Data ---
    target_data = market_data.get(target_ticker, {'price': 0})
    target_news = news_summaries.get(target_ticker, "No specific news for the index.")
    
    target_info_str = f"""
TARGET ASSET: {target_ticker} (Nasdaq-100)
Current Level: ${target_data['price']:.2f}
News/Analysis: {target_news}
"""

    # --- Format Context Data ---
    context_info_str = "MARKET CONTEXT (Major Tech Stocks - Use for Sentiment Analysis Only):\\n"
    for ticker in context_tickers:
        if ticker in market_data:
            data = market_data[ticker]
            news = news_summaries.get(ticker, "No recent news.")
            context_info_str += f"""
- {ticker}:
  Price: ${data['price']:.2f}
  News: {news}
"""

    prompt = f"""
You are a sophisticated financial trading agent specializing in the Nasdaq-100 index (NDX).
You are trading **Micro E-mini Nasdaq-100 (MNQ) Futures**, NOT the spot index directly.

**TRADING MECHANICS (CRITICAL):**
- **Instrument**: {config.FUTURES_CONFIG['contract_name']} ({config.FUTURES_CONFIG['ticker']})
- **Index Price**: ~${target_data.get('price', 0):.2f}
- **Multiplier**: ${config.FUTURES_CONFIG['point_multiplier']} per point
- **Margin Required**: ${config.FUTURES_CONFIG['margin_per_contract']} per contract
- **Leverage**: You control a notional value of (Price * Multiplier) ~${target_data.get('price', 0) * 2:.2f} using only ${config.FUTURES_CONFIG['margin_per_contract']} of capital.
- **P&L**: Proft/Loss = (Exit Price - Entry Price) * {config.FUTURES_CONFIG['point_multiplier']} * Contracts

Your task is to analyze the market data and news for the Nasdaq-100 index and its major components (AAPL, MSFT, NVDA, TSLA, AMZN).

Based on this analysis, you must generate a SINGLE trading decision ('BUY', 'SELL', or 'HOLD') for the Nasdaq-100 index.
Do NOT generate decisions for the individual component stocks. They are provided only as context to help you gauge the overall market sentiment.

Current Portfolio:
Cash (Allocatable Margin): ${portfolio['cash']:.2f}
Current Holdings (Contracts): {portfolio['holdings']}

Market Data:
{target_info_str}
{context_info_str}

INSTRUCTIONS:
1. Analyze the news and price action of the major tech stocks (Context) to form a view on the broader tech sector.
2. Combine this with the specific news and data for the Nasdaq-100 (Target).
3. **Consider your Purchasing Power**: With ${portfolio['cash']:.0f} cash, you can buy approx {int(portfolio['cash'] / config.FUTURES_CONFIG['margin_per_contract'])} contracts.
4. Output a valid JSON object containing a SINGLE key: "NDX".
5. The value for "NDX" must be an object with "decision", "reasoning", and "confidence".


EXAMPLE RESPONSE FORMAT:
{{
  "NDX": {{
    "decision": "BUY",
    "reasoning": "Strong earnings from AAPL and MSFT are lifting the tech sector, despite mixed signals from TSLA.",
    "confidence": 0.85
  }}
}}

YOUR RESPONSE (JSON ONLY):
"""
    return prompt
