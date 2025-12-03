#  Lazy Quiz - Moodle Quiz Bot
#  Copyright (C) 2025 Julius W. (@jtnqr)
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>.

import json
import re
from typing import Dict

import google.generativeai as genai
from google.api_core import exceptions


def _format_batch_prompt(quizzes: dict) -> str:
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
        prompt += f"\nSoal Nomor: {number}\n"
        prompt += f"Pertanyaan: {data['question_text']}\n"
        prompt += "Pilihan:\n"
        for opt in data["answers"]:
            prompt += f"- {opt}\n"
        prompt += "-------------------------------------\n"
    prompt += "\nHarap kembalikan hanya objek JSON sebagai respons Anda."
    return prompt


def get_gemini_answers(quizzes: dict, api_key: str, model_name: str) -> Dict[str, str]:
    genai.configure(api_key=api_key)
    try:
        model = genai.GenerativeModel(model_name)
    except exceptions.NotFound:
        print(f"Gemini API Error: Model '{model_name}' tidak ditemukan.")
        return {}

    print("--- Menghubungi Gemini API untuk semua jawaban (Mode Batch) ---")
    batch_prompt = _format_batch_prompt(quizzes)

    try:
        print(f"Mengirim {len(quizzes)} pertanyaan teks dalam satu permintaan...")
        response = model.generate_content(batch_prompt)

        json_text = re.search(r"```json\s*([\s\S]+?)\s*```", response.text)
        cleaned_text = json_text.group(1) if json_text else response.text

        answers_from_ai = json.loads(cleaned_text)
        print("Berhasil menerima dan mem-parsing semua jawaban dari Gemini.")
        return answers_from_ai
    except (json.JSONDecodeError, Exception) as e:
        print(f"  > Terjadi error saat memproses respons dari AI: {e}")
        return {}


def test_gemini_api(api_key: str, model_name: str) -> bool:
    print("\n--- Testing Gemini API Connection ---")
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(
            "This is a test. Respond with the single word: OK"
        )
        if "OK" in response.text:
            print("Gemini API Check: SUCCESS")
            return True
        else:
            print("Gemini API Check: WARNING - Respons tidak terduga")
            return True
    except exceptions.PermissionDenied:
        print("Gemini API Check: FAILED - API Key tidak valid")
        return False
    except exceptions.NotFound:
        print(f"Gemini API Check: FAILED - Model '{model_name}' tidak ditemukan")
        return False
    except Exception as e:
        print(f"Gemini API Check: FAILED - Error: {e}")
        return False
        return False
