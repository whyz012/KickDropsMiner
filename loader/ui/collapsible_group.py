from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QAbstractAnimation
from loader.utils.helpers import translate as t


class CollapsibleGroup(QWidget):
    """Группа для организации дроп-кампаний по играм с возможностью сворачивания."""

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.is_expanded = True
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Header (clickable)
        self.header_frame = QFrame()
        self.header_frame.setObjectName("CollapsibleHeader")
        self.header_frame.setCursor(Qt.CursorShape.PointingHandCursor)
        self.header_layout = QHBoxLayout(self.header_frame)
        self.header_layout.setContentsMargins(15, 10, 15, 10)

        self.toggle_icon = QLabel("▼")
        self.toggle_icon.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.header_layout.addWidget(self.toggle_icon)

        self.title_label = QLabel(f"<b>{title}</b>")
        self.title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.header_layout.addWidget(self.title_label)
        self.header_layout.addStretch(1)

        self.main_layout.addWidget(self.header_frame)

        # Content Area
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(10, 5, 10, 5)
        self.main_layout.addWidget(self.content_area)

        self.header_frame.mousePressEvent = self.toggle
        # self._apply_qss() # Удаляем вызов, так как стили будут в styles.qss

        # Анимация
        self.animation = QPropertyAnimation(self.content_area, b"maximumHeight")
        self.animation.setDuration(300) # Длительность анимации в мс
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

    def _apply_qss(self):
        # Этот метод больше не нужен, так как стили будут в styles.qss
        pass

    def add_widget(self, widget):
        self.content_layout.addWidget(widget)
        # Устанавливаем начальную максимальную высоту, чтобы анимация работала корректно
        if self.is_expanded:
            self.content_area.setMaximumHeight(self.content_area.sizeHint().height())

    def expand(self):
        self.content_area.setMaximumHeight(0)
        self.content_area.setVisible(True)
        self.animation.setStartValue(self.content_area.height())
        self.animation.setEndValue(self.content_area.sizeHint().height()) # Автоматически подбираем высоту
        self.animation.start()

    def collapse(self):
        self.animation.setStartValue(self.content_area.height())
        self.animation.setEndValue(0)
        self.animation.start()
        self.animation.finished.connect(self.content_area.hide)

    def toggle(self, event):
        self.is_expanded = not self.is_expanded
        self.toggle_icon.setText("▼" if self.is_expanded else "▶")

        if self.is_expanded:
            self.expand()
        else:
            self.collapse()
