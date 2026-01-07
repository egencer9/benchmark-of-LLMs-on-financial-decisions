import google.generativeai as genai
import requests
import json
import time
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed
import config
from src.logger import log

# --- Configuration & Client Initialization ---
log.info(f"Active LLM Models: {config.ACTIVE_PROVIDERS}")

if config.DEV_MODE:
    log.warning("DEV_MODE is enabled. All LLM calls will return dummy responses.")

# Initialize OpenRouter session if needed
openrouter_session = None
if config.OPEN_ROUTER_KEY and config.OPENROUTER_MODELS:
    openrouter_session = requests.Session()
    log.info(f"OpenRouter session initialized for {len(config.OPENROUTER_MODELS)} active models.")

# --- Main Function ---
def get_llm_decisions(prompt, available_tickers):
    """
    Gets trading decisions from ALL active LLM models in parallel.
    Returns a dictionary: { "Model Alias": "JSON Response String", ... }
    """
    results = {}

    # 1. Handle DEV_MODE (Dummy Responses)
    if config.DEV_MODE:
        dummy_response = _get_dummy_response(available_tickers)
        for model in config.OPENROUTER_MODELS:
            results[model['alias']] = dummy_response
        return results

    # 2. Prepare Tasks for OpenRouter Models
    tasks = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        for model_config in config.OPENROUTER_MODELS:
            tasks.append(executor.submit(_get_openrouter_decision, prompt, model_config))
        
        # 3. Collect Results
        for future in as_completed(tasks):
            alias, response_text = future.result()
            results[alias] = response_text
            
    # Sleep to respect rate limits (global sleep after a batch of requests)
    log.info("Sleeping for 5 seconds to respect API rate limits...")
    time.sleep(5)

    return results

# --- Provider-Specific Functions ---
def _get_openrouter_decision(prompt, model_config):
    alias = model_config['alias']
    try:
        # Log sending
        log.info(f"Sending prompt to {alias}...")
        
        payload = {
            "model": model_config['model_name'],
            "messages": [{"role": "user", "content": prompt}],
            "reasoning": {"enabled": True}
        }
        
        response = openrouter_session.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {config.OPEN_ROUTER_KEY}",
                "Content-Type": "application/json"
            },
            data=json.dumps(payload)
        )
        
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            log.info(f"Received response from {alias}")
            return alias, content
        else:
            log.error(f"Error from {alias}: {response.status_code} - {response.text}")
            return alias, _get_dummy_response([]) # Return empty dummy on error

    except Exception as e:
        log.error(f"Exception calling {alias}: {e}")
        return alias, _get_dummy_response([])

def _get_dummy_response(tickers):
    # ... (Same as before)
    dummy_decisions = {
        ticker: {"decision": "HOLD", "reasoning": "Dummy response.", "confidence": 0.5}
        for ticker in tickers
    }
    return json.dumps(dummy_decisions, indent=2)

def construct_master_prompt(portfolio, market_data, news_summaries):
    # ... (Same as before, simplified prompt)
    tickers_list = list(market_data.keys())
    market_data_str = ""
    for ticker, data in market_data.items():
        news_summary = news_summaries.get(ticker, "No relevant news today.")
        market_data_str += f"""
Stock: {ticker}
Current Price: ${data['price']:.2f}
News: {news_summary}
"""

    prompt = f"""
You are a trading bot. Your goal is to make profitable trading decisions.
You must respond with a valid JSON object. Do not write any introduction, explanation, or conclusion. Just the JSON.

Current Portfolio:
Cash: ${portfolio['cash']:.2f}
Holdings: {portfolio['holdings']}

Market Data:
{market_data_str}

INSTRUCTIONS:
For each of the following stocks: {', '.join(tickers_list)}, decide whether to BUY, SELL, or HOLD.
Return a JSON object where the keys are the stock tickers and the values are objects containing "decision", "reasoning", and "confidence".

EXAMPLE RESPONSE FORMAT:
{{
  "AAPL": {{
    "decision": "BUY",
    "reasoning": "Positive news about earnings.",
    "confidence": 0.8
  }},
  "MSFT": {{
    "decision": "HOLD",
    "reasoning": "Market is uncertain.",
    "confidence": 0.5
  }}
}}

YOUR RESPONSE (JSON ONLY):
"""
    return prompt
