# Lazy-Quiz

## Table of Contents

- [Description](#description)
- [Installation](#installation)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)

## Description

The project contains a Python script that utilizes Selenium to scrape quizzes from a specified URL. The `QuizScraper` class enables users to fetch quiz titles, URLs, and questions along with their corresponding answer choices from the targeted web page. It also provides functionality to answer quizzes automatically. The script is designed to handle the login process, extract quiz data, and store it in an organized dictionary format.

## Installation

To run this project, you need to install the following dependencies:

- Python 3
- Chromedriver
- Selenium
- dotenv

You can install the necessary dependencies using pip:

```bash
pip install selenium
pip install python-dotenv
```

## Usage

To use the project, follow these steps:

1. Clone the repository.
2. Set up a `.env` file with the required environment variables:

```Dotenv
URL=your_url_here
SELENIUM_USERNAME=your_username_here
SELENIUM_PASSWORD=your_password_here
BROWSER_BINARY_LOCATION=your_browser_binary_location_here
```

3. Run the script using the following command:

```bash
python main.py
```

## Contributing

Contributions to the project are welcome. To contribute, follow these steps:

1. Fork the repository.
2. Create a new branch.
3. Make your changes and commit them.
4. Push your changes to the branch.
5. Submit a pull request.

## License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT).
