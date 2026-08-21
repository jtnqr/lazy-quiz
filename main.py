# main.py (Support Continuous Loop / Multi-Block Exam)
# Copyright (C) 2025 Julius W. (@jtnqr)

import json
import os
import time

import typer
from dotenv import load_dotenv

import utils.ai_utils as ai
from utils.logger import logger
from utils.scraper_exam import ExamScraper
from utils.scraper_moodle import MoodleScraper

# Create Typer app
app = typer.Typer(
    help="""
Lazy Quiz - Automated quiz solver using Playwright and Gemini/Groq AI.

Note: The 'run' command is executed by default if no command is specified.

Quick Example:
  uv run python main.py --url "<url>" --provider groq --auto-submit

Use 'main.py run --help' to see all available options and flags for the runner.
"""
)

CACHE_DIR = "cache"


def get_available_models(api_key: str, provider: str = "gemini") -> list:
    """Get list of available models for the given provider."""
    if provider.lower() == "groq":
        try:
            from groq import Groq
            client = Groq(api_key=api_key)
            models = client.models.list()
            return sorted([model.id for model in models.data])
        except Exception as e:
            logger.error(f"Failed to fetch Groq models: {e}")
            return []
    else:
        try:
            import google.generativeai as genai

            genai.configure(api_key=api_key)

            models = []
            for model in genai.list_models():
                if "generateContent" in model.supported_generation_methods:
                    models.append(model.name)
            return sorted(models)
        except Exception as e:
            logger.error(f"Failed to fetch Gemini models: {e}")
            return []


def prompt_model_selection(api_key: str, provider: str = "gemini") -> str:
    """Prompt user to select a model if not configured."""
    provider_name = "Groq" if provider.lower() == "groq" else "Gemini"
    default_model = "llama-3.3-70b-versatile" if provider.lower() == "groq" else "gemini-flash-latest"
    env_var_name = "GROQ_MODEL" if provider.lower() == "groq" else "GEMINI_MODEL"

    logger.info(f"{env_var_name} not configured in .env")
    logger.info("Fetching available models...")

    models = get_available_models(api_key, provider)

    if not models:
        logger.warning(f"No models found, using default: {default_model}")
        return default_model

    logger.info(f"\nAvailable {provider_name} models:")
    for i, model in enumerate(models, 1):
        logger.info(f"  {i}. {model}")

    # Prompt for selection
    while True:
        choice = typer.prompt("\nSelect model number (or press Enter for default)")

        if choice == "":
            logger.info(f"Using default: {default_model}")
            return default_model

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(models):
                selected = models[idx]
                logger.info(f"Selected: {selected}")
                return selected
            else:
                logger.warning(f"Invalid choice. Enter 1-{len(models)}")
        except ValueError:
            logger.warning("Invalid input. Enter a number or press Enter")


def get_scraper_class(url: str):
    """Detect scraper type based on platform indicators in URL"""
    # Check for ASP.NET indicators (.aspx extension, common ASP.NET patterns)
    if ".aspx" in url.lower():
        return ExamScraper
    # Default to Moodle (most common LMS)
    else:
        return MoodleScraper


def run_quiz_process(url, args, username, password, api_key, model, provider, vision_model, no_session: bool = False):
    qz = None
    try:
        # 1. Start Browser (Hanya sekali di awal)
        ScraperClass = get_scraper_class(url)
        logger.info(f"Initializing scraper: {ScraperClass.__name__}")

        # ExamScraper needs credentials for auto-captcha solving
        if ScraperClass == ExamScraper:
            qz = ScraperClass(url, username, password, api_key, vision_model, provider, no_session)
        else:
            qz = ScraperClass(url, username, password, no_session)

        part_counter = 1  # Untuk penamaan file cache per bagian (Bagian 1, 2, dst)

        # --- LOOP UTAMA (CONTINUOUS) ---
        while True:
            if hasattr(qz, "get_current_block"):
                real_part = qz.get_current_block()
                if real_part > 0:
                    part_counter = real_part
                    logger.info(f"Detected current section: Part {part_counter}")
            logger.info(f"\n>>> STARTING PROCESS: PART {part_counter} <<<")

            # Reset memori scraper agar bersih untuk bagian baru
            qz.reset_quiz_data()

            # Ambil Info Kuis
            qz_title = qz.get_sanitized_title()
            quiz_id = qz.quiz_id

            # Setup Cache Filenames (Pembeda per part)
            # Contoh: Quiz_ID_Part1_questions.json
            file_suffix = f"_Part{part_counter}"
            cache_file = os.path.join(
                CACHE_DIR, f"{qz_title}_{quiz_id}{file_suffix}_questions.json"
            )
            answer_cache_file = os.path.join(
                CACHE_DIR, f"{qz_title}_{quiz_id}{file_suffix}_answers.json"
            )

            answers_to_fill = {}
            qz_quizzes = {}

            # --- FASE 1: SCRAPING SOAL ---
            # Cek apakah ada cache lokal untuk PART ini
            if os.path.exists(cache_file) and not args.no_cache:
                logger.info(f"Questions cache found! Loading from '{cache_file}'...")
                with open(cache_file, "r") as f:
                    qz_quizzes = json.load(f)
                qz.set_quiz_data(qz_quizzes)
            else:
                # Scraping via Playwright
                # Jika ini loop kedua (Bagian 2), fetch_all_quizzes akan ambil soal baru
                qz_quizzes = qz.fetch_all_quizzes()

                # --- CHECKPOINT KELUAR LOOP ---
                if not qz_quizzes:
                    logger.info("\nNo more questions found on this page.")
                    logger.info("Likely all sections complete or on summary page.")
                    break  # KELUAR DARI LOOP WHILE

                os.makedirs(CACHE_DIR, exist_ok=True)
                with open(cache_file, "w") as f:
                    json.dump(qz_quizzes, f, indent=2)

            # --- FASE 2: LOAD JAWABAN (AI) ---
            if args.scrape_only:
                logger.info("--scrape-only mode active. Stopping here.")
                break

            questions_for_ai = {
                int(k): {"question_text": v["question_text"], "answers": v["answers"]}
                for k, v in qz_quizzes.items()
                if not v.get("has_image")
            }

            answers_from_ai = {}
            # Cek Cache Jawaban
            if os.path.exists(answer_cache_file) and not args.no_cache:
                logger.info(
                    f"Answers cache found! Loading from '{answer_cache_file}'..."
                )
                with open(answer_cache_file, "r") as f:
                    answers_from_ai = json.load(f)
            # Tanya AI
            elif api_key and questions_for_ai:
                answers_from_ai = ai.get_ai_answers(
                    questions_for_ai, api_key, model, provider
                )
                if answers_from_ai:
                    with open(answer_cache_file, "w") as f:
                        json.dump(answers_from_ai, f, indent=2)

            # --- FASE 2b: IMAGE QUESTIONS (Vision) ---
            image_questions = {
                k: v
                for k, v in qz_quizzes.items()
                if v.get("has_image") and v.get("image_data")
            }

            if image_questions and api_key:
                logger.info(
                    f"\n>>> Processing {len(image_questions)} IMAGE questions with {provider.capitalize()} Vision <<<"
                )
                for q_num, q_data in image_questions.items():
                    # Skip if already have answer
                    if str(q_num) in answers_from_ai:
                        continue

                    answer = ai.get_ai_answer_for_image(
                        question_number=str(q_num),
                        question_text=q_data.get("question_text", ""),
                        answers=q_data.get("answers", []),
                        image_data=q_data["image_data"],
                        api_key=api_key,
                        model_name=vision_model,
                        provider=provider,
                    )

                    if answer:
                        answers_from_ai[str(q_num)] = answer

            # Gabungkan jawaban
            answers_to_fill = answers_from_ai

            # --- FASE 3: PENGISIAN & SUBMIT ---
            if answers_to_fill:
                logger.info("=" * 40)
                logger.info(f"FILLING SECTION {part_counter}...")
                logger.info("=" * 40)

                filled_ids = qz.save_answers(answers_to_fill)

                # Statistik
                total_soal = len(qz_quizzes)
                total_terisi = len(filled_ids)
                total_gagal = total_soal - total_terisi
                logger.info(f"Statistics: {total_terisi}/{total_soal} Filled.")

                # Logic Konfirmasi
                do_submit = False
                if args.auto_submit:
                    do_submit = True
                else:
                    is_safe = total_gagal == 0
                    if is_safe:
                        if isinstance(qz, ExamScraper):
                            prompt = f"Semua soal Bagian {part_counter} terisi. Lanjut Submit & Next Bagian? (y/n): "
                        else:
                            prompt = f"Semua soal Bagian {part_counter} terisi. Siap Submit & Selesai? (y/n): "
                    else:
                        logger.warning(
                            f"⚠️  Warning: {total_gagal} questions empty in Part {part_counter}!"
                        )
                        prompt = "Paksa Submit & Lanjut? (ketik 'force' / 'n'): "

                    choice = input(prompt).strip().lower()
                    if (is_safe and choice in ["y", "yes"]) or choice == "force":
                        do_submit = True
                    else:
                        logger.info(
                            "User membatalkan submit. Bot berhenti (Session Browser tetap terbuka sebentar)."
                        )
                        break  # Stop loop

                if do_submit:
                    logger.info(f"\n[Action] Submitting Part {part_counter}...")
                    qz.submit_final()

                    if not isinstance(qz, ExamScraper):
                        logger.info("Quiz submitted. Process complete.")
                        break

                    # Beri waktu napas untuk loading halaman baru
                    logger.info("Waiting for next section to load...")
                    time.sleep(5)

                    # Increment counter untuk loop berikutnya
                    part_counter += 1
            else:
                logger.warning("No answers to fill.")
                break

        logger.info("\n=== ALL PROCESSES COMPLETE ===")

    except Exception as e:
        logger.error(f"\n--- ERROR OCCURRED ---: {e}")
        import traceback

        traceback.print_exc()
    finally:
        if qz:
            qz.close()


@app.command("run")
def run_command(
    url: str = typer.Option(None, "--url", help="Quiz URL to process"),
    scrape_only: bool = typer.Option(
        False, "--scrape-only", help="Only scrape questions, don't answer"
    ),
    no_cache: bool = typer.Option(False, "--no-cache", help="Ignore cached questions"),
    auto_submit: bool = typer.Option(
        False, "--auto-submit", help="Auto submit without confirmation"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Test connection only"),
    answer_file: str = typer.Option(
        None, "--answer-file", help="Use answers from JSON file"
    ),
    provider: str = typer.Option(
        None, "--provider", help="AI provider to use (gemini/groq). Overrides LLM_PROVIDER in .env."
    ),
    no_session: bool = typer.Option(
        False, "--no-session", help="Skip saved session, force fresh login"
    ),
):
    """
    Run the quiz automation (default command).

    Automatically solves quiz questions using Playwright and Gemini / Groq AI.
    """
    load_dotenv()
    moodle_username = os.environ.get("MOODLE_USERNAME")
    moodle_password = os.environ.get("MOODLE_PASSWORD")

    # LLM Provider selection
    if not provider:
        provider = os.environ.get("LLM_PROVIDER", "gemini").strip().lower()
    else:
        provider = provider.strip().lower()

    if provider == "groq":
        api_key = os.environ.get("GROQ_API_KEY")
        model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
        vision_model = os.environ.get("GROQ_VISION_MODEL", "llama-3.2-11b-vision-preview").strip()
        if not api_key:
            logger.error("GROQ_API_KEY not found in .env file.")
    else:
        provider = "gemini"
        api_key = os.environ.get("GEMINI_API_KEY")
        model = os.environ.get("GEMINI_MODEL", "").strip()
        # If model not configured, prompt for selection
        if not model and api_key:
            model = prompt_model_selection(api_key, "gemini")
        elif not model:
            # No API key, use default
            model = "gemini-flash-latest"
            logger.warning(f"Using default model: {model}")
        vision_model = model

    # Create args object for compatibility
    class Args:
        pass

    args = Args()
    args.scrape_only = scrape_only
    args.no_cache = no_cache
    args.auto_submit = auto_submit
    args.dry_run = dry_run
    args.answer_file = answer_file

    if url:
        run_quiz_process(
            url,
            args,
            moodle_username,
            moodle_password,
            api_key,
            model,
            provider,
            vision_model,
            no_session,
        )
    else:
        # Interactive mode
        raw_url = typer.prompt("Enter Quiz URL")
        if raw_url:
            run_quiz_process(
                raw_url.strip(),
                args,
                moodle_username,
                moodle_password,
                api_key,
                model,
                provider,
                vision_model,
                no_session,
            )


@app.command()
def test_login(
    url: str = typer.Option(None, "--url", help="Moodle/platform URL"),
    no_session: bool = typer.Option(
        False, "--no-session", help="Skip saved session, force fresh login"
    ),
):
    """Test Moodle/platform login credentials (opens browser)."""
    # Import and call the test_login script
    import sys

    sys.path.insert(0, "scripts")
    from test_login import test_login as run_test_login

    run_test_login(url, no_session=no_session)


@app.command()
def check_models(
    provider: str = typer.Option(None, "--provider", help="Provider to check (gemini/groq)"),
):
    """Check available AI models for your API key (Gemini or Groq)."""
    import sys
    import os
    if provider:
        os.environ["LLM_PROVIDER"] = provider
    sys.path.insert(0, "scripts")
    if "check_models" in sys.modules:
        import importlib
        importlib.reload(sys.modules["check_models"])
    else:
        import check_models


if __name__ == "__main__":
    # Make 'run' default if no command specified
    import sys

    commands = ["run", "test-login", "check-models"]
    has_command = any(cmd in sys.argv for cmd in commands)

    if not has_command and "--help" not in sys.argv and "-h" not in sys.argv:
        sys.argv.insert(1, "run")

    app()