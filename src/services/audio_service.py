import io
from PyQt6.QtCore import QObject, pyqtSignal
import pyaudio
import numpy as np
from pathlib import Path
from datetime import datetime
from pydub import AudioSegment
import wave

class AudioService(QObject):
    audio_data_ready = pyqtSignal(np.ndarray)
    recording_saved = pyqtSignal(str)
    file_loaded = pyqtSignal(np.ndarray)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
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
        self.recordings_dir = Path(__file__).parent.parent.parent / 'recordings'
        self.recordings_dir.mkdir(exist_ok=True)

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
            filename = self.recordings_dir / f"recording_{timestamp}.wav"
            
            with wave.open(str(filename), 'wb') as wf:
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
            file_extension = Path(file_path).suffix.lower()
            
            if file_extension == '.wav':
                # Handle WAV files natively
                with wave.open(file_path, 'rb') as wf:
                    # Ensure we're getting the correct sample width
                    sample_width = wf.getsampwidth()
                    audio_data = np.frombuffer(wf.readframes(wf.getnframes()), 
                        dtype=np.int16 if sample_width == 2 else np.int32)
                    # Convert to float32 and normalize to [-1, 1]
                    audio_data = audio_data.astype(np.float32) / (2**(8 * sample_width - 1))
            else:
                # Handle other formats using pydub
                audio = AudioSegment.from_file(file_path)
                # Convert to mono if stereo
                if audio.channels > 1:
                    audio = audio.set_channels(1)
                # Set sample rate to match Whisper's requirements
                audio = audio.set_frame_rate(self.sample_rate)
                # Convert to WAV format in memory
                buffer = io.BytesIO()
                audio.export(buffer, format='wav', parameters=["-ac", "1", "-ar", str(self.sample_rate)])
                buffer.seek(0)
                
                with wave.open(buffer, 'rb') as wf:
                    audio_data = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
                    audio_data = audio_data.astype(np.float32) / 32768.0  # Normalize to [-1, 1]

            # Additional safety checks and normalization
            # Remove any DC offset
            audio_data = audio_data - np.mean(audio_data)
            
            # Ensure no values exceed [-1, 1]
            max_val = np.abs(audio_data).max()
            if max_val > 1.0:
                audio_data = audio_data / max_val
                
            # Replace any potential NaN or inf values with zeros
            audio_data = np.nan_to_num(audio_data, nan=0.0, posinf=0.0, neginf=0.0)
            
            self.file_loaded.emit(audio_data)
            return audio_data
        except Exception as e:
            self.error_occurred.emit(f"Failed to load audio file: {str(e)}")
            return None
