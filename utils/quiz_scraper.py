# utils/quiz_scraper.py

import re
from typing import Dict, List, Optional

from bs4 import BeautifulSoup
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# --- Konstanta untuk Pemeliharaan yang Mudah ---
_BASE_URL = "https://v-class.gunadarma.ac.id"
_LOGIN_URL = f"{_BASE_URL}/login/"
_QUIZ_TITLE_SELECTOR_H1 = "h1"
_QUIZ_NAV_BUTTONS_SELECTOR = ".qn_buttons .qnbutton"
_QUESTION_TEXT_SELECTOR = ".qtext"
_ANSWER_BLOCK_SELECTOR = ".answer > div"
_FINISH_ATTEMPT_LINK_SELECTOR = ".endtestlink"
_NEXT_PAGE_BUTTON_SELECTOR = ".mod_quiz-next-nav"
_ATTEMPT_QUIZ_BUTTON_XPATH = "//button[contains(text(), 'Attempt quiz now')]"
_WAIT_TIMEOUT_SECONDS = 10  # Waktu tunggu maksimal untuk elemen


def _clean_html_for_prompt(html: Optional[str]) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator=" ", strip=True)


class QuizScraper:
    def __init__(self, driver: WebDriver, url: str, username: str, password: str):
        self.driver: WebDriver = driver
        self.wait: WebDriverWait = WebDriverWait(self.driver, _WAIT_TIMEOUT_SECONDS)
        self.__quizzes: Dict[int, Dict[str, List[str]]] = {}
        self.__quiz_addresses: List[str] = []
        self.__title: Optional[str] = None

        print("Mengecek status login...")
        if not self.__is_logged_in():
            print("Belum login. Melakukan proses login...")
            self.__perform_login(username, password)

        print(f"Menavigasi ke URL kuis: {url}")
        self.driver.get(url)

        # --- FITUR BARU: Mulai Kuis Otomatis ---
        self.__start_quiz_if_needed()

        # --- PENINGKATAN KETANGGUHAN: Validasi Halaman Kuis ---
        if not self.__is_valid_quiz_page():
            raise ValueError(
                "URL yang diberikan tampaknya bukan halaman kuis yang valid. Tidak dapat menemukan navigasi kuis."
            )

        self.__title = self.__fetch_quiz_title()
        self.__quiz_addresses = self.__fetch_quiz_addresses()

    def __is_logged_in(self) -> bool:
        return "/my/" in self.driver.current_url

    def __perform_login(self, username: str, password: str):
        if _LOGIN_URL not in self.driver.current_url:
            self.driver.get(_LOGIN_URL)
        try:
            self.wait.until(
                EC.presence_of_element_located((By.ID, "username"))
            ).send_keys(username)
            self.driver.find_element(By.ID, "password").send_keys(password)
            self.driver.find_element(By.ID, "loginbtn").click()
            print("Login berhasil.")
        except (NoSuchElementException, TimeoutException):
            print(
                "Gagal menemukan elemen login. Mungkin sudah login atau halaman berubah."
            )

    def __start_quiz_if_needed(self):
        """Memeriksa keberadaan tombol 'Attempt quiz now' dan mengkliknya jika ada."""
        try:
            attempt_button = self.driver.find_element(
                By.XPATH, _ATTEMPT_QUIZ_BUTTON_XPATH
            )
            print("Tombol 'Attempt quiz now' ditemukan. Memulai percobaan kuis...")
            attempt_button.click()
            # Tunggu hingga halaman kuis yang sebenarnya (dengan navigasi) dimuat
            self.wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, _QUIZ_NAV_BUTTONS_SELECTOR)
                )
            )
            print("Percobaan kuis berhasil dimulai.")
        except NoSuchElementException:
            # Jika tombol tidak ada, berarti kita sudah di dalam percobaan kuis.
            print("Sudah berada di dalam percobaan kuis. Melanjutkan...")
            pass

    def __is_valid_quiz_page(self) -> bool:
        """Memvalidasi apakah halaman saat ini adalah halaman kuis yang aktif."""
        try:
            self.driver.find_element(By.CSS_SELECTOR, _QUIZ_NAV_BUTTONS_SELECTOR)
            return True
        except NoSuchElementException:
            return False

    def __fetch_quiz_title(self) -> str:
        try:
            return self.wait.until(
                EC.presence_of_element_located((By.TAG_NAME, _QUIZ_TITLE_SELECTOR_H1))
            ).text
        except TimeoutException:
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
        self.driver.get(self.__quiz_addresses[0])
        for i in range(len(self.__quiz_addresses)):
            question_number = i + 1
            print(f"  - Scraping pertanyaan {question_number}...")
            self.__quizzes[question_number] = self.__fetch_current_page_quiz()
            if i < len(self.__quiz_addresses) - 1:
                try:
                    self.wait.until(
                        EC.element_to_be_clickable(
                            (By.CSS_SELECTOR, _NEXT_PAGE_BUTTON_SELECTOR)
                        )
                    ).click()
                except TimeoutException:
                    print(
                        f"  - Peringatan: Tidak bisa menemukan tombol 'Next Page' setelah soal {question_number}."
                    )
                    break
        return self.__quizzes

    def __fetch_current_page_quiz(self) -> Dict[str, List[str]]:
        try:
            q_element = self.wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, _QUESTION_TEXT_SELECTOR)
                )
            )
            q_html = q_element.get_attribute("innerHTML")
            q_text = _clean_html_for_prompt(q_html)
            answer_elements = self.driver.find_elements(
                By.CSS_SELECTOR, _ANSWER_BLOCK_SELECTOR
            )
            answers = [
                _clean_html_for_prompt(el.get_attribute("innerHTML"))
                for el in answer_elements
            ]
            return {q_text: [ans for ans in answers if ans]}
        except TimeoutException:
            return {"Error": "Gagal memuat konten dari halaman saat ini."}

    def answer_quizzes(self, answers: Dict[str, str]):
        print("Memulai proses pengisian jawaban di halaman web...")
        self.driver.get(self.__quiz_addresses[0])
        self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, _QUESTION_TEXT_SELECTOR))
        )
        for i in range(len(self.__quiz_addresses)):
            question_number = i + 1
            answer_text = answers.get(str(question_number))
            if answer_text:
                print(f"  - Mengisi jawaban untuk pertanyaan {question_number}...")
                self.__answer_current_page_quiz(answer_text)
            else:
                print(
                    f"  - Peringatan: Tidak ada jawaban untuk pertanyaan {question_number}. Melewati..."
                )
            if i < len(self.__quiz_addresses) - 1:
                try:
                    self.wait.until(
                        EC.element_to_be_clickable(
                            (By.CSS_SELECTOR, _NEXT_PAGE_BUTTON_SELECTOR)
                        )
                    ).click()
                except TimeoutException:
                    print(
                        "  - Tidak bisa menemukan tombol 'Next Page'. Mungkin sudah di akhir kuis."
                    )
                    break
        try:
            self.wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, _FINISH_ATTEMPT_LINK_SELECTOR)
                )
            ).click()
            print("\nSemua jawaban telah diisi dan disimpan.")
            print(
                "PENTING: Harap periksa kembali jawaban Anda di halaman rangkuman dan klik 'Submit all and finish' secara manual."
            )
        except TimeoutException:
            print(
                "\nTidak dapat menemukan link 'Finish attempt'. Harap navigasi manual."
            )

    def __answer_current_page_quiz(self, answer_text: str):
        try:
            xpath_expression = f"//div[starts-with(@class, 'r') and contains(., \"{answer_text}\")]/input"
            input_to_click = self.wait.until(
                EC.presence_of_element_located((By.XPATH, xpath_expression))
            )
            self.driver.execute_script("arguments[0].click();", input_to_click)
        except TimeoutException:
            print(
                f"  - Peringatan: Tidak dapat menemukan atau mengklik pilihan jawaban '{answer_text}'."
            )

    def get_sanitized_title(self) -> str:
        if not self.__title:
            return "Tanpa_Judul"
        sanitized = re.sub(r'[\\/*?:"<>|]', "", self.__title)
        return re.sub(r"\s+", "_", sanitized)
