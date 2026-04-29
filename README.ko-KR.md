# Auto MC Translator

[中文](README.md) | [English](README.en-US.md) | [日本語](README.ja-JP.md) | [한국어](README.ko-KR.md) | [Español](README.es-ES.md)

Auto MC Translator는 Minecraft 모드와 모드팩을 위한 로컬 AI 번역 도구입니다. 모드 JAR, ZIP, 리소스팩 또는 전체 `mods` 폴더 안의 `assets/<namespace>/lang/` 언어 파일을 찾아 대상 언어로 번역하고, 게임에서 바로 사용할 수 있는 오버라이드 리소스팩을 생성합니다.

## 프로젝트 목적

이 프로젝트는 원본 모드를 직접 수정하는 도구가 아니라, 안전하고 반복 가능한 번역 작업 환경을 제공하는 것을 목표로 합니다.

- 단일 모드 번역 테스트
- 폴더 단위 일괄 번역
- 실시간 API 호출 로그 표시
- 모드별 번역 개수 요약 제공
- 원본 파일을 건드리지 않고 별도 리소스팩 생성
- OpenAI 호환 API 및 로컬 호환 엔드포인트 지원

## 주요 기능

- 단일 모드 번역 / 전체 폴더 번역 두 가지 워크플로
- `.jar`, `.zip`, `mods`, `resourcepacks`, 모드팩 루트, 압축 해제된 에셋 폴더 스캔
- JSON lang 파일과 구형 `.lang` 파일 지원
- 스캔, 배치 요청, 재시도, 파일 기록, 최종 요약 로그를 실시간 표시
- 어떤 모드가 몇 개 번역되었는지 로그에 표시
- 모델이 key를 누락하면 자동으로 더 작은 배치로 재시도
- 출력은 입력 경로와 같은 위치에 자동 생성
- 자주 쓰는 OpenAI 호환 서비스 프리셋 내장
- Windows 로컬 실행과 EXE 패키징 지원

## 사용하기 좋은 상황

- 전체 모드팩 전에 모드 하나만 먼저 시험하고 싶을 때
- 기존 번역에서 빠진 항목만 채우고 싶을 때
- 전체 `mods` 폴더를 한 번에 번역하고 싶을 때
- 다른 사용자에게 배포 가능한 EXE가 필요할 때

## 지원 입력

- 단일 `.jar` / `.zip` 파일
- 전체 `mods` 폴더
- 전체 `resourcepacks` 폴더
- 모드팩 루트 폴더
- 압축 해제된 에셋 폴더

## 빠른 시작

### 1. 요구 사항

- 주 대상 환경은 Windows
- Python 3.11 이상 권장
- OpenAI 호환 모델용 API Key 또는 Ollama / LM Studio 같은 로컬 호환 엔드포인트

### 2. API 설정

`.env.example`을 `.env`로 복사하고 다음과 같이 설정합니다.

```env
OPENAI_PROVIDER=deepseek
OPENAI_API_KEY=your-key
OPENAI_MODEL=deepseek-v4-flash
OPENAI_BASE_URL=
```

대부분의 경우 `OPENAI_BASE_URL`은 비워 두면 됩니다. 커스텀 엔드포인트나 비표준 포트를 사용할 때만 변경하세요.

### 3. 로컬 실행

`launch.bat`를 더블 클릭하세요.

실행 과정:

1. `.venv` 생성
2. 의존성 설치
3. 로컬 웹 UI 실행

### 4. 웹 UI 사용 방법

#### 번역 모드

- 단일 모드 번역: 하나의 `.jar` 또는 `.zip` 처리
- 전체 폴더 번역: `mods`, `resourcepacks`, 모드팩 루트 처리

#### 번역 전략

- 전체 언어팩 완전 번역
- 누락된 항목만 보완

#### 실행 중 표시 정보

- 입력 경로와 출력 미리보기
- 발견된 언어 에셋 수
- 배치별 요청 진행 상황
- 현재 처리 중인 모드
- 모드별 누적 번역 수
- 전체 완료 후 모드별 요약

## 출력 동작

도구는 원본 모드를 수정하지 않습니다. 대신 입력 경로와 같은 위치에 아래 결과를 생성합니다.

- 리소스팩 폴더
- 동일한 이름의 ZIP 파일

예시:

```text
C:\Minecraft\mods\farmers-delight-ai-translation-20260429-223239
C:\Minecraft\mods\farmers-delight-ai-translation-20260429-223239.zip
```

생성된 폴더나 ZIP을 Minecraft 리소스팩 폴더에 넣어 사용하세요.

## 로그 예시

```text
Mod total | FarmersDelight-1.20.1-1.2.8.jar | translated=289 | queued=289 | assets=1
Mod translation summary:
- FarmersDelight-1.20.1-1.2.8.jar | translated=289 | queued=289 | source=289 | existing_target=0 | assets=1
```

전체 폴더 번역 시에는 각 모드가 따로 요약됩니다.

## 내장 프로바이더 프리셋

- DeepSeek
- OpenAI
- OpenRouter
- Groq
- DashScope
- Ollama
- LM Studio
- Custom

## Windows EXE 빌드

`build_exe.bat`를 실행하면 됩니다.

동작 내용:

1. `.venv` 생성 또는 재사용
2. 의존성 및 `pyinstaller` 설치
3. 단일 EXE 생성

출력 위치:

```text
dist/MinecraftAITranslator.exe
```

## 프로젝트 구조

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

## 자주 묻는 질문

### 왜 원본 모드를 직접 수정하지 않나요?

JAR를 직접 수정하면 관리가 어렵고 업데이트 시 문제가 생기기 쉽습니다. 리소스팩 오버라이드 방식이 더 안전합니다.

### 왜 재시도가 발생하나요?

일부 모델은 key를 누락하거나 불완전한 JSON을 반환합니다. 현재는 실패한 배치를 자동으로 더 작은 단위로 재시도합니다.

## 보안 참고

- 실제 `.env`는 커밋하지 마세요
- 테스트용 API Key나 개인 메모를 커밋하지 마세요
- Push 전에 `git status`를 꼭 확인하세요

## 로드맵

- 용어집 / 번역 메모리
- KubeJS / FTB Quests / Patchouli 지원
- 번역 캐시
- 이어서 실행 기능

## 라이선스

자세한 내용은 `LICENSE` 파일을 참고하세요.