# scripts/test_groq.py
"""
Simple script to test Groq API connectivity (text and vision).
"""

import io
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image, ImageDraw

# Add parent directory to path to import utils
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import logger
import utils.ai_utils as ai

# Load environment variables
load_dotenv()


def create_dummy_captcha_image() -> bytes:
    """Generate a simple dummy image containing text 'TEST12'."""
    img = Image.new("RGB", (150, 50), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    # Write some lines and text
    d.line([(0, 0), (150, 50)], fill=(0, 0, 0), width=2)
    d.text((50, 20), "TEST12", fill=(0, 0, 0))
    
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="PNG")
    return img_byte_arr.getvalue()


def test_groq():
    api_key = os.environ.get("GROQ_API_KEY")
    model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
    vision_model = os.environ.get("GROQ_VISION_MODEL", "llama-3.2-11b-vision-preview").strip()

    if not api_key:
        logger.error("❌ Error: GROQ_API_KEY not found in .env file.")
        return

    logger.info(f"Using Groq Model (Text): {model}")
    logger.info(f"Using Groq Model (Vision): {vision_model}")

    # 1. Test connection with test_ai_api
    logger.info("\n--- Phase 1: Simple Connection Test ---")
    success = ai.test_ai_api(api_key, model, provider="groq")
    if success:
        logger.info("✅ Connection test: SUCCESS")
    else:
        logger.error("❌ Connection test: FAILED")
        return

    # 2. Test Batch Answers (text)
    logger.info("\n--- Phase 2: Batch Text Question Test ---")
    dummy_quizzes = {
        "1": {
            "question_text": "Apa ibukota dari Indonesia?",
            "answers": [
                "a. Jakarta",
                "b. Bandung",
                "c. Surabaya",
                "d. Medan"
            ]
        },
        "2": {
            "question_text": "Berapakah hasil dari 2 + 3?",
            "answers": [
                "a. 4",
                "b. 5",
                "c. 6",
                "d. 7"
            ]
        }
    }
    
    answers = ai.get_ai_answers(dummy_quizzes, api_key, model, provider="groq")
    logger.info(f"Response from Groq: {answers}")
    if answers and "1" in answers and "2" in answers:
        logger.info("✅ Batch text question test: SUCCESS")
    else:
        logger.error("❌ Batch text question test: FAILED")

    # 3. Test Vision (captcha/image question)
    logger.info("\n--- Phase 3: Vision captcha solving simulation ---")
    captcha_data = create_dummy_captcha_image()
    captcha_text = ai.solve_captcha_with_vision(captcha_data, api_key, vision_model, provider="groq")
    logger.info(f"Solved Captcha Text: {captcha_text}")
    if captcha_text:
        logger.info(f"✅ Vision captcha test: SUCCESS (Result: {captcha_text})")
    else:
        logger.error("❌ Vision captcha test: FAILED")


if __name__ == "__main__":
    test_groq()
