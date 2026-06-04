import sys
import os

# Add the project root to the Python path to allow importing from 'src'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.llm_agent import get_llm_decision
from src.logger import log
from config import LLM_PROVIDER

def run_demo():
    """
    A simple demonstration script to test the LLM provider configured for the project.
    """
    log.info("--- LLM Provider Demo ---")
    log.info(f"Using configured LLM Provider: {LLM_PROVIDER.upper()}")

    # A simple, non-financial prompt to test the connection and response.
    test_prompt = "Explain how AI works in a few words."

    log.info(f"Sending the following prompt to the LLM:\n---_n{test_prompt}\n---")

    # Use the same function as the backtester to get the LLM decision.
    # This ensures we are testing the exact same logic.
    response = get_llm_decision(test_prompt, [])

    if response:
        log.info("Received response from LLM:")
        # Use the logger to print the response.
        # The logger will handle multi-line printing gracefully.
        log.info(f"\n---\n{response}\n---")
    else:
        log.error("Did not receive a valid response from the LLM.")

if __name__ == "__main__":
    run_demo()
