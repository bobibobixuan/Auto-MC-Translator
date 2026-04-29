from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Callable, Dict, List
import zipfile

from .lang_formats import dump_lang_payload
from .llm_client import OpenAICompatibleTranslator
from .scanner import LanguageAsset, scan_for_language_assets
from .translation_optimization import DEFAULT_REUSE_MODE, DEFAULT_SKIP_COMPLETE_TARGETS, REUSE_MODE_OFF
from .translation_skills import DEFAULT_SKILL_KEY


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
    skill_key: str = DEFAULT_SKILL_KEY
    reuse_mode: str = DEFAULT_REUSE_MODE
    skip_complete_targets: bool = DEFAULT_SKIP_COMPLETE_TARGETS
    custom_prompt: str = ""


@dataclass
class TranslationResult:
    project_path: Path
    pack_folder: Path
    zip_file: Path
    report_file: Path
    skill_key: str
    reuse_mode: str
    reuse_translations: bool
    skip_complete_targets: bool
    asset_count: int
    translated_keys: int
    skipped_complete_assets: int
    cache_hits: int
    api_entry_count: int
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
    skipped_complete_assets: int = 0


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
        skill_key=options.skill_key,
        reuse_mode=options.reuse_mode,
        custom_prompt=options.custom_prompt,
        progress=emit,
    )

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_name = slugify(options.pack_name)
    pack_folder = options.output_root / f"{safe_name}-{timestamp}"
    pack_folder.mkdir(parents=True, exist_ok=True)

    translated_keys = 0
    skipped_complete_assets = 0
    written_assets: Dict[str, LanguageAsset] = {}
    mod_summaries: Dict[str, ModTranslationSummary] = {}

    for index, asset in enumerate(scan_result.assets, start=1):
        target_complete = has_complete_target_entries(asset)
        pending = build_pending_entries(
            asset,
            only_missing=options.only_missing,
            skip_complete_targets=options.skip_complete_targets,
        )
        mod_name = asset.origin_path.name
        summary = mod_summaries.setdefault(mod_name, ModTranslationSummary(mod_name=mod_name))
        summary.asset_count += 1
        summary.source_keys += len(asset.source_entries)
        summary.existing_target_keys += len(asset.target_entries)
        if target_complete and options.skip_complete_targets:
            summary.skipped_complete_assets += 1
        summary.queued_keys += len(pending)
        emit(
            f"[{index}/{len(scan_result.assets)}] {asset.identifier} | source={len(asset.source_entries)} | existing_target={len(asset.target_entries)} | complete_target={'yes' if target_complete else 'no'} | queued={len(pending)}"
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
        elif target_complete and options.skip_complete_targets:
            skipped_complete_assets += 1
            emit(f"[{index}/{len(scan_result.assets)}] Complete target detected, skipped translation for {asset.identifier}")
        else:
            emit(f"[{index}/{len(scan_result.assets)}] Existing target language already complete for {asset.identifier}")

        emit(
            f"[{index}/{len(scan_result.assets)}] Mod total | {summary.mod_name} | translated={summary.translated_keys} | queued={summary.queued_keys} | skipped_complete={summary.skipped_complete_assets} | assets={summary.asset_count}"
        )

        write_language_asset(pack_folder, asset, merged)
        written_assets[asset.identifier] = asset

    ordered_mod_summaries = list(mod_summaries.values())
    emit("Mod translation summary:")
    for summary in ordered_mod_summaries:
        emit(
            f"- {summary.mod_name} | translated={summary.translated_keys} | queued={summary.queued_keys} | skipped_complete={summary.skipped_complete_assets} | source={summary.source_keys} | existing_target={summary.existing_target_keys} | assets={summary.asset_count}"
        )
    emit(f"Complete target files skipped: {skipped_complete_assets}")

    write_pack_metadata(pack_folder, options)
    report_path = pack_folder / "translation_report.json"
    report_payload = {
        "project_name": options.modpack_path.name,
        "project_path": str(options.modpack_path),
        "pack_name": options.pack_name,
        "source_lang": options.source_lang,
        "target_lang": options.target_lang,
        "skill_key": options.skill_key,
        "reuse_mode": options.reuse_mode,
        "reuse_translations": options.reuse_mode != REUSE_MODE_OFF,
        "skip_complete_targets": options.skip_complete_targets,
        "generated_at": timestamp,
        "pack_folder": str(pack_folder),
        "zip_file": str(pack_folder.with_suffix(".zip")),
        "report_file": str(report_path),
        "asset_count": len(written_assets),
        "translated_keys": translated_keys,
        "skipped_complete_assets": skipped_complete_assets,
        "cache_hits": translator.cache_hits,
        "api_entry_count": translator.api_entry_count,
        "mod_count": len(ordered_mod_summaries),
        "translated_mod_count": sum(1 for summary in ordered_mod_summaries if summary.translated_keys > 0),
        "assets": [asset.identifier for asset in written_assets.values()],
        "mod_summaries": [
            {
                "mod_name": summary.mod_name,
                "asset_count": summary.asset_count,
                "source_keys": summary.source_keys,
                "existing_target_keys": summary.existing_target_keys,
                "queued_keys": summary.queued_keys,
                "translated_keys": summary.translated_keys,
                "skipped_complete_assets": summary.skipped_complete_assets,
            }
            for summary in ordered_mod_summaries
        ],
        "skipped": scan_result.skipped,
    }
    report_path.write_text(
        json.dumps(report_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    zip_file = pack_folder.with_suffix(".zip")
    create_zip(pack_folder, zip_file)
    emit(f"Done. Resource pack folder: {pack_folder}")
    emit(f"Done. Resource pack zip: {zip_file}")

    return TranslationResult(
        project_path=options.modpack_path,
        pack_folder=pack_folder,
        zip_file=zip_file,
        report_file=report_path,
        skill_key=options.skill_key,
        reuse_mode=options.reuse_mode,
        reuse_translations=options.reuse_mode != REUSE_MODE_OFF,
        skip_complete_targets=options.skip_complete_targets,
        asset_count=len(written_assets),
        translated_keys=translated_keys,
        skipped_complete_assets=skipped_complete_assets,
        cache_hits=translator.cache_hits,
        api_entry_count=translator.api_entry_count,
        skipped_assets=scan_result.skipped,
        mod_summaries=ordered_mod_summaries,
    )


def build_pending_entries(
    asset: LanguageAsset,
    *,
    only_missing: bool,
    skip_complete_targets: bool = DEFAULT_SKIP_COMPLETE_TARGETS,
) -> Dict[str, str]:
    if skip_complete_targets and has_complete_target_entries(asset):
        return {}

    pending: Dict[str, str] = {}
    for key, value in asset.source_entries.items():
        existing = asset.target_entries.get(key, "")
        if only_missing and existing.strip():
            continue
        pending[key] = value
    return pending


def has_complete_target_entries(asset: LanguageAsset) -> bool:
    if not asset.source_entries or not asset.target_entries:
        return False

    for key in asset.source_entries:
        existing = asset.target_entries.get(key, "")
        if not isinstance(existing, str) or not existing.strip():
            return False
    return True


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


def get_application_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def infer_output_root(_input_path: Path | None = None) -> Path:
    return get_application_root() / "output"


def resolve_output_root(input_path: Path | None = None) -> Path:
    return infer_output_root(input_path)


def derive_default_pack_name(input_path: Path, target_lang: str = "zh_cn") -> str:
    candidate = input_path.stem if input_path.suffix else input_path.name
    normalized_candidate = candidate.strip() or "AI Translation Pack"
    normalized_target = target_lang.strip().lower()
    if normalized_target:
        return f"{normalized_candidate}-{normalized_target}"
    return normalized_candidate


def resolve_pack_name(pack_name_text: str, input_path: Path | None = None, target_lang: str = "zh_cn") -> str:
    manual_name = pack_name_text.strip()
    if manual_name:
        return manual_name
    if input_path is not None:
        return derive_default_pack_name(input_path, target_lang)
    normalized_target = target_lang.strip().lower()
    if normalized_target:
        return f"AI Translation Pack-{normalized_target}"
    return "AI Translation Pack"


def build_output_preview(input_path_text: str, pack_name: str, target_lang: str = "zh_cn") -> str:
    normalized_text = input_path_text.strip().strip('"')
    input_path = Path(normalized_text).expanduser() if normalized_text else None
    resolved_name = resolve_pack_name(pack_name, input_path, target_lang)
    safe_name = slugify(resolved_name)
    root = infer_output_root(input_path)
    folder_preview = root / f"{safe_name}-<时间戳>"
    zip_preview = root / f"{safe_name}-<时间戳>.zip"
    return f"{folder_preview}\n{zip_preview}"


def slugify(value: str) -> str:
    cleaned = [character if character.isalnum() else "-" for character in value.strip().lower()]
    slug = "".join(cleaned).strip("-")
    return slug or "mc-ai-translation-pack"
