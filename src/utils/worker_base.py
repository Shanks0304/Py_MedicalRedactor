from PyQt6.QtCore import QRunnable, QObject, pyqtSignal

class WorkerSignals(QObject):
    """Defines the signals available from a running worker thread."""
    finished = pyqtSignal()
    error = pyqtSignal(str)
    result = pyqtSignal(object)
    progress = pyqtSignal(str)

class BaseWorker(QRunnable):
    """Base worker class that implements common functionality"""
    def __init__(self):
        super().__init__()
        self.signals = WorkerSignals()
        self.is_running = True
    
    def stop(self):
        """Stop the worker"""
        self.is_running = False