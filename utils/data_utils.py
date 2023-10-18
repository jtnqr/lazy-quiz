from datetime import datetime
import json, time, os
import re


def process_dictionary(dictionary, print_output=True):
    """
    Processes the dictionary of quizzes and prints or returns the formatted output.

    Args:
        dictionary (dict): The dictionary of quizzes to process.
        print_output (bool, optional): Specifies whether to print the output. Defaults to True.

    Returns:
        str or None: The formatted output as a string if print_output is False, otherwise None.
    """
    # Initialize an empty string to store the formatted output
    result = ""

    # Check if the dictionary uses question numbers as keys or question texts as keys
    if isinstance(list(dictionary.keys())[0], str):
        # Process the dictionary with question texts as keys
        for question, answers in dictionary.items():
            # Add the question to the result string
            result += f"{question}\n"

            # Add each answer to the result string
            for answer in answers:
                result += f"{answer}\n"
    else:
        # Process the dictionary with question numbers as keys
        for num, question_answers in dictionary.items():
            question = list(question_answers.keys())[0]
            answers = question_answers[question]

            # Add the question to the result string
            result += f"{question}\n"

            # Add each answer to the result string
            for answer in answers:
                result += f"{answer}\n"

    # Print or return the result based on the print_output parameter
    if print_output:
        print(result)
    else:
        return result


def store_dictionary_as_json(dictionary, title, directory):
    """
    Stores the dictionary as a JSON file with a unique filename.

    Args:
        dictionary (dict): The dictionary to store as JSON.
        title (str): The title to include in the filename.
        directory (str): The directory path to store the JSON file.

    Returns:
        None
    """
    # Remove characters not allowed in filenames on Windows and Unix systems
    title = re.sub(r'[\/:*?"<>|]', "_", title)
    # Replace spaces with underscores
    title = re.sub(r" ", "_", title)
    # Replace consecutive underscores with a single underscore
    title = re.sub(r"_{2,}", "_", title)

    # Get the current time and format it as YY-MM-DD_HH-MM-SS
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Create the filename with the title and the current time
    filename = f"{title}_{current_time}.json"
    # Specify the filepath relative to the directory parameter
    filepath = os.path.join(directory, filename)

    # Open the file and write the dictionary as JSON
    with open(filepath, "w") as file:
        json.dump(dictionary, file, indent=2)
