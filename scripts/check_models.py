import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# We check both if they have keys configured in .env, otherwise fall back to LLM_PROVIDER
gemini_key = os.environ.get("GEMINI_API_KEY")
groq_key = os.environ.get("GROQ_API_KEY")

providers = []
if gemini_key:
    providers.append("gemini")
if groq_key:
    providers.append("groq")

# If no keys are found, fall back to LLM_PROVIDER or default to gemini
if not providers:
    active_provider = os.environ.get("LLM_PROVIDER", "gemini").strip().lower()
    providers = [active_provider]

for provider in providers:
    if provider == "groq":
        API_KEY = os.environ.get("GROQ_API_KEY")

        if not API_KEY:
            print("❌ Error: GROQ_API_KEY not found in .env file.")
        else:
            try:
                from groq import Groq
                client = Groq(api_key=API_KEY)

                print("\n--- Finding Available Groq Models ---")
                print(
                    "The following models support chat completions and should work with your script:"
                )

                models = client.models.list()
                found_model = False
                for model in sorted(models.data, key=lambda m: m.id):
                    print(f"  - {model.id}")
                    found_model = True

                if not found_model:
                    print("\n❌ Could not find any models.")

            except Exception as e:
                print(f"\n❌ An error occurred while trying to connect to the Groq API: {e}")
                print(
                    "Please check that your GROQ_API_KEY in the .env file is correct and has no extra characters."
                )
    else:
        import google.generativeai as genai
        API_KEY = os.environ.get("GEMINI_API_KEY")

        if not API_KEY:
            print("❌ Error: GEMINI_API_KEY not found in .env file.")
        else:
            try:
                genai.configure(api_key=API_KEY)

                print("\n--- Finding Available Gemini Models ---")
                print(
                    "The following models support the 'generateContent' method and should work with your script:"
                )

                found_model = False
                for model in genai.list_models():
                    if "generateContent" in model.supported_generation_methods:
                        print(f"  - {model.name}")
                        found_model = True

                if not found_model:
                    print("\n❌ Could not find any models that support 'generateContent'.")

            except Exception as e:
                print(f"\n❌ An error occurred while trying to connect to the Gemini API: {e}")
                print(
                    "Please check that your GEMINI_API_KEY in the .env file is correct and has no extra characters."
                )
    print("\n" + "-" * 50)

