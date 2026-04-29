from __future__ import annotations

import html
import os
from datetime import datetime
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
from typing import Iterator, List

import gradio as gr
from dotenv import load_dotenv

from .pipeline import TranslationOptions, build_output_preview, resolve_output_root, run_translation
from .providers import (
    build_model_choices,
    build_provider_note,
    get_provider,
    infer_provider_key,
    list_provider_labels,
    provider_label_from_key,
    provider_key_from_label,
    resolve_provider_settings,
)


load_dotenv()


APP_CSS = """
:root {
    --warm-bg: #f8efe5;
    --panel: rgba(255, 251, 246, 0.92);
    --panel-border: #e6cbb1;
    --accent: #c76b12;
    --accent-dark: #7a3b0c;
    --forest: #1f4d43;
    --text: #2e2017;
    --muted: #735a47;
}

body, .gradio-container {
    background:
        radial-gradient(circle at top left, #ffe5c1 0, rgba(255, 229, 193, 0.25) 30%, transparent 55%),
        radial-gradient(circle at bottom right, #cfe3db 0, rgba(207, 227, 219, 0.32) 28%, transparent 52%),
        linear-gradient(180deg, #f6ede4 0%, #f4e7da 100%);
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    color: var(--text);
}

.gradio-container {
    max-width: 1260px !important;
    padding: 28px 20px 40px !important;
}

.hero-card {
    background: linear-gradient(135deg, rgba(255, 245, 231, 0.95), rgba(247, 233, 216, 0.95));
    border: 1px solid var(--panel-border);
    border-radius: 28px;
    padding: 28px 32px;
    margin-bottom: 18px;
    box-shadow: 0 22px 60px rgba(111, 73, 44, 0.12);
}

.hero-card h1 {
    margin: 6px 0 12px;
    font-size: 2.2rem;
    line-height: 1.1;
}

.hero-kicker {
    display: inline-block;
    padding: 6px 12px;
    border-radius: 999px;
    background: rgba(31, 77, 67, 0.12);
    color: var(--forest);
    font-size: 0.92rem;
    font-weight: 700;
    letter-spacing: 0.04em;
}

.hero-tags {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-top: 18px;
}

.hero-tags span {
    padding: 8px 14px;
    border-radius: 999px;
    background: rgba(199, 107, 18, 0.12);
    color: var(--accent-dark);
    font-size: 0.92rem;
    font-weight: 600;
}

.section-card {
    background: var(--panel);
    border: 1px solid var(--panel-border);
    border-radius: 24px;
    padding: 18px;
    box-shadow: 0 12px 32px rgba(73, 44, 27, 0.08);
}

.section-title {
    margin: 0 0 6px;
    font-size: 1.08rem;
    font-weight: 700;
    color: var(--text);
}

.section-subtitle {
    margin: 0 0 12px;
    color: var(--muted);
    font-size: 0.94rem;
}

.status-panel {
    background: linear-gradient(160deg, #173f35, #24554a);
    color: #f5fff8;
    border-radius: 22px;
    padding: 18px 20px;
    min-height: 210px;
}

.status-panel .status-label {
    font-size: 0.82rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    opacity: 0.82;
}

.status-panel h3 {
    margin: 10px 0 8px;
    font-size: 1.5rem;
}

.status-panel p {
    margin: 0 0 14px;
    line-height: 1.6;
}

.status-meta {
    padding: 12px 14px;
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.08);
    margin-top: 10px;
}

.status-meta strong {
    display: block;
    margin-bottom: 6px;
}

.status-meta code {
    display: block;
    white-space: pre-wrap;
    font-family: "Cascadia Mono", Consolas, monospace;
    font-size: 0.88rem;
}

.log-box textarea {
    background: #1b1d22 !important;
    color: #ecf3ff !important;
    border-radius: 18px !important;
    font-family: "Cascadia Mono", Consolas, monospace !important;
}

.hint-box {
    padding: 14px 16px;
    border-radius: 18px;
    background: rgba(199, 107, 18, 0.08);
    border: 1px dashed rgba(199, 107, 18, 0.28);
    color: var(--accent-dark);
}

.gr-button-primary {
    background: linear-gradient(135deg, #cd6b15, #a75410) !important;
    border: none !important;
}

.gr-button-secondary {
    border-color: rgba(122, 59, 12, 0.18) !important;
}
"""

SINGLE_MOD_MODE = "单个模组翻译"
FOLDER_MODE = "整个目录翻译"
FULL_TRANSLATION_MODE = "完整翻译整个语言包"
MISSING_ONLY_MODE = "只补全缺失项"


def build_app() -> gr.Blocks:
    default_provider_key = infer_provider_key(
        os.getenv("OPENAI_PROVIDER"),
        os.getenv("OPENAI_BASE_URL"),
    )
    default_provider = get_provider(default_provider_key)
    default_base_url = os.getenv("OPENAI_BASE_URL", default_provider.base_url)
    default_api_key = os.getenv("OPENAI_API_KEY", "")
    default_model = os.getenv("OPENAI_MODEL", default_provider.default_model)
    default_provider_label = provider_label_from_key(default_provider_key)
    default_provider_note = build_provider_note(default_provider_key)
    default_model_choices = build_model_choices(default_provider_key, default_model)
    default_pack_name = "AI Translation Pack"
    default_output_preview = build_output_preview("", default_pack_name)

    with gr.Blocks(title="Minecraft AI Translator") as app:
        gr.Markdown(
            """
<div class="hero-card">
  <div class="hero-kicker">本地 AI 汉化工作台</div>
  <h1>Minecraft AI Translator</h1>
  <p>支持单个模组和整个目录两种工作流，实时显示调用日志，并把资源包自动生成到输入路径的同级位置。</p>
  <div class="hero-tags">
    <span>实时调用日志</span>
    <span>单模组 / 整目录</span>
    <span>完整翻译优先</span>
    <span>同级目录输出</span>
  </div>
</div>
            """.strip()
        )

        with gr.Row():
            with gr.Column(scale=7, elem_classes="section-card"):
                gr.Markdown("<div class='section-title'>输入与输出</div><div class='section-subtitle'>先选翻译方式，再选择单个模组文件或整个目录。</div>")
                input_mode = gr.Radio(
                    label="翻译方式",
                    choices=[SINGLE_MOD_MODE, FOLDER_MODE],
                    value=SINGLE_MOD_MODE,
                )
                workflow_note = gr.Markdown(build_input_mode_note(SINGLE_MOD_MODE), elem_classes="hint-box")
                with gr.Row():
                    modpack_path = gr.Textbox(
                        label="模组 JAR / ZIP 文件",
                        placeholder=r"C:\Minecraft\mods\FarmersDelight.jar",
                    )
                    with gr.Column(scale=0, min_width=170):
                        choose_file_button = gr.Button("选择模组文件", variant="secondary")
                        choose_dir_button = gr.Button("选择目录", variant="secondary")
                output_preview = gr.Textbox(
                    label="输出位置预览（自动在同级目录生成）",
                    value=default_output_preview,
                    lines=2,
                    interactive=False,
                )
            with gr.Column(scale=5, elem_classes="section-card"):
                status_markdown = gr.Markdown(
                    render_status_panel(
                        title="等待开始",
                        detail="选择输入路径、服务商和翻译策略后即可启动任务。",
                        input_mode=SINGLE_MOD_MODE,
                        input_path="",
                        output_preview=default_output_preview,
                    )
                )

        with gr.Row():
            with gr.Column(scale=6, elem_classes="section-card"):
                gr.Markdown("<div class='section-title'>翻译设置</div><div class='section-subtitle'>默认改成完整翻译；如果只想补已有汉化的缺口，再切换成补全模式。</div>")
                with gr.Row():
                    source_lang = gr.Textbox(label="源语言", value="en_us")
                    target_lang = gr.Textbox(label="目标语言", value="zh_cn")
                    pack_format = gr.Number(label="pack_format", value=15, precision=0)
                pack_name = gr.Textbox(label="输出资源包名称", value=default_pack_name)
                translation_mode = gr.Radio(
                    label="翻译策略",
                    choices=[FULL_TRANSLATION_MODE, MISSING_ONLY_MODE],
                    value=FULL_TRANSLATION_MODE,
                )
                batch_size = gr.Slider(label="每批翻译条目数", minimum=5, maximum=100, value=40, step=1)

            with gr.Column(scale=6, elem_classes="section-card"):
                gr.Markdown("<div class='section-title'>模型与接口</div><div class='section-subtitle'>服务商预设会自动补齐 Base URL 和推荐模型，调用日志里会实时显示请求批次。</div>")
                with gr.Row():
                    provider = gr.Dropdown(
                        label="服务商预设",
                        choices=list_provider_labels(),
                        value=default_provider_label,
                    )
                    model = gr.Dropdown(
                        label="模型名",
                        choices=default_model_choices,
                        value=default_model,
                        allow_custom_value=True,
                    )

                provider_note = gr.Markdown(default_provider_note)
                api_key = gr.Textbox(label="API Key", type="password", value=default_api_key)
                with gr.Accordion("高级设置", open=False):
                    base_url = gr.Textbox(label="OpenAI 兼容接口 Base URL", value=default_base_url)
                custom_prompt = gr.Textbox(
                    label="额外提示词（可选）",
                    lines=4,
                    placeholder="例如：菜品名优先保留模组习惯译法，提示文本可以更自然。",
                )

        run_button = gr.Button("开始一键翻译", variant="primary")
        result_text = gr.Textbox(label="实时调用日志", lines=22, elem_classes="log-box")

        run_button.click(
            fn=run_from_ui,
            inputs=[
                input_mode,
                modpack_path,
                source_lang,
                target_lang,
                pack_name,
                pack_format,
                provider,
                base_url,
                api_key,
                model,
                translation_mode,
                batch_size,
                custom_prompt,
            ],
            outputs=[status_markdown, result_text],
            concurrency_limit=1,
        )

        provider.change(
            fn=update_provider_ui,
            inputs=[provider],
            outputs=[model, base_url, provider_note],
        )

        input_mode.change(
            fn=update_input_mode_ui,
            inputs=[input_mode, modpack_path],
            outputs=[modpack_path, workflow_note],
        )
        modpack_path.change(
            fn=update_output_preview,
            inputs=[modpack_path, pack_name],
            outputs=[output_preview],
        )
        pack_name.change(
            fn=update_output_preview,
            inputs=[modpack_path, pack_name],
            outputs=[output_preview],
        )
        choose_file_button.click(
            fn=pick_mod_file,
            inputs=[modpack_path, pack_name],
            outputs=[modpack_path, output_preview],
        )
        choose_dir_button.click(
            fn=pick_directory,
            inputs=[modpack_path, pack_name],
            outputs=[modpack_path, output_preview],
        )

        app.queue(default_concurrency_limit=2)

    return app


def build_launch_kwargs() -> dict[str, object]:
    return {
        "theme": gr.themes.Soft(
            primary_hue="amber",
            secondary_hue="emerald",
            neutral_hue="stone",
            radius_size=gr.themes.sizes.radius_lg,
        ),
        "css": APP_CSS,
    }


def run_from_ui(
    input_mode: str,
    modpack_path: str,
    source_lang: str,
    target_lang: str,
    pack_name: str,
    pack_format: float,
    provider: str,
    base_url: str,
    api_key: str,
    model: str,
    translation_mode: str,
    batch_size: int,
    custom_prompt: str,
) -> Iterator[tuple[str, str]]:
    logs: List[str] = []
    event_queue: Queue[tuple[str, object]] = Queue()

    current_input = modpack_path.strip().strip('"')
    current_output_preview = build_output_preview(current_input, pack_name)
    current_detail = "正在校验输入配置。"

    def stamp(message: str) -> str:
        return f"[{datetime.now().strftime('%H:%M:%S')}] {message}"

    def render(title: str) -> tuple[str, str]:
        return (
            render_status_panel(
                title=title,
                detail=current_detail,
                input_mode=input_mode,
                input_path=current_input,
                output_preview=current_output_preview,
            ),
            "\n".join(logs),
        )

    def emit(message: str) -> None:
        event_queue.put(("log", message))

    def worker() -> None:
        try:
            resolved_provider, resolved_base_url, resolved_model = resolve_provider_settings(
                provider,
                base_url,
                model,
            )
            api_key_stripped = api_key.strip()
            selected_path = validate_input_path(input_mode, modpack_path)
            output_root = resolve_output_root(selected_path)
            if resolved_provider.requires_api_key and not api_key_stripped:
                raise ValueError(f"【配置错误】服务商预设「{resolved_provider.label}」需要填写 API Key。")

            event_queue.put(
                (
                    "meta",
                    {
                        "input_path": str(selected_path),
                        "output_preview": build_output_preview(str(selected_path), pack_name),
                        "messages": [
                            f"Input mode: {input_mode}",
                            f"Provider preset: {resolved_provider.label}",
                            f"Model: {resolved_model}",
                            f"Base URL: {resolved_base_url}",
                            f"Output root: {output_root}",
                        ],
                    },
                )
            )

            options = TranslationOptions(
                modpack_path=selected_path,
                output_root=output_root,
                source_lang=source_lang.strip().lower(),
                target_lang=target_lang.strip().lower(),
                pack_name=pack_name.strip() or "AI Translation Pack",
                pack_format=int(pack_format),
                base_url=resolved_base_url,
                api_key=api_key_stripped,
                model=resolved_model,
                only_missing=translation_mode == MISSING_ONLY_MODE,
                batch_size=int(batch_size),
                custom_prompt=custom_prompt.strip(),
            )
            result = run_translation(options, progress=emit)
            event_queue.put(("result", result))
        except Exception as exc:
            event_queue.put(("error", str(exc)))
        finally:
            event_queue.put(("finished", None))

    yield render("准备启动")

    worker_thread = Thread(target=worker, daemon=True)
    worker_thread.start()

    finished = False
    while not finished or not event_queue.empty():
        try:
            event_type, payload = event_queue.get(timeout=0.2)
        except Empty:
            if not worker_thread.is_alive() and event_queue.empty():
                break
            continue

        if event_type == "meta":
            payload_dict = payload if isinstance(payload, dict) else {}
            current_input = str(payload_dict.get("input_path", current_input))
            current_output_preview = str(payload_dict.get("output_preview", current_output_preview))
            messages = payload_dict.get("messages", [])
            for message in messages:
                logs.append(stamp(str(message)))
            current_detail = "输入校验完成，开始扫描语言文件。"
            yield render("翻译运行中")
            continue

        if event_type == "log":
            logs.append(stamp(str(payload)))
            current_detail = str(payload)
            yield render("翻译运行中")
            continue

        if event_type == "result":
            result = payload
            if hasattr(result, "skipped_assets") and result.skipped_assets:
                logs.append(stamp("Skipped entries:"))
                logs.extend(stamp(f"SKIPPED: {item}") for item in result.skipped_assets)
            if hasattr(result, "asset_count"):
                logs.append(stamp(f"Assets written: {result.asset_count}"))
            if hasattr(result, "translated_keys"):
                logs.append(stamp(f"Keys translated: {result.translated_keys}"))
            if hasattr(result, "pack_folder"):
                logs.append(stamp(f"Resource pack folder: {result.pack_folder}"))
            if hasattr(result, "zip_file"):
                logs.append(stamp(f"Resource pack zip: {result.zip_file}"))
            current_detail = "翻译任务完成，可以直接打开输出目录使用资源包。"
            yield render("翻译完成")
            continue

        if event_type == "error":
            logs.append(stamp(f"ERROR: {payload}"))
            current_detail = str(payload)
            yield render("翻译失败")
            continue

        if event_type == "finished":
            finished = True

    if not logs:
        logs.append(stamp("No logs captured."))
        yield render("翻译结束")


def update_provider_ui(provider_label: str) -> tuple[gr.Dropdown, gr.Textbox, gr.Markdown]:
    provider_key = provider_key_from_label(provider_label)
    provider = get_provider(provider_key)
    return (
        gr.Dropdown(
            choices=build_model_choices(provider_key),
            value=provider.default_model,
            allow_custom_value=True,
        ),
        gr.Textbox(value=provider.base_url),
        gr.Markdown(build_provider_note(provider_key)),
    )


def update_input_mode_ui(input_mode: str, current_path: str) -> tuple[gr.Textbox, gr.Markdown]:
    if input_mode == FOLDER_MODE:
        return (
            gr.Textbox(
                label="mods / resourcepacks / 整合包目录",
                placeholder=r"C:\Minecraft\Instances\MyPack\mods",
                value=current_path,
            ),
            gr.Markdown(build_input_mode_note(FOLDER_MODE), elem_classes="hint-box"),
        )
    return (
        gr.Textbox(
            label="模组 JAR / ZIP 文件",
            placeholder=r"C:\Minecraft\mods\FarmersDelight.jar",
            value=current_path,
        ),
        gr.Markdown(build_input_mode_note(SINGLE_MOD_MODE), elem_classes="hint-box"),
    )


def build_input_mode_note(input_mode: str) -> str:
    if input_mode == FOLDER_MODE:
        return (
            "**整个目录翻译**：适合直接选择 `mods`、`resourcepacks` 或整合包根目录。输出资源包会自动生成到该目录的同级位置。"
        )
    return "**单个模组翻译**：适合先拿一个 `.jar` / `.zip` 做冒烟测试。输出资源包会自动生成到该模组所在目录。"


def update_output_preview(input_path: str, pack_name: str) -> str:
    return build_output_preview(input_path, pack_name)


def pick_mod_file(current_path: str, pack_name: str) -> tuple[str, str]:
    selected_path = open_native_dialog(current_path, select_directory=False)
    return selected_path, build_output_preview(selected_path, pack_name)


def pick_directory(current_path: str, pack_name: str) -> tuple[str, str]:
    selected_path = open_native_dialog(current_path, select_directory=True)
    return selected_path, build_output_preview(selected_path, pack_name)


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


def validate_input_path(input_mode: str, input_path: str) -> Path:
    cleaned_path = input_path.strip().strip('"')
    if not cleaned_path:
        raise ValueError("请先选择要翻译的模组文件或目录。")

    path = Path(cleaned_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Path not found: {path}")

    if input_mode == SINGLE_MOD_MODE:
        if not path.is_file() or path.suffix.lower() not in {".jar", ".zip"}:
            raise ValueError("单个模组翻译模式需要选择一个 .jar 或 .zip 文件。")
    elif not path.is_dir():
        raise ValueError("整个目录翻译模式需要选择一个目录。")

    return path


def render_status_panel(
    *,
    title: str,
    detail: str,
    input_mode: str,
    input_path: str,
    output_preview: str,
) -> str:
    safe_input_mode = html.escape(input_mode)
    safe_input_path = html.escape(input_path or "尚未选择")
    safe_detail = html.escape(detail)
    safe_output = html.escape(output_preview or "等待输入路径").replace("\n", "<br>")
    return f"""
<div class="status-panel">
  <div class="status-label">运行状态</div>
  <h3>{html.escape(title)}</h3>
  <p>{safe_detail}</p>
  <div class="status-meta">
    <strong>当前工作流</strong>
    <code>{safe_input_mode}</code>
  </div>
  <div class="status-meta">
    <strong>输入路径</strong>
    <code>{safe_input_path}</code>
  </div>
  <div class="status-meta">
    <strong>输出预览</strong>
    <code>{safe_output}</code>
  </div>
</div>
""".strip()
