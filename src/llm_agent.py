import time
import google.generativeai as genai
from config import GEMINI_API_KEY
from logger import log

# Configure the Gemini API
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    log.info("Gemini API configured.")

def get_llm_decision(prompt):
    """
    Gets trading decisions from the LLM.
    This function sends the aggregated, summarized prompt to the LLM API.
    """
    if not GEMINI_API_KEY:
        log.warning("GEMINI_API_KEY not found. Returning a dummy JSON response for testing.")
        dummy_response = """
        {
          "NDX": {"decision": "HOLD", "reasoning": "Dummy response: Mixed signals from tech giants (AAPL, MSFT). Market is consolidating.", "confidence": 0.6}
        }
        """
        return dummy_response

    max_retries = 10
    base_delay = 5
    
    for attempt in range(max_retries):
        try:
            log.info(f"Sending prompt to Gemini API (Attempt {attempt + 1}/{max_retries})...")
            log.debug(f"Prompt content:\n{prompt}")
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(prompt)
            log.info("Received response from Gemini API.")
            log.debug(f"Response content:\n{response.text}")
            return response.text
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "Quota exceeded" in error_str or "ResourceExhausted" in error_str:
                wait_time = base_delay * (2 ** attempt)
                log.warning(f"Rate limit hit. Retrying in {wait_time} seconds... (Error: {error_str})")
                time.sleep(wait_time)
            else:
                log.error("Error calling Gemini API: {e}", e=e, exc_info=True)
                return None # Indicate failure (non-retriable error)
    
    log.error(f"Max retries ({max_retries}) exceeded for Gemini API call.")
    return None

def construct_master_prompt(portfolio, market_data, news_summaries):
    """
    Constructs the single master prompt for the LLM, aggregating all data.
    """
    log.debug("Constructing master prompt...")
    prompt = f"""
    **Objective:** Act as a financial analyst. You will be provided with market data and news for several major tech stocks (AAPL, MSFT, NVDA, TSLA, AMZN) and the Nasdaq 100 index (NDX). Your goal is to analyze the performance and news of these heavyweights to formulate a trading strategy specifically for **NDX** (Nasdaq 100).

    **Constraints:**
    1.  Your entire response must be a single JSON object.
    2.  The JSON must strictly contain a SINGLE key: "NDX".
    3.  For "NDX", provide a 'decision' ('BUY', 'SELL', 'HOLD'), a 'reasoning' (citing specific insights from the other stocks), and a 'confidence' score (0.0 to 1.0).
    4.  Base your decisions *only* on the provided data. Do not use external knowledge.

    **Current Portfolio State:**
    - Cash: ${portfolio['cash']:.2f}
    - Holdings: {portfolio['holdings']}

    **Today's Market Data & News Summaries:**
    """

    for ticker, data in market_data.items():
        # The 'news_summaries' now directly contain the aggregated descriptions
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
    Based on all the information above (using AAPL, MSFT, etc. as leading indicators), provide your trading decision for NDX in the following JSON format:
    {
      "NDX": {"decision": "BUY|SELL|HOLD", "reasoning": "...", "confidence": 0.X}
    }
    """
    log.debug("Master prompt constructed.")
    return prompt
