import google.generativeai as genai
import requests
import json
import time
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed

# Artık sys.path ayarına burada gerek yok, main.py bunu yapıyor.

import config
from src.logger import log

# --- Initial Configuration Logging ---
log.info(f"LLM providers configured: {config.LLM_PROVIDERS}")
if config.DEV_MODE:
    log.warning("DEV_MODE is enabled. All LLM calls will return dummy responses.")
if config.YAML_CONFIG_ERROR:
    log.warning(f"YAML config issue: {config.YAML_CONFIG_ERROR} OpenRouter models may not be available.")
else:
    log.info(f"Successfully loaded {len(config.OPENROUTER_MODELS)} OpenRouter models from config.yaml.")

# --- Client Initialization ---
clients = {}
if 'gemini' in config.LLM_PROVIDERS and config.GEMINI_API_KEY:
    genai.configure(api_key=config.GEMINI_API_KEY)
    clients['gemini'] = genai.GenerativeModel('gemini-2.5-flash-lite')
    log.info("Gemini client initialized.")
if 'openai' in config.LLM_PROVIDERS and config.OPENAI_API_KEY:
    clients['openai'] = OpenAI(api_key=config.OPENAI_API_KEY)
    log.info("OpenAI client initialized.")
if 'openrouter' in config.LLM_PROVIDERS and config.OPEN_ROUTER_KEY:
    clients['openrouter'] = {'session': requests.Session()}
    log.info(f"OpenRouter client initialized for {len(config.OPENROUTER_MODELS)} models.")

# --- Main Function ---
def get_llm_decisions(prompt, available_tickers):
    if config.DEV_MODE:
        log.warning("DEV_MODE is ON. Returning a single dummy response.")
        return _get_dummy_response(available_tickers)

    if not clients:
        log.error("No valid LLM clients are initialized. Returning dummy response.")
        return _get_dummy_response(available_tickers)

    tasks = []
    with ThreadPoolExecutor() as executor:
        for provider in config.LLM_PROVIDERS:
            if provider in clients:
                if provider == 'gemini':
                    tasks.append(executor.submit(_get_gemini_decision, prompt, available_tickers))
                elif provider == 'openai':
                    tasks.append(executor.submit(_get_openai_decision, prompt, available_tickers))
                elif provider == 'openrouter':
                    for model_config in config.OPENROUTER_MODELS:
                        tasks.append(executor.submit(_get_openrouter_decision, prompt, model_config, available_tickers))

    results = {}
    for future in as_completed(tasks):
        try:
            provider_name, response_text = future.result()
            results[provider_name] = response_text
            log.info(f"Successfully received response from {provider_name}.")
            log.debug(f"Response from {provider_name}:\n{response_text}")
        except Exception as e:
            log.error(f"A task failed to complete: {e}", exc_info=True)

    primary_provider = config.LLM_PROVIDERS[0]
    if primary_provider == 'openrouter':
        primary_provider = config.OPENROUTER_MODELS[0]['alias']

    return results.get(primary_provider, _get_dummy_response(available_tickers))

# --- Provider-Specific Functions with Retry Logic ---
def _api_call_with_retry(api_function, provider_name, *args):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return api_function(*args)
        except Exception as e:
            if "429" in str(e):
                wait_time = (2 ** attempt) * 5
                log.warning(f"Rate limit exceeded for {provider_name}. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                log.error(f"Error calling {provider_name} API: {e}")
                raise e
    raise Exception(f"API call to {provider_name} failed after {max_retries} retries.")

def _get_gemini_decision(prompt, tickers):
    def api_call():
        return 'gemini', clients['gemini'].generate_content(prompt).text
    try:
        return _api_call_with_retry(api_call, 'gemini')
    except Exception:
        return 'gemini', _get_dummy_response(tickers)

def _get_openai_decision(prompt, tickers):
    def api_call():
        response = clients['openai'].chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are a financial analyst..."}, {"role": "user", "content": prompt}]
        )
        return 'openai', response.choices[0].message.content
    try:
        return _api_call_with_retry(api_call, 'openai')
    except Exception:
        return 'openai', _get_dummy_response(tickers)

def _get_openrouter_decision(prompt, model_config, tickers):
    alias = model_config['alias']
    def api_call():
        response = clients['openrouter']['session'].post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {config.OPEN_ROUTER_KEY}"},
            data=json.dumps({"model": model_config['model_name'], "messages": [{"role": "user", "content": prompt}]})
        )
        response.raise_for_status()
        return alias, response.json()['choices'][0]['message']['content']
    try:
        return _api_call_with_retry(api_call, alias)
    except Exception:
        return alias, _get_dummy_response(tickers)

def _get_dummy_response(tickers):
    log.info(f"Generating dynamic dummy response for tickers: {tickers}")
    dummy_decisions = {
        ticker: {"decision": "HOLD", "reasoning": "Dummy response due to API failure.", "confidence": 0.5}
        for ticker in tickers
    }
    return json.dumps(dummy_decisions, indent=2)

def construct_master_prompt(portfolio, market_data, news_summaries):
    log.debug("Constructing master prompt...")
    prompt = f"""
    **Objective:** Act as a financial analyst...
    **Current Portfolio State:**
    - Cash: ${portfolio['cash']:.2f}
    - Holdings: {portfolio['holdings']}
    **Today's Market Data & News Summaries:**
    """
    for ticker, data in market_data.items():
        prompt += f"""
        ---
        **Stock: {ticker}**
        - Current Price: ${data['price']:.2f}
        - News Summary: {news_summaries.get(ticker, "No relevant news today.")}
        """
    prompt += """
    ---
    **Instruction:** Based on all the information above...
    """
    return prompt
