@echo off
setlocal
cd /d %~dp0

if not exist .venv (
    where py >nul 2>nul
    if %errorlevel%==0 (
        py -3 -m venv .venv
    ) else (
        python -m venv .venv
    )
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller

pyinstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --console ^
  --name MinecraftAITranslator ^
  --collect-all fastapi ^
  --collect-all starlette ^
    --collect-all uvicorn ^
    --collect-all websockets ^
  --collect-all huggingface_hub ^
  --collect-all markdown_it ^
  --collect-all pygments ^
  --collect-all safehttpx ^
    --add-data "mc_ai_translator\web_ui\static;mc_ai_translator\web_ui\static" ^
  --paths . ^
  app.py

echo.
echo Build finished. EXE: dist\MinecraftAITranslator.exe
endlocal