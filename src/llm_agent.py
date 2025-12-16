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
    clients['gemini'] = genai.GenerativeModel('gemini-1.5-flash-latest')
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
        if provider == 'gemini':
            return _get_gemini_decision(prompt)
        elif provider == 'openai':
            return _get_openai_decision(prompt)
        elif provider == 'openrouter':
            # For OpenRouter, we'll just use the first model in the list for simplicity.
            if config.OPENROUTER_MODELS:
                model_config = config.OPENROUTER_MODELS[0]
                return _get_openrouter_decision(prompt, model_config)
            else:
                log.error("OpenRouter is selected, but no models are configured in config.yaml.")
                return _get_dummy_response(available_tickers)
    except Exception as e:
        log.error(f"An unexpected error occurred during API call for {provider}: {e}", exc_info=True)
        return _get_dummy_response(available_tickers)

# --- Provider-Specific Functions with Retry Logic ---
def _api_call_with_retry(api_function, provider_name):
    max_retries = 2
    for attempt in range(max_retries):
        try:
            return api_function()
        except Exception as e:
            if "429" in str(e):
                wait_time = 5 + (attempt * 5)
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
        response = clients['openrouter']['session'].post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {config.OPEN_ROUTER_KEY}"},
            data=json.dumps({"model": model_config['model_name'], "messages": [{"role": "user", "content": prompt}]})
        )
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    return _api_call_with_retry(api_call, alias)

def _get_dummy_response(tickers):
    log.info(f"Generating dynamic dummy response for tickers: {tickers}")
    dummy_decisions = {
        ticker: {"decision": "HOLD", "reasoning": "Dummy response due to API failure.", "confidence": 0.5}
        for ticker in tickers
    }
    return json.dumps(dummy_decisions, indent=2)

def construct_master_prompt(portfolio, market_data, news_summaries):
    log.debug("Constructing bulletproof master prompt...")
    market_data_str = ""
    for ticker, data in market_data.items():
        news_summary = news_summaries.get(ticker, "No relevant news today.")
        market_data_str += f"""- **Stock: {ticker}**
  - Current Price: ${data['price']:.2f}
  - News Summary: {news_summary}\n"""

    return f"""You are a JSON-only API endpoint...
<real_input>
**Portfolio:**
- Cash: ${portfolio['cash']:.2f}
- Holdings: {portfolio['holdings']}
**Market Data:**
{market_data_str}
</real_input>
<real_output>
"""
