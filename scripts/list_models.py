import google.generativeai as genai
import os
import sys

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import GEMINI_API_KEY

if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY not found in config.")
    sys.exit(1)

genai.configure(api_key=GEMINI_API_KEY)

print("Listing available models...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- Name: {m.name}")
            print(f"  DisplayName: {m.display_name}")
            print(f"  Description: {m.description}")
            print("-" * 20)
except Exception as e:
    print(f"Error listing models: {e}")
