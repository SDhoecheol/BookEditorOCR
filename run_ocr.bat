@echo off
chcp 65001 > nul
cd /d "%~dp0"
echo ===================================================
echo   BookEditor OCR 실행 중...
echo   단축키: F4 (영역 캡처)
echo ===================================================
python app.py
