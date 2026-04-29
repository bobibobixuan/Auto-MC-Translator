# Auto MC Translator

[中文](README.md) | [English](README.en-US.md) | [日本語](README.ja-JP.md) | [한국어](README.ko-KR.md) | [Español](README.es-ES.md)

Auto MC Translator は、Minecraft の MOD や MOD パック向けのローカル AI 翻訳ツールです。MOD の JAR、ZIP、リソースパック、`mods` フォルダーなどに含まれる `assets/<namespace>/lang/` の言語ファイルを検出し、指定した言語へ翻訳した上で、ゲーム内でそのまま有効化できる上書き型リソースパックを生成します。

## このプロジェクトの目的

このツールは元の MOD ファイルを直接書き換えるためのものではなく、安全に繰り返し利用できる翻訳ワークベンチとして設計されています。

- 単一 MOD のテスト翻訳
- フォルダー単位の一括翻訳
- リアルタイムの API 呼び出しログ表示
- MOD ごとの翻訳件数サマリー表示
- 元ファイルを汚さず、別リソースパックとして出力
- OpenAI 互換 API とローカル互換エンドポイントに対応

## 主な機能

- `単一 MOD 翻訳` と `フォルダー全体翻訳` の 2 モード
- `.jar`、`.zip`、`mods`、`resourcepacks`、MOD パックのルート、展開済みフォルダーを走査
- JSON 形式の lang ファイルと旧 `.lang` 形式をサポート
- スキャン、バッチ送信、再試行、書き込み、完了サマリーをリアルタイム表示
- どの MOD が何件翻訳されたかをログで確認可能
- モデルが key を欠落させた場合、自動で小分け再試行
- 出力は入力パスと同階層に自動生成
- よく使う OpenAI 互換サービスのプリセットを内蔵
- Windows 用ローカル起動と EXE パッケージ化に対応

## 想定される利用シーン

- まず 1 つの MOD だけ品質確認したい
- 既存翻訳の不足分だけ埋めたい
- `mods` フォルダー全体を一括翻訳したい
- 他の人にも配布できる EXE を作りたい

## 対応入力

- 単一 `.jar` / `.zip` ファイル
- `mods` ディレクトリ全体
- `resourcepacks` ディレクトリ全体
- MOD パックのルートフォルダー
- 展開済みアセットフォルダー

## クイックスタート

### 1. 必要環境

- 主対象は Windows
- Python 3.11 以上推奨
- OpenAI 互換モデルの API Key、または Ollama / LM Studio などのローカル互換エンドポイント

### 2. API 設定

`.env.example` を `.env` にコピーし、以下のように設定します。

```env
OPENAI_PROVIDER=deepseek
OPENAI_API_KEY=your-key
OPENAI_MODEL=deepseek-v4-flash
OPENAI_BASE_URL=
```

通常、`OPENAI_BASE_URL` は空のままで問題ありません。独自エンドポイントや地域別エンドポイント、カスタムポートを使う場合だけ変更してください。

### 3. ローカル起動

`launch.bat` をダブルクリックします。

実行内容:

1. `.venv` を作成
2. 依存関係をインストール
3. ローカル Web UI を起動

### 4. Web UI の使い方

#### 翻訳モード

- `単個模组翻译` 相当: 単一 MOD ファイルを翻訳
- `整个目录翻译` 相当: `mods` や `resourcepacks` 全体を翻訳

#### 翻訳戦略

- `完全翻译整个语言包`: すべてのソースエントリを翻訳
- `只补全缺失项`: 既存ターゲット言語にない key だけ翻訳

#### 実行中に見える内容

- 入力パスと出力先プレビュー
- 検出された言語アセット数
- バッチごとの送信状況
- 現在処理中の MOD
- MOD ごとの累積翻訳件数
- 全 MOD 完了後のサマリー

## 出力仕様

元の MOD を変更せず、入力パスと同じ階層に以下を出力します。

- リソースパックフォルダー
- 同名 ZIP

例:

```text
C:\Minecraft\mods\farmers-delight-ai-translation-20260429-223239
C:\Minecraft\mods\farmers-delight-ai-translation-20260429-223239.zip
```

生成物を Minecraft のリソースパックフォルダーへ入れて有効化してください。

## ログ表示の例

```text
Mod total | FarmersDelight-1.20.1-1.2.8.jar | translated=289 | queued=289 | assets=1
Mod translation summary:
- FarmersDelight-1.20.1-1.2.8.jar | translated=289 | queued=289 | source=289 | existing_target=0 | assets=1
```

フォルダー全体翻訳では、各 MOD が個別に一覧表示されます。

## 内蔵プロバイダープリセット

- DeepSeek
- OpenAI
- OpenRouter
- Groq
- DashScope
- Ollama
- LM Studio
- Custom

## Windows EXE のビルド

`build_exe.bat` を実行してください。

内容:

1. `.venv` 作成または再利用
2. 依存関係と `pyinstaller` のインストール
3. 単一 EXE の生成

出力先:

```text
dist/MinecraftAITranslator.exe
```

## プロジェクト構成

```text
mc_ai_translator/
  llm_client.py
  pipeline.py
  providers.py
  scanner.py
  ui.py
app.py
launch.bat
build_exe.bat
```

## よくある質問

### なぜ元の MOD を直接書き換えないのですか？

JAR を直接編集すると管理が難しく、アップデート時にも壊れやすいためです。リソースパック上書きの方が安全です。

### なぜ再試行が発生するのですか？

一部モデルは key を欠落させたり、不完全な JSON を返したりするためです。現在は自動で小バッチに分割して再試行します。

## セキュリティ注意

- 実際の `.env` はコミットしないでください
- テスト用 API Key やローカルメモをコミットしないでください
- Push 前に `git status` を確認してください

## 今後の予定

- 用語集 / 翻訳メモリ
- KubeJS / FTB Quests / Patchouli 対応
- キャッシュ
- 中断再開

## ライセンス

詳細は `LICENSE` を参照してください。