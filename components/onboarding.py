"""components/onboarding.py — Onboarding tour con coach marks.

Overlay semitransparente + recorte con CompositionMode_Clear + globo flotante.
Pure PySide6, sin dependencias externas. Persiste en QSettings.
"""

from __future__ import annotations
from typing import Callable, NamedTuple

from PySide6.QtCore import Qt, QRect, QTimer, QSettings, QObject, QEvent
from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QFrame,
)
from PySide6.QtGui import QPainter, QColor, QPixmap, QPen

_SETTINGS_KEY = "onboarding_v1_done"
_BUBBLE_W     = 320
_GAP          = 14    # px entre borde del cutout y el globo
_MARGIN       = 14    # margen mínimo desde los bordes de la ventana
_CUT_PAD_H    = 10    # padding horizontal del recorte (ambos lados)
_CUT_PAD_V    = 6     # padding vertical del recorte (ambos lados)
_RADIUS       = 8     # radio de los bordes redondeados del recorte
_SCREEN_DELAY = 60    # ms de espera tras un cambio de pantalla


class TourStep(NamedTuple):
    title: str
    body: str
    # Devuelve el widget a resaltar, o None para centrado sin recorte
    widget_getter: Callable[[], "QWidget | None"]
    # Callback opcional ejecutado ANTES de mostrar el paso (ej.: cambiar pantalla)
    on_enter: "Callable[[], None] | None" = None


# ─────────────────────────────────────────────────────────────────────────────
# _Overlay
# ─────────────────────────────────────────────────────────────────────────────

class _Overlay(QWidget):
    """Capa semitransparente sobre el central widget con recorte transparente.

    Bloquea la interacción con la app subyacente. El globo (_Bubble) se apila
    encima y recibe eventos normalmente porque es un widget hermano en Z superior.
    """

    def __init__(
        self,
        parent: QWidget,
        on_next: Callable[[], None],
        on_skip: Callable[[], None],
    ) -> None:
        super().__init__(parent)
        self.setGeometry(parent.rect())
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._cutout: QRect = QRect()
        self._on_next = on_next
        self._on_skip = on_skip

    def set_cutout(self, rect: QRect) -> None:
        self._cutout = rect
        self.update()

    # ── Painting ─────────────────────────────────────────────────────────────

    def paintEvent(self, _event) -> None:
        # Usamos QPixmap intermedio para CompositionMode_Clear sin afectar
        # la ventana subyacente.
        px = QPixmap(self.size())
        px.fill(Qt.GlobalColor.transparent)

        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. Fondo oscuro sobre toda el área
        p.fillRect(self.rect(), QColor(0, 0, 0, 168))

        if not self._cutout.isNull():
            padded = self._cutout.adjusted(
                -_CUT_PAD_H, -_CUT_PAD_V, _CUT_PAD_H, _CUT_PAD_V,
            )
            # 2. Recorte transparente mediante CompositionMode_Clear
            p.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_Clear
            )
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(Qt.GlobalColor.transparent)
            p.drawRoundedRect(padded, _RADIUS, _RADIUS)

            # 3. Anillo de foco dorado
            p.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_SourceOver
            )
            ring = QPen(QColor("#C9A44A"))
            ring.setWidth(2)
            p.setPen(ring)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(padded, _RADIUS, _RADIUS)

        p.end()

        out = QPainter(self)
        out.drawPixmap(0, 0, px)
        out.end()

    # ── Teclado para navegación sin mouse ─────────────────────────────────────

    def keyPressEvent(self, event) -> None:
        k = event.key()
        if k == Qt.Key.Key_Escape:
            self._on_skip()
        elif k in (
            Qt.Key.Key_Return, Qt.Key.Key_Enter,
            Qt.Key.Key_Space, Qt.Key.Key_Right,
        ):
            self._on_next()
        else:
            event.accept()

    # ── Bloquear interacción con la app ───────────────────────────────────────

    def mousePressEvent(self, e):   e.accept()
    def mouseReleaseEvent(self, e): e.accept()
    def mouseMoveEvent(self, e):    e.accept()


# ─────────────────────────────────────────────────────────────────────────────
# _Bubble
# ─────────────────────────────────────────────────────────────────────────────

class _Bubble(QFrame):
    """Globo flotante: título, cuerpo, puntos de progreso y botón Siguiente."""

    def __init__(
        self,
        total: int,
        on_next: Callable[[], None],
        on_skip: Callable[[], None],
        parent: QWidget,
    ) -> None:
        super().__init__(parent)
        self._total = total
        self._on_next = on_next
        self._on_skip = on_skip
        self.setFixedWidth(_BUBBLE_W)
        self._build()

    def _build(self) -> None:
        from styles.theme import (
            BG1, TEXT0, TEXT1, TEXT3,
            ACCENT, ACCENT2, ACCENT3, fs,
        )

        self.setStyleSheet(f"""
            QFrame {{
                background: {BG1};
                border: 1px solid rgba(201,164,74,0.35);
                border-top: 2px solid {ACCENT};
                border-radius: 6px;
            }}
        """)

        lo = QVBoxLayout(self)
        lo.setContentsMargins(18, 14, 18, 16)
        lo.setSpacing(6)

        # ── Header: "PASO N DE M" + botón cerrar ─────────────────────────────
        hdr = QHBoxLayout()
        hdr.setSpacing(0)
        self._step_lbl = QLabel()
        self._step_lbl.setStyleSheet(
            f"color:rgba(201,164,74,0.55); font-size:{fs(9)}px; font-weight:700;"
            f" letter-spacing:1.8px; background:transparent; border:none;"
        )
        hdr.addWidget(self._step_lbl)
        hdr.addStretch()
        skip_btn = QPushButton("✕")
        skip_btn.setFixedSize(20, 20)
        skip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        skip_btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:{TEXT3};border:none;"
            f"font-size:{fs(12)}px;padding:0;}}"
            f"QPushButton:hover{{color:{TEXT0};}}"
        )
        skip_btn.clicked.connect(self._on_skip)
        hdr.addWidget(skip_btn)
        lo.addLayout(hdr)

        # ── Título ────────────────────────────────────────────────────────────
        self._title_lbl = QLabel()
        self._title_lbl.setStyleSheet(
            f"color:{TEXT0}; font-size:{fs(13)}px; font-weight:700;"
            f" background:transparent; border:none;"
        )
        lo.addWidget(self._title_lbl)

        # ── Cuerpo ────────────────────────────────────────────────────────────
        self._body_lbl = QLabel()
        self._body_lbl.setWordWrap(True)
        self._body_lbl.setStyleSheet(
            f"color:{TEXT1}; font-size:{fs(11)}px;"
            f" background:transparent; border:none;"
        )
        lo.addWidget(self._body_lbl)

        lo.addSpacing(4)

        # ── Footer: puntos de progreso + botón Siguiente/Finalizar ────────────
        ftr = QHBoxLayout()
        ftr.setSpacing(5)
        self._dots: list[QLabel] = []
        for _ in range(self._total):
            d = QLabel("●")
            d.setStyleSheet(
                f"color:rgba(201,164,74,0.2); font-size:{fs(8)}px;"
                f" background:transparent; border:none;"
            )
            ftr.addWidget(d)
            self._dots.append(d)
        ftr.addStretch()

        self._next_btn = QPushButton()
        self._next_btn.setFixedHeight(30)
        self._next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._next_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {ACCENT3}, stop:1 {ACCENT});
                color: #1a1714;
                border: none;
                border-bottom: 2px solid {ACCENT2};
                border-radius: 2px;
                font-size: {fs(11)}px; font-weight: 700;
                padding: 0 18px;
            }}
            QPushButton:hover {{ background: {ACCENT3}; }}
            QPushButton:pressed {{ border-bottom: none; margin-top: 2px; }}
        """)
        self._next_btn.clicked.connect(self._on_next)
        ftr.addWidget(self._next_btn)
        lo.addLayout(ftr)

    def update_step(self, idx: int, title: str, body: str) -> None:
        from styles.theme import ACCENT, fs
        from utils.i18n import _
        self._step_lbl.setText(
            _("PASO {} DE {}").format(idx + 1, self._total)
        )
        self._title_lbl.setText(title)
        self._body_lbl.setText(body)
        self._next_btn.setText(
            _("Finalizar") if idx == self._total - 1 else _("Siguiente  →")
        )
        for i, d in enumerate(self._dots):
            if i < idx:
                style = (
                    f"color:rgba(201,164,74,0.45); font-size:{fs(8)}px;"
                    f" background:transparent; border:none;"
                )
            elif i == idx:
                style = (
                    f"color:{ACCENT}; font-size:{fs(10)}px;"
                    f" background:transparent; border:none;"
                )
            else:
                style = (
                    f"color:rgba(201,164,74,0.2); font-size:{fs(8)}px;"
                    f" background:transparent; border:none;"
                )
            d.setStyleSheet(style)
        self.adjustSize()


# ─────────────────────────────────────────────────────────────────────────────
# OnboardingTour — coordinador
# ─────────────────────────────────────────────────────────────────────────────

class OnboardingTour(QObject):
    """Coordina el tour completo: overlay, globo, avance de pasos y persistencia.

    Uso::

        tour = OnboardingTour(main_window, steps)
        tour.start_if_needed()   # no-op silencioso si ya se completó
    """

    def __init__(self, window: QWidget, steps: list[TourStep]) -> None:
        super().__init__(window)
        self._window = window
        self._steps = steps
        self._idx = 0
        self._overlay: _Overlay | None = None
        self._bubble: _Bubble | None = None
        self._active = False

    # ── API pública ───────────────────────────────────────────────────────────

    def start_if_needed(self) -> None:
        """Muestra el tour solo si QSettings indica que no se completó aún."""
        if QSettings("ScoutApp", "prefs").value(
            _SETTINGS_KEY, False, type=bool
        ):
            return
        # 900ms de gracia; _start() reintenta cada 400ms si la ventana no
        # está visible todavía (ej.: StartDialog sigue abierto).
        QTimer.singleShot(900, self._start)

    def force_start(self) -> None:
        """Fuerza el inicio del tour (ej.: Ayuda → Reiniciar tour)."""
        if self._active:
            self._cleanup()
        QSettings("ScoutApp", "prefs").setValue(_SETTINGS_KEY, False)
        QTimer.singleShot(100, self._start)

    # ── Event filter — resize del central widget ──────────────────────────────

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # type: ignore[override]
        if self._active and event.type() == QEvent.Type.Resize:
            central = self._window.centralWidget()
            if central and obj is central:
                if self._overlay:
                    self._overlay.setGeometry(central.rect())
                    self._overlay.update()
                self._refresh_positions()
        return False

    # ── Internos ──────────────────────────────────────────────────────────────

    def _central(self) -> QWidget:
        return self._window.centralWidget() or self._window

    def _start(self) -> None:
        if self._active:
            return
        # Esperar a que la ventana esté visible (StartDialog puede seguir abierto)
        if not self._window.isVisible() or self._window.isMinimized():
            QTimer.singleShot(400, self._start)
            return
        self._active = True
        self._idx = 0
        central = self._central()
        central.installEventFilter(self)

        self._overlay = _Overlay(
            parent=central,
            on_next=self._next_step,
            on_skip=self._finish,
        )
        self._overlay.show()
        self._overlay.raise_()
        self._overlay.setFocus()

        self._bubble = _Bubble(
            total=len(self._steps),
            on_next=self._next_step,
            on_skip=self._finish,
            parent=central,
        )
        self._bubble.show()
        self._bubble.raise_()

        self._show_step(0)

    def _show_step(self, idx: int) -> None:
        """Ejecuta on_enter y luego aplica el step con un pequeño delay."""
        step = self._steps[idx]
        if step.on_enter is not None:
            step.on_enter()
            # Dejar que Qt procese el cambio de pantalla antes de calcular rects
            QTimer.singleShot(_SCREEN_DELAY, lambda: self._apply_step(idx))
        else:
            self._apply_step(idx)

    def _apply_step(self, idx: int) -> None:
        """Actualiza overlay y globo para el paso idx."""
        if not self._active:
            return
        step = self._steps[idx]
        central = self._central()
        cutout = self._widget_rect_in(step.widget_getter(), central)

        self._overlay.setGeometry(central.rect())
        self._overlay.set_cutout(cutout)
        self._bubble.update_step(idx, step.title, step.body)
        self._position_bubble(cutout, central.rect())
        self._bubble.raise_()

    def _widget_rect_in(
        self, target: "QWidget | None", central: QWidget
    ) -> QRect:
        if target is None or not target.isVisible():
            return QRect()
        tl = target.mapTo(central, target.rect().topLeft())
        br = target.mapTo(central, target.rect().bottomRight())
        return QRect(tl, br)

    def _position_bubble(self, cutout: QRect, parent_rect: QRect) -> None:
        pw, ph = parent_rect.width(), parent_rect.height()
        bw = self._bubble.width()
        bh = self._bubble.height()  # actualizado por adjustSize() en update_step

        if cutout.isNull():
            self._bubble.move((pw - bw) // 2, (ph - bh) // 2)
            return

        # Preferencia: debajo → arriba → clampeado
        below = cutout.bottom() + _CUT_PAD_V + _GAP
        above = cutout.top() - _CUT_PAD_V - _GAP - bh

        if below + bh <= ph - _MARGIN:
            y = below
        elif above >= _MARGIN:
            y = above
        else:
            y = max(_MARGIN, min(below, ph - bh - _MARGIN))

        # Horizontal: centrado sobre el target, clampeado
        cx = cutout.center().x() - bw // 2
        x = max(_MARGIN, min(cx, pw - bw - _MARGIN))

        self._bubble.move(x, y)

    def _refresh_positions(self) -> None:
        if not (self._active and self._overlay and self._bubble):
            return
        step = self._steps[self._idx]
        central = self._central()
        cutout = self._widget_rect_in(step.widget_getter(), central)
        self._overlay.set_cutout(cutout)
        self._position_bubble(cutout, central.rect())

    def _next_step(self) -> None:
        self._idx += 1
        if self._idx >= len(self._steps):
            self._finish()
        else:
            self._show_step(self._idx)

    def _finish(self) -> None:
        QSettings("ScoutApp", "prefs").setValue(_SETTINGS_KEY, True)
        self._cleanup()
        # Volver a Observación al terminar el tour
        if hasattr(self._window, "_switch_screen"):
            self._window._switch_screen(0)

    def _cleanup(self) -> None:
        self._active = False
        central = self._central()
        central.removeEventFilter(self)
        for w in (self._overlay, self._bubble):
            if w is not None:
                w.hide()
                w.deleteLater()
        self._overlay = None
        self._bubble = None
