from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderPreset:
    key: str
    label: str
    base_url: str
    models: tuple[str, ...]
    default_model: str
    requires_api_key: bool = True
    note: str = ""


PROVIDER_PRESETS: dict[str, ProviderPreset] = {
    "deepseek": ProviderPreset(
        key="deepseek",
        label="DeepSeek",
        base_url="https://api.deepseek.com",
        models=(
            "deepseek-v4-flash",
            "deepseek-v4-pro",
            "deepseek-chat",
            "deepseek-reasoner",
        ),
        default_model="deepseek-v4-flash",
        note="官方 OpenAI 兼容 base URL 是 https://api.deepseek.com，低成本场景优先用 deepseek-v4-flash。",
    ),
    "openai": ProviderPreset(
        key="openai",
        label="OpenAI",
        base_url="https://api.openai.com/v1",
        models=(
            "gpt-5.5",
            "gpt-5.4",
            "gpt-5.4-mini",
            "gpt-5.4-nano",
        ),
        default_model="gpt-5.4-mini",
        note="官方模型页推荐复杂任务用 gpt-5.5，注重成本和延迟时可用 gpt-5.4-mini。",
    ),
    "openrouter": ProviderPreset(
        key="openrouter",
        label="OpenRouter",
        base_url="https://openrouter.ai/api/v1",
        models=(
            "openai/gpt-5.2",
            "anthropic/claude-sonnet-4",
            "google/gemini-2.5-flash",
            "deepseek/deepseek-chat-v3.1",
        ),
        default_model="openai/gpt-5.2",
        note="官方 Quickstart 给出的 OpenAI SDK base URL 是 https://openrouter.ai/api/v1，可只填 API Key 即用。",
    ),
    "groq": ProviderPreset(
        key="groq",
        label="Groq",
        base_url="https://api.groq.com/openai/v1",
        models=(
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "qwen/qwen3-32b",
        ),
        default_model="openai/gpt-oss-20b",
        note="官方 OpenAI 兼容 base URL 是 https://api.groq.com/openai/v1，速度快，适合大批量翻译。",
    ),
    "dashscope": ProviderPreset(
        key="dashscope",
        label="阿里百炼 DashScope",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        models=(
            "qwen-plus",
            "qwen-turbo",
            "qwen-max",
            "qwen-flash",
            "qwen3.6-plus",
            "qwen3.6-flash",
        ),
        default_model="qwen-plus",
        note="默认填的是北京地域；如果你用美国或新加坡地域，需要手动改 Base URL。",
    ),
    "ollama": ProviderPreset(
        key="ollama",
        label="Ollama 本地",
        base_url="http://localhost:11434/v1",
        models=(
            "qwen3:8b",
            "gpt-oss:20b",
            "llama3.2",
        ),
        default_model="qwen3:8b",
        requires_api_key=False,
        note="Ollama 官方 OpenAI 兼容地址是 http://localhost:11434/v1，API Key 实际会被忽略。",
    ),
    "lmstudio": ProviderPreset(
        key="lmstudio",
        label="LM Studio 本地",
        base_url="http://localhost:1234/v1",
        models=(
            "local-model",
        ),
        default_model="local-model",
        requires_api_key=False,
        note="LM Studio 官方 OpenAI 兼容地址默认是 http://localhost:1234/v1，模型名通常填 local-model 即可。",
    ),
    "custom": ProviderPreset(
        key="custom",
        label="自定义 OpenAI 兼容接口",
        base_url="",
        models=(
            "gpt-5.4-mini",
            "deepseek-v4-flash",
            "qwen-plus",
        ),
        default_model="gpt-5.4-mini",
        note="完全手动填写 Base URL 和模型名，适合其他兼容服务或自建网关。",
    ),
}


def get_provider(provider_key: str | None) -> ProviderPreset:
    if provider_key and provider_key in PROVIDER_PRESETS:
        return PROVIDER_PRESETS[provider_key]
    return PROVIDER_PRESETS["custom"]


def list_provider_labels() -> list[str]:
    return [preset.label for preset in PROVIDER_PRESETS.values()]


def provider_key_from_label(label: str | None) -> str:
    if not label:
        return "custom"
    for provider_key, preset in PROVIDER_PRESETS.items():
        if preset.label == label:
            return provider_key
    return "custom"


def provider_label_from_key(provider_key: str | None) -> str:
    return get_provider(provider_key).label


def infer_provider_key(provider_key: str | None, base_url: str | None) -> str:
    if provider_key and provider_key in PROVIDER_PRESETS:
        return provider_key

    normalized_base_url = (base_url or "").strip().rstrip("/").lower()
    if normalized_base_url:
        for candidate_key, preset in PROVIDER_PRESETS.items():
            preset_base_url = preset.base_url.strip().rstrip("/").lower()
            if preset_base_url and normalized_base_url.startswith(preset_base_url):
                return candidate_key

    return "deepseek"


def resolve_provider_settings(
    provider_label: str,
    base_url: str,
    model: str,
) -> tuple[ProviderPreset, str, str]:
    provider = get_provider(provider_key_from_label(provider_label))
    resolved_base_url = (base_url or "").strip() or provider.base_url
    resolved_model = (model or "").strip() or provider.default_model
    return provider, resolved_base_url, resolved_model


def build_model_choices(provider_key: str, preferred_model: str | None = None) -> list[str]:
    provider = get_provider(provider_key)
    choices = list(provider.models)
    if preferred_model and preferred_model not in choices:
        choices.insert(0, preferred_model)
    return choices


def build_provider_note(provider_key: str) -> str:
    provider = get_provider(provider_key)
    api_key_note = "需要 API Key。" if provider.requires_api_key else "本地模式下 API Key 可留空。"
    return f"{provider.label}: {provider.note} {api_key_note}"