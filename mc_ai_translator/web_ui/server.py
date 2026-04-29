from __future__ import annotations

import asyncio
import os
import re
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock, Thread
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from mc_ai_translator.language_presets import (
    DEFAULT_SOURCE_LANG,
    DEFAULT_TARGET_LANG,
    build_language_picker_note,
    language_choice_from_code,
    list_language_preset_labels,
    normalize_language_code,
)
from mc_ai_translator.pipeline import (
    TranslationOptions,
    build_output_preview,
    resolve_output_root,
    resolve_pack_name,
    run_translation,
)
from mc_ai_translator.providers import (
    build_model_choices,
    build_provider_note,
    get_provider,
    infer_provider_key,
    list_provider_labels,
    provider_label_from_key,
    provider_key_from_label,
    resolve_provider_settings,
)
from mc_ai_translator.translation_optimization import (
    DEFAULT_REUSE_MODE,
    build_optimization_preset_note,
    build_reuse_mode_note,
    build_skip_complete_note,
    get_optimization_preset_settings,
    list_optimization_preset_labels,
    list_reuse_mode_labels,
    list_skip_complete_labels,
    normalize_reuse_mode,
    normalize_skip_complete_targets,
    optimization_preset_key_from_label,
    optimization_preset_label_from_key,
    resolve_optimization_preset,
    reuse_mode_key_from_label,
    reuse_mode_label_from_key,
    skip_complete_enabled_from_label,
    skip_complete_label_from_enabled,
)
from mc_ai_translator.translation_skills import (
    DEFAULT_SKILL_KEY,
    build_translation_skill_note,
    list_translation_skill_labels,
    translation_skill_key_from_label,
    translation_skill_label_from_key,
)

load_dotenv()

SINGLE_MOD_MODE = "单个模组翻译"
FOLDER_MODE = "整个目录翻译"
FULL_TRANSLATION_MODE = "完整翻译整个语言包"
MISSING_ONLY_MODE = "只补全缺失项"
AUTO_DETECT_MODE = "自动识别"
DEFAULT_PACK_FORMAT = 15
DEFAULT_BATCH_SIZE = 60
JOB_RETENTION_MINUTES = 30

DISCOVERED_ASSETS_RE = re.compile(r"^Discovered (\d+) language assets\. Unreadable entries during scan: (\d+)$")
ASSET_PROGRESS_RE = re.compile(
    r"^\[(\d+)/(\d+)\] (.+) \| source=(\d+) \| existing_target=(\d+) \| complete_target=(yes|no) \| queued=(\d+)$"
)
ASSET_WRITTEN_RE = re.compile(r"^\[(\d+)/(\d+)\] Wrote (\d+) translated entries for (.+)$")
ASSET_SKIP_COMPLETE_RE = re.compile(r"^\[(\d+)/(\d+)\] Complete target detected, skipped translation for (.+)$")
COMPLETE_SKIPPED_RE = re.compile(r"^Complete target files skipped: (\d+)$")


def resolve_static_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        bundled_dir = Path(sys._MEIPASS) / "mc_ai_translator" / "web_ui" / "static"
        if bundled_dir.exists():
            return bundled_dir
    return Path(__file__).resolve().parent / "static"


STATIC_DIR = resolve_static_dir()

app = FastAPI(title="Minecraft AI Translator")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@dataclass
class TranslationJobState:
    job_id: str
    events: list[dict[str, Any]] = field(default_factory=list)
    finished: bool = False
    last_touched: datetime = field(default_factory=datetime.utcnow)
    _lock: Lock = field(default_factory=Lock, repr=False)

    def append(self, event_type: str, data: Any) -> None:
        with self._lock:
            self.events.append({"type": event_type, "data": data})
            self.finished = self.finished or event_type == "finished"
            self.last_touched = datetime.utcnow()

    def snapshot(self, start_index: int) -> list[dict[str, Any]]:
        with self._lock:
            self.last_touched = datetime.utcnow()
            return list(self.events[start_index:])


jobs: dict[str, TranslationJobState] = {}
jobs_lock = Lock()


def prune_jobs() -> None:
    cutoff = datetime.utcnow() - timedelta(minutes=JOB_RETENTION_MINUTES)
    with jobs_lock:
        stale_job_ids = [job_id for job_id, job in jobs.items() if job.finished and job.last_touched < cutoff]
        for job_id in stale_job_ids:
            jobs.pop(job_id, None)


def create_job() -> TranslationJobState:
    prune_jobs()
    job = TranslationJobState(job_id=uuid.uuid4().hex)
    with jobs_lock:
        jobs[job.job_id] = job
    return job


def get_job(job_id: str) -> TranslationJobState | None:
    with jobs_lock:
        return jobs.get(job_id)


def stamp(message: str) -> str:
    return f"[{datetime.now().strftime('%H:%M:%S')}] {message}"


def resolve_initial_directory(current_path: str) -> str:
    cleaned_path = current_path.strip().strip('"')
    if not cleaned_path:
        return str(Path.home())

    path = Path(cleaned_path).expanduser()
    if path.exists():
        return str(path if path.is_dir() else path.parent)
    if path.suffix:
        return str(path.parent)
    return str(path)


def open_native_dialog(current_path: str, *, select_directory: bool) -> str:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:
        return current_path

    root = None
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        initial_dir = resolve_initial_directory(current_path)
        if select_directory:
            selected = filedialog.askdirectory(
                title="选择要翻译的目录",
                initialdir=initial_dir,
            )
        else:
            selected = filedialog.askopenfilename(
                title="选择要翻译的模组文件",
                initialdir=initial_dir,
                filetypes=[("Minecraft 模组", "*.jar *.zip"), ("所有文件", "*.*")],
            )
        return selected or current_path
    except Exception:
        return current_path
    finally:
        if root is not None:
            root.destroy()


def validate_input_path(input_path: str) -> Path:
    cleaned_path = input_path.strip().strip('"')
    if not cleaned_path:
        raise ValueError("请先选择要翻译的模组文件或目录。")

    path = Path(cleaned_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Path not found: {path}")
    if path.is_file() and path.suffix.lower() in {".jar", ".zip"}:
        return path
    if path.is_dir():
        return path
    raise ValueError("请选择一个 .jar / .zip 模组文件，或选择一个目录。")


def describe_input_mode(path: Path) -> str:
    return SINGLE_MOD_MODE if path.is_file() else FOLDER_MODE


def summarize_asset_identifier(identifier: str) -> str:
    mod_name, _, remainder = identifier.partition(":")
    namespace, _, extension = remainder.partition(":")
    if namespace and extension:
        return f"{mod_name} / {namespace}.{extension}"
    return identifier


def build_beginner_log_entry(message: str) -> str | None:
    if message == "Scanning mods and resource packs...":
        return "正在扫描模组和资源包..."

    discovered_match = DISCOVERED_ASSETS_RE.match(message)
    if discovered_match:
        asset_count, skipped_count = discovered_match.groups()
        return f"扫描完成：发现 {asset_count} 个语言文件，读取失败 {skipped_count} 个。"

    progress_match = ASSET_PROGRESS_RE.match(message)
    if progress_match:
        index, total, identifier, _source_count, _existing_count, complete_target, queued = progress_match.groups()
        asset_label = summarize_asset_identifier(identifier)
        if complete_target == "yes" and queued == "0":
            return f"检测到 {index}/{total} {asset_label} 已有完整目标语言文件，准备跳过。"
        return f"正在处理 {index}/{total}：{asset_label}"

    written_match = ASSET_WRITTEN_RE.match(message)
    if written_match:
        index, total, translated_count, identifier = written_match.groups()
        asset_label = summarize_asset_identifier(identifier)
        return f"已完成 {index}/{total}：{asset_label}，新增翻译 {translated_count} 条。"

    skipped_match = ASSET_SKIP_COMPLETE_RE.match(message)
    if skipped_match:
        index, total, identifier = skipped_match.groups()
        asset_label = summarize_asset_identifier(identifier)
        return f"已跳过 {index}/{total}：{asset_label}，检测到完整目标语言文件。"

    if "retrying" in message.lower() or "omitted" in message.lower():
        return "模型返回不完整，正在自动重试缺失内容。"

    if message == "Mod translation summary:":
        return "正在整理翻译摘要..."

    complete_skipped_match = COMPLETE_SKIPPED_RE.match(message)
    if complete_skipped_match:
        skipped_count = complete_skipped_match.group(1)
        return f"本次共跳过 {skipped_count} 个已完整翻译的语言文件。"

    if message.startswith("Done. Resource pack folder:"):
        return "已生成资源包目录。"

    if message.startswith("Done. Resource pack zip:"):
        return "已生成资源包 ZIP。"

    return None


def serialize_mod_summary(summary: Any) -> dict[str, Any]:
    return {
        "mod_name": getattr(summary, "mod_name", "-"),
        "asset_count": getattr(summary, "asset_count", 0),
        "source_keys": getattr(summary, "source_keys", 0),
        "existing_target_keys": getattr(summary, "existing_target_keys", 0),
        "queued_keys": getattr(summary, "queued_keys", 0),
        "translated_keys": getattr(summary, "translated_keys", 0),
        "skipped_complete_assets": getattr(summary, "skipped_complete_assets", 0),
    }


def build_field_notes(
    *,
    source_lang: str,
    target_lang: str,
    skill: str,
    skip_complete_targets: str,
    reuse_mode: str,
    optimization_preset: str,
) -> dict[str, str]:
    return {
        "source_lang_note": build_language_picker_note(source_lang),
        "target_lang_note": build_language_picker_note(target_lang),
        "skill_note": build_translation_skill_note(translation_skill_key_from_label(skill)),
        "skip_complete_note": build_skip_complete_note(skip_complete_targets),
        "reuse_mode_note": build_reuse_mode_note(reuse_mode),
        "optimization_preset_note": build_optimization_preset_note(optimization_preset),
    }


class PickDialogRequest(BaseModel):
    current_path: str = ""
    select_directory: bool = False


class TranslationRequest(BaseModel):
    modpack_path: str
    pack_name: str = ""
    api_key: str = ""
    source_lang: str = DEFAULT_SOURCE_LANG
    target_lang: str = DEFAULT_TARGET_LANG
    pack_format: float = DEFAULT_PACK_FORMAT
    provider: str
    base_url: str = ""
    model: str = ""
    translation_mode: str = FULL_TRANSLATION_MODE
    skip_complete_targets: str = skip_complete_label_from_enabled(True)
    skill: str = translation_skill_label_from_key(DEFAULT_SKILL_KEY)
    reuse_mode: str = reuse_mode_label_from_key(DEFAULT_REUSE_MODE)
    batch_size: int = DEFAULT_BATCH_SIZE
    custom_prompt: str = ""


class OpenPathRequest(BaseModel):
    path: str


@app.post("/api/pick-path")
def pick_path(req: PickDialogRequest) -> dict[str, str]:
    return {"path": open_native_dialog(req.current_path, select_directory=req.select_directory)}


@app.get("/api/config/defaults")
def get_defaults() -> dict[str, Any]:
    default_provider_key = infer_provider_key(os.getenv("OPENAI_PROVIDER"), os.getenv("OPENAI_BASE_URL"))
    default_provider = get_provider(default_provider_key)
    default_model = os.getenv("OPENAI_MODEL", default_provider.default_model)
    default_skill_key = os.getenv("OPENAI_TRANSLATION_SKILL", DEFAULT_SKILL_KEY)
    default_reuse_mode = normalize_reuse_mode(os.getenv("OPENAI_TRANSLATION_REUSE_MODE", DEFAULT_REUSE_MODE))
    default_skip_complete = normalize_skip_complete_targets(os.getenv("OPENAI_SKIP_COMPLETE_TARGETS"))
    default_optimization_preset = resolve_optimization_preset(default_skip_complete, default_reuse_mode)

    return {
        "provider": provider_label_from_key(default_provider_key),
        "provider_note": build_provider_note(default_provider_key),
        "base_url": os.getenv("OPENAI_BASE_URL", default_provider.base_url) or "",
        "api_key": os.getenv("OPENAI_API_KEY", ""),
        "model": default_model,
        "source_lang": language_choice_from_code(DEFAULT_SOURCE_LANG),
        "target_lang": language_choice_from_code(DEFAULT_TARGET_LANG),
        "pack_format": DEFAULT_PACK_FORMAT,
        "batch_size": DEFAULT_BATCH_SIZE,
        "translation_mode": FULL_TRANSLATION_MODE,
        "optimization_preset": optimization_preset_label_from_key(default_optimization_preset),
        "skip_complete_targets": skip_complete_label_from_enabled(default_skip_complete),
        "reuse_mode": reuse_mode_label_from_key(default_reuse_mode),
        "skill": translation_skill_label_from_key(default_skill_key),
        "notes": build_field_notes(
            source_lang=DEFAULT_SOURCE_LANG,
            target_lang=DEFAULT_TARGET_LANG,
            skill=translation_skill_label_from_key(default_skill_key),
            skip_complete_targets=skip_complete_label_from_enabled(default_skip_complete),
            reuse_mode=reuse_mode_label_from_key(default_reuse_mode),
            optimization_preset=optimization_preset_label_from_key(default_optimization_preset),
        ),
    }


@app.get("/api/config/lookups")
def get_lookups() -> dict[str, list[str]]:
    return {
        "providers": list_provider_labels(),
        "languages": list_language_preset_labels(),
        "translation_modes": [FULL_TRANSLATION_MODE, MISSING_ONLY_MODE],
        "optimization_presets": list_optimization_preset_labels(),
        "skip_complete_targets": list_skip_complete_labels(),
        "reuse_modes": list_reuse_mode_labels(),
        "skills": list_translation_skill_labels(),
    }


@app.get("/api/config/provider-details")
def get_provider_details(provider_label: str) -> dict[str, Any]:
    provider_key = provider_key_from_label(provider_label)
    provider = get_provider(provider_key)
    return {
        "base_url": provider.base_url,
        "default_model": provider.default_model,
        "models": build_model_choices(provider_key),
        "note": build_provider_note(provider_key),
        "requires_api_key": provider.requires_api_key,
    }


@app.get("/api/config/field-notes")
def get_field_notes(
    source_lang: str,
    target_lang: str,
    skill: str,
    skip_complete_targets: str,
    reuse_mode: str,
    optimization_preset: str,
) -> dict[str, str]:
    return build_field_notes(
        source_lang=source_lang,
        target_lang=target_lang,
        skill=skill,
        skip_complete_targets=skip_complete_targets,
        reuse_mode=reuse_mode,
        optimization_preset=optimization_preset,
    )


@app.get("/api/config/optimization-preset-details")
def get_optimization_preset_details(preset_label: str, fallback_skip: str, fallback_reuse: str) -> dict[str, str]:
    skip_complete_targets, reuse_mode = get_optimization_preset_settings(
        optimization_preset_key_from_label(preset_label),
        fallback_skip_complete_targets=fallback_skip,
        fallback_reuse_mode=fallback_reuse,
    )
    return {
        "skip_complete_targets": skip_complete_label_from_enabled(skip_complete_targets),
        "reuse_mode": reuse_mode_label_from_key(reuse_mode),
        "note": build_optimization_preset_note(preset_label),
    }


@app.get("/api/preview-output")
def get_output_preview(input_path: str, pack_name: str, target_lang: str) -> dict[str, str]:
    normalized_target_lang = normalize_language_code(target_lang) or DEFAULT_TARGET_LANG
    preview = build_output_preview(input_path.strip().strip('"'), pack_name, normalized_target_lang)
    return {"preview": preview}


@app.get("/api/suggest-pack-name")
def suggest_pack_name(input_path: str, pack_name: str, target_lang: str) -> dict[str, str]:
    cleaned_path = input_path.strip().strip('"')
    normalized_target_lang = normalize_language_code(target_lang) or DEFAULT_TARGET_LANG
    input_candidate = Path(cleaned_path).expanduser() if cleaned_path else None
    resolved_pack_name = resolve_pack_name(pack_name, input_candidate, normalized_target_lang)
    return {
        "pack_name": resolved_pack_name,
        "preview": build_output_preview(cleaned_path, resolved_pack_name, normalized_target_lang),
    }


def emit_progress(job: TranslationJobState, message: str) -> None:
    beginner_message = build_beginner_log_entry(message)
    job.append(
        "log",
        {
            "developer": stamp(message),
            "beginner": stamp(beginner_message) if beginner_message else None,
            "detail": beginner_message or message,
            "raw": message,
        },
    )


def build_result_payload(result: Any, current_input: str) -> dict[str, Any]:
    mod_summaries = [serialize_mod_summary(item) for item in getattr(result, "mod_summaries", [])]
    translated_mod_count = sum(1 for item in mod_summaries if item["translated_keys"] > 0)
    detail = (
        f"翻译任务完成，共统计 {len(mod_summaries)} 个模组，实际写入 {translated_mod_count} 个模组，"
        f"跳过 {getattr(result, 'skipped_complete_assets', 0)} 个已完整翻译文件，"
        f"新增 {getattr(result, 'translated_keys', 0)} 条翻译；优化命中 {getattr(result, 'cache_hits', 0)} 条，"
        f"实际发送到模型 {getattr(result, 'api_entry_count', 0)} 条。"
    )
    return {
        "detail": detail,
        "project_path": str(getattr(result, "project_path", current_input)),
        "pack_folder": str(getattr(result, "pack_folder", "")),
        "zip_file": str(getattr(result, "zip_file", "")),
        "report_file": str(getattr(result, "report_file", "")),
        "asset_count": getattr(result, "asset_count", 0),
        "translated_keys": getattr(result, "translated_keys", 0),
        "skipped_complete_assets": getattr(result, "skipped_complete_assets", 0),
        "cache_hits": getattr(result, "cache_hits", 0),
        "api_entry_count": getattr(result, "api_entry_count", 0),
        "skipped_assets": list(getattr(result, "skipped_assets", [])),
        "skipped_count": len(getattr(result, "skipped_assets", [])),
        "mod_count": len(mod_summaries),
        "translated_mod_count": translated_mod_count,
        "mod_summaries": mod_summaries,
    }


def translation_worker(job: TranslationJobState, req: TranslationRequest) -> None:
    current_input = req.modpack_path.strip().strip('"')
    try:
        normalized_source_lang = normalize_language_code(req.source_lang) or DEFAULT_SOURCE_LANG
        normalized_target_lang = normalize_language_code(req.target_lang) or DEFAULT_TARGET_LANG
        selected_path = validate_input_path(req.modpack_path)
        workflow_label = describe_input_mode(selected_path)
        resolved_pack_name = resolve_pack_name(req.pack_name, selected_path, normalized_target_lang)
        output_preview = build_output_preview(str(selected_path), resolved_pack_name, normalized_target_lang)

        resolved_provider, resolved_base_url, resolved_model = resolve_provider_settings(
            req.provider,
            req.base_url,
            req.model,
        )
        api_key_stripped = req.api_key.strip()
        selected_skip_complete = skip_complete_enabled_from_label(req.skip_complete_targets)
        selected_reuse_mode = reuse_mode_key_from_label(req.reuse_mode)
        output_root = resolve_output_root(selected_path)
        if resolved_provider.requires_api_key and not api_key_stripped:
            raise ValueError(f"【配置错误】服务商预设「{resolved_provider.label}」需要填写 API Key。")

        job.append(
            "meta",
            {
                "workflow_label": workflow_label,
                "input_path": str(selected_path),
                "output_preview": output_preview,
                "detail": "输入校验完成，开始扫描语言文件。",
                "beginner_log": stamp("任务已启动，正在校验输入并准备扫描语言文件。"),
                "developer_logs": [
                    stamp(f"Input mode: {workflow_label}"),
                    stamp(f"Pack name: {resolved_pack_name}"),
                    stamp(f"Provider preset: {resolved_provider.label}"),
                    stamp(f"Model: {resolved_model}"),
                    stamp(f"Complete target skip: {req.skip_complete_targets}"),
                    stamp(f"Translation skill: {req.skill}"),
                    stamp(f"Duplicate text reuse: {req.reuse_mode}"),
                    stamp(f"Base URL: {resolved_base_url}"),
                    stamp(f"Output root: {output_root}"),
                ],
            },
        )

        options = TranslationOptions(
            modpack_path=selected_path,
            output_root=output_root,
            source_lang=normalized_source_lang,
            target_lang=normalized_target_lang,
            pack_name=resolved_pack_name,
            pack_format=int(req.pack_format),
            base_url=resolved_base_url,
            api_key=api_key_stripped,
            model=resolved_model,
            only_missing=req.translation_mode == MISSING_ONLY_MODE,
            batch_size=int(req.batch_size),
            skill_key=translation_skill_key_from_label(req.skill),
            reuse_mode=selected_reuse_mode,
            skip_complete_targets=selected_skip_complete,
            custom_prompt=req.custom_prompt.strip(),
        )
        result = run_translation(options, progress=lambda message: emit_progress(job, message))
        job.append("result", build_result_payload(result, current_input))
    except Exception as exc:
        message = str(exc)
        job.append(
            "error",
            {
                "message": message,
                "developer": stamp(f"ERROR: {message}"),
                "beginner": stamp(f"任务失败：{message}"),
            },
        )
    finally:
        job.append("finished", {})


@app.post("/api/translate")
def start_translation(req: TranslationRequest) -> dict[str, str]:
    job = create_job()
    Thread(target=translation_worker, args=(job, req), daemon=True).start()
    return {"status": "started", "job_id": job.job_id}


@app.websocket("/api/jobs/{job_id}/stream")
async def stream_job_events(websocket: WebSocket, job_id: str) -> None:
    job = get_job(job_id)
    if job is None:
        await websocket.close(code=4404)
        return

    await websocket.accept()
    next_index = 0
    try:
        while True:
            events = job.snapshot(next_index)
            if events:
                for event in events:
                    await websocket.send_json(event)
                next_index += len(events)
                continue

            if job.finished:
                break
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        return
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


@app.post("/api/open-path")
def open_path(req: OpenPathRequest) -> dict[str, str]:
    path = Path(req.path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Path does not exist")

    try:
        if os.name == "nt":
            os.startfile(str(path))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"status": "opened"}


@app.get("/")
def read_root() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

