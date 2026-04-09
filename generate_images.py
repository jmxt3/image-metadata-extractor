import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.types import JobState

INPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR = Path(__file__).parent / "output_images"
MODEL = "gemini-2.5-flash-image"
POLL_INTERVAL = 15  # seconds between polling


def build_prompt(json_content: str) -> str:
    return (
        f"Build a new image 16:9 based on the following json: {json_content}. "
        "Do not include any text, words, letters, numbers, symbols, watermarks, or typography in the image."
    )


def main():
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set in .env")

    client = genai.Client(api_key=api_key)
    OUTPUT_DIR.mkdir(exist_ok=True)

    json_files = sorted(INPUT_DIR.glob("*.json"))
    if not json_files:
        print(f"No JSON files found in {INPUT_DIR}")
        return

    pending = [p for p in json_files if not (OUTPUT_DIR / f"{p.stem}.png").exists()]
    skipped = len(json_files) - len(pending)
    if skipped:
        print(f"Skipped {skipped} already-processed file(s).")
    if not pending:
        print("Nothing to do.")
        return

    print(f"Submitting batch of {len(pending)} request(s)...")

    inline_requests = [
        types.InlinedRequest(
            contents=build_prompt(p.read_text(encoding="utf-8")),
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )
        for p in pending
    ]

    batch_job = client.batches.create(model=MODEL, src=inline_requests)
    print(f"Batch job created: {batch_job.name}")

    terminal_states = {
        JobState.JOB_STATE_SUCCEEDED,
        JobState.JOB_STATE_FAILED,
        JobState.JOB_STATE_CANCELLED,
    }
    while batch_job.state not in terminal_states:
        print(f"State: {batch_job.state} — polling again in {POLL_INTERVAL}s...")
        time.sleep(POLL_INTERVAL)
        batch_job = client.batches.get(name=batch_job.name or "")

    if batch_job.state != JobState.JOB_STATE_SUCCEEDED:
        print(f"Batch job ended with state: {batch_job.state}")
        return

    print("Batch complete. Saving images...")

    inlined_responses = (batch_job.dest and batch_job.dest.inlined_responses) or []
    for json_path, inlined in zip(pending, inlined_responses):
        output_path = OUTPUT_DIR / f"{json_path.stem}.png"

        if inlined.error:
            print(f"ERROR ({json_path.name}): {inlined.error}")
            continue

        response = inlined.response
        candidates = response.candidates if response else []
        image_part = next(
            (
                part
                for candidate in (candidates or [])
                for part in (candidate.content.parts or [] if candidate.content else [])
                if part.inline_data and part.inline_data.data
            ),
            None,
        )
        if image_part is None or image_part.inline_data is None:
            print(f"ERROR (no image in response for {json_path.name})")
            continue

        output_path.write_bytes(image_part.inline_data.data)  # type: ignore[arg-type]
        print(f"Saved: {output_path.relative_to(Path(__file__).parent)}")

    print("Done.")


if __name__ == "__main__":
    main()
