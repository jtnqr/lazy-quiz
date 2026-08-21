# utils/scraper_moodle.py
# Logika Spesifik Moodle (V-Class) menggunakan Playwright

import re
import time
from typing import Any, Dict, List

from utils.logger import logger

from .scraper_base import BaseScraper


class MoodleScraper(BaseScraper):
    def __init__(self, url: str, username: str, password: str, no_session: bool = False):
        # Panggil init parent untuk setup Playwright & Browser
        super().__init__(url, username, password, no_session)

        # Extract base URL from user-provided URL
        from urllib.parse import urlparse

        parsed = urlparse(url)
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"

        # Eksekusi Flow Login & Init
        try:
            self.login()
            # Jika URL bukan halaman login, coba inisialisasi kuis
            if url and "login" not in url:
                self._initialize_quiz_attempt(url)
        except Exception as e:
            logger.error(f"{e}")
            self.close()  # Bersihkan browser jika gagal init
            raise e

    def login(self):
        logger.info(f"Melakukan login ke Moodle sebagai: {self.username}...")
        try:
            self.page.goto(f"{self.base_url}/login/index.php")

            # Cek session reuse (jika cookies masih valid)
            if "Dashboard" in self.page.title() or "My courses" in self.page.title():
                logger.info("Session valid terdeteksi. Skip login.")
                return

            # Isi form login
            self.page.fill('input[name="username"]', self.username)
            self.page.fill('input[name="password"]', self.password)

            # Klik login dan tunggu navigasi
            # Menggunakan Promise.all untuk memastikan navigasi selesai
            with self.page.expect_navigation(timeout=15000):
                self.page.click("button#loginbtn")  # Selector default moodle

            # Validasi
            if "login" in self.page.url and "Invalid login" in self.page.content():
                raise ValueError("Login Gagal! Username/Password salah.")

            logger.info("Login Berhasil.")
            # Save session for next time
            self.session_manager.save_session(self.context, self.username)

        except Exception as e:
            # Fallback jika timeout atau selector beda
            if "Dashboard" in self.page.title():
                logger.info("Login berhasil (Fallback check).")
                # Save session for next time
                self.session_manager.save_session(self.context, self.username)
                return
            raise ConnectionError(f"Gagal Login: {e}")

    def _initialize_quiz_attempt(self, url: str):
        logger.info(f"Mengakses halaman kuis: {url}")
        self.page.goto(url)
        self.page.wait_for_load_state("domcontentloaded")

        # 1. Cek Tombol "Continue attempt" (Lanjut)
        continue_btn = (
            self.page.locator("button:has-text('Continue attempt')")
            .or_(self.page.locator("a:has-text('Continue attempt')"))
            .or_(self.page.locator("button:has-text('Lanjutkan attempt')"))
            .or_(self.page.locator("a:has-text('Lanjutkan attempt')"))
        )

        # 1b. Alternatif teks Continue attempt (Jika yang pertama tidak ditemukan)
        continue_btn_alt = (
            self.page.locator("button:has-text('Continue the last attempt')")
            .or_(self.page.locator("a:has-text('Continue the last attempt')"))
            .or_(self.page.locator("button:has-text('Lanjutkan attempt terakhir')"))
            .or_(self.page.locator("a:has-text('Lanjutkan attempt terakhir')"))
        )

        # 2. Cek Tombol "Attempt quiz now" (Baru)
        attempt_btn = self.page.locator("button:has-text('Attempt quiz now')").or_(
            self.page.locator("input[value='Attempt quiz now']")
        )

        clicked_continue = False
        if continue_btn.count() > 0 and continue_btn.first.is_visible():
            logger.info("Melanjutkan attempt yang sudah ada...")
            continue_btn.first.click()
            self.page.wait_for_load_state("domcontentloaded")
            clicked_continue = True
        elif continue_btn_alt.count() > 0 and continue_btn_alt.first.is_visible():
            logger.info("Melanjutkan attempt yang sudah ada (alternatif)...")
            continue_btn_alt.first.click()
            self.page.wait_for_load_state("domcontentloaded")
            clicked_continue = True
        elif attempt_btn.count() > 0 and attempt_btn.first.is_visible():
            logger.info("Memulai attempt baru...")
            attempt_btn.first.click()

            # 3. Handle Modal Konfirmasi (Time Limit / Password)
            # Biasanya ada tombol 'Start attempt' di dalam modal atau halaman baru
            start_confirm = self.page.locator("input[name='submitbutton']").or_(
                self.page.locator("button:has-text('Start attempt')")
            )

            # Tunggu sebentar barangkali modal muncul
            try:
                if start_confirm.count() > 0:
                    # Jika tombol konfirmasi ada, klik
                    if start_confirm.first.is_visible():
                        logger.info("  > Konfirmasi 'Start attempt'...")
                        start_confirm.first.click()
                        self.page.wait_for_load_state("domcontentloaded")
            except Exception:
                pass

        # Validasi akhir
        if "attempt.php" in self.page.url:
            self.attempt_url = self.page.url
            logger.info(f"Masuk di halaman attempt: {self.attempt_url}")
        else:
            raise Exception(
                "Gagal masuk ke halaman attempt kuis. Cek URL atau status kuis."
            )

    def fetch_all_quizzes(self) -> Dict[int, Dict[str, Any]]:
        if not self.attempt_url:
            raise Exception("Attempt URL belum siap.")

        logger.info("Mengambil struktur navigasi soal (Scraping)...")
        # Pastikan di halaman attempt
        if self.page.url != self.attempt_url:
            self.page.goto(self.attempt_url)

        # Ambil navigasi (pagination)
        nav_locator = self.page.locator(".qn_buttons .qnbutton")
        pages_to_visit = []
        seen_urls = set()

        # Tambahkan current page
        seen_urls.add(self.page.url)
        pages_to_visit.append(self.page.url)

        # Loop link navigasi
        count = nav_locator.count()
        for i in range(count):
            href = nav_locator.nth(i).get_attribute("href")
            if href and "javascript" not in href and href != "#":
                if href not in seen_urls:
                    seen_urls.add(href)
                    pages_to_visit.append(href)

        pages_to_visit = sorted(list(seen_urls))
        logger.info(f"Total halaman kuis: {len(pages_to_visit)}")

        global_q_counter = 1

        for page_url in pages_to_visit:
            logger.info(f"  > Scraping Halaman: {page_url}")
            if self.page.url != page_url:
                self.page.goto(page_url)
                self.page.wait_for_load_state("domcontentloaded")

            # Selector soal Moodle
            questions = self.page.locator(".que.multichoice")
            q_count = questions.count()

            for i in range(q_count):
                q_div = questions.nth(i)

                # Ambil Teks Soal
                q_text_el = q_div.locator(".qtext")
                if not q_text_el.is_visible():
                    continue

                raw_text = q_text_el.inner_text()
                # Bersihkan nomor soal (misal "1. Apa itu...")
                q_text = re.sub(r"^[0-9]+\.\s*", "", raw_text)

                # Cek Gambar
                has_image = q_text_el.locator("img").count() > 0

                # Ambil Pilihan Jawaban
                answers = []
                ans_divs = q_div.locator(".answer div[class^='r']")  # r0, r1

                for j in range(ans_divs.count()):
                    ans_row = ans_divs.nth(j)
                    label = ans_row.locator("label")
                    if label.count() > 0:
                        ans_text = label.inner_text()
                        # Bersihkan label (a. Jawaban)
                        ans_text = re.sub(r"^[a-z]\.\s*", "", ans_text)

                        if label.locator("img").count() > 0:
                            has_image = True

                        answers.append(ans_text)

                # Capture image if question has images
                image_data = None
                if has_image:
                    try:
                        # Screenshot the question container
                        image_data = q_div.screenshot()
                        logger.info(
                            f"    [Q{global_q_counter}] Captured image ({len(image_data)} bytes)"
                        )
                    except Exception as e:
                        logger.warning(
                            f"    [Q{global_q_counter}] Failed to capture image: {e}"
                        )

                self.quizzes_data[global_q_counter] = {
                    "question_text": q_text.strip(),
                    "answers": answers,
                    "has_image": has_image,
                    "image_data": image_data,
                    "page_url": page_url,
                }
                global_q_counter += 1

        return self.quizzes_data

    def save_answers(self, answers: Dict[str, str]) -> List[int]:
        logger.info("Memulai pengisian jawaban (UI Interaction)...")

        def clean_str(text):
            text = text.replace("\xa0", " ")
            text = re.sub(r"\s+", " ", text).strip().lower()
            return text.rstrip(".")

        # Grouping jawaban per halaman URL agar efisien
        page_buckets = {}
        for q_num_str, ans_text in answers.items():
            q_num = int(q_num_str)
            if q_num in self.quizzes_data:
                p_url = self.quizzes_data[q_num]["page_url"]
                if p_url not in page_buckets:
                    page_buckets[p_url] = {}
                page_buckets[p_url][q_num] = ans_text

        successfully_filled = []

        for page_url, q_map in page_buckets.items():
            logger.info(f"  > Mengakses halaman: {page_url}")
            if self.page.url != page_url:
                self.page.goto(page_url)
                self.page.wait_for_load_state("domcontentloaded")

            page_success_count = 0

            # 1. SCAN page sekaligus untuk build map (Optimization O(N))
            logger.info("    Scanning page for questions...")
            question_divs = self.page.locator(".que.multichoice")
            count = question_divs.count()
            dom_map = {}  # Key: cleaned_text_snippet, Value: Locator

            for i in range(count):
                q_div = question_divs.nth(i)
                # Ambil text dari DOM sekali saja
                raw_q_text = q_div.locator(".qtext").inner_text()
                q_text_dom = clean_str(raw_q_text)
                q_text_dom = re.sub(r"^[0-9]+\.\s*", "", q_text_dom)

                # Gunakan 100 karakter pertama sebagai key lookup yang efisien
                search_key = q_text_dom[:100]
                dom_map[search_key] = q_div

            # 2. ISI Jawaban (Lookup O(1))
            page_success_count = 0
            for q_num, ans_text in q_map.items():
                cache_q_text = self.quizzes_data[q_num]["question_text"]
                search_key = clean_str(cache_q_text)[:100]

                # Cari di map yang sudah dibangun
                found_div = dom_map.get(search_key)

                if found_div:
                    ans_ai_clean = clean_str(ans_text)
                    options = found_div.locator(".answer div[class^='r']")
                    clicked = False

                    # Loop opsi jawaban (jumlah opsi sedikit, jadi ok loop biasa)
                    count_opts = options.count()
                    for j in range(count_opts):
                        opt_row = options.nth(j)
                        label = opt_row.locator("label")
                        lbl_clean = clean_str(
                            re.sub(r"^[a-z]\.\s*", "", label.inner_text())
                        )

                        # Fuzzy Match Sederhana
                        if ans_ai_clean in lbl_clean or lbl_clean in ans_ai_clean:
                            radio = opt_row.locator("input[type='radio']")
                            if radio.is_visible():
                                radio.check()  # Playwright check()
                                clicked = True
                                successfully_filled.append(q_num)
                                page_success_count += 1
                                break

                    if not clicked:
                        logger.info(f"    [Gagal Match Opsi] Soal {q_num}")
                else:
                    # Fallback jika key lookup gagal (sangat jarang terjadi jika logic sama)
                    logger.info(
                        f"    [Gagal HTML] Soal {q_num} tidak ditemukan di DOM map."
                    )

            logger.info(f"    Berhasil mengisi {page_success_count} soal.")

            # Klik Next Page untuk save (Moodle save on navigate)
            # Kecuali ini halaman terakhir
            next_btn = self.page.locator("input[name='next']")
            if next_btn.is_visible():
                next_btn.click()
                self.page.wait_for_load_state("domcontentloaded")

        return successfully_filled

    def submit_final(self):
        logger.info("Memulai proses Final Submit...")
        if not self.attempt_url:
            return

        # Ke halaman Summary
        summary_url = self.attempt_url.replace("attempt.php", "summary.php")
        summary_url = re.sub(r"&page=\d+", "", summary_url)
        self.page.goto(summary_url)

        # Cari tombol "Submit all and finish"
        finish_btn = self.page.locator("button:has-text('Submit all and finish')").or_(
            self.page.locator("input[value='Submit all and finish']")
        )

        if finish_btn.count() > 0:
            finish_btn.first.click()

            # Handle Modal Konfirmasi (Moodle Modern)
            confirm_btn = (
                self.page.locator(
                    ".moodle-dialogue-bd input[value='Submit all and finish']"
                )
                .or_(self.page.locator(".modal-footer button.btn-primary"))
                .or_(self.page.locator("input[id='id_submitbutton']"))
            )  # Fallback

            time.sleep(1)  # Tunggu animasi modal
            if confirm_btn.count() > 0 and confirm_btn.first.is_visible():
                confirm_btn.first.click()
                self.page.wait_for_load_state("networkidle")
                logger.info("SUKSES: Kuis telah disubmit (Finished).")
            else:
                logger.info("SUKSES: Submit (Tanpa Modal).")
        else:
            logger.info("Info: Tombol submit tidak ditemukan (Mungkin sudah selesai).")
