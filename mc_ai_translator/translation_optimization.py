from __future__ import annotations

REUSE_MODE_CONSERVATIVE = "conservative"
REUSE_MODE_AGGRESSIVE = "aggressive"
REUSE_MODE_OFF = "off"
DEFAULT_REUSE_MODE = REUSE_MODE_CONSERVATIVE
REUSE_MODE_ORDER = (
    REUSE_MODE_CONSERVATIVE,
    REUSE_MODE_AGGRESSIVE,
    REUSE_MODE_OFF,
)
REUSE_MODE_LABELS = {
    REUSE_MODE_CONSERVATIVE: "保守模式",
    REUSE_MODE_AGGRESSIVE: "激进模式",
    REUSE_MODE_OFF: "关闭",
}
REUSE_MODE_NOTES = {
    REUSE_MODE_CONSERVATIVE: "只在同一个语言 key 和原文都相同的时候复用，优先保证上下文稳定。",
    REUSE_MODE_AGGRESSIVE: "只要原文相同就直接复用，速度最快，但更容易把不同上下文压成同一个译法。",
    REUSE_MODE_OFF: "不复用任何历史翻译，每个 key 都单独送模型，最稳但最慢。",
}

DEFAULT_SKIP_COMPLETE_TARGETS = True
SKIP_COMPLETE_LABELS = {
    True: "开启",
    False: "关闭",
}

OPTIMIZATION_PRESET_STABLE = "stable"
OPTIMIZATION_PRESET_BALANCED = "balanced"
OPTIMIZATION_PRESET_FAST = "fast"
OPTIMIZATION_PRESET_CUSTOM = "custom"
DEFAULT_OPTIMIZATION_PRESET = OPTIMIZATION_PRESET_BALANCED
OPTIMIZATION_PRESET_ORDER = (
    OPTIMIZATION_PRESET_STABLE,
    OPTIMIZATION_PRESET_BALANCED,
    OPTIMIZATION_PRESET_FAST,
    OPTIMIZATION_PRESET_CUSTOM,
)
OPTIMIZATION_PRESET_LABELS = {
    OPTIMIZATION_PRESET_STABLE: "最稳",
    OPTIMIZATION_PRESET_BALANCED: "均衡",
    OPTIMIZATION_PRESET_FAST: "最快",
    OPTIMIZATION_PRESET_CUSTOM: "自定义",
}
OPTIMIZATION_PRESET_NOTES = {
    OPTIMIZATION_PRESET_STABLE: "关闭完整目标跳过和重复文本复用，优先保证结果一致性。",
    OPTIMIZATION_PRESET_BALANCED: "开启完整目标跳过，并使用保守复用，兼顾稳定性和速度。",
    OPTIMIZATION_PRESET_FAST: "开启完整目标跳过，并使用激进复用，优先减少请求量。",
    OPTIMIZATION_PRESET_CUSTOM: "当前是手动组合，可继续在下面两个开关里细调。",
}
OPTIMIZATION_PRESET_SETTINGS = {
    OPTIMIZATION_PRESET_STABLE: (False, REUSE_MODE_OFF),
    OPTIMIZATION_PRESET_BALANCED: (True, REUSE_MODE_CONSERVATIVE),
    OPTIMIZATION_PRESET_FAST: (True, REUSE_MODE_AGGRESSIVE),
}


def normalize_reuse_mode(mode: str | bool | None) -> str:
    if isinstance(mode, bool):
        return REUSE_MODE_AGGRESSIVE if mode else REUSE_MODE_OFF
    if not mode:
        return DEFAULT_REUSE_MODE

    normalized = str(mode).strip().lower()
    if normalized in REUSE_MODE_LABELS:
        return normalized

    for reuse_mode, label in REUSE_MODE_LABELS.items():
        if normalized == label.lower():
            return reuse_mode

    return DEFAULT_REUSE_MODE


def list_reuse_mode_labels() -> list[str]:
    return [REUSE_MODE_LABELS[mode] for mode in REUSE_MODE_ORDER]


def reuse_mode_key_from_label(label: str | bool | None) -> str:
    return normalize_reuse_mode(label)


def reuse_mode_label_from_key(mode: str | bool | None) -> str:
    return REUSE_MODE_LABELS[normalize_reuse_mode(mode)]


def build_reuse_mode_note(mode: str | bool | None) -> str:
    normalized = normalize_reuse_mode(mode)
    return f"**{REUSE_MODE_LABELS[normalized]}**：{REUSE_MODE_NOTES[normalized]}"


def normalize_skip_complete_targets(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return DEFAULT_SKIP_COMPLETE_TARGETS

    normalized = str(value).strip().lower()
    if not normalized:
        return DEFAULT_SKIP_COMPLETE_TARGETS
    if normalized in {"0", "false", "off", "关闭", "no", "n"}:
        return False
    if normalized in {"1", "true", "on", "开启", "yes", "y"}:
        return True

    for enabled, label in SKIP_COMPLETE_LABELS.items():
        if normalized == label.lower():
            return enabled
    return DEFAULT_SKIP_COMPLETE_TARGETS


def list_skip_complete_labels() -> list[str]:
    return [SKIP_COMPLETE_LABELS[True], SKIP_COMPLETE_LABELS[False]]


def skip_complete_enabled_from_label(label: str | bool | None) -> bool:
    return normalize_skip_complete_targets(label)


def skip_complete_label_from_enabled(enabled: str | bool | None) -> str:
    return SKIP_COMPLETE_LABELS[normalize_skip_complete_targets(enabled)]


def build_skip_complete_note(enabled: str | bool | None) -> str:
    if normalize_skip_complete_targets(enabled):
        return "**开启**：如果目标语言文件已经完整，就直接跳过，适合追求速度。"
    return "**关闭**：即使目标语言文件已经完整，也继续按当前翻译模式处理，适合严格重跑。"


def normalize_optimization_preset(preset: str | None) -> str:
    if not preset:
        return DEFAULT_OPTIMIZATION_PRESET

    normalized = str(preset).strip().lower()
    if normalized in OPTIMIZATION_PRESET_LABELS:
        return normalized

    for preset_key, label in OPTIMIZATION_PRESET_LABELS.items():
        if normalized == label.lower():
            return preset_key

    return DEFAULT_OPTIMIZATION_PRESET


def list_optimization_preset_labels() -> list[str]:
    return [OPTIMIZATION_PRESET_LABELS[preset] for preset in OPTIMIZATION_PRESET_ORDER]


def optimization_preset_key_from_label(label: str | None) -> str:
    return normalize_optimization_preset(label)


def optimization_preset_label_from_key(preset: str | None) -> str:
    return OPTIMIZATION_PRESET_LABELS[normalize_optimization_preset(preset)]


def build_optimization_preset_note(preset: str | None) -> str:
    normalized = normalize_optimization_preset(preset)
    return f"**{OPTIMIZATION_PRESET_LABELS[normalized]}**：{OPTIMIZATION_PRESET_NOTES[normalized]}"


def get_optimization_preset_settings(
    preset: str | None,
    *,
    fallback_skip_complete_targets: str | bool | None = DEFAULT_SKIP_COMPLETE_TARGETS,
    fallback_reuse_mode: str | bool | None = DEFAULT_REUSE_MODE,
) -> tuple[bool, str]:
    normalized = normalize_optimization_preset(preset)
    if normalized in OPTIMIZATION_PRESET_SETTINGS:
        skip_complete_targets, reuse_mode = OPTIMIZATION_PRESET_SETTINGS[normalized]
        return skip_complete_targets, reuse_mode

    return (
        normalize_skip_complete_targets(fallback_skip_complete_targets),
        normalize_reuse_mode(fallback_reuse_mode),
    )


def resolve_optimization_preset(
    skip_complete_targets: str | bool | None,
    reuse_mode: str | bool | None,
) -> str:
    normalized_skip = normalize_skip_complete_targets(skip_complete_targets)
    normalized_reuse = normalize_reuse_mode(reuse_mode)
    for preset, settings in OPTIMIZATION_PRESET_SETTINGS.items():
        if settings == (normalized_skip, normalized_reuse):
            return preset
    return OPTIMIZATION_PRESET_CUSTOM