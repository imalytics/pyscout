import warnings

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QSizePolicy, QDialog, QSpinBox,
    QLineEdit, QFileDialog, QApplication, QMenu, QMessageBox
)
from PySide6.QtCore import Qt, QSize, QThread, Signal as _Signal
from PySide6.QtGui import QKeyEvent, QAction

from components.video_player import MpvWidget
from components.timeline import ScrubBar
from components.dialogs import ClipEditDialog
from store.state import state, Clip, Button
from utils.theme_helpers import BG0, BG1, BG2, BG3, BG4, ACCENT, ACCENT2, ACCENT3, TEXT0, TEXT1, TEXT2, TEXT3, BORDER, BORDER2
from styles.theme import CLIP_COLORS, fs, fs
from utils.time_utils import fmt_time
from utils.i18n import _
from icons_helper import play_icon, pause_icon, mute_icon, volume_icon, fullscreen_icon, plus_icon, settings_icon


def _make_svg_placeholder(svg_bytes: bytes, text: str, font_size_px) -> QWidget:
    """Widget de estado vacío con ícono SVG + texto descriptivo."""
    from PySide6.QtCore import QByteArray
    container = QWidget()
    container.setStyleSheet("background:transparent;")
    lo = QVBoxLayout(container)
    lo.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lo.setSpacing(10)
    lo.setContentsMargins(16, 24, 16, 20)
    icon_lbl = QLabel()
    icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_lbl.setStyleSheet("background:transparent; border:none;")
    try:
        from PySide6.QtSvg import QSvgRenderer
        from PySide6.QtGui import QPainter, QPixmap
        renderer = QSvgRenderer(QByteArray(svg_bytes))
        pm = QPixmap(36, 36)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        renderer.render(p)
        p.end()
        icon_lbl.setPixmap(pm)
    except Exception:
        pass
    lo.addWidget(icon_lbl)
    txt = QLabel(text)
    txt.setAlignment(Qt.AlignmentFlag.AlignCenter)
    txt.setWordWrap(True)
    txt.setStyleSheet(
        f"color:#3E3C3A; font-size:{font_size_px}px;"
        f" background:transparent; border:none;"
    )
    lo.addWidget(txt)
    return container


class AddButtonDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Nuevo botón"))
        self.setFixedWidth(340)
        self.setModal(True)
        from utils.theme_helpers import BG1, BG2, ACCENT, TEXT0, TEXT3, ACCENT2
        self.setStyleSheet(f"background:{BG1}; color:{TEXT0};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        lbl = QLabel(_("NOMBRE DEL BOTÓN"))
        lbl.setStyleSheet(f"color:{TEXT3}; font-size:{fs(10)}px; font-weight:600; letter-spacing:1px;")
        layout.addWidget(lbl)

        self._input = QLineEdit()
        self._input.setMaxLength(18)
        self._input.setPlaceholderText(_("Ej: PNR, Poste bajo, Transición..."))
        self._input.returnPressed.connect(self._create_another)
        layout.addWidget(self._input)

        hint = QLabel(_("Enter = Crear otro"))
        hint.setStyleSheet(f"color:{TEXT3}; font-size:{fs(10)}px;")
        layout.addWidget(hint)

        btns = QHBoxLayout()
        done_btn = QPushButton(_("Listo"))
        done_btn.setObjectName("primary")
        done_btn.setStyleSheet(
            f"QPushButton {{ background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            f"stop:0 {ACCENT3},stop:1 {ACCENT}); color:#1a1714; border:none;"
            f" border-bottom:2px solid {ACCENT2}; border-radius:2px;"
            f" padding:6px 18px; font-size:{fs(12)}px; font-weight:600; }}"
            f"QPushButton:hover {{ background:{ACCENT3}; }}"
            f"QPushButton:pressed {{ border-bottom:none; padding-top:8px; }}"
        )
        done_btn.clicked.connect(self._finish)
        create_btn = QPushButton(_("Crear otro"))
        create_btn.clicked.connect(self._create_another)
        btns.addStretch()
        btns.addWidget(create_btn)
        btns.addWidget(done_btn)
        layout.addLayout(btns)

    def _create_another(self):
        name = self._input.text().strip()
        if name:
            state.add_button(name, "#1c1c1c")
            self._input.clear()
            self._input.setFocus()

    def _finish(self):
        name = self._input.text().strip()
        if name:
            state.add_button(name, "#1c1c1c")
        self.accept()

    def showEvent(self, e):
        super().showEvent(e)
        self._input.setFocus()
        # Disable all app shortcuts while typing in this dialog
        QApplication.instance().installEventFilter(self)

    def hideEvent(self, e):
        super().hideEvent(e)
        QApplication.instance().removeEventFilter(self)

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        from PySide6.QtWidgets import QWidget
        # Block all key events from reaching shortcuts while modal is open
        if event.type() in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease, QEvent.Type.ShortcutOverride):
            # Solo verificar si obj es un QWidget (no QWindow)
            if isinstance(obj, QWidget) and obj is not self and not self.isAncestorOf(obj):
                return True
        return False


class _ClipExportThread(QThread):
    done = _Signal(bool, str)

    def __init__(self, clip_dict: dict, output_path: str,
                 crf: int = 20, fps: int = 30,
                 mute_audio: bool = False,
                 show_overlay: bool = False,
                 clip_name: str = ""):
        super().__init__()
        self._clip         = clip_dict
        self._path         = output_path
        self._crf          = crf
        self._fps          = fps
        self._mute_audio   = mute_audio
        self._show_overlay = show_overlay
        self._clip_name    = clip_name

    def run(self):
        try:
            from utils.ffmpeg import export_clip
            ok = export_clip(
                self._clip, self._path,
                crf=self._crf, fps=self._fps,
                mute_audio=self._mute_audio,
                show_overlay=self._show_overlay,
                clip_name=self._clip_name,
            )
            self.done.emit(ok, self._path if ok else "")
        except Exception as ex:
            self.done.emit(False, str(ex)[:200])


class ObservationScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._btn_widgets     = {}
        self._clip_widgets    = {}
        self._clip_pres_state = {}  # {clip_id: in_presentation} para detectar cambios
        self._tab_widgets  = []
        self._muted        = False
        self._speeds       = [0.25, 0.5, 1.0, 1.5, 2.0]
        self._speed_idx    = 2
        self._build_ui()
        self._connect_state()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        from PySide6.QtWidgets import QSplitter

        # ── Splitter principal: sidebar | video+registros ─────────────────────
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setHandleWidth(1)
        self._splitter.setStyleSheet(f"QSplitter::handle {{ background: rgba(255,255,255,0.06); }}")

        # ── Sidebar izquierdo ─────────────────────────────────────────────────
        left = QWidget()
        left.setObjectName("sidebar_left")
        left.setMinimumWidth(180)
        left.setMaximumWidth(400)
        left.setStyleSheet(f"""
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 {BG0}, stop:1 {BG1});
            border-right:1px solid rgba(255,255,255,0.06);
        """)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────────
        hdr = QWidget()
        hdr.setFixedHeight(46)
        hdr.setStyleSheet(f"background:transparent; border:none;")
        hh = QHBoxLayout(hdr)
        hh.setContentsMargins(16, 0, 10, 0)
        hh.setSpacing(0)
        hh.addWidget(QLabel(_("BOTONES"), styleSheet=f"""
                color: {ACCENT};
                font-size: {fs(10)}px;
                font-weight: 700;
                letter-spacing: 2px;
            """))
        hh.addStretch()

        _btn_ss = f"""
            QPushButton {{
                background: transparent;
                border: 1px solid {TEXT3};
                border-radius: 2px;
                padding: 0;
            }}
            QPushButton:hover {{
                border-color: {ACCENT};
                background: rgba(201,164,74,0.08);
            }}
            QPushButton:pressed {{
                background: rgba(201,164,74,0.15);
            }}
        """
        add_btn = QPushButton()
        add_btn.setFixedSize(26, 26)
        add_btn.setIcon(plus_icon(size=(12, 12), color=str(TEXT2)))
        add_btn.setIconSize(QSize(12, 12))
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setToolTip(_("Nuevo botón"))
        add_btn.setStyleSheet(_btn_ss)
        add_btn.enterEvent = lambda e, b=add_btn: b.setIcon(plus_icon(size=(12, 12), color=str(ACCENT)))
        add_btn.leaveEvent = lambda e, b=add_btn: b.setIcon(plus_icon(size=(12, 12), color=str(TEXT2)))
        add_btn.clicked.connect(self._show_add_modal)
        self._add_btn = add_btn
        hh.addWidget(add_btn)
        hh.addSpacing(4)

        cfg_btn = QPushButton()
        cfg_btn.setFixedSize(26, 26)
        cfg_btn.setIcon(settings_icon(size=(13, 13), color=str(TEXT2)))
        cfg_btn.setIconSize(QSize(13, 13))
        cfg_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cfg_btn.setToolTip(_("Configurar botones"))
        cfg_btn.setStyleSheet(_btn_ss)
        cfg_btn.enterEvent = lambda e, b=cfg_btn: b.setIcon(settings_icon(size=(13, 13), color=str(ACCENT)))
        cfg_btn.leaveEvent = lambda e, b=cfg_btn: b.setIcon(settings_icon(size=(13, 13), color=str(TEXT2)))
        cfg_btn.clicked.connect(self._show_btn_config)
        hh.addWidget(cfg_btn)
        ll.addWidget(hdr)

        # Separador fino
        hdr_sep = QFrame()
        hdr_sep.setFixedHeight(1)
        hdr_sep.setStyleSheet(f"background:rgba(255,255,255,0.06);")
        ll.addWidget(hdr_sep)

        # ── Scroll de botones ─────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background:transparent;")
        self._btn_container = QWidget()
        self._btn_container.setStyleSheet("background:transparent;")
        self._btn_layout = QVBoxLayout(self._btn_container)
        self._btn_layout.setContentsMargins(10, 8, 10, 8)
        self._btn_layout.setSpacing(3)
        self._btn_layout.addStretch()
        scroll.setWidget(self._btn_container)
        ll.addWidget(scroll, stretch=1)

        self._btn_empty = _make_svg_placeholder(
            b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"'
            b' stroke="#3E3C3A" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
            b'<rect x="2" y="6" width="20" height="13" rx="3"/>'
            b'<line x1="12" y1="10" x2="12" y2="15"/>'
            b'<line x1="9.5" y1="12.5" x2="14.5" y2="12.5"/>'
            b'</svg>',
            _("Creá tu primer botón\ncon el  +  de arriba"),
            fs(11)
        )
        self._btn_empty.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_empty.mousePressEvent = lambda e: self._show_add_modal()
        self._btn_layout.insertWidget(0, self._btn_empty)

        # left se agrega al splitter más abajo

        # ── Panel derecho ─────────────────────────────────────────────────────
        right = QWidget()

        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)

        right_vsplit = QSplitter(Qt.Orientation.Vertical)
        right_vsplit.setHandleWidth(1)
        right_vsplit.setStyleSheet(f"QSplitter::handle {{ background: rgba(255,255,255,0.06); }}")
        rl.addWidget(right_vsplit)

        top_right = QWidget()
        trl = QVBoxLayout(top_right)
        trl.setContentsMargins(0, 0, 0, 0)
        trl.setSpacing(0)

        bot_right = QWidget()
        bot_right.setMinimumHeight(80)
        brl = QVBoxLayout(bot_right)
        brl.setContentsMargins(0, 0, 0, 0)
        brl.setSpacing(0)

        # Tab bar
        self._tab_bar = QWidget()
        self._tab_bar.setObjectName("tab_bar_widget")
        self._tab_bar.setFixedHeight(max(33, fs(28)))
        self._tab_bar.setStyleSheet(f"background:{BG1}; border-bottom:1px solid rgba(255,255,255,0.06);")
        self._tab_bar_layout = QHBoxLayout(self._tab_bar)
        self._tab_bar_layout.setContentsMargins(0, 0, 0, 0)
        self._tab_bar_layout.setSpacing(0)
        self._tab_bar_layout.addStretch()

        self._add_src_btn = QPushButton("+")
        self._add_src_btn.setFixedSize(32, 32)
        self._add_src_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {TEXT3};
                border: none;
                border-top: 2px solid transparent;
                font-size: {fs(20)}px;
                font-weight: 300;
                padding: 0;
            }}
            QPushButton:hover {{
                color: {ACCENT3};
                border-top: 2px solid {ACCENT3};
                background: rgba(255,255,255,0.03);
            }}
        """)
        self._add_src_btn.setToolTip(_("Agregar video fuente"))
        self._add_src_btn.clicked.connect(self._open_video)
        self._tab_bar_layout.addWidget(self._add_src_btn)
        trl.addWidget(self._tab_bar)

        # Video
        self._video = MpvWidget()
        self._video.duration_changed.connect(lambda d: self._scrub_bar.set_duration(d))
        self._video.position_changed.connect(self._on_position)
        self._video.playback_started.connect(
            lambda: self._play_btn.setIcon(pause_icon(size=(18, 18), color="#1a1714"))
        )
        self._video.playback_paused.connect(
            lambda: self._play_btn.setIcon(play_icon(size=(18, 18), color="#1a1714"))
        )

        self._placeholder = QWidget()
        
        ph = QVBoxLayout(self._placeholder)
        ph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        folder_btn = QPushButton("🗂")
        folder_btn.setFlat(True)
        folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        folder_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; border:none;"
            f" font-family:'Segoe UI Emoji','Noto Color Emoji',sans-serif;"
            f" font-size:{fs(52)}px; padding:0; }}"
            f"QPushButton:hover {{ background:transparent; }}"
        )
        folder_btn.clicked.connect(self._open_video)
        ph.addWidget(folder_btn)
        load_btn = QPushButton(_("Agregar video fuente"))
        load_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; color:{ACCENT}; border:none;"
            f" border-bottom:1px solid {ACCENT}; font-size:{fs(14)}px; font-weight:600;"
            f" letter-spacing:0.5px; padding:6px 0; }}"
            f"QPushButton:hover {{ color:{ACCENT3}; border-bottom-color:{ACCENT3}; }}"
        )
        load_btn.clicked.connect(self._open_video)
        ph.addWidget(load_btn)
        ph.addWidget(QLabel(_("MP4 · MOV · AVI · MKV"),
            styleSheet=f"color:{TEXT3}; font-size:{fs(11)}px;",
            alignment=Qt.AlignmentFlag.AlignCenter))

        vs = QWidget()
        vs.setObjectName("vs_wrap")
        vs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        vsl = QVBoxLayout(vs)
        vsl.setContentsMargins(0, 0, 0, 0)
        vsl.addWidget(self._video)
        vsl.addWidget(self._placeholder)
        self._video.hide()
        trl.addWidget(vs, stretch=1)

        # Barra de controles
        ctrl = QWidget()
        ctrl.setFixedHeight(max(44, fs(36)))
        ctrl.setObjectName("ctrl_bar")
        cl = QHBoxLayout(ctrl)
        cl.setContentsMargins(12, 0, 12, 0)
        cl.setSpacing(8)

        self._play_btn = QPushButton()
        self._play_btn.setIcon(play_icon(size=(18, 18), color="#1a1714"))
        self._play_btn.setIconSize(QSize(18, 18))
        self._play_btn.setFixedSize(34, 34)
        self._play_btn.setStyleSheet(f"""
            QPushButton {{ background:qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 {ACCENT3},stop:1 {ACCENT}); border:none;
                border-bottom:2px solid {ACCENT2}; border-radius:4px;
                padding:0; icon-size:18px 18px; }}
            QPushButton:hover {{ background:{ACCENT3}; }}
            QPushButton:pressed {{ border-bottom:none; padding-top:2px; }}
        """)
        self._play_btn.clicked.connect(self._video.toggle_play)
        cl.addWidget(self._play_btn)

        for label, delta in [("-5s", -5), ("+5s", 5)]:
            b = QPushButton(label)
            b.setFixedWidth(42)
            b.setStyleSheet(f"""
                QPushButton {{ background:transparent; color:{TEXT2}; border:none; border-bottom:1px solid {BORDER2}; font-size:{fs(11)}px; font-weight:500; padding:4px 8px; min-height:26px; }}
                QPushButton:hover {{ color:{ACCENT}; border-bottom:1px solid {ACCENT}; }}
            """)
            b.clicked.connect(lambda checked, d=delta: self._video.seek(self._video.position + d))
            cl.addWidget(b)

        self._time_lbl = QLabel("0:00:00 / 0:00:00")
        self._time_lbl.setStyleSheet(f"color:{TEXT2}; font-size:{fs(11)}px; min-width:120px;")
        cl.addWidget(self._time_lbl)

        self._scrub_bar = ScrubBar()
        self._scrub_bar.seek_requested.connect(self._video.seek)
        cl.addWidget(self._scrub_bar, stretch=1)

        self._speed_btn = QPushButton("1x")
        self._speed_btn.setObjectName("ctrl_btn")
        self._speed_btn.setFixedWidth(44)
        self._speed_btn.clicked.connect(self._cycle_speed)
        cl.addWidget(self._speed_btn)

        self._mute_btn = QPushButton()
        self._mute_btn.setIcon(volume_icon(size=(18, 18), color=TEXT2))
        self._mute_btn.setIconSize(QSize(18, 18))
        self._mute_btn.setFixedSize(34, 34)
        self._muted = False
        self._mute_btn.setStyleSheet(f"""
            QPushButton {{ background:transparent; border:none;
                border-bottom:1px solid {BORDER2}; padding:0; min-height:26px; icon-size:18px 18px; }}
            QPushButton:hover {{ border-bottom:1px solid {ACCENT}; }}
        """)
        self._mute_btn.clicked.connect(self._toggle_mute)
        cl.addWidget(self._mute_btn)

        self._fs_btn = QPushButton()
        self._fs_btn.setIcon(fullscreen_icon(size=(18, 18), color=TEXT2))
        self._fs_btn.setIconSize(QSize(18, 18))
        self._fs_btn.setFixedSize(34, 34)
        self._fs_btn.setStyleSheet(f"""
            QPushButton {{ background:transparent; border:none;
                border-bottom:1px solid {BORDER2}; padding:0; icon-size:18px 18px; }}
            QPushButton:hover {{ border-bottom:1px solid {ACCENT}; }}
        """)
        self._fs_btn.setToolTip(_("Pantalla completa (F)"))
        self._fs_btn.clicked.connect(self._enter_fullscreen)
        cl.addWidget(self._fs_btn)

        trl.addWidget(ctrl)

        # Registros
        rh_w = QWidget()
        rh_w.setObjectName("reg_header")
        rh_w.setFixedHeight(32)
        rh_w.setObjectName("reg_header")
        rh = QHBoxLayout(rh_w)
        rh.setContentsMargins(12, 0, 12, 0)
        self._reg_lbl = QLabel(_("REGISTROS ({})").format(0))
        self._reg_lbl.setStyleSheet(f"""
            color: {ACCENT};
            font-size: {fs(10)}px;
            font-weight: 700;
            letter-spacing: 2px;
        """)
        rh.addWidget(self._reg_lbl)
        brl.addWidget(rh_w)

        reg_scroll = QScrollArea()
        reg_scroll.setWidgetResizable(True)
        reg_scroll.setFrameShape(QFrame.Shape.NoFrame)
        reg_scroll.setStyleSheet("background:transparent;")

        self._reg_container = QWidget()
        self._reg_container.setStyleSheet(f"background:transparent;")
        self._reg_layout = QVBoxLayout(self._reg_container)
        self._reg_layout.setContentsMargins(0, 0, 0, 0)
        self._reg_layout.setSpacing(0)
        self._reg_layout.addStretch()
        self._reg_empty = QLabel(_("Presioná un botón mientras el video corre"))
        self._reg_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._reg_empty.setStyleSheet(f"color:{TEXT3}; font-size:{fs(12)}px; padding:20px;")
        self._reg_layout.insertWidget(0, self._reg_empty)
        reg_scroll.setWidget(self._reg_container)
        brl.addWidget(reg_scroll, stretch=1)

        self._right_vsplit = right_vsplit
        right_vsplit.addWidget(top_right)
        right_vsplit.addWidget(bot_right)
        right_vsplit.setSizes([500, 160])
        right_vsplit.setStretchFactor(0, 1)
        right_vsplit.setStretchFactor(1, 0)

        # Agregar al splitter
        self._splitter.addWidget(left)
        self._splitter.addWidget(right)
        self._splitter.setSizes([230, 900])  # Proporciones iniciales
        self._splitter.setStretchFactor(0, 0)  # Sidebar no se estira con la ventana
        self._splitter.setStretchFactor(1, 1)  # Video sí

        layout.addWidget(self._splitter)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def _toggle_mute(self):
        self._muted = not self._muted
        try:
            if self._video._player:
                self._video._player.mute = self._muted
        except Exception:
            pass
        # Actualizar icono
        if self._muted:
            self._mute_btn.setIcon(mute_icon(size=(18, 18), color=TEXT2))
        else:
            self._mute_btn.setIcon(volume_icon(size=(18, 18), color=TEXT2))

    def _show_btn_config(self):
        ButtonConfigDialog(self).exec()
        # Full rebuild to pick up new colors
        for bid, (row, count_lbl) in list(self._btn_widgets.items()):
            try:
                self._btn_layout.removeWidget(row)
                row.deleteLater()
            except RuntimeError:
                pass
        self._btn_widgets.clear()
        self._sync_buttons()

    def _enter_fullscreen(self):
        self._fs_active = True
        # Desconectar señales de obs antes de pasar el widget al fullscreen
        try: self._video.position_changed.disconnect(self._on_position)
        except Exception: pass
        try: self._video.duration_changed.disconnect()
        except Exception: pass
        try: self._video.playback_started.disconnect()
        except Exception: pass
        try: self._video.playback_paused.disconnect()
        except Exception: pass

        dlg = FullscreenObserver(self._video, state, self)
        dlg.exec()
        self._fs_active = False

    def _connect_state(self):
        state.buttons_changed.connect(self._sync_buttons)
        state.clips_changed.connect(self._sync_clips)
        state.presentation_changed.connect(self._sync_clips)
        state.sources_changed.connect(self._rebuild_tabs)
        state.active_source_changed.connect(self._on_source_changed)
        self._sync_buttons()
        self._sync_clips()
        self._rebuild_tabs()

    # ── Tabs ──────────────────────────────────────────────────────────────────

    def _rebuild_tabs(self):
        # Remove all except stretch (last) and + btn (second to last)
        while self._tab_bar_layout.count() > 2:
            item = self._tab_bar_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._tab_widgets.clear()
        n = len(state.video_sources)
        for i, vs in enumerate(state.video_sources):
            tab = self._make_tab(vs.name, i, i == state.active_source_idx)
            self._tab_bar_layout.insertWidget(i, tab)
            self._tab_widgets.append(tab)
        # + button: right after last tab, hidden if 10 sources
        self._add_src_btn.setVisible(n < 10)
        # Move + to position n (right after last tab, before stretch)
        self._tab_bar_layout.removeWidget(self._add_src_btn)
        self._tab_bar_layout.insertWidget(n, self._add_src_btn)
        has = n > 0
        self._video.setVisible(has)
        self._placeholder.setVisible(not has)

    def _make_tab(self, name: str, index: int, active: bool) -> QWidget:
        wrap = QWidget()
        wrap.setFixedHeight(32)
        wl = QHBoxLayout(wrap)
        wl.setContentsMargins(0, 0, 0, 0)
        wl.setSpacing(0)

        tab = QWidget()
        tab.setCursor(Qt.CursorShape.PointingHandCursor)
        tl = QHBoxLayout(tab)
        tl.setContentsMargins(12, 0, 12, 0)
        display = name if len(name) <= 20 else name[:18] + "..."
        name_lbl = QLabel(display)
        name_lbl.setToolTip(name)
        fw = "600" if active else "400"
        fc = str(TEXT0) if active else str(TEXT3)
        name_lbl.setStyleSheet(
            f"color:{fc}; font-size:{fs(11)}px; font-weight:{fw};"
            " background:transparent; border:none;")
        tl.addWidget(name_lbl)

        if active:
            tab.setStyleSheet(
                f"QWidget {{ background:{BG0}; border:none; border-top:2px solid {ACCENT}; }}")
        else:
            tab.setStyleSheet(
                f"QWidget {{ background:transparent; border:none; border-top:2px solid transparent; }}"
            )
        tab.mousePressEvent = lambda e, idx=index: self._switch_source(idx)
        wl.addWidget(tab)

        if active:
            close_btn = QPushButton("×")
            close_btn.setFixedSize(24, 32)
            close_btn.setStyleSheet(
                f"QPushButton {{ background:{BG0}; color:{ACCENT}; border:none;"
                f" border-top:2px solid {ACCENT}; font-size:{fs(14)}px; font-weight:700; padding:0; }}"
                f"QPushButton:hover {{ color:#ffffff; background:{BG1}; }}"
            )
            close_btn.clicked.connect(lambda checked, idx=index: self._close_source(idx))
            wl.addWidget(close_btn)

        return wrap

    def _switch_source(self, idx: int):
        if idx == state.active_source_idx:
            return
        state.save_source_position(self._video.position)
        state.switch_source(idx)

    def _close_source(self, idx: int):
        state.save_source_position(self._video.position)
        state.remove_video_source(idx)

    def _on_source_changed(self, path: str, name: str):
        self._rebuild_tabs()
        if not path:
            self._video.stop()
            return
        vs = state._active_source()
        self._video.load(path)
        # Limpiar conexiones previas para evitar acumulación
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                self._video.file_loaded.disconnect()
            except Exception:
                pass
        if vs and vs.last_pos > 30:
            saved_pos = vs.last_pos
            def _ask_resume():
                try: self._video.file_loaded.disconnect(_ask_resume)
                except Exception: pass
                reply = QMessageBox.question(
                    self, _("Reanudar"),
                    _("¿Continuar desde {}?").format(fmt_time(saved_pos)),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self._video.seek(saved_pos)
            self._video.file_loaded.connect(_ask_resume)
        elif vs and vs.last_pos > 0:
            saved_pos = vs.last_pos
            def _do_seek():
                try: self._video.file_loaded.disconnect(_do_seek)
                except Exception: pass
                self._video.seek(saved_pos)
            self._video.file_loaded.connect(_do_seek)
        self._video.show()
        self._placeholder.hide()

    # ── Video ─────────────────────────────────────────────────────────────────

    def _open_video(self):
        paths, _filt = QFileDialog.getOpenFileNames(
            self, _("Agregar video fuente"),
            filter="Video (*.mp4 *.mov *.avi *.mkv *.webm *.m4v *.mts)")
        for path in paths:
            state.add_video_source(path)

    def _on_position(self, t: float):
        self._scrub_bar.set_position(t)
        self._time_lbl.setText(f"{fmt_time(t)} / {fmt_time(self._video.duration)}")

    def _cycle_speed(self):
        self._speed_idx = (self._speed_idx + 1) % len(self._speeds)
        spd = self._speeds[self._speed_idx]
        self._video.set_speed(spd)
        self._speed_btn.setText(f"{spd}x")

    def keyPressEvent(self, e: QKeyEvent):
        # Si fullscreen está activo, ignorar — el FullscreenObserver maneja todo
        if getattr(self, '_fs_active', False):
            e.accept()
            return
        k = e.key()
        pos = self._video.position
        shift = bool(e.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        if   k == Qt.Key.Key_Left:  self._video.seek(pos + (-60 if shift else -5))
        elif k == Qt.Key.Key_Right: self._video.seek(pos + ( 60 if shift else  5))
        elif k == Qt.Key.Key_Up:    self._video.seek(pos + 10)
        elif k == Qt.Key.Key_Down:  self._video.seek(pos - 10)
        elif k == Qt.Key.Key_Space: self._video.toggle_play()
        elif k == Qt.Key.Key_F:     self._enter_fullscreen()
        else:
            text = e.text().upper()
            if text:
                for btn in state.buttons:
                    if getattr(btn, 'hotkey', '').upper() == text:
                        self._register_clip(btn)
                        return
            super().keyPressEvent(e)

    # ── Botonera ──────────────────────────────────────────────────────────────

    def _show_add_modal(self):
        AddButtonDialog(self).exec()

    def _sync_buttons(self):
        current_ids = {b.id for b in state.buttons}
        for bid in set(self._btn_widgets) - current_ids:
            row, _ = self._btn_widgets.pop(bid)
            try:
                self._btn_layout.removeWidget(row)
                row.deleteLater()
            except RuntimeError:
                pass
        for i, btn in enumerate(state.buttons):
            if btn.id not in self._btn_widgets:
                row, count_lbl = self._make_btn_row(btn)
                self._btn_layout.insertWidget(i, row)
                self._btn_widgets[btn.id] = (row, count_lbl)
        for btn in state.buttons:
            if btn.id in self._btn_widgets:
                count = sum(1 for c in state.clips if getattr(c, 'category', c.name) == btn.label)
                try:
                    self._btn_widgets[btn.id][1].setText(str(count))
                except RuntimeError:
                    pass
        self._btn_empty.setVisible(len(state.buttons) == 0)

    def _make_btn_row(self, btn: Button):
        row = QWidget()
        row.setFixedHeight(34)
        row.setStyleSheet("background:transparent;")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)

        label_text = btn.label[:16] + ("…" if len(btn.label) > 16 else "")
        ab = QPushButton(label_text)
        ab.setFixedHeight(34)
        has_accent = btn.color not in ("#1c1c1c", "#2a2a2a", "", None)
        accent_c = btn.color if has_accent else str(TEXT3)
        ab.setStyleSheet(
            f"QPushButton {{ background:{BG1}; color:{TEXT1}; border:none;"
            f" border-left:3px solid {accent_c};"
            f" font-size:{fs(13)}px; font-weight:500; text-align:left;"
            f" padding:0 12px 0 10px; letter-spacing:0.2px; }}"
            f"QPushButton:hover {{ background:{BG2}; color:{TEXT0};"
            f" border-left:3px solid {ACCENT}; }}"
            f"QPushButton:pressed {{ background:{BG3}; }}"
        )
        ab.setCursor(Qt.CursorShape.PointingHandCursor)
        ab.clicked.connect(lambda checked, b=btn: self._register_clip(b))

        count_lbl = QLabel("0")
        count_lbl.setFixedWidth(32)
        count_lbl.setFixedHeight(34)
        count_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        count_lbl.setStyleSheet(
            f"background:{BG1}; color:{TEXT2};"
            f" border:none; font-size:{fs(12)}px; font-weight:600;"
            f" letter-spacing:0.5px;"
        )

        rl.addWidget(ab, stretch=1)
        rl.addWidget(count_lbl)

        # Hotkey badge — pequeño indicador de tecla asignada
        hk = getattr(btn, 'hotkey', '') or ''
        hk_container = QWidget()
        hk_container.setFixedWidth(26)
        hk_container.setFixedHeight(34)
        hk_container.setStyleSheet("background:transparent;")
        if hk:
            _hlo = QVBoxLayout(hk_container)
            _hlo.setContentsMargins(0, 0, 4, 0)
            _hlo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            _hk = QLabel(hk.upper())
            _hk.setFixedSize(21, 15)
            _hk.setAlignment(Qt.AlignmentFlag.AlignCenter)
            _hk.setStyleSheet(
                f"background:{BG3}; color:{TEXT1};"
                f" border:1px solid rgba(255,252,248,0.12);"
                f" border-radius:3px;"
                f" font-size:{fs(10)}px; font-weight:700;"
                f" font-family:'Courier New',monospace;"
            )
            _hlo.addWidget(_hk)
        rl.addWidget(hk_container)

        return row, count_lbl

    def _register_clip(self, btn: Button):
        if not state.active_video_path:
            state.toast_requested.emit("Cargá un video primero")
            return
        state.add_clip(btn, self._video.position, self._video.duration)

    # ── Registros ─────────────────────────────────────────────────────────────

    def _sync_clips(self):
        current_ids = {c.id for c in state.clips}
        for cid in set(self._clip_widgets) - current_ids:
            w, _ind = self._clip_widgets.pop(cid)
            self._clip_pres_state.pop(cid, None)
            try:
                self._reg_layout.removeWidget(w)
                w.deleteLater()
            except RuntimeError:
                pass
        for clip in state.clips:
            in_pres = getattr(clip, 'in_presentation', False)
            if clip.id not in self._clip_widgets:
                row, pres_ind = self._make_clip_row(clip)
                self._reg_layout.insertWidget(0, row)
                self._clip_widgets[clip.id] = (row, pres_ind)
                self._clip_pres_state[clip.id] = in_pres
            elif self._clip_pres_state.get(clip.id) != in_pres:
                # in_presentation cambió — actualizar solo el indicador ✓
                _row, pres_ind = self._clip_widgets[clip.id]
                pres_ind.setVisible(in_pres)
                self._clip_pres_state[clip.id] = in_pres
        self._reg_lbl.setText(_("REGISTROS ({})").format(len(state.clips)))
        self._reg_empty.setVisible(len(state.clips) == 0)
        for btn in state.buttons:
            if btn.id in self._btn_widgets:
                count = sum(1 for c in state.clips if getattr(c, 'category', c.name) == btn.label)
                try:
                    self._btn_widgets[btn.id][1].setText(str(count))
                except RuntimeError:
                    pass

    def _make_clip_row(self, clip: Clip):
        row = QWidget()
        row.setFixedHeight(32)
        row.setStyleSheet(f"""
            QWidget {{ background:{BG1}; border-bottom:1px solid {BORDER}; }}
            QWidget:hover {{ background:{BG2}; }}
        """)
        rl = QHBoxLayout(row)
        rl.setContentsMargins(12, 0, 8, 0)
        rl.setSpacing(8)

        dot = QLabel()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(f"background:{clip.color}; border-radius:4px;")
        rl.addWidget(dot)

        name_lbl = QLabel(clip.name)
        name_lbl.setStyleSheet(f"color:{TEXT0}; font-size:{fs(12)}px; font-weight:500; background:transparent; border:none;")
        rl.addWidget(name_lbl, stretch=1)

        src_lbl = QLabel(clip.video_name[:12] + ("..." if len(clip.video_name) > 12 else ""))
        src_lbl.setStyleSheet(f"color:{TEXT3}; font-size:{fs(9)}px; background:transparent; border:none;")
        rl.addWidget(src_lbl)

        tl = QLabel(clip.timestamp)
        tl.setStyleSheet(f"color:{TEXT2}; font-size:{fs(11)}px; background:transparent; border:none;")
        rl.addWidget(tl)

        # Indicador ✓ — siempre creado, visible solo si in_presentation
        pres_ind = QLabel("✓")
        pres_ind.setFixedWidth(14)
        pres_ind.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pres_ind.setToolTip(_("Ya está en la presentación"))
        pres_ind.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        pres_ind.setStyleSheet(
            f"color:#27AE60; font-size:{fs(11)}px; font-weight:700;"
            f" background:transparent; border:none;"
        )
        pres_ind.setVisible(getattr(clip, 'in_presentation', False))
        rl.addWidget(pres_ind)

        del_btn = QPushButton("x")
        del_btn.setFixedSize(18, 18)
        del_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; color:{TEXT3}; border:none;"
            f" font-size:{fs(12)}px; font-weight:700; padding:0; }}"
            f"QPushButton:hover {{ color:#e05555; }}"
        )
        del_btn.clicked.connect(lambda checked, cid=clip.id: state.remove_clip(cid))
        rl.addWidget(del_btn)

        def _clip_press(e, c=clip):
            if e.button() == Qt.MouseButton.RightButton:
                self._show_clip_context_menu(c, e.globalPosition().toPoint())
            else:
                self._seek_to_clip(c)
        row.mousePressEvent = _clip_press
        row.mouseDoubleClickEvent = lambda e, c=clip: self._edit_clip(c)
        return row, pres_ind

    def _seek_to_clip(self, clip: Clip):
        """Seek video to clip timestamp. Switch source if needed."""
        if clip.video_path and clip.video_path != state.active_video_path:
            # Find and switch to the correct source
            for i, vs in enumerate(state.video_sources):
                if vs.path == clip.video_path:
                    state.save_source_position(self._video.position)
                    state.switch_source(i)
                    # After source loads, seek to position
                    def _do_seek(t=clip.time_sec):
                        try: self._video.file_loaded.disconnect()
                        except Exception: pass
                        self._video.seek(t)
                    self._video.file_loaded.connect(_do_seek)
                    return
        self._video.seek(clip.time_sec)

    def _edit_clip(self, clip: Clip):
        dlg = ClipEditDialog(clip.name, clip.note, clip.color, self)
        if dlg.exec():
            state.update_clip(clip.id, name=dlg.name, note=dlg.note, color=dlg.color)

    def _show_clip_context_menu(self, clip: Clip, pos):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background:{BG2}; border:1px solid {BORDER2}; padding:4px 0; color:{TEXT0}; }}
            QMenu::item {{ padding:7px 20px; font-size:{fs(12)}px; }}
            QMenu::item:selected {{ background:{BG3}; color:{ACCENT}; }}
            QMenu::separator {{ height:1px; background:{BORDER}; margin:3px 0; }}
        """)
        act_export = QAction(_("Exportar clip"), menu)
        act_export.triggered.connect(lambda: self._export_clip(clip))
        menu.addAction(act_export)
        menu.addSeparator()
        act_adjust = QAction(_("Abrir en Ajuste"), menu)
        act_adjust.triggered.connect(lambda: self._goto_adjust_for_clip(clip))
        menu.addAction(act_adjust)
        menu.exec(pos)

    def _goto_adjust_for_clip(self, clip: Clip):
        mw = self.window()
        if hasattr(mw, '_goto_adjust'):
            mw._goto_adjust(getattr(clip, 'category', clip.name))

    def _export_clip(self, clip: Clip):
        from components.dialogs import ClipExportSettingsDialog
        dlg = ClipExportSettingsDialog(self)
        if dlg.exec() != ClipExportSettingsDialog.DialogCode.Accepted:
            return
        import os
        docs = os.path.join(os.path.expanduser("~"), "Documents", "PyScout", "Exported")
        os.makedirs(docs, exist_ok=True)
        safe = clip.name.replace("/", "-").replace("\\", "-").replace(":", "-")
        default = os.path.join(docs, f"{safe}.mp4")
        out, _ = QFileDialog.getSaveFileName(
            self, _("Guardar clip como"), default, "Video MP4 (*.mp4)"
        )
        if not out:
            return
        clip_dict = {
            "video_path": clip.video_path,
            "clip_start":  clip.start_sec,
            "clip_dur":    max(0.1, clip.end_sec - clip.start_sec),
        }
        state.toast_requested.emit(_("Exportando {}...").format(clip.name))
        self._export_thread = _ClipExportThread(
            clip_dict, out,
            crf=dlg.crf, fps=dlg.fps,
            mute_audio=dlg.mute_audio,
            show_overlay=dlg.show_overlay,
            clip_name=clip.name,
        )
        def _on_done(ok, path):
            if ok:
                state.toast_requested.emit(_("Exportado: {}").format(os.path.basename(path)))
            else:
                state.toast_requested.emit(_("Error al exportar"))
        self._export_thread.done.connect(_on_done)
        self._export_thread.start()


# ── Ventana fullscreen ─────────────────────────────────────────────────────────

class FullscreenObserver(QDialog):
    """
    Fullscreen con el video del ObservationScreen + sidebar compacto de botones.
    Toma el MpvWidget existente temporalmente (reparent) y lo devuelve al cerrar.
    """
    def __init__(self, video_widget, state_ref, obs_screen, parent=None):
        super().__init__(parent)
        self._video      = video_widget
        self._obs        = obs_screen
        self._original_parent  = video_widget.parent()
        self._original_layout  = None

        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.showFullScreen()
        self.raise_()
        self.activateWindow()
        self.setFocus()

        from utils.theme_helpers import BG0, BG1, BG2, BG3, BG4
        from utils.theme_helpers import ACCENT, ACCENT2, ACCENT3, TEXT0, TEXT1, TEXT2, TEXT3, BORDER, BORDER2
        from styles.theme import CLIP_COLORS, fs, fs
        from store.state import state, Button

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Video ocupa todo ───────────────────────────────────────────────────
        video_wrap = QWidget()
        video_wrap.setStyleSheet("background:#000;")
        vl = QVBoxLayout(video_wrap)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        # Reparent del widget de video
        self._video.setParent(video_wrap)
        vl.addWidget(self._video, stretch=1)

        # Mini control bar
        ctrl = QWidget()
        ctrl.setFixedHeight(40)
        ctrl.setStyleSheet(f"background:rgba(0,0,0,0.75); border:none;")
        cl = QHBoxLayout(ctrl)
        cl.setContentsMargins(12, 0, 12, 0)
        cl.setSpacing(10)

        self._play_btn = QPushButton()
        self._play_btn.setIcon(play_icon(size=(18, 18), color="#1a1714"))
        self._play_btn.setIconSize(QSize(18, 18))
        self._play_btn.setFixedSize(32, 32)
        self._play_btn.setStyleSheet(f"""
            QPushButton {{ background:qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 {ACCENT3},stop:1 {ACCENT}); border:none;
                border-bottom:2px solid {ACCENT2}; border-radius:4px;
                padding:0; icon-size:18px 18px; }}
            QPushButton:hover {{ background:{ACCENT3}; }}
            QPushButton:pressed {{ border-bottom:none; padding-top:2px; }}
        """)
        self._play_btn.clicked.connect(self._video.toggle_play)
        self._video.playback_started.connect(
            lambda: self._play_btn.setIcon(pause_icon(size=(18, 18), color="#1a1714"))
        )
        self._video.playback_paused.connect(
            lambda: self._play_btn.setIcon(play_icon(size=(18, 18), color="#1a1714"))
        )
        cl.addWidget(self._play_btn)

        self._fs_mute_btn = QPushButton()
        self._fs_mute_btn.setIcon(volume_icon(size=(18, 18), color=TEXT2))
        self._fs_mute_btn.setIconSize(QSize(18, 18))
        self._fs_mute_btn.setFixedSize(32, 32)
        self._fs_muted = False
        self._fs_mute_btn.setStyleSheet(f"""
            QPushButton {{ background:transparent; color:{TEXT2}; border:none; font-size:{fs(16)}px; padding:0; }}
            QPushButton:hover {{ color:{ACCENT}; }}
        """)
        self._fs_mute_btn.clicked.connect(self._toggle_fs_mute)
        cl.addWidget(self._fs_mute_btn)

        self._time_lbl = QLabel("0:00:00")
        self._time_lbl.setStyleSheet(f"color:{TEXT2}; font-size:{fs(11)}px; min-width:90px;")
        cl.addWidget(self._time_lbl)

        self._scrub = ScrubBar()
        self._scrub.seek_requested.connect(self._video.seek)
        self._video.duration_changed.connect(self._scrub.set_duration)
        if self._video.duration > 0:
            self._scrub.set_duration(self._video.duration)
            self._scrub.set_position(self._video.position)
        self._video.position_changed.connect(self._on_pos)
        cl.addWidget(self._scrub, stretch=1)

        self._dur_lbl = QLabel("0:00:00")
        self._dur_lbl.setStyleSheet(f"color:{TEXT3}; font-size:{fs(11)}px; min-width:60px;")
        cl.addWidget(self._dur_lbl)

        exit_btn = QPushButton("Salir")
        exit_btn.setStyleSheet(f"""
            QPushButton {{ background:transparent; color:{TEXT2}; border:none;
                border-bottom:1px solid {BORDER2}; font-size:{fs(11)}px; padding:4px 10px; }}
            QPushButton:hover {{ color:{ACCENT}; border-bottom-color:{ACCENT}; }}
        """)
        exit_btn.clicked.connect(self.close)
        cl.addWidget(exit_btn)

        # Hint de atajos — entre video y barra de controles
        hint = QLabel(
            "\u2190 \u2192  \xb15s     \u2191 \u2193  \xb110s     Shift+\u2190\u2192  \xb11 min     Space  pausa     M  silenciar     Esc  salir"
        )
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet(
            f"background:rgba(0,0,0,0.50); color:rgba(255,255,255,0.30);"
            f" font-size:{fs(10)}px; letter-spacing:0.8px; padding:3px 0; border:none;"
        )
        vl.addWidget(hint)
        vl.addWidget(ctrl)

        # ── Sidebar compacto (izquierda) ──────────────────────────────────────
        sidebar = QWidget()
        sidebar.setFixedWidth(180)
        sidebar.setStyleSheet(f"""
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 rgba(17,17,21,0.96), stop:1 rgba(11,11,14,0.98));
            border-right: 1px solid rgba(255,255,255,0.06);
        """)
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(0)

        # Header
        shdr = QWidget()
        shdr.setFixedHeight(40)
        shdr.setStyleSheet("background:transparent; border:none;")
        sh = QHBoxLayout(shdr)
        sh.setContentsMargins(14, 0, 10, 0)
        lbl = QLabel(_("BOTONES"))
        lbl.setStyleSheet(f"color:{ACCENT}; font-size:{fs(9)}px; font-weight:700; letter-spacing:2px;")
        sh.addWidget(lbl)
        sl.addWidget(shdr)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:rgba(255,255,255,0.05);")
        sl.addWidget(sep)

        # Lista de botones
        self._fs_btn_scroll = QScrollArea()
        self._fs_btn_scroll.setWidgetResizable(True)
        self._fs_btn_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._fs_btn_scroll.setStyleSheet("background:transparent;")
        self._fs_btn_container = QWidget()
        self._fs_btn_container.setStyleSheet("background:transparent;")
        self._fs_btn_layout = QVBoxLayout(self._fs_btn_container)
        self._fs_btn_layout.setContentsMargins(10, 10, 10, 10)
        self._fs_btn_layout.setSpacing(6)
        self._fs_btn_layout.addStretch()
        self._fs_btn_scroll.setWidget(self._fs_btn_container)
        sl.addWidget(self._fs_btn_scroll, stretch=1)

        # Registros recientes (últimos 5)
        sep2 = QFrame()
        sep2.setFixedHeight(1)
        sep2.setStyleSheet(f"background:rgba(255,255,255,0.05);")
        sl.addWidget(sep2)

        rec_hdr = QLabel("RECIENTES")
        rec_hdr.setFixedHeight(28)
        rec_hdr.setStyleSheet(f"""
            color:{ACCENT}; font-size:{fs(9)}px; font-weight:700;
            letter-spacing:2px; padding-left:14px;
        """)
        sl.addWidget(rec_hdr)

        self._recent_container = QWidget()
        self._recent_container.setStyleSheet("background:transparent;")
        self._recent_layout = QVBoxLayout(self._recent_container)
        self._recent_layout.setContentsMargins(0, 0, 0, 0)
        self._recent_layout.setSpacing(0)
        sl.addWidget(self._recent_container)

        root.addWidget(sidebar)
        root.addWidget(video_wrap, stretch=1)

        # Auto-play y focus
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication
        QApplication.instance().installEventFilter(self)
        QTimer.singleShot(200, lambda: (self._video.play(), self.setFocus()))

        # Conectar estado
        state.buttons_changed.connect(self._sync_fs_buttons)
        state.clips_changed.connect(self._sync_recent)
        self._sync_fs_buttons()
        self._sync_recent()

    def _on_pos(self, t: float):
        from utils.time_utils import fmt_time
        self._scrub.set_position(t)
        self._time_lbl.setText(fmt_time(t))
        if hasattr(self, '_dur_lbl'): self._dur_lbl.setText(fmt_time(self._video.duration))
        try:
            self._obs._scrub_bar.set_position(t)
            self._obs._time_lbl.setText(f"{fmt_time(t)} / {fmt_time(self._video.duration)}")
        except Exception:
            pass

    def _toggle_fs_mute(self):
        self._fs_muted = not self._fs_muted
        try:
            if self._video._player:
                self._video._player.mute = self._fs_muted
        except Exception:
            pass
        self._fs_mute_btn.setIcon(mute_icon(size=(18, 18), color=TEXT2) if self._fs_muted else volume_icon(size=(18, 18), color=TEXT2))

    def _sync_fs_buttons(self):
        from utils.theme_helpers import BG1, BG2, BG3, BG4, ACCENT, ACCENT2, ACCENT3, TEXT0, TEXT1, TEXT2, TEXT3, BORDER2
        from store.state import state

        # Limpiar
        while self._fs_btn_layout.count() > 1:
            item = self._fs_btn_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for btn in state.buttons:
            has_accent = btn.color not in ("#1c1c1c", "#2a2a2a", "", None)
            accent_c = btn.color if has_accent else str(TEXT3)
            b = QPushButton(btn.label)
            b.setFixedHeight(36)
            b.setStyleSheet(f"""
                QPushButton {{
                    background: {BG2};
                    color: {TEXT0};
                    border: none;
                    border-left: 3px solid {accent_c};
                    font-size: {fs(13)}px;
                    font-weight: 500;
                    text-align: left;
                    padding: 0 12px 0 10px;
                }}
                QPushButton:hover {{
                    background: {BG3};
                    border-left: 3px solid {ACCENT};
                }}
                QPushButton:pressed {{
                    background: {BG4};
                }}
            """)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.clicked.connect(lambda checked, bt=btn: self._register(bt))
            self._fs_btn_layout.insertWidget(self._fs_btn_layout.count()-1, b)

    def _register(self, btn):
        from store.state import state
        if not state.active_video_path:
            return
        state.add_clip(btn, self._video.position, self._video.duration)

    def _seek_recent_clip(self, clip):
        """Ir al clip reciente reutilizando la lógica del ObservationScreen."""
        try:
            self._obs._seek_to_clip(clip)
            self._video.play()
        except Exception:
            pass

    def _sync_recent(self):
        from store.state import state
        from utils.theme_helpers import TEXT0, TEXT2, TEXT3, BORDER, ACCENT

        while self._recent_layout.count():
            item = self._recent_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        recent = list(reversed(state.clips))[:5]
        for clip in recent:
            row = QWidget()
            row.setFixedHeight(28)
            row.setCursor(Qt.CursorShape.PointingHandCursor)
            row.setStyleSheet(f"""
                QWidget {{
                    background: transparent;
                    border-bottom: 1px solid rgba(255,255,255,0.04);
                }}
                QWidget:hover {{
                    background: rgba(255,255,255,0.05);
                }}
            """)
            rl = QHBoxLayout(row)
            rl.setContentsMargins(10, 0, 10, 0)
            rl.setSpacing(6)
            dot = QLabel()
            dot.setFixedSize(6, 6)
            dot.setStyleSheet(f"background:{clip.color}; border-radius:3px;")
            rl.addWidget(dot)
            nm = QLabel(clip.name[:14] + ("..." if len(clip.name)>14 else ""))
            nm.setStyleSheet(f"color:{TEXT0}; font-size:{fs(11)}px; background:transparent; border:none;")
            rl.addWidget(nm, stretch=1)
            ts = QLabel(clip.timestamp)
            ts.setStyleSheet(f"color:{TEXT3}; font-size:{fs(10)}px; background:transparent; border:none;")
            rl.addWidget(ts)
            row.mousePressEvent = lambda e, c=clip: self._seek_recent_clip(c)
            self._recent_layout.addWidget(row)

    def _handle_key(self, k, shift):
        """Usa seek absoluto — idempotente si se llama dos veces."""
        pos = self._video.position
        if   k == Qt.Key.Key_Escape: self.close(); return True
        elif k == Qt.Key.Key_F:      self.close(); return True
        elif k == Qt.Key.Key_Space:  self._video.toggle_play(); return True
        elif k == Qt.Key.Key_M:      self._toggle_fs_mute(); return True
        elif k == Qt.Key.Key_Left:   self._video.seek(pos + (-60 if shift else -5))
        elif k == Qt.Key.Key_Right:  self._video.seek(pos + ( 60 if shift else  5))
        elif k == Qt.Key.Key_Up:     self._video.seek(pos + 10)
        elif k == Qt.Key.Key_Down:   self._video.seek(pos - 10)
        else: return False
        return True

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.Type.KeyPress:
            shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
            if self._handle_key(event.key(), shift):
                return True  # consumido
        return super().eventFilter(obj, event)

    def keyPressEvent(self, e):
        shift = bool(e.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        if self._handle_key(e.key(), shift):
            e.accept()
        else:
            super().keyPressEvent(e)

    def closeEvent(self, e):
        # 1. Desconectar todas las señales del fullscreen
        for sig, slot in [
            (self._video.position_changed,  self._on_pos),
            (self._video.playback_started,  None),
            (self._video.playback_paused,   None),
        ]:
            try: 
                sig.disconnect(slot) if slot else sig.disconnect()
            except (RuntimeError, TypeError): 
                pass  # Ya desconectada
        
        try: 
            self._video.duration_changed.disconnect(self._scrub.set_duration)
        except (RuntimeError, TypeError): 
            pass  # Ya desconectada

        # 2. Desconectar estado fullscreen
        try:
            from store.state import state
            state.buttons_changed.disconnect(self._sync_fs_buttons)
            state.clips_changed.disconnect(self._sync_recent)
        except (RuntimeError, TypeError):
            pass  # Ya desconectada

        # 3. Devolver video a vs_wrap ANTES de reconectar señales
        try:
            vs_widget = self._obs.findChild(QWidget, "vs_wrap")
            if vs_widget:
                self._video.setParent(vs_widget)
                vs_widget.layout().insertWidget(0, self._video)
                self._video.show()
        except Exception as ex:
            print(f"[FS] restore error: {ex}")

        # 4. Reconectar señales del obs screen (desconectar TODO primero)
        try: 
            self._video.position_changed.disconnect()
        except (RuntimeError, TypeError): 
            pass
        
        try: 
            self._video.playback_started.disconnect()
        except (RuntimeError, TypeError): 
            pass
        
        try: 
            self._video.playback_paused.disconnect()
        except (RuntimeError, TypeError): 
            pass
        
        try: 
            self._video.duration_changed.disconnect()
        except (RuntimeError, TypeError): 
            pass
        
        # Reconectar señales del ObservationScreen
        try:
            self._video.playback_started.connect(
                lambda: self._obs._play_btn.setIcon(pause_icon(size=(18, 18), color="#1a1714"))
            )
            self._video.playback_paused.connect(
                lambda: self._obs._play_btn.setIcon(play_icon(size=(18, 18), color="#1a1714"))
            )
            self._video.duration_changed.connect(lambda d: self._obs._scrub_bar.set_duration(d))
            self._video.position_changed.connect(self._obs._on_position)
        except (RuntimeError, TypeError):
            pass

        from PySide6.QtWidgets import QApplication
        QApplication.instance().removeEventFilter(self)
        super().closeEvent(e)
        
        # Restaurar ventana principal al frente
        try:
            w = self._obs.window()
            w.setWindowState(w.windowState() & ~Qt.WindowState.WindowMinimized)
            w.raise_()
            w.activateWindow()
        except Exception:
            pass


# ── Modal de configuración de botones ────────────────────────────────────────

class ButtonConfigDialog(QDialog):
    RESERVED = {"F", "M", "ESCAPE", " "}

    SPORT_PRESETS = {
        "Fútbol": [
            ("Gol",           "#1a3d2b"), ("Tiro al arco",  "#1a3d2b"),
            ("Corner",        "#4a3000"), ("Falta",         "#5c1a1a"),
            ("Offside",       "#5c1a1a"), ("Contraataque",  "#1e3a5f"),
            ("Presión",       "#3d1a4a"), ("Penal",         "#5c1a1a"),
        ],
        "Básquet": [
            ("Pick & Roll",   "#1e3a5f"), ("Triple",        "#1a3d2b"),
            ("Drive",         "#4a3000"), ("Asistencia",    "#1e3a5f"),
            ("Robo",          "#5c1a1a"), ("Rebote",        "#3d1a4a"),
            ("Bloqueo",       "#1a3a3a"), ("Pérdida",       "#5c1a1a"),
        ],
        "Vóley": [
            ("Saque",         "#4a3000"), ("Recepción",     "#1a3d2b"),
            ("Armado",        "#1e3a5f"), ("Ataque",        "#1a3d2b"),
            ("Bloqueo",       "#3d1a4a"), ("Defensa",       "#1a3a3a"),
            ("Error propio",  "#5c1a1a"),
        ],
        "Handball": [
            ("Gol",           "#1a3d2b"), ("Tiro libre",    "#4a3000"),
            ("Contraataque",  "#1e3a5f"), ("7 metros",      "#5c1a1a"),
            ("Bloqueo",       "#3d1a4a"), ("Robo",          "#1a3a3a"),
            ("Exclusión",     "#5c1a1a"),
        ],
    }

    BTN_COLORS = [
        ("#1c1c1c", "Sin acento"),
        ("#1e3a5f", "Azul"),
        ("#1a3d2b", "Verde"),
        ("#5c1a1a", "Rojo"),
        ("#3d1a4a", "Morado"),
        ("#4a3000", "Dorado"),
        ("#1a3a3a", "Teal"),
        ("#3a2a1a", "Tierra"),
        ("#3a1a2a", "Rosa"),
        ("#1a1a3a", "Noche"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Configurar botones"))
        self.setMinimumWidth(560)
        self.setModal(True)
        from utils.theme_helpers import BG1, BG0, TEXT0
        self.setStyleSheet(f"background:{BG1}; color:{TEXT0};")
        self._rows = {}
        self._build()

    def _build(self):
        from utils.theme_helpers import (
            BG0, BG1, BG2, BG3, BG4, ACCENT, ACCENT2, ACCENT3,
            TEXT0, TEXT1, TEXT2, TEXT3, BORDER, BORDER2
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title_row = QHBoxLayout()
        title = QLabel(_("Configurar botones"))
        title.setStyleSheet(f"color:{TEXT0}; font-size:{fs(14)}px; font-weight:700;")
        title_row.addWidget(title)
        title_row.addStretch()
        presets_btn = QPushButton(_("Cargar preset..."))
        presets_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; color:{ACCENT}; border:1px solid {ACCENT2};"
            f" border-radius:2px; padding:4px 12px; font-size:{fs(11)}px; font-weight:600; }}"
            f"QPushButton:hover {{ background:rgba(201,164,74,0.1); border-color:{ACCENT}; }}"
        )
        presets_btn.clicked.connect(self._open_preset_chooser)
        title_row.addWidget(presets_btn)
        layout.addLayout(title_row)

        subtitle = QLabel(_("Pad: tiempo antes/después del click  ·  Hotkey: tecla para registrar sin mouse"))
        subtitle.setStyleSheet(f"color:{TEXT3}; font-size:{fs(11)}px;")
        layout.addWidget(subtitle)

        # Header de columnas
        hdr = QWidget()
        hdr.setStyleSheet(f"background:transparent; border-bottom:1px solid rgba(255,255,255,0.06);")
        hh = QHBoxLayout(hdr)
        hh.setContentsMargins(0, 0, 0, 6)
        for text, w in [(_("BOTÓN"), 140), (_("COLOR"), 100), (_("ANTES (s)"), 80), (_("DESPUÉS (s)"), 80), (_("HOTKEY"), 70)]:
            l = QLabel(text)
            l.setFixedWidth(w)
            l.setStyleSheet(f"color:{ACCENT}; font-size:{fs(9)}px; font-weight:700; letter-spacing:1.5px;")
            hh.addWidget(l)
        layout.addWidget(hdr)

        # Scroll de filas
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background:transparent;")
        scroll.setMaximumHeight(400)
        container = QWidget()
        container.setStyleSheet("background:transparent;")
        vl = QVBoxLayout(container)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(4)

        for btn in state.buttons:
            row = self._make_row(btn)
            vl.addWidget(row)
        vl.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

        # Footer
        sep = QFrame(); sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:rgba(255,255,255,0.06);")
        layout.addWidget(sep)

        btns = QHBoxLayout()
        btns.addStretch()
        rand_btn = QPushButton(_("🎲 Hotkeys random"))
        rand_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; color:{TEXT2}; border:1px solid {BORDER2};"
            f" border-radius:2px; padding:7px 14px; font-size:{fs(11)}px; }}"
            f"QPushButton:hover {{ color:{TEXT0}; border-color:rgba(255,255,255,0.25); }}"
        )
        rand_btn.setToolTip(_("Asigna una tecla distinta a cada botón de forma aleatoria"))
        rand_btn.clicked.connect(self._assign_random_hotkeys)
        btns.addWidget(rand_btn)
        btns.addSpacing(8)
        close_btn = QPushButton(_("Listo"))
        close_btn.setStyleSheet(
            f"QPushButton {{ background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            f"stop:0 {ACCENT3},stop:1 {ACCENT2}); color:#1a1714; border:none;"
            f" border-bottom:2px solid {ACCENT2}; padding:7px 24px; font-weight:600; }}"
            f"QPushButton:hover {{ background:{ACCENT3}; }}"
        )
        close_btn.clicked.connect(self._save_and_close)
        btns.addWidget(close_btn)
        layout.addLayout(btns)

    def _assign_random_hotkeys(self):
        import random
        import string
        reserved_single = {r for r in self.RESERVED if len(r) == 1}
        pool = [c for c in string.ascii_uppercase if c not in reserved_single]
        random.shuffle(pool)
        for i, btn in enumerate(state.buttons):
            if btn.id not in self._rows:
                continue
            _, _, _, hotkey_input, _ = self._rows[btn.id]
            key = pool[i] if i < len(pool) else ""
            hotkey_input._saved = key
            hotkey_input.setText(key)

    def _make_row(self, btn):
        from utils.theme_helpers import BG2, BG3, BG4, TEXT0, TEXT1, TEXT2, TEXT3, ACCENT, BORDER2, DANGER
        from PySide6.QtWidgets import QSpinBox, QComboBox, QLineEdit
        row = QWidget()
        row.setStyleSheet(
            f"QWidget {{ background:transparent; border-bottom:1px solid rgba(255,255,255,0.04); }}"
        )
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 6, 0, 6)
        rl.setSpacing(8)

        # Nombre (no editable aquí, solo label)
        dot = QWidget(); dot.setFixedSize(6, 6)
        dot.setStyleSheet(f"background:{btn.color}; border-radius:3px;")
        rl.addWidget(dot)
        name = QLineEdit(btn.label)
        name.setMaxLength(18)
        name.setFixedWidth(130)
        name.setStyleSheet(
            f"background:transparent; color:{TEXT0}; border:none; border-bottom:1px solid {BORDER2};"
            f" font-size:{fs(13)}px; font-weight:500; padding:2px 4px;"
        )
        name.setObjectName(f"name_{btn.id}")
        rl.addWidget(name)

        # Color combo con preview
        color_combo = QComboBox()
        color_combo.setFixedWidth(110)
        for hex_c, label in self.BTN_COLORS:
            color_combo.addItem("  " + label, hex_c)
            idx = color_combo.count() - 1
            from PySide6.QtGui import QColor
            color_combo.setItemData(idx, QColor(hex_c), Qt.ItemDataRole.BackgroundRole)
            color_combo.setItemData(idx, QColor("#f0ede8"), Qt.ItemDataRole.ForegroundRole)
        # Find current color or add it if custom
        current_idx = next((i for i,(h,_) in enumerate(self.BTN_COLORS) if h == btn.color), -1)
        if current_idx == -1:
            color_combo.addItem("  " + _("Personalizado"), btn.color)
            from PySide6.QtGui import QColor
            color_combo.setItemData(color_combo.count()-1, QColor(btn.color), Qt.ItemDataRole.BackgroundRole)
            color_combo.setItemData(color_combo.count()-1, QColor("#f0ede8"), Qt.ItemDataRole.ForegroundRole)
            color_combo.setCurrentIndex(color_combo.count()-1)
        else:
            color_combo.setCurrentIndex(current_idx)
        rl.addWidget(color_combo)

        # Pad before
        spin_b = QSpinBox()
        spin_b.setRange(0, 60)
        spin_b.setValue(max(0, int(getattr(btn, 'pad_before', 5))) if getattr(btn, 'pad_before', -1) >= 0 else 5)
        spin_b.setFixedWidth(78)
        spin_b.setSuffix("s")
        rl.addWidget(spin_b)

        # Pad after
        spin_a = QSpinBox()
        spin_a.setRange(0, 60)
        spin_a.setValue(max(0, int(getattr(btn, 'pad_after', 5))) if getattr(btn, 'pad_after', -1) >= 0 else 5)
        spin_a.setFixedWidth(78)
        spin_a.setSuffix("s")
        rl.addWidget(spin_a)

        # Hotkey
        hotkey_input = _HotkeyInput(getattr(btn, 'hotkey', ''), self.RESERVED)
        hotkey_input.setFixedWidth(68)
        hotkey_input.setPlaceholderText("—")
        hotkey_input.setToolTip(_("Escribí una tecla (no F, M, Esc, Space)"))
        hotkey_input.setStyleSheet(
            f"background:{BG2}; color:{TEXT0}; border:1.5px solid {TEXT3};"
            f" border-radius:0; padding:4px 8px; font-size:{fs(13)}px; font-weight:600;"
        )
        rl.addWidget(hotkey_input)

        # Delete button
        del_btn = QPushButton("✕")
        del_btn.setFixedSize(28, 28)
        del_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; color:{TEXT3}; border:none;"
            f" font-family:'Segoe UI Emoji','Noto Color Emoji',sans-serif;"
            f" font-size:{fs(16)}px; padding:0; }}"
            f"QPushButton:hover {{ color:#e05555; }}"
        )
        del_btn.clicked.connect(lambda checked, bid=btn.id: self._delete_btn(bid))
        rl.addWidget(del_btn)

        self._rows[btn.id] = (color_combo, spin_b, spin_a, hotkey_input, name)
        return row

    def _delete_btn(self, bid):
        btn = next((b for b in state.buttons if b.id == bid), None)
        if btn:
            clip_count = sum(1 for c in state.clips
                             if getattr(c, 'category', c.name) == btn.label)
            pres_count = sum(
                1 for pres in state.presentations for item in pres
                if getattr(item, 'category', item.name) == btn.label
            )
            if clip_count > 0 or pres_count > 0:
                parts = []
                if clip_count:
                    parts.append(_("{} clip{}").format(clip_count, "s" if clip_count != 1 else ""))
                if pres_count:
                    parts.append(_("{} en presentación").format(pres_count))
                reply = QMessageBox.question(
                    self, _("Borrar botón"),
                    _("El botón '{}' tiene {}.\n¿Borrar igual?").format(
                        btn.label, " y ".join(parts)
                    ),
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Cancel
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
        state.remove_button(bid)
        if bid in self._rows:
            del self._rows[bid]
        self.accept()
        ButtonConfigDialog(self.parent()).exec()

    def _save_and_close(self):
        # Check for duplicate hotkeys
        seen_keys = {}
        for btn in state.buttons:
            if btn.id not in self._rows: continue
            _, _, _, hotkey_input, _ = self._rows[btn.id]
            hk = hotkey_input.text().strip().upper()
            if hk:
                if hk in seen_keys:
                    from PySide6.QtWidgets import QMessageBox
                    QMessageBox.warning(self, _("Hotkey duplicada"),
                        _("La tecla '{}' está asignada a más de un botón.\nCambiá una antes de guardar.").format(hk))
                    return
                seen_keys[hk] = btn.id

        for btn in state.buttons:
            if btn.id not in self._rows:
                continue
            color_combo, spin_b, spin_a, hotkey_input, name_input = self._rows[btn.id]
            btn.color     = color_combo.currentData()
            btn.pad_before = float(spin_b.value())
            btn.pad_after  = float(spin_a.value())
            btn.hotkey     = hotkey_input.text().strip()
            new_label = name_input.text().strip()
            if new_label:
                btn.label = new_label
        state.buttons_changed.emit()
        self.accept()


    def _open_preset_chooser(self):
        from utils.theme_helpers import BG1, BG2, BG3, ACCENT, ACCENT2, ACCENT3, TEXT0, TEXT1, TEXT2, TEXT3, BORDER2
        dlg = QDialog(self)
        dlg.setWindowTitle(_("Cargar preset de deporte"))
        dlg.setFixedWidth(360)
        dlg.setModal(True)
        dlg.setStyleSheet(f"background:{BG1}; color:{TEXT0};")
        lo = QVBoxLayout(dlg)
        lo.setContentsMargins(20, 20, 20, 20)
        lo.setSpacing(10)

        lo.addWidget(QLabel(_("Elegí un deporte:"),
            styleSheet=f"color:{TEXT0}; font-size:{fs(13)}px; font-weight:600;"))

        btn_group = QWidget()
        bg_lo = QVBoxLayout(btn_group)
        bg_lo.setContentsMargins(0, 0, 0, 0)
        bg_lo.setSpacing(6)
        _selected = [None]

        sport_btns = []
        for sport in self.SPORT_PRESETS:
            b = QPushButton(sport)
            b.setCheckable(True)
            b.setFixedHeight(34)
            b.setStyleSheet(f"""
                QPushButton {{ background:{BG2}; color:{TEXT1}; border:1px solid rgba(255,255,255,0.07);
                    border-radius:3px; font-size:{fs(13)}px; text-align:left; padding:0 14px; }}
                QPushButton:checked {{ background:{BG3}; color:{TEXT0}; border-color:{ACCENT}; }}
                QPushButton:hover {{ background:{BG3}; }}
            """)
            def _pick(checked, s=sport, btn=b, others=sport_btns):
                _selected[0] = s if checked else None
                for ob in others:
                    if ob is not btn:
                        ob.setChecked(False)
            b.toggled.connect(_pick)
            sport_btns.append(b)
            bg_lo.addWidget(b)
        lo.addWidget(btn_group)

        sep = QFrame(); sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:rgba(255,255,255,0.06);")
        lo.addWidget(sep)

        replace_cb = QPushButton(_("Reemplazar botonera actual"))
        replace_cb.setCheckable(True)
        replace_cb.setChecked(False)
        replace_cb.setStyleSheet(f"""
            QPushButton {{ background:{BG2}; color:{TEXT2}; border:1px solid rgba(255,255,255,0.07);
                border-radius:3px; font-size:{fs(11)}px; padding:5px 12px; text-align:left; }}
            QPushButton:checked {{ color:{TEXT0}; border-color:{ACCENT2}; }}
        """)
        lo.addWidget(replace_cb)

        btns_row = QHBoxLayout()
        btns_row.addStretch()
        cancel = QPushButton(_("Cancelar"))
        cancel.setStyleSheet(f"QPushButton {{ background:transparent; color:{TEXT2}; border:none; padding:6px 16px; }}")
        cancel.clicked.connect(dlg.reject)
        btns_row.addWidget(cancel)
        load = QPushButton(_("Cargar"))
        load.setStyleSheet(
            f"QPushButton {{ background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            f"stop:0 {ACCENT3},stop:1 {ACCENT}); color:#1a1714; border:none;"
            f" border-bottom:2px solid {ACCENT2}; border-radius:2px; padding:6px 18px;"
            f" font-size:{fs(12)}px; font-weight:600; }}"
            f"QPushButton:hover {{ background:{ACCENT3}; }}"
        )
        load.clicked.connect(dlg.accept)
        btns_row.addWidget(load)
        lo.addLayout(btns_row)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        sport = _selected[0]
        if not sport:
            return

        buttons_def = self.SPORT_PRESETS[sport]
        if replace_cb.isChecked():
            for b in list(state.buttons):
                state.remove_button(b.id)

        for label, color in buttons_def:
            if not any(b.label == label for b in state.buttons):
                state.add_button(label, color)

        # Guardar copia JSON en Documentos/PyScout/Botoneras/
        import os, json
        docs = os.path.join(os.path.expanduser("~"), "Documents", "PyScout", "Buttons")
        os.makedirs(docs, exist_ok=True)
        preset_path = os.path.join(docs, f"{sport}.json")
        try:
            with open(preset_path, "w", encoding="utf-8") as f:
                json.dump({"name": sport, "buttons": [
                    {"label": lbl, "color": clr} for lbl, clr in buttons_def
                ]}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        self.accept()
        ButtonConfigDialog(self.parent()).exec()


class _HotkeyInput(QLineEdit):
    """Input que captura una sola tecla. Sin overrides virtuales C++ — compatible con Nuitka."""
    def __init__(self, current: str, reserved: set, parent=None):
        super().__init__(parent)
        self._reserved = {r.upper() for r in reserved}
        self._saved = (current or "").upper()
        self.setMaxLength(1)
        self.setText(self._saved)
        self.setPlaceholderText("—")
        # focusChanged: limpiar al ganar foco para que el próximo keypress sea reemplazo directo
        # (sin esto, setMaxLength(1) con "P" existente bloquea la inserción de cualquier nuevo char)
        from PySide6.QtWidgets import QApplication
        QApplication.instance().focusChanged.connect(self._on_focus_change)
        self.textEdited.connect(self._on_edited)

    def _on_focus_change(self, old_widget, new_widget):
        if new_widget is self:
            self.setText("")
        elif old_widget is self and not self.text():
            self.setText(self._saved)

    def _on_edited(self, text: str):
        upper = text.upper()
        if upper in self._reserved:
            self.setText("")
        else:
            self._saved = upper
            if text != upper:
                self.setText(upper)