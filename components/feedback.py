"""components/feedback.py — Dialog de feedback: 5 estrellas + sugerencias.

Se muestra automáticamente después de producir una película (post_render)
y está disponible en Ayuda → Feedback. Guarda las respuestas en
Documentos/PyScout/feedback.jsonl (una línea JSON por envío).
"""
from __future__ import annotations
import os, json
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QFrame, QWidget,
)

from utils.i18n import _

_SUPABASE_URL     = "https://vntpgdvfxmzpwwjdgpbm.supabase.co"
_SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZudHBnZHZmeG16cHd3amRncGJtIiwicm9sZSI6"
    "ImFub24iLCJpYXQiOjE3Nzk4NjAxMjMsImV4cCI6MjA5NTQzNjEyM30"
    ".TtD0LxjtEJvL49Z42r4DYl2k7HVKDeZMvnu8Q1Ceaj4"
)
from styles.theme import (
    BG1, BG2, BG3,
    TEXT0, TEXT1, TEXT2, TEXT3,
    ACCENT, ACCENT2, ACCENT3,
    BORDER2, fs,
)


def _docs_root() -> Path:
    if os.name == "nt":
        return Path(os.path.expanduser("~/Documents")) / "PyScout"
    return Path.home() / "Documents" / "PyScout"


_STAR_LABELS = {
    1: "Muy malo",
    2: "Malo",
    3: "Regular",
    4: "Bueno",
    5: "¡Excelente!",
}


class FeedbackDialog(QDialog):
    """5 estrellas clickeables + caja de sugerencias opcional."""

    def __init__(self, parent=None, context: str = "general"):
        super().__init__(parent)
        self._context = context
        self._stars   = 0
        self.setWindowTitle(_("Tu opinión"))
        self.setFixedWidth(380)
        self.setModal(True)
        self.setStyleSheet(f"background:{BG1}; color:{TEXT0};")
        self._build()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Página del formulario ─────────────────────────────────────────────
        self._form_page = QWidget()
        lo = QVBoxLayout(self._form_page)
        lo.setContentsMargins(28, 24, 28, 20)
        lo.setSpacing(0)
        root.addWidget(self._form_page)

        title_text = (
            _("¿Cómo quedó tu película?")
            if self._context == "post_render"
            else _("¿Cómo vas con PyScout?")
        )
        title = QLabel(title_text)
        title.setStyleSheet(
            f"color:{TEXT0}; font-size:{fs(15)}px; font-weight:700;"
        )
        lo.addWidget(title)
        lo.addSpacing(4)

        sub = QLabel(_("Tu feedback nos ayuda a mejorar."))
        sub.setStyleSheet(f"color:{TEXT2}; font-size:{fs(11)}px;")
        lo.addWidget(sub)
        lo.addSpacing(20)

        # Estrellas
        star_row = QHBoxLayout()
        star_row.setSpacing(8)
        star_row.addStretch()
        self._star_btns: list[QPushButton] = []
        for i in range(1, 6):
            btn = QPushButton("★")
            btn.setFixedSize(38, 38)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(self._star_style(False))
            btn.clicked.connect(lambda _=False, n=i: self._set_stars(n))
            star_row.addWidget(btn)
            self._star_btns.append(btn)
        star_row.addStretch()
        lo.addLayout(star_row)
        lo.addSpacing(6)

        self._star_lbl = QLabel("")
        self._star_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._star_lbl.setStyleSheet(
            f"color:{ACCENT}; font-size:{fs(11)}px; font-weight:600;"
        )
        self._star_lbl.setFixedHeight(18)
        lo.addWidget(self._star_lbl)
        lo.addSpacing(16)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{BORDER2};")
        lo.addWidget(sep)
        lo.addSpacing(14)

        # Sugerencias
        sugg_lbl = QLabel(_("SUGERENCIAS (OPCIONAL)"))
        sugg_lbl.setStyleSheet(
            f"color:{TEXT3}; font-size:{fs(9)}px; font-weight:700; letter-spacing:1.5px;"
        )
        lo.addWidget(sugg_lbl)
        lo.addSpacing(6)

        self._text = QTextEdit()
        self._text.setPlaceholderText(
            _("¿Qué mejorarías? ¿Qué extrañás? ¿Qué funciona perfecto?")
        )
        self._text.setFixedHeight(80)
        self._text.setStyleSheet(f"""
            QTextEdit {{
                background: {BG2}; color: {TEXT0};
                border: 1px solid {BORDER2}; border-radius: 4px;
                font-size: {fs(12)}px; padding: 8px;
            }}
            QTextEdit:focus {{ border: 1px solid {ACCENT}; }}
        """)
        lo.addWidget(self._text)
        lo.addSpacing(18)

        # Botones
        ftr = QHBoxLayout()
        skip = QPushButton(_("Ahora no"))
        skip.setCursor(Qt.CursorShape.PointingHandCursor)
        skip.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {TEXT3}; border: none;
                font-size: {fs(11)}px; padding: 6px 12px; }}
            QPushButton:hover {{ color: {TEXT1}; }}
        """)
        skip.clicked.connect(self.reject)
        ftr.addWidget(skip)
        ftr.addStretch()

        self._send_btn = QPushButton(_("Enviar feedback"))
        self._send_btn.setEnabled(False)
        self._send_btn.setFixedHeight(34)
        self._send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._send_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {ACCENT3}, stop:1 {ACCENT});
                color: #1a1714; border: none;
                border-bottom: 2px solid {ACCENT2};
                border-radius: 2px;
                font-size: {fs(11)}px; font-weight: 700; padding: 0 20px;
            }}
            QPushButton:hover {{ background: {ACCENT3}; }}
            QPushButton:disabled {{ background: {BG3}; color: {TEXT3};
                border-bottom: none; }}
        """)
        self._send_btn.clicked.connect(self._submit)
        ftr.addWidget(self._send_btn)
        lo.addLayout(ftr)

        # ── Página de gracias (oculta hasta que el user envía) ────────────────
        self._thanks_page = QWidget()
        tlo = QVBoxLayout(self._thanks_page)
        tlo.setContentsMargins(28, 40, 28, 44)
        tlo.setSpacing(8)
        tlo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        ck = QLabel("✓")
        ck.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ck.setStyleSheet(f"color:{ACCENT}; font-size:{fs(34)}px; font-weight:700;")
        tlo.addWidget(ck)

        ty = QLabel(_("¡Gracias por tu feedback!"))
        ty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ty.setStyleSheet(f"color:{TEXT0}; font-size:{fs(14)}px; font-weight:600;")
        tlo.addWidget(ty)

        ty2 = QLabel(_("Tu opinión nos ayuda a mejorar PyScout."))
        ty2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ty2.setStyleSheet(f"color:{TEXT2}; font-size:{fs(11)}px;")
        tlo.addWidget(ty2)

        root.addWidget(self._thanks_page)
        self._thanks_page.hide()

    # ── Estrellas ─────────────────────────────────────────────────────────────

    def _star_style(self, active: bool) -> str:
        if active:
            return (
                f"QPushButton {{ background: transparent; color: {ACCENT};"
                f" border: none; font-size: 24px; padding: 0; }}"
                f"QPushButton:hover {{ color: {ACCENT3}; }}"
            )
        return (
            f"QPushButton {{ background: transparent; color: {TEXT3};"
            f" border: none; font-size: 24px; padding: 0; }}"
            f"QPushButton:hover {{ color: {ACCENT}; }}"
        )

    def _set_stars(self, n: int):
        self._stars = n
        for i, btn in enumerate(self._star_btns):
            btn.setStyleSheet(self._star_style(i < n))
        label = _STAR_LABELS.get(n, "")
        self._star_lbl.setText(_(label) if label else "")
        self._send_btn.setEnabled(True)

    # ── Submit ────────────────────────────────────────────────────────────────

    def _submit(self):
        version = ""
        try:
            from PySide6.QtWidgets import QApplication
            version = QApplication.instance().applicationVersion()
        except Exception:
            pass

        comment = self._text.toPlainText().strip()
        local_data = {
            "ts":      datetime.now().isoformat(timespec="seconds"),
            "stars":   self._stars,
            "text":    comment,
            "context": self._context,
            "version": version,
        }

        sent_remote = self._send_to_supabase(self._stars, comment, self._context, version)

        if not sent_remote:
            try:
                path = _docs_root() / "feedback.jsonl"
                with open(path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(local_data, ensure_ascii=False) + "\n")
            except Exception:
                pass

        self._form_page.hide()
        self._thanks_page.show()
        self.adjustSize()
        QTimer.singleShot(1800, self.accept)

    def _send_to_supabase(self, stars: int, comment: str, context: str, version: str) -> bool:
        try:
            import requests
            payload = {
                "stars":       stars,
                "comment":     comment or None,
                "context":     context,
                "app_version": version or None,
            }
            headers = {
                "apikey":        _SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {_SUPABASE_ANON_KEY}",
                "Content-Type":  "application/json",
                "Prefer":        "return=minimal",
            }
            r = requests.post(
                f"{_SUPABASE_URL}/rest/v1/feedback",
                json=payload,
                headers=headers,
                timeout=5,
            )
            return r.status_code in (200, 201)
        except Exception:
            return False


# ── API pública ───────────────────────────────────────────────────────────────

def show_post_render_feedback(parent=None) -> None:
    """Llama esto después de un render exitoso. El dialog aparece 1.2s después."""
    QTimer.singleShot(1200, lambda: _show(parent, "post_render"))


def show_general_feedback(parent=None) -> None:
    """Llama esto desde Ayuda → Feedback."""
    _show(parent, "general")


def _show(parent, context: str) -> None:
    dlg = FeedbackDialog(parent, context=context)
    dlg.exec()
