"""
Base class for all scrapers with common Playwright setup.
Provides anti-detection features and session management.
"""

import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

from utils.logger import logger
from utils.session_manager import SessionManager


class BaseScraper(ABC):
    def __init__(self, url: str, username: str, password: str, no_session: bool = False):
        self.url = url
        self.username = username
        self.password = password

        # Internal State
        self.quiz_id: Optional[str] = self._extract_id_from_url(url)
        self.attempt_url: Optional[str] = None
        self.quizzes_data: Dict[int, Dict[str, Any]] = {}

        # Initialize session manager
        self.session_manager = SessionManager()

        # Playwright Setup (Shared)
        logger.info(f"--- [Playwright] Init Browser ({self.__class__.__name__}) ---")
        self.playwright = sync_playwright().start()
        self.browser: Browser = self.playwright.chromium.launch(
            headless=False,  # Set False jika ingin debugging visual
            slow_mo=500,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                # "--start-maximized",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--exclude-switches=enable-automation",
            ],
        )

        # Load session only if not skipped
        storage_state = None
        if not no_session:
            storage_state = self.session_manager.load_session(username)

        self.context: BrowserContext = self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            no_viewport=True,
            locale="id-ID",
            timezone_id="Asia/Jakarta",
            storage_state=storage_state,
        )

        self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            // Mocking plugins agar terlihat seperti browser beneran
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            // Mocking languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['id-ID', 'id', 'en-US', 'en']
            });
        """)

        # Block heavy resources
        # self.context.route(
        #     "**/*",
        #     lambda route: route.abort()
        #     if route.request.resource_type in ["image", "media", "font"]
        #     else route.continue_(),
        # )

        self.page: Page = self.context.new_page()

    @abstractmethod
    def login(self):
        """Logic login spesifik per website"""
        pass

    @abstractmethod
    def fetch_all_quizzes(self) -> Dict[int, Dict[str, Any]]:
        """Scrape soal -> return dict standar"""
        pass

    @abstractmethod
    def save_answers(self, answers: Dict[str, str]) -> List[int]:
        """Isi form -> return list ID soal yg sukses"""
        pass

    @abstractmethod
    def submit_final(self):
        """Klik tombol submit akhir"""
        pass

    def _extract_id_from_url(self, url: str) -> Optional[str]:
        """Bisa di-override jika format ID di URL beda"""
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        # Default logic (cocok untuk moodle/umum)
        if "id" in params:
            return params["id"][0]
        return "UnknownID"

    def get_sanitized_title(self) -> str:
        try:
            title = self.page.title()
        except Exception:
            title = "Quiz"
        clean_title = re.sub(r"[^a-zA-Z0-9]", "_", title)[:30]
        return f"{clean_title}_{self.quiz_id}"

    def set_quiz_data(self, data: Dict[str, Any]):
        """Load cache"""
        self.quizzes_data = {int(k): v for k, v in data.items()}

    def reset_quiz_data(self):
        """Membersihkan data soal dari memori (untuk persiapan Bagian selanjutnya)"""
        self.quizzes_data = {}
        logger.info("[Info] Memori soal dibersihkan untuk bagian baru.")

    def close(self):
        import time

        time.sleep(3)
        if hasattr(self, "browser"):
            self.browser.close()
        if hasattr(self, "playwright"):
            self.playwright.stop()
        logger.info("[Playwright] Browser closed.")
