from __future__ import annotations

import json
from typing import Dict


def decode_text(raw_bytes: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "latin-1"):
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw_bytes.decode("utf-8", errors="replace")


def parse_lang_payload(file_name: str, raw_bytes: bytes) -> Dict[str, str]:
    text = decode_text(raw_bytes)
    lower_name = file_name.lower()
    if lower_name.endswith(".json"):
        data = json.loads(text)
        return {str(key): str(value) for key, value in data.items() if isinstance(value, (str, int, float, bool))}
    if lower_name.endswith(".lang"):
        result: Dict[str, str] = {}
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            result[key.strip()] = value.strip()
        return result
    raise ValueError(f"Unsupported language file: {file_name}")


def dump_lang_payload(data: Dict[str, str], extension: str) -> str:
    normalized_extension = extension.lower().lstrip(".")
    ordered = dict(sorted(data.items(), key=lambda item: item[0]))
    if normalized_extension == "json":
        return json.dumps(ordered, ensure_ascii=False, indent=2) + "\n"
    if normalized_extension == "lang":
        lines = [f"{key}={value}" for key, value in ordered.items()]
        return "\n".join(lines) + "\n"
    raise ValueError(f"Unsupported language format: {extension}")
