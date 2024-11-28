from datetime import datetime
import os
from pathlib import Path
import sys
import time
import numpy as np
import soundfile as sf
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from utils.config import setup_logger


class TranscriptionWorker(QThread):
    result_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, model, audio_data):
        super().__init__()
        self.model = model
        self.audio_data = audio_data
        self.SAMPLE_RATE = 16000
        self.is_running = True
        
        # Configure torch for optimal performance
        import torch
        if hasattr(torch.backends, 'cuda'):
            torch.backends.cuda.enabled = False

        self.logger = setup_logger(__name__)
    
    def stop(self):
        self.is_running = False
        self.wait()
        self.deleteLater()
    
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
            
            self.logger.info("Individual worker thread started")
            # self._save_audio_chunk(self.audio_data)
            
            if len(self.audio_data) < 16000:
                self.error_occurred.emit("Audio chunk too short")
                return

            self.logger.info(f"Processing audio chunk of length {len(self.audio_data)}")
               
            if np.abs(self.audio_data).max() > 1.0:
                self.audio_data = self.audio_data / np.abs(self.audio_data).max()

            try:
                self.logger.info("Starting Whisper transcription...")
                start_time = time.time()

                # Convert audio data to the format Whisper expects
                audio_float32 = np.array(self.audio_data, dtype=np.float32)
                result = self.model.transcribe(
                    audio_float32,
                    language='en',
                    fp16=False
                )  # Specify language if needed

                self.logger.info(f"Whisper transcription took {time.time() - start_time} seconds")
                self.logger.info("Transcription completed:", result)
                
                if result and "text" in result:
                    text = result["text"].strip()
                    if text:
                        self.logger.info(f"Emitting result: {text}")
                        self.result_ready.emit(text)
                else:
                    self.logger.info("No text in result:", result)
            except Exception as whisper_error:
                self.logger.error(f"Whisper transcription error: {whisper_error}")
                self.error_occurred.emit(f"Whisper transcription error: {whisper_error}")
            
            self.logger.info("Worker thread finished")

            # Clear resources after processing
            del self.audio_data
            self.audio_data = None

        except Exception as e:
            self.logger.error(f"Error in worker thread: {e}")
            self.logger.error(f"Error type: {type(e)}")
            import traceback
            self.logger.debug(traceback.format_exc())
            self.error_occurred.emit(f"Transcription error: {e}")
        finally:
            self.is_running = False
            del self.audio_data
            self.audio_data = None

class TranscriptionService(QObject):
    transcription_chunk_ready = pyqtSignal(str)
    processing_status = pyqtSignal(bool)
    transcription_complete = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    progress_message = pyqtSignal(str)
    
    SAMPLE_RATE = 16000
    MIN_AUDIO_LENGTH = SAMPLE_RATE
    OPTIMAL_CHUNK_DURATION = 6
    
    def __init__(self, model_size="small"):
        super().__init__()

        # Initialize multiprocessing resources at startup
        import multiprocessing
        if sys.platform == 'darwin':
            multiprocessing.set_start_method('fork', force=True)
            os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'
        
        # Pre-initialize torch settings
        import torch
        torch.set_num_threads(1)
        if hasattr(torch.backends, 'cuda'):
            torch.backends.cuda.enabled = False
        
        self.model = None
        self.model_size = model_size
        self.buffer = []
        self.buffer_threshold = self.SAMPLE_RATE * self.OPTIMAL_CHUNK_DURATION
        self.is_processing = False
        self.worker = None
        self.transcription_text = "" # Store complete transcription      

        # Keep track of workers to prevent garbage collection
        self.workers = []
        self._ensure_audio_directory()
        
        self.logger = setup_logger(__name__)
        self.logger.info("AudioService initialized")

    def _load_model(self):
        self.logger.info("Loading Whisper model...")
        self.progress_message.emit("Loading Whisper model...")

        try:
            import whisper
            import torch
            
            # Configure torch
            torch.set_num_threads(1)
            torch.set_num_interop_threads(1)
            
            if getattr(sys, 'frozen', False):
                bundle_dir = os.path.dirname(sys.executable)
                resources_dir = os.path.join(os.path.dirname(bundle_dir), 'Resources')
                model_path = os.path.join(resources_dir, 'resources', 'models')
            else:
                model_path = os.path.join(os.path.dirname(__file__), '..', '..', 'resources', 'models')

            self.model = whisper.load_model(
                name=self.model_size,
                download_root=model_path,
                in_memory=True,
            )
            self.logger.info("Whisper model loaded successfully")
            self.progress_message.emit("Whisper model loaded successfully")
            
        except Exception as e:
            self.error_occurred.emit(f"Failed to load Whisper model: {str(e)}")
            raise
    
    def _unload_model(self):
        """Safely unload Whisper model"""
        if self.model is not None:
            self.logger.info("Unloading Whisper model...")
            self.progress_message.emit("Unloading Whisper model...")
            try:
                del self.model
                self.model = None
                import gc
                gc.collect()
                self.logger.debug("Whisper model unloaded successfully")
                self.progress_message.emit("Whisper model unloaded successfully")
            except Exception as e:
                self.logger.error(f"Error unloading Whisper model: {e}")
    
    def _ensure_audio_directory(self):
        chunk_dir = os.path.join(os.path.expanduser('~/Documents'), 'medicalapp', 'audio_chunks')
        os.makedirs(chunk_dir, exist_ok=True)

    def start_processing(self):
        """Start streaming process and load model"""
        try:
            self._load_model()  # Load model once at start
            self.is_processing = True
            self.buffer = []
            self.processing_status.emit(True)
        except Exception as e:
            self.error_occurred.emit(f"Failed to start processing: {str(e)}")
            self.is_processing = False

    def stop_processing(self):
        """Stop processing and cleanup resources"""
        try:
            self.is_processing = False
            self._process_final_buffer()

            # Clean up workers
            for worker in self.workers[:]:
                try:
                    if worker.isRunning():
                        worker.stop()
                        worker.wait()
                    worker.deleteLater()
                    self.workers.remove(worker)
                except Exception as e:
                    self.logger.error(f"Error cleaning up worker: {e}")
            
            self.workers.clear()
            
            # Emit complete transcription
            if self.transcription_text:
                self.transcription_complete.emit(self.transcription_text.strip())
                self.transcription_text = ""

            # Unload model after all processing is complete
            self._unload_model()
            self.processing_status.emit(False)
            
        except Exception as e:
            self.error_occurred.emit(f"Error stopping processing: {str(e)}")

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
            self.worker.finished.connect(lambda: self._cleanup_worker(self.worker))
            
            # Keep reference to prevent garbage collection
            self.workers.append(self.worker)
            self.worker.start()
            self.progress_message.emit('Start stream processing...')
        except Exception as e:
            self.error_occurred.emit(f"Buffer processing error: {e}")

    def process_full_audio(self, audio_data: np.ndarray):
        self.progress_message.emit('Start full audio processing...')
        try:
            self._load_model()

            worker = TranscriptionWorker(self.model, audio_data)
            worker.result_ready.connect(self.transcription_complete.emit)
            worker.error_occurred.connect(self.error_occurred.emit)
            
            # Keep reference to prevent garbage collection
            self.workers.append(worker)
            worker.finished.connect(lambda: self._cleanup_worker(worker))
            
            worker.start()
            self.logger.info("Thread is started")
            self.progress_message.emit("Thread is started")
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
        try:
            if worker in self.workers:
                if worker.isRunning():
                    worker.stop()
                    worker.wait(2000)  # Wait for thread to finish
                    if worker.isRunning():
                        worker.terminate()
                worker.deleteLater()
                self.workers.remove(worker)
            
            # Clean up multiprocessing resources
            try:
                from multiprocessing import resource_tracker
                resource_tracker._resource_tracker = None  # Reset the resource tracker
            except:
                pass
            
            # If this was the last worker and we're not streaming, unload the model
            if not self.workers and not self.is_processing:
                self.logger.debug("No active workers, unloading model...")
                self.progress_message.emit("No active workers, unloading model...")
                self._unload_model()
        except Exception as e:
            self.logger.error(f"Error cleaning up worker: {e}")

    def __del__(self):
        """Ensure proper cleanup on deletion"""
        try:
            # Stop all workers
            for worker in self.workers[:]:
                try:
                    if worker.isRunning():
                        worker.stop()
                        worker.wait()
                    worker.deleteLater()
                except:
                    pass
            self.workers.clear()
            
            # Unload model
            with self.model_lock:
                if self.model is not None:
                    self._unload_model()
        except:
            pass