# Lazy Quiz v2.0 - Bot Otomatis Kuis Moodle (HTTP Version)

## Pendahuluan

**Lazy Quiz** adalah skrip Python cerdas yang dirancang untuk mengotomatiskan pengerjaan kuis di platform e-learning Moodle.

🚀 **Pembaruan Versi 2.0:**
Proyek ini telah mengalami **refactoring total**. Tidak lagi menggunakan Selenium (Browser Automation) yang berat, versi ini beralih menggunakan **`requests` dan `BeautifulSoup`** (HTTP Protocol Automation).

**Apa bedanya dengan versi lama?**

- **Sangat Ringan & Cepat:** Tidak perlu membuka browser Chrome. Memproses kuis dalam hitungan detik.
- **Headless Ready:** Bisa berjalan di server Linux (VPS), Terminal, atau bahkan **Termux (Android)**.
- **Lebih Stabil:** Menggunakan manajemen sesi HTTP native, meminimalisir error akibat loading page yang lambat.

Proyek ini tetap terintegrasi dengan **Google Gemini AI** untuk menganalisis dan menjawab pertanyaan secara otomatis.

---

## 🚨 **Penting: Penafian (Disclaimer)**

**PROYEK INI DIBUAT HANYA UNTUK TUJUAN PENDIDIKAN DAN EKSPERIMENTAL.**

- **Jangan Pernah** menggunakan skrip ini untuk mengerjakan ujian, kuis, atau tugas akademik yang sesungguhnya. Melakukan hal tersebut adalah bentuk kecurangan dan pelanggaran serius terhadap **integritas akademik**.
- Konsekuensi dari kecurangan akademik bisa sangat berat, termasuk kegagalan mata kuliah, skorsing, atau bahkan dikeluarkan dari institusi pendidikan Anda.
- **Pengguna bertanggung jawab penuh** atas segala tindakan yang dilakukan menggunakan kode ini. Pengembang tidak bertanggung jawab atas penyalahgunaan apa pun.

---

## ✨ Fitur Baru (v2.0)

- **HTTP Session Management:** Login dan manajemen _cookies_ (MoodleSession) dilakukan secara otomatis di latar belakang tanpa browser.
- **Auto-Fill & Save (Safe Mode):**
  - Bot akan **mengisi dan menyimpan** jawaban ke server Moodle secara otomatis.
  - **Human-in-the-loop:** Secara default, bot **TIDAK** akan melakukan _Final Submit_. Bot akan berhenti dan meminta konfirmasi Anda, memberi Anda kesempatan untuk memeriksa jawaban di browser sebelum disubmit.
- **Auto-Submit:** Opsi argumen `--auto-submit` untuk Anda yang ingin bot langsung melakukan _Submit all and finish_ tanpa konfirmasi.
- **Smart Scraping:** Mendeteksi navigasi halaman (pagination) dan melewati soal bergambar secara otomatis.
- **Integrasi AI:** Menggunakan Google Gemini untuk menjawab soal pilihan ganda berbasis teks.
- **Cache System:** Menyimpan soal yang sudah diambil agar tidak perlu _request_ ulang jika terjadi gangguan koneksi.

---

## ⚙️ Kebutuhan Sistem

- **Python 3.8** atau yang lebih baru.
- Koneksi Internet.
- Akun Google Gemini API (Gratis).
- **TIDAK PERLU** Google Chrome atau WebDriver.

---

## 🚀 Cara Penggunaan

1.  **Clone Repositori**

    ```bash
    git clone https://github.com/jtnqr/lazy-quiz.git
    cd lazy-quiz
    ```

2.  **Instal Dependensi**

    ```bash
    pip install -r requirements.txt
    ```

3.  **Siapkan File Konfigurasi (`.env`)**
    Salin file `.env.example` menjadi `.env` dan isi dengan kredensial Anda.

    ```bash
    # Ganti kredensial berikut dengan akun Moodle/V-Class Anda
    MOODLE_USERNAME="USERNAME_ANDA"
    MOODLE_PASSWORD="PASSWORD_ANDA"

    # API Key Google Gemini (Wajib untuk fitur AI)
    GEMINI_API_KEY="AIzaSy....."
    GEMINI_MODEL="gemini-pro"
    ```

4.  **Jalankan Skrip**

    - **Mode Interaktif (Rekomendasi):**
      Jalankan tanpa argumen. Skrip akan meminta URL kuis, mengisi jawaban, lalu meminta konfirmasi sebelum submit.

      ```bash
      python main.py
      ```

    - **Mode Non-Interaktif (Langsung URL):**

      ```bash
      python main.py --url "https://v-class.gunadarma.ac.id/mod/quiz/attempt.php?attempt=xxxxx"
      ```

    - **Mode Auto-Submit (Langsung Kumpul):**
      Gunakan flag ini jika Anda ingin bot langsung melakukan _Submit all and finish_ tanpa konfirmasi.

      ```bash
      python main.py --url "..." --auto-submit
      ```

    - **Opsi Tambahan:**
      - `--scrape-only`: Hanya mengambil soal dan simpan ke JSON (tidak menjawab/mengisi ke Moodle).
      - `--answer-file "file.json"`: Mengisi kuis menggunakan jawaban dari file JSON lokal (tanpa AI).
      - `--no-cache`: Paksa ambil ulang soal dari server.
      - `--dry-run`: Tes login dan koneksi API tanpa mengakses kuis.

---

## 📁 Struktur Proyek

```
lazy-quiz/
├── .env # Konfigurasi kredensial
├── main.py # Entry point (CLI & Logic Controller)
├── requirements.txt # Daftar library (requests, beautifulsoup4, google-generativeai)
├── utils/
│ ├── quiz_scraper.py # Core Logic: HTTP Requests, CSRF Handling, HTML Parsing
│ └── ai_utils.py # Integrasi Gemini API
├── cache/ # Penyimpanan sementara soal (JSON)
└── output/ # Hasil jawaban (Shareable JSON)
```

## 📜 Lisensi

Proyek ini didistribusikan di bawah Lisensi MIT. Lihat file `LICENSE` untuk informasi lebih lanjut.
