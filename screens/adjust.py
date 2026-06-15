import warnings

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QSizePolicy, QLineEdit, QMessageBox,
    QComboBox, QSplitter, QMenu
)
from PySide6.QtCore import Qt, QSize, QThread, Signal as _Signal
from PySide6.QtGui import QAction

from components.video_player import MpvWidget
from components.timeline import ScrubBar, ClipTimeline
from components.dialogs import ClipEditDialog
from store.state import state, Clip
from styles.theme import fs
from utils.i18n import _
from utils.theme_helpers import (
    BG0, BG1, BG2, BG3, BG4, ACCENT, ACCENT2, ACCENT3,
    DANGER, TEXT0, TEXT1, TEXT2, TEXT3, BORDER, BORDER2,
    CLIP_COLORS, FONT
)
from utils.time_utils import fmt_time
from utils.i18n import _
from icons_helper import play_icon, pause_icon, mute_icon, volume_icon

ROW_EVEN = "#1a1a22"
ROW_ODD  = "#16161e"
ROW_SEL  = "#222230"


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


class AdjustScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_clip: Clip | None = None
        self._loaded_video_path = ""
        self._clip_widgets    = {}
        self._filter_cat      = None
        self._filter_cat_btns = {}
        self._muted = False
        self._build_ui()
        self._connect_state()

    def _build_ui(self):
        from PySide6.QtWidgets import QSplitter
        
        # Usar splitter para permitir redimensionar sidebar con mouse
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {BORDER}; }}")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(splitter)

        # ── Sidebar ───────────────────────────────────────────────────────────
        sidebar = QWidget()
        # Hacer sidebar redimensionable para diferentes tamaños de pantalla
        sidebar.setMinimumWidth(180)  # Mínimo compacto para pantallas pequeñas
        sidebar.setMaximumWidth(320)  # Máximo para pantallas grandes
        sidebar.setObjectName("sidebar_left")
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(0)

        # Header — CLIPS label
        hdr = QWidget()
        hdr.setFixedHeight(28)
        hdr.setStyleSheet("background:transparent;")
        hh = QHBoxLayout(hdr)
        hh.setContentsMargins(12, 0, 12, 0)
        self._clips_lbl = QLabel("CLIPS (0)")
        self._clips_lbl.setStyleSheet(f"""
            color: {ACCENT};
            font-size: {fs(10)}px;
            font-weight: 700;
            letter-spacing: 2px;
        """)
        hh.addWidget(self._clips_lbl)
        sl.addWidget(hdr)

        # Filter bar
        self._filter_bar = QWidget()
        self._filter_bar.setFixedHeight(30)
        self._filter_bar.setStyleSheet("background:transparent;")
        fb = QHBoxLayout(self._filter_bar)
        fb.setContentsMargins(12, 2, 12, 4)
        fb.setSpacing(4)

        self._filter_all_btn = QPushButton(_("Todos"))
        self._filter_all_btn.setFixedHeight(22)
        self._filter_all_btn.setCheckable(True)
        self._filter_all_btn.setChecked(True)
        self._filter_all_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {ACCENT3}, stop:1 {ACCENT2});
                color: #1a1714; border: none;
                border-bottom: 2px solid {ACCENT2};
                border-radius: 2px;
                font-size: {fs(10)}px; font-weight: 600;
                padding: 0 10px;
            }}
            QPushButton:!checked {{
                background: {BG3}; color: {TEXT2}; border-bottom: none;
            }}
            QPushButton:!checked:hover {{
                background: #383840; color: {TEXT0};
            }}
        """)
        self._filter_all_btn.clicked.connect(lambda: self._set_filter(None))
        fb.addWidget(self._filter_all_btn)

        # Combo for >7 categories (hidden by default)
        self._filter_combo_wrap = QWidget()
        self._filter_combo_wrap.setStyleSheet("background:transparent;")
        self._filter_combo_wrap.hide()
        cw = QHBoxLayout(self._filter_combo_wrap)
        cw.setContentsMargins(0, 0, 0, 0)
        cw.setSpacing(0)

        self._filter_combo = QComboBox()
        self._filter_combo.setFixedHeight(28)
        self._filter_combo.setStyleSheet(f"""
            QComboBox {{
                background: {BG3}; color: {TEXT0}; border: none;
                border-bottom: 1px solid {BORDER2};
                font-size: {fs(12)}px; padding: 4px 28px 4px 12px;
            }}
            QComboBox:hover {{ border-bottom: 1px solid {ACCENT}; }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 24px; border: none;
                background: transparent;
            }}
            QComboBox::down-arrow {{
                image: none; width: 0; height: 0;
            }}
            QComboBox QAbstractItemView {{
                background: {BG2}; color: {TEXT0};
                border: 1px solid {BORDER2};
                border-top: 2px solid {ACCENT};
                selection-background-color: {BG3};
                selection-color: {ACCENT};
                font-size: {fs(12)}px;
                padding: 2px 0;
            }}
        """)
        self._filter_combo.currentIndexChanged.connect(self._on_filter_combo_changed)
        cw.addWidget(self._filter_combo, stretch=1)

        # Arrow label overlaid at right side of combo
        self._combo_arrow = QLabel(" ▾")
        self._combo_arrow.setStyleSheet(
            f"color:{ACCENT}; font-size:{fs(11)}px; background:transparent; border:none;")
        self._combo_arrow.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        cw.addWidget(self._combo_arrow)

        fb.addWidget(self._filter_combo_wrap, stretch=1)
        fb.addStretch()

        sl.addWidget(self._filter_bar)
        sl.addSpacing(2)

        # Thin divider
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background: rgba(255,255,255,0.06);")
        sl.addWidget(div)

        # Clip list
        clip_scroll = QScrollArea()
        clip_scroll.setWidgetResizable(True)
        clip_scroll.setFrameShape(QFrame.Shape.NoFrame)
        clip_scroll.setStyleSheet("background:transparent;")
        self._clip_list = QWidget()
        self._clip_list.setStyleSheet("background:transparent;")
        self._clip_list_layout = QVBoxLayout(self._clip_list)
        self._clip_list_layout.setContentsMargins(0, 0, 0, 0)
        self._clip_list_layout.setSpacing(0)
        self._clip_list_layout.addStretch()
        clip_scroll.setWidget(self._clip_list)
        sl.addWidget(clip_scroll, stretch=1)
        splitter.addWidget(sidebar)

        # ── Panel principal ───────────────────────────────────────────────────
        main = QWidget()
        ml = QVBoxLayout(main)
        ml.setContentsMargins(0, 0, 0, 0)
        ml.setSpacing(0)

        self._empty = QLabel("\u25cb\n\n" + _("Seleccioná un clip para editar"))
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setStyleSheet(f"color:{TEXT3}; font-size:{fs(13)}px;")
        ml.addWidget(self._empty)

        self._edit = QWidget()
        self._edit.hide()
        el = QVBoxLayout(self._edit)
        el.setContentsMargins(0, 0, 0, 0)
        el.setSpacing(0)

        edit_vsplit = QSplitter(Qt.Orientation.Vertical)
        edit_vsplit.setHandleWidth(1)
        edit_vsplit.setStyleSheet(f"QSplitter::handle {{ background: rgba(255,255,255,0.06); }}")
        el.addWidget(edit_vsplit, stretch=1)

        top_edit = QWidget()
        tel = QVBoxLayout(top_edit)
        tel.setContentsMargins(0, 0, 0, 0)
        tel.setSpacing(0)

        self._video = MpvWidget()
        self._video.duration_changed.connect(self._on_duration)
        self._video.position_changed.connect(self._on_position)
        self._video.playback_started.connect(lambda: self._play_btn.setIcon(pause_icon(size=(18, 18), color="#1a1714")))
        self._video.playback_paused.connect(lambda: self._play_btn.setIcon(play_icon(size=(18, 18), color="#1a1714")))
        self._video.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        tel.addWidget(self._video, stretch=1)

        # Control bar
        ctrl_bar = QWidget()
        ctrl_bar.setFixedHeight(44)
        ctrl_bar.setObjectName("ctrl_bar")
        cb = QHBoxLayout(ctrl_bar)
        cb.setContentsMargins(12, 0, 12, 0)
        cb.setSpacing(8)

        self._play_btn = QPushButton()
        self._play_btn.setIcon(play_icon(size=(18, 18), color="#1a1714"))
        self._play_btn.setIconSize(QSize(18, 18))
        self._play_btn.setFixedSize(34, 34)
        self._play_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {ACCENT3}, stop:1 {ACCENT});
                border: none;
                border-bottom: 2px solid {ACCENT2};
                border-radius: 4px; padding: 0; icon-size: 18px 18px;
            }}
            QPushButton:hover {{ background: {ACCENT3}; }}
            QPushButton:pressed {{ border-bottom: none; padding-top: 2px; }}
        """)
        self._play_btn.clicked.connect(self._video.toggle_play)
        cb.addWidget(self._play_btn)

        self._mute_btn = QPushButton()
        self._mute_btn.setIcon(volume_icon(size=(18, 18), color=TEXT2))
        self._mute_btn.setIconSize(QSize(18, 18))
        self._mute_btn.setFixedSize(34, 34)
        self._mute_btn.setStyleSheet(f"""
            QPushButton {{ background:transparent; border:none;
                border-bottom:1px solid {BORDER2}; padding:0; icon-size: 18px 18px; }}
            QPushButton:hover {{ border-bottom:1px solid {ACCENT}; }}
        """)
        self._mute_btn.clicked.connect(self._toggle_mute)
        cb.addWidget(self._mute_btn)

        self._pos_lbl = QLabel("0:00:00 / 0:00:00")
        self._pos_lbl.setStyleSheet(f"color:{TEXT2}; font-size:{fs(11)}px; min-width:130px;")
        cb.addWidget(self._pos_lbl)

        self._macro_bar = ScrubBar()
        self._macro_bar.seek_requested.connect(self._video.seek)
        cb.addWidget(self._macro_bar, stretch=1)
        tel.addWidget(ctrl_bar)

        # Bottom fields + timeline
        bottom = QWidget()
        bl = QVBoxLayout(bottom)
        bl.setContentsMargins(14, 6, 14, 4)
        bl.setSpacing(4)

        fields = QHBoxLayout()
        fields.setSpacing(10)
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText(_("Nombre del clip"))
        self._name_input.editingFinished.connect(self._save_name)
        fields.addWidget(self._name_input, stretch=2)
        self._note_input = QLineEdit()
        self._note_input.setPlaceholderText(_("Nota..."))
        self._note_input.editingFinished.connect(self._save_note)
        fields.addWidget(self._note_input, stretch=2)
        bl.addLayout(fields)

        tl_box = QWidget()
        tl_box.setStyleSheet(f"""
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 {BG2}, stop:1 {BG1});
            border-top: 1px solid rgba(255,255,255,0.06);
            border-bottom: 1px solid rgba(255,255,255,0.06);
        """)
        tb = QVBoxLayout(tl_box)
        tb.setContentsMargins(14, 2, 14, 2)
        tb.setSpacing(0)

        tl_hdr = QHBoxLayout()
        tl_hdr.setContentsMargins(0, 0, 0, 2)
        tl_hdr.addStretch()
        for label, slot in [("🔍+", "_zoom_in"), ("🔍−", "_zoom_out")]:
            b = QPushButton(label)
            b.setFixedHeight(22)
            b.setStyleSheet(f"""
                QPushButton {{ background:transparent; color:{TEXT2}; border:none;
                    border-bottom:1px solid {BORDER2}; font-size:{fs(11)}px; padding:2px 8px; }}
                QPushButton:hover {{ color:{ACCENT}; border-bottom:1px solid {ACCENT}; }}
            """)
            b.clicked.connect(getattr(self, slot))
            tl_hdr.addWidget(b)
        tb.addLayout(tl_hdr)

        self._timeline = ClipTimeline()
        self._timeline.scrub_requested.connect(self._video.seek)
        self._timeline.start_changed.connect(self._on_start_changed)
        self._timeline.end_changed.connect(self._on_end_changed)
        tb.addWidget(self._timeline)
        bl.addWidget(tl_box)

        actions = QHBoxLayout()
        add_btn = QPushButton(_("+ Agregar a presentación"))
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {ACCENT3}, stop:1 {ACCENT});
                color: #1a1714; border: none;
                border-bottom: 2px solid {ACCENT2};
                border-radius: 1px; font-size:{fs(12)}px; font-weight:600; padding:2px 14px;
            }}
            QPushButton:hover {{ background:{ACCENT3}; }}
            QPushButton:pressed {{ border-bottom:none; padding-top:4px; }}
        """)
        add_btn.clicked.connect(self._add_to_presentation)
        actions.addWidget(add_btn)

        edit_btn = QPushButton(_("Editar detalle"))
        edit_btn.setStyleSheet(f"""
            QPushButton {{ background:transparent; color:{TEXT2}; border:none;
                border-bottom:1px solid {BORDER2}; border-radius:1px; font-size:{fs(11)}px; padding:2px 10px; }}
            QPushButton:hover {{ color:{TEXT0}; border-bottom:1px solid {ACCENT}; }}
        """)
        edit_btn.clicked.connect(lambda: self._open_edit_dialog())
        actions.addWidget(edit_btn)
        actions.addStretch()
        self._dur_lbl = QLabel(_("Duración: —"))
        self._dur_lbl.setStyleSheet(f"color:{TEXT3}; font-size:{fs(12)}px;")
        actions.addWidget(self._dur_lbl)
        bl.addLayout(actions)

        self._edit_vsplit = edit_vsplit
        bottom.setMinimumHeight(180)
        edit_vsplit.addWidget(top_edit)
        edit_vsplit.addWidget(bottom)
        edit_vsplit.setSizes([500, 200])
        edit_vsplit.setStretchFactor(0, 1)
        edit_vsplit.setStretchFactor(1, 0)

        ml.addWidget(self._edit, stretch=1)
        self._h_splitter = splitter
        splitter.addWidget(main)

        # Configurar proporciones iniciales del splitter (sidebar: 240px, resto: main)
        splitter.setSizes([240, 800])  # Valores iniciales, el usuario puede ajustar
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def _connect_state(self):
        state.clips_changed.connect(self._sync_clips)
        state.clips_changed.connect(self._rebuild_filter_bar)
        self._rebuild_filter_bar()
        self._sync_clips()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Space:
            self._video.toggle_play()
            e.accept()
        elif e.key() == Qt.Key.Key_3:
            self._add_to_presentation()
        else:
            super().keyPressEvent(e)

    # ── Filtros ───────────────────────────────────────────────────────────────

    _MAX_FILTER_BTNS = 0  # Siempre usar dropdown

    def _rebuild_filter_bar(self):
        cats = list(dict.fromkeys(
            getattr(c, 'category', '') or c.name for c in state.clips
        ))
        use_combo = len(cats) > self._MAX_FILTER_BTNS

        # ── Clean up existing category buttons ────────────────────────────────
        for cat in list(self._filter_cat_btns.keys()):
            btn = self._filter_cat_btns.pop(cat)
            try:
                self._filter_bar.layout().removeWidget(btn)
                btn.deleteLater()
            except RuntimeError:
                pass

        if use_combo:
            # ── Combo mode ────────────────────────────────────────────────────
            self._filter_all_btn.hide()
            self._filter_combo.blockSignals(True)
            self._filter_combo.clear()
            self._filter_combo.addItem(_("Todos"), None)
            for cat in cats:
                self._filter_combo.addItem(cat, cat)
            # Restore current selection
            if self._filter_cat and self._filter_cat in cats:
                idx = cats.index(self._filter_cat) + 1  # +1 for "Todo"
                self._filter_combo.setCurrentIndex(idx)
            else:
                self._filter_combo.setCurrentIndex(0)
            self._filter_combo.blockSignals(False)
            self._filter_combo_wrap.show()
        else:
            # ── Button mode ───────────────────────────────────────────────────
            self._filter_combo_wrap.hide()
            self._filter_all_btn.show()
            for cat in cats:
                btn = QPushButton(cat)
                btn.setFixedHeight(22)
                btn.setCheckable(True)
                btn.setChecked(cat == self._filter_cat)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {BG3}; color: {TEXT2}; border: none;
                        border-radius: 2px; font-size: {fs(10)}px; padding: 0 10px;
                    }}
                    QPushButton:hover {{ background: #383840; color: {TEXT0}; }}
                    QPushButton:checked {{
                        background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                            stop:0 {ACCENT3}, stop:1 {ACCENT});
                        color: #1a1714;
                    }}
                """)
                btn.clicked.connect(lambda checked, c=cat: self._set_filter(c))
                try:
                    layout = self._filter_bar.layout()
                    # Insert before stretch (last item)
                    layout.insertWidget(layout.count() - 1, btn)
                    self._filter_cat_btns[cat] = btn
                except RuntimeError:
                    pass

    def _on_filter_combo_changed(self, index):
        cat = self._filter_combo.currentData()
        self._filter_cat = cat
        self._sync_clips()

    def _set_filter(self, cat):
        self._filter_cat = cat
        self._filter_all_btn.setChecked(cat is None)
        for c, btn in self._filter_cat_btns.items():
            btn.setChecked(c == cat)
        # Also sync combo if visible
        if self._filter_combo_wrap.isVisible():
            self._filter_combo.blockSignals(True)
            if cat is None:
                self._filter_combo.setCurrentIndex(0)
            else:
                idx = self._filter_combo.findData(cat)
                if idx >= 0:
                    self._filter_combo.setCurrentIndex(idx)
            self._filter_combo.blockSignals(False)
        self._sync_clips()

    def _get_filtered(self):
        if self._filter_cat is None:
            return state.clips
        return [c for c in state.clips
                if (getattr(c, 'category', '') or c.name) == self._filter_cat]

    # ── Lista ─────────────────────────────────────────────────────────────────

    def _sync_clips(self):
        filtered    = self._get_filtered()
        current_ids = {c.id for c in filtered}
        for cid in set(self._clip_widgets) - current_ids:
            w = self._clip_widgets.pop(cid)
            try:
                self._clip_list_layout.removeWidget(w)
                w.deleteLater()
            except RuntimeError:
                pass
        for i, clip in enumerate(filtered):
            if clip.id not in self._clip_widgets:
                row = self._make_clip_row(clip, i)
                self._clip_list_layout.insertWidget(i, row)
                self._clip_widgets[clip.id] = row
        total = len(state.clips)
        shown = len(filtered)
        self._clips_lbl.setText(f"CLIPS ({shown}/{total})" if self._filter_cat else f"CLIPS ({total})")

        # Si el clip seleccionado ya no existe (proyecto nuevo/limpiado), volver al estado vacío
        if self._selected_clip and self._selected_clip.id not in {c.id for c in state.clips}:
            self._selected_clip = None
            self._loaded_video_path = ""
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                try:
                    self._video.file_loaded.disconnect()
                except Exception:
                    pass
            self._video.pause()
            self._edit.hide()
            self._empty.show()

    def _make_clip_row(self, clip: Clip, idx: int = 0) -> QWidget:
        bg = ROW_EVEN if idx % 2 == 0 else ROW_ODD
        row = QWidget()
        row.setFixedHeight(52)
        row.setProperty("row_bg", bg)
        row.setStyleSheet(f"QWidget {{ background:{bg}; border:none; }}")
        row.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        rl = QHBoxLayout(row)
        rl.setContentsMargins(12, 0, 10, 0)
        rl.setSpacing(8)

        # Dot indicator: transparent by default, gold-transparent on hover, gold on select
        dot = QLabel()
        dot.setFixedSize(7, 7)
        dot.setObjectName(f"dot_{clip.id}")
        dot.setStyleSheet("background:transparent; border-radius:3px;")
        rl.addWidget(dot)

        info = QWidget()
        info.setStyleSheet("background:transparent;")
        il = QVBoxLayout(info)
        il.setContentsMargins(0, 0, 0, 0)
        il.setSpacing(2)
        n = QLabel(clip.name)
        n.setStyleSheet(f"color:{TEXT0}; font-size:{fs(13)}px; font-weight:600; background:transparent;")
        il.addWidget(n)
        m = QLabel(f"{clip.video_name}  ·  {clip.timestamp}")
        m.setStyleSheet(f"color:{TEXT2}; font-size:{fs(10)}px; background:transparent;")
        il.addWidget(m)
        if clip.note:
            nt = QLabel(clip.note[:40] + ("..." if len(clip.note) > 40 else ""))
            nt.setStyleSheet(f"color:{TEXT3}; font-size:{fs(10)}px; font-style:italic; background:transparent;")
            il.addWidget(nt)
        rl.addWidget(info, stretch=1)

        del_btn = QPushButton("×")
        del_btn.setFixedSize(24, 24)
        del_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; color:{TEXT3}; border:none;"
            f" font-size:{fs(14)}px; font-weight:700; padding:0; }}"
            f"QPushButton:hover {{ color:{DANGER}; }}"
        )
        del_btn.setToolTip(_("Eliminar registro"))
        del_btn.clicked.connect(lambda checked, c=clip: self._confirm_delete_clip(c))
        rl.addWidget(del_btn)

        # Hover: show semi-transparent gold dot
        _orig_enter = row.enterEvent
        _orig_leave = row.leaveEvent
        def _on_enter(e, r=row, d=dot, cid=clip.id):
            is_sel = self._selected_clip and self._selected_clip.id == cid
            r.setStyleSheet(f"QWidget {{ background:{BG2}; border:none; }}")
            if not is_sel:
                d.setStyleSheet(f"background:rgba(201,164,74,0.35); border-radius:3px;")
            if _orig_enter: _orig_enter(e)
        def _on_leave(e, r=row, d=dot, cid=clip.id, bg_val=bg):
            is_sel = self._selected_clip and self._selected_clip.id == cid
            if is_sel:
                r.setStyleSheet(f"QWidget {{ background:{ROW_SEL}; border:none; }}")
            else:
                r.setStyleSheet(f"QWidget {{ background:{bg_val}; border:none; }}")
                d.setStyleSheet("background:transparent; border-radius:3px;")
            if _orig_leave: _orig_leave(e)
        row.enterEvent = _on_enter
        row.leaveEvent = _on_leave

        def _row_press(e, c=clip):
            if e.button() == Qt.MouseButton.RightButton:
                self._show_clip_context_menu(c, e.globalPosition().toPoint())
            else:
                self._select_clip(c)
        row.mousePressEvent       = _row_press
        row.mouseDoubleClickEvent = lambda e, c=clip: self._open_edit_dialog(c)
        return row

    # ── Selección ─────────────────────────────────────────────────────────────

    def _select_clip(self, clip: Clip):
        # Deselect previous
        if self._selected_clip and self._selected_clip.id in self._clip_widgets:
            prev = self._clip_widgets[self._selected_clip.id]
            bg = prev.property("row_bg") or ROW_EVEN
            prev.setStyleSheet(f"QWidget {{ background:{bg}; border:none; }}")
            d = prev.findChild(QLabel, f"dot_{self._selected_clip.id}")
            if d: d.setStyleSheet("background:transparent; border-radius:3px;")

        # Select new
        self._selected_clip = clip
        if clip.id in self._clip_widgets:
            w = self._clip_widgets[clip.id]
            w.setStyleSheet(f"QWidget {{ background:{ROW_SEL}; border:none; }}")
            d = w.findChild(QLabel, f"dot_{clip.id}")
            if d: d.setStyleSheet(f"background:{ACCENT}; border-radius:3px;")

        self._name_input.setText(clip.name)
        self._note_input.setText(clip.note)
        self._timeline.reset(
            clip.time_sec,
            start_off=clip.start_sec - clip.time_sec,
            end_off=clip.end_sec - clip.time_sec)
        self._update_dur_label()
        self._empty.hide()
        self._edit.show()
        if clip.video_path != self._loaded_video_path:
            self._loaded_video_path = clip.video_path
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                try:
                    self._video.file_loaded.disconnect()
                except Exception:
                    pass
            self._video.file_loaded.connect(lambda: self._do_seek(clip.time_sec))
            self._video.load(clip.video_path)
        else:
            self._video.seek(clip.time_sec)

    def _do_seek(self, sec: float):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            try:
                self._video.file_loaded.disconnect()
            except Exception:
                pass
        self._video.seek(sec)

    # ── Controles ─────────────────────────────────────────────────────────────

    def _toggle_mute(self):
        self._muted = not self._muted
        try:
            if self._video._player: self._video._player.mute = self._muted
        except Exception: pass
        self._mute_btn.setIcon(mute_icon(size=(18, 18), color=TEXT2) if self._muted else volume_icon(size=(18, 18), color=TEXT2))

    def _on_duration(self, d: float):
        self._macro_bar.set_duration(d)

    def _on_position(self, t: float):
        self._macro_bar.set_position(t)
        self._pos_lbl.setText(f"{fmt_time(t)} / {fmt_time(self._video.duration)}")
        self._timeline.update_playhead(t)

    def _on_start_changed(self, offset: float):
        if self._selected_clip:
            state.update_clip(self._selected_clip.id, start_sec=self._selected_clip.time_sec + offset)
            self._update_dur_label()

    def _on_end_changed(self, offset: float):
        if self._selected_clip:
            state.update_clip(self._selected_clip.id, end_sec=self._selected_clip.time_sec + offset)
            self._update_dur_label()

    def _zoom_in(self):   self._timeline.zoom_in()
    def _zoom_out(self):  self._timeline.zoom_out()

    def _recenter(self):
        if self._selected_clip:
            c = self._selected_clip
            self._timeline.reset(c.time_sec, start_off=c.start_sec-c.time_sec, end_off=c.end_sec-c.time_sec)
            self._video.seek(c.start_sec)

    def _save_name(self):
        if self._selected_clip:
            state.update_clip(self._selected_clip.id, name=self._name_input.text())

    def _save_note(self):
        if self._selected_clip:
            state.update_clip(self._selected_clip.id, note=self._note_input.text())

    def _update_dur_label(self):
        self._dur_lbl.setText(_("Duración: {}s").format(f"{self._timeline.duration:.1f}"))

    def _add_to_presentation(self):
        if self._selected_clip:
            state.add_clip_to_presentation(
                self._selected_clip,
                clip_start=self._timeline.start_sec,
                clip_dur=self._timeline.duration)

    def _open_edit_dialog(self, clip=None):
        c = clip or self._selected_clip
        if not c: return
        dlg = ClipEditDialog(c.name, c.note, c.color, self)
        if dlg.exec():
            state.update_clip(c.id, name=dlg.name, note=dlg.note, color=dlg.color)
            if self._selected_clip and c.id == self._selected_clip.id:
                self._name_input.setText(dlg.name)
                self._note_input.setText(dlg.note)

    def _confirm_delete_clip(self, clip: Clip):
        dlg = QMessageBox(self)
        dlg.setWindowTitle(_("Eliminar registro"))
        dlg.setText(_('¿Eliminar "{}" ({})?').format(clip.name, clip.timestamp))
        dlg.setInformativeText(_("Esta acción se puede deshacer con Ctrl+Z."))
        ok = dlg.addButton(_("Eliminar"), QMessageBox.ButtonRole.DestructiveRole)
        dlg.addButton(_("Cancelar"), QMessageBox.ButtonRole.RejectRole)
        dlg.exec()
        if dlg.clickedButton() == ok:
            if self._selected_clip and self._selected_clip.id == clip.id:
                self._selected_clip = None
                self._edit.hide()
                self._empty.show()
            state.remove_clip(clip.id)

    def _show_clip_context_menu(self, clip: Clip, pos):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background:{BG2}; border:1px solid {BORDER2}; padding:4px 0; color:{TEXT0}; }}
            QMenu::item {{ padding:7px 20px; font-size:{fs(13)}px; }}
            QMenu::item:selected {{ background:{BG3}; color:{ACCENT}; }}
            QMenu::separator {{ height:1px; background:{BORDER}; margin:3px 0; }}
        """)
        act_export = QAction(_("Exportar clip"), menu)
        act_export.triggered.connect(lambda: self._export_clip(clip))
        menu.addAction(act_export)
        menu.addSeparator()
        act_pres = QAction(_("Agregar a presentación"), menu)
        act_pres.triggered.connect(lambda: state.add_clip_to_presentation(
            clip,
            clip_start=self._timeline.start_sec if self._selected_clip and self._selected_clip.id == clip.id else clip.start_sec,
            clip_dur=self._timeline.duration if self._selected_clip and self._selected_clip.id == clip.id else max(0.1, clip.end_sec - clip.start_sec),
        ))
        menu.addAction(act_pres)
        menu.exec(pos)

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
        # Si el clip está seleccionado usamos los tiempos ajustados del timeline
        if self._selected_clip and self._selected_clip.id == clip.id:
            start = self._timeline.start_sec
            dur   = self._timeline.duration
        else:
            start = clip.start_sec
            dur   = max(0.1, clip.end_sec - clip.start_sec)
        clip_dict = {"video_path": clip.video_path, "clip_start": start, "clip_dur": dur}
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