from __future__ import annotations

import json
import re
from typing import Callable, Dict, Iterable, List, Tuple

from openai import OpenAI

from .translation_optimization import (
    DEFAULT_REUSE_MODE,
    REUSE_MODE_AGGRESSIVE,
    REUSE_MODE_OFF,
    normalize_reuse_mode,
)
from .translation_skills import DEFAULT_SKILL_KEY, get_translation_skill


ProgressCallback = Callable[[str], None]


class OpenAICompatibleTranslator:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        batch_size: int = 40,
        skill_key: str = DEFAULT_SKILL_KEY,
        reuse_mode: str = DEFAULT_REUSE_MODE,
        custom_prompt: str = "",
        progress: ProgressCallback | None = None,
    ) -> None:
        self.client = OpenAI(
            api_key=api_key or "not-needed",
            base_url=base_url or None,
        )
        self.model = model
        self.batch_size = max(1, batch_size)
        self.skill = get_translation_skill(skill_key)
        self.reuse_mode = normalize_reuse_mode(reuse_mode)
        self.reuse_translations = self.reuse_mode != REUSE_MODE_OFF
        self.custom_prompt = custom_prompt.strip()
        self.progress = progress or (lambda _message: None)
        self.translation_cache: Dict[tuple[str, str, str, str, str, str], str] = {}
        self.cache_hits = 0
        self.api_entry_count = 0

    def translate_entries(
        self,
        entries: Dict[str, str],
        *,
        source_lang: str,
        target_lang: str,
    ) -> Dict[str, str]:
        if not entries:
            return {}

        if self.reuse_mode == REUSE_MODE_OFF:
            return self._translate_unique_entries(
                entries,
                source_lang=source_lang,
                target_lang=target_lang,
            )

        translated: Dict[str, str] = {}
        grouped_entries: Dict[tuple[str, str], List[str]] = {}
        reused_cached = 0

        for key, value in entries.items():
            cache_key = self._build_cache_key(
                source_lang=source_lang,
                target_lang=target_lang,
                entry_key=key,
                source_text=value,
            )
            cached_value = self.translation_cache.get(cache_key)
            if isinstance(cached_value, str) and cached_value.strip():
                translated[key] = cached_value
                reused_cached += 1
                continue
            group_key = self._build_group_key(entry_key=key, source_text=value)
            grouped_entries.setdefault(group_key, []).append(key)

        unique_payload: Dict[str, str] = {}
        representative_to_keys: Dict[str, List[str]] = {}
        deduplicated = 0
        for _group_key, keys in grouped_entries.items():
            representative_key = keys[0]
            source_text = entries[representative_key]
            representative_to_keys[representative_key] = keys
            unique_payload[representative_key] = source_text
            deduplicated += max(0, len(keys) - 1)

        if reused_cached or deduplicated:
            self.progress(
                f"Optimization ({self.reuse_mode}): reused {reused_cached} cached entries and skipped {deduplicated} duplicate source texts."
            )
            self.cache_hits += reused_cached + deduplicated

        if not unique_payload:
            return translated

        unique_translated = self._translate_unique_entries(
            unique_payload,
            source_lang=source_lang,
            target_lang=target_lang,
        )
        for representative_key, translated_value in unique_translated.items():
            source_text = unique_payload[representative_key]
            for key in representative_to_keys.get(representative_key, [representative_key]):
                self.translation_cache[
                    self._build_cache_key(
                        source_lang=source_lang,
                        target_lang=target_lang,
                        entry_key=key,
                        source_text=source_text,
                    )
                ] = translated_value
                translated[key] = translated_value

        return translated

    def _translate_unique_entries(
        self,
        entries: Dict[str, str],
        *,
        source_lang: str,
        target_lang: str,
    ) -> Dict[str, str]:
        if not entries:
            return {}

        translated: Dict[str, str] = {}
        batches = self._chunk_entries(entries.items())
        for index, batch in enumerate(batches, start=1):
            payload = dict(batch)
            batch_label = f"{index}/{len(batches)}"
            self.progress(f"Batch {batch_label}: sending {len(payload)} unique entries to {self.model}")
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
        prompt_parts = [
            f"Translate Minecraft mod localization {source_lang}->{target_lang}.",
            "Return a JSON object only with the same keys.",
            "Keep placeholders like %s, %1$s, {0}, {player}, \\n and formatting codes like §a exactly.",
            self.skill.system_prompt,
        ]
        if self.custom_prompt:
            prompt_parts.append(self.custom_prompt)
        system_prompt = " ".join(part for part in prompt_parts if part)

        self.api_entry_count += len(payload)

        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.1,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                },
            ],
        )
        message = response.choices[0].message.content or ""
        return self._extract_json_object(message)

    def _build_cache_key(
        self,
        *,
        source_lang: str,
        target_lang: str,
        entry_key: str,
        source_text: str,
    ) -> tuple[str, str, str, str, str, str]:
        return (
            source_lang,
            target_lang,
            self.skill.key,
            self.custom_prompt,
            self._build_context_signature(entry_key),
            source_text,
        )

    def _build_group_key(self, *, entry_key: str, source_text: str) -> tuple[str, str]:
        return (self._build_context_signature(entry_key), source_text)

    def _build_context_signature(self, entry_key: str) -> str:
        if self.reuse_mode == REUSE_MODE_AGGRESSIVE:
            return ""
        return entry_key.strip()

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
