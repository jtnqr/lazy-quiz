# utils/quiz_scraper.py (Final A++ Version with "Next Page" Click)

import re
import time
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

# --- Konstanta untuk Pemeliharaan yang Mudah ---
_BASE_URL = "https://v-class.gunadarma.ac.id"
_LOGIN_URL = f"{_BASE_URL}/login/"
_QUIZ_TITLE_SELECTOR_H1 = "h1"
_QUIZ_NAV_BUTTONS_SELECTOR = ".qn_buttons .qnbutton"
_QUESTION_TEXT_SELECTOR = ".qtext"
_ANSWER_BLOCK_SELECTOR = ".answer > div"
_FINISH_ATTEMPT_LINK_SELECTOR = ".endtestlink"
_NEXT_PAGE_BUTTON_SELECTOR = ".mod_quiz-next-nav"  # <- Selector untuk tombol Next
_ANSWER_CLICK_DELAY_SECONDS = 0.5  # Jeda singkat setelah klik radio


def _clean_html_for_prompt(html: Optional[str]) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator=" ", strip=True)


class QuizScraper:
    def __init__(self, driver: WebDriver, url: str, username: str, password: str):
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
        return "/my/" in self.driver.current_url

    def __perform_login(self, username: str, password: str):
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
        try:
            return self.driver.find_element(By.TAG_NAME, _QUIZ_TITLE_SELECTOR_H1).text
        except NoSuchElementException:
            return "Judul_Kuis_Tidak_Ditemukan"

    def __fetch_quiz_addresses(self) -> List[str]:
        elements = self.driver.find_elements(
            By.CSS_SELECTOR, _QUIZ_NAV_BUTTONS_SELECTOR
        )
        return [el.get_attribute("href") for el in elements if el.get_attribute("href")]

    def fetch_all_quizzes(self) -> Dict[int, Dict[str, List[str]]]:
        if not self.__quiz_addresses:
            print("Peringatan: Tidak ada tombol navigasi kuis yang ditemukan.")
            return {}
        print(f"Menemukan {len(self.__quiz_addresses)} pertanyaan. Memulai scraping...")
        # Cukup navigasi ke halaman pertama, sisanya akan ditangani oleh klik "Next Page"
        self.driver.get(self.__quiz_addresses[0])
        for i in range(len(self.__quiz_addresses)):
            question_number = i + 1
            print(f"  - Scraping pertanyaan {question_number}...")
            self.__quizzes[question_number] = self.__fetch_current_page_quiz()
            # Pindah ke halaman berikutnya untuk scrape, kecuali untuk soal terakhir
            if i < len(self.__quiz_addresses) - 1:
                try:
                    self.driver.find_element(
                        By.CSS_SELECTOR, _NEXT_PAGE_BUTTON_SELECTOR
                    ).click()
                except NoSuchElementException:
                    print(
                        f"  - Peringatan: Tidak bisa menemukan tombol 'Next Page' setelah soal {question_number}. Scraping mungkin tidak lengkap."
                    )
                    break
        return self.__quizzes

    def __fetch_current_page_quiz(self) -> Dict[str, List[str]]:
        """Mengambil data kuis dari halaman yang sedang aktif."""
        try:
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
        except NoSuchElementException:
            return {"Error": "Gagal memuat konten dari halaman saat ini."}

    def answer_quizzes(self, answers: Dict[str, str]):
        print("Memulai proses pengisian jawaban di halaman web...")
        # Navigasi ke pertanyaan pertama untuk memulai
        self.driver.get(self.__quiz_addresses[0])
        time.sleep(1)  # Beri waktu halaman untuk memuat sepenuhnya

        for i in range(len(self.__quiz_addresses)):
            question_number = i + 1
            answer_text = answers.get(str(question_number))  # Ambil jawaban dari dict

            if answer_text:
                print(f"  - Mengisi jawaban untuk pertanyaan {question_number}...")
                self.__answer_current_page_quiz(answer_text)
            else:
                print(
                    f"  - Peringatan: Tidak ada jawaban untuk pertanyaan {question_number}. Melewati..."
                )

            # Klik "Next Page" untuk menyimpan dan pindah, kecuali untuk soal terakhir
            if i < len(self.__quiz_addresses) - 1:
                try:
                    self.driver.find_element(
                        By.CSS_SELECTOR, _NEXT_PAGE_BUTTON_SELECTOR
                    ).click()
                    # time.sleep(1)  # Beri waktu halaman berikutnya untuk memuat
                except NoSuchElementException:
                    print(
                        "  - Tidak bisa menemukan tombol 'Next Page'. Mungkin sudah di akhir kuis."
                    )
                    break
        try:
            self.driver.find_element(
                By.CSS_SELECTOR, _FINISH_ATTEMPT_LINK_SELECTOR
            ).click()
            print("\nSemua jawaban telah diisi dan disimpan.")
            print(
                "PENTING: Harap periksa kembali jawaban Anda di halaman rangkuman dan klik 'Submit all and finish' secara manual."
            )
        except NoSuchElementException:
            print(
                "\nTidak dapat menemukan link 'Finish attempt'. Harap navigasi manual."
            )

    def __answer_current_page_quiz(self, answer_text: str):
        """Memilih jawaban di halaman yang sedang aktif."""
        try:
            xpath_expression = f"//div[starts-with(@class, 'r') and contains(., \"{answer_text}\")]/input"
            input_to_click = self.driver.find_element(By.XPATH, xpath_expression)
            self.driver.execute_script("arguments[0].click();", input_to_click)
            time.sleep(_ANSWER_CLICK_DELAY_SECONDS)
        except NoSuchElementException:
            print(
                f"  - Peringatan: Tidak dapat menemukan atau mengklik pilihan jawaban '{answer_text}'."
            )

    def get_sanitized_title(self) -> str:
        if not self.__title:
            return "Tanpa_Judul"
        sanitized = re.sub(r'[\\/*?:"<>|]', "", self.__title)
        return re.sub(r"\s+", "_", sanitized)
