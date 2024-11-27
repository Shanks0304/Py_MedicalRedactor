# app.spec
from PyInstaller.building.api import EXE, PYZ, COLLECT
from PyInstaller.building.build_main import Analysis
import subprocess
import shutil
import os
import whisper
from pathlib import Path

block_cipher = None

# Get the whisper package location
whisper_path = os.path.dirname(whisper.__file__)

def find_ffmpeg_tools():
    # For macOS, try to find ffmpeg and ffprobe in common locations
    common_paths = [
        '/opt/homebrew/bin',
        '/usr/local/bin',
        '/usr/bin',
    ]
    
    ffmpeg_path = None
    ffprobe_path = None
    
    # Try common paths
    for base_path in common_paths:
        possible_ffmpeg = os.path.join(base_path, 'ffmpeg')
        possible_ffprobe = os.path.join(base_path, 'ffprobe')
        
        if os.path.exists(possible_ffmpeg) and not ffmpeg_path:
            ffmpeg_path = possible_ffmpeg
            print(f"Found ffmpeg in: {ffmpeg_path}")
            
        if os.path.exists(possible_ffprobe) and not ffprobe_path:
            ffprobe_path = possible_ffprobe
            print(f"Found ffprobe in: {ffprobe_path}")
            
        if ffmpeg_path and ffprobe_path:
            break
    
    # Check Homebrew Cellar as fallback
    if not (ffmpeg_path and ffprobe_path):
        cellar_path = '/opt/homebrew/Cellar/ffmpeg/'
        if os.path.exists(cellar_path):
            versions = os.listdir(cellar_path)
            if versions:
                latest = sorted(versions)[-1]
                bin_path = os.path.join(cellar_path, latest, 'bin')
                if not ffmpeg_path:
                    possible_ffmpeg = os.path.join(bin_path, 'ffmpeg')
                    if os.path.exists(possible_ffmpeg):
                        ffmpeg_path = possible_ffmpeg
                        print(f"Found ffmpeg in Homebrew cellar: {ffmpeg_path}")
                if not ffprobe_path:
                    possible_ffprobe = os.path.join(bin_path, 'ffprobe')
                    if os.path.exists(possible_ffprobe):
                        ffprobe_path = possible_ffprobe
                        print(f"Found ffprobe in Homebrew cellar: {ffprobe_path}")
    
    if not (ffmpeg_path and ffprobe_path):
        raise Exception("ffmpeg and/or ffprobe not found. Please install ffmpeg first.")
    
    return ffmpeg_path, ffprobe_path

# Get ffmpeg and ffprobe paths
ffmpeg_path, ffprobe_path = find_ffmpeg_tools()

a = Analysis(
    ['src/main.py'],
    pathex=[os.path.abspath(os.getcwd())],
    binaries=[
        (ffmpeg_path, '.'),
        (ffprobe_path, '.'),
    ],
    datas=[
        ('.env', '.'),  # Include .env file
        ('resources/icons', 'resources/icons'),  # Include icons
        ('resources/scripts', 'resources/scripts'),  # Include scripts
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
        'ui.main_window',
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
    [],
    exclude_binaries=True,
    name='Medical Notes Redactor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icons/icon.icns'
)

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


# Add this new section for macOS app bundle
app = BUNDLE(
    coll,
    name='Medical Notes Redactor.app',
    icon='resources/icons/icon.icns',
    bundle_identifier='com.michael.hospital.medicalnotes',  # Change this to your bundle identifier
    info_plist={
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'NSHighResolutionCapable': 'True',
        'LSMinimumSystemVersion': '10.13.0',
        'CFBundleExecutable': 'Medical Notes Redactor',  # Add this
        'CFBundlePackageType': 'APPL',                  # Add this
        'CFBundleName': 'Medical Notes Redactor',
        # Add these environment variables
        'LSEnvironment': {
            'PATH': '@executable_path:@executable_path/../Resources:${PATH}'
        }
    }
)