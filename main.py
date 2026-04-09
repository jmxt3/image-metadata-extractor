import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

BACKGROUNDS_DIR = Path(__file__).parent / "backgrounds"
OUTPUT_DIR = Path(__file__).parent / "output"
PROMPT = """Analyze this image and return a JSON object with exactly this structure:

{
  "metadata": {
    "color_space": "<e.g. RGB, Grayscale/Monochrome, CMYK>",
    "aspect_ratio": "<e.g. 3:2, 16:9>",
    "dimensions": "<width x height if detectable, otherwise estimated>"
  },
  "visual_techniques": {
    "composition": {
      "style": "<compositional style e.g. Minimalist Surrealism, Rule of Thirds>",
      "framing": "<how framing is used>",
      "balance": "<symmetrical or asymmetrical, and how>",
      "perspective": "<depth/perspective technique used>"
    },
    "lighting_and_shadow": {
      "light_source": "<direction and quality of light e.g. Hard Light from left>",
      "contrast": "<contrast technique e.g. High Chiaroscuro>",
      "shadow_types": "<types of shadows present and their effect>"
    },
    "texture_and_materials": {
      "surface_properties": [
        "<material description 1>",
        "<material description 2>"
      ]
    },
    "architectural_elements": {
      "geometry": "<geometric forms and their relationships>",
      "symbolism": "<any symbolic or art-historical references>"
    },
    "color_theory": {
      "palette": "<e.g. Monochromatic, Complementary, Analogous>",
      "effect": "<how the palette affects the mood or focus>"
    }
  }
}

Fill in all fields accurately based on the image."""
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
