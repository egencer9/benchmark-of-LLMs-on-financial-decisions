import os
from transformers import pipeline, logging as hf_logging
import google.generativeai as genai
from config import GEMINI_API_KEY
from logger import log

# Suppress verbose logging from transformers
hf_logging.set_verbosity_error()

# Configure the Gemini API
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    log.info("Gemini API configured.")

# Load a local summarization model
try:
    log.info("Loading local summarization model (Qwen/Qwen2-0.5B)...")
    summarizer = pipeline("summarization", model="Qwen/Qwen2-0.5B")
    log.info("Summarization model loaded successfully.")
except Exception as e:
    log.error(f"Failed to load summarization model: {e}", exc_info=True)
    summarizer = None

def summarize_text(text, max_length=150, min_length=30):
    """
    Summarizes a given text using a local transformer model.
    """
    if not summarizer:
        log.warning("Summarization model not available. Returning truncated text.")
        return text[:max_length]
    if not text or not isinstance(text, str):
        return ""
    try:
        log.debug(f"Summarizing text of length {len(text)}")
        summary = summarizer(text, max_length=max_length, min_length=min_length, do_sample=False)
        log.debug(f"Generated summary: {summary[0]['summary_text']}")
        return summary[0]['summary_text']
    except Exception as e:
        log.error(f"Error during summarization: {e}", exc_info=True)
        return text[:max_length] # Fallback

def get_llm_decision(prompt):
    """
    Gets trading decisions from the LLM.
    """
    if not GEMINI_API_KEY:
        log.warning("GEMINI_API_KEY not found. Returning a dummy JSON response for testing.")
        dummy_response = """
        {
          "AAPL": {"decision": "HOLD", "reasoning": "Dummy: Market stable.", "confidence": 0.7},
          "MSFT": {"decision": "BUY", "reasoning": "Dummy: Positive news.", "confidence": 0.6},
          "NVDA": {"decision": "SELL", "reasoning": "Dummy: Overbought.", "confidence": 0.5},
          "TSLA": {"decision": "HOLD", "reasoning": "Dummy: Volatile.", "confidence": 0.8},
          "AMZN": {"decision": "BUY", "reasoning": "Dummy: Strong fundamentals.", "confidence": 0.75}
        }
        """
        return dummy_response

    try:
        log.info("Sending prompt to Gemini API...")
        log.debug(f"Prompt content:\n{prompt}")
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        log.info("Received response from Gemini API.")
        log.debug(f"Response content:\n{response.text}")
        return response.text
    except Exception as e:
        log.error(f"Error calling Gemini API: {e}", exc_info=True)
        return None

def construct_master_prompt(portfolio, market_data, news_summaries):
    """
    Constructs the single master prompt for the LLM.
    """
    log.debug("Constructing master prompt...")
    # ... (rest of the function is the same, no logging needed inside the prompt string)
    prompt = f"""
    **Objective:** Act as a financial analyst and decide whether to BUY, SELL, or HOLD for each stock in the portfolio. Provide your response in a single, clean JSON object.

    **Constraints:**
    1.  Your entire response must be a single JSON object.
    2.  For each stock, provide a 'decision' ('BUY', 'SELL', 'HOLD'), a brief 'reasoning', and a 'confidence' score (0.0 to 1.0).
    3.  Base your decisions *only* on the provided data. Do not use external knowledge.

    **Current Portfolio State:**
    - Cash: ${portfolio['cash']:.2f}
    - Holdings: {portfolio['holdings']}

    **Today's Market Data & News Summaries:**
    """

    for ticker, data in market_data.items():
        news_summary = news_summaries.get(ticker, "No relevant news today.")
        prompt += f"""
        ---
        **Stock: {ticker}**
        - Current Price: ${data['price']:.2f}
        - P/E Ratio: {data.get('pe_ratio', 'N/A')}
        - News Summary: {news_summary}
        """

    prompt += """
    ---
    **Instruction:**
    Based on all the information above, provide your trading decisions for all stocks in the following JSON format:
    {
      "TICKER1": {"decision": "BUY|SELL|HOLD", "reasoning": "...", "confidence": 0.X},
      "TICKER2": {"decision": "BUY|SELL|HOLD", "reasoning": "...", "confidence": 0.X},
      ...
    }
    """
    log.debug("Master prompt constructed.")
    return prompt
