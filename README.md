# Episode Renamer for Infuse

A simple yet useful macOS application built with Python and PyQt6 designed to rename TV show files into a format compatible with [Infuse](https://firecore.com/infuse) automatic metadata scraping.

[App Screenshot](![alt text](assets/image-3.png))

## Features

* **Infuse-Ready Formatting:** Automatically renames files to the standard `Show Name SxxExx` format required by media scrapers.
* **Local LLMs support:** using local small LLMs automatically extract the show name, season number and episode number start from the original file names
* **Drag & Drop:** Easily drag folders directly into the app.
* **Smart Preview:** See exactly what your files will look like before applying changes.
* **Backup & Restore:** Safety first! The app creates a `rename_backup.txt` file in the directory. If something goes wrong, you can switch to the **Restore** tab and revert the filenames instantly.
* **Filters:** Option to include/exclude video files or subtitles.

## AI Autodetection

This application supports an AI-powered function to automatically detect show names and episode numbers using local Large Language Models (LLMs). This ensures privacy and runs completely offline.

### Requirements

- **Ollama:** You must have [Ollama](https://ollama.com/) installed and running.
- **Model:** The recommended model is `qwen3:8b`,`gemma2:9b`,`gemma3:12b`. To install, run:
```bash
  ollama pull qwen3:8b
```

### Performance & Hardware

- **Recommended RAM:** 16GB or higher
- **Tested Environment:** Runs smoothly on Apple Silicon M1 Pro with 16GB RAM

> **Note:** While other models available on Ollama can be used, `qwen3:8b` is recommended for the best balance of accuracy and speed. `gemma2:9b` and `gemma3:12b` also tested on my local machine without problem, llama3.1 should not be used as it doest not follow the prompt and does not output json format sometimes.

![alt text](assets/image-2.png)
![alt text](assets/image-1.png)

## Requirements

* Python 3.10
* PyQt6

## UI
![alt text](assets/image.png)


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
    python episode_renamer_app_llm.py
    ```
2.  **Rename Tab:**
    * Select your TV show folder (or drag and drop it).
    * Using AI Auto-Detect if you have ollama running
    * Enter the **Show Name** and **Season** (e.g., S1).
    * Set the **Starting Episode** number.
    * Click **Preview Renaming** to check the results.
    * Click **Apply Renaming** to finish.

3.  **Restore Tab:**
    * If you made a mistake, select the folder containing the `rename_backup.txt` file.
    * Click **Load Backup File** and then **Restore Original Filenames**.

## License

Apache License 2.0
