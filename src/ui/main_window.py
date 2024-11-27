from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt
from .components.audio_recorder import AudioRecorderWidget
from .components.llm_panel import LLMPanel

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Audio Transcription & Analysis Tool")
        self.setMinimumSize(1000, 800)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Initialize components
        self.audio_recorder = AudioRecorderWidget()
        self.llm_panel = LLMPanel()
        
        # Connect signals for both live and recorded transcription
        self.audio_recorder.transcription_chunk_ready.connect(
            self.llm_panel.append_input_text
        )
        self.audio_recorder.transcription_complete.connect(
            self.llm_panel.set_input_text
        )
        self.audio_recorder.transcription_progress_message.connect(
            self.llm_panel.log_message
        )
        # Layout
        layout.addWidget(self.audio_recorder, stretch=1)
        layout.addWidget(self.llm_panel, stretch=2)
        
        self.setup_window_properties()
        
    def setup_window_properties(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: white;
            }
        """)
