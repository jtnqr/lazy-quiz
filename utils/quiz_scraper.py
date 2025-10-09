# utils/quiz_scraper.py

import json
import os
import re
from typing import Dict, List, Optional

from bs4 import BeautifulSoup
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

_BASE_URL = "https://v-class.gunadarma.ac.id"
_LOGIN_URL = f"{_BASE_URL}/login/index.php"
_SESSION_FILE = "session.json"

_QUIZ_TITLE_SELECTOR_H1 = "h1"
_QUIZ_NAV_BUTTONS_SELECTOR = ".qn_buttons .qnbutton"
_QUESTION_TEXT_SELECTOR = ".qtext"
_ANSWER_BLOCK_SELECTOR = ".answer > div"
_FINISH_ATTEMPT_LINK_SELECTOR = ".endtestlink"
_NEXT_PAGE_BUTTON_SELECTOR = ".mod_quiz-next-nav"
_ATTEMPT_QUIZ_BUTTON_XPATH = "//button[contains(text(), 'Attempt quiz now')]"
_START_ATTEMPT_CONFIRM_BUTTON_ID = "id_submitbutton"
_WAIT_TIMEOUT_SECONDS = 10


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

        print("Mencoba memuat sesi dari file...")
        if not self.__load_session_and_verify():
            print("Sesi tidak ditemukan atau tidak valid. Melakukan login manual...")
            self.__perform_login_robustly(username, password)
            self.__save_session()
        else:
            print("Berhasil melanjutkan sesi dari file.")

        print(f"Menavigasi ke URL kuis: {url}")
        self.driver.get(url)

        self.__start_quiz_if_needed()

        if not self.__is_valid_quiz_page():
            raise ValueError(
                "URL yang diberikan tampaknya bukan halaman kuis yang valid. Tidak dapat menemukan navigasi kuis."
            )

        self.__title = self.__fetch_quiz_title()
        self.__quiz_addresses = self.__fetch_quiz_addresses()

    def __load_session_and_verify(self) -> bool:
        if not os.path.exists(_SESSION_FILE):
            return False
        try:
            with open(_SESSION_FILE, "r") as f:
                cookies = json.load(f)
            self.driver.get(_BASE_URL)
            for cookie in cookies:
                self.driver.add_cookie(cookie)
            self.driver.get(_BASE_URL + "/my/")
            self.wait.until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            return self.__is_logged_in()
        except Exception:
            return False

    def __save_session(self):
        try:
            cookies = self.driver.get_cookies()
            with open(_SESSION_FILE, "w") as f:
                json.dump(cookies, f)
            print(f"Sesi berhasil disimpan ke '{_SESSION_FILE}'.")
        except Exception as e:
            print(f"Gagal menyimpan sesi: {e}")

    def __is_logged_in(self) -> bool:
        return "/my/" in self.driver.current_url

    def __perform_login_robustly(self, username: str, password: str):
        try:
            self.driver.get(_LOGIN_URL)

            username_field = self.wait.until(
                EC.visibility_of_element_located((By.ID, "username"))
            )
            password_field = self.driver.find_element(By.ID, "password")
            login_button = self.driver.find_element(By.ID, "loginbtn")

            username_field.send_keys(username)
            password_field.send_keys(password)
            login_button.click()

            self.wait.until(EC.staleness_of(login_button))

            if not self.__is_logged_in():
                raise Exception(
                    "Login gagal. Halaman tidak beralih ke dasbor setelah submit."
                )

            print("Login manual berhasil.")
        except (TimeoutException, Exception) as e:
            print(
                "Gagal melakukan login. Periksa kredensial Anda atau koneksi jaringan."
            )
            self.driver.save_screenshot("login_failure_screenshot.png")
            print(
                "Screenshot halaman kegagalan disimpan sebagai 'login_failure_screenshot.png'"
            )
            raise e

    def __start_quiz_if_needed(self):
        try:
            attempt_button = self.wait.until(
                EC.presence_of_element_located((By.XPATH, _ATTEMPT_QUIZ_BUTTON_XPATH))
            )
            print("Tombol 'Attempt quiz now' ditemukan. Mengklik...")
            attempt_button.click()
            print("Menunggu popup konfirmasi...")
            confirm_button = self.wait.until(
                EC.element_to_be_clickable((By.ID, _START_ATTEMPT_CONFIRM_BUTTON_ID))
            )
            print("Popup ditemukan. Mengklik tombol konfirmasi 'Start attempt'...")
            confirm_button.click()
            self.wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, _QUIZ_NAV_BUTTONS_SELECTOR)
                )
            )
            print("Percobaan kuis berhasil dimulai.")
        except (NoSuchElementException, TimeoutException):
            print(
                "Sudah berada di dalam percobaan kuis atau tombol tidak ditemukan. Melanjutkan..."
            )
            pass

    def __is_valid_quiz_page(self) -> bool:
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
            return {}
        print(f"Menemukan {len(self.__quiz_addresses)} pertanyaan. Memulai scraping...")
        self.driver.get(self.__quiz_addresses[0])
        for i in range(len(self.__quiz_addresses)):
            q_num = i + 1
            print(f"  - Scraping pertanyaan {q_num}...")
            self.__quizzes[q_num] = self.__fetch_current_page_quiz()
            if i < len(self.__quiz_addresses) - 1:
                try:
                    self.wait.until(
                        EC.element_to_be_clickable(
                            (By.CSS_SELECTOR, _NEXT_PAGE_BUTTON_SELECTOR)
                        )
                    ).click()
                except TimeoutException:
                    print(
                        f"  - Peringatan: Tidak bisa menemukan tombol 'Next Page' setelah soal {q_num}."
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
            q_num = i + 1
            answer_text = answers.get(str(q_num))
            if answer_text:
                print(f"  - Mengisi jawaban untuk pertanyaan {q_num}...")
                self.__answer_current_page_quiz(answer_text)
            else:
                print(
                    f"  - Peringatan: Tidak ada jawaban untuk pertanyaan {q_num}. Melewati..."
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
            xpath = f"//div[starts-with(@class, 'r') and contains(., \"{answer_text}\")]/input"
            input_to_click = self.wait.until(
                EC.presence_of_element_located((By.XPATH, xpath))
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
