from __future__ import annotations

import json
import re
from typing import Callable, Dict, Iterable, List, Tuple

from openai import OpenAI


ProgressCallback = Callable[[str], None]


class OpenAICompatibleTranslator:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        batch_size: int = 40,
        custom_prompt: str = "",
        progress: ProgressCallback | None = None,
    ) -> None:
        self.client = OpenAI(
            api_key=api_key or "not-needed",
            base_url=base_url or None,
        )
        self.model = model
        self.batch_size = max(1, batch_size)
        self.custom_prompt = custom_prompt.strip()
        self.progress = progress or (lambda _message: None)

    def translate_entries(
        self,
        entries: Dict[str, str],
        *,
        source_lang: str,
        target_lang: str,
    ) -> Dict[str, str]:
        translated: Dict[str, str] = {}
        batches = self._chunk_entries(entries.items())
        for index, batch in enumerate(batches, start=1):
            payload = dict(batch)
            batch_label = f"{index}/{len(batches)}"
            self.progress(f"Batch {batch_label}: sending {len(payload)} entries to {self.model}")
            translated.update(
                self._translate_batch_with_retry(
                    payload,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    batch_label=batch_label,
                )
            )
            self.progress(f"Batch {batch_label}: completed")
        return translated

    def _translate_batch_with_retry(
        self,
        payload: Dict[str, str],
        *,
        source_lang: str,
        target_lang: str,
        batch_label: str,
    ) -> Dict[str, str]:
        try:
            parsed = self._request_translation(
                payload,
                source_lang=source_lang,
                target_lang=target_lang,
            )
        except Exception as exc:
            if len(payload) == 1:
                key, original_value = next(iter(payload.items()))
                self.progress(
                    f"Batch {batch_label}: failed on key {key}, keep source text. Reason: {exc}"
                )
                return {key: original_value}

            self.progress(
                f"Batch {batch_label}: request failed for {len(payload)} entries, retrying in smaller batches. Reason: {exc}"
            )
            return self._split_batch_and_retry(
                payload,
                source_lang=source_lang,
                target_lang=target_lang,
                batch_label=batch_label,
            )

        completed: Dict[str, str] = {}
        missing: Dict[str, str] = {}
        for key, original_value in payload.items():
            value = parsed.get(key)
            if isinstance(value, str) and value.strip():
                completed[key] = value
            else:
                missing[key] = original_value

        if missing:
            self.progress(
                f"Batch {batch_label}: model omitted {len(missing)} entries, retrying missing items."
            )
            if len(missing) == 1:
                key, original_value = next(iter(missing.items()))
                try:
                    retried = self._request_translation(
                        missing,
                        source_lang=source_lang,
                        target_lang=target_lang,
                    )
                except Exception as exc:
                    self.progress(
                        f"Batch {batch_label}: retry failed on key {key}, keep source text. Reason: {exc}"
                    )
                    retried = {}
                value = retried.get(key)
                completed[key] = value if isinstance(value, str) and value.strip() else original_value
                return completed

            completed.update(
                self._split_batch_and_retry(
                    missing,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    batch_label=f"{batch_label}.retry",
                )
            )

        for key, original_value in payload.items():
            completed.setdefault(key, original_value)
        return completed

    def _split_batch_and_retry(
        self,
        payload: Dict[str, str],
        *,
        source_lang: str,
        target_lang: str,
        batch_label: str,
    ) -> Dict[str, str]:
        items = list(payload.items())
        midpoint = max(1, len(items) // 2)
        left_payload = dict(items[:midpoint])
        right_payload = dict(items[midpoint:])
        translated: Dict[str, str] = {}

        translated.update(
            self._translate_batch_with_retry(
                left_payload,
                source_lang=source_lang,
                target_lang=target_lang,
                batch_label=f"{batch_label}.1",
            )
        )
        if right_payload:
            translated.update(
                self._translate_batch_with_retry(
                    right_payload,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    batch_label=f"{batch_label}.2",
                )
            )
        return translated

    def _request_translation(
        self,
        payload: Dict[str, str],
        *,
        source_lang: str,
        target_lang: str,
    ) -> Dict[str, str]:
        system_prompt = (
            f"You translate Minecraft localization from {source_lang} to {target_lang}. "
            "Keep keys unchanged. Preserve placeholders like %s, %1$s, {0}, {player}, \\n, and Minecraft formatting codes like §a exactly. "
            "Do not wrap the result in markdown. Return only a JSON object."
        )
        if self.custom_prompt:
            system_prompt = system_prompt + " " + self.custom_prompt

        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.1,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(payload, ensure_ascii=False, indent=2),
                },
            ],
        )
        message = response.choices[0].message.content or ""
        return self._extract_json_object(message)

    @staticmethod
    def _extract_json_object(text: str) -> Dict[str, str]:
        stripped = text.strip()
        if stripped.startswith("```"):
            stripped = re.sub(r"^```[a-zA-Z0-9_+-]*", "", stripped)
            stripped = stripped.rstrip("`").strip()
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("Model did not return a JSON object.")
        payload = stripped[start : end + 1]
        data = json.loads(payload)
        if not isinstance(data, dict):
            raise ValueError("Model output is not a JSON object.")
        return {str(key): str(value) for key, value in data.items()}

    def _chunk_entries(self, items: Iterable[Tuple[str, str]]) -> List[List[Tuple[str, str]]]:
        chunk: List[Tuple[str, str]] = []
        chunks: List[List[Tuple[str, str]]] = []
        for item in items:
            chunk.append(item)
            if len(chunk) >= self.batch_size:
                chunks.append(chunk)
                chunk = []
        if chunk:
            chunks.append(chunk)
        return chunks
