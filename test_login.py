# test_login.py

import os
import time

from dotenv import load_dotenv
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# --- Konstanta Hanya Untuk Tes Login ---
LOGIN_URL = "https://v-class.gunadarma.ac.id/login/index.php"
# Selector unik yang hanya ada setelah login berhasil
POST_LOGIN_SUCCESS_SELECTOR = ".action-menu"
USERNAME_SELECTOR = (By.ID, "username")
PASSWORD_SELECTOR = (By.ID, "password")
LOGIN_BUTTON_SELECTOR = (By.ID, "loginbtn")


def test_login():
    """
    Skrip tes terisolasi untuk melakukan login dan memverifikasinya.
    """
    load_dotenv()
    username = os.environ.get("SELENIUM_USERNAME")
    password = os.environ.get("SELENIUM_PASSWORD")
    binary_location = os.environ.get("BROWSER_BINARY_LOCATION")

    if not all([username, password]):
        print(
            "Error: Pastikan SELENIUM_USERNAME dan SELENIUM_PASSWORD ada di file .env"
        )
        return

    options = Options()
    # Hapus '--headless' jika Anda ingin melihat browser secara langsung saat tes
    # options.add_argument("--headless")
    options.add_argument("--start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    if binary_location:
        options.binary_location = binary_location

    print("Memulai WebDriver untuk tes login...")
    with webdriver.Chrome(options=options) as driver:
        wait = WebDriverWait(
            driver, 15
        )  # Beri waktu tunggu sedikit lebih lama untuk tes

        try:
            print(f"Membuka halaman login: {LOGIN_URL}")
            driver.get(LOGIN_URL)

            print("Menunggu form login muncul...")
            username_field = wait.until(
                EC.visibility_of_element_located(USERNAME_SELECTOR)
            )
            password_field = driver.find_element(*PASSWORD_SELECTOR)
            login_button = driver.find_element(*LOGIN_BUTTON_SELECTOR)

            print("Mengisi username dan password...")
            username_field.send_keys(username)
            password_field.send_keys(password)

            print("Mengklik tombol 'Log in'...")
            login_button.click()

            print("Menunggu verifikasi login berhasil (mencari elemen dasbor)...")
            wait.until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, POST_LOGIN_SUCCESS_SELECTOR)
                )
            )

            # Jika baris di atas berhasil tanpa error, berarti login sukses
            print("\n=====================")
            print("  LOGIN BERHASIL!  ")
            print("=====================")
            print(f"URL saat ini: {driver.current_url}")
            print("Skrip akan ditutup dalam 5 detik...")
            time.sleep(5)

        except TimeoutException:
            print("\n========================================================")
            print("  LOGIN GAGAL: Timeout terjadi saat menunggu halaman dasbor.")
            print("========================================================")
            print(
                "Ini berarti setelah mengklik 'Log in', elemen dasbor tidak pernah muncul."
            )
            print("Kemungkinan penyebab:")
            print("1. Username atau Password salah.")
            print("2. Halaman login hanya me-refresh dirinya sendiri (masalah sesi).")
            print("3. Koneksi internet sangat lambat.")

            screenshot_file = "login_test_failure.png"
            driver.save_screenshot(screenshot_file)
            print(
                f"\nScreenshot halaman kegagalan disimpan sebagai '{screenshot_file}'"
            )

        except Exception as e:
            print(f"\nTerjadi error tak terduga: {e}")


### Jalankan Tes ###
if __name__ == "__main__":
    test_login()
