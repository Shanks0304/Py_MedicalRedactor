from PyInstaller.building.api import EXE, PYZ, COLLECT
from PyInstaller.building.build_main import Analysis
import os
import whisper

block_cipher = None

# Get the whisper package location
whisper_path = os.path.dirname(whisper.__file__)

# Specific FFmpeg paths for your Windows system
ffmpeg_path = r"C:\ffmpeg-7.0.1-essentials_build\bin\ffmpeg.exe"
ffprobe_path = r"C:\ffmpeg-7.0.1-essentials_build\bin\ffprobe.exe"

# Verify ffmpeg exists
if not (os.path.exists(ffmpeg_path) and os.path.exists(ffprobe_path)):
    raise Exception("ffmpeg/ffprobe not found. Please check the paths are correct.")

a = Analysis(
    ['src/main.py'],
    pathex=[os.path.abspath(os.getcwd())],
    binaries=[
        (ffmpeg_path, '.'),
        (ffprobe_path, '.'),
    ],
    datas=[
        ('.env', '.'),  # Include .env file
        ('resources/icons', 'resources/icons'),
        ('resources/scripts', 'resources/scripts'),
        ('resources/models', 'resources/models'),
        ('src/ui', 'ui'),
        ('src/services', 'services'),
        ('src/utils', 'utils'),
        (whisper_path, 'whisper'),
        (os.path.join(whisper_path, 'assets'), 'whisper/assets'),
    ],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'ui',
        'ui.main_window',
        'ui.components',
        'ui.components.audio_recorder',
        'ui.components.llm_panel',
        'services',
        'services.llm_service',
        'services.transcription_service',
        'services.audio_service',
        'pyaudio',
        'numpy',
        'pydub',
        'soundfile',
        'whisper',
        'docx',
        'dotenv',
        'langchain_core',
        'langchain_ollama',
        'pydantic',
        'pydantic.deprecated.decorator',
        'win32api',
        'win32con',
        'win32gui',
        'pywin32',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],  # Empty list here
    exclude_binaries=True,  # Important!
    name='Medical Notes Redactor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icons/icon.ico'
)

# Add this COLLECT section
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Medical Notes Redactor'
)