import google.generativeai as genai
import time

def get_gemini_answers(quizzes: dict, api_key: str):
    """
    Uses the Gemini API to generate answers for a dictionary of quizzes.

    Args:
        quizzes (dict): The dictionary of scraped quizzes.
        api_key (str): Your Gemini API key.

    Returns:
        dict: A dictionary of {question_number: answer_text} suitable for the QuizScraper.
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro')

    ai_answers = {}
    print("--- Contacting Gemini API for answers ---")

    # The quiz dictionary is structured as: {1: {"Question Text 1": ["Opt A", "Opt B"]}, 2: ...}
    for num, question_data in quizzes.items():
        # Unpack the question text and answer options from the inner dictionary
        question_text, options = list(question_data.items())[0]
        
        # --- This is the Prompt Engineering part ---
        # We give the AI clear instructions to ensure it returns the answer
        # in a format we can easily parse.
        prompt = f"""
        You are an expert answering a multiple-choice quiz.
        Based on the following question and options, please return only the exact text of the most likely correct answer.
        Do not add any explanation, punctuation, or any other text. Just return the answer string.

        Question: "{question_text}"

        Options:
        - {"\n- ".join(options)}

        Correct Answer Text:
        """

        try:
            print(f"Asking Gemini about Question {num}...")
            response = model.generate_content(prompt)
            
            # The response.text will contain the AI's chosen answer
            chosen_answer = response.text.strip()
            
            # Basic validation to see if the AI's answer is one of the options
            if chosen_answer in options:
                print(f"  > Gemini chose: '{chosen_answer}'")
                ai_answers[num] = chosen_answer
            else:
                # If Gemini returns something unexpected, we can log it and maybe default to the first option
                print(f"  > Warning: Gemini returned an answer ('{chosen_answer}') not in the provided options. Defaulting to the first option.")
                ai_answers[num] = options[0] if options else ""

            # Be a good citizen and don't spam the API too quickly
            time.sleep(1) 

        except Exception as e:
            print(f"An error occurred while calling the Gemini API for question {num}: {e}")
            # If the API fails, we can skip this question or provide a default
            ai_answers[num] = ""

    print("--- Finished getting answers from Gemini ---")
    return ai_answers
