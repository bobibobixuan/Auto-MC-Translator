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
- 当模型漏掉部分 key 或某批失败时，自动拆小批次重试
- 自动把输出写到输入路径的同级目录
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

#### 翻译方式

- `单个模组翻译`：适合先验证模型质量、术语风格和日志效果
- `整个目录翻译`：适合直接处理整个 `mods`、`resourcepacks` 或整合包目录

#### 翻译策略

- `完整翻译整个语言包`：默认选项，所有源语言条目都会重新翻译
- `只补全缺失项`：只对目标语言中缺失的 key 发起翻译请求

#### 选择路径

- 可以手输路径
- 可以点击 `选择模组文件`
- 可以点击 `选择目录`

#### 运行中能看到什么

- 当前输入路径和输出预览
- 扫描到多少语言资产
- 每一批发出了多少条请求
- 当前在翻哪个模组
- 当前模组累计翻译了多少条
- 所有模组结束后的汇总清单

## 输出规则

程序不会修改原始模组，而是自动在输入路径的同级目录生成：

- 一个资源包文件夹
- 一个同名 ZIP 文件

例如，你翻译：

```text
C:\Minecraft\mods\FarmersDelight.jar
```

那么输出会类似：

```text
C:\Minecraft\mods\farmers-delight-ai-translation-20260429-223239
C:\Minecraft\mods\farmers-delight-ai-translation-20260429-223239.zip
```

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

### 为什么输出路径不是固定 `output/`？

因为现在改成了和输入路径同级输出，方便你处理单个模组或某个指定目录时，直接在附近找到结果。

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
