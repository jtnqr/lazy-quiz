import json
import os
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from utils.quiz_scraper import QuizScraper
import utils.data_utils as data

# Load environment variables from a .env file
load_dotenv()

# Define the URL, username, and password using environment variables
url = os.environ.get("URL")
username = os.environ.get("SELENIUM_USERNAME")
password = os.environ.get("SELENIUM_PASSWORD")
binary_location = os.environ.get("BROWSER_BINARY_LOCATION")

# Configure Chrome WebDriver options
options = Options()
options.add_argument("--start-minimized")
options.add_experimental_option("excludeSwitches", ["enable-logging"])
options.binary_location = binary_location

cookies_file = "session.json"

# Check if a session cookies file exists
# Load cookies from a JSON file
# if os.path.exists(cookies_file):
#     with open(cookies_file, "r") as cookie_file:
#         cookies = json.load(cookie_file)
# else:
#     cookies = []

try:
    # Create a Chrome WebDriver instance using a context manager
    with webdriver.Chrome(options=options) as driver:
        # Apply loaded session cookies
        # driver.add_cookie(cookies)

        # print(driver.get_cookies())

        # driver.refresh()

        # print(driver.get_cookies())
        # Create a QuizScraper instance
        qz = QuizScraper(driver, url, username, password)

        # Store quizzes as JSON
        # data.store_dictionary_as_json(qz.get_quizzes(), qz.get_title(), "quiz")

        # Get the cookies from the WebDriver
        # cookies = driver.get_cookies()

        # Save cookies as JSON to a file
        # with open("cookies.json", "w") as cookie_file:
        #     json.dump(cookies, cookie_file)


except Exception as e:
    # Handle exceptions gracefully (e.g., log the error)
    print(f"An error occurred: {str(e)}")
