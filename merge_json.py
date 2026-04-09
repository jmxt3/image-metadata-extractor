import json
import glob
import os

output_dir = os.path.join(os.path.dirname(__file__), "output")
merged = []

EXCLUDE_METADATA_FIELDS = {"filename", "format", "content_type"}

for filepath in sorted(glob.glob(os.path.join(output_dir, "*.json"))):
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        for item in data:
            if isinstance(item.get("metadata"), dict):
                for field in EXCLUDE_METADATA_FIELDS:
                    item["metadata"].pop(field, None)
        merged.extend(data)
    else:
        if isinstance(data.get("metadata"), dict):
            for field in EXCLUDE_METADATA_FIELDS:
                data["metadata"].pop(field, None)
        merged.append(data)

out_path = os.path.join(output_dir, "merged.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(merged, f, indent=2)

print(f"Merged {len(glob.glob(os.path.join(output_dir, '*.json'))) - 1} files -> {out_path} ({len(merged)} items)")
