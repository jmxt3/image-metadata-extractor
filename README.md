# Image Metadata Extractor

Extracts image techniques and metadata from images using Google Gemini, saving results as JSON files.

## Requirements

- [uv](https://docs.astral.sh/uv/) package manager
- Python 3.13+
- A Gemini API key

## Setup

1. Clone the repository and navigate to the project folder.

2. Install dependencies:
   ```bash
   uv sync
   ```

3. Create a `.env` file in the project root and add your Gemini API key:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

4. Place images in the `backgrounds/` folder (`.webp`, `.jpg`, `.jpeg`, `.png` supported).

## Usage

```bash
uv run main.py
```

Results are saved as JSON files in the `output/` folder, one per image.

Re-running the script skips any images that have already been processed.
