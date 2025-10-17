# main.py

import argparse
import json
import os
import sys
import time
from datetime import datetime

from dotenv import load_dotenv
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options

import utils.ai_utils as ai
from utils.quiz_scraper import QuizScraper

CACHE_DIR = "cache"


def handle_dry_run(username, password, binary_location, gemini_api_key, gemini_model):
    print("--- Starting Dry Run (Default Mode) ---")
    driver = None
    try:
        options = Options()
        options.add_argument("--headless")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        if binary_location:
            options.binary_location = binary_location
        driver = webdriver.Chrome(options=options)
        QuizScraper(driver, "https://v-class.gunadarma.ac.id/my/", username, password)
        print("Moodle Login Check: SUCCESS")
    except Exception as e:
        print("Moodle Login Check: FAILED")
        print(f"  > Error Message: {e}")
    finally:
        if driver:
            driver.quit()
    if gemini_api_key:
        ai.test_gemini_api(gemini_api_key, gemini_model)
    else:
        print("\n--- Testing Gemini API Connection ---")
        print("Skipped: GEMINI_API_KEY not found in .env file.")
    print("\n--- Dry Run Complete ---")
    print("To run the full script, provide a URL with the --url flag.")


def main():
    parser = argparse.ArgumentParser(
        description="A script to scrape and/or answer Moodle quizzes."
    )
    parser.add_argument("--url", help="URL kuis untuk memulai proses penuh.")
    parser.add_argument(
        "--answer-file",
        help="Path ke file JSON kunci jawaban untuk langsung mengisi kuis.",
    )
    parser.add_argument(
        "--scrape-only",
        action="store_true",
        help="Hanya scrape pertanyaan; jangan jawab.",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Paksa scrape baru dan abaikan data cache.",
    )
    args = parser.parse_args()

    load_dotenv()
    username = os.environ.get("SELENIUM_USERNAME")
    password = os.environ.get("SELENIUM_PASSWORD")
    binary_location = os.environ.get("BROWSER_BINARY_LOCATION")
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    gemini_model = os.environ.get("GEMINI_MODEL", "gemini-pro")

    if not all([username, password]):
        print("Error: Pastikan SELENIUM_USERNAME dan SELENIUM_PASSWORD ada di .env.")
        sys.exit(1)
    if not args.url and not args.answer_file:
        handle_dry_run(
            username, password, binary_location, gemini_api_key, gemini_model
        )
        sys.exit(0)
    if not args.url and (args.scrape_only or not args.answer_file):
        print("Error: Argumen --url diperlukan untuk mode ini.")
        sys.exit(1)

    driver = None
    is_successful = False
    try:
        options = Options()
        options.add_argument("--start-maximized")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        if binary_location:
            options.binary_location = binary_location
        driver = webdriver.Chrome(options=options)

        quiz_url = args.url if args.url else "https://v-class.gunadarma.ac.id/my/"
        try:
            qz = QuizScraper(driver, quiz_url, username, password)
        except ValueError as e:
            print(f"\nError: Inisialisasi scraper gagal. {e}")
            sys.exit(1)

        qz_title = qz.get_sanitized_title()
        quiz_id = qz.quiz_id

        cache_filename = (
            f"{qz_title}_{quiz_id}_questions.json"
            if quiz_id
            else f"{qz_title}_questions.json"
        )
        cache_file = os.path.join(CACHE_DIR, cache_filename)

        answers_to_fill = {}

        if args.answer_file:
            print(f"Mode Kunci Jawaban: Memuat jawaban dari '{args.answer_file}'...")
            with open(args.answer_file, "r") as f:
                loaded_answers = json.load(f)
            for num, data in loaded_answers.items():
                answers_to_fill[num] = list(data.values())[0]
        else:
            os.makedirs(CACHE_DIR, exist_ok=True)
            qz_quizzes = None
            if os.path.exists(cache_file) and not args.no_cache:
                print(f"Cache ditemukan! Memuat pertanyaan dari '{cache_file}'...")
                with open(cache_file, "r") as f:
                    qz_quizzes = json.load(f)
            else:
                print(
                    "Cache tidak ditemukan atau --no-cache digunakan. Memulai scraping baru..."
                )
                qz_quizzes = qz.fetch_all_quizzes()
                with open(cache_file, "w") as f:
                    json.dump(qz_quizzes, f, indent=2)
                print(
                    f"Pertanyaan berhasil di-scrape dan disimpan ke cache: '{cache_file}'"
                )

            questions_for_ai = {}
            skipped_questions = []
            for num, data in qz_quizzes.items():
                if data.get("has_image", False):
                    skipped_questions.append(int(num))
                else:
                    questions_for_ai[int(num)] = {
                        "question_text": data["question_text"],
                        "answers": data["answers"],
                    }

            if skipped_questions:
                print(
                    f"\nPeringatan: Soal nomor {', '.join(map(str, skipped_questions))} dilewati karena mengandung gambar."
                )

            if not args.scrape_only and gemini_api_key and questions_for_ai:
                answers_from_ai = ai.get_gemini_answers(
                    questions_for_ai, gemini_api_key, gemini_model
                )
                if answers_from_ai:
                    run_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    output_dir_name = (
                        f"{qz_title}_{quiz_id}_{run_timestamp}"
                        if quiz_id
                        else f"{qz_title}_{run_timestamp}"
                    )
                    output_dir = os.path.join("output", output_dir_name)
                    os.makedirs(output_dir, exist_ok=True)

                    shareable_answers = {}
                    for num_str, answer_text in answers_from_ai.items():
                        question_text = questions_for_ai[int(num_str)]["question_text"]
                        shareable_answers[num_str] = {question_text: answer_text}

                    shareable_filename = (
                        f"{qz_title}_{quiz_id}_SHAREABLE_ANSWERS.json"
                        if quiz_id
                        else f"{qz_title}_SHAREABLE_ANSWERS.json"
                    )
                    shareable_file_path = os.path.join(output_dir, shareable_filename)
                    with open(shareable_file_path, "w") as f:
                        json.dump(shareable_answers, f, indent=2)
                    print(
                        f"Kunci Jawaban yang bisa dibagikan disimpan di: '{shareable_file_path}'"
                    )
                    answers_to_fill = answers_from_ai
                else:
                    print("Gagal mendapatkan jawaban dari AI.")
            elif args.scrape_only:
                print("\nMode --scrape-only. Proses selesai.")
                is_successful = True
            elif not questions_for_ai:
                print("\nTidak ada pertanyaan berbasis teks yang bisa dijawab oleh AI.")
            else:
                print("\nAPI key Gemini tidak ditemukan.")
                is_successful = True

        if answers_to_fill:
            qz.answer_quizzes(answers_to_fill)
            is_successful = True
            print(
                "\n--------------------------------------------------------------------"
            )
            print("Semua jawaban telah terisi. Anda dapat meninjau jawaban di browser.")
            print(
                "Skrip akan berhenti secara otomatis setelah Anda menutup jendela browser."
            )
            print(
                "--------------------------------------------------------------------"
            )
            while True:
                try:
                    if not driver.window_handles:
                        print("\nBrowser ditutup oleh pengguna. Skrip selesai.")
                        break
                    time.sleep(1)
                except (WebDriverException, ConnectionRefusedError):
                    print("\nKoneksi ke browser terputus. Skrip selesai.")
                    break
        else:
            if not args.scrape_only:
                print("Tidak ada jawaban untuk diisi. Proses selesai.")
    except Exception:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print("\n--- TERJADI ERROR TAK TERDUGA ---")
        print(f"  - Tipe: {exc_type.__name__}")
        print(f"  - File: {fname} (Baris: {exc_tb.tb_lineno})")
        print(f"  - Pesan: {str(exc_obj)}")
    finally:
        if driver and not is_successful:
            print("Menutup WebDriver karena proses tidak selesai atau terjadi error...")
            driver.quit()


if __name__ == "__main__":
    main()
