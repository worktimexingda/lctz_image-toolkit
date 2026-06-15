@echo off
setlocal
cd /d "%~dp0"
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --clean --onefile --windowed --name "lctz_image-toolkit" "lctz_image_toolkit.py"
echo.
echo Build finished: dist\lctz_image-toolkit.exe
pause
