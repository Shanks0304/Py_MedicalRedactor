import sys
from PyQt6.QtWidgets import QApplication, QMessageBox
from ui.main_window import MainWindow
from utils.config import setup_logger

def main():

    # Set up logger
    logger = setup_logger(__name__)
    logger.info("Application starting...")

    try:
        # Create QApplication
        app = QApplication(sys.argv)
        
        # Set application metadata
        app.setApplicationName("Medical Notes Redactor")
        app.setOrganizationName("Michael Hospital")
        app.setOrganizationDomain("com.michael.hospital")
        
        # Create and show main window
        main_window = MainWindow()
        main_window.show()
        
        # Start the event loop
        return app.exec()
        
    except Exception as e:
        # Make sure QApplication exists before creating QMessageBox
        if QApplication.instance() is None:
            app = QApplication(sys.argv)
        
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setText(f"Application failed to start: {str(e)}")
        msg.setWindowTitle("Critical Error")
        msg.exec()
        return 1

if __name__ == "__main__":
    sys.exit(main())