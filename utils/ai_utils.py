# utils/ai_utils.py (Final A++ Version with Batching)

import re
import google.generativeai as genai
import time
import json
from google.api_core import exceptions


def _format_batch_prompt(quizzes: dict) -> str:
    """Membangun satu prompt besar yang berisi semua pertanyaan untuk pemrosesan batch."""
    prompt = (
        "Anda adalah seorang ahli yang sangat akurat dalam menjawab kuis pilihan ganda. "
        "Di bawah ini ada beberapa pertanyaan. Analisis setiap pertanyaan dan pilihan jawabannya, "
        "lalu kembalikan satu objek JSON yang valid.\n\n"
        'Struktur JSON harus berupa: { "nomor_soal": "teks_jawaban_lengkap" }.\n'
        'Contoh: { "1": "b. Pilihan Jawaban Benar", "2": "c. Pilihan Lainnya" }.\n'
        "Pastikan teks jawaban yang Anda kembalikan sama persis dengan salah satu pilihan yang diberikan.\n\n"
        "Berikut adalah pertanyaannya:\n"
        "-------------------------------------\n"
    )

    for number, data in quizzes.items():
        question_text, options = list(data.items())[0]
        prompt += f"\nSoal Nomor: {number}\n"
        prompt += f"Pertanyaan: {question_text}\n"
        prompt += "Pilihan:\n"
        for opt in options:
            prompt += f"- {opt}\n"
        prompt += "-------------------------------------\n"

    prompt += "\nHarap kembalikan hanya objek JSON sebagai respons Anda."
    return prompt


def get_gemini_answers(quizzes: dict, api_key: str, model_name: str):
    """
    Menggunakan Gemini API untuk menjawab semua kuis dalam satu panggilan batch.
    """
    genai.configure(api_key=api_key)
    try:
        model = genai.GenerativeModel(model_name)
    except exceptions.NotFound:
        print(
            f"Gemini API Error: Model '{model_name}' tidak ditemukan. Periksa nama model di file .env Anda."
        )
        return {}

    print("--- Menghubungi Gemini API untuk semua jawaban (Mode Batch) ---")

    # Konsep Penanganan Limit Token (untuk masa depan):
    # Model modern seperti gemini-1.5-flash memiliki limit token yang sangat besar (1 juta),
    # sehingga satu kuis hampir pasti muat dalam satu batch. Jika diperlukan untuk model
    # yang lebih lama, kita bisa memecah `quizzes` menjadi beberapa 'chunk' dan memanggil
    # API untuk setiap chunk. Untuk saat ini, satu batch sudah cukup.

    batch_prompt = _format_batch_prompt(quizzes)
    ai_answers = {}

    try:
        print("Mengirim semua pertanyaan dalam satu permintaan...")
        response = model.generate_content(batch_prompt)

        # Ekstrak blok JSON dari respons AI, yang terkadang menyertakan ```json ... ```
        json_text = re.search(r"```json\s*([\s\S]+?)\s*```", response.text)
        if json_text:
            cleaned_text = json_text.group(1)
        else:
            cleaned_text = response.text

        # Parsing respons JSON
        ai_answers = json.loads(cleaned_text)
        print("Berhasil menerima dan mem-parsing semua jawaban dari Gemini.")

    except json.JSONDecodeError:
        print(
            "  > Peringatan: Gagal mem-parsing respons JSON dari Gemini. AI mungkin tidak mengembalikan format yang benar."
        )
        print(f"  > Respons Mentah: {response.text}")
        # Sebagai fallback, kita bisa mencoba menjawab satu per satu, tapi untuk sekarang kita biarkan kosong.
        return {}
    except Exception as e:
        print(f"  > Terjadi error tak terduga saat memanggil API: {e}")
        return {}

    print("--- Selesai mendapatkan jawaban dari Gemini ---")
    return ai_answers


def test_gemini_api(api_key: str, model_name: str) -> bool:
    # ... (fungsi ini tidak perlu diubah)
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
    except exceptions.NotFound:
        print(
            f"Gemini API Check: FAILED - Model '{model_name}' not found. Check the model name in your .env file."
        )
        return False
    except Exception as e:
        print(f"Gemini API Check: FAILED - An unexpected error occurred: {e}")
        return False
