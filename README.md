# Episode Renamer for Infuse

A simple yet powerful macOS application built with Python and PyQt6 designed to rename TV show files into a format compatible with [Infuse](https://firecore.com/infuse) automatic metadata scraping.

![App Screenshot](screenshot_placeholder.png)
*(Note: You can upload your screenshot to the repo later and link it here)*

## Features

* **Infuse-Ready Formatting:** Automatically renames files to the standard `Show Name SxxExx` format required by media scrapers.
* **Drag & Drop:** Easily drag folders directly into the app.
* **Smart Preview:** See exactly what your files will look like before applying changes.
* **Backup & Restore:** Safety first! The app creates a `rename_backup.txt` file in the directory. If something goes wrong, you can switch to the **Restore** tab and revert the filenames instantly.
* **Filters:** Option to include/exclude video files or subtitles.

## Requirements

* Python 3.x
* PyQt6

## UI
![alt text](image.png)

## Installation

1.  Clone this repository:
    ```bash
    git clone [https://github.com/Shoucong/episodes_renamer.git](https://github.com/Shoucong/episodes_renamer.git)
    cd episodes_renamer
    ```

2.  Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

1.  Run the application:
    ```bash
    python episode_renamer_app.py
    ```
2.  **Rename Tab:**
    * Select your TV show folder (or drag and drop it).
    * Enter the **Show Name** and **Season** (e.g., S1).
    * Set the **Starting Episode** number.
    * Click **Preview Renaming** to check the results.
    * Click **Apply Renaming** to finish.

3.  **Restore Tab:**
    * If you made a mistake, select the folder containing the `rename_backup.txt` file.
    * Click **Load Backup File** and then **Restore Original Filenames**.

## License

Apache License 2.0
