# src/llm_agent.py
#TODO prompt
import pandas as pd
import json
from datetime import timedelta


# (Your code to import GEMINI_API_KEY from config.py
# and initialize the model will go here)
# import google.generativeai as genai
# from config import GEMINI_API_KEY
# genai.configure(api_key=GEMINI_API_KEY)
# model = genai.GenerativeModel('gemini-1.5-flash-latest')


def create_prompt(current_date, current_portfolio, market_data, news_data, tickers_list):
    """
    Combines all data for a specific day to create
    the main prompt that will be sent to the LLM.

    Args:
        current_date (datetime): The current day in the simulation.
        current_portfolio (dict): The agent's current cash and holdings.
        market_data (DataFrame): ALL market data.
        news_data (DataFrame): ALL news data.
        tickers_list (list): The list of stocks to be traded (e.g., ['AAPL', 'MSFT']).
    """

    # --- 1. Format Portfolio Information ---
    portfolio_str = json.dumps(current_portfolio, indent=2)

    # --- 2. Filter Market Data for the Day ---
    try:
        # We can easily select the day using .loc since 'date' is the index
        # We must filter market_data for the relevant tickers first
        market_data_today = market_data[market_data['symbol'].isin(tickers_list)]
        market_data_today = market_data_today.loc[current_date.strftime('%Y-%m-%d')]
        market_str = market_data_today.to_string()
    except KeyError:
        market_str = "No market data found for today."
    except Exception as e:
        market_str = f"Error retrieving market data: {e}"

    # --- 3. Filter News for the Day (Last 24 hours) ---
    start_time = current_date - timedelta(days=1)
    end_time = current_date

    # Filter by time AND relevant tickers
    todays_news = news_data[
        (news_data['published_at'] >= start_time) &
        (news_data['published_at'] < end_time) &
        (news_data['symbol'].isin(tickers_list))  # Only show news for our target stocks
        ]

    news_str = ""
    if todays_news.empty:
        news_str = "No relevant news found for the target stocks in the last 24 hours."
    else:
        # Let's just get the summary and headline
        for index, row in todays_news.iterrows():
            news_str += f"- Ticker: {row['symbol']}\n  Headline: {row['headline']}\n  Summary: {row['summary']}\n\n"

    # --- 4. Dynamically Create the Desired JSON Format Example ---
    json_format_example = "{\n"
    # Show NASDAQ tickers as an example
    example_tickers = [t for t in tickers_list if t in ['AAPL', 'MSFT', 'NVDA']]
    if not example_tickers:
        example_tickers = tickers_list[:3]  # Fallback to first 3

    for ticker in example_tickers:
        json_format_example += f'  "{ticker}": "decision",\n'
    json_format_example += "  ...\n}"

    # --- 5. Combine All Parts into the Final Prompt ---
    prompt = f"""
    You are an expert investment analyst agent specializing in the US NASDAQ market, analyzing quantitative and qualitative data. Your task is to make logical trading decisions based on the current data provided to you.

    ---
    1. CURRENT PORTFOLIO STATUS:
    (Cash in USD and number of shares owned)
    {portfolio_str}

    ---
    2. TODAY'S MARKET DATA (Opening Prices, P/E Ratios, etc.):
    {market_str}

    ---
    3. RELEVANT MARKET NEWS (LAST 24 HOURS):
    {news_str}
    ---

    TASK:
    Analyze all the data above as a whole. Make a rational decision for each stock in the target list: {tickers_list}.

    Decisions can be:
    - "increase": Increase the position (Buy)
    - "decrease": Decrease the position (Sell)
    - "hold": Maintain the position (Do nothing)

    Please provide your response ONLY and EXACTLY in the following JSON format, with no additional explanations:

    {json_format_example}
    """

    return prompt


def get_llm_decisions(prompt, tickers_list):
    """
    (This is your function that calls the LLM API)
    It takes the generated prompt, sends it to the API, and returns the JSON response.
    """
    print("   Consulting LLM Agent for decisions...")
    try:
        # response = model.generate_content(...) # ACTUAL API CALL

        # --- DUMMY RESPONSE FOR TESTING ---
        # To avoid using the real API during testing, let's return a fake (dummy) response
        import random
        fake_response = {ticker: random.choice(['increase', 'decrease', 'hold']) for ticker in tickers_list}
        print(f"   Agent's Decision (Dummy): {fake_response}")
        return fake_response
        # --- DELETE DUMMY CODE AND RETURN ACTUAL RESPONSE ---
        # return json.loads(response.text)

    except Exception as e:
        print(f"   ERROR: LLM API call failed: {e}")
        # In case of an error, 'hold' all positions to prevent risk
        return {ticker: 'hold' for ticker in tickers_list}