# main.py (Final Version with all improvements)

import os
import sys
import argparse  # <-- IMPORT ARGPARSE
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from utils.quiz_scraper import QuizScraper
import utils.data_utils as data
import utils.ai_utils as ai


def main():
    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(
        description="A script to scrape and automatically answer Moodle quizzes using the Gemini API."
    )
    parser.add_argument("url", help="The full URL of the Moodle quiz to start.")
    args = parser.parse_args()

    # --- Load Configuration ---
    load_dotenv()

    # The URL now comes from the command-line argument
    url = args.url

    username = os.environ.get("SELENIUM_USERNAME")
    password = os.environ.get("SELENIUM_PASSWORD")
    binary_location = os.environ.get("BROWSER_BINARY_LOCATION")
    gemini_api_key = os.environ.get("GEMINI_API_KEY")

    # Get the Gemini model from .env, with a fallback default
    gemini_model = os.environ.get("GEMINI_MODEL", "gemini-pro")

    # --- Pre-run Checks ---
    if not all([username, password, gemini_api_key]):
        print(
            "Error: Ensure SELENIUM_USERNAME, SELENIUM_PASSWORD, and GEMINI_API_KEY are set in your .env file."
        )
        sys.exit(1)

    # --- Main Logic ---
    try:
        options = Options()
        options.add_argument("--start-minimized")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        if binary_location:
            options.binary_location = binary_location

        with webdriver.Chrome(options=options) as driver:
            print("Starting the quiz scraper...")
            qz = QuizScraper(driver, url, username, password)
            qz_title = qz.get_title()

            print(f"Successfully scraped quiz title: {qz_title}")
            print("Fetching all quiz questions...")
            qz_quizzes = qz.get_quizzes()

            # Call the AI utility, passing the model name
            ai_generated_answers = ai.get_gemini_answers(
                qz_quizzes, gemini_api_key, gemini_model
            )

            answer_file_path = os.path.join("quiz", f"{qz_title}_ai_answers.json")
            data.store_dictionary_as_json(
                f"{qz_title}_ai_answers", ai_generated_answers, "quiz"
            )
            print(f"AI-generated answers have been saved to {answer_file_path}")

            final_answers = {int(k): v for k, v in ai_generated_answers.items()}

            print("Now, answering the quizzes with Gemini's responses...")
            qz.answer_quizzes(final_answers)

            print(
                "\nProcess completed. The script has selected the answers provided by the Gemini API."
            )
            print(
                "Please review the answers on the webpage before manually submitting the quiz."
            )

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(f"\n--- AN ERROR OCCURRED ---")
        print(f"Exception type: {exc_type}")
        print(f"File name: {fname}")
        print(f"Line number: {exc_tb.tb_lineno}")
        print(f"Exception message: {str(e)}")


if __name__ == "__main__":
    main()
