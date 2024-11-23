from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog
from PyQt6.QtCore import pyqtSignal, Qt, QRect
from PyQt6.QtGui import QPainter, QBrush, QColor
from pathlib import Path
from services.audio_service import AudioService
from services.transcription_service import TranscriptionService

class AudioRecorderWidget(QWidget):
    recording_finished = pyqtSignal(str)
    file_selected = pyqtSignal(str)
    transcription_chunk_ready = pyqtSignal(str)  # For live updates
    transcription_complete = pyqtSignal(str)     # For final transcript

    def __init__(self):
        super().__init__()
        self.setup_ui()
        
        self.audio_service = AudioService()
        self.transcription_service = TranscriptionService()
        self.current_file = None
        
        # Connect services
        self.audio_service.audio_data_ready.connect(
            self.transcription_service.process_audio_chunk
        )
        self.transcription_service.transcription_chunk_ready.connect(
            self.handle_transcription
        )
        self.audio_service.recording_saved.connect(
            self.handle_recording_saved
        )
            
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)  # Add consistent spacing between widgets
        
        # Create a styled record button
        self.record_button = RecordButton()
        self.record_button.clicked.connect(self.toggle_recording)
        
        # Style the status label
        self.status_label = QLabel("Ready to record")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 14px;
                margin: 10px 0;
            }
        """)
        
        # Updated file label styling
        self.file_label = QLabel("No file selected")
        self.file_label.setWordWrap(True)
        self.file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.file_label.setStyleSheet("""
            QLabel {
                color: #333;
                font-size: 12px;
                padding: 15px;
                background-color: #f5f5f5;
                border-radius: 4px;
                margin: 5px 0;
                min-width: 200px;
                max-width: 400px;
                min-height: 40px;
            }
        """)
        
        # Style the select file button
        self.select_file_button = QPushButton("Select Existing Recording")
        self.select_file_button.setStyleSheet("""
            QPushButton {
                padding: 10px 20px;
                background-color: #f0f0f0;
                border: none;
                border-radius: 4px;
                color: #333;
                font-size: 13px;
                min-width: 200px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
        """)
        self.select_file_button.clicked.connect(self.select_recording)
        
        # Add widgets to layout with proper spacing
        layout.addStretch(1)
        layout.addWidget(self.record_button, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.file_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.select_file_button, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(1)
        
    def toggle_recording(self):
        if not self.audio_service.recording:
            self.start_recording()
        else:
            self.stop_recording()
            
    def start_recording(self):
        self.recording = True
        self.record_button.set_recording(True)
        self.status_label.setText("Recording and transcribing...")
        self.status_label.setStyleSheet("QLabel { color: #ff4444; }")
        self.transcription_complete.emit("")
        
        self.transcription_service.start_processing()
        self.audio_service.start_recording()
    
    def closeEvent(self, event):
        """Handle cleanup when widget is closed"""
        self.transcription_service.stop_processing()
        super().closeEvent(event)

    def stop_recording(self):
        self.recording = False
        self.record_button.set_recording(False)
        self.status_label.setText("Processing final audio...")
        self.select_file_button.setEnabled(True)
        
        self.transcription_service.stop_processing()
        self.audio_service.stop_recording()
        
    def handle_transcription(self, text: str):
        self.transcription_chunk_ready.emit(text)

    def handle_recording_saved(self, filepath: str):
        self.current_file = filepath
        self.file_label.setText(f"Saved: {Path(filepath).name}")
        self.status_label.setText("Recording saved")
        self.status_label.setStyleSheet("QLabel { color: #28a745; }")
        self.recording_finished.emit(filepath)

    def select_recording(self):
        self.transcription_complete.emit("")

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Recording",
            self.audio_service.get_recordings_dir(),
            "Audio Files (*.wav *.mp3 *.m4a *.aac *.ogg *.flac);;All Files (*.*)"
        )
        
        if file_path:
            self.current_file = file_path
            self.file_label.setText(f"Selected file: {Path(file_path).name}")
            self.file_selected.emit(file_path)

             # Load and process the audio file
        audio_data = self.audio_service.load_audio_file(file_path)
        if audio_data is not None:
            self.file_label.setText(f"Processing: {Path(file_path).name}")
            # Connect the transcription complete signal for this specific process
            self.transcription_service.transcription_complete.connect(
                self._handle_file_transcription
            )
            self.transcription_service.process_full_audio(audio_data)
    
    def _handle_file_transcription(self, text: str):
        # Disconnect after receiving the transcription
        self.transcription_service.transcription_complete.disconnect(
            self._handle_file_transcription
        )
        self.transcription_complete.emit(text)
        
        # Reset UI state
        self.record_button.setEnabled(True)
        self.select_file_button.setEnabled(True)
        self.status_label.setText("File processing complete")




class RecordButton(QPushButton):
    def __init__(self):
        super().__init__()
        self.setFixedSize(80, 80)
        self.is_recording = False
        self.setup_style()
        
    def setup_style(self):
        self.setStyleSheet("""
            QPushButton {
                border-radius: 40px;
                border: 3px solid #ff4444;
                background-color: white;
            }
            QPushButton:hover {
                background-color: #ffeeee;
            }
            QPushButton:pressed {
                background-color: #ffe0e0;
            }
        """)
        
    def set_recording(self, is_recording):
        self.is_recording = is_recording
        if is_recording:
            self.setStyleSheet("""
                QPushButton {
                    border-radius: 40px;
                    border: 3px solid #ff4444;
                    background-color: #ff4444;
                }
                QPushButton:hover {
                    background-color: #ff6666;
                }
                QPushButton:pressed {
                    background-color: #ff8888;
                }
            """)
        else:
            self.setup_style()
        
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if self.is_recording:
            # Draw stop symbol
            painter.fillRect(
                QRect(30, 30, 20, 20),
                QColor("#ffffff")
            )
        else:
            # Draw record symbol
            painter.setBrush(QBrush(QColor("#ff4444")))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(30, 30, 20, 20)
