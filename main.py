# main.py

import argparse
import json
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

import utils.ai_utils as ai
from utils.quiz_scraper import QuizScraper


def handle_dry_run(username, password, binary_location, gemini_api_key, gemini_model):
    print("--- Starting Dry Run (Default Mode) ---")
    print("\n--- Testing Moodle Login ---")
    try:
        options = Options()
        options.add_argument("--headless")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        if binary_location:
            options.binary_location = binary_location
        with webdriver.Chrome(options=options) as driver:
            QuizScraper(driver, "https://v-class.gunadarma.ac.id/", username, password)
        print("Moodle Login Check: SUCCESS")
    except Exception as e:
        print("Moodle Login Check: FAILED")
        print(
            "  > Details: Check SELENIUM_USERNAME and SELENIUM_PASSWORD in the .env file."
        )
        print(f"  > Error Message: {e}")
    if gemini_api_key:
        ai.test_gemini_api(gemini_api_key, gemini_model)
    else:
        print("\n--- Testing Gemini API Connection ---")
        print("Skipped: GEMINI_API_KEY not found in .env file.")
    print("\n--- Dry Run Complete ---")
    print("To run the full script, provide a URL with the --url flag.")


def main():
    parser = argparse.ArgumentParser(
        description="A script to scrape and/or answer Moodle quizzes. Runs a dry run by default."
    )
    parser.add_argument(
        "--url", help="The full URL of the Moodle quiz to start the full process."
    )
    parser.add_argument(
        "--scrape-only",
        action="store_true",
        help="Only scrape questions; do not answer. Requires --url.",
    )
    args = parser.parse_args()

    load_dotenv()
    username = os.environ.get("SELENIUM_USERNAME")
    password = os.environ.get("SELENIUM_PASSWORD")
    binary_location = os.environ.get("BROWSER_BINARY_LOCATION")
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    gemini_model = os.environ.get("GEMINI_MODEL", "gemini-pro")

    if not all([username, password]):
        print(
            "Error: Ensure SELENIUM_USERNAME and SELENIUM_PASSWORD are set in your .env file."
        )
        sys.exit(1)

    if not args.url:
        handle_dry_run(
            username, password, binary_location, gemini_api_key, gemini_model
        )
        sys.exit(0)

    print(f"URL provided. Starting full run for: {args.url}")
    try:
        options = Options()
        options.add_argument("--start-minimized")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        if binary_location:
            options.binary_location = binary_location

        with webdriver.Chrome(options=options) as driver:
            try:
                qz = QuizScraper(driver, args.url, username, password)
            except ValueError as e:
                print(f"\nError: Inisialisasi scraper gagal. {e}")
                sys.exit(1)

            qz_title = qz.get_sanitized_title()
            run_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            output_dir = os.path.join("output", f"{qz_title}_{run_timestamp}")
            os.makedirs(output_dir, exist_ok=True)
            print(f"Output will be saved in: '{output_dir}'")

            qz_quizzes = qz.fetch_all_quizzes()

            scraped_questions_path = os.path.join(output_dir, "scraped_questions.json")
            with open(scraped_questions_path, "w") as f:
                json.dump(qz_quizzes, f, indent=2)

            print(f"Successfully scraped {len(qz_quizzes)} questions.")
            print(f"Scraped questions saved to: '{scraped_questions_path}'")

            use_ai_to_answer = not args.scrape_only and gemini_api_key
            if use_ai_to_answer:
                print("\nGemini API key found. Proceeding to answer quizzes...")
                ai_generated_answers = ai.get_gemini_answers(
                    qz_quizzes, gemini_api_key, gemini_model
                )
                if ai_generated_answers:
                    ai_answers_path = os.path.join(output_dir, "ai_answers.json")
                    with open(ai_answers_path, "w") as f:
                        json.dump(ai_generated_answers, f, indent=2)
                    print(f"AI-generated answers saved to: '{ai_answers_path}'")
                    qz.answer_quizzes(ai_generated_answers)
                else:
                    print(
                        "Gagal mendapatkan jawaban dari AI. Proses menjawab dibatalkan."
                    )
            else:
                if args.scrape_only:
                    print("\nRunning in --scrape-only mode. Skipping answering phase.")
                else:
                    print(
                        "\nGEMINI_API_KEY not found in .env file. Skipping answering phase."
                    )

    except Exception:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print("\n--- AN UNEXPECTED ERROR OCCURRED ---")
        print(f"  - Type: {exc_type.__name__}")
        print(f"  - File: {fname} (Line: {exc_tb.tb_lineno})")
        print(f"  - Message: {str(exc_obj)}")


if __name__ == "__main__":
    main()
