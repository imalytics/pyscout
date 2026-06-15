import os, json
from pathlib import Path as _Path
from utils.i18n import _

def _docs_folder(sub: str = "") -> str:
    """Ruta a la carpeta PyScout en Documentos."""
    if os.name == "nt":
        docs = _Path(os.path.expanduser("~/Documents"))
    else:
        docs = _Path.home() / "Documents"
    root = docs / "PyScout"
    if sub:
        return str(root / sub)
    return str(root)

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QStackedWidget,
    QMenuBar, QMenu, QMessageBox, QApplication, QDialog,
    QVBoxLayout as QVL, QHBoxLayout as QHL, QTextEdit,
    QScrollArea, QFrame, QSplitter
)
from PySide6.QtCore import Qt, QSettings, QTimer
from PySide6.QtGui import QKeySequence, QShortcut, QFont, QAction, QIcon

from screens.observation  import ObservationScreen
from screens.adjust       import AdjustScreen
from screens.presentation import PresentationScreen
from components.toast     import Toast
from store.state          import state
from styles.theme import (
    build_style, FONT, fs,
    BG0, BG1, BG2, BG3,
    TEXT0, TEXT1, TEXT2, TEXT3,
    ACCENT, ACCENT2, ACCENT3, BORDER, BORDER2
)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyScout")
        _icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ico.ico")
        if os.path.exists(_icon_path):
            self.setWindowIcon(QIcon(_icon_path))
        self.setMinimumSize(1100, 700)
        self.resize(1380, 860)
        from styles.theme import load_saved_theme
        load_saved_theme()
        self._mute_all = False
        self._font_scale = 1.0
        self._current_path_val = ""
        self._autosave_path: str = ""
        self._autosave_enabled = True
        self._autosave_locked = False
        self._build_ui()
        self._build_menubar()
        self._connect_state()
        self._setup_shortcuts()
        try:
            from utils.updater import UpdateChecker
            self._updater = UpdateChecker()
            self._pending_update = {}
            self._updater.update_available.connect(self._on_update_available)
            self._updater.check()
        except Exception:
            pass
        # Licencia se gestiona desde StartDialog
        self._setup_tour()
        self._check_whats_new()
        self.showMaximized()
        QTimer.singleShot(0, self._apply_native_dark_titlebar)

    def _apply_native_dark_titlebar(self):
        if os.name != "nt":
            return
        try:
            import ctypes
            hwnd = int(self.winId())
            dwm = ctypes.windll.dwmapi
            use_dark = ctypes.c_int(1)
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            dwm.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE,
                ctypes.byref(use_dark), ctypes.sizeof(use_dark))
            def colorref(r, g, b):
                return ctypes.c_uint(r | (g << 8) | (b << 16))
            for attr, val in ((35, colorref(18, 20, 24)), (36, colorref(230, 232, 235)), (34, colorref(35, 40, 48))):
                try:
                    dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(val), ctypes.sizeof(val))
                except Exception:
                    pass
        except Exception:
            pass

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._titlebar = QWidget()
        self._titlebar.setFixedHeight(48)
        self._apply_titlebar_style()
        tbl = QHBoxLayout(self._titlebar)
        tbl.setContentsMargins(20, 0, 16, 0)
        tbl.setSpacing(0)

        self._brand = QLabel("PyScout")
        self._brand.setStyleSheet(
            f"font-family:Georgia,'Times New Roman',serif;"
            f" font-weight:700; font-size:{fs(18)}px;"
            f" color:#C9A44A; letter-spacing:0.5px;"
            f" padding-right:12px; border:none;")
        self._rebuild_menubar_style()
        tbl.addWidget(self._brand)
        tbl.addSpacing(24)

        self._tabs = []
        for i, label in enumerate([_("Observación"), _("Ajuste"), _("Presentación")]):
            btn = QPushButton(label)
            btn.setObjectName("tab_active" if i == 0 else "tab")
            btn.clicked.connect(lambda checked, idx=i: self._switch_screen(idx))
            tbl.addWidget(btn)
            self._tabs.append(btn)

        for _sc_idx, _sc in enumerate(["Ctrl+1", "Ctrl+2", "Ctrl+3"]):
            _sc_action = QAction(self)
            _sc_action.setShortcut(QKeySequence(_sc))
            _sc_action.triggered.connect(lambda checked, i=_sc_idx: self._switch_screen(i))
            self.addAction(_sc_action)

        tbl.addStretch()

        self._project_lbl = QLabel("")
        self._project_lbl.setStyleSheet(f"color:{TEXT3}; font-size:{fs(11)}px; margin-right:8px;")
        tbl.addWidget(self._project_lbl)

        _undo_redo_style = (
            f"QPushButton {{ background:transparent; color:{TEXT3}; border:none;"
            f" font-size:{fs(12)}px; padding:4px 8px; }}"
            f"QPushButton:hover {{ color:{ACCENT}; }}"
            f"QPushButton:disabled {{ color:{BG3}; }}")
        self._undo_btn = QPushButton(_("↩ Deshacer"))
        self._undo_btn.setStyleSheet(_undo_redo_style)
        self._undo_btn.setEnabled(False)
        self._undo_btn.clicked.connect(state.undo)
        tbl.addWidget(self._undo_btn)

        self._redo_btn = QPushButton(_("Rehacer ↪"))
        self._redo_btn.setStyleSheet(_undo_redo_style)
        self._redo_btn.setEnabled(False)
        self._redo_btn.clicked.connect(state.redo)
        tbl.addWidget(self._redo_btn)

        layout.addWidget(self._titlebar)

        self._title_sep = QWidget()
        self._title_sep.setFixedHeight(1)
        self._title_sep.setStyleSheet("background: rgba(201,164,74,0.35); border:none;")
        layout.addWidget(self._title_sep)

        self._stack       = QStackedWidget()
        self._obs_screen  = ObservationScreen()
        self._adj_screen  = AdjustScreen()
        self._pres_screen = PresentationScreen()
        self._stack.addWidget(self._obs_screen)
        self._stack.addWidget(self._adj_screen)
        self._stack.addWidget(self._pres_screen)
        self._pres_screen.navigate_to_adjust.connect(self._goto_adjust)
        layout.addWidget(self._stack, stretch=1)

        self._toast = Toast(central)
        self._toast.raise_()

    def _build_menubar(self):
        mb = self.menuBar()
        mb.setStyleSheet(f"""
            QMenuBar {{ background: {BG1}; color: {TEXT1}; font-family: {FONT};
                font-size: {fs(13)}px; border-bottom: none; padding: 0 8px; }}
            QMenuBar::item {{ background: transparent; padding: 6px 14px; border-radius: 2px; }}
            QMenuBar::item:selected {{ background: {BG2}; color: {ACCENT}; }}
            QMenuBar::item:pressed {{ background: {BG3}; color: {ACCENT}; }}
            QMenu {{ background: {BG1}; color: {TEXT0}; border: 1px solid {BORDER2};
                border-top: 2px solid {ACCENT}; border-radius: 0; padding: 4px 0;
                font-family: {FONT}; font-size: {fs(13)}px; }}
            QMenu::item {{ padding: 8px 32px 8px 20px; border-left: 3px solid transparent; }}
            QMenu::item:selected {{ background: {BG2}; color: {ACCENT}; border-left: 3px solid {ACCENT}; }}
            QMenu::item:disabled {{ color: {TEXT3}; }}
            QMenu::separator {{ height: 1px; background: {BORDER}; margin: 3px 0; }}
            QMenu::indicator {{ width: 16px; height: 16px; margin-left: 4px; }}
            QMenu::indicator:checked {{ color: {ACCENT}; }}""")

        m_archivo = mb.addMenu(_("Archivo"))
        m_archivo.addAction(self._act(_("Nuevo proyecto"), self._new_project, "Ctrl+N"))
        m_archivo.addSeparator()
        m_archivo.addAction(self._act(_("Abrir proyecto..."), self._load_project, "Ctrl+O"))
        self._recent_menu = m_archivo.addMenu(_("Recientes"))
        self._rebuild_recent_menu()
        m_archivo.addSeparator()
        m_archivo.addAction(self._act(_("Guardar"), self._save_project, "Ctrl+S"))
        m_archivo.addAction(self._act(_("Guardar como..."), self._save_project_as, "Ctrl+Shift+S"))

        m_opciones = mb.addMenu(_("Opciones"))
        self._act_autosave = QAction(_("Activar autoguardado"), self)
        self._act_autosave.setCheckable(True)
        self._act_autosave.setChecked(True)
        self._act_autosave.triggered.connect(self._toggle_autosave)
        m_opciones.addAction(self._act_autosave)
        m_opciones.addSeparator()

        self._act_mute_all = QAction(_("Silenciar todos los videos"), self)
        self._act_mute_all.setCheckable(True)
        self._act_mute_all.setChecked(False)
        self._act_mute_all.triggered.connect(self._toggle_mute_all)
        m_opciones.addAction(self._act_mute_all)

        m_opciones.addSeparator()

        m_lang = m_opciones.addMenu(_("Idioma"))
        from utils.i18n import current_language
        for lang_code, lang_label in [("es", "Español"), ("en", "English")]:
            a = QAction(lang_label, self)
            a.setCheckable(True)
            a.setChecked(lang_code == current_language())
            a.triggered.connect(lambda checked, lc=lang_code: self._set_language(lc))
            m_lang.addAction(a)
        self._lang_actions = m_lang.actions()
        m_opciones.addSeparator()

        m_font = m_opciones.addMenu(_("Tamaño del texto"))
        for label, scale in [(_("Normal (100%)"), 1.0), (_("Grande (150%)"), 1.5), (_("Muy grande (200%)"), 2.0)]:
            a = QAction(label, self)
            a.setCheckable(True)
            a.setChecked(scale == 1.0)
            a.triggered.connect(lambda checked, s=scale: self._set_font_scale(s))
            m_font.addAction(a)
        self._font_scale_actions = m_font.actions()

        m_botonera = mb.addMenu(_("Botonera"))
        m_botonera.addAction(self._act(_("Nueva botonera"), self._new_buttons))
        m_botonera.addSeparator()
        m_botonera.addAction(self._act(_("Abrir botonera..."), self._load_buttons))
        m_botonera.addAction(self._act(_("Guardar botonera..."), self._save_buttons))

        m_ventana = mb.addMenu(_("Ventana"))
        self._act_fullscreen = QAction(_("Pantalla completa"), self)
        self._act_fullscreen.setCheckable(True)
        self._act_fullscreen.setShortcut(QKeySequence("F11"))
        self._act_fullscreen.triggered.connect(self._toggle_window_fullscreen)
        m_ventana.addAction(self._act_fullscreen)
        m_ventana.addSeparator()
        m_ventana.addAction(self._act(_("Restaurar disposición"), self._restore_layout))

        m_config = mb.addMenu(_("Configuraciones"))
        m_config.addAction(self._act(_("Buscar actualizaciones"), self._check_updates))
        m_config.addAction(self._act(_("Instalar códecs"), self._install_codecs))

        m_help = mb.addMenu(_("Ayuda"))
        m_help.addAction(self._act(_("¿Cómo funciona?"), self._show_help))
        m_help.addAction(self._act(_("Reiniciar tour de bienvenida"), self._restart_tour))
        m_help.addSeparator()
        m_help.addAction(self._act(_("Feedback"), self._show_feedback))
        m_help.addSeparator()
        m_help.addAction(self._act(_("Acerca de PyScout"), self._show_about))
        self.setMenuBar(mb)

    def _act(self, label, slot, shortcut=None):
        a = QAction(label, self)
        if shortcut:
            a.setShortcut(QKeySequence(shortcut))
        a.triggered.connect(slot)
        return a

    def _rebuild_menubar_style(self):
        mb = self.menuBar()
        mb.setStyleSheet(f"""
            QMenuBar {{ background:{BG1}; color:{TEXT1}; font-family:{FONT}; font-size:{fs(13)}px;
                border-bottom:1px solid {BORDER}; padding:0 8px; }}
            QMenuBar::item {{ background:transparent; padding:6px 14px; border-radius:2px; }}
            QMenuBar::item:selected {{ background:{BG2}; color:{ACCENT}; }}
            QMenu {{ background:{BG1}; color:{TEXT0}; border:1px solid {BORDER2};
                border-top:2px solid {ACCENT}; border-radius:0; padding:4px 0;
                font-family:{FONT}; font-size:{fs(13)}px; }}
            QMenu::item {{ padding:8px 32px 8px 20px; border-left:3px solid transparent; }}
            QMenu::item:selected {{ background:{BG2}; color:{ACCENT}; border-left:3px solid {ACCENT}; }}
            QMenu::item:disabled {{ color:{TEXT3}; }}
            QMenu::separator {{ height:1px; background:{BORDER}; margin:3px 0; }}""")

    def _apply_titlebar_style(self):
        self._titlebar.setStyleSheet("background:#0a0a0c; border:none;")

    def _toggle_window_fullscreen(self):
        if self.isFullScreen():
            self.showMaximized()
            self._act_fullscreen.setChecked(False)
        else:
            self.showFullScreen()
            self._act_fullscreen.setChecked(True)

    def _restore_layout(self):
        obs = self._obs_screen
        adj = self._adj_screen
        if hasattr(obs, '_splitter'):
            obs._splitter.setSizes([230, 900])
        if hasattr(obs, '_right_vsplit'):
            obs._right_vsplit.setSizes([500, 160])
        if hasattr(adj, '_h_splitter'):
            adj._h_splitter.setSizes([240, 800])
        if hasattr(adj, '_edit_vsplit'):
            adj._edit_vsplit.setSizes([500, 175])

    def _connect_state(self):
        state.toast_requested.connect(self._toast.show_message)
        state.project_changed.connect(self._on_project_changed)
        # Autosave — cualquier cambio de datos dispara guardado
        for sig in (state.buttons_changed, state.clips_changed,
                    state.presentation_changed, state.sources_changed,
                    state.presentations_changed, state.overlay_changed):
            sig.connect(self._autosave)
        state.undo_redo_changed.connect(self._on_undo_redo)

    def _on_project_changed(self, name: str):
        """Actualizar label y título de ventana con el nombre del proyecto."""
        self._project_lbl.setText(name)
        self.setWindowTitle(f"{name} — PyScout" if name else "PyScout")

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+Z"), self).activated.connect(state.undo)
        QShortcut(QKeySequence("Ctrl+Shift+Z"), self).activated.connect(state.redo)

    def _on_undo_redo(self, can_undo, can_redo):
        self._undo_btn.setEnabled(can_undo)
        self._redo_btn.setEnabled(can_redo)

    def closeEvent(self, event):
        """Cancelar render activo antes de cerrar para no dejar procesos zombie."""
        rt = getattr(self._pres_screen, '_render_thread', None)
        if rt and rt.isRunning():
            rt.cancel()
            rt.wait(3000)
        event.accept()

    def _switch_screen(self, idx):
        # Pausar el player de la pantalla que se abandona para liberar el
        # slot de hardware decoding (evita interferencia entre instancias mpv)
        prev = self._stack.currentIndex()
        if prev != idx:
            from components.video_player import MpvWidget
            leaving = self._stack.widget(prev)
            for mpv_w in leaving.findChildren(MpvWidget):
                try:
                    if not mpv_w._paused:
                        mpv_w.pause()
                except Exception:
                    pass
        self._stack.setCurrentIndex(idx)
        for i, btn in enumerate(self._tabs):
            btn.setObjectName("tab_active" if i == idx else "tab")
            btn.style().unpolish(btn); btn.style().polish(btn)

    def _goto_adjust(self, category):
        self._switch_screen(1)
        for clip in state.clips:
            if getattr(clip, 'category', clip.name) == category:
                try: self._adj_screen._select_clip(clip)
                except Exception: pass
                break

    # ── Mute global ───────────────────────────────────────────────────────────
    def _toggle_mute_all(self, checked):
        """Modo Silencio — mutea/desmutea TODOS los players existentes y futuros."""
        self._mute_all = checked
        state.global_mute = checked
        state.global_mute_changed.emit(checked)
        state.toast_requested.emit(
            _("Modo silencio activado") if checked else _("Audio activado"))

    def _set_font_scale(self, scale):
        self._font_scale = scale
        from styles.theme import set_font_scale
        set_font_scale(scale)
        QApplication.instance().setStyleSheet(build_style())
        self._rebuild_screens()
        self._apply_titlebar_style()
        for a in self._font_scale_actions:
            a.setChecked(str(int(scale*100)) in a.text())
        state.toast_requested.emit(_("Escala: {}%").format(int(scale*100)))

    def _set_language(self, lang_code: str):
        from utils.i18n import save_language
        save_language(lang_code)
        for a in self._lang_actions:
            a.setChecked(a.text() in {"Español": "es", "English": "en"} and
                         {"Español": "es", "English": "en"}[a.text()] == lang_code)
        state.toast_requested.emit(_("Reiniciá la app para aplicar el idioma"))

    def _reset_prefs(self):
        from styles.theme import set_font_scale
        set_font_scale(1.0)
        self._font_scale = 1.0
        for a in self._font_scale_actions:
            a.setChecked("100%" in a.text())
        QApplication.instance().setStyleSheet(build_style())
        self._rebuild_screens()
        self._apply_titlebar_style()
        state.toast_requested.emit(_("Preferencias restablecidas"))

    # ── Proyecto ─────────────────────────────────────────────────────────────
    def _new_project(self):
        """Nuevo proyecto desde menú Archivo — pide nombre y crea archivo."""
        if state.clips or state.buttons or state.presentation:
            dlg = QMessageBox(self)
            dlg.setWindowTitle(_("Nuevo proyecto"))
            dlg.setText(_("¿Guardás el proyecto actual?"))
            s = dlg.addButton(_("Guardar"), QMessageBox.ButtonRole.AcceptRole)
            dlg.addButton(_("Sin guardar"), QMessageBox.ButtonRole.DestructiveRole)
            c = dlg.addButton(_("Cancelar"), QMessageBox.ButtonRole.RejectRole)
            dlg.exec()
            if dlg.clickedButton() == c: return
            if dlg.clickedButton() == s: self._save_project()

        # Modal para nombre
        from PySide6.QtWidgets import QDialog, QInputDialog
        name, ok = QInputDialog.getText(self, _("Nuevo proyecto"), _("Nombre del proyecto:"),
                                        text=_("Sin título"))
        if not ok or not name.strip():
            return
        name = name.strip()

        # Crear archivo en Documentos/PyScout/Proyectos/
        safe = "".join(c for c in name if c.isalnum() or c in " _-().").strip() or "Proyecto"
        path = os.path.join(_docs_folder("Projects"), f"{safe}.scout")
        counter = 1
        base = path
        while os.path.exists(path):
            path = base.replace(".scout", f" ({counter}).scout")
            counter += 1

        self._create_new_project(path)

    def _save_project(self):
        current = getattr(self, "_current_path_val", "")
        if not current:
            self._save_project_as()
            return
        if state.save_to_file(current):
            state.toast_requested.emit(_("Guardado"))

    @property
    def _current_path(self):
        return getattr(self, "_current_path_val", "")

    @_current_path.setter
    def _current_path(self, v):
        self._current_path_val = v
        self._autosave_path = ""

    def _save_project_as(self):
        path, _filt = QFileDialog.getSaveFileName(self, _("Guardar proyecto"),
            os.path.join(_docs_folder("Projects"), f"{state.project_name}.scout"),
            filter="Scout Project (*.scout)")
        if not path: return
        if state.save_to_file(path):
            self._current_path = path
            name = os.path.basename(path).rsplit(".", 1)[0]
            state.project_name = name
            self._project_lbl.setText(name)
            self._add_to_recents(path)
            state.toast_requested.emit(_('"{}" guardado').format(name))

    def _load_project(self):
        path, _filt = QFileDialog.getOpenFileName(self, _("Abrir proyecto"),
            _docs_folder("Projects"), filter="Scout Project (*.scout)")
        if not path: return
        self._load_project_path(path)

    def _load_project_path(self, path):
        """Cargar proyecto existente O crear uno nuevo si no existe."""
        if not path:
            return

        if os.path.exists(path):
            # ── Abrir existente ───────────────────────────────────────
            self._autosave_locked = True
            try: loaded = state.load_from_file(path)
            finally: self._autosave_locked = False
            if loaded:
                self._current_path = path
                name = os.path.basename(path).rsplit(".", 1)[0]
                state.project_name = name
                self._project_lbl.setText(name)
                self._add_to_recents(path)
                state.toast_requested.emit(_('"{}" cargado').format(name))
        else:
            # ── Crear nuevo ───────────────────────────────────────────
            self._create_new_project(path)

    def _create_new_project(self, path):
        """Crear proyecto nuevo: limpiar estado, crear archivo, activar autosave."""
        self._autosave_locked = True
        try:
            for attr in ("buttons", "video_sources", "clips", "presentation"):
                getattr(state, attr).clear()
            state.presentations = [[]]
            state.presentation_names = []
            state.active_pres_idx = 0
            state.active_source_idx = -1
        finally:
            self._autosave_locked = False

        name = os.path.basename(path).rsplit(".", 1)[0]
        state.project_name = name

        # Crear el archivo inmediatamente
        os.makedirs(os.path.dirname(path), exist_ok=True)
        state.save_to_file(path)

        # Setear current_path → autosave va a guardar acá
        self._current_path = path
        self._project_lbl.setText(name)
        self._add_to_recents(path)

        # Emitir señales para que las screens se actualicen
        for sig in (state.buttons_changed, state.clips_changed,
                    state.presentation_changed, state.presentations_changed,
                    state.sources_changed):
            sig.emit()
        state.active_source_changed.emit("", "")
        state.project_changed.emit(name)
        state.toast_requested.emit(_('Proyecto "{}" creado').format(name))

    # ── Botonera ──────────────────────────────────────────────────────────────
    def _new_buttons(self):
        if state.buttons:
            dlg = QMessageBox(self)
            dlg.setWindowTitle(_("Nueva botonera"))
            dlg.setText(_("Esto eliminará los {} botones actuales.").format(len(state.buttons)))
            ok = dlg.addButton(_("Continuar"), QMessageBox.ButtonRole.DestructiveRole)
            can = dlg.addButton(_("Cancelar"), QMessageBox.ButtonRole.RejectRole)
            dlg.exec()
            if dlg.clickedButton() == can: return
        state.buttons.clear()
        state.buttons_changed.emit()
        state.toast_requested.emit(_("Botonera vacía"))

    def _save_buttons(self):
        path, _filt = QFileDialog.getSaveFileName(self, _("Guardar botonera"),
            os.path.join(_docs_folder("Buttons"), "botonera.scoutbtn"),
            filter="Scout Botonera (*.scoutbtn)")
        if not path: return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"_type":"scoutbtn","_version":1,
                    "buttons":[{"label":b.label,"color":b.color,
                                "pad_before":getattr(b,'pad_before',-1),
                                "pad_after":getattr(b,'pad_after',-1),
                                "hotkey":getattr(b,'hotkey','')}
                               for b in state.buttons]}, f, indent=2)
            state.toast_requested.emit(_("Botonera guardada ({} botones)").format(len(state.buttons)))
        except Exception as e:
            state.toast_requested.emit(f"Error: {e}")

    def _load_buttons(self):
        path, _filt = QFileDialog.getOpenFileName(self, _("Abrir botonera"),
            _docs_folder("Buttons"),
            filter="Scout Botonera (*.scoutbtn);;JSON (*.json)")
        if not path: return
        self._autosave_locked = True
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            buttons = data.get("buttons", [])
            if not buttons:
                state.toast_requested.emit(_("Botonera vacía")); return
            if state.buttons:
                dlg = QMessageBox(self)
                dlg.setWindowTitle(_("Abrir botonera"))
                dlg.setText(_("Ya tenés {} botones. ¿Reemplazar o agregar?").format(len(state.buttons)))
                rep = dlg.addButton(_("Reemplazar"), QMessageBox.ButtonRole.DestructiveRole)
                dlg.addButton(_("Agregar"), QMessageBox.ButtonRole.AcceptRole)
                can = dlg.addButton(_("Cancelar"), QMessageBox.ButtonRole.RejectRole)
                dlg.exec()
                if dlg.clickedButton() == can: return
                if dlg.clickedButton() == rep:
                    state.buttons.clear(); state.buttons_changed.emit()
            for bd in buttons:
                lbl = bd.get("label","")
                col = bd.get("color","#1c1c1c")
                if lbl:
                    btn = state.add_button(lbl, col)
                    btn.pad_before = bd.get("pad_before", -1)
                    btn.pad_after = bd.get("pad_after", -1)
                    btn.hotkey = bd.get("hotkey", "")
            state.toast_requested.emit(_("{} botones cargados").format(len(buttons)))
        except Exception as e:
            state.toast_requested.emit(f"Error: {e}")
        finally:
            self._autosave_locked = False

    # ── Actualizaciones / Codecs ──────────────────────────────────────────────

    def _on_update_available(self, version, download_url, changelog):
        self._pending_update = {"version": version, "download_url": download_url, "changelog": changelog}
        self._toast.show_message(f"PyScout {version} disponible — Configuraciones → Buscar actualizaciones")

    def _check_updates(self):
        from PySide6.QtWidgets import QMessageBox
        try:
            import requests
            from utils.updater import CURRENT_VERSION, UPDATE_URL, UpdateChecker
            self._toast.show_message(_("Buscando actualizaciones..."))
            try:
                r = requests.get(UPDATE_URL, timeout=5)
            except Exception:
                self._toast.show_message(_("Sin conexión a internet"))
                return
            if r.status_code == 404:
                self._toast.show_message(_("Estás al día (v{})").format(CURRENT_VERSION))
                return
            if r.status_code != 200:
                self._toast.show_message(_("Servidor no disponible (HTTP {})").format(r.status_code))
                return
            data = r.json()
            latest = data.get("version", CURRENT_VERSION)
            download_url = data.get("download_url", "")
            changelog = data.get("changelog", "")
            if not UpdateChecker._is_newer(latest, CURRENT_VERSION):
                self._toast.show_message(_("Estás al día (v{})").format(CURRENT_VERSION))
                return
            # Nueva versión disponible
            if not download_url:
                QMessageBox.information(self, _("Actualización disponible"),
                    f"Nueva versión: {latest}\nTu versión: {CURRENT_VERSION}\n\n"
                    f"{changelog or 'Visitá la página para descargar.'}")
                return
            msg = QMessageBox(self)
            msg.setWindowTitle(_("Actualización disponible"))
            msg.setText(f"<b>PyScout {latest}</b> está disponible.<br>Versión actual: {CURRENT_VERSION}")
            if changelog:
                msg.setInformativeText(changelog)
            msg.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
            msg.button(QMessageBox.StandardButton.Ok).setText(_("Descargar y actualizar"))
            msg.button(QMessageBox.StandardButton.Cancel).setText(_("Más tarde"))
            if msg.exec() == QMessageBox.StandardButton.Ok:
                self._download_and_apply_update(latest, download_url)
        except ImportError:
            self._toast.show_message(_("Módulo de actualizaciones no disponible"))
        except Exception as e:
            self._toast.show_message(f"Error: {e}")

    def _download_and_apply_update(self, version: str, download_url: str):
        from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                                        QLabel, QPushButton, QProgressBar, QMessageBox)
        from PySide6.QtCore import Qt
        from utils.updater import UpdateDownloader, apply_update

        dlg = QDialog(self)
        dlg.setWindowTitle(_("Descargando PyScout {}").format(version))
        dlg.setFixedWidth(420)
        dlg.setModal(True)
        dlg.setStyleSheet(f"background:{BG1}; color:{TEXT0};")

        vl = QVBoxLayout(dlg)
        vl.setContentsMargins(28, 24, 28, 20)
        vl.setSpacing(12)

        lbl_title = QLabel(_("Descargando PyScout {}...").format(version))
        lbl_title.setStyleSheet(f"color:{TEXT0}; font-size:{fs(14)}px; font-weight:600;")
        vl.addWidget(lbl_title)

        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(0)
        bar.setTextVisible(False)
        bar.setFixedHeight(8)
        bar.setStyleSheet(
            f"QProgressBar {{ background:{BG3}; border-radius:4px; border:none; }}"
            f"QProgressBar::chunk {{ background:{ACCENT}; border-radius:4px; }}")
        vl.addWidget(bar)

        lbl_info = QLabel(_("Conectando..."))
        lbl_info.setStyleSheet(f"color:{TEXT2}; font-size:{fs(11)}px;")
        vl.addWidget(lbl_info)

        hl = QHBoxLayout()
        hl.addStretch()
        btn_cancel = QPushButton(_("Cancelar"))
        btn_cancel.setStyleSheet(
            f"QPushButton {{ background:{BG2}; color:{TEXT1}; border:none;"
            f" border-radius:6px; padding:8px 20px; font-size:{fs(12)}px; }}"
            f"QPushButton:hover {{ background:{BG3}; }}")
        hl.addWidget(btn_cancel)
        vl.addLayout(hl)

        downloader = UpdateDownloader(download_url)

        def on_progress(done, total):
            if total > 0:
                bar.setValue(int(done * 100 / total))
                lbl_info.setText(f"{done/1_048_576:.1f} MB / {total/1_048_576:.1f} MB")
            else:
                lbl_info.setText(f"{done/1_048_576:.1f} MB descargados...")

        def on_finished(zip_path):
            dlg.accept()
            reply = QMessageBox.question(self, _("Actualización lista"),
                _("PyScout {} listo para instalar.\n\nLa app se cerrará y se reiniciará automáticamente.\n¿Continuar?").format(version),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                apply_update(zip_path)

        def on_failed(err):
            dlg.reject()
            self._toast.show_message(_("Error al descargar: {}").format(err))

        downloader.progress.connect(on_progress)
        downloader.finished.connect(on_finished)
        downloader.failed.connect(on_failed)
        btn_cancel.clicked.connect(lambda: (downloader.cancel(), dlg.reject()))

        downloader.start()
        dlg.exec()

    def _install_codecs(self):
        import subprocess
        from PySide6.QtWidgets import QDialog, QVBoxLayout as QVL, QHBoxLayout as QHL, QLabel, QPushButton, QFrame
        from utils.ffmpeg import get_ffmpeg

        # ── Verificar FFmpeg ──────────────────────────────────────────────────
        ffmpeg_ver = None
        ffmpeg_path = None
        try:
            fp = get_ffmpeg()
            r = subprocess.run([fp, "-version"], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                ffmpeg_ver = r.stdout.split('\n')[0].replace("ffmpeg version ", "").split(" ")[0]
                ffmpeg_path = fp
        except Exception:
            pass

        # ── Verificar libmpv ──────────────────────────────────────────────────
        mpv_ok = False
        try:
            import mpv as _mpv  # noqa: F401
            mpv_ok = True
        except Exception:
            pass

        # ── Dialog de estado ──────────────────────────────────────────────────
        dlg = QDialog(self)
        dlg.setWindowTitle(_("Estado de componentes"))
        dlg.setFixedWidth(440)
        dlg.setStyleSheet(f"background:{BG1}; color:{TEXT0};")
        vl = QVL(dlg)
        vl.setContentsMargins(28, 24, 28, 20)
        vl.setSpacing(0)

        title = QLabel(_("Componentes de video"))
        title.setStyleSheet(f"color:{ACCENT}; font-size:{fs(14)}px; font-weight:700;")
        vl.addWidget(title)
        vl.addSpacing(16)

        sep = QFrame(); sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{BORDER2};")
        vl.addWidget(sep)
        vl.addSpacing(14)

        def _row(label: str, ok: bool, detail: str = ""):
            row = QHL()
            dot = QLabel("●")
            dot.setFixedWidth(16)
            dot.setStyleSheet(f"color:{'#27AE60' if ok else '#C0392B'}; font-size:{fs(10)}px;")
            name = QLabel(label)
            name.setStyleSheet(f"color:{TEXT0}; font-size:{fs(12)}px; font-weight:600;")
            row.addWidget(dot)
            row.addWidget(name)
            row.addStretch()
            if detail:
                det = QLabel(detail)
                det.setStyleSheet(f"color:{TEXT2}; font-size:{fs(10)}px;")
                row.addWidget(det)
            vl.addLayout(row)
            if not ok:
                warn = QLabel(_("  No encontrado — reinstalá PyScout"))
                warn.setStyleSheet(f"color:#C0392B; font-size:{fs(10)}px;")
                vl.addWidget(warn)
            vl.addSpacing(10)

        _row("FFmpeg  (exportar video)", ffmpeg_ver is not None,
             f"v{ffmpeg_ver}" if ffmpeg_ver else "")
        _row("libmpv  (reproducción)", mpv_ok,
             _("cargado") if mpv_ok else "")

        vl.addSpacing(4)
        sep2 = QFrame(); sep2.setFixedHeight(1)
        sep2.setStyleSheet(f"background:{BORDER2};")
        vl.addWidget(sep2)
        vl.addSpacing(14)

        all_ok = ffmpeg_ver is not None and mpv_ok
        summary = QLabel(_("Todos los componentes están instalados correctamente.") if all_ok
                         else _("Algunos componentes faltan. Reinstalá PyScout para reparar."))
        summary.setWordWrap(True)
        summary.setStyleSheet(
            f"color:{'#27AE60' if all_ok else '#C0392B'}; font-size:{fs(11)}px;")
        vl.addWidget(summary)
        vl.addSpacing(20)

        btn = QPushButton(_("Cerrar"))
        btn.setFixedHeight(34)
        btn.setStyleSheet(
            f"QPushButton{{background:{BG3};color:{TEXT0};border:none;"
            f"border-radius:4px;font-size:{fs(12)}px;padding:0 20px;}}"
            f"QPushButton:hover{{background:{ACCENT};color:#000;}}"
        )
        btn.clicked.connect(dlg.accept)
        hl = QHL(); hl.addStretch(); hl.addWidget(btn)
        vl.addLayout(hl)

        dlg.exec()

    # ── Ayuda ─────────────────────────────────────────────────────────────────
    def _show_about(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(_("Acerca de PyScout"))
        dlg.setFixedWidth(460)
        dlg.setStyleSheet(f"background:{BG1}; color:{TEXT0};")
        vl = QVL(dlg)
        vl.setContentsMargins(32, 32, 32, 28)
        vl.setSpacing(0)

        name_lbl = QLabel("PyScout")
        name_lbl.setStyleSheet(
            f"color:{ACCENT}; font-size:{fs(24)}px; font-weight:700; letter-spacing:-0.5px;")
        vl.addWidget(name_lbl)

        tagline = QLabel(_("Análisis de video deportivo"))
        tagline.setStyleSheet(f"color:{TEXT2}; font-size:{fs(12)}px;")
        vl.addWidget(tagline)
        vl.addSpacing(4)

        version_lbl = QLabel(_("Versión {}").format(QApplication.instance().applicationVersion()))
        version_lbl.setStyleSheet(f"color:{TEXT3}; font-size:{fs(10)}px;")
        vl.addWidget(version_lbl)
        vl.addSpacing(20)

        sep = QFrame(); sep.setFixedHeight(1); sep.setStyleSheet(f"background:{BORDER2};")
        vl.addWidget(sep)
        vl.addSpacing(18)

        desc = QLabel(_(
            "PyScout es una herramienta para entrenadores y analistas deportivos. "
            "Marcá jugadas en tiempo real mientras mirás el partido, recortá cada clip "
            "con precisión, armá listados tácticos y producí video editado listo para presentar al equipo."
        ))
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color:{TEXT1}; font-size:{fs(12)}px;")
        vl.addWidget(desc)
        vl.addSpacing(18)

        offline_lbl = QLabel(_("Sin conexión a internet  ·  Sin límite de proyectos  ·  Sin nube"))
        offline_lbl.setStyleSheet(f"color:{TEXT3}; font-size:{fs(10)}px;")
        vl.addWidget(offline_lbl)
        vl.addSpacing(8)

        formats_lbl = QLabel(_("Formatos de video:  MP4  ·  MOV  ·  MKV  ·  AVI  ·  WebM  ·  MTS"))
        formats_lbl.setStyleSheet(f"color:{TEXT2}; font-size:{fs(11)}px;")
        vl.addWidget(formats_lbl)
        vl.addSpacing(24)

        sep2 = QFrame(); sep2.setFixedHeight(1); sep2.setStyleSheet(f"background:{BORDER2};")
        vl.addWidget(sep2)
        vl.addSpacing(14)

        footer_lbl = QLabel(_("© 2026 PyScout. Todos los derechos reservados."))
        footer_lbl.setStyleSheet(f"color:{TEXT3}; font-size:{fs(10)}px;")
        vl.addWidget(footer_lbl)
        vl.addSpacing(18)

        close_btn = QPushButton(_("Cerrar"))
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {ACCENT3}, stop:1 {ACCENT});
                color: #1a1714; border: none;
                border-bottom: 2px solid {ACCENT2};
                border-radius: 2px;
                font-size: {fs(12)}px; font-weight: 600;
                padding: 6px 24px;
            }}
            QPushButton:hover {{ background: {ACCENT3}; }}
            QPushButton:pressed {{ border-bottom: none; padding-top: 8px; }}
        """)
        close_btn.clicked.connect(dlg.accept)
        vl.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)
        dlg.exec()

    _MAX_RECENT = 8

    def _rebuild_recent_menu(self):
        self._recent_menu.clear()
        settings = QSettings("ScoutApp", "prefs")
        recents = settings.value("recent_projects", [])
        if not recents:
            a = self._recent_menu.addAction(_("(vacío)"))
            a.setEnabled(False); return
        for path in recents:
            name = os.path.basename(path).rsplit(".", 1)[0]
            a = QAction(name, self)
            a.setToolTip(path)
            a.triggered.connect(lambda checked, p=path: self._open_recent(p))
            self._recent_menu.addAction(a)
        self._recent_menu.addSeparator()
        self._recent_menu.addAction(self._act("Limpiar recientes", self._clear_recents))

    def _add_to_recents(self, path):
        settings = QSettings("ScoutApp", "prefs")
        recents = settings.value("recent_projects", [])
        if not isinstance(recents, list): recents = []
        if path in recents: recents.remove(path)
        recents.insert(0, path)
        recents = recents[:self._MAX_RECENT]
        settings.setValue("recent_projects", recents)
        self._rebuild_recent_menu()

    def _open_recent(self, path):
        if not os.path.exists(path):
            state.toast_requested.emit(_("Archivo no encontrado"))
            settings = QSettings("ScoutApp", "prefs")
            recents = settings.value("recent_projects", [])
            if path in recents:
                recents.remove(path)
                settings.setValue("recent_projects", recents)
                self._rebuild_recent_menu()
            return
        self._autosave_locked = True
        try: loaded = state.load_from_file(path)
        finally: self._autosave_locked = False
        if loaded:
            self._current_path = path
            name = os.path.basename(path).rsplit(".", 1)[0]
            state.project_name = name
            self._project_lbl.setText(name)
            self._add_to_recents(path)
            state.toast_requested.emit(_('"{}" cargado').format(name))

    def _clear_recents(self):
        QSettings("ScoutApp", "prefs").setValue("recent_projects", [])
        self._rebuild_recent_menu()

    def _show_help(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(_("¿Cómo funciona PyScout?"))
        dlg.setMinimumSize(720, 540)
        dlg.setStyleSheet(f"background:{BG1}; color:{TEXT0};")
        root = QHL(dlg)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar de navegación
        nav = QWidget()
        nav.setFixedWidth(186)
        nav.setStyleSheet(f"background:{BG0}; border-right:1px solid rgba(255,255,255,0.05);")
        nl = QVL(nav)
        nl.setContentsMargins(0, 20, 0, 16)
        nl.setSpacing(0)
        nav_title = QLabel(_("CONTENIDO"))
        nav_title.setStyleSheet(
            f"color:{ACCENT}; font-size:{fs(9)}px; font-weight:700;"
            f" letter-spacing:2px; padding:0 16px 10px 16px;")
        nl.addWidget(nav_title)

        sections = [
            (_("Flujo de trabajo"),  "flujo"),
            (_("1. Observación"),    "obs"),
            (_("2. Ajuste"),         "adj"),
            (_("3. Presentación"),   "pres"),
            (_("Atajos de teclado"), "keys"),
            (_("Preguntas frecuentes"), "faq"),
        ]

        content_area = QScrollArea()
        content_area.setWidgetResizable(True)
        content_area.setFrameShape(QFrame.Shape.NoFrame)
        content_area.setStyleSheet("background:transparent;")
        self._help_anchors = {}

        nav_btn_style = (
            f"QPushButton {{ background:transparent; color:{TEXT2}; border:none;"
            f" border-left:2px solid transparent; text-align:left;"
            f" padding:9px 14px; font-size:{fs(12)}px; }}"
            f"QPushButton:hover {{ color:{TEXT0}; border-left:2px solid {ACCENT};"
            f" background:rgba(255,255,255,0.03); }}")
        for label, key in sections:
            b = QPushButton(label)
            b.setStyleSheet(nav_btn_style)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda checked, k=key: self._scroll_to_help(k, content_area))
            nl.addWidget(b)
        nl.addStretch()
        root.addWidget(nav)

        # Área de contenido
        content = QWidget()
        cl = QVL(content)
        cl.setContentsMargins(32, 28, 32, 28)
        cl.setSpacing(14)

        def heading(text, key):
            h = QLabel(text)
            h.setStyleSheet(
                f"color:{ACCENT}; font-size:{fs(15)}px; font-weight:700;"
                f" letter-spacing:0.3px; padding-top:6px;")
            self._help_anchors[key] = h
            return h

        def subheading(text):
            h = QLabel(text)
            h.setStyleSheet(
                f"color:{TEXT0}; font-size:{fs(12)}px; font-weight:700; padding-top:4px;")
            return h

        def para(text):
            p = QLabel(text)
            p.setWordWrap(True)
            p.setStyleSheet(f"color:{TEXT1}; font-size:{fs(12)}px;")
            p.setTextFormat(Qt.TextFormat.RichText)
            return p

        def sep():
            s = QFrame()
            s.setFixedHeight(1)
            s.setStyleSheet(f"background:{BORDER2};")
            return s

        # ── Flujo de trabajo ──────────────────────────────────────────────────
        cl.addWidget(heading(_("Flujo de trabajo"), "flujo"))
        cl.addWidget(para(_(
            "PyScout te guía por tres pantallas que se encadenan naturalmente:<br><br>"
            "<b>① Observación</b> — Mirás el partido y marcás momentos clave con un clic.<br>"
            "<b>② Ajuste</b> — Revisás cada registro y afinás el inicio y fin del clip.<br>"
            "<b>③ Presentación</b> — Ordenás los clips, armás listados y producís el video final."
        )))

        # ── Observación ───────────────────────────────────────────────────────
        cl.addWidget(sep())
        cl.addWidget(heading(_("1. Observación"), "obs"))
        cl.addWidget(para(_(
            "Cargá uno o varios videos fuente con el botón <b>+</b> de la barra de pestañas "
            "(hasta 10 simultáneos). En el sidebar izquierdo creá los botones de categoría "
            "que necesitás: PNR, Transición, Tiro libre, etc."
        )))
        cl.addWidget(para(_(
            "Mientras el video corre, presioná el botón en el momento exacto. "
            "PyScout registra el clip con un margen automático antes y después del instante marcado. "
            "Podés ajustar ese margen por categoría con el ícono <b>⚙</b>, y asignar una tecla de atajo "
            "para registrar sin usar el mouse."
        )))
        cl.addWidget(para(_(
            "La lista de <b>Registros</b> en la parte inferior muestra todo lo marcado en el video activo. "
            "Clic en un registro para ir al instante; doble clic para editar nombre, nota y color."
        )))

        # ── Ajuste ────────────────────────────────────────────────────────────
        cl.addWidget(sep())
        cl.addWidget(heading(_("2. Ajuste"), "adj"))
        cl.addWidget(para(
            "El sidebar muestra todos tus registros con filtro por categoría. "
            "Seleccioná uno para cargarlo en el reproductor."
        ))
        cl.addWidget(para(
            "El <b>timeline</b> muestra el clip en contexto. Arrastrá el handle izquierdo o derecho "
            "para mover el inicio o fin del clip. Arrastrá el cuerpo para desplazarlo completo. "
            "El playhead (línea blanca) es tu referencia de posición — los handles se pegan a él "
            "automáticamente cuando se acercan. Usá <b>🔍+ / 🔍−</b> para hacer zoom en el timeline."
        ))
        cl.addWidget(para(_(
            "Cuando el clip está listo, presioná <b>+ Agregar a presentación</b> "
            "para sumarlo al listado activo."
        )))

        # ── Presentación ──────────────────────────────────────────────────────
        cl.addWidget(sep())
        cl.addWidget(heading(_("3. Presentación"), "pres"))
        cl.addWidget(para(_(
            "Cada proyecto puede tener hasta <b>5 listados independientes</b> — útil para separar "
            "ofensiva, defensiva, o distintos jugadores. Cambiá entre ellos con las pestañas del "
            "panel superior; renombrá cualquiera con doble clic."
        )))
        cl.addWidget(para(_(
            "Arrastrá las filas para reordenar los clips. Podés intercalar imágenes estáticas, "
            "configurar la transición de cada clip (corte directo o fade), y activar el overlay "
            "de nombre sobre el video."
        )))
        cl.addWidget(para(_(
            "Presioná <b>Producir presentación</b> para exportar un MP4 con todos los clips "
            "concatenados. Podés elegir resolución, calidad y si incluir audio. "
            "También podés exportar cada clip por separado."
        )))

        # ── Atajos ────────────────────────────────────────────────────────────
        cl.addWidget(sep())
        cl.addWidget(heading(_("Atajos de teclado"), "keys"))
        shortcuts = [
            (_("Reproducción"),
             _("Space  play / pausa\n"
             "← / →  retroceder / avanzar 5 s\n"
             "↑ / ↓  avanzar / retroceder 10 s\n"
             "Shift + ← / →  ±1 minuto")),
            (_("Ventana"),
             _("F  pantalla completa (video en Observación)\n"
             "F11  pantalla completa de la aplicación\n"
             "M  silenciar")),
            (_("Proyecto"),
             _("Ctrl+Z  deshacer\n"
             "Ctrl+Shift+Z  rehacer\n"
             "Ctrl+S  guardar\n"
             "Ctrl+O  abrir proyecto\n"
             "Ctrl+N  nuevo proyecto")),
        ]
        for group_title, keys_text in shortcuts:
            cl.addWidget(subheading(group_title))
            cl.addWidget(para(keys_text))

        # ── FAQ ───────────────────────────────────────────────────────────────
        cl.addWidget(sep())
        cl.addWidget(heading(_("Preguntas frecuentes"), "faq"))
        faq_items = [
            (_("¿Qué formatos de video acepta?"),
             _("MP4, MOV, MKV, AVI, WebM y MTS. La mayoría de cámaras de acción, "
             "drones y captura de pantalla generan alguno de estos formatos.")),
            (_("¿Necesito conexión a internet?"),
             _("No. PyScout funciona completamente offline. La única conexión que puede "
             "necesitar es al activar o renovar la licencia.")),
            (_("¿Dónde se guardan los proyectos?"),
             _("En Documentos / PyScout / Projects. Cada proyecto es un único archivo .scout "
             "que contiene todos tus botones, registros y listados.")),
            (_("¿Puedo trabajar con varios videos del mismo partido?"),
             _("Sí. Podés cargar hasta 10 videos fuente simultáneos y cambiar entre ellos "
             "con las pestañas. Los clips de cada video quedan asociados a su fuente.")),
            (_("¿Puedo deshacer cambios accidentales?"),
             _("Sí. Ctrl+Z deshace y Ctrl+Shift+Z rehace. El historial cubre "
             "registros, ajustes de clips y cambios en los listados de presentación.")),
            (_("¿Qué pasa si cierro la app sin guardar?"),
             _("PyScout tiene autoguardado activo por defecto. Cualquier cambio se escribe "
             "al archivo del proyecto automáticamente, sin necesidad de guardar manualmente.")),
        ]
        for q, a in faq_items:
            cl.addWidget(para(f"<b>{q}</b><br>{a}"))

        cl.addStretch()
        content_area.setWidget(content)
        root.addWidget(content_area, stretch=1)
        dlg.exec()

    def _scroll_to_help(self, key, scroll_area):
        if key in self._help_anchors:
            scroll_area.ensureWidgetVisible(self._help_anchors[key], 0, 50)

    def _toggle_autosave(self, checked):
        self._autosave_enabled = checked
        state.toast_requested.emit(_("Autoguardado activado") if checked else _("Autoguardado desactivado"))

    def _autosave(self):
        if not getattr(self, "_autosave_enabled", False): return
        if getattr(state, "is_loading", False): return
        if getattr(self, "_autosave_locked", False): return
        import os, tempfile
        if hasattr(self, "_current_path") and self._current_path:
            try:
                state.save_to_file(self._current_path)
                self._project_lbl.setToolTip(_("Guardado automáticamente"))
            except Exception: pass
            return
        if not self._autosave_path:
            fd, path = tempfile.mkstemp(suffix=".scout", prefix="pyscout_autosave_")
            os.close(fd); self._autosave_path = path
        try: state.save_to_file(self._autosave_path)
        except Exception: pass

    def _rebuild_screens(self):
        current_idx = self._stack.currentIndex()

        # Guardar fuentes activas para restaurar después
        active_path = state.active_video_path
        active_name = state.active_video_name

        # Parar timers y desconectar players ANTES de destruir widgets
        from components.video_player import MpvWidget
        for screen_idx in range(self._stack.count()):
            screen = self._stack.widget(screen_idx)
            for mpv_w in screen.findChildren(MpvWidget):
                try:
                    if hasattr(mpv_w, '_ui_timer') and mpv_w._ui_timer:
                        mpv_w._ui_timer.stop()
                except Exception:
                    pass
                try:
                    if getattr(mpv_w, '_player', None):
                        mpv_w._player.pause = True
                        mpv_w._player.command("stop")
                except Exception:
                    pass

        # Procesar eventos pendientes para que los callbacks de mpv drenen
        QApplication.processEvents()
        QApplication.processEvents()

        # Terminar los players ya silenciados
        for screen_idx in range(self._stack.count()):
            screen = self._stack.widget(screen_idx)
            for mpv_w in screen.findChildren(MpvWidget):
                try:
                    if getattr(mpv_w, '_player', None):
                        mpv_w._player.terminate()
                        mpv_w._player = None
                except Exception:
                    pass

        QApplication.processEvents()

        while self._stack.count():
            w = self._stack.widget(0)
            self._stack.removeWidget(w)
            w.setParent(None)
            w.deleteLater()

        QApplication.processEvents()

        self._obs_screen = ObservationScreen()
        self._adj_screen = AdjustScreen()
        self._pres_screen = PresentationScreen()
        self._pres_screen.navigate_to_adjust.connect(self._goto_adjust)
        self._stack.addWidget(self._obs_screen)
        self._stack.addWidget(self._adj_screen)
        self._stack.addWidget(self._pres_screen)
        self._stack.setCurrentIndex(current_idx)

        state.buttons_changed.emit()
        state.clips_changed.emit()
        state.presentation_changed.emit()
        state.sources_changed.emit()

        # Restaurar el video activo si había uno cargado
        if active_path:
            state.active_source_changed.emit(active_path, active_name)

    # ── Onboarding tour ───────────────────────────────────────────────────────
    def _setup_tour(self) -> None:
        from components.onboarding import OnboardingTour, TourStep
        steps = [
            # 1. Bienvenida
            TourStep(
                title=_("Bienvenido a PyScout"),
                body=_(
                    "Este tour rápido te muestra las 3 pantallas y las funciones clave. "
                    "Avanzá con Siguiente o saltealo con ✕."
                ),
                widget_getter=lambda: None,
            ),
            # 2. Agregar video fuente
            TourStep(
                title=_("Agregar video fuente"),
                body=_(
                    "Hacé clic aquí para cargar el video del partido. "
                    "Podés tener hasta 10 videos abiertos al mismo tiempo, cada uno en su pestaña."
                ),
                widget_getter=lambda: self._obs_screen._add_src_btn,
                on_enter=lambda: self._switch_screen(0),
            ),
            # 3. Botones de categoría
            TourStep(
                title=_("Crear botones de categoría"),
                body=_(
                    "Con el '+' creás un botón por tipo de jugada: PNR, Transición, Tiro libre... "
                    "Asignales color y tecla de atajo para registrar sin mouse."
                ),
                widget_getter=lambda: self._obs_screen._add_btn,
            ),
            # 4. Pestaña Ajuste
            TourStep(
                title=_("Pantalla Ajuste"),
                body=_(
                    "Cuando tengas registros, pasá a Ajuste para afinar el inicio y fin "
                    "de cada clip con el timeline interactivo."
                ),
                widget_getter=lambda: self._tabs[1],
            ),
            # 5. Pantalla Ajuste vacía
            TourStep(
                title=_("Aquí aparecerán tus registros"),
                body=_(
                    "Cada clip marcado en Observación se lista aquí. "
                    "Seleccioná uno y ajustá sus bordes en el timeline."
                ),
                widget_getter=lambda: None,
                on_enter=lambda: self._switch_screen(1),
            ),
            # 6. Pestaña Presentación
            TourStep(
                title=_("Pantalla Presentación"),
                body=_(
                    "Desde Ajuste, enviás clips a Presentación para construir el video final."
                ),
                widget_getter=lambda: self._tabs[2],
            ),
            # 7. Pantalla Presentación vacía
            TourStep(
                title=_("Aquí aparecerán tus clips"),
                body=_(
                    "Los clips de tu presentación se listan aquí. "
                    "Arrastrá las filas para reordenarlos."
                ),
                widget_getter=lambda: None,
                on_enter=lambda: self._switch_screen(2),
            ),
            # 8. Agregar imagen
            TourStep(
                title=_("Intercalar imágenes"),
                body=_(
                    "Agregá imágenes estáticas —pizarrones, diagramas— entre los clips "
                    "para enriquecer tu presentación táctica."
                ),
                widget_getter=lambda: self._pres_screen._add_img_btn,
            ),
            # 9. Crear película
            TourStep(
                title=_("Crear película"),
                body=_(
                    "Producí un MP4 con todos los clips concatenados, listo para el equipo. "
                    "Elegís resolución, calidad, transiciones y si incluir audio."
                ),
                widget_getter=lambda: self._pres_screen._render_btn,
            ),
            # 10. Autoguardado y deshacer
            TourStep(
                title=_("Autoguardado y deshacer"),
                body=_(
                    "Cada cambio se guarda automáticamente. "
                    "Ctrl+Z deshace cualquier acción. "
                    "Usá F11 para pantalla completa durante las presentaciones."
                ),
                widget_getter=lambda: self._undo_btn,
            ),
        ]
        self._tour = OnboardingTour(self, steps)
        self._tour.start_if_needed()

    def _restart_tour(self) -> None:
        if hasattr(self, "_tour"):
            self._tour.force_start()

    # ── Feedback ──────────────────────────────────────────────────────────────
    def _show_feedback(self) -> None:
        from components.feedback import show_general_feedback
        show_general_feedback(self)

    # ── ¿Qué hay de nuevo? ────────────────────────────────────────────────────
    _CHANGELOGS: dict[str, list[str]] = {
        "1.0.3": [
            "Corrección en el ajuste de clips desde el detalle de presentación",
            "Tour de bienvenida interactivo de 10 pasos",
            "Feedback integrado — calificá la app después de producir una película",
            "Logging automático en Documentos/PyScout/pyscout.log",
            "Dialog de error cuando ocurre un crash inesperado",
        ],
    }

    def _check_whats_new(self) -> None:
        settings = QSettings("ScoutApp", "prefs")
        last    = settings.value("last_shown_version", "")
        current = QApplication.instance().applicationVersion()
        settings.setValue("last_shown_version", current)

        if not last or last == current:
            return  # Primera vez o misma versión — no mostrar
        changes = self._CHANGELOGS.get(current)
        if not changes:
            return
        QTimer.singleShot(2500, lambda: self._show_whats_new(current, changes))

    def _show_whats_new(self, version: str, changes: list[str]) -> None:
        from PySide6.QtWidgets import QDialog
        dlg = QDialog(self)
        dlg.setWindowTitle(_("Novedades"))
        dlg.setFixedWidth(420)
        dlg.setStyleSheet(f"background:{BG1}; color:{TEXT0};")

        vl = QVL(dlg)
        vl.setContentsMargins(28, 24, 28, 20)
        vl.setSpacing(0)

        badge = QLabel(f"v{version}")
        badge.setStyleSheet(
            f"color:{BG1}; background:{ACCENT}; font-size:{fs(9)}px;"
            f" font-weight:700; padding:2px 8px; border-radius:2px;"
        )
        badge.setFixedWidth(badge.sizeHint().width() + 8)
        vl.addWidget(badge, alignment=Qt.AlignmentFlag.AlignLeft)
        vl.addSpacing(10)

        title = QLabel(_("¡PyScout actualizado!"))
        title.setStyleSheet(
            f"color:{TEXT0}; font-size:{fs(16)}px; font-weight:700;"
        )
        vl.addWidget(title)
        vl.addSpacing(4)

        sub = QLabel(_("Esto es lo que hay de nuevo en esta versión:"))
        sub.setStyleSheet(f"color:{TEXT2}; font-size:{fs(11)}px;")
        vl.addWidget(sub)
        vl.addSpacing(16)

        for change in changes:
            row = QHL()
            dot = QLabel("•")
            dot.setFixedWidth(14)
            dot.setStyleSheet(
                f"color:{ACCENT}; font-size:{fs(13)}px; background:transparent; border:none;"
            )
            dot.setAlignment(Qt.AlignmentFlag.AlignTop)
            txt = QLabel(_(change))
            txt.setWordWrap(True)
            txt.setStyleSheet(
                f"color:{TEXT1}; font-size:{fs(12)}px; background:transparent; border:none;"
            )
            row.addWidget(dot)
            row.addSpacing(4)
            row.addWidget(txt, stretch=1)
            vl.addLayout(row)
            vl.addSpacing(5)

        vl.addSpacing(16)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:rgba(255,252,248,0.05);")
        vl.addWidget(sep)
        vl.addSpacing(14)

        hl = QHL()
        hl.addStretch()
        ok_btn = QPushButton(_("Entendido"))
        ok_btn.setFixedHeight(34)
        ok_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {ACCENT3}, stop:1 {ACCENT});
                color: #1a1714; border: none;
                border-bottom: 2px solid {ACCENT2};
                border-radius: 2px;
                font-size: {fs(12)}px; font-weight: 700; padding: 0 24px;
            }}
            QPushButton:hover {{ background: {ACCENT3}; }}
            QPushButton:pressed {{ border-bottom: none; margin-top: 2px; }}
        """)
        ok_btn.clicked.connect(dlg.accept)
        hl.addWidget(ok_btn)
        vl.addLayout(hl)

        dlg.exec()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, "_toast"):
            cw = self.centralWidget()
            if cw:
                self._toast.move(cw.width() - self._toast.width() - 24,
                                 cw.height() - self._toast.height() - 24)