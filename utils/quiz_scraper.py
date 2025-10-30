# utils/quiz_scraper.py

import re
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

_BASE_URL = "https://v-class.gunadarma.ac.id"
_LOGIN_URL = f"{_BASE_URL}/login/index.php"
_DASHBOARD_ELEMENT_SELECTOR = ".action-menu"

_QUIZ_TITLE_SELECTOR_H1 = "h2"
_QUIZ_NAV_BUTTONS_SELECTOR = ".qn_buttons .qnbutton"
_QUESTION_TEXT_SELECTOR = ".qtext"
_ANSWER_BLOCK_SELECTOR = ".answer > div"
_FINISH_ATTEMPT_LINK_SELECTOR = ".endtestlink"
_NEXT_PAGE_BUTTON_SELECTOR = ".mod_quiz-next-nav"
_QUIZ_ACTION_BUTTON_XPATH = (
    "//div[contains(@class, 'quizstartbuttondiv')]//button[@type='submit']"
)
_START_ATTEMPT_CONFIRM_BUTTON_ID = "id_submitbutton"
_WAIT_TIMEOUT_SECONDS = 15


def _clean_html_for_prompt(html: Optional[str]) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    # Hapus label seperti "a. ", "b. ", dll. dari awal string.
    return re.sub(r"^[a-z]\.\s+", "", text).strip()


class QuizScraper:
    def __init__(self, driver: WebDriver, url: str, username: str, password: str):
        self.driver: WebDriver = driver
        self.wait: WebDriverWait = WebDriverWait(self.driver, _WAIT_TIMEOUT_SECONDS)
        self.quiz_id: Optional[str] = self._extract_id_from_url(url)
        self.__quizzes: Dict[int, Dict[str, Any]] = {}
        self.__quiz_addresses: List[str] = []
        self.__title: Optional[str] = None

        print("Memulai proses otentikasi...")
        self._perform_login(username, password)

        print(f"Login berhasil. Menavigasi ke URL kuis: {url}")
        self.driver.get(url)

        self.__title = self._fetch_quiz_title()

        self._start_quiz_if_needed()

        if not self._is_valid_quiz_page():
            raise ValueError(
                "URL yang diberikan tampaknya bukan halaman kuis yang valid."
            )

        self.__quiz_addresses = self._fetch_quiz_addresses()

    def _extract_id_from_url(self, url: str) -> Optional[str]:
        match = re.search(r"[?&](id|cmid)=(\d+)", url)
        return match.group(2) if match else None

    def _perform_login(self, username: str, password: str):
        try:
            self.driver.get(_LOGIN_URL)
            username_field = self.wait.until(
                EC.visibility_of_element_located((By.ID, "username"))
            )
            password_field = self.driver.find_element(By.ID, "password")
            username_field.send_keys(username)
            password_field.send_keys(password)
            self.driver.find_element(By.ID, "loginbtn").click()
            self.wait.until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, _DASHBOARD_ELEMENT_SELECTOR)
                )
            )
        except (TimeoutException, Exception) as e:
            print("Gagal melakukan login.")
            self.driver.save_screenshot("login_failure.png")
            raise e

    def _start_quiz_if_needed(self):
        try:
            action_button = self.wait.until(
                EC.presence_of_element_located((By.XPATH, _QUIZ_ACTION_BUTTON_XPATH))
            )
            print(f"Tombol '{action_button.text}' ditemukan. Mengklik...")
            action_button.click()
            try:
                confirm_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable(
                        (By.ID, _START_ATTEMPT_CONFIRM_BUTTON_ID)
                    )
                )
                print("Popup ditemukan. Mengklik tombol konfirmasi...")
                confirm_button.click()
            except TimeoutException:
                print("Tidak ada popup konfirmasi. Melanjutkan...")
            self.wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, _QUIZ_NAV_BUTTONS_SELECTOR)
                )
            )
            print("Percobaan kuis berhasil dimulai/dilanjutkan.")
        except TimeoutException:
            print("Sudah berada di dalam percobaan kuis. Melanjutkan...")
            pass

    def _is_valid_quiz_page(self) -> bool:
        try:
            self.driver.find_element(By.CSS_SELECTOR, _QUIZ_NAV_BUTTONS_SELECTOR)
            return True
        except NoSuchElementException:
            return False

    def _fetch_quiz_title(self) -> str:
        try:
            return self.wait.until(
                EC.presence_of_element_located((By.TAG_NAME, _QUIZ_TITLE_SELECTOR_H1))
            ).text
        except TimeoutException:
            return "Judul_Kuis_Tidak_Ditemukan"

    def _fetch_quiz_addresses(self) -> List[str]:
        elements = self.driver.find_elements(
            By.CSS_SELECTOR, _QUIZ_NAV_BUTTONS_SELECTOR
        )
        return [el.get_attribute("href") for el in elements if el.get_attribute("href")]

    def fetch_all_quizzes(self) -> Dict[int, Dict[str, Any]]:
        if not self.__quiz_addresses:
            return {}
        print(f"Menemukan {len(self.__quiz_addresses)} pertanyaan. Memulai scraping...")
        self.driver.get(self.__quiz_addresses[0])
        for i in range(len(self.__quiz_addresses)):
            q_num = i + 1
            print(f"  - Scraping pertanyaan {q_num}...")
            self.__quizzes[q_num] = self._fetch_current_page_quiz()
            if i < len(self.__quiz_addresses) - 1:
                try:
                    self.wait.until(
                        EC.element_to_be_clickable(
                            (By.CSS_SELECTOR, _NEXT_PAGE_BUTTON_SELECTOR)
                        )
                    ).click()
                except TimeoutException:
                    print(
                        f"  - Peringatan: Gagal menemukan tombol 'Next Page' setelah soal {q_num}."
                    )
                    break
        return self.__quizzes

    def _fetch_current_page_quiz(self) -> Dict[str, Any]:
        try:
            q_element = self.wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, _QUESTION_TEXT_SELECTOR)
                )
            )
            q_html = q_element.get_attribute("innerHTML")
            q_text = _clean_html_for_prompt(q_html)
            has_image = "<img" in q_html
            answer_elements = self.driver.find_elements(
                By.CSS_SELECTOR, _ANSWER_BLOCK_SELECTOR
            )
            answers = []
            for el in answer_elements:
                ans_html = el.get_attribute("innerHTML")
                if "<img" in ans_html:
                    has_image = True
                answers.append(_clean_html_for_prompt(ans_html))
            return {
                "question_text": q_text,
                "answers": [ans for ans in answers if ans],
                "has_image": has_image,
            }
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
                self._answer_current_page_quiz(answer_text)
            if i < len(self.__quiz_addresses) - 1:
                try:
                    self.wait.until(
                        EC.element_to_be_clickable(
                            (By.CSS_SELECTOR, _NEXT_PAGE_BUTTON_SELECTOR)
                        )
                    ).click()
                except TimeoutException:
                    print("  - Tidak bisa menemukan tombol 'Next Page'.")
                    break
        try:
            self.wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, _FINISH_ATTEMPT_LINK_SELECTOR)
                )
            ).click()
            print("\nSemua jawaban yang memungkinkan telah diisi dan disimpan.")
            print(
                "PENTING: Harap periksa kembali jawaban Anda dan klik 'Submit all and finish' secara manual."
            )
        except TimeoutException:
            print(
                "\nTidak dapat menemukan link 'Finish attempt'. Harap navigasi manual."
            )

    def _answer_current_page_quiz(self, answer_text: str):
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
        sanitized = sanitized.replace("(", "").replace(")", "")
        return re.sub(r"\s+", "_", sanitized)
