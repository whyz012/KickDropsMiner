import sys
import subprocess

from PyQt6.QtWidgets import QApplication

from loader.utils.helpers import translate as t
from loader.ui.app import App

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec())