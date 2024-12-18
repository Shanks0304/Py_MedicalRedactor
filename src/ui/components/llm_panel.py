from PyQt6.QtWidgets import (
    QWidget, 
    QVBoxLayout, 
    QHBoxLayout,
    QPushButton, 
    QLabel, 
    QTextEdit,
    QFileDialog,
    QMessageBox,
    QPlainTextEdit
)
from PyQt6.QtCore import pyqtSignal
from services.llm_service import LLMService
from docx import Document
from docx.shared import Pt
import tempfile
import os


class LLMPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.llm_service = LLMService()
        self.template_content = ""
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Template section
        template_layout = QHBoxLayout()
        self.template_status = QLabel("No template loaded")
        self.template_button = QPushButton("Load Template")
        self.template_button.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: palette(button);
                color: palette(buttonText);
                border: 1px solid palette(mid);
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: palette(light);
            }
        """)
        template_layout.addWidget(self.template_status)
        template_layout.addWidget(self.template_button)
        layout.addLayout(template_layout)
        
        # Input section
        self.input_label = QLabel("Transcription:")
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("Transcription will appear here...")
        self.input_text.setReadOnly(False)
        self.input_text.setStyleSheet("""
            QTextEdit {
                background-color: palette(base);
                color: palette(text);
                border: 1px solid palette(mid);
                border-radius: 4px;
                padding: 8px;
            }
        """)
        layout.addWidget(self.input_label)
        layout.addWidget(self.input_text)
        
        # Process button
        self.process_button = QPushButton("Process with LLM")
        self.process_button.setEnabled(True)  # Enabled when transcription is available
        layout.addWidget(self.process_button)
        
        # Response section
        response_label = QLabel("LLM Response:")
        self.response_text = QTextEdit()
        self.response_text.setReadOnly(True)
        self.response_text.setStyleSheet("""
            QTextEdit {
                background-color: palette(base);
                color: palette(text);
                border: 1px solid palette(mid);
                border-radius: 4px;
                padding: 8px;
            }
        """)
        layout.addWidget(response_label)
        layout.addWidget(self.response_text)
        
        # Add log display section
        log_label = QLabel("Processing Logs:")
        self.log_display = QPlainTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setMaximumHeight(150)  # Limit height
        self.log_display.setStyleSheet("""
            QPlainTextEdit {
                background-color: palette(base);
                color: palette(text);
                border: 1px solid palette(mid);
                border-radius: 4px;
                padding: 8px;
            }
        """)
        layout.addWidget(log_label)
        layout.addWidget(self.log_display)

        # Export button
        self.export_button = QPushButton("Export Response")
        self.export_button.setEnabled(False)  # Enabled when response is available
        layout.addWidget(self.export_button)

    def setup_connections(self):
        # Connect buttons to their respective functions
        self.template_button.clicked.connect(self.load_template)
        self.process_button.clicked.connect(self.process_transcription)
        self.export_button.clicked.connect(self.export_response)
        
        # Connect LLM service signals
        self.llm_service.response_ready.connect(self.handle_llm_response)
        self.llm_service.debug_message.connect(self.log_message)
        self.llm_service.error_occurred.connect(self.handle_error)

    def log_message(self, message: str):
        """Add a new log message to the display"""
        self.log_display.appendPlainText(message)
        # Auto-scroll to bottom
        self.log_display.verticalScrollBar().setValue(
            self.log_display.verticalScrollBar().maximum()
        )
    
    def load_template(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select Template File",
            "",
            "Word Documents (*.docx *.doc);;All Files (*)"  # Updated file filter for Word docs
        )
        
        if file_name:
            try:
                if self.llm_service.set_template(file_name):  # Pass the file path directly
                    self.template_status.setText(f"Template loaded: {file_name.split('/')[-1]}")
                    self.process_button.setEnabled(True)  # Enable process button when template is loaded
                else:
                    self.template_status.setText("Error loading template")
                    self.process_button.setEnabled(False)
            except Exception as e:
                self.handle_error(f"Error loading template: {str(e)}")
                self.process_button.setEnabled(False)
                
    def set_input_text(self, text: str):
        """Set the transcription text - called from outside"""
        self.input_text.setText(text)
        self.process_button.setEnabled(bool(text))
    
    def process_transcription(self):
        transcription = self.input_text.toPlainText()
        if transcription:
            self.llm_service.process_text(transcription)

    def handle_llm_response(self, response: str):
        self.response_text.setText(response)
        self.export_button.setEnabled(True)

    def export_response(self):
        response = self.response_text.toPlainText()
        if response:
            saved_path = self.llm_service.save_response(response)
            if saved_path:
                QMessageBox.information(
                    self,
                    "Success",
                    f"Response saved to:\n{saved_path}"
                )

    def handle_error(self, error: str):
        QMessageBox.critical(
            self,
            "Error",
            error
        )

    def append_input_text(self, text: str):
        """Append new transcription text for live updates"""
        current_text = self.input_text.toPlainText()
        new_text = f"{current_text} {text}".strip()
        self.input_text.setText(new_text)
        self.process_button.setEnabled(bool(new_text))