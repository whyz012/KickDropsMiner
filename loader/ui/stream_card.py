# ===============================
# Worker streaming (Adapted from bob.py)
# ===============================

# ===============================
# Config (Same)
# ===============================
from loader.core.config import Config


from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QSpacerItem,
    QSizePolicy,
    QMessageBox,
    QInputDialog,
    QProgressBar, # Добавлен QProgressBar
)
from PyQt6.QtGui import QFont
from loader.utils.helpers import translate as t, domain_from_url
from urllib.parse import urlparse


# ===============================
# Custom Widgets (StreamCard, CollapsibleGroup) - Adapted to PyQt6
# ===============================


class StreamCard(QFrame):
    """Кастомный виджет для отображения информации о стриме с новым дизайном."""

    stop_signal = pyqtSignal(int)
    remove_signal = pyqtSignal(int)
    start_signal = pyqtSignal(int)
    edit_minutes_signal = pyqtSignal(int, int)
    card_double_clicked = pyqtSignal(int) # Новый сигнал для двойного клика
    update_progress_signal = pyqtSignal(int, int, int) # idx, elapsed_seconds, target_seconds

    def __init__(self, idx, item, parent=None):
        super().__init__(parent)
        self.idx = idx
        self.item = item
        self.is_active = False
        self.is_selected = False # Новый флаг для состояния выбора
        self.t = t
        self.parsed_url = urlparse(item["url"]) # Разбираем URL один раз

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setObjectName("StreamCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(
            15, 15, 15, 15
        )  # Increased padding for spacious feel

        # --- Left Section: Status & URL ---
        left_layout = QVBoxLayout()
        left_layout.setSpacing(5)

        self.url_label = QLabel(self._get_channel_name(self.parsed_url))
        self.url_label.setObjectName("ChannelName")
        left_layout.addWidget(self.url_label)

        self.full_url_label = QLabel(item["url"])
        self.full_url_label.setObjectName("FullUrl")
        left_layout.addWidget(self.full_url_label)

        self.loading_indicator = QLabel(self.t("loading_text"))  # Новый индикатор загрузки
        self.loading_indicator.setObjectName("LoadingIndicator")
        self.loading_indicator.setVisible(False)  # Изначально скрыт
        left_layout.addWidget(self.loading_indicator)

        self.status_label = QLabel(self.t("tag_stop"))
        self.status_label.setObjectName("StatusTag")
        left_layout.addWidget(self.status_label)

        self.layout.addLayout(left_layout)
        self.layout.addItem(
            QSpacerItem(20, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        )

        # --- Middle Section: Elapsed & Target ---
        middle_layout = QVBoxLayout()
        middle_layout.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.elapsed_label = QLabel("0s")
        self.elapsed_label.setObjectName("Elapsed")
        middle_layout.addWidget(self.elapsed_label)

        target_minutes = (
            self.t("inf_minutes") if item["minutes"] == 0 else f"{item['minutes']}m"
        )
        self.target_label = QLabel(f"{self.t('col_minutes')}: {target_minutes}")
        self.target_label.setObjectName("Target")
        self.target_label.setToolTip(
            self.t("cannot_edit_active_stream")
            if self.is_active
            else self.t("prompt_minutes_title")
        )
        self.target_label.mouseDoubleClickEvent = self._handle_target_double_click
        middle_layout.addWidget(self.target_label)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setObjectName("StreamProgressBar")
        self.progress_bar.setRange(0, 100) # Прогресс от 0 до 100%
        self.progress_bar.setTextVisible(True)
        middle_layout.addWidget(self.progress_bar)

        self.layout.addLayout(middle_layout)
        self.layout.addItem(
            QSpacerItem(20, 0, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
        )

        # --- Right Section: Control Buttons ---
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(8)
        controls_layout.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.btn_action = QPushButton(self.t("btn_start_short"))
        self.btn_action.setObjectName("ActionButton")
        self.btn_action.clicked.connect(self._handle_action_click)
        controls_layout.addWidget(self.btn_action)

        self.btn_remove = QPushButton(self.t("btn_remove_short"))
        self.btn_remove.setObjectName("RemoveButton")
        self.btn_remove.clicked.connect(lambda: self.remove_signal.emit(self.idx))
        controls_layout.addWidget(self.btn_remove)

        self.layout.addLayout(controls_layout)
        self.update_state(item.get("elapsed", 0), False, is_active=False)

    def mouseDoubleClickEvent(self, event):
        """Обработка двойного клика для выбора карточки."""
        self.card_double_clicked.emit(self.idx)
        super().mouseDoubleClickEvent(event)

    def select_card(self):
        """Выделить карточку."""
        self.is_selected = True
        self._update_card_style()

    def deselect_card(self):
        """Снять выделение с карточки."""
        self.is_selected = False
        self._update_card_style()

    def _update_card_style(self):
        """Возвращает строку стиля рамки в зависимости от состояния выбора."""
        return "border: 2px solid #0078D7;" if self.is_selected else ""

    def _handle_target_double_click(self, event):
        if self.is_active:
            QMessageBox.warning(
                self, self.t("warning"), self.t("cannot_edit_active_stream")
            )
            return

        current_minutes = self.item["minutes"]
        new_minutes, ok = QInputDialog.getInt(
            self,
            self.t("prompt_minutes_title"),
            self.t("prompt_minutes_msg"),
            current_minutes,
            0,
            999999,
        )

        if ok:
            self.edit_minutes_signal.emit(self.idx, new_minutes)

    def _handle_action_click(self):
        if self.is_active:
            self.stop_signal.emit(self.idx)
        else:
            self.start_signal.emit(self.idx)

    def _get_channel_name(self, parsed_url):
        return parsed_url.path.strip("/").split("/")[0] or domain_from_url(parsed_url.netloc)

    def update_state(self, seconds, live, is_active=False, completed=False):

        self.is_active = is_active
        # Save elapsed time back to the item dictionary (reference to config_data.items[idx])
        self.item["elapsed"] = seconds

        minutes_target_seconds = self.item["minutes"] * 60

        if minutes_target_seconds > 0:
            remaining_seconds = max(0, minutes_target_seconds - seconds)
            display_seconds = remaining_seconds
            prefix = "Еще смотреть: "
        else:
            display_seconds = seconds
            prefix = self.t("col_elapsed") + ": "

        minutes = display_seconds // 60
        secs = display_seconds % 60
        time_str = f"{minutes}m {secs}s"

        if completed:
            status = self.t("tag_finished")
            action_text = self.t("retry")
        elif is_active:
            status = self.t("tag_live") if live else self.t("tag_paused")
            action_text = self.t("btn_stop_short")
        else:
            status = self.t("tag_stop")
            action_text = self.t("btn_start_short")

        self.elapsed_label.setText(f"{prefix}{time_str}")  # Используем новый prefix
        self.status_label.setText(status)
        self.btn_action.setText(action_text)

        if self.loading_indicator.isVisible() and (seconds > 0 or live):
            self.loading_indicator.setVisible(
                False
            )  # Скрываем индикатор после начала отсчета или получения live-статуса

        target_minutes = (
            self.t("inf_minutes")
            if self.item["minutes"] == 0
            else f"{self.item['minutes']}m"
        )
        self.target_label.setText(f"{self.t('col_minutes')}: {target_minutes}")

        # Динамическое применение стилей в зависимости от статуса
        status_map = {
            self.t("tag_live"): ("#00B060", "rgba(0, 176, 96, 0.3)"),  # Зеленый
            self.t("tag_paused"): ("#FFA000", "rgba(255, 160, 0, 0.3)"),  # Оранжевый
            self.t("tag_finished"): ("#B0B0B0", "rgba(176, 176, 176, 0.3)"),  # Светло-серый
            self.t("tag_stop"): ("#808080", "rgba(128, 128, 128, 0.3)"),  # Серый
            self.t("retry"): ("#808080", "rgba(128, 128, 128, 0.3)"),  # Серый
        }

        border_color, bg_color_status = status_map.get(
            status, ("#808080", "rgba(128, 128, 128, 0.3)")
        )
        action_button_bg = (
            "#505050" if self.is_active else "#707070"
        )
        action_button_hover = "#606060" if self.is_active else "#808080"

        # Получаем стиль рамки для выделения
        selection_border_style = self._update_card_style()

        self.setStyleSheet(f"""
            QFrame#StreamCard {{
                border: 1px solid {border_color};
                {selection_border_style} /* Применяем стиль выделения */
            }}
            QLabel#StatusTag {{
                background-color: {bg_color_status};
            }}
            QPushButton#ActionButton {{
                background-color: {action_button_bg};
            }}
            QPushButton#ActionButton:hover {{
                background-color: {action_button_hover};
            }}
        """)
        self.update_progress(seconds, minutes_target_seconds)

        self.target_label.setToolTip(
            self.t("cannot_edit_active_stream")
            if self.is_active
            else self.t("prompt_minutes_title")
        )

    def update_progress(self, elapsed_seconds, target_seconds):
        """Обновляет прогресс-бар в зависимости от прошедшего времени и целевого времени."""
        if target_seconds > 0:
            progress = (elapsed_seconds / target_seconds) * 100
            self.progress_bar.setValue(int(progress))
            self.update_progress_signal.emit(self.idx, elapsed_seconds, target_seconds)
