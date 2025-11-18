from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QDialog
from loader.utils.helpers import translate as t


class TelegramSettingsDialog(QDialog):
    def __init__(self, parent, config_data):
        super().__init__(parent)
        self.config_data = config_data
        self.t = t
        self.setWindowTitle(self.t("telegram_settings_title"))
        self.setFixedSize(400, 200)
        # Теперь TelegramSettingsDialog использует стили из главного приложения
        self.parent()._load_stylesheet() # Загружаем стили из главного приложения
        self.setStyleSheet(self.parent().styleSheet()) # Применяем стили главного приложения

        layout = QVBoxLayout(self)

        # Bot Token
        token_layout = QHBoxLayout()
        token_layout.addWidget(QLabel(self.t("telegram_bot_token")))
        self.token_input = QtWidgets.QLineEdit(self.config_data.telegram_bot_token)
        self.token_input.setPlaceholderText("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
        token_layout.addWidget(self.token_input)
        layout.addLayout(token_layout)

        # Chat ID
        chat_id_layout = QHBoxLayout()
        chat_id_layout.addWidget(QLabel(self.t("telegram_chat_id")))
        self.chat_id_input = QtWidgets.QLineEdit(self.config_data.telegram_chat_id)
        self.chat_id_input.setPlaceholderText("-1234567890")
        chat_id_layout.addWidget(self.chat_id_input)
        layout.addLayout(chat_id_layout)

        # Notification settings
        self.chk_telegram_target_time = QtWidgets.QCheckBox(self.t("notify_telegram_target_time")) # Добавляем флажок
        self.chk_telegram_target_time.setChecked(self.config_data.notify_events.get("telegram_target_time", False))
        layout.addWidget(self.chk_telegram_target_time)

        self.chk_telegram_offline = QtWidgets.QCheckBox(self.t("notify_telegram_offline")) # Добавляем флажок
        self.chk_telegram_offline.setChecked(self.config_data.notify_events.get("telegram_offline", False))
        layout.addWidget(self.chk_telegram_offline)

        self.chk_telegram_error = QtWidgets.QCheckBox(self.t("notify_telegram_error")) # Добавляем флажок
        self.chk_telegram_error.setChecked(self.config_data.notify_events.get("telegram_error", False))
        layout.addWidget(self.chk_telegram_error)

        # Hint for chat ID
        hint_label = QLabel(self.t("telegram_chat_id_hint")) # Новый QLabel для подсказки
        hint_label.setObjectName("TelegramHintLabel") # Устанавливаем objectName для стилей из QSS
        layout.addWidget(hint_label)

        # Buttons
        buttons_layout = QHBoxLayout()
        ok_button = QPushButton(self.t("ok"))
        ok_button.clicked.connect(self.accept)
        buttons_layout.addWidget(ok_button)

        cancel_button = QPushButton(self.t("cancel"))
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)

    def accept(self):
        self.config_data.telegram_bot_token = self.token_input.text()
        self.config_data.telegram_chat_id = self.chat_id_input.text()
        # Сохраняем состояние новых флажков
        self.config_data.notify_events["telegram_target_time"] = self.chk_telegram_target_time.isChecked()
        self.config_data.notify_events["telegram_offline"] = self.chk_telegram_offline.isChecked()
        self.config_data.notify_events["telegram_error"] = self.chk_telegram_error.isChecked()
        self.config_data.save()
        super().accept()
