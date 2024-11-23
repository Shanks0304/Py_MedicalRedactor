from datetime import datetime
import os
import time
import whisper
import numpy as np
import soundfile as sf
from PyQt6.QtCore import QObject, pyqtSignal, QThread

class TranscriptionWorker(QThread):
    result_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    progress = pyqtSignal(str)
    
    def __init__(self, model, audio_data):
        super().__init__()
        self.model = model
        self.audio_data = audio_data
        self.SAMPLE_RATE = 16000  # Need to match TranscriptionService.SAMPLE_RATE
        self.is_running = True
    
    def stop(self):
        self.is_running = False
        self.wait()
    
    # def _save_audio_chunk(self, audio_data: np.ndarray):
    #     try:
    #         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    #         wav_path = f'audio_chunks/{timestamp}.wav'
    #         sf.write(wav_path, audio_data, self.SAMPLE_RATE)
    #     except Exception as e:
    #         self.error_occurred.emit(f"Error saving audio chunk: {e}")

    def run(self):
        try:
            if not self.is_running:
                return
            
            print("Worker thread started")
            # self._save_audio_chunk(self.audio_data)
            
            if len(self.audio_data) < 16000:
                self.error_occurred.emit("Audio chunk too short")
                return

            self.progress.emit("Processing audio...")
            print(f"Processing audio chunk of length {len(self.audio_data)}")
            
            # Add more debug info
            print(f"Audio data type: {type(self.audio_data)}")
            print(f"Audio data shape: {self.audio_data.shape}")
            print(f"Audio data dtype: {self.audio_data.dtype}")
            
            if np.abs(self.audio_data).max() > 1.0:
                self.audio_data = self.audio_data / np.abs(self.audio_data).max()

            print("Starting Whisper transcription...")
            try:
                start_time = time.time()
                # Convert audio data to the format Whisper expects
                audio_float32 = np.array(self.audio_data, dtype=np.float32)
                result = self.model.transcribe(audio_float32, language='en')  # Specify language if needed
                print(f"Whisper transcription took {time.time() - start_time} seconds")
                print("Transcription completed:", result)
                
                if result and "text" in result:
                    text = result["text"].strip()
                    if text:
                        print(f"Emitting result: {text}")
                        self.result_ready.emit(text)
                else:
                    print("No text in result:", result)
            except Exception as whisper_error:
                print(f"Whisper transcription error: {whisper_error}")
                print(f"Error type: {type(whisper_error)}")
                import traceback
                print(traceback.format_exc())
                self.error_occurred.emit(f"Whisper transcription error: {whisper_error}")
            
            print("Worker thread finished")
        except Exception as e:
            print(f"Error in worker thread: {e}")
            print(f"Error type: {type(e)}")
            import traceback
            print(traceback.format_exc())
            self.error_occurred.emit(f"Transcription error: {e}")

class TranscriptionService(QObject):
    transcription_chunk_ready = pyqtSignal(str)
    processing_status = pyqtSignal(bool)
    transcription_complete = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    SAMPLE_RATE = 16000
    MIN_AUDIO_LENGTH = SAMPLE_RATE
    OPTIMAL_CHUNK_DURATION = 6
    
    def __init__(self, model_size="small"):
        super().__init__()
        self.model = whisper.load_model(model_size)
        self.buffer = []
        self.buffer_threshold = self.SAMPLE_RATE * self.OPTIMAL_CHUNK_DURATION
        self.is_processing = False
        self.worker = None
        self.transcription_text = "" # Store complete transcription

        # Keep track of workers to prevent garbage collection
        self.workers = []
        self._ensure_audio_directory()

    def _ensure_audio_directory(self):
        os.makedirs('audio_chunks', exist_ok=True)

    def start_processing(self):
        self.is_processing = True
        self.buffer = []
        self.processing_status.emit(True)

    def stop_processing(self):
        self.is_processing = False
        self._process_final_buffer()

        # Stop all running workers
        for worker in self.workers:
            if worker.isRunning():
                worker.stop()
        self._process_final_buffer()

        # Emit complete transcription after processing stops
        if self.transcription_text:
            self.transcription_complete.emit(self.transcription_text.strip())
        self.transcription_text = ""  # Reset for next recording
        self.processing_status.emit(False)

    def process_audio_chunk(self, audio_data: np.ndarray):
        if not self.is_processing:
            return

        self.buffer.extend(audio_data)
        
        if len(self.buffer) >= self.buffer_threshold:
            self._process_buffer()

    def _process_buffer(self):
        if not self.buffer:
            return

        try:
            audio_data = np.array(self.buffer, dtype=np.float32)
            self.buffer = []

            self.worker = TranscriptionWorker(self.model, audio_data)
            self.worker.result_ready.connect(self._handle_transcription)
            self.worker.error_occurred.connect(self._handle_error)

            # Add debug signals
            self.worker.progress.connect(lambda msg: print(f"Progress: {msg}"))
            self.worker.finished.connect(lambda: self._cleanup_worker(self.worker))
            
            # Keep reference to prevent garbage collection
            self.workers.append(self.worker)
            self.worker.start()

        except Exception as e:
            self.error_occurred.emit(f"Buffer processing error: {e}")

    def process_full_audio(self, audio_data: np.ndarray):
        try:
            worker = TranscriptionWorker(self.model, audio_data)
            worker.result_ready.connect(self.transcription_complete.emit)
            worker.error_occurred.connect(self.error_occurred.emit)
            worker.progress.connect(lambda msg: print(f"Full audio progress: {msg}"))
            
            # Keep reference to prevent garbage collection
            self.workers.append(worker)
            worker.finished.connect(lambda: self._cleanup_worker(worker))
            
            worker.start()
        except Exception as e:
            self.error_occurred.emit(f"Error processing full audio: {e}")

    def _process_final_buffer(self):
        if len(self.buffer) >= self.MIN_AUDIO_LENGTH:
            self._process_buffer()

    def _handle_transcription(self, text: str):
        self.transcription_text += f" {text}"
        self.transcription_chunk_ready.emit(text)

    def _handle_error(self, error_message: str):
        self.error_occurred.emit(error_message)

    def _cleanup_worker(self, worker):
        """Clean up the worker after it's done"""
        if worker in self.workers:
            if worker.isRunning():
                worker.stop()
            worker.deleteLater()
            self.workers.remove(worker)
    
    def __del__(self):
        """Cleanup when the service is destroyed"""
        for worker in self.workers:
            if worker.isRunning():
                worker.stop()
        self.workers.clear()
