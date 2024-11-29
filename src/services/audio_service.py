import os
import sys
from PyQt6.QtCore import QObject, pyqtSignal
import pyaudio
import numpy as np
from pathlib import Path
from datetime import datetime
from pydub import AudioSegment
import wave
from utils.config import setup_logger
import platform

class AudioService(QObject):
    audio_data_ready = pyqtSignal(np.ndarray)
    recording_saved = pyqtSignal(str)
    file_loaded = pyqtSignal(np.ndarray)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        self.logger = setup_logger(__name__)
        self.logger.info("AudioService initialized")

        # Add this near the start of your __init__
        if getattr(sys, 'frozen', False):
             # Get base directory for the bundled app
            if platform.system() == 'Darwin':  # macOS
                bundle_dir = os.path.dirname(sys.executable)
                resources_dir = os.path.join(os.path.dirname(bundle_dir), 'Resources')
                self.ffmpeg_path = os.path.join(resources_dir, 'ffmpeg')
                self.ffprobe_path = os.path.join(resources_dir, 'ffprobe')
                
                # Make the binaries executable on macOS
                os.chmod(self.ffmpeg_path, 0o755)
                os.chmod(self.ffprobe_path, 0o755)
                
            else:  # Windows
                bundle_dir = os.path.dirname(sys.executable)
                resources_dir = os.path.join(bundle_dir, '_internal')
                self.ffmpeg_path = os.path.join(resources_dir, 'ffmpeg.exe')
                self.ffprobe_path = os.path.join(resources_dir, 'ffprobe.exe')
            
            # Set environment variables for both ffmpeg and ffprobe
            os.environ['PATH'] = f"{resources_dir}{os.pathsep}{os.environ.get('PATH', '')}"
            os.environ['FFMPEG_BINARY'] = self.ffmpeg_path
            os.environ['FFPROBE_BINARY'] = self.ffprobe_path
                       
            self.logger.info(f"Running as bundled app")
            self.logger.info(f"Resources dir: {resources_dir}")
            self.logger.info(f"FFMPEG_BINARY: {os.environ['FFMPEG_BINARY']}")
            self.logger.info(f"FFPROBE_BINARY: {os.environ['FFPROBE_BINARY']}")
            self.logger.info(f"PATH: {os.environ['PATH']}")

            #  Verify the binaries exist and are executable
            if not os.path.exists(self.ffmpeg_path):
                raise Exception(f"ffmpeg not found at {self.ffmpeg_path}")
            if not os.path.exists(self.ffprobe_path):
                raise Exception(f"ffprobe not found at {self.ffprobe_path}")
        
        else:
            # Development environment - use system ffmpeg
            self.ffmpeg_path = 'ffmpeg'
            self.ffprobe_path = 'ffprobe'
            if platform.system() == 'Windows':
                self.ffmpeg_path += '.exe'
                self.ffprobe_path += '.exe'


        self.recording = False
        self.sample_rate = 16000  # Required for Whisper
        self.chunk_size = 1024 * 4  # Adjust for better performance
        self.audio_format = pyaudio.paFloat32
        self.channels = 1
        
        # PyAudio setup
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.frames = []
        
        # Create recordings directory
        self.recordings_dir = os.path.join(os.path.expanduser('~/Documents'), 'medicalapp', 'recordings')
        os.makedirs(self.recordings_dir, exist_ok=True)

    def start_recording(self):
        if not self.recording:
            try:
                self.recording = True
                self.frames = []
                
                self.stream = self.audio.open(
                    format=self.audio_format,
                    channels=self.channels,
                    rate=self.sample_rate,
                    input=True,
                    frames_per_buffer=self.chunk_size,
                    stream_callback=self.audio_callback
                )
                self.stream.start_stream()
            except Exception as e:
                self.error_occurred.emit(f"Failed to start recording: {str(e)}")
                self.recording = False

    def stop_recording(self):
        if self.recording:
            self.recording = False
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            
            # Save the recording
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(self.recordings_dir, f"recording_{timestamp}.wav")
            
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.audio.get_sample_size(self.audio_format))
                wf.setframerate(self.sample_rate)
                wf.writeframes(b''.join(self.frames))
            
            self.recording_saved.emit(str(filename))
            return str(filename)

    def audio_callback(self, in_data, frame_count, time_info, status):
        if self.recording:
            self.frames.append(in_data)
            audio_data = np.frombuffer(in_data, dtype=np.float32)
            self.audio_data_ready.emit(audio_data)
        return (in_data, pyaudio.paContinue)

    def get_recordings_dir(self):
        return str(self.recordings_dir)

    def __del__(self):
        self.audio.terminate()

    def load_audio_file(self, file_path: str):
        try:
            self.logger.info(f"Attempting to load audio file: {file_path}")
            audio_data = None
            file_extension = Path(file_path).suffix.lower()
            self.logger.info(f"File extension: {file_extension}")
            
            if file_extension == '.wav':
                self.logger.debug("Processing WAV file directly")
                # Handle WAV files natively
                with wave.open(file_path, 'rb') as wf:
                    # Ensure we're getting the correct sample width
                    sample_width = wf.getsampwidth()
                    audio_data = np.frombuffer(wf.readframes(wf.getnframes()), 
                        dtype=np.int16 if sample_width == 2 else np.int32)
                    # Convert to float32 and normalize to [-1, 1]
                    audio_data = audio_data.astype(np.float32) / (2**(8 * sample_width - 1))
            else:
                self.logger.debug("Processing WAV file directly")
                # Improve error handling for non-WAV files
                self.error_occurred.emit(f"Converting {file_extension} file to WAV format...")
                
                try:
                    self.logger.debug(f"ffmpeg path: {self.ffmpeg_path}")
                    self.logger.debug(f"ffprobe path: {self.ffprobe_path}")
                    if getattr(sys, 'frozen', False):
                        if not os.path.exists(self.ffmpeg_path):
                            raise Exception(f"ffmpeg not found at {self.ffmpeg_path}")
                        if not os.path.exists(self.ffprobe_path):
                            raise Exception(f"ffmpeg not found at {self.ffprobe_path}")
                        
                        # Update this section to use the new method
                        AudioSegment.converter = self.ffmpeg_path
                        self.logger.debug(f"Set ffmpeg converter path to: {self.ffmpeg_path}")


                    self.logger.debug("Creating AudioSegment")
                    audio = AudioSegment.from_file(file_path)

                    self.logger.debug(f"Original audio: channels={audio.channels}, frame_rate={audio.frame_rate}")
                    
                    if audio.channels > 1:
                        audio = audio.set_channels(1)
                    audio = audio.set_frame_rate(self.sample_rate)
                    
                    # Use a temporary file instead of BytesIO
                    temp_wav = os.path.join(self.recordings_dir, "temp_conversion.wav")
                    self.logger.debug(f"Exporting to temp file: {temp_wav}")
                    
                    audio.export(temp_wav, format='wav', parameters=["-ac", "1", "-ar", str(self.sample_rate)])
                    self.logger.debug("Export completed")
                    
                    with wave.open(temp_wav, 'rb') as wf:
                        audio_data = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
                        audio_data = audio_data.astype(np.float32) / 32768.0
                    # Clean up temporary file
                    os.remove(temp_wav)
                    
                except Exception as e:
                    self.logger.error(f"Audio conversion error: {str(e)}")
                    self.error_occurred.emit(f"Audio conversion error: {str(e)}")
                    return None

            # Additional safety checks and normalization
            # Remove any DC offset
            if audio_data is not None:
                audio_data = audio_data - np.mean(audio_data)
                max_val = np.abs(audio_data).max()
                if max_val > 1.0:
                    audio_data = audio_data / max_val
                audio_data = np.nan_to_num(audio_data, nan=0.0, posinf=0.0, neginf=0.0)
                
                self.file_loaded.emit(audio_data)
                return audio_data
            else:
                self.logger.error("There is no audio file")
                return None
        except Exception as e:
            self.error_occurred.emit(f"Failed to load audio file: {str(e)}")
            self.logger.error(f"Failed to load audio file: {str(e)}", exc_info=True)
            return None
            
