import os
import json
from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from loader.utils.helpers import APP_DIR, translate as t


class StatsWindow(QMainWindow):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_app = parent
        self.t = t
        self.setWindowTitle(self.t("stats_title"))
        self.setGeometry(200, 200, 800, 600)
        self.setMinimumSize(700, 500)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        # Теперь StatsWindow использует стили из главного приложения
        self.parent_app._load_stylesheet() # Загружаем стили из главного приложения
        self.setStyleSheet(self.parent_app.styleSheet()) # Применяем стили главного приложения

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Header
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        self.total_time_label = QLabel("")
        self.total_time_label.setObjectName("TotalTimeLabel")
        header_layout.addWidget(self.total_time_label)
        header_layout.addStretch(1)

        btn_open_log = QPushButton(self.t("stats_history_log"))
        btn_open_log.clicked.connect(self._open_session_log)
        btn_open_log.setFixedWidth(200)
        header_layout.addWidget(btn_open_log)
        main_layout.addWidget(header_widget)

        # Table for stream statistics
        self.stats_table = QtWidgets.QTableWidget()
        self.stats_table.setColumnCount(2)
        self.stats_table.setHorizontalHeaderLabels(
            [self.t("col_stream"), self.t("col_total_minutes")]
        )
        self.stats_table.horizontalHeader().setSectionResizeMode(
            0, QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        self.stats_table.horizontalHeader().setSectionResizeMode(
            1, QtWidgets.QHeaderView.ResizeMode.Fixed
        )
        self.stats_table.setColumnWidth(1, 150)
        self.stats_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.stats_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        main_layout.addWidget(self.stats_table)

        self._load_and_display_stats()

    def _load_and_display_stats(self):
        log_file = os.path.join(APP_DIR, "session_log.json")
        if not os.path.exists(log_file):
            self.total_time_label.setText(
                self.t("stats_total_time").format(period=self.t("overall"), time=0)
            )
            return

        with open(log_file, "r", encoding="utf-8") as f:
            log_entries = [json.loads(line) for line in f if line.strip()]

        # Calculate total time for different periods
        total_minutes_overall = 0
        stream_totals = {}

        for entry in log_entries:
            elapsed_seconds = entry.get("elapsed_seconds", 0);
            stream_url = entry.get("stream_url", "Unknown Stream");
            total_minutes_overall += elapsed_seconds // 60;
            stream_totals[stream_url] = stream_totals.get(stream_url, 0) + (
                elapsed_seconds // 60
            );

        self.total_time_label.setText(
            self.t("stats_total_time").format(
                period=self.t("overall"), time=total_minutes_overall
            )
        )

        self.stats_table.setRowCount(len(stream_totals))
        row = 0
        for url, minutes in sorted(
            stream_totals.items(), key=lambda item: item[1], reverse=True
        ):
            self.stats_table.setItem(row, 0, QtWidgets.QTableWidgetItem(url))
            self.stats_table.setItem(row, 1, QtWidgets.QTableWidgetItem(str(minutes)))
            row += 1

        self.stats_table.resizeRowsToContents()

    def _open_session_log(self):
        log_file = os.path.join(APP_DIR, "session_log.json")
        if os.path.exists(log_file):
            QDesktopServices.openUrl(QUrl.fromLocalFile(log_file))
        else:
            QMessageBox.information(self, self.t("warning"), self.t("stats_no_log_file"))
