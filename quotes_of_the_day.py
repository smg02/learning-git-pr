import os
import sys
from dotenv import load_dotenv
from google import genai

# 1. Load variables from your local .env or GitHub Action environment
load_dotenv()

# 2. Get the key matching your GitHub secret name
api_key = os.environ.get("AI_API_KEY")

if not api_key:
    print("Error: AI_API_KEY environment variable is not set.")
    sys.exit(1)

try:
    # 3. Initialize the official Google GenAI Client with your key
    client = genai.Client(api_key=api_key)

    # 4. Generate the quotes using the current active Gemini 3.5 model
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents="Generate 3 short, punchy quotes about automation.",
    )
    
    print("Gemini API Connection Successful!\n")
    print("Generated Quotes:")
    print(response.text)

except Exception as e:
    print(f"Gemini API Error: {e}")
