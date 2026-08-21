# utils/scraper_exam.py
# Scraper for ASP.NET Web Forms-based exam platforms

import re
import time
from typing import Any, Dict, List

from utils.logger import logger

from .scraper_base import BaseScraper


class ExamScraper(BaseScraper):
    def __init__(
        self,
        url: str,
        username: str,
        password: str,
        api_key: str = None,
        model_name: str = None,
        provider: str = "gemini",
        no_session: bool = False,
    ):
        # Init parent
        super().__init__(url, username, password, no_session)

        # Extract base URL from user-provided URL
        from urllib.parse import urlparse

        parsed = urlparse(url)
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"

        # Internal state untuk tracking 'Bagian' (Block)
        self.current_block_questions = []

        try:
            self.login(api_key, model_name, provider)
        except Exception as e:
            logger.error(f"{e}")
            self.close()
            raise e

    def login(self, api_key: str = None, model_name: str = None, provider: str = "gemini"):
        """
        Automatic login with captcha solving using Gemini/Groq Vision.
        Falls back to manual login if no API key provided.

        Args:
            api_key: API key for vision captcha solving
            model_name: Model to use
            provider: 'gemini' or 'groq'
        """
        from utils.ai_utils import solve_captcha_with_vision

        logger.info(f"Membuka halaman login: {self.base_url}")
        self.page.goto(self.base_url)
        self.page.wait_for_load_state("domcontentloaded")

        # Check if we can auto-solve captcha
        if api_key and model_name:
            logger.info(f"Auto-login mode: solving captcha with {provider.capitalize()} Vision...")

            max_attempts = 3
            for attempt in range(max_attempts):
                logger.info(f"  > Login attempt {attempt + 1}/{max_attempts}")

                # Fill credentials
                self.page.fill("#txtNPM", self.username)
                self.page.fill("#txtKey", self.password)

                # Screenshot the captcha image
                captcha_img = self.page.locator("#imgKode")
                if captcha_img.is_visible():
                    captcha_data = captcha_img.screenshot()

                    # Solve captcha with Vision API
                    captcha_text = solve_captcha_with_vision(
                        captcha_data, api_key, model_name, provider
                    )

                    if captcha_text:
                        self.page.fill("#txtKode", captcha_text)
                        self.page.click("#btnLogin")
                        self.page.wait_for_load_state("networkidle")

                        # Check if login succeeded (not still on login page)
                        if (
                            "#pnlLogin" not in self.page.content()
                            or "Pakta" in self.page.content()
                        ):
                            logger.info("✓ Login successful!")
                            break
                        else:
                            logger.warning(
                                "  > Login failed, retrying with new captcha..."
                            )
                            # Refresh captcha
                            refresh_btn = self.page.locator("#btnRefresh")
                            if refresh_btn.is_visible():
                                refresh_btn.click()
                                self.page.wait_for_load_state("networkidle")
                    else:
                        logger.warning("  > Captcha solving failed, refreshing...")
                        refresh_btn = self.page.locator("#btnRefresh")
                        if refresh_btn.is_visible():
                            refresh_btn.click()
                            self.page.wait_for_load_state("networkidle")
        else:
            # --- FALLBACK: MANUAL LOGIN ---
            print("\n" + "!" * 50)
            logger.info("PERHATIAN: Website ini menggunakan Captcha Gambar.")
            logger.info(
                "Silakan isi NPM, Password, dan Captcha di Browser yang terbuka secara MANUAL."
            )
            logger.info(
                "Klik 'Sign In' sampai berhasil masuk ke halaman Pakta Integritas."
            )
            print("!" * 50)

            input(
                "\n>>> JIKA SUDAH LOGIN BERHASIL, TEKAN ENTER DI SINI UNTUK LANJUT... <<<"
            )

        # --- FASE OTOMATIS (Pakta Integritas) ---
        logger.info("Memeriksa Pakta Integritas...")

        # Cek apakah ada checkbox konfirmasi
        chk_konfirm = self.page.locator("#chkKonfirm")
        btn_konfirm = self.page.locator("#btnKonfirm")

        if chk_konfirm.is_visible():
            logger.info("  > Menyetujui Pakta Integritas...")
            chk_konfirm.check()
            time.sleep(0.5)
            btn_konfirm.click()
            self.page.wait_for_load_state("networkidle")
            logger.info("  > Pakta Integritas disetujui.")
        else:
            logger.info(
                "  > Halaman Pakta Integritas tidak ditemukan (Mungkin sudah lewat)."
            )

        logger.info("Siap melakukan scraping soal.")

    def fetch_all_quizzes(self) -> Dict[int, Dict[str, Any]]:
        """
        ASP.NET Logic:
        Navigasi soal menggunakan tombol angka (lnkSoal1, lnkSoal2, dst).
        Kita harus klik satu per satu untuk mengambil teks soal.
        """
        logger.info("Mengambil daftar soal yang tersedia di Bagian ini...")

        # Cari semua tombol navigasi soal yang aktif (Class: tombol-ers)
        # ID pattern: lnkSoal1, lnkSoal2, dst.
        nav_buttons = self.page.locator("div.tombol-ers a[id^='lnkSoal']")
        count = nav_buttons.count()

        logger.info(f"Ditemukan {count} soal pada Bagian (Block) ini.")

        # Kita simpan ID tombol untuk di-iterate
        # (Playwright element handle bisa stale jika page reload, jadi kita simpan ID string-nya saja)
        button_ids = []
        for i in range(count):
            id_val = nav_buttons.nth(i).get_attribute("id")
            if id_val:
                button_ids.append(id_val)

        for btn_id in button_ids:
            # Extract nomor soal dari ID (lnkSoal1 -> 1)
            q_num_match = re.search(r"lnkSoal(\d+)", btn_id)
            if not q_num_match:
                continue
            q_num_real = int(q_num_match.group(1))

            logger.info(f"  > Scraping Soal Nomor: {q_num_real}")

            # Klik tombol nomor soal dan tunggu PostBack
            self.page.click(f"#{btn_id}")
            self.page.wait_for_load_state("networkidle")  # Tunggu loading ASPX selesai

            # --- SCRAPING KONTEN ---
            # Selector berdasarkan HTML yang diberikan user

            # 1. Teks Soal
            # Lokasi: div.label-ers -> div.kolom-12 (biasanya di dalam span form-xxx)
            # Kita gunakan selector yang agak longgar agar tahan perubahan ID dinamis
            q_container = self.page.locator(".label-ers .kolom-12").first

            # Hapus elemen radio button dari teks soal jika ada
            q_text_raw = q_container.inner_text()

            # Bersihkan teks (biasanya soal ada di bagian atas sebelum opsi)
            # Karena struktur ASPX berantakan, kita ambil text node yang bukan label opsi
            # Cara termudah: Ambil text penuh, lalu hapus text opsi yang diketahui.
            # Tapi di sini kita coba ambil text dari div.baris pertama di dalam q_container
            q_text_el = q_container.locator(".baris .kolom-12").first
            if q_text_el.is_visible():
                q_text = q_text_el.inner_text()
            else:
                q_text = q_text_raw  # Fallback

            q_text = q_text.replace("\n", " ").strip()

            # 2. Pilihan Jawaban
            answers = []
            # Selector: div.form-check -> label
            options = self.page.locator(".form-check label")
            opt_count = options.count()

            # Cek opsi "Belum dijawab" (biasanya terakhir), kita skip
            valid_opts_count = opt_count
            last_opt_text = options.nth(opt_count - 1).inner_text()
            if "Belum dijawab" in last_opt_text:
                valid_opts_count -= 1

            for j in range(valid_opts_count):
                opt_text = options.nth(j).inner_text().strip()
                answers.append(opt_text)

            # Detect if question has images
            has_image = q_container.locator("img").count() > 0

            # Capture image if present
            image_data = None
            if has_image:
                try:
                    image_data = q_container.screenshot()
                    logger.info(
                        f"    [Q{q_num_real}] Captured image ({len(image_data)} bytes)"
                    )
                except Exception as e:
                    logger.warning(f"    [Q{q_num_real}] Failed to capture image: {e}")

            # Simpan data
            self.quizzes_data[q_num_real] = {
                "question_text": q_text,
                "answers": answers,
                "has_image": has_image,
                "image_data": image_data,
                "page_url": self.base_url,
                "button_id": btn_id,
            }

        return self.quizzes_data

    def save_answers(self, answers: Dict[str, str]) -> List[int]:
        logger.info("Memulai pengisian jawaban (Web Forms PostBack)...")

        successfully_filled = []

        def clean_str(text):
            return re.sub(r"\s+", " ", text).strip().lower().rstrip(".")

        # Urutkan pengisian berdasarkan nomor soal agar navigasi rapi
        sorted_q_ids = sorted([int(k) for k in answers.keys()])

        for q_num in sorted_q_ids:
            if q_num not in self.quizzes_data:
                continue

            ans_text = answers[str(q_num)]
            q_data = self.quizzes_data[q_num]
            btn_id = q_data.get("button_id")

            logger.info(f"  > Menuju Soal {q_num}...")

            # 1. Navigasi ke soal
            # Cek apakah kita sudah di soal yang benar (optimasi)
            # Tapi aman-nya klik tombol navigasi saja
            self.page.click(f"#{btn_id}")
            self.page.wait_for_load_state("networkidle")

            # 2. Cari Radio Button yang sesuai
            # Kita cari label yang text-nya match, lalu ambil ID radio-nya
            labels = self.page.locator(".form-check label")
            count = labels.count()
            clicked = False

            target_clean = clean_str(ans_text)

            for i in range(count):
                lbl_el = labels.nth(i)
                lbl_text = clean_str(lbl_el.inner_text())

                # Match Logic
                if target_clean in lbl_text or lbl_text in target_clean:
                    # Ambil atribut 'for' dari label untuk tahu ID radio button
                    radio_id = lbl_el.get_attribute("for")
                    if radio_id:
                        self.page.check(f"#{radio_id}")
                        clicked = True
                        successfully_filled.append(q_num)
                        logger.info(f"    Jawaban dipilih: {ans_text[:20]}...")
                        break

            if not clicked:
                logger.warning(
                    f"    [Gagal Match] Tidak menemukan opsi untuk: {ans_text[:20]}..."
                )
                continue

            # 3. SIMPAN JAWABAN
            # Di Ujian, tombol "Simpan & Tampilkan Nomor X" (Next) berfungsi sebagai Save.
            # Atau tombol "Simpan Nomor X" (Prev).
            # Kita klik tombol Next (lnkNext) untuk save.

            # Cek tombol Next
            next_btn = self.page.locator("#lnkNext")
            if next_btn.is_visible():
                next_btn.click()
                self.page.wait_for_load_state("networkidle")
            else:
                # Jika di soal terakhir, mungkin tombolnya beda atau harus klik navigasi lain
                # Biasanya tombol navigasi angka juga trigger save jika pindah nomor
                pass

        return successfully_filled

    def submit_final(self):
        """
        Menangani penyelesaian Bagian.
        Mendeteksi apakah ini bagian terakhir atau bukan.
        """
        # Deteksi apakah ini bagian terakhir
        try:
            current = self.page.locator("#lblBlok").inner_text()
            total = self.page.locator("#lblJumlahBlok").inner_text()
            is_last_part = current == total
        except Exception:
            is_last_part = False

        if is_last_part:
            logger.info("\n[!] TERDETEKSI INI ADALAH BAGIAN TERAKHIR.")
            logger.info("[!] SETELAH INI UJIAN AKAN BERAKHIR SEPENUHNYA.")

        # Sisa logikanya tetap sama karena ID elemennya identik
        finish_root_btn = self.page.locator("#lnkKeluarUjianRoot")

        if not finish_root_btn.is_visible():
            logger.info("Info: Tombol Keluar tidak ditemukan.")
            return

        finish_root_btn.click()

        modal = self.page.locator("#modalUjian")
        try:
            modal.wait_for(state="visible", timeout=3000)

            chk_confirm = modal.locator("#chkKonfirm")
            if chk_confirm.is_visible():
                chk_confirm.check()

            final_btn = modal.locator("#lnkKeluarUjian")
            final_btn.wait_for(state="visible", timeout=3000)

            final_btn.click()
            self.page.wait_for_load_state("networkidle")

            if is_last_part:
                logger.info("\n✅ UJIAN SELESAI SEPENUHNYA!")
            else:
                logger.info(
                    f"✅ Bagian {current} Selesai. Loading Bagian selanjutnya..."
                )

        except Exception as e:
            logger.info(f"Gagal submit final: {e}")
            logger.info("Coba submit manual di browser yang terbuka.")

    def get_current_block(self) -> int:
        """
        Mendeteksi kita sedang berada di Bagian (Block) nomor berapa
        berdasarkan elemen <span id="lblBlok">.
        """
        try:
            lbl = self.page.locator("#lblBlok")
            if lbl.is_visible():
                text = lbl.inner_text().strip()
                return int(text)
        except Exception:
            pass
        return 0
