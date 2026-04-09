import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

BACKGROUNDS_DIR = Path(__file__).parent / "backgrounds"
OUTPUT_DIR = Path(__file__).parent / "output"
PROMPT = "Extract the metadata and analyze the image techniques in JSON format."
MODEL = "gemini-2.5-flash-lite"
REQUEST_DELAY = 4  # seconds between requests (~15 RPM free-tier limit)
MAX_RETRIES = 3

MIME_TYPES = {
    ".webp": "image/webp",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


def main():
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set in .env")

    client = genai.Client(api_key=api_key)
    OUTPUT_DIR.mkdir(exist_ok=True)

    images = sorted(
        p for p in BACKGROUNDS_DIR.iterdir() if p.suffix.lower() in MIME_TYPES
    )

    for image_path in images:
        output_path = OUTPUT_DIR / f"{image_path.stem}.json"

        if output_path.exists():
            print(f"Skipped (already exists): {image_path.name}")
            continue

        mime_type = MIME_TYPES[image_path.suffix.lower()]
        image_bytes = image_path.read_bytes()

        print(f"Processing: {image_path.name} ...", end=" ", flush=True)
        response = None
        for attempt in range(MAX_RETRIES):
            try:
                response = client.models.generate_content(
                    model=MODEL,
                    contents=[
                        types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                        PROMPT,
                    ],
                    config={"response_mime_type": "application/json"},
                )
                break
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    wait = REQUEST_DELAY * (2 ** attempt)
                    print(f"retrying in {wait}s ({e})...", end=" ", flush=True)
                    time.sleep(wait)
                else:
                    print(f"ERROR (gave up after {MAX_RETRIES} attempts): {e}")

        if response is None:
            continue

        text = response.text or ""
        if not text.strip():
            print("ERROR (empty response)")
            continue

        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            print(f"ERROR (invalid JSON): {e}")
            continue

        time.sleep(REQUEST_DELAY)

        output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"saved to {output_path.relative_to(Path(__file__).parent)}")

    print("Done.")


if __name__ == "__main__":
    main()
