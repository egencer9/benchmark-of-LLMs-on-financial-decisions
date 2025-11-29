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
          "AAPL": {"decision": "HOLD", "reasoning": "Dummy response: Market is stable, holding position.", "confidence": 0.7},
          "MSFT": {"decision": "BUY", "reasoning": "Dummy response: Positive news indicates potential growth.", "confidence": 0.6},
          "NVDA": {"decision": "SELL", "reasoning": "Dummy response: Stock appears overbought.", "confidence": 0.5},
          "TSLA": {"decision": "HOLD", "reasoning": "Dummy response: High volatility, waiting for clearer signals.", "confidence": 0.8},
          "AMZN": {"decision": "BUY", "reasoning": "Dummy response: Strong fundamentals and recent positive news.", "confidence": 0.75}
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
        return None # Indicate failure

def construct_master_prompt(portfolio, market_data, news_summaries):
    """
    Constructs the single master prompt for the LLM, aggregating all data.
    """
    log.debug("Constructing master prompt...")
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
    Based on all the information above, provide your trading decisions for all stocks in the following JSON format:
    {
      "TICKER1": {"decision": "BUY|SELL|HOLD", "reasoning": "...", "confidence": 0.X},
      "TICKER2": {"decision": "BUY|SELL|HOLD", "reasoning": "...", "confidence": 0.X},
      ...
    }
    """
    log.debug("Master prompt constructed.")
    return prompt
