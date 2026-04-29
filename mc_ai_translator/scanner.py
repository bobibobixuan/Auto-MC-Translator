from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Dict, Iterable, List, Tuple
import zipfile

from .lang_formats import parse_lang_payload


SUPPORTED_ARCHIVES = {".jar", ".zip"}
SUPPORTED_EXTENSIONS = {"json", "lang"}


@dataclass
class LanguageAsset:
    namespace: str
    source_lang: str
    target_lang: str
    extension: str
    source_entries: Dict[str, str]
    target_entries: Dict[str, str]
    source_internal_path: PurePosixPath
    target_internal_path: PurePosixPath
    origin_path: Path
    origin_kind: str

    @property
    def identifier(self) -> str:
        return f"{self.origin_path.name}:{self.namespace}:{self.extension}"


@dataclass
class ScanResult:
    assets: List[LanguageAsset]
    skipped: List[str]


def scan_for_language_assets(root_path: Path, source_lang: str, target_lang: str) -> ScanResult:
    skipped: List[str] = []
    assets: List[LanguageAsset] = []

    for candidate in discover_candidates(root_path):
        try:
            if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_ARCHIVES:
                assets.extend(scan_archive(candidate, source_lang, target_lang))
            elif candidate.is_dir():
                assets.extend(scan_directory(candidate, source_lang, target_lang))
        except Exception as exc:
            skipped.append(f"{candidate}: {exc}")

    return ScanResult(assets=assets, skipped=skipped)


def discover_candidates(root_path: Path) -> Iterable[Path]:
    if root_path.is_file():
        yield root_path
        return

    mods_dir = root_path / "mods"
    resourcepacks_dir = root_path / "resourcepacks"

    seen: set[Path] = set()

    def emit(path: Path) -> Iterable[Path]:
        if path.exists() and path not in seen:
            seen.add(path)
            yield path

    if root_path.name.lower() in {"mods", "resourcepacks"}:
        for child in sorted(root_path.iterdir()):
            yield from emit(child)
        return

    if mods_dir.is_dir():
        for child in sorted(mods_dir.iterdir()):
            yield from emit(child)

    if resourcepacks_dir.is_dir():
        for child in sorted(resourcepacks_dir.iterdir()):
            yield from emit(child)

    if (root_path / "assets").is_dir():
        yield from emit(root_path)

    if not seen:
        for child in sorted(root_path.iterdir()):
            if child.suffix.lower() in SUPPORTED_ARCHIVES or child.is_dir():
                yield from emit(child)


def scan_archive(archive_path: Path, source_lang: str, target_lang: str) -> List[LanguageAsset]:
    assets: List[LanguageAsset] = []
    with zipfile.ZipFile(archive_path) as archive:
        names = {PurePosixPath(name) for name in archive.namelist()}
        for source_path in names:
            parsed = parse_lang_path(source_path, source_lang)
            if not parsed:
                continue
            namespace, extension = parsed
            target_path = source_path.with_name(f"{target_lang}.{extension}")
            source_entries = parse_lang_payload(source_path.name, archive.read(source_path.as_posix()))
            target_entries: Dict[str, str] = {}
            if target_path in names:
                target_entries = parse_lang_payload(target_path.name, archive.read(target_path.as_posix()))
            assets.append(
                LanguageAsset(
                    namespace=namespace,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    extension=extension,
                    source_entries=source_entries,
                    target_entries=target_entries,
                    source_internal_path=source_path,
                    target_internal_path=target_path,
                    origin_path=archive_path,
                    origin_kind="archive",
                )
            )
    return assets


def scan_directory(directory_path: Path, source_lang: str, target_lang: str) -> List[LanguageAsset]:
    assets: List[LanguageAsset] = []
    for source_file in directory_path.rglob(f"{source_lang}.*"):
        relative_path = source_file.relative_to(directory_path)
        posix_relative = PurePosixPath(relative_path.as_posix())
        parsed = parse_lang_path(posix_relative, source_lang)
        if not parsed:
            continue
        namespace, extension = parsed
        source_entries = parse_lang_payload(source_file.name, source_file.read_bytes())
        target_file = source_file.with_name(f"{target_lang}.{extension}")
        target_entries: Dict[str, str] = {}
        if target_file.exists():
            target_entries = parse_lang_payload(target_file.name, target_file.read_bytes())
        assets.append(
            LanguageAsset(
                namespace=namespace,
                source_lang=source_lang,
                target_lang=target_lang,
                extension=extension,
                source_entries=source_entries,
                target_entries=target_entries,
                source_internal_path=posix_relative,
                target_internal_path=PurePosixPath(target_file.relative_to(directory_path).as_posix()),
                origin_path=directory_path,
                origin_kind="directory",
            )
        )
    return assets


def parse_lang_path(path: PurePosixPath, expected_lang: str) -> Tuple[str, str] | None:
    parts = path.parts
    if len(parts) < 4:
        return None
    if parts[0] != "assets" or parts[2] != "lang":
        return None
    file_name = parts[-1]
    if "." not in file_name:
        return None
    lang_code, extension = file_name.rsplit(".", 1)
    if lang_code.lower() != expected_lang.lower():
        return None
    if extension.lower() not in SUPPORTED_EXTENSIONS:
        return None
    return parts[1], extension.lower()
