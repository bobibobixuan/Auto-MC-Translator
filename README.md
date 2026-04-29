# Auto MC Translator

[中文](README.md) | [English](README.en-US.md) | [日本語](README.ja-JP.md) | [한국어](README.ko-KR.md) | [Español](README.es-ES.md)

Auto MC Translator 是一个面向 Minecraft 模组整合包的本地 AI 翻译工具。它会扫描模组 JAR、ZIP、资源包目录或整个 `mods` 文件夹中的语言文件，把 `assets/<namespace>/lang/` 下的文本翻译成目标语言，并生成可直接放进游戏使用的覆盖式资源包。

## 项目定位

这个项目不是去修改原模组，也不是一次性把整合包“魔改”掉，而是尽量做成一个安全、可重复、低门槛的本地翻译工作台：

- 支持单个模组测试，也支持整个目录批量翻译
- 实时展示模型调用日志，便于你观察每个批次在做什么
- 在日志里按模组汇总翻译数量，方便判断哪些模组已经处理完
- 默认完整翻译整个语言包，也可以切换到“只补全缺失项”
- 输出新的资源包文件夹和 ZIP，不直接污染原始整合包

## 核心功能

- 单个模组翻译和整个目录翻译两种工作流
- 扫描 `mods`、`resourcepacks`、单个 `.jar` / `.zip`、解压后的资源目录
- 支持现代 JSON 语言文件和旧版 `.lang` 文件
- 实时显示扫描、分批请求、失败重试、写文件和最终汇总日志
- 日志里显示“翻译了哪些模组”和“每个模组分别翻译了多少条”
- 翻译完成后额外显示项目摘要面板，列出模组清单、条数统计和导出路径
- 内建多档翻译 Skill，默认优先使用低 token 的极速模组翻译策略
- 可复用相同原文的翻译结果，减少跨模组重复请求
- 内置完整目标语言检测，已完整翻译的语言文件会直接跳过
- 支持大量常用语言预设，也支持手填自定义语言代码
- 当模型漏掉部分 key 或某批失败时，自动拆小批次重试
- 自动把输出写到程序目录下的 `output/` 文件夹
- 提供小白日志和开发者日志两种视图
- 提供快捷按钮直接打开导出文件夹和翻译报告
- 内置多个 OpenAI 兼容服务商预设，通常只需要填 API Key
- 提供 Windows 本地运行和单文件 EXE 打包流程

## 适合的使用场景

- 你想先拿一个模组做汉化冒烟测试
- 你已经有部分汉化，只想补齐缺失项
- 你想把整个 `mods` 目录批量翻译成 `zh_cn`
- 你想确认某个模型在模组文本上的稳定性和成本
- 你需要一个可分发给别人使用的本地 EXE 工具

## 当前支持的输入

- 单个模组文件：`.jar`、`.zip`
- 整个 `mods` 文件夹
- 整个 `resourcepacks` 文件夹
- 整合包根目录
- 已经解压的资源目录

## 快速开始

### 1. 运行环境

- Windows 为主，项目当前已针对 Windows 启动脚本和 EXE 打包做过适配
- Python 3.11 以上推荐，当前开发环境已在 Python 3.13 下验证
- 需要一个 OpenAI 兼容模型接口的 API Key，或本地兼容接口（如 Ollama / LM Studio）

### 2. 配置 API

复制 `.env.example` 为 `.env`，填入你的模型配置：

```env
OPENAI_PROVIDER=deepseek
OPENAI_API_KEY=你的密钥
OPENAI_MODEL=deepseek-v4-flash
OPENAI_BASE_URL=
```

大部分情况下，`OPENAI_BASE_URL` 不需要手填。只有下面这些情况才需要改：

- 你选择了 `custom`
- 你使用 DashScope 的非默认地域
- 你使用本地 Ollama / LM Studio 且端口或路径不是默认值

### 3. 本地启动

直接双击 `launch.bat`。

脚本会自动完成以下步骤：

1. 创建 `.venv`
2. 安装依赖
3. 启动本地 Web 页面

### 4. 在界面里操作

新版界面默认是小白模式：首页只保留路径、资源包名称、API Key 和开始按钮，其他模型与翻译细节都放进 `高级设置`。

首页现在额外提供 `目标语言` 选择器，常见语言可以直接选，特殊语言代码也可以手填。

#### 翻译方式

- 现在默认 **自动识别输入类型**：
- 选择 `.jar` / `.zip` 时，会按单个模组处理
- 选择目录时，会按整个目录批量处理

#### 语言选择

- 首页可直接选择 `目标语言`
- 内置了大量常用语言预设，例如 `zh_cn`、`ja_jp`、`ko_kr`、`fr_fr`、`de_de`、`ru_ru`、`es_es`、`pt_br` 等
- 如果预设里没有你要的语言，也可以直接输入自定义语言代码
- `源语言` 放在 `高级设置` 里，默认是 `en_us`

#### 翻译策略

- `完整翻译整个语言包`：默认选项，所有源语言条目都会重新翻译
- `只补全缺失项`：只对目标语言中缺失的 key 发起翻译请求

#### 翻译 Skill

- `极速模组翻译 Skill`：默认推荐，提示词最短，适合先追求速度和成本
- `平衡术语 Skill`：兼顾常见社区译法和可读性
- `沉浸润色 Skill`：更偏向表现力，通常更慢，也更耗 token

#### 省 token 的设置建议

- 保持 `复用相同原文翻译结果` 为开启状态
- 大批量翻译时优先用 `极速模组翻译 Skill`
- `额外提示词` 只在确有必要时填写，因为它会随每个批次重复发送给模型
- 如果只是补现有汉化缺口，切换到 `只补全缺失项`

#### 选择路径

- 可以手输路径
- 可以点击 `选择模组文件`
- 可以点击 `选择目录`
- `资源包名称` 可以自定义；如果留空，会按输入名称自动生成，例如 `FarmersDelight-zh_cn`

#### 运行中能看到什么

- 当前输入路径和输出预览
- `小白日志`：只显示扫描、跳过完整翻译、当前处理进度、完成结果等中文摘要
- `开发者日志`：显示扫描细节、批次请求、重试、完整翻译跳过、统计汇总等完整原始日志

#### 完成后能直接做什么

- 查看翻译项目摘要，包括当前项目、模组总数、翻译条数和跳过项
- 查看本次跳过了多少个已经完整翻译的语言文件
- 查看每个模组的已翻译条数、待处理条数、总词条数和语言文件数
- 点击 `快捷打开导出文件夹` 直接查看输出资源包
- 点击 `快捷打开翻译报告` 打开 `translation_report.json`
- 在日志里查看本次优化命中多少重复条目，以及实际发给模型多少条内容

## 输出规则

程序不会修改原始模组，而是自动在 **程序目录下的 `output/` 文件夹** 生成：

- 一个资源包文件夹
- 一个同名 ZIP 文件
- 一个 `translation_report.json` 翻译报告

例如，你翻译：

```text
C:\Minecraft\mods\FarmersDelight.jar
```

那么输出会类似：

```text
C:\path\to\MinecraftAITranslator\output\farmersdelight-zh-cn-20260429-223239
C:\path\to\MinecraftAITranslator\output\farmersdelight-zh-cn-20260429-223239.zip
```

源码运行时，这个目录通常就是项目根目录下的 `output/`；打包成 EXE 后，则是 EXE 同级目录下的 `output/`。

把 ZIP 或目录放到 Minecraft 的资源包目录里启用即可。

## 日志会显示什么

新版日志不仅显示全局总进度，还会显示按模组汇总的结果。例如：

```text
Mod total | FarmersDelight-1.20.1-1.2.8.jar | translated=289 | queued=289 | assets=1
Mod translation summary:
- FarmersDelight-1.20.1-1.2.8.jar | translated=289 | queued=289 | source=289 | existing_target=0 | assets=1
```

如果你翻译整个目录，这个汇总会把每个模组分别列出来。

## 内置服务商预设

- DeepSeek：`https://api.deepseek.com`，默认 `deepseek-v4-flash`
- OpenAI：`https://api.openai.com/v1`，默认 `gpt-5.4-mini`
- OpenRouter：`https://openrouter.ai/api/v1`，默认 `openai/gpt-5.2`
- Groq：`https://api.groq.com/openai/v1`，默认 `openai/gpt-oss-20b`
- DashScope：`https://dashscope.aliyuncs.com/compatible-mode/v1`，默认 `qwen-plus`
- Ollama：`http://localhost:11434/v1`
- LM Studio：`http://localhost:1234/v1`
- Custom：自定义 OpenAI 兼容接口

## 打包 EXE

仓库里自带 `build_exe.bat`。

它会自动：

1. 创建或复用 `.venv`
2. 安装依赖和 `pyinstaller`
3. 重新打包单文件 EXE

默认输出文件：

```text
dist/MinecraftAITranslator.exe
```

## 项目结构

```text
mc_ai_translator/
	llm_client.py      # 模型请求、拆批和失败重试
	pipeline.py        # 翻译主流程、日志汇总、输出生成
	providers.py       # 服务商预设
	scanner.py         # 扫描模组/目录中的语言文件
	ui.py              # Gradio 页面和实时日志交互
app.py               # 入口
launch.bat           # 本地运行脚本
build_exe.bat        # Windows EXE 打包脚本
```

## 常见问题

### 为什么不直接改原模组？

因为直接修改 JAR 风险高，更新整合包时也容易丢改动。资源包覆盖更安全，也更符合 Minecraft 的原生加载方式。

### 为什么某些模组翻得慢？

常见原因包括：

- 模组语言文件很大
- 你设置的 batch size 较小
- 当前模型响应速度慢
- 接口存在速率限制

### 为什么有时候会重试？

因为某些模型可能漏 key、返回不完整 JSON，或者单批请求失败。现在程序会自动拆批重试，优先保证翻译完整性。

### 为什么现在固定输出到 `output/`？

因为现在统一改成了程序目录下的 `output/`，这样源码运行和 EXE 运行的输出位置都固定，更适合小白直接找到结果，也方便快捷打开。

## 安全说明

- 不要把真实 `.env`、测试密钥或个人笔记提交到 Git 仓库
- 本仓库默认忽略 `.env`、构建目录、测试 JAR 和本地说明文件
- 推送前建议再检查一次 `git status`

## 计划中的增强项

- 术语表 / 记忆库
- KubeJS、FTB Quests、Patchouli 文本扫描
- 已翻译缓存
- 断点续翻
- 完整整合包报告导出

## 许可证

本项目沿用仓库中的 `LICENSE` 文件。推送到 GitHub 前请确认许可证与你希望的发布方式一致。
