# utils/quiz_scraper.py

import re
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup


class QuizScraper:
    def __init__(self, url: str, username: str, password: str):
        self.base_url = "https://v-class.gunadarma.ac.id"
        self.login_url = f"{self.base_url}/login/index.php"
        # Headers supaya terlihat seperti browser asli
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        # Inisialisasi Session (Menyimpan Cookies/MoodleSession secara otomatis)
        self.session = requests.Session()
        self.session.headers.update(self.headers)

        # State Internal
        self.sesskey: str = ""
        self.quiz_id: Optional[str] = self._extract_id_from_url(url)
        self.attempt_url: Optional[str] = None

        # Cache Data
        self.__quizzes: Dict[int, Dict[str, Any]] = {}

        print("--- [Requests] Memulai Sesi ---")
        self._login(username, password)

        # Jika URL diberikan saat init, langsung siapkan attempt
        if url and "login" not in url:
            self._initialize_quiz_attempt(url)

    def _extract_id_from_url(self, url: str) -> Optional[str]:
        if not url:
            return None
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        if "id" in params:
            return params["id"][0]
        elif "cmid" in params:
            return params["cmid"][0]
        return None

    def _login(self, username, password):
        print(f"Melakukan login sebagai: {username}...")

        # 1. GET Halaman Login untuk ambil logintoken
        try:
            resp = self.session.get(self.login_url, timeout=10)
            soup = BeautifulSoup(resp.content, "lxml")
            logintoken_input = soup.find("input", {"name": "logintoken"})
            if not logintoken_input:
                # Cek jika ternyata sudah login (session reuse)
                if "Dashboard" in soup.text or "My courses" in soup.text:
                    print("Session valid terdeteksi. Skip login.")
                    self._extract_sesskey_from_soup(soup)
                    return
                raise Exception("Tidak dapat menemukan token login.")

            logintoken = logintoken_input["value"]
        except Exception as e:
            raise ConnectionError(f"Gagal memuat halaman login: {e}")

        # 2. POST Credentials
        payload = {
            "anchor": "",
            "logintoken": logintoken,
            "username": username,
            "password": password,
            "rememberusername": "1",
        }

        login_resp = self.session.post(self.login_url, data=payload)

        # 3. Validasi Login & Ambil Sesskey
        if "login/index.php" in login_resp.url or "Invalid login" in login_resp.text:
            raise ValueError("Login Gagal! Cek username/password di .env")

        self._extract_sesskey_from_soup(BeautifulSoup(login_resp.content, "lxml"))
        print("Login Berhasil.")

    def _extract_sesskey_from_soup(self, soup):
        # Sesskey biasanya ada di link logout: ".../login/logout.php?sesskey=XYZ"
        logout_link = soup.find("a", href=re.compile(r"sesskey="))
        if logout_link:
            qs = parse_qs(urlparse(logout_link["href"]).query)
            self.sesskey = qs.get("sesskey", [""])[0]
        else:
            # Fallback: cari di input hidden form apa saja
            inp = soup.find("input", {"name": "sesskey"})
            if inp:
                self.sesskey = inp["value"]

    def _initialize_quiz_attempt(self, url: str):
        """Masuk ke halaman kuis, klik 'Attempt now', handle konfirmasi, atau 'Continue attempt'"""
        print(f"Mengakses halaman kuis: {url}")
        resp = self.session.get(url)
        soup = BeautifulSoup(resp.content, "lxml")

        # Update sesskey jika belum punya
        if not self.sesskey:
            self._extract_sesskey_from_soup(soup)

        # Cek tombol Continue (Lanjut)
        continue_link = soup.find("a", href=re.compile(r"attempt\.php"))

        # Cek tombol Start baru (Form)
        start_form = soup.find("form", action=re.compile(r"startattempt\.php"))

        if continue_link:
            print("Melanjutkan attempt yang sudah ada...")
            self.attempt_url = continue_link["href"]
            self.session.get(self.attempt_url)  # Refresh halaman agar session update

        elif start_form:
            print("Memulai attempt baru...")
            action_url = start_form["action"]
            data = {
                inp["name"]: inp["value"]
                for inp in start_form.find_all("input", type="hidden")
            }

            # Handle tombol submit di halaman view
            submit_btn = start_form.find("button", type="submit")
            if submit_btn and submit_btn.get("name"):
                data[submit_btn["name"]] = submit_btn.get("value", "")

            # POST 1: Klik "Attempt quiz now"
            start_resp = self.session.post(action_url, data=data)

            # --- [FIX UTAMA DISINI] ---
            # Cek apakah kita tertahan di halaman konfirmasi (URL masih startattempt.php)
            if "startattempt.php" in start_resp.url:
                print("  > Menemukan halaman konfirmasi (Time Limit/Password)...")
                soup_conf = BeautifulSoup(start_resp.content, "lxml")

                # Cari form konfirmasi (biasanya id="moodle-dialogue-..." atau form generik ke startattempt.php)
                conf_form = soup_conf.find(
                    "form", action=re.compile(r"startattempt\.php")
                )

                if conf_form:
                    # Ambil hidden fields lagi (sesskey, cmid, dll)
                    conf_data = {
                        inp["name"]: inp.get("value", "")
                        for inp in conf_form.find_all("input", type="hidden")
                    }

                    # Cari tombol konfirmasi (biasanya id="id_submitbutton")
                    conf_btn = conf_form.find(
                        "button", id="id_submitbutton"
                    ) or conf_form.find("input", id="id_submitbutton")

                    if conf_btn and conf_btn.get("name"):
                        conf_data[conf_btn["name"]] = conf_btn.get("value", 1)

                    print("  > Mengirim konfirmasi 'Start attempt'...")
                    start_resp = self.session.post(conf_form["action"], data=conf_data)

            self.attempt_url = start_resp.url

        elif "attempt.php" in resp.url:
            self.attempt_url = resp.url
        else:
            raise Exception(
                "Tidak dapat masuk ke kuis. Pastikan URL benar dan kuis sedang aktif."
            )

        # Final Check: Pastikan kita benar-benar di attempt.php
        if "attempt.php" not in self.attempt_url:
            raise Exception(f"Gagal memulai kuis. Terjebak di: {self.attempt_url}")

    def get_sanitized_title(self) -> str:
        return f"Quiz_{self.quiz_id}" if self.quiz_id else "Quiz_Unknown"

    def fetch_all_quizzes(self) -> Dict[int, Dict[str, Any]]:
        if not self.attempt_url:
            raise Exception("Attempt URL belum siap.")

        print("Mengambil struktur navigasi soal...")
        resp = self.session.get(self.attempt_url)
        soup = BeautifulSoup(resp.content, "lxml")

        # Ambil semua link halaman navigasi (kotak-kotak nomor soal di kanan)
        nav_links = soup.select(".qn_buttons .qnbutton")
        pages_to_visit = []
        for btn in nav_links:
            href = btn.get("href")
            if href:
                # FIX: Jika href="#", itu artinya halaman ini sendiri.
                # Kita skip request ke "#", tapi nanti kita tambahkan attempt_url manual.
                if href == "#" or "javascript" in href:
                    continue
                pages_to_visit.append(href)

        # PENTING: Tambahkan halaman saat ini (self.attempt_url) ke daftar scrape
        # agar halaman aktif tidak terlewat
        if self.attempt_url:
            pages_to_visit.append(self.attempt_url)

        unique_pages = sorted(list(set(pages_to_visit)), key=lambda x: x)
        if not unique_pages:
            unique_pages = [self.attempt_url]

        print(f"Total halaman kuis: {len(unique_pages)}")

        global_q_counter = 1

        for page_url in unique_pages:
            print(f"  > Scraping Halaman: {page_url}")
            page_resp = self.session.get(page_url)
            page_soup = BeautifulSoup(page_resp.content, "lxml")

            # Cari container soal (class 'que multichoice')
            questions = page_soup.select(".que.multichoice")

            for q_div in questions:
                # 1. Ambil Teks Soal
                q_text_el = q_div.select_one(".qtext")
                if not q_text_el:
                    continue

                q_text = q_text_el.get_text(" ", strip=True)
                q_text = re.sub(
                    r"^[0-9]+\.\s*", "", q_text
                )  # Hapus nomor soal bawaan moodle

                # 2. Cek Gambar
                has_image = bool(q_text_el.find("img"))

                # 3. Ambil Pilihan Jawaban
                answers = []
                # Pilihan jawaban ada di div class='r0', 'r1', dst.
                answer_divs = q_div.select(".answer div[class^='r']")
                for ans in answer_divs:
                    label = ans.find("label")
                    if label:
                        ans_text = label.get_text(" ", strip=True)
                        ans_text = re.sub(r"^[a-z]\.\s*", "", ans_text)
                        # Cek gambar hanya di dalam label jawaban, bukan div pembungkus
                        if label.find("img"):
                            has_image = True
                        answers.append(ans_text)

                self.__quizzes[global_q_counter] = {
                    "question_text": q_text,
                    "answers": answers,
                    "has_image": has_image,
                    "page_url": page_url,  # Simpan URL halaman ini untuk proses submit nanti
                }
                global_q_counter += 1

        return self.__quizzes

    def save_answers(self, answers: Dict[str, str]):
        """
        Hanya mengirim jawaban ke Moodle (Save), tapi TIDAK melakukan Final Submit.
        Versi Robust: Menangani spasi aneh dan case-insensitive matching.
        """
        print("Memulai pengisian jawaban ke server (Saving)...")

        # Helper untuk membersihkan string (hapus spasi ganda, lowercase, hapus titik di akhir)
        def clean_str(text):
            text = text.replace("\xa0", " ")  # Hapus Non-breaking space
            text = (
                re.sub(r"\s+", " ", text).strip().lower()
            )  # Normalisasi spasi & lowercase
            return text.rstrip(".")  # Hapus titik di akhir kalimat

        page_buckets = {}
        for q_num_str, ans_text in answers.items():
            q_num = int(q_num_str)
            if q_num in self.__quizzes:
                p_url = self.__quizzes[q_num]["page_url"]
                if p_url not in page_buckets:
                    page_buckets[p_url] = {}
                page_buckets[p_url][q_num] = ans_text

        for page_url, q_map in page_buckets.items():
            print(f"  > Mengisi halaman: {page_url}")

            resp = self.session.get(page_url)
            soup = BeautifulSoup(resp.content, "lxml")
            form = soup.find("form", id="responseform")

            if not form:
                print("    [Error] Form tidak ditemukan di halaman ini.")
                continue

            payload = {
                inp["name"]: inp.get("value", "")
                for inp in form.find_all("input", type="hidden")
                if inp.get("name")
            }
            payload["next"] = "Next page"

            count_filled = 0

            for q_num, ans_text in q_map.items():
                target_div = None

                # Ambil teks soal dari cache dan bersihkan
                cache_q_text_raw = self.__quizzes[q_num]["question_text"]
                # Ambil 30 karakter pertama yang sudah dibersihkan untuk kunci pencarian
                search_key = clean_str(cache_q_text_raw)[:30]

                # Cari div soal yang cocok
                question_divs = soup.select(".que.multichoice")
                if not question_divs:
                    # Fallback untuk tipe soal lain (misal True/False)
                    question_divs = soup.select(".que")

                for q_div in question_divs:
                    q_text_el = q_div.select_one(".qtext")
                    if not q_text_el:
                        continue

                    curr_text_raw = q_text_el.get_text(" ", strip=True)
                    # Hapus nomor soal (misal "10.")
                    curr_text_clean = re.sub(r"^[0-9]+\.\s*", "", curr_text_raw)

                    if search_key in clean_str(curr_text_clean):
                        target_div = q_div
                        break

                if target_div:
                    found_option = False
                    options = target_div.select(".answer div[class^='r']")

                    # Bersihkan jawaban AI
                    ans_ai_clean = clean_str(ans_text)

                    for opt in options:
                        label = opt.find("label")
                        if not label:
                            continue

                        label_text_raw = label.get_text(" ", strip=True)
                        # Hapus "a.", "b."
                        label_text_clean = re.sub(r"^[a-z]\.\s*", "", label_text_raw)

                        lbl_web_clean = clean_str(label_text_clean)

                        # MATCHING LOGIC:
                        # 1. Cek if "Jawaban AI" ada di dalam "Opsi Web" (Substring)
                        # 2. Cek if "Opsi Web" ada di dalam "Jawaban AI" (Reverse Substring)
                        if (
                            ans_ai_clean in lbl_web_clean
                            or lbl_web_clean in ans_ai_clean
                        ):
                            radio = opt.find("input", type="radio")
                            if radio:
                                payload[radio["name"]] = radio["value"]
                                prefix = radio["name"].split("_")[0]
                                seq_inp = soup.find(
                                    "input", {"name": f"{prefix}_:sequencecheck"}
                                )
                                if seq_inp:
                                    payload[seq_inp["name"]] = seq_inp["value"]
                                found_option = True
                                count_filled += 1
                                break

                    if not found_option:
                        print(f"    [Gagal] Soal {q_num}: Opsi jawaban tidak cocok.")
                        print(f"      - AI: '{ans_text}'")
                        print(
                            f"      - Web (First 20 chars): {[clean_str(o.text)[:20] for o in options]}"
                        )
                else:
                    print(
                        f"    [Gagal] Soal {q_num}: Teks soal tidak ditemukan di HTML."
                    )
                    print(f"      - Cache (Cari): '{search_key}...'")

            self.session.post(form["action"], data=payload)
            print(f"    Berhasil menyimpan {count_filled} jawaban di halaman ini.")

    def submit_final(self):
        """
        Melakukan klik 'Submit all and finish'.
        """
        print("Memulai proses Final Submit...")

        # Cek halaman attempt terakhir atau summary
        if not self.attempt_url:
            return

        # Akses halaman summary
        # Biasanya patternnya: summary.php?attempt=...&cmid=...
        summary_url = self.attempt_url.replace("attempt.php", "summary.php")
        # Hapus page parameter jika ada
        summary_url = re.sub(r"&page=\d+", "", summary_url)

        resp = self.session.get(summary_url)
        soup = BeautifulSoup(resp.content, "lxml")

        # Cari form final submit
        finish_form = soup.find("form", action=re.compile(r"processattempt\.php"))
        if finish_form:
            fin_data = {
                inp["name"]: inp.get("value", "")
                for inp in finish_form.find_all("input", type="hidden")
            }

            # Post final
            res = self.session.post(finish_form["action"], data=fin_data)
            if res.status_code == 200:
                print("SUKSES: Kuis telah disubmit (Finished).")
            else:
                print(f"Gagal submit. Status code: {res.status_code}")
        else:
            print(
                "Info: Tidak menemukan tombol konfirmasi akhir (mungkin sudah selesai)."
            )

    def set_quiz_data(self, data: Dict[str, Any]):
        """
        Memasukkan data kuis dari cache eksternal ke dalam class instance.
        Penting agar fungsi save_answers bisa bekerja tanpa scraping ulang.
        """
        self.__quizzes = {}
        for k, v in data.items():
            # JSON keys selalu string, kita ubah ke int agar cocok dengan logic internal
            self.__quizzes[int(k)] = v
        print(
            f"  [Info] Berhasil memuat {len(self.__quizzes)} soal ke dalam memori scraper."
        )
