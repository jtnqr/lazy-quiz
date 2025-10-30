# Lazy Quiz - Bot Otomatis untuk Kuis Moodle

## Pendahuluan

**Lazy Quiz** adalah sebuah skrip Python yang dirancang untuk mengotomatiskan proses pengerjaan kuis di platform e-learning Moodle. Proyek ini menggunakan Selenium untuk interaksi dengan browser dan terintegrasi dengan Google Gemini API untuk menjawab pertanyaan berbasis teks secara otomatis.

Proyek ini dibuat sebagai studi kasus untuk eksplorasi dan pembelajaran dalam bidang:

- Automasi Web dengan Selenium.
- Web Scraping dengan BeautifulSoup.
- Integrasi API dengan model AI generatif (Google Gemini).
- Desain Command-Line Interface (CLI) yang ramah pengguna.
- Praktik terbaik dalam pengembangan perangkat lunak (konfigurasi, struktur proyek, penanganan error).

---

## 🚨 **Penting: Penafian (Disclaimer)**

**PROYEK INI DIBUAT HANYA UNTUK TUJUAN PENDIDIKAN DAN EKSPERIMENTAL.**

- **Jangan Pernah** menggunakan skrip ini untuk mengerjakan ujian, kuis, atau tugas akademik yang sesungguhnya. Melakukan hal tersebut adalah bentuk kecurangan dan pelanggaran serius terhadap **integritas akademik**.
- Konsekuensi dari kecurangan akademik bisa sangat berat, termasuk kegagalan mata kuliah, skorsing, atau bahkan dikeluarkan dari institusi pendidikan Anda.
- **Pengguna bertanggung jawab penuh** atas segala tindakan yang dilakukan menggunakan kode ini. Pengembang tidak bertanggung jawab atas penyalahgunaan apa pun.

---

## ✨ Fitur

- **Login Otomatis:** Skrip akan melakukan login ke akun Moodle Anda setiap kali dijalankan.
- **Alur Kuis Otomatis:** Mampu menangani seluruh alur kuis, mulai dari mengklik "Attempt quiz", "Continue last attempt", menangani popup konfirmasi, hingga menavigasi antar soal.
- **Scraping Cerdas:** Mampu mengambil semua pertanyaan dan pilihan jawaban, serta mendeteksi soal yang berisi gambar untuk dilewati.
- **Menjawab dengan AI:** Terintegrasi dengan Google Gemini API untuk menganalisis pertanyaan dan memilih jawaban yang paling relevan.
- **Mode Eksekusi Ganda:**
  - **Mode Interaktif:** Jalankan skrip tanpa argumen dan Anda akan dipandu untuk memasukkan URL.
  - **Mode Non-Interaktif:** Gunakan _flags_ seperti `--url` untuk menjalankan skrip sepenuhnya secara otomatis.
- **Sistem Cache Cerdas:** Secara otomatis menyimpan pertanyaan yang sudah di-scrape ke _cache_. Pada eksekusi berikutnya untuk kuis yang sama, skrip akan melewatkan proses scraping yang lambat.
- **Fitur Berbagi Jawaban:** Menghasilkan file "kunci jawaban" berformat JSON yang bisa dibagikan ke pengguna lain, memungkinkan mereka mengisi kuis secara otomatis tanpa perlu akses API.

---

## ⚙️ Kebutuhan Sistem

- Python 3.8 atau yang lebih baru.
- Browser Google Chrome.
- Dependensi Python yang tercantum di `requirements.txt`.

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
    # Ganti kredensial berikut dengan milik Anda
    SELENIUM_USERNAME="USERNAME_VCLASS_ANDA"
    SELENIUM_PASSWORD="PASSWORD_VCLASS_ANDA"

    # (Opsional) Path ke chrome.exe jika tidak terdeteksi otomatis
    BROWSER_BINARY_LOCATION="C:/Program Files/Google/Chrome/Application/chrome.exe"

    # (Opsional) Diperlukan jika ingin menjawab dengan AI
    GEMINI_API_KEY="API_KEY_GEMINI_ANDA"
    GEMINI_MODEL="gemini-pro"
    ```

4.  **Jalankan Skrip**

    - **Mode Interaktif (Penggunaan Utama):**
      Jalankan skrip tanpa argumen. Anda akan diminta untuk memasukkan URL kuis.

      ```bash
      python main.py
      ```

    - **Mode Non-Interaktif (Untuk Otomasi/Scripting):**
      Gunakan _flag_ `--url` untuk menjalankan proses penuh secara otomatis.

      ```bash
      python main.py --url "https://v-class.gunadarma.ac.id/mod/quiz/view.php?id=xxxxxx"
      ```

    - **Menggunakan File Kunci Jawaban (Sharing):**
      Gunakan _flag_ `--answer-file` untuk mengisi jawaban dari file JSON yang sudah ada.

      ```bash
      python main.py --url "https://v-class.gunadarma.ac.id/mod/quiz/view.php?id=xxxxxx" --answer-file "path/ke/file_jawaban.json"
      ```

    - **Opsi Tambahan:**
      - `--scrape-only`: Hanya mengambil pertanyaan, tidak menjawab.
      - `--no-cache`: Memaksa scraping baru dan mengabaikan cache.
      - `--dry-run`: Menjalankan tes koneksi untuk login dan API, lalu keluar.

---

## 📁 Struktur Proyek

```
lazy-quiz/
├── .env # File konfigurasi (kredensial, API key)
├── main.py # Skrip utama untuk menjalankan program
├── requirements.txt # Daftar dependensi Python
├── utils/ # Modul-modul pembantu
│ ├── quiz_scraper.py # Kelas utama untuk logika scraping dan interaksi browser
│ └── ai_utils.py # Fungsi-fungsi untuk berinteraksi dengan Gemini API
├── cache/ # Folder tempat data pertanyaan yang sudah di-scrape disimpan
└── output/ # Folder tempat hasil (misal: file jawaban) disimpan
```

## 📜 Lisensi

Proyek ini didistribusikan di bawah Lisensi MIT. Lihat file `LICENSE` untuk informasi lebih lanjut.
