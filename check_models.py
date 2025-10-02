import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get your API key from the environment
API_KEY = os.environ.get("GEMINI_API_KEY")

if not API_KEY:
    print("Error: GEMINI_API_KEY not found in .env file.")
else:
    try:
        genai.configure(api_key=API_KEY)

        print("--- Finding Available Gemini Models ---")
        print(
            "The following models support the 'generateContent' method and should work with your script:"
        )

        found_model = False
        for model in genai.list_models():
            # The script uses the 'generateContent' method, so we check for that support.
            if "generateContent" in model.supported_generation_methods:
                print(f"  - {model.name}")
                found_model = True

        if not found_model:
            print("\nCould not find any models that support 'generateContent'.")
            print("This is unusual. Consider the following:")
            print("1. Your API key may have restrictions.")
            print("2. You might be in a region with limited model access.")
            print(
                "3. Try generating a new API key in a new project in Google AI Studio."
            )

    except Exception as e:
        print(f"\nAn error occurred while trying to connect to the API: {e}")
        print(
            "Please check that your GEMINI_API_KEY in the .env file is correct and has no extra characters."
        )
