from PySide6.QtWidgets import QLabel, QWidget, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor
from utils.theme_helpers import BG1, ACCENT, TEXT0, BORDER2, SHADOW


class Toast(QLabel):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hide()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)
        self._opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity)
        self._opacity.setOpacity(1.0)

    def show_message(self, text: str, duration_ms: int = 2800):
        from styles.theme import fs
        self.setStyleSheet(f"""
            QLabel {{
                background: {BG1};
                color: {TEXT0};
                border: 1.5px solid {BORDER2};
                border-left: 3px solid {ACCENT};
                border-radius: 3px;
                padding: 10px 18px;
                font-size: {fs(13)}px;
                font-weight: 500;
            }}
        """)
        self.setText(text)
        self.adjustSize()
        parent = self.parent()
        if parent:
            self.move(parent.width()  - self.width()  - 24,
                      parent.height() - self.height() - 24)
        self.show()
        self.raise_()
        self._timer.start(duration_ms)