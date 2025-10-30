# Lazy Quiz - Bot Otomatis untuk Kuis Moodle

## Pendahuluan

**Lazy Quiz** adalah sebuah skrip Python yang dirancang untuk mengotomatiskan proses pengerjaan kuis di platform e-learning Moodle. Proyek ini menggunakan Selenium untuk interaksi dengan browser dan dapat diintegrasikan dengan Google Gemini API untuk menjawab pertanyaan secara otomatis berdasarkan konten yang di-scrape.

Proyek ini dibuat sebagai studi kasus untuk eksplorasi dan pembelajaran dalam bidang:
-   Automasi Web dengan Selenium.
-   Web Scraping dengan BeautifulSoup.
-   Integrasi API dengan model AI generatif (Google Gemini).
-   Praktik terbaik dalam pengembangan perangkat lunak (konfigurasi, struktur proyek, penanganan error).

---

## 🚨 **Penting: Penafian (Disclaimer)**

**PROYEK INI DIBUAT HANYA UNTUK TUJUAN PENDIDIKAN DAN EKSPERIMENTAL.**

-   **Jangan Pernah** menggunakan skrip ini untuk mengerjakan ujian, kuis, atau tugas akademik yang sesungguhnya. Melakukan hal tersebut adalah bentuk kecurangan dan pelanggaran serius terhadap **integritas akademik**.
-   Konsekuensi dari kecurangan akademik bisa sangat berat, termasuk kegagalan mata kuliah, skorsing, atau bahkan dikeluarkan dari institusi pendidikan Anda.
-   **Pengguna bertanggung jawab penuh** atas segala tindakan yang dilakukan menggunakan kode ini. Pengembang tidak bertanggung jawab atas penyalahgunaan apa pun.

---

## ✨ Fitur

-   **Login Otomatis:** Skrip dapat secara otomatis login ke akun Moodle Anda.
-   **Scraping Kuis:** Mampu mengambil semua pertanyaan dan pilihan jawaban dari sebuah kuis, termasuk konten yang mengandung gambar (dengan mengambil teks alternatifnya).
-   **Menjawab dengan AI:** Terintegrasi dengan Google Gemini API untuk menganalisis pertanyaan dan memilih jawaban yang paling relevan.
-   **Mode Scrape-Saja:** Opsi untuk hanya mengambil data kuis dan menyimpannya ke file JSON tanpa mencoba menjawabnya.
-   **Mode Dry Run:** Fitur untuk menguji kredensial login dan koneksi API Key Gemini sebelum menjalankan proses penuh.
-   **Penanganan Rate Limit:** Secara otomatis berhenti sejenak dan mencoba lagi jika batas permintaan API tercapai, cocok untuk kuis dengan banyak soal.
-   **Struktur Output Terorganisir:** Setiap hasil eksekusi disimpan dalam folder unik dengan timestamp untuk kemudahan pelacakan.

---

## ⚙️ Kebutuhan Sistem

-   Python 3.8 atau yang lebih baru.
-   Browser Google Chrome.
-   [ChromeDriver](https://googlechromelabs.github.io/chrome-for-testing/) yang versinya **sesuai** dengan versi Google Chrome Anda.
-   API Key dari [Google AI Studio](https://aistudio.google.com/) (gratis untuk penggunaan pengembangan).

---

## 🚀 Cara Penggunaan

1.  **Clone Repositori**
    ```bash
    git clone https://github.com/username/lazy-quiz.git
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
    SELENIUM_USERNAME="NPM_ANDA"
    SELENIUM_PASSWORD="PASSWORD_VCLASS_ANDA"
    
    # (Opsional) Path ke chrome.exe jika tidak terdeteksi otomatis
    BROWSER_BINARY_LOCATION="C:/Program Files/Google/Chrome/Application/chrome.exe"
    
    # (Opsional) Diperlukan jika ingin menjawab dengan AI
    GEMINI_API_KEY="API_KEY_GEMINI_ANDA"
    GEMINI_MODEL="models/gemini-1.5-flash-latest" # atau 'models/gemini-pro'
    ```

4.  **Jalankan Skrip**

    -   **Dry Run (Mode Default untuk Tes Konfigurasi):**
        Jalankan tanpa argumen untuk memeriksa login dan API key.
        ```bash
        python main.py
        ```

    -   **Scrape & Jawab Otomatis dengan AI:**
        Gunakan flag `--url` diikuti dengan URL kuis.
        ```bash
        python main.py --url "https://v-class.gunadarma.ac.id/mod/quiz/view.php?id=xxxxxx"
        ```

    -   **Hanya Scrape (Tanpa Menjawab):**
        Tambahkan flag `--scrape-only`.
        ```bash
        python main.py --url "https://v-class.gunadarma.ac.id/mod/quiz/view.php?id=xxxxxx" --scrape-only
        ```

---

## 📁 Struktur Proyek
```
lazy-quiz/
├── .env # File konfigurasi (kredensial, API key)
├── main.py # Skrip utama untuk menjalankan program
├── requirements.txt # Daftar dependensi Python
├── utils/ # Modul-modul pembantu
│ ├── init.py
│ ├── quiz_scraper.py # Kelas utama untuk logika scraping dan interaksi browser
│ └── ai_utils.py # Fungsi-fungsi untuk berinteraksi dengan Gemini API
└── output/ # Folder tempat hasil scrape disimpan
└── Nama_Kuis_YYYY-MM-DD_HH-MM-SS/
├── scraped_questions.json
└── ai_answers.json
```

## 📜 Lisensi

Didistribusikan di bawah Lisensi MIT. Lihat `LICENSE` untuk informasi lebih lanjut.
