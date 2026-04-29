from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Callable, Dict, List
import zipfile

from .lang_formats import dump_lang_payload
from .llm_client import OpenAICompatibleTranslator
from .scanner import LanguageAsset, scan_for_language_assets


ProgressCallback = Callable[[str], None]


@dataclass
class TranslationOptions:
    modpack_path: Path
    output_root: Path
    source_lang: str
    target_lang: str
    pack_name: str
    pack_format: int
    base_url: str
    api_key: str
    model: str
    only_missing: bool
    batch_size: int
    custom_prompt: str = ""


@dataclass
class TranslationResult:
    pack_folder: Path
    zip_file: Path
    asset_count: int
    translated_keys: int
    skipped_assets: List[str]
    mod_summaries: List["ModTranslationSummary"]


@dataclass
class ModTranslationSummary:
    mod_name: str
    asset_count: int = 0
    source_keys: int = 0
    existing_target_keys: int = 0
    queued_keys: int = 0
    translated_keys: int = 0


def run_translation(options: TranslationOptions, progress: ProgressCallback | None = None) -> TranslationResult:
    emit = progress or (lambda _message: None)

    if not options.modpack_path.exists():
        raise FileNotFoundError(f"Path not found: {options.modpack_path}")
    if not options.model.strip():
        raise ValueError("Model is required.")

    emit("Scanning mods and resource packs...")
    scan_result = scan_for_language_assets(
        options.modpack_path,
        source_lang=options.source_lang,
        target_lang=options.target_lang,
    )
    if not scan_result.assets:
        raise RuntimeError("No matching language files were found. Check source language or folder path.")
    emit(
        f"Discovered {len(scan_result.assets)} language assets. Unreadable entries during scan: {len(scan_result.skipped)}"
    )

    translator = OpenAICompatibleTranslator(
        base_url=options.base_url,
        api_key=options.api_key,
        model=options.model,
        batch_size=options.batch_size,
        custom_prompt=options.custom_prompt,
        progress=emit,
    )

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_name = slugify(options.pack_name)
    pack_folder = options.output_root / f"{safe_name}-{timestamp}"
    pack_folder.mkdir(parents=True, exist_ok=True)

    translated_keys = 0
    written_assets: Dict[str, LanguageAsset] = {}
    mod_summaries: Dict[str, ModTranslationSummary] = {}

    for index, asset in enumerate(scan_result.assets, start=1):
        pending = build_pending_entries(asset, only_missing=options.only_missing)
        mod_name = asset.origin_path.name
        summary = mod_summaries.setdefault(mod_name, ModTranslationSummary(mod_name=mod_name))
        summary.asset_count += 1
        summary.source_keys += len(asset.source_entries)
        summary.existing_target_keys += len(asset.target_entries)
        summary.queued_keys += len(pending)
        emit(
            f"[{index}/{len(scan_result.assets)}] {asset.identifier} | source={len(asset.source_entries)} | existing_target={len(asset.target_entries)} | queued={len(pending)}"
        )
        merged = dict(asset.target_entries)
        if pending:
            translated = translator.translate_entries(
                pending,
                source_lang=options.source_lang,
                target_lang=options.target_lang,
            )
            merged.update(translated)
            translated_count = len(translated)
            translated_keys += translated_count
            summary.translated_keys += translated_count
            emit(f"[{index}/{len(scan_result.assets)}] Wrote {translated_count} translated entries for {asset.identifier}")
        elif not merged:
            merged.update(asset.source_entries)
            emit(f"[{index}/{len(scan_result.assets)}] Source file is empty, copied original entries for {asset.identifier}")
        else:
            emit(f"[{index}/{len(scan_result.assets)}] Existing target language already complete for {asset.identifier}")

        emit(
            f"[{index}/{len(scan_result.assets)}] Mod total | {summary.mod_name} | translated={summary.translated_keys} | queued={summary.queued_keys} | assets={summary.asset_count}"
        )

        write_language_asset(pack_folder, asset, merged)
        written_assets[asset.identifier] = asset

    ordered_mod_summaries = list(mod_summaries.values())
    emit("Mod translation summary:")
    for summary in ordered_mod_summaries:
        emit(
            f"- {summary.mod_name} | translated={summary.translated_keys} | queued={summary.queued_keys} | source={summary.source_keys} | existing_target={summary.existing_target_keys} | assets={summary.asset_count}"
        )

    write_pack_metadata(pack_folder, options)
    report_path = pack_folder / "translation_report.json"
    report_path.write_text(
        json.dumps(
            {
                "pack_name": options.pack_name,
                "source_lang": options.source_lang,
                "target_lang": options.target_lang,
                "generated_at": timestamp,
                "assets": [asset.identifier for asset in written_assets.values()],
                "mod_summaries": [
                    {
                        "mod_name": summary.mod_name,
                        "asset_count": summary.asset_count,
                        "source_keys": summary.source_keys,
                        "existing_target_keys": summary.existing_target_keys,
                        "queued_keys": summary.queued_keys,
                        "translated_keys": summary.translated_keys,
                    }
                    for summary in ordered_mod_summaries
                ],
                "skipped": scan_result.skipped,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    zip_file = pack_folder.with_suffix(".zip")
    create_zip(pack_folder, zip_file)
    emit(f"Done. Resource pack folder: {pack_folder}")
    emit(f"Done. Resource pack zip: {zip_file}")

    return TranslationResult(
        pack_folder=pack_folder,
        zip_file=zip_file,
        asset_count=len(written_assets),
        translated_keys=translated_keys,
        skipped_assets=scan_result.skipped,
        mod_summaries=ordered_mod_summaries,
    )


def build_pending_entries(asset: LanguageAsset, *, only_missing: bool) -> Dict[str, str]:
    pending: Dict[str, str] = {}
    for key, value in asset.source_entries.items():
        existing = asset.target_entries.get(key, "")
        if only_missing and existing.strip():
            continue
        pending[key] = value
    return pending


def write_language_asset(pack_folder: Path, asset: LanguageAsset, payload: Dict[str, str]) -> None:
    output_path = pack_folder / Path(asset.target_internal_path.as_posix())
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        dump_lang_payload(payload, asset.extension),
        encoding="utf-8",
    )


def write_pack_metadata(pack_folder: Path, options: TranslationOptions) -> None:
    metadata = {
        "pack": {
            "pack_format": options.pack_format,
            "description": f"{options.pack_name} ({options.source_lang} -> {options.target_lang})",
        }
    }
    (pack_folder / "pack.mcmeta").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def create_zip(folder: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in folder.rglob("*"):
            if file_path.is_file():
                archive.write(file_path, file_path.relative_to(folder))


def infer_output_root(input_path: Path) -> Path:
    normalized_path = input_path.expanduser()
    if normalized_path.suffix.lower() in {".jar", ".zip"}:
        return normalized_path.parent
    if normalized_path.name.lower() in {"mods", "resourcepacks"}:
        return normalized_path.parent
    return normalized_path


def resolve_output_root(input_path: Path) -> Path:
    return infer_output_root(input_path)


def build_output_preview(input_path_text: str, pack_name: str) -> str:
    normalized_text = input_path_text.strip().strip('"')
    safe_name = slugify(pack_name.strip() or "AI Translation Pack")
    if not normalized_text:
        return "选择输入路径后，会自动在同级目录生成资源包文件夹和 ZIP。"
    root = infer_output_root(Path(normalized_text).expanduser())
    folder_preview = root / f"{safe_name}-<时间戳>"
    zip_preview = root / f"{safe_name}-<时间戳>.zip"
    return f"{folder_preview}\n{zip_preview}"


def slugify(value: str) -> str:
    cleaned = [character if character.isalnum() else "-" for character in value.strip().lower()]
    slug = "".join(cleaned).strip("-")
    return slug or "mc-ai-translation-pack"
