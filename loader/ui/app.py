import sys
import os
import threading
import time
from PyQt6.QtWidgets import QMainWindow, QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QScrollArea, QFrame, QSizePolicy, QSpacerItem, QCheckBox, QMessageBox, QInputDialog, QFileDialog, QLineEdit
from PyQt6.QtCore import Qt, QUrl, QTimer, QMetaObject, pyqtSlot, Q_ARG
from PyQt6.QtGui import QIcon, QDesktopServices, QFont, QFontDatabase
from PyQt6 import QtCore, QtWidgets # Добавляем QtWidgets
import functools # Добавляем импорт functools

import loader.utils.helpers as helpers
from loader.core.notifier import TelegramNotifier
from loader.core.cookie_manager import CookieManager
from loader.core.stream_worker import StreamWorker
from loader.core.config import Config
from loader.ui.stream_card import StreamCard
from loader.ui.drops_window import DropsWindow
from loader.ui.stats_window import StatsWindow
from loader.ui.telegram_settings_dialog import TelegramSettingsDialog
from loader.ui.collapsible_group import CollapsibleGroup # Добавлен импорт для CollapsibleGroup
from loader.ui.settings_dialog import SettingsDialog # Добавлен импорт для SettingsDialog
from loader.core.selenium_driver import make_chrome_driver # Импортируем make_chrome_driver
from loader.core.paths import APP_DIR # Убедимся, что APP_DIR импортирован


# ===============================
# Application (PyQt6 UI) - Основное окно
# ===============================
class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config_data = Config()
        self.workers = {}
        self.queue_running = False
        self.queue_current_idx = None
        self.t = helpers.translate # Обновляем на helpers.translate
        self.card_widgets = {}
        self.selected_card_idx = None # Добавляем для отслеживания выбранной карточки
        self._interactive_driver = None # Добавляем для интерактивного драйвера

        self.setWindowIcon(QIcon(os.path.join(APP_DIR, "loader", "assets", "icons.ico")))

        # Load Montserrat font
        font_path = os.path.join(APP_DIR, "assets", "Montserrat-Regular.ttf") # Обновлен путь к шрифту
        if os.path.exists(font_path):
            font_id = QFontDatabase.addApplicationFont(font_path)
            if font_id != -1:
                font_families = QFontDatabase.applicationFontFamilies(font_id)
                if font_families:
                    self.app_font = QFont(font_families[0])
                    self.app_font.setPointSize(9)  # Уменьшаем размер шрифта на 1 пункт
                    QApplication.instance().setFont(self.app_font)
                    print(f"Font '{font_families[0]}' loaded and applied.")
                else:
                    print(f"Error: No font families found for font ID {font_id}")
            else:
                print(f"Error: Could not add font from {font_path}")
        else:
            print(f"Warning: Font file not found at {font_path}. Using default font.")

        self._setup_ui()
        self.refresh_list()

    def _load_stylesheet(self):
        style_path = os.path.join(APP_DIR, "ui", "styles.qss")
        if os.path.exists(style_path):
            with open(style_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        else:
            print(f"Warning: Stylesheet file not found at {style_path}. Using default styles.")

    def _run_queue_from(self, start_idx):
        if start_idx >= len(self.config_data.items):
            self.queue_running = False
            self.queue_current_idx = None
            self.toggle_button.setText(self.t("btn_start_queue"))
            self.status_label.setText(self.t("queue_finished_status"))
            self.refresh_list()
            return

        self.queue_current_idx = start_idx
        self._start_index(start_idx)

    def _setup_ui(self):
        self.setWindowTitle("KickDropsMiner")
        self.setGeometry(100, 100, 1000, 600)
        self.setFixedSize(880, 550) # Устанавливаем фиксированный размер окна# Это больше не нужно, так как размер фиксирован, но оставлю на всякий случай
        self._load_stylesheet()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # --- Header Control Panel ---
        self._setup_header_control_panel(main_layout)

        # --- Main Content Area (Stream Cards) ---
        self._setup_main_content_area(main_layout)

        # --- Status Bar ---
        self._setup_status_bar()

    def _setup_header_control_panel(self, main_layout):
        header = QFrame()
        header.setObjectName("ControlPanel")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(15, 15, 15, 15)
        header_layout.setSpacing(15)

        # Row 1: Main Actions
        actions_row = QHBoxLayout()
        actions_row.setSpacing(15)

        btn_add = QPushButton(self.t("btn_add"))
        btn_add.clicked.connect(self.add_link)
        actions_row.addWidget(btn_add)

        # Main Toggle Button
        btn_toggle_all = QPushButton(self.t("btn_start_queue"))
        btn_toggle_all.setObjectName("ToggleAllButton")
        btn_toggle_all.clicked.connect(self.toggle_all_streams)
        self.toggle_button = btn_toggle_all
        actions_row.addWidget(btn_toggle_all)

        btn_remove = QPushButton(self.t("btn_remove"))
        btn_remove.clicked.connect(self.remove_selected)
        actions_row.addWidget(btn_remove)

        btn_drops = QPushButton(self.t("btn_drops"))
        btn_drops.setObjectName("DropsButton")
        btn_drops.clicked.connect(self.show_drops_window)
        actions_row.addWidget(btn_drops)

        self.btn_telegram = QPushButton(self.t("btn_telegram"))
        self.btn_telegram.setObjectName("TelegramButton")
        # Исправленный путь к icons.ico
        self.btn_telegram.setIcon(helpers.get_icon("assets/icons.ico")) # Обновляем на helpers.get_icon
        self.btn_telegram.clicked.connect(self.show_telegram_settings)
        actions_row.addWidget(self.btn_telegram)

        # Кнопка Статистика
        self.btn_stats = QPushButton(self.t("btn_stats"))
        self.btn_stats.clicked.connect(self.show_stats_window)
        actions_row.addWidget(self.btn_stats)

        # Кнопка Настройки
        self.btn_settings = QPushButton(self.t("settings_title")) # Используем перевод для текста кнопки
        self.btn_settings.clicked.connect(self.show_settings_dialog) # Подключаем к новому слоту
        actions_row.addWidget(self.btn_settings)

        actions_row.addStretch(1)

        # Row 2: Settings and Toggles
        settings_row = QHBoxLayout()
        settings_row.setSpacing(25)

        self.chk_mute = QCheckBox(self.t("switch_mute"))
        self.chk_mute.setChecked(self.config_data.mute)
        self.chk_mute.stateChanged.connect(self.on_toggle_mute)
        settings_row.addWidget(self.chk_mute)

        self.chk_hide_player = QCheckBox(self.t("switch_hide"))
        self.chk_hide_player.setChecked(self.config_data.hide_player)
        self.chk_hide_player.stateChanged.connect(self.on_toggle_hide)
        settings_row.addWidget(self.chk_hide_player)

        self.chk_mini_player = QCheckBox(self.t("switch_mini"))
        self.chk_mini_player.setChecked(self.config_data.mini_player)
        self.chk_mini_player.stateChanged.connect(self.on_toggle_mini)
        settings_row.addWidget(self.chk_mini_player)

        settings_row.addStretch(2) # Добавляем растяжку, чтобы кнопки сдвигались вправо

        # Группа кнопок для управления Chrome и сохранения конфигурации
        btn_save_config = QPushButton(self.t("save_config"))
        btn_save_config.clicked.connect(self.save_config)
        settings_row.addWidget(btn_save_config)

        btn_signin = QPushButton(self.t("btn_signin"))
        btn_signin.clicked.connect(self.connect_to_kick)
        settings_row.addWidget(btn_signin)

        # Кнопка Редактировать карточку
        btn_edit_card = QPushButton(self.t("btn_edit_card"))
        btn_edit_card.clicked.connect(self.edit_selected_card)
        settings_row.addWidget(btn_edit_card)

        header_layout.addLayout(actions_row)
        header_layout.addLayout(settings_row)
        main_layout.addWidget(header)

    def _setup_main_content_area(self, main_layout):
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.list_content = QWidget()
        self.list_layout = QVBoxLayout(self.list_content)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.list_content.setObjectName("ListContent")
        self.scroll_area.setWidget(self.list_content)
        main_layout.addWidget(self.scroll_area, 1)

    def _setup_status_bar(self):
        self.status_bar = self.statusBar()
        self.status_label = QLabel(self.t("status_ready"))
        self.status_bar.addWidget(self.status_label)

        # "Водяной знак" с ссылкой на Telegram создателя
        self.creator_link_label = QLabel(f"<a href=\"{self.config_data.telegram_creator_link}\">{self.t("creator_link_text")}</a>")
        self.creator_link_label.setOpenExternalLinks(True) # Открывать ссылки во внешнем браузере
        self.creator_link_label.setTextFormat(Qt.TextFormat.RichText) # Разрешить HTML-форматирование
        self.creator_link_label.setToolTip(self.config_data.telegram_creator_link) # Подсказка с полной ссылкой
        self.creator_link_label.setAlignment(Qt.AlignmentFlag.AlignRight) # Выравнивание вправо
        self.status_bar.addPermanentWidget(self.creator_link_label)

    @QtCore.pyqtSlot()
    def refresh_list(self):
        # Clear existing cards and widgets
        for i in reversed(range(self.list_layout.count())):
            widget = self.list_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self.card_widgets.clear()

        # This re-indexing logic needs to run before the loop begins to ensure `self.workers` keys are correct.
        temp_workers = {}
        for old_idx, worker in sorted(self.workers.items()):
            # Find the new index of the worker's URL in the refreshed config
            try:
                # The config item might have changed index or been deleted
                new_idx = next(
                    i
                    for i, item in enumerate(self.config_data.items)
                    if item.get("url") == worker.url
                )
                if new_idx != old_idx:
                    worker.idx = new_idx
                temp_workers[new_idx] = worker
            except StopIteration:
                # Worker's stream URL no longer exists in the config, stop it gracefully
                worker.stop()
        self.workers = temp_workers

        for idx, item in enumerate(self.config_data.items):
            card = StreamCard(idx, item, self.list_content)

            # Connect card signals to main app slots
            card.stop_signal.connect(self._stop_index)
            card.remove_signal.connect(self.remove_selected_by_index)
            card.start_signal.connect(self._start_index)
            card.edit_minutes_signal.connect(self._edit_stream_minutes)
            card.card_double_clicked.connect(self._on_card_double_clicked) # Подключаем новый сигнал

            self.card_widgets[idx] = card

            # --- ИСПРАВЛЕННАЯ ЛОГИКА ИЗВЛЕЧЕНИЯ ВРЕМЕНИ ---
            worker = self.workers.get(idx)
            if worker:
                # Если рабочий поток активен, берем текущее время из его атрибута
                elapsed_seconds = worker.elapsed_seconds
            else:
                # Если рабочий поток неактивен, берем последнее сохраненное время из конфигурации
                elapsed_seconds = item.get("elapsed", 0)
            # --- КОНЕЦ ИСПРАВЛЕННОЙ ЛОГИКИ ---

            is_active = idx in self.workers and self.workers[idx].is_alive()
            is_completed = item.get("finished", False) and item["minutes"] > 0

            card.update_state(
                elapsed_seconds, live=False, is_active=is_active, completed=is_completed
            )

            self.list_layout.addWidget(card)

        # Update main toggle button text
        active_count = sum(1 for w in self.workers.values() if w.is_alive())
        if active_count > 0:
            self.toggle_button.setText(self.t("btn_stop_queue"))
        else:
            self.toggle_button.setText(self.t("btn_start_queue"))

    @QtCore.pyqtSlot(int)
    def _on_card_double_clicked(self, idx):
        """Слот для обработки двойного клика по карточке стрима."""
        if self.selected_card_idx is not None and self.selected_card_idx in self.card_widgets:
            self.card_widgets[self.selected_card_idx].deselect_card()

        self.selected_card_idx = idx
        if idx in self.card_widgets:
            self.card_widgets[idx].select_card()

    def _edit_stream_minutes(self, idx, new_minutes):
        self.config_data.items[idx]["minutes"] = new_minutes
        self.config_data.save()
        self.refresh_list()

    # --- UI Events ---
    def on_toggle_mute(self, state):
        self.config_data.mute = state == Qt.CheckState.Checked
        self.config_data.save()

    def on_toggle_hide(self, state):
        self.config_data.hide_player = state == Qt.CheckState.Checked
        self.config_data.save()

    def on_toggle_mini(self, state):
        self.config_data.mini_player = state == Qt.CheckState.Checked
        self.config_data.save()

    # --- Actions ---
    def add_link(self):
        # Use existing QInputDialog for simplicity
        url, ok = QInputDialog.getText(
            self, self.t("prompt_live_url_title"), self.t("prompt_live_url_msg")
        )
        if not ok or not url:
            return

        minutes, ok = QInputDialog.getInt(
            self,
            self.t("prompt_minutes_title"),
            self.t("prompt_minutes_msg"),
            120,
            0,
            999999,
        )
        if ok:
            self.config_data.add(url, minutes)
            self.refresh_list()
            self.status_label.setText(self.t("status_link_added"))

    def remove_selected(self):
        # Find the index of the focused card or the last card
        focused_idx = None
        for idx, card in self.card_widgets.items():
            if card.hasFocus():
                focused_idx = idx
                break

        if focused_idx is not None:
            self.remove_selected_by_index(focused_idx)
            return

        if self.card_widgets:
            idx_to_remove = max(self.card_widgets.keys())
            self.remove_selected_by_index(idx_to_remove)

    def remove_selected_by_index(self, idx):
        if idx in self.workers:
            self.workers[idx].stop()

        self.config_data.remove(idx)

        # Note: The refresh_list function now handles worker re-indexing based on URL,
        # so manual re-indexing here is no longer strictly necessary but is kept
        # for immediate consistency if refresh_list is not called immediately.
        # However, since refresh_list is called right after, we can rely on it.

        self.refresh_list()
        self.status_label.setText(self.t("status_link_removed"))

    # --- Concurrency Logic ---
    def toggle_all_streams(self):
        print("toggle_all_streams: Кнопка 'Запустить Все' нажата.")
        is_running = any(w.is_alive() for w in self.workers.values())

        if is_running:
            print("toggle_all_streams: Стримы активны, останавливаем их.")
            for idx, worker in list(self.workers.items()):
                worker.stop()
            self.toggle_button.setText(self.t("btn_start_queue"))
            self.status_label.setText(self.t("queue_finished_status"))
            self.queue_running = False
            self.queue_current_idx = None  # Сбрасываем текущий индекс
            self.refresh_list()
            return

        if not self.config_data.items:
            print("toggle_all_streams: Нет элементов в конфигурации для запуска.")
            self.status_label.setText(self.t("status_ready"))
            return

        print("toggle_all_streams: Запускаем очередь стримов.")
        self.queue_running = True
        self.queue_current_idx = 0
        self._run_queue_from(0)
        self.toggle_button.setText(self.t("btn_stop_queue"))

    def _start_index(self, idx):
        print(f"_start_index: Попытка запустить стрим с индексом {idx}.")
        if idx >= len(self.config_data.items):
            print(f"_start_index: Индекс {idx} вне диапазона конфигурации.")
            return

        if idx in self.workers and self.workers[idx].is_alive():
            print(f"_start_index: Стрим с индексом {idx} уже активен.")
            return

        item = self.config_data.items[idx]
        print(f"_start_index: Проверяем статус 'live' для URL: {item['url']}")
        if not helpers.kick_is_live_by_api(item["url"]):
            print(f"_start_index: Стрим {item['url']} не активен (offline).")
            self.status_label.setText(
                self.t("offline_wait_retry").format(url=item["url"])
            )
            if idx in self.card_widgets:
                self.card_widgets[idx].update_state(
                    item.get("elapsed", 0), False, is_active=False
                )
            return

        domain = helpers.domain_from_url(item["url"])
        if not domain:
            print(f"_start_index: Неверный домен для URL: {item['url']}")
            QMetaObject.invokeMethod(
                self,
                "_show_critical_message_slot",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, self.t("error")),
                Q_ARG(str, self.t("invalid_url"))
            )
            return

        if idx in self.workers:
            print(f"_start_index: Останавливаем существующий worker для индекса {idx}.")
            self.workers[idx].stop()
            time.sleep(0.5)

        try:
            print(f"_start_index: Создаем StreamWorker для индекса {idx}, URL: {item['url']}")
            worker = StreamWorker(
                item["url"],
                item["minutes"],
                idx,
                driver_path=self.config_data.chromedriver_path,
                extension_path=self.config_data.extension_path,
                hide_player=self.chk_hide_player.isChecked(),
                mute=self.chk_mute.isChecked(),
                mini_player=self.chk_mini_player.isChecked(),
                config=self.config_data,
            )

            # Инициализация TelegramNotifier и передача его в StreamWorker
            if self.config_data.telegram_bot_token and self.config_data.telegram_chat_id:
                print("_start_index: Инициализация TelegramNotifier.")
                worker.telegram_notifier = TelegramNotifier(
                    self.config_data.telegram_bot_token, self.config_data.telegram_chat_id
                )

            worker.signals.update.connect(self._on_worker_update_slot)
            worker.signals.finish.connect(self._on_worker_finish_slot)
            worker.signals.progress_update.connect(self._on_worker_progress_update_slot) # Подключаем новый сигнал
            worker.signals.error.connect(
                functools.partial(self._show_critical_message_slot, self.t("error"))
            )

            self.workers[idx] = worker
            worker.start()
            print(f"_start_index: StreamWorker для индекса {idx} запущен.")

            if idx in self.card_widgets:
                self.card_widgets[idx].loading_indicator.setVisible(
                    True
                )
                self.card_widgets[idx].update_state(
                    item.get("elapsed", 0), True, is_active=True
                )

            self.status_label.setText(self.t("status_playing").format(url=item["url"]))
        except Exception as e:
            print(f"_start_index: Ошибка при запуске StreamWorker для индекса {idx}: {e}")
            QMetaObject.invokeMethod(
                self,
                "_show_critical_message_slot",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, self.t("error")),
                Q_ARG(str, f"Ошибка при запуске стрима: {e}")
            )

    def show_telegram_settings(self):
        dialog = TelegramSettingsDialog(self, self.config_data)
        dialog.exec()

    def _stop_index(self, idx):
        if idx in self.workers:
            worker = self.workers[idx]
            worker.stop()
            self.status_label.setText(self.t("status_stopped"))

    # --- Worker Signal Slots (Run in Main UI Thread) ---
    @QtCore.pyqtSlot(int, int, bool)
    def _on_worker_update_slot(self, idx, seconds, live):

        if idx not in self.card_widgets:
            return

        card = self.card_widgets[idx]
        card.update_state(seconds, live, is_active=True)

        active_count = sum(1 for w in self.workers.values() if w.is_alive())
        if active_count > 0:
            try:
                item = self.config_data.items[idx]
                minutes = seconds // 60
                secs = seconds % 60
                time_str = f"{minutes}m {secs}s" if minutes > 0 else f"{secs}s"
                status = self.t("tag_live") if live else self.t("tag_paused")

                status_text = self.t("queue_running_status").format(
                    count=active_count, url=item["url"]
                )
                self.status_label.setText(f"{status_text} ({time_str}, {status})")
            except IndexError:
                self.status_label.setText(f"Активно: {active_count} стрим(ов).")
        else:
            self.status_label.setText(self.t("status_ready"))

    @QtCore.pyqtSlot(int, int, bool, str) # Добавлен аргумент reason
    def _on_worker_finish_slot(self, idx, elapsed, completed, reason): # Добавлен аргумент reason
        worker = self.workers.pop(idx, None)
        if worker is None:
            return

        if idx < len(self.config_data.items):
            self.config_data.items[idx][
                "elapsed"
            ] = elapsed
            self.config_data.items[idx]["finished"] = completed
            self.config_data.save()

        if idx in self.card_widgets:
            self.card_widgets[idx].update_state(
                elapsed, False, is_active=False, completed=completed
            )

        self.refresh_list()

        # Восстанавливаем логику queue_running для последовательного запуска
        if self.queue_running and self.queue_current_idx == idx:
            print(f"_on_worker_finish_slot: Стрим {idx} завершился с причиной: {reason}. Запускаем следующий.") # Добавлено логирование
            # Если стрим завершился из-за офлайна или достижения цели, переходим к следующему
            if reason == "Stream Offline" or reason == "Target Reached": # Добавлено условие для Target Reached
                self._run_queue_from(idx + 1)
            # Если это был последний стрим в очереди, или остановлен пользователем, то очередь завершается
            else: # Если любая другая причина, включая "Stopped by user"
                if self.queue_current_idx < len(self.config_data.items) - 1: # Если есть следующий стрим в очереди
                    self._run_queue_from(idx + 1) # Продолжаем очередь
                else: # Это был последний стрим
                    self.queue_running = False
                    self.queue_current_idx = None
                    self.toggle_button.setText(self.t("btn_start_queue"))
                    self.status_label.setText(self.t("queue_finished_status"))
                    self.refresh_list()

    @QtCore.pyqtSlot(int, int, int) # Новый слот для обновления прогресса
    def _on_worker_progress_update_slot(self, idx, elapsed_seconds, target_seconds):
        if idx in self.card_widgets:
            self.card_widgets[idx].update_progress(elapsed_seconds, target_seconds)

    # --- File/Cookie Logic (Uses PyQt6 QDesktopServices for opening links) ---
    def connect_to_kick(self):
        url = "https://kick.com"
        focused_card = next(
            (card for card in self.card_widgets.values() if card.hasFocus()), None
        )
        if focused_card:
            url = focused_card.item["url"]
        domain = helpers.domain_from_url(url)

        try:
            drv = make_chrome_driver(
                headless=False,
                driver_path=self.config_data.chromedriver_path,
                extension_path=self.config_data.extension_path,
            )
            self._interactive_driver = drv
        except Exception as e:
            QMessageBox.critical(self, self.t("error"), self.t("chrome_start_fail").format(e=e))
            return
        drv.get(url)
        QMessageBox.information(self, self.t("action_required"), self.t("sign_in_and_click_ok"))
        try:
            CookieManager.save_cookies(drv, domain)
            QMessageBox.information(
                self, self.t("ok"), self.t("cookies_saved_for").format(domain=domain)
            )
        except Exception as e:
            QMessageBox.critical(self, self.t("error"), self.t("cannot_save_cookies").format(e=e))
        finally:
            try:
                drv.quit()
            except Exception:
                pass
            finally:
                self._interactive_driver = None

        self.refresh_list()

    def save_config(self):
        self.config_data.save()
        self.refresh_list()
        self.status_label.setText(self.t("config_saved"))

    def edit_selected_card(self):
        # Используем self.selected_card_idx вместо поиска по фокусу
        focused_idx = self.selected_card_idx

        if focused_idx is None or focused_idx not in self.card_widgets:
            QMessageBox.information(self, self.t("warning"), self.t("no_card_selected_for_edit"))
            return

        # Редактируем URL
        current_url = self.config_data.items[focused_idx]["url"]
        new_url, ok = QInputDialog.getText(
            self, self.t("edit_stream_url_title"), self.t("edit_stream_url_msg"), QLineEdit.EchoMode.Normal, current_url
        )
        if not ok or not new_url:
            return

        # Редактируем минуты просмотра
        current_minutes = self.config_data.items[focused_idx]["minutes"]
        new_minutes, ok = QInputDialog.getInt(
            self, self.t("edit_stream_minutes_title"), self.t("edit_stream_minutes_msg"),
            current_minutes, 0, 999999
        )
        if ok:
            self.config_data.items[focused_idx]["url"] = new_url
            self.config_data.items[focused_idx]["minutes"] = new_minutes
            self.config_data.save()
            self.refresh_list()
            self.status_label.setText(self.t("status_card_edited"))

    def initialize_client(self, config_path="config.json"):
        self.config_data.load()
        self.refresh_list()
        self.status_label.setText(self.t("status_ready"))

    @pyqtSlot(str, str, QtWidgets.QMessageBox.StandardButton)
    def _show_info_message_slot(self, title, message, buttons):
        QMessageBox.information(self, title, message, buttons)

    @pyqtSlot(str, str)
    def _show_critical_message_slot(self, title, message):
        QMessageBox.critical(self, title, message)

    def show_error_message(self, message):
        QMessageBox.critical(self, self.t("error"), message)

    def show_drops_window(self):
        drops_window = DropsWindow(self)
        drops_window.show()

    def show_stats_window(self):
        """Открывает окно статистики."""
        self.stats_window = StatsWindow(self)
        self.stats_window.show()

    def show_settings_dialog(self):
        dialog = SettingsDialog(self.config_data, self)
        dialog.exec()

    def closeEvent(self, event):
        # Gracefully stop all workers before closing
        for idx, w in list(self.workers.items()):
            try:
                w.stop()
            except Exception:
                pass

        # Close interactive driver if open
        if self._interactive_driver:
            try:
                self._interactive_driver.quit()
            except Exception:
                pass
            self._interactive_driver = None

        event.accept()
