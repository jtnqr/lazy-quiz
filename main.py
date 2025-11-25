# main.py

import argparse
import json
import os
import sys
from datetime import datetime

from dotenv import load_dotenv

import utils.ai_utils as ai
from utils.quiz_scraper import QuizScraper

CACHE_DIR = "cache"


def handle_dry_run(username, password, gemini_api_key, gemini_model):
    print("--- Starting Dry Run (HTTP Mode) ---")

    print("\n--- Testing Moodle Login ---")
    try:
        # Gunakan string kosong untuk tes login saja tanpa akses kuis
        QuizScraper("", username, password)
        print("Moodle Login Check: SUCCESS")
    except Exception as e:
        print("Moodle Login Check: FAILED")
        print(f"  > Error Message: {e}")

    if gemini_api_key:
        ai.test_gemini_api(gemini_api_key, gemini_model)
    else:
        print("\n--- Testing Gemini API Connection ---")
        print("Skipped: GEMINI_API_KEY not found in .env file.")
    print("\n--- Dry Run Complete ---")


def run_quiz_process(
    quiz_url: str, args, username, password, gemini_api_key, gemini_model
):
    try:
        # Inisialisasi Scraper
        qz = QuizScraper(quiz_url, username, password)

        qz_title = qz.get_sanitized_title()
        quiz_id = qz.quiz_id

        # Penamaan File Cache
        cache_filename = (
            f"{qz_title}_{quiz_id}_questions.json"
            if quiz_id
            else f"{qz_title}_questions.json"
        )
        cache_file = os.path.join(CACHE_DIR, cache_filename)

        answers_to_fill = {}
        shareable_path = None

        # 1. LOGIKA LOAD JAWABAN (Manual File / AI)
        if args.answer_file:
            print(f"Mode Kunci Jawaban: Memuat jawaban dari '{args.answer_file}'...")
            with open(args.answer_file, "r") as f:
                loaded_answers = json.load(f)
            # Normalisasi format json
            for num, data in loaded_answers.items():
                val = data if isinstance(data, str) else list(data.values())[0]
                answers_to_fill[num] = val
        else:
            os.makedirs(CACHE_DIR, exist_ok=True)
            qz_quizzes = None

            # Cek Cache Lokal
            if os.path.exists(cache_file) and not args.no_cache:
                print(f"Cache ditemukan! Memuat pertanyaan dari '{cache_file}'...")
                with open(cache_file, "r") as f:
                    qz_quizzes = json.load(f)

                qz.set_quiz_data(qz_quizzes)
            else:
                print("Cache tidak tersedia/diabaikan. Memulai scraping baru...")
                qz_quizzes = qz.fetch_all_quizzes()
                with open(cache_file, "w") as f:
                    json.dump(qz_quizzes, f, indent=2)
                print(f"Pertanyaan disimpan ke cache: '{cache_file}'")

            # Persiapan Data untuk AI
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
                    f"\nPeringatan: Soal {skipped_questions} dilewati (mengandung gambar)."
                )

            # Panggil AI
            if not args.scrape_only and gemini_api_key and questions_for_ai:
                answers_from_ai = ai.get_gemini_answers(
                    questions_for_ai, gemini_api_key, gemini_model
                )

                if answers_from_ai:
                    # Simpan Hasil AI
                    run_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    output_dir = os.path.join("output", f"{qz_title}_{run_timestamp}")
                    os.makedirs(output_dir, exist_ok=True)

                    shareable_answers = {}
                    for num_str, answer_text in answers_from_ai.items():
                        q_text = questions_for_ai[int(num_str)]["question_text"]
                        shareable_answers[num_str] = {q_text: answer_text}

                    shareable_path = os.path.join(output_dir, "SHAREABLE_ANSWERS.json")
                    with open(shareable_path, "w") as f:
                        json.dump(shareable_answers, f, indent=2)

                    print(f"Kunci Jawaban disimpan di: '{shareable_path}'")
                    answers_to_fill = answers_from_ai
                else:
                    print("Gagal mendapatkan jawaban dari AI.")
            elif args.scrape_only:
                print("\nMode --scrape-only. Selesai.")
                return

        # 2. LOGIKA KONFIRMASI & PENGISIAN JAWABAN
        if answers_to_fill:
            current_attempt_url = qz.attempt_url if qz.attempt_url else quiz_url

            # 1. SELALU ISI JAWABAN (SAVE STATE)
            print("\n" + "=" * 60)
            print("MENGISI JAWABAN KE MOODLE (AUTO-FILL)...")
            print("=" * 60)
            qz.save_answers(answers_to_fill)
            print("\n✅ Jawaban telah terisi dan tersimpan di server.")
            print("   (Jika Anda membuka browser, jawaban sudah terpilih/Saved)")

            # 2. CEK AUTO SUBMIT
            if args.auto_submit:
                print("\n[Mode Auto-Submit] Melakukan Final Submit...")
                qz.submit_final()
            else:
                # 3. KONFIRMASI FINAL SUBMIT
                print("\n" + "-" * 60)
                print("KONFIRMASI FINAL SUBMIT")
                print("-" * 60)
                print(f"URL Kuis : {current_attempt_url}")
                print(
                    "Jawaban sudah diisi. Anda bisa merefresh browser untuk mengeceknya."
                )
                print(
                    "Apakah Anda ingin bot melakukan 'Submit all and finish' sekarang?"
                )

                choice = input("\nSubmit Kuis Sekarang? (y/N): ").strip().lower()
                if choice in ["y", "yes", "ya"]:
                    qz.submit_final()
                else:
                    print("\nOke. Kuis belum disubmit (tapi jawaban sudah tersimpan).")
                    print("Silakan buka browser dan submit manual jika sudah yakin.")

    except Exception as e:
        print("\n--- TERJADI ERROR ---")
        print(f"Message: {e}")
        import traceback

        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(description="Moodle Quiz Bot (Requests Version)")
    parser.add_argument("--url", help="URL kuis Moodle")
    parser.add_argument("--answer-file", help="Path file JSON jawaban")
    parser.add_argument(
        "--scrape-only", action="store_true", help="Hanya scrape, jangan jawab"
    )
    parser.add_argument("--no-cache", action="store_true", help="Abaikan cache lokal")
    parser.add_argument(
        "--auto-submit",
        action="store_true",
        help="Langsung submit jawaban tanpa konfirmasi user",
    )
    parser.add_argument("--dry-run", action="store_true", help="Tes koneksi login & AI")
    args = parser.parse_args()

    load_dotenv()
    username = os.environ.get("SELENIUM_USERNAME")
    password = os.environ.get("SELENIUM_PASSWORD")
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    gemini_model = os.environ.get("GEMINI_MODEL", "gemini-pro")

    if not all([username, password]):
        print("Error: Pastikan Username & Password ada di .env")
        sys.exit(1)

    if args.dry_run:
        handle_dry_run(username, password, gemini_api_key, gemini_model)
    elif args.url or args.answer_file:
        url = args.url if args.url else "https://v-class.gunadarma.ac.id/my/"
        run_quiz_process(url, args, username, password, gemini_api_key, gemini_model)
    else:
        print("--- Mode Interaktif ---")
        while True:
            raw_url = input("Masukkan URL Kuis: ")
            if "view.php" in raw_url or "attempt.php" in raw_url:
                run_quiz_process(
                    raw_url.strip(),
                    args,
                    username,
                    password,
                    gemini_api_key,
                    gemini_model,
                )
                break
            else:
                print("URL tidak valid. Harus mengandung 'view.php' atau 'attempt.php'")


if __name__ == "__main__":
    main()
