# Tver State University Helper Bot

This bot offers several features to help students manage their academic life:

## Features

- **Record Scores**: Allows students to record their scores for different subjects.
- **Group and Faculty Selection**: Students can select any group and faculty, which are parsed from the university's website.
- **Schedule Parsing**: Parses the schedule based on the selected group, providing up-to-date information on classes and timings.

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/Soda-Na/TvSU-Helper
    cd tver-state-university-helper-bot
    ```

2. Install the dependencies:
    ```sh
    pip install -r requirements.txt
    ```

3. Create a `.env` file in the root directory and add your bot token:
    ```
    BOT_TOKEN=your_bot_token_here
    ```

4. Run the bot:
    ```sh
    python main.py
    ```