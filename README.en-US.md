# Auto MC Translator

[中文](README.md) | [English](README.en-US.md) | [日本語](README.ja-JP.md) | [한국어](README.ko-KR.md) | [Español](README.es-ES.md)

Auto MC Translator is a local AI-assisted translation tool for Minecraft mods and modpacks. It scans language files inside mod JARs, ZIP archives, resource packs, or full `mods` folders, translates entries under `assets/<namespace>/lang/`, and generates an override resource pack that you can enable directly in-game.

## What This Project Is For

This project is designed to be a safe, repeatable translation workbench instead of a destructive “rewrite the original mod files” tool.

- Translate a single mod for quick testing
- Translate a whole folder for batch processing
- Show real-time request and retry logs
- Show per-mod translation summaries in the log
- Output a separate resource pack instead of modifying original files
- Support OpenAI-compatible providers and local compatible endpoints

## Key Features

- Two workflows: single mod and whole folder
- Scans `.jar`, `.zip`, `mods`, `resourcepacks`, modpack roots, and extracted asset folders
- Supports both modern JSON lang files and legacy `.lang` files
- Real-time logs for scanning, batching, retries, file writing, and final summary
- Per-mod summary lines showing which mods were translated and how many entries were produced
- Automatic retry splitting when a model omits keys or a batch fails
- Output is generated next to the selected input path
- Built-in provider presets for common OpenAI-compatible services
- Windows-friendly local launcher and EXE packaging script

## Good Use Cases

- You want to test one mod before translating the entire pack
- You already have partial translations and only want to fill missing keys
- You want to batch translate an entire `mods` folder
- You need a portable Windows EXE for other users

## Supported Inputs

- Single `.jar` or `.zip` mod file
- Full `mods` directory
- Full `resourcepacks` directory
- Modpack root directory
- Extracted asset directory

## Quick Start

### 1. Requirements

- Windows is the primary target environment
- Python 3.11+ recommended
- An API key for an OpenAI-compatible model, or a local compatible endpoint such as Ollama / LM Studio

### 2. Configure the Model

Copy `.env.example` to `.env` and fill in your model settings:

```env
OPENAI_PROVIDER=deepseek
OPENAI_API_KEY=your-key
OPENAI_MODEL=deepseek-v4-flash
OPENAI_BASE_URL=
```

In most cases you do not need to set `OPENAI_BASE_URL` manually unless you are using a custom provider, a non-default regional endpoint, or a local service with a custom port.

### 3. Launch Locally

Double-click `launch.bat`.

It will:

1. Create `.venv`
2. Install dependencies
3. Start the local web UI

### 4. Use the Web UI

#### Translation Mode

- `Single Mod Translation`: pick one `.jar` or `.zip` file
- `Whole Folder Translation`: pick `mods`, `resourcepacks`, or a modpack root

#### Translation Strategy

- `Fully Translate Entire Language Pack`: default mode, translates all source entries
- `Only Fill Missing Entries`: only translates missing keys in the target language

#### Path Selection

- Type a path manually
- Use `Choose Mod File`
- Use `Choose Directory`

#### What You See While Running

- Selected workflow and input path
- Output location preview
- Number of discovered language assets
- Batch-by-batch request progress
- Which mod is currently being processed
- How many entries each mod has translated so far
- A final mod summary after the job is finished

## Output Behavior

The tool never edits the original mod files. Instead, it generates the translated pack next to the selected input path.

Example input:

```text
C:\Minecraft\mods\FarmersDelight.jar
```

Example output:

```text
C:\Minecraft\mods\farmers-delight-ai-translation-20260429-223239
C:\Minecraft\mods\farmers-delight-ai-translation-20260429-223239.zip
```

You can place the generated folder or ZIP into Minecraft's resource pack directory.

## Log Format

The log now includes per-mod summary lines such as:

```text
Mod total | FarmersDelight-1.20.1-1.2.8.jar | translated=289 | queued=289 | assets=1
Mod translation summary:
- FarmersDelight-1.20.1-1.2.8.jar | translated=289 | queued=289 | source=289 | existing_target=0 | assets=1
```

When translating a full folder, the summary lists every processed mod separately.

## Built-in Provider Presets

- DeepSeek: `https://api.deepseek.com`
- OpenAI: `https://api.openai.com/v1`
- OpenRouter: `https://openrouter.ai/api/v1`
- Groq: `https://api.groq.com/openai/v1`
- DashScope: `https://dashscope.aliyuncs.com/compatible-mode/v1`
- Ollama: `http://localhost:11434/v1`
- LM Studio: `http://localhost:1234/v1`
- Custom: any OpenAI-compatible endpoint

## Build a Windows EXE

Use `build_exe.bat`.

It will:

1. Create or reuse `.venv`
2. Install runtime dependencies and `pyinstaller`
3. Build a single-file executable

Output path:

```text
dist/MinecraftAITranslator.exe
```

## Project Structure

```text
mc_ai_translator/
  llm_client.py      # model requests, batching, retry splitting
  pipeline.py        # main workflow, summaries, output generation
  providers.py       # provider presets
  scanner.py         # language asset discovery
  ui.py              # Gradio UI and live log flow
app.py               # application entry point
launch.bat           # local launcher
build_exe.bat        # Windows EXE build script
```

## Troubleshooting

### Why does the tool not modify the original mod?

Because modifying JAR files directly is risky and harder to maintain. Minecraft already supports language overrides through resource packs, so this approach is safer.

### Why is a mod taking a long time?

Common reasons:

- Large language files
- Small batch size
- Slow provider response
- Rate limits on the selected API

### Why do retries happen?

Some models omit keys, return invalid JSON, or fail on larger batches. The tool now retries by splitting failed or incomplete batches into smaller groups.

## Security Notes

- Do not commit your real `.env`
- Do not commit test API keys or local notes
- Check `git status` before pushing

## Roadmap

- Terminology memory
- KubeJS / FTB Quests / Patchouli scanning
- Translation cache
- Resume support
- More export reports

## License

See the repository `LICENSE` file.