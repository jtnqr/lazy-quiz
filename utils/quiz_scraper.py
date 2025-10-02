from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By


class QuizScraper:
    def __init__(self, driver, url, username, password):
        self.driver = driver
        self.__quizzes = {}
        self.__quiz_addresses = []
        self.__title = None

        self.__logged_in = self.__check_login_state()

        if self.__logged_in != True:
            self.__perform_login(username, password)

        self.driver.get(url)

        # Fetch title, quiz addresses, and quizzes
        self.__title = self.__fetch_quiz_title()
        self.__quiz_addresses = self.__fetch_quiz_addresses()
        self.__quizzes = self.__fetch_all_quizzes()

    def __perform_login(self, username, password):
        """
        Perform the login using provided credentials.

        Args:
            username (str): The username for login.
            password (str): The password for login.
        """

        if self.driver.current_url not in "https://v-class.gunadarma.ac.id/login/":
            self.driver.get("https://v-class.gunadarma.ac.id/login/")

        try:
            login_button = self.driver.find_element(By.ID, "loginbtn")
            username_field = self.driver.find_element(By.ID, "username")
            password_field = self.driver.find_element(By.ID, "password")
            username_field.send_keys(username)
            password_field.send_keys(password)
            login_button.click()

        except NoSuchElementException:
            cancel_button = self.driver.find_element(
                By.CSS_SELECTOR, "button[type='submit'][contains(text(), 'Cancel')]"
            )
            cancel_button.click()

        self.__logged_in = True

    def __check_login_state(self):
        if self.driver.current_url != "https://v-class.gunadarma.ac.id/login/":
            self.driver.get("https://v-class.gunadarma.ac.id/login/")

        try:
            self.driver.find_element(By.ID, "loginbtn")
            self.driver.find_element(By.ID, "username")
            self.driver.find_element(By.ID, "password")

            return False
        except NoSuchElementException:
            cancel_button = self.driver.find_element(
                By.CSS_SELECTOR, "button[type='submit'][contains(text(), 'Cancel')]"
            )
            cancel_button.click()

            return True

    def __fetch_quiz_addresses(self):
        """
        Extracts the URLs of the quizzes from the navigation buttons.

        Returns:
            list: A list of URLs of the quizzes.
        """
        nav_buttons = self.driver.find_elements(
            By.CSS_SELECTOR, ".qn_buttons .qnbutton"
        )
        return [button.get_attribute("href") for button in nav_buttons]

    def __fetch_quiz_title(self):
        """
        Fetches the title of a quiz from a web page using a WebDriver.

        Returns:
            str: The title of the quiz as a string.
        """
        try:
            title_element = self.driver.find_element(By.XPATH, "//a[@title='Quiz']")
            return title_element.text
        except NoSuchElementException:
            # If the title element is not found, return a default value or handle the error appropriately
            return "Title not found"

    def __fetch_quiz(self, question_number):
        """
        Fetches a single quiz with the specified question number.

        Args:
            question_number (int): The question number of the quiz to fetch.

        Returns:
            dict: A dictionary representing the question and its answers.
        """
        try:
            current_question_number = int(
                self.driver.find_element(By.CSS_SELECTOR, ".info .no .qno").text
            )

            if current_question_number != question_number:
                self.driver.get(self.__quiz_addresses[question_number - 1])

            question_text = self.driver.find_element(
                By.XPATH, "//div[@class='qtext']"
            ).text
            answer_choices = self.driver.find_elements(
                By.XPATH, "//div[@class='answer']//label"
            )
            answers = [answer_choice.text for answer_choice in answer_choices]

            return {f"{question_number}. {question_text}": answers}
        except NoSuchElementException:
            # If any element is not found, return a default value or handle the error appropriately
            return {"Error": "Quiz not found"}

    def __fetch_all_quizzes(self, num_quizzes=None):
        """
        Fetches all the quizzes and stores them in a dictionary.

        Args:
            num_quizzes (int, optional): The number of quizzes to fetch. Defaults to None (fetch all quizzes).

        Returns:
            dict: A dictionary containing all the quizzes.
        """
        if num_quizzes is None:
            num_quizzes = len(self.__quiz_addresses)

        self.__quizzes = {}
        for i in range(1, num_quizzes + 1):
            if i not in self.__quizzes or not self.__quizzes[i]:
                self.__quizzes[i] = self.__fetch_quiz(i)
        return self.__quizzes

    def __answer_quiz(self, question_number, answer):
        """
        Answers a quiz question with the specified answer.

        Args:
            question_number (int): The question number to answer.
            answer (str): The answer to select. Can be an answer choice or a literal answer.

        Returns:
            bool: True if the answer was successfully selected, False otherwise.
        """
        try:
            # Find the question element
            quiz_address = self.__quiz_addresses[question_number - 1]
            self.driver.get(quiz_address)

            # Find the answer element and click it
            answer_element = None
            try:
                # Try to find the answer choice element
                answer_element = self.driver.find_element(
                    By.XPATH, f"//*[text()='{answer}']"
                )
            except NoSuchElementException:
                # If answer choice element not found, try to find the literal answer element
                answer_element = self.driver.find_element(
                    By.XPATH, f"//*[contains(text(), '{answer}')]"
                )

            answer_element.click()
            return True
        except NoSuchElementException:
            # If any element is not found, return False or handle the error appropriately
            return False

    def answer_quizzes(self, answers):
        """
        Answers all the quizzes with the specified answers.

        Args:
            answers (dict): A dictionary containing the question numbers and their corresponding answers.
                The keys are the question numbers (int) and the values are the answers (str).
                The answers can be either answer choices or literal answers.
        """
        for question_number, answer in answers.items():
            self.__answer_quiz(question_number, answer)

    def get_title(self):
        """
        Get the title of the quiz.

        Returns:
            str: The title of the quiz as a string.
        """
        return self.__title

    def get_quiz_addresses(self):
        """
        Get the quiz addresses.

        Returns:
            list: A list of URLs of the quizzes.
        """
        return self.__quiz_addresses

    def get_quizzes(self):
        """
        Get the quizzes as a dictionary.

        Returns:
            dict: A dictionary containing all the quizzes.
        """
        return self.__quizzes
