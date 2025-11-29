import requests
import json
from dotenv import load_dotenv
import os


from Util.utils import read_yaml

# Note: 'import yaml' is no longer needed here

load_dotenv()
OPEN_ROUTER_KEY = os.getenv('OPEN_ROUTER_KEY')

# --- 2. Load the model name from the config file ---
try:
    config = read_yaml('../config.yaml')  # <-- 3. Use the new function
    model_name = config['model'][1]  # <-- 4. Get the model key

except FileNotFoundError:
    print("Error: config.yaml not found.")
    exit()
except KeyError:
    print("Error: 'model' key not found in config.yaml.")
    exit()
except Exception as e:
    # This will catch YAML parsing errors or other issues
    print(f"An error occurred loading config: {e}")
    exit()
# ----------------------------------------------------


if not OPEN_ROUTER_KEY:
    print("Error: OPEN_ROUTER_KEY not found. Check your .env file.")
else:
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPEN_ROUTER_KEY}",
                "Content-Type": "application/json"
            },
            data=json.dumps({
                "model": model_name,  # <-- 5. The variable is used here
                "messages": [
                    {
                        "role": "user",
                        "content": "What is the meaning of life?"
                    }
                ],
            })
        )

        response.raise_for_status()

        # Print just the message content
        json_response = response.json()
        message_content = json_response['choices'][0]['message']['content']
        print(message_content)

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        print(f"Response content: {response.text}")
    except Exception as err:
        print(f"An error occurred: {err}")