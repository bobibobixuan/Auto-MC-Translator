from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TranslationSkill:
    key: str
    label: str
    system_prompt: str
    note: str


DEFAULT_SKILL_KEY = "fast"


TRANSLATION_SKILLS: dict[str, TranslationSkill] = {
    "fast": TranslationSkill(
        key="fast",
        label="极速模组翻译 Skill",
        system_prompt=(
            "Prefer concise direct Chinese for Minecraft UI, item, block, entity and tooltip text. "
            "Keep recurring terms stable. Do not explain choices or add extra wording."
        ),
        note="默认推荐。提示词最短，适合大批量模组翻译，优先省 token 和时间。",
    ),
    "balanced": TranslationSkill(
        key="balanced",
        label="平衡术语 Skill",
        system_prompt=(
            "Use common Minecraft community terms when they are obvious, while keeping the wording concise and readable."
        ),
        note="在速度和自然度之间取平衡，适合大多数公开整合包。",
    ),
    "immersive": TranslationSkill(
        key="immersive",
        label="沉浸润色 Skill",
        system_prompt=(
            "Prefer a slightly more polished in-game tone, but keep names, placeholders and gameplay meaning exact."
        ),
        note="更偏向表现力，通常会比默认 skill 更慢，也更耗 token。",
    ),
}


def get_translation_skill(skill_key: str | None) -> TranslationSkill:
    if skill_key and skill_key in TRANSLATION_SKILLS:
        return TRANSLATION_SKILLS[skill_key]
    return TRANSLATION_SKILLS[DEFAULT_SKILL_KEY]


def list_translation_skill_labels() -> list[str]:
    return [skill.label for skill in TRANSLATION_SKILLS.values()]


def translation_skill_key_from_label(label: str | None) -> str:
    if not label:
        return DEFAULT_SKILL_KEY
    for skill_key, skill in TRANSLATION_SKILLS.items():
        if skill.label == label:
            return skill_key
    return DEFAULT_SKILL_KEY


def translation_skill_label_from_key(skill_key: str | None) -> str:
    return get_translation_skill(skill_key).label


def build_translation_skill_note(skill_key: str | None) -> str:
    skill = get_translation_skill(skill_key)
    return f"{skill.label}: {skill.note}"