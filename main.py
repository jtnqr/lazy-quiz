import json
import os
import sys
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from utils.quiz_scraper import QuizScraper
import utils.data_utils as data
import utils.ai_utils as ai  # <-- IMPORT THE NEW AI UTILS

# Load environment variables from a .env file
load_dotenv()

# Define the URL and credentials using environment variables
url = os.environ.get("URL")
username = os.environ.get("SELENIUM_USERNAME")
password = os.environ.get("SELENIUM_PASSWORD")
binary_location = os.environ.get("BROWSER_BINARY_LOCATION")
gemini_api_key = os.environ.get("GEMINI_API_KEY")  # <-- GET THE NEW API KEY

# Configure Chrome WebDriver options
options = Options()
options.add_argument("--start-minimized")
options.add_experimental_option("excludeSwitches", ["enable-logging"])
options.binary_location = binary_location

# Check if the Gemini API key is provided
if not gemini_api_key:
    print("Error: GEMINI_API_KEY not found in .env file. Please add it.")
    sys.exit(1)

try:
    # Create a Chrome WebDriver instance using a context manager
    with webdriver.Chrome(options=options) as driver:
        # Create a QuizScraper instance
        print("Starting the quiz scraper...")
        qz = QuizScraper(driver, url, username, password)
        qz_title = qz.get_title()

        print(f"Successfully scraped quiz title: {qz_title}")
        print("Fetching all quiz questions...")
        qz_quizzes = qz.get_quizzes()

        # --- NEW LOGIC: USE AI TO GET ANSWERS ---
        # Instead of looking for a local answers file, we call the Gemini API
        ai_generated_answers = ai.get_gemini_answers(qz_quizzes, gemini_api_key)

        # You can optionally save the AI's answers for review
        answer_file_path = os.path.join("quiz", f"{qz_title}_ai_answers.json")
        data.store_dictionary_as_json(
            f"{qz_title}_ai_answers", ai_generated_answers, "quiz"
        )
        print(f"AI-generated answers have been saved to {answer_file_path}")

        # --- USE THE AI ANSWERS TO ANSWER THE QUIZ ---
        # The keys in ai_generated_answers need to be integers for your __answer_quiz method
        # Let's ensure they are correct.
        final_answers = {int(k): v for k, v in ai_generated_answers.items()}

        print("Now, answering the quizzes with Gemini's responses...")
        # Note: This will interact with the webpage, selecting the answers.
        # It does NOT submit the final quiz.
        qz.answer_quizzes(final_answers)

        print(
            "\nProcess completed. The script has selected the answers provided by the Gemini API."
        )
        print(
            "Please review the answers on the webpage before manually submitting the quiz."
        )

except Exception as e:
    # Handle exceptions gracefully
    exc_type, exc_obj, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    print(f"\n--- AN ERROR OCCURRED ---")
    print(f"Exception type: {exc_type}")
    print(f"File name: {fname}")
    print(f"Line number: {exc_tb.tb_lineno}")
    print(f"Exception message: {str(e)}")
