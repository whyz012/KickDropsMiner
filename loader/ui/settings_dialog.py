from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QFileDialog, QCheckBox, QLabel, QDialogButtonBox, QMessageBox
from PyQt6.QtGui import QIntValidator # Импортируем QIntValidator
from loader.utils.helpers import translate as t
from loader.core.cookie_manager import CookieManager # Импортируем CookieManager
import asyncio # Импортируем asyncio
import threading # Импортируем threading
from PyQt6.QtCore import QMetaObject, Q_ARG, Qt # Импортируем QMetaObject, Q_ARG, Qt
from PyQt6.QtWidgets import QMessageBox # Импортируем QMessageBox
from PyQt6.QtWidgets import QTextEdit # Импортируем QTextEdit напрямую


class SettingsDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle(t("settings_title"))
        self.setGeometry(100, 100, 500, 600) # Увеличиваем размер окна

        self.main_layout = QVBoxLayout()
        self.form_layout = QFormLayout()

        # Chromedriver Path
        self.chromedriver_path_label = QLabel(t("settings_chromedriver_path"))
        self.chromedriver_path_input = QLineEdit(self.config.chromedriver_path if self.config.chromedriver_path else "")
        self.chromedriver_path_button = QPushButton(t("settings_browse"))
        self.chromedriver_path_button.clicked.connect(self._browse_chromedriver_path)
        self.form_layout.addRow(self.chromedriver_path_label, self.chromedriver_path_input)
        self.form_layout.addRow("", self.chromedriver_path_button)

        # Extension Path
        self.extension_path_label = QLabel(t("settings_extension_path"))
        self.extension_path_input = QLineEdit(self.config.extension_path if self.config.extension_path else "")
        self.extension_path_button = QPushButton(t("settings_browse"))
        self.extension_path_button.clicked.connect(self._browse_extension_path)
        self.form_layout.addRow(self.extension_path_label, self.extension_path_input)
        self.form_layout.addRow("", self.extension_path_button)

        # Player settings
        self.hide_player_checkbox = QCheckBox(t("settings_hide_player"))
        self.hide_player_checkbox.setChecked(self.config.hide_player)
        self.mute_checkbox = QCheckBox(t("settings_mute_player"))
        self.mute_checkbox.setChecked(self.config.mute)
        self.mini_player_checkbox = QCheckBox(t("settings_mini_player"))
        self.mini_player_checkbox.setChecked(self.config.mini_player)
        
        self.form_layout.addRow(self.hide_player_checkbox)
        self.form_layout.addRow(self.mute_checkbox)
        self.form_layout.addRow(self.mini_player_checkbox)

        # Default Drop Minutes
        self.default_drop_minutes_label = QLabel(t("settings_default_drop_minutes"))
        self.default_drop_minutes_input = QLineEdit(str(self.config.default_drop_minutes))
        self.default_drop_minutes_input.setValidator(QIntValidator(0, 999999, self)) # Добавляем валидатор для целых чисел
        self.form_layout.addRow(self.default_drop_minutes_label, self.default_drop_minutes_input)

        # Telegram Creator Link
        self.telegram_creator_link_label = QLabel(t("settings_telegram_creator_link"))
        self.telegram_creator_link_input = QLineEdit(self.config.telegram_creator_link)
        self.form_layout.addRow(self.telegram_creator_link_label, self.telegram_creator_link_input)

        # Куки-менеджмент
        self.cookies_label = QLabel(t("connect_title")) # Используем существующий перевод
        self.import_cookies_button = QPushButton(t("select_cookie_file_title"))
        self.import_cookies_button.clicked.connect(self._import_cookies_from_file_thread)
        self.form_layout.addRow(self.cookies_label, self.import_cookies_button)

        # Manual Cookie Input
        self.cookie_input_label = QLabel(t("settings_cookie_input_label"))
        self.cookie_input_textedit = QTextEdit() # Используем QTextEdit напрямую
        self.cookie_input_textedit.setPlaceholderText('''[
  {
    "name": "cookie_name",
    "value": "cookie_value",
    "domain": "kick.com",
    "path": "/",
    "expires": 1678886400,
    "httpOnly": true,
    "secure": true,
    "sameSite": "Lax"
  }
]''')
        self.cookie_input_textedit.setFixedHeight(150)
        self.save_cookies_button = QPushButton(t("settings_save_cookies_button"))
        self.save_cookies_button.clicked.connect(self._save_cookies_from_input_thread)
        self.form_layout.addRow(self.cookie_input_label)
        self.form_layout.addRow(self.cookie_input_textedit)
        self.form_layout.addRow(self.save_cookies_button)

        # Check Cookies Button
        self.check_cookies_button = QPushButton(t("settings_check_cookies_button"))
        self.check_cookies_button.clicked.connect(self._check_cookies_thread)
        self.form_layout.addRow(self.check_cookies_button)

        self.main_layout.addLayout(self.form_layout)

        # Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.main_layout.addWidget(self.button_box)

        self.setLayout(self.main_layout)

    def _browse_chromedriver_path(self):
        path, _ = QFileDialog.getOpenFileName(self, t("settings_select_chromedriver"), "", t("executables_filter") + " (chromedriver.exe);;" + t("all_files_filter") + " (*.*)")
        if path:
            self.chromedriver_path_input.setText(path)

    def _browse_extension_path(self):
        path, _ = QFileDialog.getOpenFileName(self, t("settings_select_extension"), "", "CRX (*.crx);;" + t("all_files_filter") + " (*.*)")
        if path:
            self.extension_path_input.setText(path)

    def _import_cookies_from_file_thread(self):
        """Запускает диалог выбора файла в основном потоке, а импорт куки - в отдельном потоке."""
        options = QFileDialog.Option.DontUseNativeDialog
        file_path, _ = QFileDialog.getOpenFileName(self.parent(), t("select_cookie_file_title"), "", "JSON Files (*.json);;Text Files (*.txt);;All Files (*)", options=options)
        if file_path:
            threading.Thread(target=lambda: asyncio.run(self._import_cookies_async(file_path)), daemon=True).start()
        else:
            QMetaObject.invokeMethod(self.parent(), "_show_info_message_slot", 
                                    Qt.ConnectionType.QueuedConnection, 
                                    Q_ARG(str, t("warning")),
                                    Q_ARG(str, t("cookie_import_failed_or_cancelled")))

    async def _import_cookies_async(self, file_path: str):
        domain = "kick.com"
        success = await CookieManager.import_from_file(file_path, domain)
        if success:
            QMetaObject.invokeMethod(self.parent(), "_show_info_message_slot", 
                                    Qt.ConnectionType.QueuedConnection, 
                                    Q_ARG(str, t("ok")),
                                    Q_ARG(str, t("cookies_saved_for").format(domain=domain)),
                                    Q_ARG(QMessageBox.StandardButton, QMessageBox.StandardButton.Ok))
        else:
            QMetaObject.invokeMethod(self.parent(), "_show_critical_message_slot", 
                                    Qt.ConnectionType.QueuedConnection, 
                                    Q_ARG(str, t("error")),
                                    Q_ARG(str, t("cookie_import_failed_or_cancelled")))

    def _save_cookies_from_input_thread(self):
        """Запускает сохранение куки из текстового поля в отдельном потоке."""
        threading.Thread(target=lambda: asyncio.run(self._save_cookies_from_input_async()), daemon=True).start()

    async def _save_cookies_from_input_async(self):
        cookie_json_string = self.cookie_input_textedit.toPlainText().strip()
        if not cookie_json_string:
            QMetaObject.invokeMethod(self.parent(), "_show_info_message_slot",
                                    Qt.ConnectionType.QueuedConnection,
                                    Q_ARG(str, t("warning")),
                                    Q_ARG(str, t("cookie_import_failed_or_cancelled")))
            return
        domain = "kick.com"
        success = await CookieManager.import_from_string(cookie_json_string, domain)

        if success:
            QMetaObject.invokeMethod(self.parent(), "_show_info_message_slot",
                                    Qt.ConnectionType.QueuedConnection,
                                    Q_ARG(str, t("ok")),
                                    Q_ARG(str, t("cookie_input_success")),
                                    Q_ARG(QMessageBox.StandardButton, QMessageBox.StandardButton.Ok))
            self.cookie_input_textedit.clear() # Очищаем поле после успешного сохранения
        else:
            QMetaObject.invokeMethod(self.parent(), "_show_critical_message_slot",
                                    Qt.ConnectionType.QueuedConnection,
                                    Q_ARG(str, t("error")),
                                    Q_ARG(str, t("cookie_input_error")))

    def _check_cookies_thread(self):
        """Запускает проверку куки в отдельном потоке."""
        threading.Thread(target=lambda: asyncio.run(self._check_cookies_async()), daemon=True).start()

    async def _check_cookies_async(self):
        domain = "kick.com"
        has_cookies = await CookieManager.check_cookies(domain)

        if has_cookies:
            QMetaObject.invokeMethod(self.parent(), "_show_info_message_slot",
                                    Qt.ConnectionType.QueuedConnection,
                                    Q_ARG(str, t("ok")),
                                    Q_ARG(str, t("cookies_found").format(domain=domain)),
                                    Q_ARG(QMessageBox.StandardButton, QMessageBox.StandardButton.Ok))
        else:
            QMetaObject.invokeMethod(self.parent(), "_show_info_message_slot",
                                    Qt.ConnectionType.QueuedConnection,
                                    Q_ARG(str, t("warning")),
                                    Q_ARG(str, t("cookies_not_found").format(domain=domain)),
                                    Q_ARG(QMessageBox.StandardButton, QMessageBox.StandardButton.Ok))


    def accept(self):
        self.config.chromedriver_path = self.chromedriver_path_input.text()
        self.config.extension_path = self.extension_path_input.text()
        self.config.hide_player = self.hide_player_checkbox.isChecked()
        self.config.mute = self.mute_checkbox.isChecked()
        self.config.mini_player = self.mini_player_checkbox.isChecked()
        
        # Валидация для default_drop_minutes
        try:
            minutes = int(self.default_drop_minutes_input.text())
            if not (0 <= minutes <= 999999):
                raise ValueError("Invalid minutes value")
            self.config.default_drop_minutes = minutes
        except ValueError:
            QMessageBox.warning(self, t("warning"), t("invalid_minutes_value"))
            return # Отменяем закрытие диалога, если значение неверно

        # Сохраняем ссылку на Telegram создателя
        self.config.telegram_creator_link = self.telegram_creator_link_input.text()

        self.config.save()
        super().accept()
