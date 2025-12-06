import google.generativeai as genai
from openai import OpenAI # Correct import for modern client
from config import LLM_PROVIDER, GEMINI_API_KEY, OPENAI_API_KEY
from logger import log

# --- Client Initialization ---
gemini_client = None
openai_client = None

if LLM_PROVIDER == 'gemini':
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        # --- FIX: Update the model name ---
        gemini_client = genai.GenerativeModel('gemini-2.5-flash-lite')
        log.info("LLM Provider: Gemini. Client initialized with model 'gemini-2.5-flash-lite'.")
    else:
        log.warning("LLM_PROVIDER is 'gemini' but GEMINI_API_KEY is not set.")
elif LLM_PROVIDER == 'openai':
    if OPENAI_API_KEY:
        openai_client = OpenAI(api_key=OPENAI_API_KEY) # Correct client instantiation
        log.info("LLM Provider: OpenAI. Client initialized.")
    else:
        log.warning("LLM_PROVIDER is 'openai' but OPENAI_API_KEY is not set.")
else:
    log.warning(f"LLM_PROVIDER '{LLM_PROVIDER}' is not supported. Using dummy response mode.")


def get_llm_decision(prompt):
    """
    Gets trading decisions from the configured LLM provider.
    """
    if LLM_PROVIDER == 'gemini' and gemini_client:
        return _get_gemini_decision(prompt)
    elif LLM_PROVIDER == 'openai' and openai_client:
        return _get_openai_decision(prompt)
    else:
        log.warning(f"No valid LLM client initialized. Returning a dummy JSON response.")
        return _get_dummy_response()

def _get_gemini_decision(prompt):
    """Handles the API call to Google Gemini."""
    try:
        log.info("Sending prompt to Gemini API...")
        response = gemini_client.generate_content(prompt)
        log.info("Received response from Gemini API.")
        log.debug(f"Response content:\n{response.text}")
        return response.text
    except Exception as e:
        log.error(f"Error calling Gemini API: {e}", exc_info=True)
        return _get_dummy_response()

def _get_openai_decision(prompt):
    """Handles the API call to OpenAI using the modern client."""
    try:
        log.info("Sending prompt to OpenAI API...")
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a financial analyst providing responses in clean JSON format."},
                {"role": "user", "content": prompt}
            ]
        )
        log.info("Received response from OpenAI API.")
        decision = response.choices[0].message.content
        log.debug(f"Response content:\n{decision}")
        return decision
    except Exception as e:
        log.error(f"Error calling OpenAI API: {e}", exc_info=True)
        return _get_dummy_response()

def _get_dummy_response():
    """Returns a dummy JSON response for testing or in case of API failure."""
    return """
    {
      "AAPL": {"decision": "HOLD", "reasoning": "Dummy response: Market is stable.", "confidence": 0.7},
      "MSFT": {"decision": "BUY", "reasoning": "Dummy response: Positive news.", "confidence": 0.6},
      "NVDA": {"decision": "SELL", "reasoning": "Dummy response: Overbought.", "confidence": 0.5},
      "TSLA": {"decision": "HOLD", "reasoning": "Dummy response: Volatile.", "confidence": 0.8},
      "AMZN": {"decision": "BUY", "reasoning": "Dummy response: Strong fundamentals.", "confidence": 0.75}
    }
    """

def construct_master_prompt(portfolio, market_data, news_summaries):
    """
    Constructs the single master prompt for the LLM, aggregating all data.
    """
    # This function remains the same as it is provider-agnostic.
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
