import google.generativeai as genai
import time
from google.api_core import exceptions


def get_gemini_answers(quizzes: dict, api_key: str, model_name: str):
    """
    Uses the Gemini API to generate answers for a dictionary of quizzes.
    Includes retry logic to handle API rate limiting and model not found errors.
    """
    genai.configure(api_key=api_key)
    try:
        model = genai.GenerativeModel(model_name)
    except exceptions.NotFound:
        print(
            f"Gemini API Error: Model '{model_name}' not found. Please check the model name in your .env file."
        )
        return {}  # Return empty dict to stop the process

    ai_answers = {}
    print(f"--- Contacting Gemini API using model '{model_name}' for answers ---")

    for num, question_data in quizzes.items():
        question_text, options = list(question_data.items())[0]

        formatted_options = "\n- ".join(options)

        prompt = f"""
        You are an expert answering a multiple-choice quiz.
        Based on the following question and options, please return only the exact text of the most likely correct answer.
        Do not add any explanation, punctuation, or any other text. Just return the answer string.

        Question: "{question_text}"

        Options:
        - {formatted_options}

        Correct Answer Text:
        """

        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"Asking Gemini about Question {num} (Attempt {attempt + 1})...")
                response = model.generate_content(prompt)

                chosen_answer = response.text.strip()

                if chosen_answer in options:
                    print(f"  > Gemini chose: '{chosen_answer}'")
                    ai_answers[num] = chosen_answer
                else:
                    print(
                        f"  > Warning: Gemini returned an answer ('{chosen_answer}') not in the options. Defaulting to first option."
                    )
                    ai_answers[num] = options[0] if options else ""

                time.sleep(1)  # Be a good citizen
                break

            except exceptions.ResourceExhausted:
                wait_time = 30
                print(
                    f"  > Rate limit hit. Pausing for {wait_time} seconds before retrying..."
                )
                time.sleep(wait_time)

            except Exception as e:
                print(f"  > An unexpected API error occurred: {e}")
                ai_answers[num] = ""
                break
        else:
            print(
                f"  > Failed to get an answer for question {num} after {max_retries} attempts."
            )
            ai_answers[num] = ""

    print("--- Finished getting answers from Gemini ---")
    return ai_answers


def test_gemini_api(api_key: str, model_name: str) -> bool:
    """
    Performs a simple API call to check if the Gemini API key and model are valid.
    """
    print("\n--- Testing Gemini API Connection ---")
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(
            "This is a test. Respond with the single word: OK"
        )

        if "OK" in response.text:
            print("Gemini API Check: SUCCESS - Received a valid response.")
            return True
        else:
            print(
                "Gemini API Check: WARNING - Connection worked, but received an unexpected response."
            )
            return True

    except exceptions.PermissionDenied:
        print(
            "Gemini API Check: FAILED - Permission Denied. Your API key is likely invalid or has been revoked."
        )
        return False
    # --- THIS IS THE CORRECTED LINE ---
    except exceptions.NotFound:
        print(
            f"Gemini API Check: FAILED - Model '{model_name}' not found. Check the model name in your .env file."
        )
        return False
    except Exception as e:
        print(f"Gemini API Check: FAILED - An unexpected error occurred: {e}")
        return False
