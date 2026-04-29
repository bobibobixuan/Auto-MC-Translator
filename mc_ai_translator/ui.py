from __future__ import annotations

import html
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
from typing import Iterator, List

import gradio as gr
from dotenv import load_dotenv

from .pipeline import (
    TranslationOptions,
    build_output_preview,
    resolve_output_root,
    resolve_pack_name,
    run_translation,
)
from .translation_optimization import (
    DEFAULT_REUSE_MODE,
    build_reuse_mode_note,
    build_skip_complete_note,
    build_optimization_preset_note,
    get_optimization_preset_settings,
    list_reuse_mode_labels,
    list_skip_complete_labels,
    list_optimization_preset_labels,
    normalize_reuse_mode,
    normalize_skip_complete_targets,
    optimization_preset_label_from_key,
    optimization_preset_key_from_label,
    resolve_optimization_preset,
    reuse_mode_key_from_label,
    reuse_mode_label_from_key,
    skip_complete_enabled_from_label,
    skip_complete_label_from_enabled,
)
from .language_presets import (
    build_language_picker_note,
    language_choice_from_code,
    list_language_preset_labels,
    normalize_language_code,
)
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
from .translation_skills import (
    DEFAULT_SKILL_KEY,
    build_translation_skill_note,
    list_translation_skill_labels,
    translation_skill_key_from_label,
    translation_skill_label_from_key,
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

.summary-card {
    background: linear-gradient(180deg, rgba(255, 250, 244, 0.96), rgba(248, 239, 229, 0.96));
    border: 1px solid var(--panel-border);
    border-radius: 22px;
    padding: 18px 20px;
    color: var(--text);
}

.summary-card h3 {
    margin: 0 0 8px;
    font-size: 1.22rem;
}

.summary-card p {
    margin: 0 0 14px;
    line-height: 1.6;
    color: var(--muted);
}

.summary-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 12px;
    margin-bottom: 14px;
}

.summary-metric {
    background: rgba(255, 255, 255, 0.72);
    border: 1px solid rgba(230, 203, 177, 0.9);
    border-radius: 16px;
    padding: 12px 14px;
}

.summary-metric span {
    display: block;
    font-size: 0.82rem;
    color: var(--muted);
    margin-bottom: 6px;
}

.summary-metric strong {
    font-size: 1.35rem;
    color: var(--accent-dark);
}

.summary-paths {
    display: grid;
    gap: 10px;
    margin-bottom: 12px;
}

.summary-paths strong {
    display: block;
    margin-bottom: 5px;
}

.summary-paths code {
    display: block;
    white-space: pre-wrap;
    font-family: "Cascadia Mono", Consolas, monospace;
    background: rgba(31, 77, 67, 0.08);
    border-radius: 12px;
    padding: 10px 12px;
}

.summary-table-wrap {
    overflow-x: auto;
}

.summary-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.94rem;
}

.summary-table th,
.summary-table td {
    text-align: left;
    padding: 10px 12px;
    border-bottom: 1px solid rgba(230, 203, 177, 0.8);
}

.summary-table th {
    color: var(--accent-dark);
    font-weight: 700;
    background: rgba(199, 107, 18, 0.08);
}

.summary-table tbody tr:nth-child(odd) {
    background: rgba(255, 255, 255, 0.55);
}

.action-stack {
    display: grid;
    gap: 10px;
}

.action-note {
    min-height: 72px;
}
"""

SINGLE_MOD_MODE = "单个模组翻译"
FOLDER_MODE = "整个目录翻译"
FULL_TRANSLATION_MODE = "完整翻译整个语言包"
MISSING_ONLY_MODE = "只补全缺失项"
AUTO_DETECT_MODE = "自动识别"
DEFAULT_SOURCE_LANG = "en_us"
DEFAULT_TARGET_LANG = "zh_cn"
DEFAULT_PACK_FORMAT = 15
DEFAULT_BATCH_SIZE = 60

DISCOVERED_ASSETS_RE = re.compile(r"^Discovered (\d+) language assets\. Unreadable entries during scan: (\d+)$")
ASSET_PROGRESS_RE = re.compile(
    r"^\[(\d+)/(\d+)\] (.+) \| source=(\d+) \| existing_target=(\d+) \| complete_target=(yes|no) \| queued=(\d+)$"
)
ASSET_WRITTEN_RE = re.compile(r"^\[(\d+)/(\d+)\] Wrote (\d+) translated entries for (.+)$")
ASSET_SKIP_COMPLETE_RE = re.compile(r"^\[(\d+)/(\d+)\] Complete target detected, skipped translation for (.+)$")
COMPLETE_SKIPPED_RE = re.compile(r"^Complete target files skipped: (\d+)$")


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
    default_skill_key = os.getenv("OPENAI_TRANSLATION_SKILL", DEFAULT_SKILL_KEY)
    default_skill_label = translation_skill_label_from_key(default_skill_key)
    default_skill_note = build_translation_skill_note(default_skill_key)
    default_reuse_mode = normalize_reuse_mode(os.getenv("OPENAI_TRANSLATION_REUSE_MODE", DEFAULT_REUSE_MODE))
    default_reuse_label = reuse_mode_label_from_key(default_reuse_mode)
    default_reuse_note = build_reuse_mode_note(default_reuse_mode)
    default_skip_complete = normalize_skip_complete_targets(os.getenv("OPENAI_SKIP_COMPLETE_TARGETS"))
    default_skip_complete_label = skip_complete_label_from_enabled(default_skip_complete)
    default_skip_complete_note = build_skip_complete_note(default_skip_complete)
    default_optimization_preset = resolve_optimization_preset(default_skip_complete, default_reuse_mode)
    default_optimization_preset_label = optimization_preset_label_from_key(default_optimization_preset)
    default_optimization_preset_note = build_optimization_preset_note(default_optimization_preset)
    default_source_choice = language_choice_from_code(DEFAULT_SOURCE_LANG)
    default_target_choice = language_choice_from_code(DEFAULT_TARGET_LANG)
    default_target_note = build_language_picker_note(DEFAULT_TARGET_LANG)
    default_source_note = build_language_picker_note(DEFAULT_SOURCE_LANG)
    default_pack_name = ""
    default_output_preview = build_output_preview("", default_pack_name, DEFAULT_TARGET_LANG)

    with gr.Blocks(title="Minecraft AI Translator") as app:
        gr.Markdown(
            """
<div class="hero-card">
  <div class="hero-kicker">本地 AI 汉化工作台</div>
  <h1>Minecraft AI Translator</h1>
  <p>默认配置已经调好。通常只要选择模组或目录、填写 API Key，然后点击开始翻译，结果会固定导出到程序目录下的 output 文件夹。</p>
  <div class="hero-tags">
    <span>开箱即用默认值</span>
    <span>自动识别输入类型</span>
    <span>固定输出到 output</span>
    <span>资源包名称可自定义</span>
  </div>
</div>
            """.strip()
        )

        with gr.Row():
            with gr.Column(scale=7, elem_classes="section-card"):
                gr.Markdown("<div class='section-title'>一步开始</div><div class='section-subtitle'>默认值已经调好。通常只需要选择路径、填写资源包名称和 API Key。</div>")
                workflow_note = gr.Markdown(
                    "**自动识别输入类型**：可以直接选择单个 `.jar` / `.zip`，也可以选择 `mods`、`resourcepacks` 或整合包目录。输出会固定写到程序目录下的 `output` 文件夹。",
                    elem_classes="hint-box",
                )
                with gr.Row():
                    modpack_path = gr.Textbox(
                        label="模组文件或目录",
                        placeholder=r"C:\Minecraft\mods\FarmersDelight.jar 或 C:\Minecraft\Instances\MyPack\mods",
                    )
                    with gr.Column(scale=0, min_width=170):
                        choose_file_button = gr.Button("选择模组文件", variant="secondary")
                        choose_dir_button = gr.Button("选择目录", variant="secondary")
                pack_name = gr.Textbox(
                    label="资源包名称（可自定义）",
                    value=default_pack_name,
                    placeholder="不填会按输入名称自动生成，例如 FarmersDelight-zh_cn",
                )
                target_lang = gr.Dropdown(
                    label="目标语言",
                    choices=list_language_preset_labels(),
                    value=default_target_choice,
                    allow_custom_value=True,
                )
                target_lang_note = gr.Markdown(default_target_note)
                api_key = gr.Textbox(label="API Key", type="password", value=default_api_key)
                output_preview = gr.Textbox(
                    label="输出位置预览（固定输出到程序目录 output）",
                    value=default_output_preview,
                    lines=2,
                    interactive=False,
                )
            with gr.Column(scale=5, elem_classes="section-card"):
                status_panel = gr.HTML(
                    render_status_panel(
                        title="等待开始",
                        detail="选择输入路径并填写 API Key 后即可启动任务。默认结果固定保存到程序目录下的 output 文件夹。",
                        input_mode=AUTO_DETECT_MODE,
                        input_path="",
                        output_preview=default_output_preview,
                    )
                )

        with gr.Accordion("高级设置", open=False):
            with gr.Row():
                with gr.Column(scale=6, elem_classes="section-card"):
                    gr.Markdown("<div class='section-title'>翻译细节</div><div class='section-subtitle'>一般保持默认即可。只有需要特殊语言、特殊输出格式或补全模式时再修改。</div>")
                    with gr.Row():
                        source_lang = gr.Dropdown(
                            label="源语言",
                            choices=list_language_preset_labels(),
                            value=default_source_choice,
                            allow_custom_value=True,
                        )
                        pack_format = gr.Number(label="pack_format", value=DEFAULT_PACK_FORMAT, precision=0)
                    source_lang_note = gr.Markdown(default_source_note)
                    optimization_preset = gr.Dropdown(
                        label="推荐预设",
                        choices=list_optimization_preset_labels(),
                        value=default_optimization_preset_label,
                        allow_custom_value=False,
                    )
                    optimization_preset_note = gr.Markdown(default_optimization_preset_note)
                    translation_mode = gr.Radio(
                        label="翻译策略",
                        choices=[FULL_TRANSLATION_MODE, MISSING_ONLY_MODE],
                        value=FULL_TRANSLATION_MODE,
                    )
                    skip_complete_targets = gr.Radio(
                        label="完整目标文件跳过",
                        choices=list_skip_complete_labels(),
                        value=default_skip_complete_label,
                    )
                    skip_complete_note = gr.Markdown(default_skip_complete_note)
                    skill = gr.Dropdown(
                        label="翻译 Skill",
                        choices=list_translation_skill_labels(),
                        value=default_skill_label,
                    )
                    skill_note = gr.Markdown(default_skill_note)
                    reuse_mode = gr.Radio(
                        label="重复文本复用",
                        choices=list_reuse_mode_labels(),
                        value=default_reuse_label,
                    )
                    reuse_mode_note = gr.Markdown(default_reuse_note)
                    batch_size = gr.Slider(label="每批翻译条目数", minimum=5, maximum=100, value=DEFAULT_BATCH_SIZE, step=1)

                with gr.Column(scale=6, elem_classes="section-card"):
                    gr.Markdown("<div class='section-title'>模型与接口</div><div class='section-subtitle'>默认是 DeepSeek 低成本配置。只有更换服务商或调试兼容接口时才需要改动。</div>")
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
                    base_url = gr.Textbox(label="OpenAI 兼容接口 Base URL", value=default_base_url)
                    custom_prompt = gr.Textbox(
                        label="额外提示词（可选，越长越耗 token）",
                        lines=4,
                        placeholder="仅在确有必要时填写；这段内容会跟随每个批次重复发送给模型。",
                    )

        run_button = gr.Button("开始一键翻译", variant="primary")
        with gr.Tabs():
            with gr.Tab("小白日志"):
                beginner_log_text = gr.Textbox(label="小白日志", lines=14, elem_classes="log-box", interactive=False)
            with gr.Tab("开发者日志"):
                developer_log_text = gr.Textbox(label="开发者日志", lines=22, elem_classes="log-box", interactive=False)
        with gr.Row():
            with gr.Column(scale=8, elem_classes="section-card"):
                gr.Markdown("<div class='section-title'>翻译摘要</div><div class='section-subtitle'>任务完成后，会汇总当前项目、模组列表和词条统计。</div>")
                summary_panel = gr.HTML(
                    render_summary_panel(
                        input_path="",
                        source_lang="en_us",
                        target_lang="zh_cn",
                        output_folder="",
                        report_file="",
                        asset_count=None,
                        translated_keys=None,
                        skipped_complete_assets=0,
                        skipped_count=0,
                        mod_summaries=[],
                    )
                )
            with gr.Column(scale=4, elem_classes="section-card action-stack"):
                gr.Markdown("<div class='section-title'>快捷打开</div><div class='section-subtitle'>翻译完成后可以直接打开导出目录和报告文件。</div>")
                quick_open_status = gr.HTML("<div class='hint-box action-note'>翻译完成后，这里会启用快捷打开操作。</div>")
                open_folder_button = gr.Button("快捷打开导出文件夹", variant="secondary", interactive=False)
                open_report_button = gr.Button("快捷打开翻译报告", variant="secondary", interactive=False)
                export_folder_state = gr.State("")
                report_file_state = gr.State("")

        run_button.click(
            fn=run_from_ui,
            inputs=[
                modpack_path,
                pack_name,
                api_key,
                source_lang,
                target_lang,
                pack_format,
                provider,
                base_url,
                model,
                translation_mode,
                skip_complete_targets,
                skill,
                reuse_mode,
                batch_size,
                custom_prompt,
            ],
            outputs=[
                status_panel,
                beginner_log_text,
                developer_log_text,
                summary_panel,
                export_folder_state,
                report_file_state,
                open_folder_button,
                open_report_button,
                quick_open_status,
            ],
            concurrency_limit=1,
        )

        open_folder_button.click(
            fn=open_export_target,
            inputs=[export_folder_state],
            outputs=[quick_open_status],
            concurrency_limit=1,
        )
        open_report_button.click(
            fn=open_export_target,
            inputs=[report_file_state],
            outputs=[quick_open_status],
            concurrency_limit=1,
        )

        provider.change(
            fn=update_provider_ui,
            inputs=[provider],
            outputs=[model, base_url, provider_note],
        )
        skill.change(
            fn=update_skill_note,
            inputs=[skill],
            outputs=[skill_note],
        )
        optimization_preset.change(
            fn=apply_optimization_preset,
            inputs=[optimization_preset, skip_complete_targets, reuse_mode],
            outputs=[
                skip_complete_targets,
                skip_complete_note,
                reuse_mode,
                reuse_mode_note,
                optimization_preset_note,
            ],
        )
        skip_complete_targets.change(
            fn=handle_skip_complete_change,
            inputs=[skip_complete_targets, reuse_mode],
            outputs=[skip_complete_note, optimization_preset, optimization_preset_note],
        )
        reuse_mode.change(
            fn=handle_reuse_mode_change,
            inputs=[skip_complete_targets, reuse_mode],
            outputs=[reuse_mode_note, optimization_preset, optimization_preset_note],
        )
        target_lang.change(
            fn=update_language_note,
            inputs=[target_lang],
            outputs=[target_lang_note],
        )
        source_lang.change(
            fn=update_language_note,
            inputs=[source_lang],
            outputs=[source_lang_note],
        )

        modpack_path.change(
            fn=update_output_preview,
            inputs=[modpack_path, pack_name, target_lang],
            outputs=[output_preview],
        )
        pack_name.change(
            fn=update_output_preview,
            inputs=[modpack_path, pack_name, target_lang],
            outputs=[output_preview],
        )
        target_lang.change(
            fn=update_output_preview,
            inputs=[modpack_path, pack_name, target_lang],
            outputs=[output_preview],
        )
        choose_file_button.click(
            fn=pick_mod_file,
            inputs=[modpack_path, pack_name, target_lang],
            outputs=[modpack_path, pack_name, output_preview],
        )
        choose_dir_button.click(
            fn=pick_directory,
            inputs=[modpack_path, pack_name, target_lang],
            outputs=[modpack_path, pack_name, output_preview],
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
    modpack_path: str,
    pack_name: str,
    api_key: str,
    source_lang: str,
    target_lang: str,
    pack_format: float,
    provider: str,
    base_url: str,
    model: str,
    translation_mode: str,
    skip_complete_targets: str,
    skill: str,
    reuse_mode: str,
    batch_size: int,
    custom_prompt: str,
) -> Iterator[tuple[str, str, str, str, str, str, gr.Button, gr.Button, str]]:
    beginner_logs: List[str] = []
    developer_logs: List[str] = []
    event_queue: Queue[tuple[str, object]] = Queue()

    normalized_source_lang = normalize_language_code(source_lang) or DEFAULT_SOURCE_LANG
    normalized_target_lang = normalize_language_code(target_lang) or DEFAULT_TARGET_LANG
    current_input = modpack_path.strip().strip('"')
    current_workflow = AUTO_DETECT_MODE
    current_output_preview = build_output_preview(current_input, pack_name, normalized_target_lang)
    current_detail = "默认配置已就绪，正在校验输入配置。"
    current_summary = render_summary_panel(
        input_path=current_input,
        source_lang=normalized_source_lang,
        target_lang=normalized_target_lang,
        output_folder="",
        report_file="",
        asset_count=None,
        translated_keys=None,
        skipped_complete_assets=0,
        skipped_count=0,
        mod_summaries=[],
    )
    export_folder = ""
    report_file = ""
    quick_open_note = "<div class='hint-box action-note'>翻译完成后，你可以直接打开程序目录下的 output 文件夹或翻译报告。</div>"

    def stamp(message: str) -> str:
        return f"[{datetime.now().strftime('%H:%M:%S')}] {message}"

    def render(title: str) -> tuple[str, str, str, str, str, str, gr.Button, gr.Button, str]:
        return (
            render_status_panel(
                title=title,
                detail=current_detail,
                input_mode=current_workflow,
                input_path=current_input,
                output_preview=current_output_preview,
            ),
            "\n".join(beginner_logs),
            "\n".join(developer_logs),
            current_summary,
            export_folder,
            report_file,
            build_action_button("快捷打开导出文件夹", interactive=bool(export_folder)),
            build_action_button("快捷打开翻译报告", interactive=bool(report_file)),
            quick_open_note,
        )

    def emit(message: str) -> None:
        event_queue.put(("log", message))

    def add_beginner_log(message: str) -> None:
        beginner_logs.append(stamp(message))

    def add_developer_log(message: str) -> None:
        developer_logs.append(stamp(message))

    def worker() -> None:
        try:
            resolved_provider, resolved_base_url, resolved_model = resolve_provider_settings(
                provider,
                base_url,
                model,
            )
            api_key_stripped = api_key.strip()
            selected_path = validate_input_path(modpack_path)
            workflow_label = describe_input_mode(selected_path)
            resolved_pack_name = resolve_pack_name(pack_name, selected_path, normalized_target_lang)
            output_root = resolve_output_root(selected_path)
            selected_skip_complete = skip_complete_enabled_from_label(skip_complete_targets)
            selected_reuse_mode = reuse_mode_key_from_label(reuse_mode)
            if resolved_provider.requires_api_key and not api_key_stripped:
                raise ValueError(f"【配置错误】服务商预设「{resolved_provider.label}」需要填写 API Key。")

            event_queue.put(
                (
                    "meta",
                    {
                        "workflow_label": workflow_label,
                        "input_path": str(selected_path),
                        "output_preview": build_output_preview(str(selected_path), resolved_pack_name, normalized_target_lang),
                        "messages": [
                            f"Input mode: {workflow_label}",
                            f"Pack name: {resolved_pack_name}",
                            f"Provider preset: {resolved_provider.label}",
                            f"Model: {resolved_model}",
                            f"Complete target skip: {skip_complete_targets}",
                            f"Translation skill: {skill}",
                            f"Duplicate text reuse: {reuse_mode}",
                            f"Base URL: {resolved_base_url}",
                            f"Output root: {output_root}",
                        ],
                    },
                )
            )

            options = TranslationOptions(
                modpack_path=selected_path,
                output_root=output_root,
                source_lang=normalized_source_lang,
                target_lang=normalized_target_lang,
                pack_name=resolved_pack_name,
                pack_format=int(pack_format),
                base_url=resolved_base_url,
                api_key=api_key_stripped,
                model=resolved_model,
                only_missing=translation_mode == MISSING_ONLY_MODE,
                batch_size=int(batch_size),
                skill_key=translation_skill_key_from_label(skill),
                reuse_mode=selected_reuse_mode,
                skip_complete_targets=selected_skip_complete,
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
            current_workflow = str(payload_dict.get("workflow_label", current_workflow))
            current_input = str(payload_dict.get("input_path", current_input))
            current_output_preview = str(payload_dict.get("output_preview", current_output_preview))
            messages = payload_dict.get("messages", [])
            add_beginner_log("任务已启动，正在校验输入并准备扫描语言文件。")
            for message in messages:
                add_developer_log(str(message))
            current_detail = "输入校验完成，开始扫描语言文件。"
            current_summary = render_summary_panel(
                input_path=current_input,
                source_lang=normalized_source_lang,
                target_lang=normalized_target_lang,
                output_folder="",
                report_file="",
                asset_count=None,
                translated_keys=None,
                skipped_complete_assets=0,
                skipped_count=0,
                mod_summaries=[],
            )
            yield render("翻译运行中")
            continue

        if event_type == "log":
            message = str(payload)
            add_developer_log(message)
            beginner_message = build_beginner_log_entry(message)
            if beginner_message:
                add_beginner_log(beginner_message)
            current_detail = beginner_message or message
            yield render("翻译运行中")
            continue

        if event_type == "result":
            result = payload
            if hasattr(result, "skipped_assets") and result.skipped_assets:
                add_developer_log("Skipped entries:")
                for item in result.skipped_assets:
                    add_developer_log(f"SKIPPED: {item}")
            if hasattr(result, "asset_count"):
                add_developer_log(f"Assets written: {result.asset_count}")
            if hasattr(result, "translated_keys"):
                add_developer_log(f"Keys translated: {result.translated_keys}")
            if hasattr(result, "skipped_complete_assets"):
                add_developer_log(f"Complete target files skipped: {result.skipped_complete_assets}")
            if hasattr(result, "cache_hits"):
                add_developer_log(f"Optimization hits: {result.cache_hits}")
            if hasattr(result, "api_entry_count"):
                add_developer_log(f"Entries sent to API: {result.api_entry_count}")
            if hasattr(result, "pack_folder"):
                add_developer_log(f"Resource pack folder: {result.pack_folder}")
            if hasattr(result, "zip_file"):
                add_developer_log(f"Resource pack zip: {result.zip_file}")
            export_folder = str(getattr(result, "pack_folder", ""))
            report_file = str(getattr(result, "report_file", ""))
            mod_summaries = list(getattr(result, "mod_summaries", []))
            translated_mod_count = sum(1 for item in mod_summaries if getattr(item, "translated_keys", 0) > 0)
            current_detail = (
                f"翻译任务完成，共统计 {len(mod_summaries)} 个模组，实际写入 {translated_mod_count} 个模组、"
                f"跳过 {getattr(result, 'skipped_complete_assets', 0)} 个已完整翻译文件，"
                f"{getattr(result, 'translated_keys', 0)} 条翻译；优化命中 {getattr(result, 'cache_hits', 0)} 条，"
                f"实际发送到模型 {getattr(result, 'api_entry_count', 0)} 条。"
            )
            add_beginner_log(current_detail)
            current_summary = render_summary_panel(
                input_path=str(getattr(result, "project_path", current_input)),
                source_lang=normalized_source_lang,
                target_lang=normalized_target_lang,
                output_folder=export_folder,
                report_file=report_file,
                asset_count=getattr(result, "asset_count", 0),
                translated_keys=getattr(result, "translated_keys", 0),
                skipped_complete_assets=getattr(result, "skipped_complete_assets", 0),
                skipped_count=len(getattr(result, "skipped_assets", [])),
                mod_summaries=mod_summaries,
            )
            quick_open_note = "<div class='hint-box action-note'>已生成导出目录，可以直接使用下方按钮打开文件夹或翻译报告。</div>"
            yield render("翻译完成")
            continue

        if event_type == "error":
            add_developer_log(f"ERROR: {payload}")
            add_beginner_log(f"任务失败：{payload}")
            current_detail = str(payload)
            export_folder = ""
            report_file = ""
            quick_open_note = "<div class='hint-box action-note'>任务未完成，快捷打开操作暂不可用。</div>"
            yield render("翻译失败")
            continue

        if event_type == "finished":
            finished = True

    if not beginner_logs and not developer_logs:
        add_developer_log("No logs captured.")
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


def update_skill_note(skill_label: str) -> gr.Markdown:
    return gr.Markdown(build_translation_skill_note(translation_skill_key_from_label(skill_label)))


def apply_optimization_preset(
    preset_label: str,
    current_skip_complete_label: str,
    current_reuse_mode_label: str,
) -> tuple[dict[str, object], gr.Markdown, dict[str, object], gr.Markdown, gr.Markdown]:
    skip_complete_targets, reuse_mode = get_optimization_preset_settings(
        optimization_preset_key_from_label(preset_label),
        fallback_skip_complete_targets=current_skip_complete_label,
        fallback_reuse_mode=current_reuse_mode_label,
    )
    return (
        gr.update(
            choices=list_skip_complete_labels(),
            value=skip_complete_label_from_enabled(skip_complete_targets),
        ),
        gr.Markdown(build_skip_complete_note(skip_complete_targets)),
        gr.update(
            choices=list_reuse_mode_labels(),
            value=reuse_mode_label_from_key(reuse_mode),
        ),
        gr.Markdown(build_reuse_mode_note(reuse_mode)),
        gr.Markdown(build_optimization_preset_note(preset_label)),
    )


def _resolve_optimization_preset_update(skip_complete_label: str, reuse_mode_label: str) -> tuple[dict[str, object], gr.Markdown]:
    preset_key = resolve_optimization_preset(skip_complete_label, reuse_mode_label)
    return (
        gr.update(
            choices=list_optimization_preset_labels(),
            value=optimization_preset_label_from_key(preset_key),
        ),
        gr.Markdown(build_optimization_preset_note(preset_key)),
    )


def handle_skip_complete_change(
    skip_complete_label: str,
    reuse_mode_label: str,
) -> tuple[gr.Markdown, dict[str, object], gr.Markdown]:
    preset_update, preset_note_update = _resolve_optimization_preset_update(skip_complete_label, reuse_mode_label)
    return (
        gr.Markdown(build_skip_complete_note(skip_complete_label)),
        preset_update,
        preset_note_update,
    )


def update_skip_complete_note(skip_complete_label: str) -> gr.Markdown:
    return gr.Markdown(build_skip_complete_note(skip_complete_label))


def handle_reuse_mode_change(
    skip_complete_label: str,
    reuse_mode_label: str,
) -> tuple[gr.Markdown, dict[str, object], gr.Markdown]:
    preset_update, preset_note_update = _resolve_optimization_preset_update(skip_complete_label, reuse_mode_label)
    return (
        gr.Markdown(build_reuse_mode_note(reuse_mode_label)),
        preset_update,
        preset_note_update,
    )


def update_reuse_mode_note(reuse_mode_label: str) -> gr.Markdown:
    return gr.Markdown(build_reuse_mode_note(reuse_mode_label))


def update_language_note(language_value: str) -> gr.Markdown:
    return gr.Markdown(build_language_picker_note(normalize_language_code(language_value)))


def update_output_preview(input_path: str, pack_name: str, target_lang: str) -> str:
    normalized_target_lang = normalize_language_code(target_lang) or DEFAULT_TARGET_LANG
    return build_output_preview(input_path, pack_name, normalized_target_lang)


def pick_mod_file(current_path: str, pack_name: str, target_lang: str) -> tuple[str, str, str]:
    selected_path = open_native_dialog(current_path, select_directory=False)
    resolved_pack_name = suggest_pack_name(selected_path, pack_name, target_lang)
    return selected_path, resolved_pack_name, update_output_preview(selected_path, resolved_pack_name, target_lang)


def pick_directory(current_path: str, pack_name: str, target_lang: str) -> tuple[str, str, str]:
    selected_path = open_native_dialog(current_path, select_directory=True)
    resolved_pack_name = suggest_pack_name(selected_path, pack_name, target_lang)
    return selected_path, resolved_pack_name, update_output_preview(selected_path, resolved_pack_name, target_lang)


def suggest_pack_name(input_path: str, pack_name: str, target_lang: str) -> str:
    if pack_name.strip():
        return pack_name.strip()
    cleaned_path = input_path.strip().strip('"')
    if not cleaned_path:
        return ""
    normalized_target_lang = normalize_language_code(target_lang) or DEFAULT_TARGET_LANG
    path = Path(cleaned_path).expanduser()
    base_name = path.stem if path.suffix else path.name
    base_name = base_name.strip() or "AI Translation Pack"
    return f"{base_name}-{normalized_target_lang}"


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
    if path.is_file():
        return SINGLE_MOD_MODE
    return FOLDER_MODE


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


def summarize_asset_identifier(identifier: str) -> str:
    mod_name, _, rest = identifier.partition(":")
    namespace, _, extension = rest.partition(":")
    if namespace and extension:
        return f"{mod_name} / {namespace}.{extension}"
    return identifier


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


def render_summary_panel(
        *,
        input_path: str,
        source_lang: str,
        target_lang: str,
        output_folder: str,
        report_file: str,
        asset_count: int | None,
        translated_keys: int | None,
    skipped_complete_assets: int,
        skipped_count: int,
        mod_summaries: List[object],
) -> str:
        project_name = Path(input_path).name if input_path else "等待任务开始"
        safe_project_name = html.escape(project_name)
        safe_input_path = html.escape(input_path or "尚未开始任务")
        safe_output_folder = html.escape(output_folder or "任务完成后显示")
        safe_report_file = html.escape(report_file or "任务完成后生成 translation_report.json")
        metrics = [
                ("模组总数", len(mod_summaries) if asset_count is not None else "-"),
                (
                        "实际翻译模组",
                        sum(1 for item in mod_summaries if getattr(item, "translated_keys", 0) > 0) if asset_count is not None else "-",
                ),
                ("语言文件数", asset_count if asset_count is not None else "-"),
                ("翻译条数", translated_keys if translated_keys is not None else "-"),
                ("完整翻译跳过", skipped_complete_assets if asset_count is not None else "-"),
                ("跳过项", skipped_count if asset_count is not None else "-"),
        ]
        metric_cards = "".join(
                f"<div class='summary-metric'><span>{html.escape(label)}</span><strong>{html.escape(str(value))}</strong></div>"
                for label, value in metrics
        )

        if asset_count is None:
                table_rows = "<tr><td colspan='5'>任务完成后，会在这里列出每个模组的翻译条数和语言文件数。</td></tr>"
                summary_lead = (
                        f"当前等待执行。项目会按 {html.escape(source_lang)} -> {html.escape(target_lang)} 的方向翻译，完成后在这里汇总结果。"
                )
        else:
                ordered_summaries = sorted(
                        mod_summaries,
                        key=lambda item: (-getattr(item, "translated_keys", 0), getattr(item, "mod_name", "").lower()),
                )
                table_rows = "".join(
                        "<tr>"
                        f"<td>{html.escape(str(getattr(item, 'mod_name', '-')))}</td>"
                        f"<td>{html.escape(str(getattr(item, 'translated_keys', 0)))}</td>"
                        f"<td>{html.escape(str(getattr(item, 'queued_keys', 0)))}</td>"
                        f"<td>{html.escape(str(getattr(item, 'source_keys', 0)))}</td>"
                        f"<td>{html.escape(str(getattr(item, 'asset_count', 0)))}</td>"
                        "</tr>"
                        for item in ordered_summaries
                )
                summary_lead = (
                        f"项目 {safe_project_name} 已完成翻译，以下是本次导出的模组和词条统计。"
                )

        return f"""
<div class="summary-card">
    <h3>翻译项目摘要</h3>
    <p>{summary_lead}</p>
    <div class="summary-grid">
        {metric_cards}
    </div>
    <div class="summary-paths">
        <div>
            <strong>翻译项目</strong>
            <code>{safe_input_path}</code>
        </div>
        <div>
            <strong>导出目录</strong>
            <code>{safe_output_folder}</code>
        </div>
        <div>
            <strong>翻译报告</strong>
            <code>{safe_report_file}</code>
        </div>
    </div>
    <div class="summary-table-wrap">
        <table class="summary-table">
            <thead>
                <tr>
                    <th>模组</th>
                    <th>已翻译条数</th>
                    <th>待处理条数</th>
                    <th>总词条数</th>
                    <th>语言文件数</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
    </div>
</div>
""".strip()


def build_action_button(label: str, *, interactive: bool) -> gr.Button:
        return gr.Button(value=label, variant="secondary", interactive=interactive)


def open_export_target(path_text: str) -> str:
        cleaned_path = path_text.strip().strip('"')
        if not cleaned_path:
                return "<div class='hint-box action-note'>当前没有可打开的导出目标，请先完成一次翻译任务。</div>"

        path = Path(cleaned_path)
        if not path.exists():
                raise FileNotFoundError(f"输出不存在: {path}")

        open_path_with_system(path)
        target_kind = "目录" if path.is_dir() else "文件"
        safe_path = html.escape(str(path))
        return f"<div class='hint-box action-note'>已打开{target_kind}：<br>{safe_path}</div>"


def open_path_with_system(path: Path) -> None:
        if os.name == "nt":
                os.startfile(str(path))
                return
        if sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
                return
        subprocess.Popen(["xdg-open", str(path)])
