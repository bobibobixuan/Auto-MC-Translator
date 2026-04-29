from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LanguagePreset:
    code: str
    label: str

    @property
    def display_label(self) -> str:
        return f"{self.label} | {self.code}"


DEFAULT_SOURCE_LANG = "en_us"
DEFAULT_TARGET_LANG = "zh_cn"

LANGUAGE_PRESETS: tuple[LanguagePreset, ...] = (
    LanguagePreset("en_us", "英语（美国）"),
    LanguagePreset("en_gb", "英语（英国）"),
    LanguagePreset("zh_cn", "简体中文"),
    LanguagePreset("zh_tw", "繁体中文"),
    LanguagePreset("ja_jp", "日语"),
    LanguagePreset("ko_kr", "韩语"),
    LanguagePreset("fr_fr", "法语"),
    LanguagePreset("de_de", "德语"),
    LanguagePreset("es_es", "西班牙语（西班牙）"),
    LanguagePreset("es_mx", "西班牙语（墨西哥）"),
    LanguagePreset("pt_br", "葡萄牙语（巴西）"),
    LanguagePreset("pt_pt", "葡萄牙语（葡萄牙）"),
    LanguagePreset("it_it", "意大利语"),
    LanguagePreset("ru_ru", "俄语"),
    LanguagePreset("uk_ua", "乌克兰语"),
    LanguagePreset("pl_pl", "波兰语"),
    LanguagePreset("nl_nl", "荷兰语"),
    LanguagePreset("cs_cz", "捷克语"),
    LanguagePreset("sk_sk", "斯洛伐克语"),
    LanguagePreset("hu_hu", "匈牙利语"),
    LanguagePreset("tr_tr", "土耳其语"),
    LanguagePreset("sv_se", "瑞典语"),
    LanguagePreset("fi_fi", "芬兰语"),
    LanguagePreset("da_dk", "丹麦语"),
    LanguagePreset("nb_no", "挪威语"),
    LanguagePreset("ro_ro", "罗马尼亚语"),
    LanguagePreset("bg_bg", "保加利亚语"),
    LanguagePreset("el_gr", "希腊语"),
    LanguagePreset("hr_hr", "克罗地亚语"),
    LanguagePreset("sl_si", "斯洛文尼亚语"),
    LanguagePreset("lt_lt", "立陶宛语"),
    LanguagePreset("lv_lv", "拉脱维亚语"),
    LanguagePreset("et_ee", "爱沙尼亚语"),
    LanguagePreset("vi_vn", "越南语"),
    LanguagePreset("id_id", "印度尼西亚语"),
    LanguagePreset("ms_my", "马来语"),
    LanguagePreset("th_th", "泰语"),
    LanguagePreset("hi_in", "印地语"),
    LanguagePreset("ar_sa", "阿拉伯语"),
    LanguagePreset("he_il", "希伯来语"),
    LanguagePreset("fa_ir", "波斯语"),
    LanguagePreset("ca_es", "加泰罗尼亚语"),
    LanguagePreset("eu_es", "巴斯克语"),
    LanguagePreset("gl_es", "加利西亚语"),
    LanguagePreset("af_za", "南非语"),
    LanguagePreset("be_by", "白俄罗斯语"),
    LanguagePreset("kk_kz", "哈萨克语"),
    LanguagePreset("mn_mn", "蒙古语"),
    LanguagePreset("ga_ie", "爱尔兰语"),
    LanguagePreset("is_is", "冰岛语"),
    LanguagePreset("fil_ph", "菲律宾语"),
)


def list_language_preset_labels() -> list[str]:
    return [preset.display_label for preset in LANGUAGE_PRESETS]


def normalize_language_code(value: str | None) -> str:
    normalized_value = (value or "").strip()
    if not normalized_value:
        return ""

    if " | " in normalized_value:
        normalized_value = normalized_value.rsplit(" | ", 1)[-1]

    return normalized_value.replace("-", "_").lower()


def language_choice_from_code(code: str | None) -> str:
    normalized_code = normalize_language_code(code)
    for preset in LANGUAGE_PRESETS:
        if preset.code == normalized_code:
            return preset.display_label
    return normalized_code or ""


def build_language_picker_note(code: str | None) -> str:
    normalized_code = normalize_language_code(code)
    if not normalized_code:
        return "可直接输入自定义语言代码，例如 `fr_fr`、`ru_ru`、`ar_sa`。"

    for preset in LANGUAGE_PRESETS:
        if preset.code == normalized_code:
            return f"当前语言：{preset.label}（{preset.code}）。也可以直接输入自定义语言代码。"

    return f"当前语言代码：{normalized_code}。这不是内置预设，但仍会按自定义语言代码处理。"