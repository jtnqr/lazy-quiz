# utils/quiz_scraper.py

import re
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

# --- Konstanta untuk Pemeliharaan yang Mudah ---
# Jika Moodle mengubah selector atau URL, Anda hanya perlu mengubahnya di satu tempat.
_BASE_URL = "https://v-class.gunadarma.ac.id"
_LOGIN_URL = f"{_BASE_URL}/login/"

_QUIZ_TITLE_SELECTOR_H1 = "h1"
_QUIZ_NAV_BUTTONS_SELECTOR = ".qn_buttons .qnbutton"
_QUESTION_TEXT_SELECTOR = ".qtext"
_ANSWER_BLOCK_SELECTOR = ".answer > div"
_ANSWER_INPUT_XPATH = ".//input"
_FINISH_ATTEMPT_LINK_SELECTOR = ".endtestlink"


def _clean_html_for_prompt(html: Optional[str]) -> str:
    """
    Membersihkan string HTML menjadi teks biasa yang mudah dibaca oleh AI,
    termasuk mengambil teks alternatif (alt text) dari gambar.
    """
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")
    text_parts = []

    # Ambil semua teks dan gambar secara berurutan
    for element in soup.find_all(["img", re.compile(".*")]):
        if element.name == "img":
            alt_text = element.get("alt", "").strip()
            if alt_text:
                text_parts.append(f"[Gambar dengan deskripsi: {alt_text}]")
            else:
                # Fallback jika tidak ada alt text, gunakan nama file gambar
                src = element.get("src", "").split("/")[-1]
                text_parts.append(f"[Gambar: {src}]")
        elif element.string and element.string.strip():
            text_parts.append(element.string.strip())

    full_text = " ".join(text_parts)
    return re.sub(r"\s+", " ", full_text).strip()


class QuizScraper:
    """
    Sebuah kelas untuk mengotomatiskan interaksi dengan kuis Moodle.
    Bertanggung jawab untuk login, scraping pertanyaan, dan mengisi jawaban.
    """

    def __init__(self, driver: WebDriver, url: str, username: str, password: str):
        """
        Inisialisasi scraper.

        Args:
            driver (WebDriver): Instance Selenium WebDriver yang akan digunakan.
            url (str): URL awal (bisa halaman login atau halaman kuis).
            username (str): Nama pengguna untuk login.
            password (str): Kata sandi untuk login.
        """
        self.driver: WebDriver = driver
        self.__quizzes: Dict[int, Dict[str, List[str]]] = {}
        self.__quiz_addresses: List[str] = []
        self.__title: Optional[str] = None

        print("Mengecek status login...")
        if not self.__is_logged_in():
            print("Belum login. Melakukan proses login...")
            self.__perform_login(username, password)

        print(f"Menavigasi ke URL kuis: {url}")
        self.driver.get(url)

        self.__title = self.__fetch_quiz_title()
        self.__quiz_addresses = self.__fetch_quiz_addresses()

    def __is_logged_in(self) -> bool:
        """Memeriksa apakah sesi pengguna saat ini sudah login."""
        # Cara sederhana: URL setelah login biasanya mengandung '/my/'
        return "/my/" in self.driver.current_url

    def __perform_login(self, username: str, password: str):
        """Melakukan login ke Moodle menggunakan kredensial yang diberikan."""
        if _LOGIN_URL not in self.driver.current_url:
            self.driver.get(_LOGIN_URL)
        try:
            self.driver.find_element(By.ID, "username").send_keys(username)
            self.driver.find_element(By.ID, "password").send_keys(password)
            self.driver.find_element(By.ID, "loginbtn").click()
            print("Login berhasil.")
        except NoSuchElementException:
            print(
                "Gagal menemukan elemen login. Mungkin sudah login atau halaman berubah."
            )

    def __fetch_quiz_title(self) -> str:
        """Mengambil judul kuis dari halaman."""
        try:
            return self.driver.find_element(By.TAG_NAME, _QUIZ_TITLE_SELECTOR_H1).text
        except NoSuchElementException:
            return "Judul_Kuis_Tidak_Ditemukan"

    def __fetch_quiz_addresses(self) -> List[str]:
        """Mengambil semua URL untuk setiap halaman pertanyaan kuis."""
        elements = self.driver.find_elements(
            By.CSS_SELECTOR, _QUIZ_NAV_BUTTONS_SELECTOR
        )
        return [el.get_attribute("href") for el in elements if el.get_attribute("href")]

    def fetch_all_quizzes(self) -> Dict[int, Dict[str, List[str]]]:
        """
        Mengambil semua pertanyaan dan pilihan jawaban dari setiap halaman kuis.
        Ini adalah metode publik utama untuk memulai proses scraping.

        Returns:
            Dict: Kamus berisi semua data kuis yang telah di-scrape.
        """
        if not self.__quiz_addresses:
            print("Peringatan: Tidak ada tombol navigasi kuis yang ditemukan.")
            return {}

        print(f"Menemukan {len(self.__quiz_addresses)} pertanyaan. Memulai scraping...")
        for i in range(len(self.__quiz_addresses)):
            question_number = i + 1
            print(f"  - Scraping pertanyaan {question_number}...")
            self.__quizzes[question_number] = self.__fetch_single_quiz(question_number)
        return self.__quizzes

    def __fetch_single_quiz(self, question_number: int) -> Dict[str, List[str]]:
        """Mengambil teks pertanyaan dan pilihan jawaban untuk satu nomor."""
        try:
            target_url = self.__quiz_addresses[question_number - 1]
            # --- Peningkatan Efisiensi: Hanya navigasi jika URL berbeda ---
            if self.driver.current_url != target_url:
                self.driver.get(target_url)

            q_html = self.driver.find_element(
                By.CSS_SELECTOR, _QUESTION_TEXT_SELECTOR
            ).get_attribute("innerHTML")
            q_text = _clean_html_for_prompt(q_html)

            answer_elements = self.driver.find_elements(
                By.CSS_SELECTOR, _ANSWER_BLOCK_SELECTOR
            )
            answers = [
                _clean_html_for_prompt(el.get_attribute("innerHTML"))
                for el in answer_elements
            ]

            return {q_text: [ans for ans in answers if ans]}
        except (NoSuchElementException, IndexError):
            return {"Error": f"Gagal memuat konten untuk pertanyaan {question_number}."}

    def answer_quizzes(self, answers: Dict[str, str]):
        """
        Mengisi semua jawaban di halaman web berdasarkan kamus jawaban.

        Args:
            answers (Dict[str, str]): Kamus dengan nomor pertanyaan (string) sebagai kunci dan teks jawaban sebagai nilai.
        """
        print("Memulai proses pengisian jawaban di halaman web...")
        for q_num_str, answer_text in answers.items():
            question_number = int(q_num_str)
            print(f"  - Mengisi jawaban untuk pertanyaan {question_number}...")
            self.__answer_single_quiz(question_number, answer_text)

        try:
            # Setelah semua jawaban terisi, klik link untuk ke halaman rangkuman.
            self.driver.find_element(
                By.CSS_SELECTOR, _FINISH_ATTEMPT_LINK_SELECTOR
            ).click()
            print("\nSemua jawaban telah dipilih.")
            print(
                "PENTING: Harap periksa kembali jawaban Anda di halaman rangkuman dan klik 'Submit all and finish' secara manual."
            )
        except NoSuchElementException:
            print(
                "\nTidak dapat menemukan link 'Finish attempt'. Harap navigasi manual."
            )

    def __answer_single_quiz(self, question_number: int, answer_text: str):
        """Memilih satu jawaban untuk satu nomor pertanyaan."""
        try:
            target_url = self.__quiz_addresses[question_number - 1]
            if self.driver.current_url != target_url:
                self.driver.get(target_url)

            # XPath ini lebih kuat karena mencari input (radio/checkbox) yang berasosiasi dengan teks jawaban.
            xpath_expression = f"//div[contains(@class, 'answer')]//div[contains(., \"{answer_text}\")]"
            answer_element_container = self.driver.find_element(
                By.XPATH, xpath_expression
            )

            # Klik pada input di dalam elemen jawaban
            input_to_click = answer_element_container.find_element(
                By.XPATH, _ANSWER_INPUT_XPATH
            )
            self.driver.execute_script("arguments[0].click();", input_to_click)

        except (NoSuchElementException, IndexError):
            print(
                f"  - Peringatan: Tidak dapat menemukan pilihan jawaban '{answer_text}' untuk pertanyaan {question_number}."
            )

    def get_sanitized_title(self) -> str:
        """
        Mengembalikan judul kuis yang sudah dibersihkan untuk digunakan sebagai nama file/folder.
        """
        if not self.__title:
            return "Tanpa_Judul"

        sanitized = re.sub(r'[\\/*?:"<>|]', "", self.__title)
        return re.sub(r"\s+", "_", sanitized)
