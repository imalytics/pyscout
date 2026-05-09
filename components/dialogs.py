"""components/dialogs.py — StartDialog arrastrable con licencia integrada + ClipEditDialog"""
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTextEdit, QFrame, QScrollArea, QFileDialog, QMessageBox,
    QWidget, QGraphicsOpacityEffect, QApplication
)
from PySide6.QtCore import (
    Qt, Signal, QUrl, QTimer, QPropertyAnimation, QEasingCurve, QRect, QSettings, QPoint
)
from PySide6.QtGui import QDesktopServices, QColor, QPixmap

from styles.theme import (
    fs, BG0, BG1, BG2, BG3, ACCENT, ACCENT2, ACCENT3,
    TEXT0, TEXT1, TEXT2, TEXT3, BORDER2, CLIP_COLORS
)


# ══════════════════════════════════════════════════════════════════════════════
# ClipEditDialog
# ══════════════════════════════════════════════════════════════════════════════

class ColorDot(QWidget):
    def __init__(self, color, selected=False, parent=None):
        super().__init__(parent)
        self.setFixedSize(24, 24)
        self._color = color
        self._selected = selected
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    def set_selected(self, v):
        self._selected = v; self.update()
    def paintEvent(self, e):
        from PySide6.QtGui import QPainter, QBrush, QPen
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(QColor(self._color)))
        p.setPen(QPen(QColor("white"), 2) if self._selected else Qt.PenStyle.NoPen)
        p.drawEllipse(2, 2, 20, 20)

class ClipEditDialog(QDialog):
    def __init__(self, name, note, color, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editar clip"); self.setFixedWidth(420); self.setModal(True)
        self.setStyleSheet(f"background-color:{BG1}; border-radius:10px;")
        self._color = color; self._dots = []
        lo = QVBoxLayout(self); lo.setContentsMargins(20,20,20,20); lo.setSpacing(14)
        lo.addWidget(QLabel("NOMBRE DEL CLIP", styleSheet=f"color:{TEXT3};font-size:10px;font-weight:600;letter-spacing:0.8px;"))
        self._name_input = QLineEdit(name)
        self._name_input.setStyleSheet(f"background:{BG2};color:#f0f0f0;border:1px solid #333;border-radius:6px;padding:8px 10px;")
        lo.addWidget(self._name_input)
        lo.addWidget(QLabel("COLOR", styleSheet=f"color:{TEXT3};font-size:10px;font-weight:600;letter-spacing:0.8px;"))
        cr = QHBoxLayout(); cr.setSpacing(8)
        for c in CLIP_COLORS:
            dot = ColorDot(c, selected=(c==color))
            dot.mousePressEvent = lambda e, col=c: self._select_color(col)
            cr.addWidget(dot); self._dots.append((c, dot))
        cr.addStretch(); lo.addLayout(cr)
        lo.addWidget(QLabel("NOTA", styleSheet=f"color:{TEXT3};font-size:10px;font-weight:600;letter-spacing:0.8px;"))
        self._note_input = QTextEdit(note); self._note_input.setFixedHeight(80)
        self._note_input.setStyleSheet(f"background:{BG2};color:#f0f0f0;border:1px solid #333;border-radius:6px;padding:8px 10px;")
        self._note_input.setPlaceholderText("Agregar nota..."); lo.addWidget(self._note_input)
        br = QHBoxLayout(); br.addStretch()
        c = QPushButton("Cancelar"); c.setStyleSheet(f"background:{BG2};color:#888;border:1px solid #333;border-radius:6px;padding:7px 16px;")
        c.clicked.connect(self.reject); br.addWidget(c)
        s = QPushButton("Guardar"); s.setObjectName("primary"); s.clicked.connect(self.accept); br.addWidget(s)
        lo.addLayout(br)
    def _select_color(self, color):
        self._color = color
        for c, dot in self._dots: dot.set_selected(c == color)
    @property
    def name(self): return self._name_input.text().strip()
    @property
    def note(self): return self._note_input.toPlainText().strip()
    @property
    def color(self): return self._color


# ══════════════════════════════════════════════════════════════════════════════
# StartDialog — Adobe + Licencia integrada + Arrastrable
# ══════════════════════════════════════════════════════════════════════════════

class StartDialog(QDialog):
    project_selected = Signal(str)
    _connectivity_result = Signal(str)   # HTML para _online_label
    _update_signal = Signal(str, str)    # (version, download_url) cuando hay update

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_project_path = None
        self._drag_pos = None
        self._pending_update_url = ""
        self._update_dl = None
        self._setup_window()
        self._load_license()
        self._build_ui()
        self._update_signal.connect(self._on_update_available)
        self._load_recents()
        self._animate_entrance()
        self._start_tick_timer()
        self._check_connectivity()

    def _setup_window(self):
        self.setWindowTitle("PyScout")
        self.setFixedSize(780, 500)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowMinimizeButtonHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.x() + (screen.width() - self.width()) // 2,
                  screen.y() + (screen.height() - self.height()) // 2)

    def _load_license(self):
        """Cargar estado de licencia — único punto de verdad para todos los flujos."""
        try:
            from utils.license_manager import check_license, get_license_info, get_checkout_url
            self._lic_valid, self._lic_remaining, self._lic_type = check_license()
            self._lic_info = get_license_info()
            self._checkout_url = get_checkout_url()

            # Auto-start trial solo si es realmente primera vez
            if self._lic_type == "no_license":
                from utils.license_manager import start_trial, TRIAL_SECONDS
                start_trial()
                self._lic_valid = True
                self._lic_remaining = TRIAL_SECONDS
                self._lic_type = "trial"
        except ImportError:
            self._lic_valid, self._lic_remaining, self._lic_type = True, 999999, "dev"
            self._lic_info = {}
            self._checkout_url = ""
        except Exception as e:
            print(f"[License] Error: {e}")
            # Estado defensivo: tratar errores raros como corrupto → requiere activación
            self._lic_valid, self._lic_remaining, self._lic_type = False, 0, "corrupted"
            self._lic_info = {}
            self._checkout_url = ""

    def _start_tick_timer(self):
        """Refresco del label cada segundo para trial."""
        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(1000)
        self._tick_timer.timeout.connect(self._tick)
        if self._lic_type in ("trial", "grace"):
            self._tick_timer.start()

    def _tick(self):
        """Decrementa el contador local para mostrar el countdown sin recargar todo."""
        if self._lic_type not in ("trial", "grace"):
            self._tick_timer.stop()
            return
        self._lic_remaining = max(0, self._lic_remaining - 1)
        self._update_license_label()
        # Cuando llega a 0, re-verificar con el manager (por grace period)
        if self._lic_remaining <= 0:
            self._tick_timer.stop()
            self._load_license()
            self._update_license_label()
            self._apply_license_permissions()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._card = QFrame()
        self._card.setObjectName("sc")
        self._card.setStyleSheet(f"""QFrame#sc {{
            background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                stop:0 #0d0d10, stop:0.5 #111116, stop:1 #0d0d10);
            border: 1px solid rgba(201,164,74,0.18); border-radius: 1px; }}""")
        root.addWidget(self._card)
        clo = QVBoxLayout(self._card)
        clo.setContentsMargins(0, 0, 0, 0)
        clo.setSpacing(0)

        # Top accent
        a = QWidget(); a.setFixedHeight(2)
        a.setStyleSheet(f"background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 transparent,stop:0.2 {ACCENT},stop:0.8 {ACCENT},stop:1 transparent);")
        clo.addWidget(a)

        # Header
        hdr = QWidget(); hdr.setFixedHeight(68); hdr.setStyleSheet("background:transparent;")
        hl = QHBoxLayout(hdr); hl.setContentsMargins(28, 12, 28, 12); hl.setSpacing(14)
        self._logo = QLabel(); self._logo.setFixedSize(44, 44); self._logo.setStyleSheet("background:transparent;")
        ip = os.path.join(os.path.dirname(__file__), "ico_4k.png")
        if os.path.exists(ip):
            pm = QPixmap(ip)
            if not pm.isNull():
                self._logo.setPixmap(pm.scaled(44, 44, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self._logo_fx = QGraphicsOpacityEffect(self._logo); self._logo_fx.setOpacity(0); self._logo.setGraphicsEffect(self._logo_fx)
        hl.addWidget(self._logo)

        tc = QVBoxLayout(); tc.setSpacing(1)
        t1 = QLabel("PYSCOUT")
        t1.setStyleSheet(f"color:{ACCENT};font-size:22px;font-weight:700;letter-spacing:4px;background:transparent;")
        tc.addWidget(t1)
        t2 = QLabel("Professional Sports Video Analysis")
        t2.setStyleSheet("color:rgba(255,255,255,0.35);font-size:10px;letter-spacing:2px;background:transparent;")
        tc.addWidget(t2)
        hl.addLayout(tc); hl.addStretch()

        # Minimize / Close buttons en header
        min_btn = QPushButton("–")
        min_btn.setFixedSize(24, 24)
        min_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        min_btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:{TEXT3};border:none;font-size:14px;}}"
            f"QPushButton:hover{{color:{ACCENT};}}")
        min_btn.clicked.connect(self.showMinimized)
        hl.addWidget(min_btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"QPushButton{{background:transparent;color:{TEXT3};border:none;font-size:14px;}}"
            f"QPushButton:hover{{color:#E74C3C;}}")
        close_btn.clicked.connect(self._action_exit)
        hl.addWidget(close_btn)

        clo.addWidget(hdr)
        clo.addWidget(self._sep())

        # Content: 2 columns
        content = QWidget(); content.setStyleSheet("background:transparent;")
        cl = QHBoxLayout(content); cl.setContentsMargins(28, 20, 28, 16); cl.setSpacing(0)

        # Left: actions
        left = QVBoxLayout(); left.setSpacing(8)
        self._new_btn = self._mk_btn("  Nuevo proyecto", True, self._action_new)
        self._open_btn = self._mk_btn("  Abrir proyecto", False, self._action_open)
        left.addWidget(self._new_btn)
        left.addWidget(self._open_btn)
        left.addSpacing(8)
        eb = QPushButton("Salir"); eb.setFixedHeight(30); eb.setCursor(Qt.CursorShape.PointingHandCursor)
        eb.setStyleSheet("QPushButton{background:transparent;border:1px solid rgba(255,255,255,0.08);border-radius:1px;color:rgba(255,255,255,0.3);font-size:11px;padding:0 12px;}"
            "QPushButton:hover{color:rgba(255,255,255,0.6);border-color:rgba(255,255,255,0.15);}")
        eb.clicked.connect(self._action_exit); left.addWidget(eb)
        left.addStretch()
        cl.addLayout(left, stretch=4)

        # Vsep
        sw = QWidget(); sw.setFixedWidth(32); sw.setStyleSheet("background:transparent;")
        sl = QVBoxLayout(sw); sl.setContentsMargins(15,0,15,0)
        vs = QWidget(); vs.setFixedWidth(1)
        vs.setStyleSheet(f"background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 transparent,stop:0.3 rgba(201,164,74,0.15),stop:0.7 rgba(201,164,74,0.15),stop:1 transparent);")
        sl.addWidget(vs); cl.addWidget(sw)

        # Right: recents
        right = QVBoxLayout(); right.setSpacing(10)
        r_hdr = QLabel("RECIENTES")
        r_hdr.setStyleSheet("color:rgba(201,164,74,0.6);font-size:9px;font-weight:700;letter-spacing:3px;background:transparent;")
        right.addWidget(r_hdr)
        self._scroll = QScrollArea(); self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}QScrollBar:vertical{background:transparent;width:4px;}QScrollBar::handle:vertical{background:rgba(201,164,74,0.2);min-height:20px;}QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}")
        self._recents_widget = QWidget(); self._recents_widget.setStyleSheet("background:transparent;")
        self._recents_lo = QVBoxLayout(self._recents_widget)
        self._recents_lo.setContentsMargins(0, 0, 4, 0); self._recents_lo.setSpacing(2)
        self._scroll.setWidget(self._recents_widget)
        right.addWidget(self._scroll)
        cl.addLayout(right, stretch=5)
        clo.addWidget(content, stretch=1)

        # License bar
        clo.addWidget(self._sep())
        self._build_license_bar(clo)

    def _sep(self):
        s = QWidget(); s.setFixedHeight(1); s.setStyleSheet("background:rgba(255,255,255,0.06);"); return s

    def _mk_btn(self, text, primary, cb):
        b = QPushButton(text); b.setFixedHeight(42); b.setCursor(Qt.CursorShape.PointingHandCursor)
        if primary:
            b.setStyleSheet(f"QPushButton{{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 rgba(201,164,74,0.15),stop:1 rgba(201,164,74,0.05));border:1px solid rgba(201,164,74,0.35);border-left:3px solid {ACCENT};border-radius:1px;color:{ACCENT};font-size:13px;font-weight:600;padding:0 16px;text-align:left;}}QPushButton:hover{{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 rgba(201,164,74,0.25),stop:1 rgba(201,164,74,0.10));border-color:{ACCENT};}}QPushButton:disabled{{color:{TEXT3};border-color:{BORDER2};background:transparent;}}")
        else:
            b.setStyleSheet(f"QPushButton{{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 rgba(255,255,255,0.04),stop:1 rgba(255,255,255,0.01));border:1px solid rgba(255,255,255,0.10);border-left:3px solid rgba(255,255,255,0.25);border-radius:1px;color:{TEXT1};font-size:13px;font-weight:500;padding:0 16px;text-align:left;}}QPushButton:hover{{background:rgba(255,255,255,0.06);border-left-color:{ACCENT};color:{TEXT0};}}QPushButton:disabled{{color:{TEXT3};border-color:{BORDER2};background:transparent;}}")
        b.clicked.connect(cb); return b

    def _load_recents(self):
        """Cargar proyectos recientes desde QSettings."""
        # Limpiar
        while self._recents_lo.count():
            it = self._recents_lo.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

        settings = QSettings("ScoutApp", "prefs")
        recents = settings.value("recent_projects", [])
        if not isinstance(recents, list):
            recents = []

        # Filtrar archivos que existen
        valid_recents = [p for p in recents if isinstance(p, str) and os.path.exists(p)]

        if not valid_recents:
            e = QLabel("Sin proyectos recientes")
            e.setAlignment(Qt.AlignmentFlag.AlignCenter)
            e.setFixedHeight(80)
            e.setStyleSheet("color:rgba(255,255,255,0.15);font-size:11px;font-style:italic;background:transparent;")
            self._recents_lo.addWidget(e)
        else:
            for i, p in enumerate(valid_recents[:8]):
                self._recents_lo.addWidget(self._mk_recent(p, i))
        self._recents_lo.addStretch()

    def _mk_recent(self, path, idx):
        """Crear fila de reciente — QPushButton con labels transparentes al mouse."""
        row = QPushButton()
        row.setFixedHeight(34)
        row.setCursor(Qt.CursorShape.PointingHandCursor)

        rlo = QHBoxLayout(row)
        rlo.setContentsMargins(10, 0, 8, 0)
        rlo.setSpacing(8)

        # Number
        num = QLabel(f"{idx + 1}")
        num.setFixedWidth(14)
        num.setAlignment(Qt.AlignmentFlag.AlignCenter)
        num.setStyleSheet("color:rgba(201,164,74,0.3);font-size:9px;font-weight:600;background:transparent;")
        num.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        rlo.addWidget(num)

        # Name
        name = os.path.basename(path)
        for ext in ('.scproj', '.scout'):
            if name.endswith(ext):
                name = name[:-len(ext)]
                break
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(f"color:{TEXT1};font-size:12px;font-weight:500;background:transparent;")
        name_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        rlo.addWidget(name_lbl, stretch=1)

        # Path hint
        dp = os.path.dirname(path)
        if len(dp) > 30:
            dp = "..." + dp[-27:]
        dir_lbl = QLabel(dp)
        dir_lbl.setStyleSheet("color:rgba(255,255,255,0.15);font-size:9px;background:transparent;")
        dir_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        rlo.addWidget(dir_lbl)

        row.setStyleSheet(
            "QPushButton{background:transparent;border:none;border-left:2px solid transparent;border-radius:0;text-align:left;}"
            "QPushButton:hover{background:rgba(201,164,74,0.05);border-left:2px solid rgba(201,164,74,0.4);}"
            "QPushButton:disabled{color:#555;}"
        )
        # clicked.connect con bind explícito (la señal pasa un bool "checked")
        row.clicked.connect(lambda checked=False, p=path: self._action_open_recent(p))

        if not self._lic_valid and self._lic_type != "dev":
            row.setEnabled(False)
        return row

    def _apply_license_permissions(self):
        """Aplica el estado de licencia a todos los botones. Se llama tras cada cambio."""
        can_work = self._lic_valid or self._lic_type == "dev"
        self._new_btn.setEnabled(can_work)
        self._open_btn.setEnabled(can_work)
        # Re-enable/disable recents
        for i in range(self._recents_lo.count()):
            w = self._recents_lo.itemAt(i).widget()
            if isinstance(w, QPushButton):
                w.setEnabled(can_work)
        # License bar buttons
        if self._lic_type in ("pro", "pro_offline"):
            self._show_key_btn.setVisible(False)
            self._buy_btn.setVisible(False)
        elif self._lic_type == "dev":
            self._show_key_btn.setVisible(False)
            self._buy_btn.setVisible(False)
        else:
            self._show_key_btn.setVisible(True)
            self._buy_btn.setVisible(True)

    # ── License bar ───────────────────────────────────────────────────────

    def _build_license_bar(self, parent_lo):
        bar = QWidget(); bar.setFixedHeight(44)
        bar.setStyleSheet("background:rgba(0,0,0,0.3);")
        bl = QHBoxLayout(bar); bl.setContentsMargins(28, 0, 28, 0); bl.setSpacing(10)

        self._lic_label = QLabel()
        self._lic_label.setStyleSheet("background:transparent;")
        self._update_license_label()
        bl.addWidget(self._lic_label)

        self._online_label = QLabel()
        self._online_label.setStyleSheet("background:transparent;")
        self._connectivity_result.connect(self._online_label.setText)
        bl.addWidget(self._online_label)

        self._update_btn = QPushButton("⬇ Actualizar")
        self._update_btn.setFixedHeight(28)
        self._update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_btn.setStyleSheet(
            f"QPushButton{{background:{ACCENT};color:#1a1714;border:none;"
            f"font-size:11px;font-weight:700;padding:0 14px;border-radius:1px;}}"
            f"QPushButton:hover{{background:{ACCENT3};}}"
            f"QPushButton:disabled{{background:{BG3};color:{TEXT3};}}")
        self._update_btn.clicked.connect(self._do_update)
        self._update_btn.setVisible(False)
        bl.addWidget(self._update_btn)

        bl.addStretch()

        self._key_input = QLineEdit()
        self._key_input.setFixedSize(240, 28)
        self._key_input.setPlaceholderText("Pegar clave de licencia...")
        self._key_input.setStyleSheet(f"background:{BG2};color:{TEXT0};border:1px solid {BORDER2};font-size:11px;padding:0 8px;border-radius:1px;")
        self._key_input.returnPressed.connect(self._do_activate)
        self._key_input.setVisible(False)
        bl.addWidget(self._key_input)

        self._act_btn = QPushButton("Activar")
        self._act_btn.setFixedSize(60, 28)
        self._act_btn.setStyleSheet(f"QPushButton{{background:{ACCENT};color:#1a1714;border:none;font-size:11px;font-weight:600;border-radius:1px;}}QPushButton:hover{{background:{ACCENT3};}}QPushButton:disabled{{background:{BG3};color:{TEXT3};}}")
        self._act_btn.clicked.connect(self._do_activate)
        self._act_btn.setVisible(False)
        bl.addWidget(self._act_btn)

        self._cancel_key = QPushButton("✕")
        self._cancel_key.setFixedSize(28, 28)
        self._cancel_key.setStyleSheet(f"QPushButton{{background:transparent;color:{TEXT3};border:1px solid {BORDER2};font-size:11px;border-radius:1px;}}QPushButton:hover{{color:{TEXT0};}}")
        self._cancel_key.clicked.connect(self._hide_key)
        self._cancel_key.setVisible(False)
        bl.addWidget(self._cancel_key)

        self._show_key_btn = QPushButton("Activar licencia")
        self._show_key_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._show_key_btn.setStyleSheet(f"QPushButton{{background:transparent;color:{ACCENT};border:1px solid rgba(201,164,74,0.3);font-size:11px;padding:4px 12px;border-radius:1px;}}QPushButton:hover{{border-color:{ACCENT};color:{ACCENT3};}}")
        self._show_key_btn.clicked.connect(self._show_key)
        bl.addWidget(self._show_key_btn)

        self._buy_btn = QPushButton("Comprar")
        self._buy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._buy_btn.setStyleSheet(f"QPushButton{{background:transparent;color:{TEXT2};border:1px solid {BORDER2};font-size:11px;padding:4px 12px;border-radius:1px;}}QPushButton:hover{{color:{ACCENT};border-color:{ACCENT};}}")
        self._buy_btn.clicked.connect(self._open_buy)
        bl.addWidget(self._buy_btn)

        parent_lo.addWidget(bar)
        self._apply_license_permissions()

    def _update_license_label(self):
        t = self._lic_type
        r = self._lic_remaining
        if t == "pro":
            dot, text = "#27AE60", "Licencia activa"
        elif t == "pro_offline":
            hours = max(1, r // 3600)
            dot, text = "#E67E22", f"Pro (offline) — {hours}h de gracia"
        elif t == "trial":
            if r > 86400:
                days = r // 86400
                dot = ACCENT if days > 7 else "#E67E22" if days > 3 else "#E74C3C"
                text = f"Prueba: {days} días restantes"
            elif r > 3600:
                hours = r // 3600
                dot = "#E67E22"
                text = f"Prueba: {hours}h restantes"
            elif r > 60:
                mins = r // 60
                dot = "#E74C3C"
                text = f"Prueba: {mins}min restantes"
            else:
                dot = "#E74C3C"
                text = f"Prueba: {r}s restantes"
        elif t == "grace":
            dot, text = "#E67E22", "Período de gracia — activá tu licencia"
        elif t == "dev":
            dot, text = "#3498DB", "Modo desarrollo"
        elif t == "expired":
            dot, text = "#E74C3C", "Prueba expirada — activá tu licencia"
        elif t == "wrong_pc":
            dot, text = "#E74C3C", "Licencia de otro equipo"
        elif t == "tampered":
            dot, text = "#E74C3C", "Reloj del sistema manipulado"
        elif t == "corrupted":
            dot, text = "#E74C3C", "Archivo de licencia dañado"
        else:
            dot, text = "#E74C3C", "Sin licencia"

        self._lic_label.setText(
            f'<span style="color:{dot};font-size:11px;">●</span>'
            f' <span style="color:rgba(255,255,255,0.7);font-size:11px;">{text}</span>')

    def _show_key(self):
        self._key_input.setVisible(True); self._act_btn.setVisible(True); self._cancel_key.setVisible(True)
        self._show_key_btn.setVisible(False); self._buy_btn.setVisible(False)
        self._key_input.setFocus()

    def _hide_key(self):
        self._key_input.setVisible(False); self._act_btn.setVisible(False); self._cancel_key.setVisible(False)
        self._key_input.clear()
        if self._lic_type not in ("pro", "pro_offline", "dev"):
            self._show_key_btn.setVisible(True)
            self._buy_btn.setVisible(True)

    def _do_activate(self):
        key = self._key_input.text().strip()
        if not key:
            QMessageBox.warning(self, "Clave vacía", "Pegá una clave de licencia válida.")
            return
        # Deshabilitar mientras procesa
        self._act_btn.setEnabled(False)
        self._act_btn.setText("...")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            from utils.license_manager import activate_license
            ok, msg = activate_license(key)
        except ImportError:
            ok, msg = False, "Sistema de licencias no disponible"
        except Exception as e:
            ok, msg = False, f"Error: {e}"
        finally:
            QApplication.restoreOverrideCursor()
            self._act_btn.setEnabled(True)
            self._act_btn.setText("Activar")

        if ok:
            QMessageBox.information(self, "Activado", msg)
            # Recargar estado desde disco
            self._load_license()
            self._update_license_label()
            self._hide_key()
            self._apply_license_permissions()
            # Parar el timer si ya está en pro o pro_offline
            if self._lic_type in ("pro", "pro_offline") and self._tick_timer.isActive():
                self._tick_timer.stop()
        else:
            QMessageBox.warning(self, "Error", msg)

    def _open_buy(self):
        url = self._checkout_url or "https://polar.sh"
        QDesktopServices.openUrl(QUrl(url))

    # ── Actions ───────────────────────────────────────────────────────────

    def _guard_license(self) -> bool:
        """Verifica si hay licencia válida antes de permitir acción."""
        if self._lic_valid or self._lic_type == "dev":
            return True
        msgs = {
            "expired": "Tu período de prueba expiró. Activá una licencia para continuar.",
            "wrong_pc": "Esta licencia pertenece a otro equipo.",
            "tampered": "Se detectó una manipulación del reloj del sistema.",
            "corrupted": "El archivo de licencia está dañado. Activá una licencia.",
        }
        QMessageBox.warning(self, "Licencia requerida",
            msgs.get(self._lic_type, "Activá tu licencia para continuar."))
        return False

    def _action_new(self):
        if not self._guard_license(): return

        # Modal no-cerrable para nombre del proyecto
        dlg = QDialog(self)
        dlg.setWindowTitle("Nuevo proyecto")
        dlg.setFixedSize(380, 160)
        dlg.setModal(True)
        # Sin botón de cerrar
        dlg.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        dlg.setStyleSheet(f"background:{BG0}; color:{TEXT0};")

        lo = QVBoxLayout(dlg)
        lo.setContentsMargins(24, 20, 24, 16)
        lo.setSpacing(12)

        lo.addWidget(QLabel("NOMBRE DEL PROYECTO",
            styleSheet=f"color:{ACCENT};font-size:9px;font-weight:700;letter-spacing:1.5px;background:transparent;"))

        name_input = QLineEdit()
        name_input.setPlaceholderText("Ej: Semifinal Liga Nacional...")
        name_input.setStyleSheet(f"background:{BG2};color:{TEXT0};border:none;"
            f"border-bottom:2px solid {BORDER2};font-size:14px;padding:8px 10px;")
        lo.addWidget(name_input)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel = QPushButton("Cancelar")
        cancel.setStyleSheet(f"QPushButton{{background:transparent;color:{TEXT3};"
            f"border:1px solid {BORDER2};padding:7px 16px;font-size:12px;border-radius:1px;}}"
            f"QPushButton:hover{{color:{TEXT0};border-color:rgba(255,255,255,0.2);}}")
        cancel.clicked.connect(dlg.reject)
        btn_row.addWidget(cancel)

        crear = QPushButton("Crear")
        crear.setStyleSheet(f"QPushButton{{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            f"stop:0 {ACCENT3},stop:1 {ACCENT});color:#1a1714;border:none;"
            f"border-bottom:2px solid {ACCENT2};padding:7px 24px;"
            f"font-size:13px;font-weight:600;border-radius:1px;}}"
            f"QPushButton:hover{{background:{ACCENT3};}}")

        def do_create():
            n = name_input.text().strip()
            if not n:
                name_input.setStyleSheet(f"background:{BG2};color:{TEXT0};border:none;"
                    f"border-bottom:2px solid #E74C3C;font-size:14px;padding:8px 10px;")
                return
            dlg.accept()

        crear.clicked.connect(do_create)
        name_input.returnPressed.connect(do_create)
        btn_row.addWidget(crear)
        lo.addLayout(btn_row)

        name_input.setFocus()

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        project_name = name_input.text().strip()

        # Guardar en Documentos/PyScout/Proyectos/
        import os
        if os.name == "nt":
            docs = os.path.expanduser("~/Documents")
        else:
            docs = os.path.join(os.path.expanduser("~"), "Documents")
        projects_dir = os.path.join(docs, "PyScout", "Proyectos")
        os.makedirs(projects_dir, exist_ok=True)

        # Sanitizar nombre para filename
        safe_name = "".join(c for c in project_name if c.isalnum() or c in " _-().").strip()
        if not safe_name:
            safe_name = "Proyecto"
        path = os.path.join(projects_dir, f"{safe_name}.scout")

        # Si ya existe, agregar número
        base = path
        counter = 1
        while os.path.exists(path):
            path = base.replace(".scout", f" ({counter}).scout")
            counter += 1

        self.selected_project_path = path
        self.project_selected.emit(path)
        self.accept()

    def _action_open(self):
        if not self._guard_license(): return
        path, _ = QFileDialog.getOpenFileName(self, "Abrir proyecto", "",
            "PyScout Project (*.scproj);;Scout Project (*.scout);;All (*)")
        if path:
            self.selected_project_path = path
            self.project_selected.emit(path)
            self.accept()

    def _action_open_recent(self, path):
        if not self._guard_license(): return
        if os.path.exists(path):
            self.selected_project_path = path
            self.project_selected.emit(path)
            self.accept()
        else:
            QMessageBox.warning(self, "No encontrado", f"El archivo no existe:\n{path}")
            # Removerlo de recientes
            settings = QSettings("ScoutApp", "prefs")
            recents = settings.value("recent_projects", [])
            if isinstance(recents, list) and path in recents:
                recents.remove(path)
                settings.setValue("recent_projects", recents)
                self._load_recents()

    def _action_exit(self):
        QApplication.quit()

    # ── Connectivity check ────────────────────────────────────────────────

    def _check_connectivity(self):
        import threading
        def _bg():
            online = False
            try:
                import requests
                r = requests.get("https://api.polar.sh", timeout=3)
                online = r.status_code < 500
            except Exception:
                pass

            if online:
                try:
                    from utils.updater import UpdateChecker, CURRENT_VERSION, UPDATE_URL
                    import requests
                    r = requests.get(UPDATE_URL, timeout=5)
                    data = r.json()
                    latest = data.get("version", CURRENT_VERSION)
                    download_url = data.get("download_url", "")
                    if UpdateChecker._is_newer(latest, CURRENT_VERSION) and download_url:
                        self._connectivity_result.emit(
                            f'<span style="color:#27AE60;">●</span>'
                            f' <span style="color:rgba(255,255,255,0.4);">'
                            f'v{latest} disponible</span>')
                        self._update_signal.emit(latest, download_url)
                    else:
                        self._connectivity_result.emit(
                            f'<span style="color:#27AE60;">●</span>'
                            f' <span style="color:rgba(255,255,255,0.25);">Online</span>')
                except Exception:
                    self._connectivity_result.emit(
                        f'<span style="color:#27AE60;">●</span>'
                        f' <span style="color:rgba(255,255,255,0.25);">Online</span>')
            else:
                grace_text = "Offline"
                if self._lic_type in ("pro", "pro_offline") and self._lic_info:
                    last_val = self._lic_info.get("last_validate", "")
                    if last_val:
                        try:
                            import datetime
                            last = datetime.datetime.fromisoformat(last_val)
                            elapsed = datetime.datetime.now() - last
                            remaining_h = max(0, 48 - int(elapsed.total_seconds() / 3600))
                            if remaining_h > 0:
                                grace_text = f"Offline — {remaining_h}h de gracia"
                            else:
                                grace_text = "Offline — gracia expirada"
                        except Exception:
                            pass
                self._connectivity_result.emit(
                    f'<span style="color:#E67E22;">●</span>'
                    f' <span style="color:rgba(255,255,255,0.4);">'
                    f'{grace_text}</span>')

        threading.Thread(target=_bg, daemon=True).start()

    def _on_update_available(self, version: str, download_url: str):
        self._pending_update_url = download_url
        self._pending_update_version = version
        self._update_btn.setText(f"⬇  Actualizar a v{version}")
        self._update_btn.setVisible(True)

    def _do_update(self):
        if not self._pending_update_url:
            return
        self._update_btn.setEnabled(False)
        self._update_btn.setText("Descargando...")
        from utils.updater import UpdateDownloader
        self._update_dl = UpdateDownloader(self._pending_update_url)
        self._update_dl.progress.connect(self._on_dl_progress)
        self._update_dl.finished.connect(self._on_dl_finished)
        self._update_dl.failed.connect(self._on_dl_failed)
        self._update_dl.start()

    def _on_dl_progress(self, done: int, total: int):
        if total > 0:
            pct = int(done * 100 / total)
            self._update_btn.setText(f"Descargando {pct}%")
        else:
            mb = done / 1_048_576
            self._update_btn.setText(f"Descargando {mb:.1f} MB")

    def _on_dl_finished(self, path: str):
        self._update_btn.setText("Instalando...")
        from utils.updater import apply_update
        QTimer.singleShot(300, lambda: apply_update(path))

    def _on_dl_failed(self, error: str):
        v = getattr(self, "_pending_update_version", "")
        self._update_btn.setText(f"⬇  Actualizar a v{v}" if v else "⬇  Actualizar")
        self._update_btn.setEnabled(True)
        QMessageBox.warning(self, "Error de actualización",
            f"No se pudo descargar la actualización.\n\n{error}")

    # ── Drag window ───────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        """Permitir arrastrar la ventana desde cualquier zona no-interactiva."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()

    # ── Animation ─────────────────────────────────────────────────────────

    def _animate_entrance(self):
        geo = self.geometry(); self.setWindowOpacity(0)
        self._a1 = QPropertyAnimation(self, b"windowOpacity")
        self._a1.setDuration(350); self._a1.setStartValue(0.0); self._a1.setEndValue(1.0)
        self._a1.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._a2 = QPropertyAnimation(self, b"geometry")
        self._a2.setDuration(350)
        self._a2.setStartValue(QRect(geo.x(), geo.y()+20, geo.width(), geo.height()))
        self._a2.setEndValue(geo)
        self._a2.setEasingCurve(QEasingCurve.Type.OutCubic)
        QTimer.singleShot(30, lambda: (self._a1.start(), self._a2.start()))
        self._a3 = QPropertyAnimation(self._logo_fx, b"opacity")
        self._a3.setDuration(500); self._a3.setStartValue(0.0); self._a3.setEndValue(1.0)
        self._a3.setEasingCurve(QEasingCurve.Type.OutCubic)
        QTimer.singleShot(250, self._a3.start)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape: self.reject()
        else: super().keyPressEvent(e)

    def closeEvent(self, event):
        if hasattr(self, '_tick_timer'):
            self._tick_timer.stop()
        super().closeEvent(event)