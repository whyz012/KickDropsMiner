from PyQt6.QtCore import QObject, pyqtSignal


class WorkerSignals(QObject):
    # Signals are compatible with PyQt6
    update = pyqtSignal(int, int, bool)
    finish = pyqtSignal(int, int, bool, str) # Добавлен аргумент для причины завершения
    progress_update = pyqtSignal(int, int, int) # idx, elapsed_seconds, target_seconds
    error = pyqtSignal(str)
