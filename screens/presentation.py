from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QProgressBar, QComboBox, QSizePolicy,
    QFileDialog, QDialog, QApplication, QSpinBox, QCheckBox,
    QRadioButton, QButtonGroup, QGraphicsOpacityEffect, QLineEdit,
    QMenu
)
from PySide6.QtCore import Qt, QThread, Signal, QMimeData, QPoint, QSize
from PySide6.QtGui import QPixmap, QDrag, QColor, QImage, QPainter, QPen
import os
import subprocess
import platform

from store.state import state, PresentationItem
from styles.theme import fs
from utils.theme_helpers import (
    BG0, BG1, BG2, BG3, BG4, ACCENT, ACCENT2, ACCENT3,
    DANGER, TEXT0, TEXT1, TEXT2, TEXT3, BORDER, BORDER2,
    CLIP_COLORS, FONT
)
from utils.time_utils import fmt_time, fmt_dur
from utils.ffmpeg import render_presentation
from components.video_player import MpvWidget
from icons_helper import (
    play_icon, pause_icon, fullscreen_icon, fullscreen_exit_icon,
    previous_icon, next_icon, mute_icon, volume_icon, eye_icon, eye_off_icon
)


# ── Render thread ─────────────────────────────────────────────────────────────

class RenderThread(QThread):
    progress = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, items, output_path, show_overlay,
                 mute_audio=False, crf=23, fps=30, transition="cut", total_dur=0.0):
        super().__init__()
        self.items        = items
        self.output_path  = output_path
        self.show_overlay = show_overlay
        self.mute_audio   = mute_audio
        self.crf          = crf
        self.fps          = fps
        self.transition   = transition
        self.total_dur    = total_dur
        self._cancelled   = False

    def cancel(self):
        """Señalar cancelación — el render se detiene al siguiente progress check."""
        self._cancelled = True

    def run(self):
        try:
            def progress_with_cancel(t):
                if self._cancelled:
                    raise InterruptedError("Render cancelado por el usuario")
                self.progress.emit(t)

            render_presentation(self.items, self.output_path,
                show_overlay=self.show_overlay,
                mute_audio=self.mute_audio,
                crf=self.crf,
                fps=self.fps,
                transition=self.transition,
                progress_cb=progress_with_cancel)

            if self._cancelled:
                self.finished.emit(False, "Cancelado")
            else:
                self.finished.emit(True, self.output_path)
        except InterruptedError:
            self.finished.emit(False, "Cancelado")
        except Exception as e:
            self.finished.emit(False, str(e)[:400])


# ── Modal progreso ────────────────────────────────────────────────────────────

class RenderProgressDialog(QDialog):
    cancel_requested = Signal()

    def __init__(self, total_dur: float, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Produciendo presentación...")
        self.setFixedWidth(420)
        self.setModal(True)
        self.setStyleSheet(f"background:{BG1};")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)
        self._total_dur  = max(total_dur, 1.0)
        self._start_time = None
        self._output_path = ""  # Guardar path del video generado

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        title = QLabel("Procesando video...")
        title.setStyleSheet(f"color:{TEXT0}; font-size:{fs(14)}px; font-weight:600;")
        layout.addWidget(title)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setFixedHeight(4)
        layout.addWidget(self._progress_bar)

        info_row = QHBoxLayout()
        self._pct_lbl = QLabel("0%")
        self._pct_lbl.setStyleSheet(f"color:{ACCENT}; font-size:{fs(22)}px; font-weight:700;")
        info_row.addWidget(self._pct_lbl)
        info_row.addStretch()
        self._time_lbl = QLabel("")
        self._time_lbl.setStyleSheet(f"color:{TEXT2}; font-size:{fs(11)}px;")
        info_row.addWidget(self._time_lbl)
        layout.addLayout(info_row)

        self._eta_lbl = QLabel("Calculando tiempo restante...")
        self._eta_lbl.setStyleSheet(f"color:{TEXT3}; font-size:{fs(11)}px;")
        layout.addWidget(self._eta_lbl)

        sep = QFrame(); sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:rgba(255,255,255,0.06);")
        layout.addWidget(sep)

        self._cancel_btn = QPushButton("Cancelar")
        self._cancel_btn.setStyleSheet(f"""
            QPushButton {{ background:transparent; color:{DANGER};
                border:1px solid {DANGER}; border-radius:0; padding:6px 16px; font-size:{fs(12)}px; }}
            QPushButton:hover {{ background:rgba(192,57,43,0.1); }}
        """)
        self._cancel_btn.clicked.connect(self.cancel_requested.emit)
        layout.addWidget(self._cancel_btn, alignment=Qt.AlignmentFlag.AlignRight)
        
        # Contenedor de botones finales (oculto inicialmente)
        self._completion_buttons = QWidget()
        comp_layout = QHBoxLayout(self._completion_buttons)
        comp_layout.setContentsMargins(0, 0, 0, 0)
        comp_layout.setSpacing(8)
        
        self._open_folder_btn = QPushButton("Abrir carpeta")
        self._open_folder_btn.setStyleSheet(f"""
            QPushButton {{ background:{ACCENT}; color:#1a1714;
                border:none; border-radius:4px; padding:8px 20px; font-size:{fs(13)}px; font-weight:600; }}
            QPushButton:hover {{ background:{ACCENT3}; }}
        """)
        self._open_folder_btn.clicked.connect(self._open_folder)
        comp_layout.addWidget(self._open_folder_btn)
        
        self._close_btn = QPushButton("Cerrar")
        self._close_btn.setStyleSheet(f"""
            QPushButton {{ background:transparent; color:{TEXT0};
                border:1px solid {BORDER2}; border-radius:4px; padding:8px 20px; font-size:{fs(13)}px; }}
            QPushButton:hover {{ background:{BG3}; }}
        """)
        self._close_btn.clicked.connect(self.accept)
        comp_layout.addWidget(self._close_btn)
        
        layout.addWidget(self._completion_buttons)
        self._completion_buttons.hide()

    def set_output_path(self, path: str):
        """Guardar el path del video generado."""
        self._output_path = path

    def _time_to_sec(self, t: str) -> float:
        try:
            parts = t.split(":")
            return int(parts[0])*3600 + int(parts[1])*60 + float(parts[2])
        except Exception:
            return 0.0

    def update_progress(self, time_str: str):
        import time as _time
        if self._start_time is None:
            self._start_time = _time.monotonic()
        done_sec = self._time_to_sec(time_str)
        pct = min(99, int(done_sec / self._total_dur * 100))
        self._progress_bar.setValue(pct)
        self._pct_lbl.setText(f"{pct}%")
        h = int(done_sec // 3600); m = int((done_sec % 3600) // 60); s = int(done_sec % 60)
        cur_str = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
        tot = self._total_dur
        th = int(tot//3600); tm = int((tot%3600)//60); ts = int(tot%60)
        tot_str = f"{th}:{tm:02d}:{ts:02d}" if th else f"{tm}:{ts:02d}"
        self._time_lbl.setText(f"{cur_str} / {tot_str}")
        elapsed = _time.monotonic() - self._start_time
        if done_sec > 0.5 and elapsed > 1:
            speed = done_sec / elapsed
            eta_sec = (self._total_dur - done_sec) / speed
            em = int(eta_sec // 60); es = int(eta_sec % 60)
            self._eta_lbl.setText(f"Tiempo restante: {em}m {es}s")

    def mark_done(self):
        """Marcar como completado y mostrar botones finales."""
        self._progress_bar.setValue(100)
        self._pct_lbl.setText("100%")
        self._eta_lbl.setText("✓ Película creada exitosamente")
        self._eta_lbl.setStyleSheet(f"color:{ACCENT}; font-size:{fs(13)}px; font-weight:600;")
        
        # Ocultar botón cancelar, mostrar botones finales
        self._cancel_btn.hide()
        self._completion_buttons.show()
        
        # Permitir cerrar con X
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowCloseButtonHint)
        self.show()  # Refrescar flags
    
    def _open_folder(self):
        """Abrir la carpeta donde está el video."""
        if not self._output_path or not os.path.exists(self._output_path):
            return
        
        import subprocess, platform
        folder = os.path.dirname(self._output_path)
        
        try:
            if platform.system() == "Windows":
                os.startfile(folder)
            elif platform.system() == "Darwin":
                subprocess.call(["open", folder])
            else:
                subprocess.call(["xdg-open", folder])
        except Exception as e:
            print(f"Error opening folder: {e}")


# ── Modal configuración de render ────────────────────────────────────────────

class RenderSettingsDialog(QDialog):
    QUALITY = {
        "Alta (60fps)":  {"crf": 18, "fps": 60, "hint": "1920×1080  ·  60fps  ·  ~70 MB/min"},
        "Alta (30fps)":  {"crf": 18, "fps": 30, "hint": "1920×1080  ·  30fps  ·  ~50 MB/min"},
        "Media (60fps)": {"crf": 23, "fps": 60, "hint": "1920×1080  ·  60fps  ·  ~35 MB/min"},
        "Media (30fps)": {"crf": 23, "fps": 30, "hint": "1920×1080  ·  30fps  ·  ~20 MB/min"},
        "Baja":          {"crf": 30, "fps": 30, "hint": "1920×1080  ·  30fps  ·  ~8 MB/min"},
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración de exportación")
        self.setFixedWidth(420)
        self.setModal(True)
        self.setStyleSheet(f"background:{BG1};")

        self.mute_audio = False
        self.crf = 23
        self.fps = 30
        self.separate_files = False
        self.show_overlay = False
        self.transition = "cut"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        title = QLabel("Crear película")
        title.setStyleSheet(f"color:{TEXT0}; font-size:{fs(16)}px; font-weight:600;")
        layout.addWidget(title)

        # Calidad
        q_lbl = QLabel("CALIDAD")
        q_lbl.setStyleSheet(f"color:{ACCENT}; font-size:{fs(9)}px; font-weight:700; letter-spacing:1.5px;")
        layout.addWidget(q_lbl)

        self._quality_group = QButtonGroup(self)
        self._quality_hints = {}
        for label, info in self.QUALITY.items():
            row = QWidget()
            row.setStyleSheet("background:transparent;")
            rl = QVBoxLayout(row)
            rl.setContentsMargins(0, 2, 0, 2)
            rl.setSpacing(1)
            rb = QRadioButton(label)
            rb.setStyleSheet(f"color:{TEXT0}; font-size:{fs(12)}px;")
            rb.setProperty("crf", info["crf"])
            rb.setProperty("fps", info["fps"])
            if label == "Media (30fps)":
                rb.setChecked(True)
            self._quality_group.addButton(rb)
            rl.addWidget(rb)
            hint = QLabel(info["hint"])
            hint.setStyleSheet(f"color:{TEXT3}; font-size:{fs(10)}px; padding-left:22px;")
            rl.addWidget(hint)
            layout.addWidget(row)

        sep1 = QFrame()
        sep1.setFixedHeight(1)
        sep1.setStyleSheet("background:rgba(255,255,255,0.06);")
        layout.addWidget(sep1)

        # Overlay y Transición
        o_lbl = QLabel("OPCIONES DE VIDEO")
        o_lbl.setStyleSheet(f"color:{ACCENT}; font-size:{fs(9)}px; font-weight:700; letter-spacing:1.5px;")
        layout.addWidget(o_lbl)
        
        # Mostrar nombre del clip
        self._overlay_cb = QCheckBox("Mostrar nombre del clip en el video")
        self._overlay_cb.setStyleSheet(f"color:{TEXT1}; font-size:{fs(12)}px;")
        self._overlay_cb.setChecked(False)
        layout.addWidget(self._overlay_cb)
        
        # Transición
        trans_lbl = QLabel("Transición entre clips:")
        trans_lbl.setStyleSheet(f"color:{TEXT2}; font-size:{fs(11)}px; margin-top:8px;")
        layout.addWidget(trans_lbl)
        
        self._trans_combo = QComboBox()
        self._trans_combo.addItems(["Corte directo", "Fade negro (0.5s)", "Fade negro (1s)"])
        self._trans_combo.setStyleSheet(f"""
            QComboBox {{
                background:{BG2}; color:{TEXT0}; border:1px solid {BORDER2};
                border-radius:4px; padding:6px 10px; font-size:{fs(12)}px;
            }}
            QComboBox:hover {{ border-color:{ACCENT}; }}
            QComboBox::drop-down {{ border:none; }}
        """)
        layout.addWidget(self._trans_combo)

        sep2 = QFrame()
        sep2.setFixedHeight(1)
        sep2.setStyleSheet("background:rgba(255,255,255,0.06);")
        layout.addWidget(sep2)
        
        # Audio
        a_lbl = QLabel("OPCIONES DE AUDIO")
        a_lbl.setStyleSheet(f"color:{ACCENT}; font-size:{fs(9)}px; font-weight:700; letter-spacing:1.5px;")
        layout.addWidget(a_lbl)

        self._mute_cb = QCheckBox("Silenciar audio")
        self._mute_cb.setStyleSheet(f"color:{TEXT1}; font-size:{fs(12)}px;")
        layout.addWidget(self._mute_cb)

        self._separate_cb = QCheckBox("Crear archivos separados")
        self._separate_cb.setStyleSheet(f"color:{TEXT1}; font-size:{fs(12)}px;")
        layout.addWidget(self._separate_cb)

        sep_hint = QLabel("Cada registro se exporta como un MP4 individual")
        sep_hint.setStyleSheet(f"color:{TEXT3}; font-size:{fs(10)}px; padding-left:22px;")
        layout.addWidget(sep_hint)

        sep2 = QFrame()
        sep2.setFixedHeight(1)
        sep2.setStyleSheet("background:rgba(255,255,255,0.06);")
        layout.addWidget(sep2)

        # Botones
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{ background:transparent; color:{TEXT2};
                border:1px solid {BORDER2}; padding:6px 16px; font-size:{fs(12)}px; }}
            QPushButton:hover {{ color:{TEXT0}; border-color:{ACCENT}; }}
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        ok_btn = QPushButton("Exportar")
        ok_btn.setStyleSheet(f"""
            QPushButton {{ background:qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 {ACCENT3},stop:1 {ACCENT}); color:#1a1714;
                border:none; border-bottom:2px solid {ACCENT2};
                padding:6px 20px; font-size:{fs(12)}px; font-weight:600; }}
            QPushButton:hover {{ background:{ACCENT3}; }}
        """)
        ok_btn.clicked.connect(self._accept)
        btn_row.addWidget(ok_btn)
        layout.addLayout(btn_row)

    def _accept(self):
        checked = self._quality_group.checkedButton()
        self.crf = checked.property("crf") if checked else 23
        self.fps = checked.property("fps") if checked else 30
        self.mute_audio = self._mute_cb.isChecked()
        self.separate_files = self._separate_cb.isChecked()
        self.show_overlay = self._overlay_cb.isChecked()
        # Mapear transición
        trans_map = {
            "Corte directo": "cut",
            "Fade negro (0.5s)": "fade05",
            "Fade negro (1s)": "fade10"
        }
        self.transition = trans_map.get(self._trans_combo.currentText(), "cut")
        self.accept()


# ── Modal detalle clip ────────────────────────────────────────────────────────

class ClipDetailDialog(QDialog):
    item_deleted = Signal(str)
    navigate_to  = Signal(int)   # index delta: -1 prev, +1 next

    PALETTE = [
        "#2A2A30",
        "#C9A44A", "#4A90D9", "#27AE60", "#9B59B6",
        "#E67E22", "#E74C3C", "#1ABC9C", "#8BC34A",
    ]

    def __init__(self, item: PresentationItem, all_items: list = None, parent=None):
        super().__init__(parent)
        
        # Permitir maximizar la ventana
        from PySide6.QtCore import Qt
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint)
        
        self.setWindowTitle(item.name)
        self.setStyleSheet(f"background:{BG1};")
        self._item = item
        self._all_items = all_items or state.presentation
        self._mpv_player = None
        self._deleted = False
        self._goto_adjust_flag = False
        self._nav_delta = 0
        self._parent_widget = parent  # Guardar para usar en showEvent
        
        # Cargar preferencia de mute global
        from PySide6.QtCore import QSettings
        settings = QSettings("ScoutApp", "prefs")
        self._muted = settings.value("detail_muted", False, type=bool)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # No hay header en modo normal - más espacio para el video
        # El título se muestra en la barra de ventana
        self._header = None

        # ── Video preview ─────────────────────────────────────────────────────
        self._video_widget = None
        self._timeline = None
        
        if item.type == "clip" and item.video_path:
            from components.timeline import ClipTimeline
            
            # Container para video + timeline
            video_container = QWidget()
            video_container.setStyleSheet("background: #000;")
            vc_layout = QVBoxLayout(video_container)
            vc_layout.setContentsMargins(0, 0, 0, 0)
            vc_layout.setSpacing(0)
            
            # Video player
            vw = MpvWidget()
            vw.setMinimumHeight(400)
            self._video_widget = vw
            self._mpv_player = vw._player
            vc_layout.addWidget(vw, stretch=1)
            
            # Timeline con ventana amplia alrededor del clip
            self._timeline = ClipTimeline()
            
            # Usar zoom_idx=8 (300s = 5 minutos de ventana total)
            # Esto muestra ±2.5 minutos alrededor del centro
            self._timeline._zoom_idx = 8  # 300s window
            
            # Calcular el centro del clip como timestamp
            clip_center = item.clip_start + (item.clip_dur / 2)
            
            # Calcular offsets desde el centro del clip
            start_offset = -item.clip_dur / 2  # Distancia del centro al inicio
            end_offset = item.clip_dur / 2     # Distancia del centro al fin
            
            # Resetear timeline - esto mostrará el clip en el contexto de ±2.5 minutos
            self._timeline.reset(clip_center, start_offset, end_offset)
            
            # El usuario puede hacer zoom in/out para ajustar la ventana
            self._timeline.scrub_requested.connect(vw.seek)
            self._timeline.start_changed.connect(self._on_start_changed)
            self._timeline.end_changed.connect(self._on_end_changed)
            vw.position_changed.connect(self._timeline.update_playhead)
            vc_layout.addWidget(self._timeline)
            
            layout.addWidget(video_container, stretch=1)
            
            # Cargar video
            def on_loaded():
                try:
                    vw.seek(item.clip_start)
                    if self._muted and self._mpv_player:
                        self._mpv_player.mute = True
                    vw.play()
                except Exception: pass
            vw.file_loaded.connect(on_loaded)
            vw.playback_started.connect(lambda: self._play_btn.setIcon(pause_icon(size=(20, 20), color="#FFFFFF")))
            vw.playback_paused.connect(lambda: self._play_btn.setIcon(play_icon(size=(20, 20), color="#FFFFFF")))
            vw.load(item.video_path)

        elif item.type == "image" and item.image_path:
            import os
            if os.path.exists(item.image_path):
                img_lbl = QLabel()
                img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                img_lbl.setStyleSheet("background:#000;")
                pm = QPixmap(item.image_path)
                if not pm.isNull():
                    img_lbl.setPixmap(pm.scaled(800, 600,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation))
                layout.addWidget(img_lbl, stretch=1)
        else:
            lbl = QLabel("Vista previa no disponible")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color:{TEXT3}; font-size:{fs(13)}px;")
            layout.addWidget(lbl, stretch=1)

        # ── Control bar con navegación y controles ───────────────────────────
        ctrl = QWidget()
        ctrl.setFixedHeight(40)  # Reducido a 40px para maximizar video
        ctrl.setStyleSheet(f"""
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 {BG2}, stop:1 {BG1});
            border-top: 1px solid {BORDER2};
        """)
        cl = QHBoxLayout(ctrl)
        cl.setContentsMargins(16, 0, 16, 0)
        cl.setSpacing(12)

        # BOTÓN ANTERIOR - destacado
        prev_btn = QPushButton(" Anterior")
        prev_btn.setIcon(previous_icon(size=(16, 16), color=TEXT0))
        prev_btn.setIconSize(QSize(16, 16))
        prev_btn.setFixedSize(110, 40)
        prev_btn.setStyleSheet(f"""
            QPushButton {{ 
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 {BG3}, stop:1 {BG2});
                color: {TEXT0}; 
                border: 1px solid {BORDER2};
                border-radius: 6px;
                font-size: {fs(13)}px; 
                font-weight: 600;
                padding: 0;
            }}
            QPushButton:hover {{ 
                background: {BG3};
                border-color: {ACCENT};
            }}
        """)
        prev_btn.clicked.connect(lambda: self._navigate(-1))
        cl.addWidget(prev_btn)

        # Play/Pause
        self._play_btn = QPushButton()
        self._play_btn.setIcon(pause_icon(size=(20, 20), color="#FFFFFF") if self._video_widget else play_icon(size=(20, 20), color="#FFFFFF"))
        self._play_btn.setIconSize(QSize(20, 20))
        self._play_btn.setFixedSize(44, 44)
        self._play_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 {BG3}, stop:1 {BG2});
                border: 1px solid {BORDER2};
                border-bottom: 2px solid {BORDER2};
                border-radius: 6px;
                padding: 0; icon-size: 20px 20px;
            }}
            QPushButton:hover {{ background: {BG3}; border-color: {ACCENT}; }}
        """)
        if self._video_widget:
            self._play_btn.clicked.connect(self._video_widget.toggle_play)
        cl.addWidget(self._play_btn)

        # BOTÓN SIGUIENTE - destacado
        next_btn = QPushButton("Siguiente ")
        next_btn.setIcon(next_icon(size=(16, 16), color=TEXT0))
        next_btn.setIconSize(QSize(16, 16))
        next_btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        next_btn.setFixedSize(110, 40)
        next_btn.setStyleSheet(f"""
            QPushButton {{ 
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 {BG3}, stop:1 {BG2});
                color: {TEXT0}; 
                border: 1px solid {BORDER2};
                border-radius: 6px;
                font-size: {fs(13)}px; 
                font-weight: 600;
                padding: 0;
            }}
            QPushButton:hover {{ 
                background: {BG3};
                border-color: {ACCENT};
            }}
        """)
        next_btn.clicked.connect(lambda: self._navigate(1))
        cl.addWidget(next_btn)

        # Mute
        self._mute_btn = QPushButton()
        self._mute_btn.setIcon(mute_icon(size=(18, 18), color=TEXT2) if self._muted else volume_icon(size=(18, 18), color=TEXT2))
        self._mute_btn.setIconSize(QSize(18, 18))
        self._mute_btn.setFixedSize(36, 36)
        self._mute_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {TEXT2};
                border: none;
                font-size: {fs(18)}px;
                padding: 0; icon-size: 18px 18px;
            }}
            QPushButton:hover {{ color: {ACCENT}; }}
        """)
        self._mute_btn.clicked.connect(self._toggle_mute)
        cl.addWidget(self._mute_btn)

        # Botones de zoom del timeline (si hay timeline)
        if self._timeline:
            zoom_out_btn = QPushButton("−")
            zoom_out_btn.setFixedSize(32, 32)
            zoom_out_btn.setStyleSheet(f"""
                QPushButton {{ 
                    background: {BG3}; 
                    color: {TEXT0}; 
                    border: 1px solid {BORDER2};
                    border-radius: 4px;
                    font-size: {fs(16)}px; 
                    font-weight: bold;
                    padding: 0;
                }}
                QPushButton:hover {{ border-color: {ACCENT}; }}
            """)
            zoom_out_btn.clicked.connect(self._timeline.zoom_out)
            cl.addWidget(zoom_out_btn)

            zoom_in_btn = QPushButton("+")
            zoom_in_btn.setFixedSize(32, 32)
            zoom_in_btn.setStyleSheet(f"""
                QPushButton {{ 
                    background: {BG3}; 
                    color: {TEXT0}; 
                    border: 1px solid {BORDER2};
                    border-radius: 4px;
                    font-size: {fs(16)}px; 
                    font-weight: bold;
                    padding: 0;
                }}
                QPushButton:hover {{ border-color: {ACCENT}; }}
            """)
            zoom_in_btn.clicked.connect(self._timeline.zoom_in)
            cl.addWidget(zoom_in_btn)

        cl.addStretch()

        # Botón de pantalla completa
        self._fullscreen_btn = QPushButton()
        self._fullscreen_btn.setIcon(fullscreen_icon(size=(20, 20), color=TEXT2))
        self._fullscreen_btn.setIconSize(QSize(20, 20))
        self._fullscreen_btn.setFixedSize(36, 36)  # Botón compacto
        self._fullscreen_btn.setToolTip("Modo pantalla completa")
        self._fullscreen_btn.setStyleSheet(f"""
            QPushButton {{ 
                background: transparent; 
                color: {TEXT2}; 
                border: none;
                font-size: {fs(24)}px;  # Unicode más grande
                padding: 0;
            }}
            QPushButton:hover {{ color: {ACCENT}; }}
        """)
        self._fullscreen_btn.clicked.connect(self._toggle_fullscreen)
        cl.addWidget(self._fullscreen_btn)

        # Tiempo actual (solo si hay video)
        if self._video_widget:
            self._time_lbl = QLabel(f"0:00 / {self._fmt(item.clip_dur)}")
            self._time_lbl.setStyleSheet(f"color:{TEXT2}; font-size:{fs(11)}px; min-width:90px;")
            cl.addWidget(self._time_lbl)

        layout.addWidget(ctrl)
        
        # Guardar referencias para modo fullscreen
        self._normal_ctrl = ctrl
        self._is_fullscreen = False

        # ── Info bar combinado: Nombre + Notas en una sola fila ──────────────
        info = QWidget()
        info.setFixedHeight(44)  # Una sola fila compacta
        info.setStyleSheet(f"background:{BG2}; border-top:1px solid {BORDER2};")
        il = QHBoxLayout(info)
        il.setContentsMargins(12, 6, 12, 6)
        il.setSpacing(12)

        # Icono de edición
        pencil = QLabel("✎")
        pencil.setStyleSheet(f"color:{TEXT3}; font-size:{fs(14)}px; background:transparent;")
        il.addWidget(pencil)

        # Nombre (más compacto)
        self._name_edit = QLineEdit(item.name)
        self._name_edit.setFixedWidth(180)  # Ancho fijo para dejar espacio a notas
        self._name_edit.setStyleSheet(f"""
            QLineEdit {{ 
                color: {TEXT0}; 
                background: {BG3}; 
                border: none;
                border-bottom: 1px solid {BORDER2};
                font-size: {fs(13)}px; 
                font-weight: 600; 
                padding: 4px 8px;
            }}
            QLineEdit:focus {{ border-bottom: 1px solid {ACCENT}; }}
        """)
        self._name_edit.editingFinished.connect(self._save_name)
        il.addWidget(self._name_edit)

        # Duración
        il.addWidget(QLabel(f"{item.duration:.1f}s",
            styleSheet=f"color:{ACCENT}; font-size:{fs(11)}px; font-weight:600; background:transparent;"))

        # Separador visual
        sep = QFrame()
        sep.setFixedSize(1, 24)
        sep.setStyleSheet(f"background:{BORDER2};")
        il.addWidget(sep)

        # Notas (en la misma fila, sin label "NOTAS")
        from PySide6.QtWidgets import QTextEdit
        self._note_edit = QTextEdit()
        self._note_edit.setPlainText(item.note or "")
        self._note_edit.setFixedHeight(32)  # Altura de una línea
        self._note_edit.setStyleSheet(f"""
            QTextEdit {{
                background: {BG3};
                color: {TEXT1};
                border: none;
                border-bottom: 1px solid {BORDER2};
                padding: 4px 8px;
                font-size: {fs(11)}px;
            }}
            QTextEdit:focus {{
                border-bottom: 1px solid {ACCENT};
            }}
        """)
        self._note_edit.setPlaceholderText("Notas...")
        self._note_edit.textChanged.connect(self._save_note)
        il.addWidget(self._note_edit, stretch=1)  # Ocupa el resto del espacio

        layout.addWidget(info)
        self._info_bar = info  # Guardar referencia
        self._notes_container = info  # Apuntar al mismo widget (para compatibilidad)

        # ── Color bar + visibilidad + delete ──────────────────────────────────
        toolbar = QWidget()
        toolbar.setFixedHeight(28)  # Reducido de 32 a 28
        toolbar.setStyleSheet(f"background:{BG2}; border-top:1px solid {BORDER2};")
        tl = QHBoxLayout(toolbar)
        tl.setContentsMargins(16, 0, 16, 0)
        tl.setSpacing(8)

        tl.addWidget(QLabel("Color:", styleSheet=f"color:{TEXT2}; font-size:{fs(10)}px;"))
        self._color_btns = []
        for c in self.PALETTE:
            cb = QPushButton()
            cb.setFixedSize(18, 18)
            cb.setStyleSheet(self._swatch_style(c, c == item.color))
            cb.setCursor(Qt.CursorShape.PointingHandCursor)
            cb.clicked.connect(lambda checked, color=c: self._set_color(color))
            tl.addWidget(cb)
            self._color_btns.append((cb, c))

        tl.addStretch()

        # Visibility toggle
        self._vis_state = item.visible
        self._vis_btn = QPushButton(" Visible" if self._vis_state else " Oculto")
        self._vis_btn.setIcon(eye_icon(size=(16, 16), color=TEXT2) if self._vis_state else eye_off_icon(size=(16, 16), color=DANGER))
        self._vis_btn.setIconSize(QSize(16, 16))
        self._vis_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; color:{TEXT2}; border:none;"
            f" border-bottom:1px solid {BORDER2}; font-size:{fs(10)}px; padding:3px 8px;"
            f" min-height:0; min-width:0; }}"
            f"QPushButton:hover {{ color:{ACCENT}; border-bottom-color:{ACCENT}; }}"
        )
        self._vis_btn.clicked.connect(self._toggle_visibility)
        tl.addWidget(self._vis_btn)

        del_btn = QPushButton("Eliminar")
        del_btn.setStyleSheet(f"""
            QPushButton {{ background:transparent; color:{DANGER}; border:none;
                border-bottom:1px solid {DANGER}; font-size:{fs(11)}px; padding:3px 8px; }}
            QPushButton:hover {{ background:rgba(192,57,43,0.1); }}
        """)
        del_btn.clicked.connect(self._confirm_delete)
        tl.addWidget(del_btn)
        layout.addWidget(toolbar)
        self._toolbar = toolbar  # Guardar referencia

        # ── Botón Salir (compacto) ────────────────────────────────────────────
        # Solo visible cuando NO está en fullscreen
        self._footer = QWidget()
        self._footer.setStyleSheet(f"background:{BG2}; border-top:1px solid {BORDER2};")
        footer_layout = QHBoxLayout(self._footer)
        footer_layout.setContentsMargins(12, 4, 12, 4)  # Reducido de 8 a 4
        footer_layout.setSpacing(8)
        
        footer_layout.addStretch()  # Empujar botón a la derecha
        
        exit_btn = QPushButton("Salir")
        exit_btn.setFixedHeight(24)  # 50% del original (era 32)
        exit_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {TEXT0};
                border: none;
                border-bottom: 1px solid {BORDER2};
                padding: 2px 16px;
                font-size: {fs(11)}px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                color: {ACCENT};
                border-bottom: 1px solid {ACCENT};
            }}
        """)
        exit_btn.clicked.connect(self.close)
        footer_layout.addWidget(exit_btn)
        
        layout.addWidget(self._footer)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _nav_btn_style(self):
        return (
            f"QPushButton {{ background:transparent; color:{TEXT2}; border:none;"
            f" font-size:{fs(12)}px; padding:0; min-height:0; min-width:0; }}"
            f"QPushButton:hover {{ color:{ACCENT}; }}"
        )

    @staticmethod
    def _fmt(s):
        m, sec = int(s) // 60, int(s) % 60
        return f"{m}:{sec:02d}"

    # ── Playback ──────────────────────────────────────────────────────────────

    def _on_start_changed(self, offset_sec):
        """Callback cuando el usuario arrastra el handle de inicio en el timeline."""
        # El timeline emite offset desde el centro del clip
        # Necesitamos calcular el nuevo inicio absoluto
        clip_center = self._item.clip_start + (self._item.clip_dur / 2)
        new_start = clip_center + offset_sec
        
        # Calcular nueva duración (el fin no cambia)
        clip_end = self._item.clip_start + self._item.clip_dur
        new_dur = clip_end - new_start
        
        # Actualizar en el estado
        state.update_pres_item(self._item.id, clip_start=new_start, clip_dur=new_dur)
        self._item.clip_start = new_start
        self._item.clip_dur = new_dur
    
    def _on_end_changed(self, offset_sec):
        """Callback cuando el usuario arrastra el handle de fin en el timeline."""
        # El timeline emite offset desde el centro del clip
        clip_center = self._item.clip_start + (self._item.clip_dur / 2)
        new_end = clip_center + offset_sec
        
        # Calcular nueva duración (el inicio no cambia)
        new_dur = new_end - self._item.clip_start
        
        # Actualizar en el estado
        state.update_pres_item(self._item.id, clip_dur=new_dur)
        self._item.clip_dur = new_dur

    def _check_loop(self, pos):
        """Loop: si la posición supera el final del clip, volver al inicio."""
        if getattr(self, '_looping', False):
            return
        # Usar el final dinámico desde el timeline si existe
        clip_end = self._item.clip_start + self._item.clip_dur
        if pos >= clip_end - 0.15:
            self._looping = True
            self._video_widget.seek(self._item.clip_start)
            from PySide6.QtCore import QTimer
            QTimer.singleShot(300, lambda: setattr(self, '_looping', False))

    def _on_pos_update(self, pos):
        """Actualizar tiempo mostrado (ya no se usa con timeline, pero mantener para imágenes)."""
        if hasattr(self, '_time_lbl'):
            elapsed = max(0, pos - self._item.clip_start)
            self._time_lbl.setText(f"{self._fmt(elapsed)} / {self._fmt(self._item.clip_dur)}")

    def _on_scrub_seek(self, t):
        """Ya no se usa con timeline, pero mantener por compatibilidad."""
        if self._video_widget:
            self._video_widget.seek(self._item.clip_start + t)

    def _toggle_mute(self):
        self._muted = not self._muted
        
        # Guardar preferencia global
        from PySide6.QtCore import QSettings
        settings = QSettings("ScoutApp", "prefs")
        settings.setValue("detail_muted", self._muted)
        
        # Aplicar al player actual
        try:
            if self._mpv_player:
                self._mpv_player.mute = self._muted
        except Exception: pass
        
        self._mute_btn.setIcon(mute_icon(size=(18, 18), color=TEXT2) if self._muted else volume_icon(size=(18, 18), color=TEXT2))

    # ── Keyboard shortcuts ────────────────────────────────────────────────────

    def keyPressEvent(self, e):
        k = e.key()
        shift = bool(e.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        if k == Qt.Key.Key_Space:
            if self._video_widget: self._video_widget.toggle_play()
        elif k == Qt.Key.Key_M:
            self._toggle_mute()
        elif k == Qt.Key.Key_Left:
            if self._video_widget:
                d = -60 if shift else -5
                self._video_widget.seek(max(self._item.clip_start, self._video_widget.position + d))
        elif k == Qt.Key.Key_Right:
            if self._video_widget:
                d = 60 if shift else 5
                self._video_widget.seek(min(self._clip_end, self._video_widget.position + d))
        elif k == Qt.Key.Key_Up:
            if self._video_widget:
                self._video_widget.seek(max(self._item.clip_start, self._video_widget.position + 10))
        elif k == Qt.Key.Key_Down:
            if self._video_widget:
                self._video_widget.seek(max(self._item.clip_start, self._video_widget.position - 10))
        elif k == Qt.Key.Key_Escape:
            if self._is_fullscreen:
                self._exit_fullscreen()
            else:
                self._safe_close()
        else:
            super().keyPressEvent(e)

    # ── Navigation ────────────────────────────────────────────────────────────

    def _navigate(self, delta):
        """Navegar al clip anterior/siguiente sin cerrar la ventana."""
        # Encontrar índice actual
        try:
            idx = next(i for i, it in enumerate(self._all_items) if it.id == self._item.id)
        except StopIteration:
            return
        
        # Calcular nuevo índice
        new_idx = idx + delta
        if not (0 <= new_idx < len(self._all_items)):
            return  # Fuera de rango
        
        # Cargar nuevo clip
        new_item = self._all_items[new_idx]
        self._load_item(new_item)
    
    def _load_item(self, item: PresentationItem):
        """Recargar el diálogo con un nuevo clip."""
        # Mostrar indicador de carga
        if hasattr(self, '_title_lbl'):
            self._title_lbl.setText("Cargando...")
        
        # Limpiar video anterior si existe
        if self._video_widget and self._mpv_player:
            try:
                self._mpv_player.pause = True
            except Exception:
                pass
        
        # Actualizar item
        self._item = item
        
        # Actualizar título
        self.setWindowTitle(item.name)
        if hasattr(self, '_title_lbl'):
            self._title_lbl.setText(item.name)
        
        # Actualizar nombre en el campo de edición
        if hasattr(self, '_name_edit'):
            self._name_edit.setText(item.name)
        
        # Actualizar notas
        if hasattr(self, '_note_edit'):
            self._note_edit.setPlainText(item.note or "")
        
        # Actualizar visibilidad
        if hasattr(self, '_vis_btn'):
            self._vis_state = item.visible
            self._vis_btn.setIcon(eye_icon(size=(16, 16), color=TEXT2) if item.visible else eye_off_icon(size=(16, 16), color=DANGER))
            self._vis_btn.setText(" Visible" if item.visible else " Oculto")
        
        # Actualizar colores
        if hasattr(self, '_color_btns'):
            for cb, c in self._color_btns:
                cb.setStyleSheet(self._swatch_style(c, c == item.color))
        
        # Recargar video/imagen si existe
        if item.type == "clip" and item.video_path and self._video_widget:
            # Actualizar timeline
            if self._timeline:
                clip_center = item.clip_start + (item.clip_dur / 2)
                start_offset = -item.clip_dur / 2
                end_offset = item.clip_dur / 2
                self._timeline.reset(clip_center, start_offset, end_offset)
            
            # Cargar nuevo video
            self._video_widget.load(item.video_path)
            
            # Seek al inicio del clip cuando cargue
            def on_loaded():
                try:
                    self._video_widget.seek(item.clip_start)
                    if self._muted and self._mpv_player:
                        self._mpv_player.mute = True
                    self._video_widget.play()
                except Exception:
                    pass
            
            # Reconectar señal de carga
            try:
                self._video_widget.file_loaded.disconnect()
            except (RuntimeError, TypeError):
                pass
            self._video_widget.file_loaded.connect(on_loaded)

    # ── Color / name / delete ─────────────────────────────────────────────────

    def _swatch_style(self, color, active):
        border = f"2px solid {TEXT0}" if active else "1px solid rgba(255,255,255,0.15)"
        return (f"QPushButton {{ background:{color}; border:{border}; border-radius:2px; }}"
                f"QPushButton:hover {{ border:2px solid {ACCENT}; }}")

    def _set_color(self, color):
        state.update_pres_item(self._item.id, color=color)
        self._item.color = color
        for cb, c in self._color_btns:
            cb.setStyleSheet(self._swatch_style(c, c == color))

    def _toggle_visibility(self):
        self._vis_state = not self._vis_state
        self._item.visible = self._vis_state
        self._vis_btn.setIcon(eye_icon(size=(16, 16), color=TEXT2) if self._vis_state else eye_off_icon(size=(16, 16), color=DANGER))
        self._vis_btn.setText(" Visible" if self._vis_state else " Oculto")
        state.presentation_changed.emit()

    def _save_name(self):
        new_name = self._name_edit.text().strip()
        if new_name and new_name != self._item.name:
            state.update_pres_item(self._item.id, name=new_name)
            self._item.name = new_name
            self.setWindowTitle(new_name)
            if hasattr(self, '_title_lbl'):
                self._title_lbl.setText(new_name)
    
    def _save_note(self):
        """Guardar notas del clip."""
        new_note = self._note_edit.toPlainText().strip()
        if new_note != self._item.note:
            state.update_pres_item(self._item.id, note=new_note)
            self._item.note = new_note
    
    def _toggle_fullscreen(self):
        """Alternar entre modo normal y pantalla completa."""
        if not self._is_fullscreen:
            # Entrar en modo pantalla completa
            self._enter_fullscreen()
        else:
            # Salir de modo pantalla completa
            self._exit_fullscreen()
    
    def _enter_fullscreen(self):
        """Entrar en modo pantalla completa REAL."""
        self._is_fullscreen = True
        
        # Guardar geometría anterior
        self._normal_geometry = self.geometry()
        
        # Entrar en pantalla completa del sistema
        self.showFullScreen()
        
        # Ocultar timeline, info bar, toolbar, notas, footer (no hay header)
        if self._timeline:
            self._timeline.hide()
        self._normal_ctrl.hide()
        self._info_bar.hide()
        self._toolbar.hide()
        self._notes_container.hide()
        if hasattr(self, '_footer'):
            self._footer.hide()  # Ocultar botón Salir en fullscreen
        
        # Crear control bar elegante para fullscreen
        self._fs_ctrl = QWidget()
        self._fs_ctrl.setFixedHeight(56)
        self._fs_ctrl.setStyleSheet(f"""
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1, 
                stop:0 rgba(26,26,30,0.95), stop:1 rgba(18,18,22,0.98));
            border-top: 1px solid rgba(255,255,255,0.08);
        """)
        
        fs_lo = QHBoxLayout(self._fs_ctrl)
        fs_lo.setContentsMargins(24, 0, 24, 0)
        fs_lo.setSpacing(16)
        
        # ◀ ANTERIOR
        prev_btn = QPushButton()
        prev_btn.setIcon(previous_icon(size=(20, 20), color=TEXT0))
        prev_btn.setIconSize(QSize(20, 20))
        prev_btn.setFixedSize(44, 44)
        prev_btn.setToolTip("Anterior (←)")
        prev_btn.setStyleSheet(f"""
            QPushButton {{ 
                background: rgba(255,255,255,0.08);
                color: {TEXT0}; 
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 22px;
                font-size: {fs(16)}px;
                font-weight: 600;
            }}
            QPushButton:hover {{ 
                background: rgba(255,255,255,0.15);
                border-color: {ACCENT};
            }}
        """)
        prev_btn.clicked.connect(lambda: self._navigate(-1))
        fs_lo.addWidget(prev_btn)
        
        # ▶ PLAY/PAUSE
        play_btn = QPushButton()
        play_btn.setIcon(pause_icon(size=(24, 24), color="#FFFFFF") if (self._video_widget and not self._video_widget.is_paused()) else play_icon(size=(24, 24), color="#FFFFFF"))
        play_btn.setIconSize(QSize(24, 24))
        play_btn.setFixedSize(52, 52)
        play_btn.setStyleSheet(f"""
            QPushButton {{ 
                background: rgba(255,255,255,0.10);
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 26px;
                padding: 0;
            }}
            QPushButton:hover {{ 
                background: rgba(255,255,255,0.18);
                border-color: {ACCENT};
            }}
        """)
        if self._video_widget:
            play_btn.clicked.connect(self._video_widget.toggle_play)
        fs_lo.addWidget(play_btn)
        self._fs_play_btn = play_btn
        
        # ▶ SIGUIENTE
        next_btn = QPushButton()
        next_btn.setIcon(next_icon(size=(20, 20), color=TEXT0))
        next_btn.setIconSize(QSize(20, 20))
        next_btn.setFixedSize(44, 44)
        next_btn.setToolTip("Siguiente (→)")
        next_btn.setStyleSheet(f"""
            QPushButton {{ 
                background: rgba(255,255,255,0.08);
                color: {TEXT0}; 
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 22px;
                font-size: {fs(16)}px;
                font-weight: 600;
            }}
            QPushButton:hover {{ 
                background: rgba(255,255,255,0.15);
                border-color: {ACCENT};
            }}
        """)
        next_btn.clicked.connect(lambda: self._navigate(1))
        fs_lo.addWidget(next_btn)
        
        fs_lo.addSpacing(24)
        
        # NOMBRE (editable)
        name_wrap = QWidget()
        name_wrap.setStyleSheet("background: transparent;")
        name_lo = QHBoxLayout(name_wrap)
        name_lo.setContentsMargins(0, 0, 0, 0)
        name_lo.setSpacing(8)
        
        pencil = QLabel("✎")
        pencil.setStyleSheet(f"color:{TEXT3}; font-size:{fs(14)}px;")
        name_lo.addWidget(pencil)
        
        fs_name_edit = QLineEdit(self._item.name)
        fs_name_edit.setStyleSheet(f"""
            QLineEdit {{ 
                color: {ACCENT}; 
                background: transparent;
                border: none;
                border-bottom: 1px solid rgba(255,255,255,0.2);
                font-size: {fs(16)}px; 
                font-weight: 600;
                padding: 4px 8px;
            }}
            QLineEdit:focus {{ 
                border-bottom-color: {ACCENT};
            }}
        """)
        fs_name_edit.editingFinished.connect(lambda: self._save_fs_name(fs_name_edit))
        name_lo.addWidget(fs_name_edit, stretch=1)
        self._fs_name_edit = fs_name_edit
        
        fs_lo.addWidget(name_wrap, stretch=1)
        
        fs_lo.addSpacing(24)
        
        # VISIBILIDAD (texto en lugar de emoji)
        vis_text = "Visible" if self._item.visible else "Oculto"
        vis_btn = QPushButton(vis_text)
        vis_btn.setFixedHeight(44)
        vis_btn.setMinimumWidth(80)
        vis_btn.setToolTip("Alternar visibilidad")
        vis_color = ACCENT if self._item.visible else DANGER
        vis_btn.setStyleSheet(f"""
            QPushButton {{ 
                background: rgba(255,255,255,0.05);
                color: {vis_color}; 
                border: 1px solid {vis_color};
                border-radius: 22px;
                font-size: {fs(13)}px;
                font-weight: 600;
                padding: 0 16px;
            }}
            QPushButton:hover {{ 
                background: rgba(255,255,255,0.12);
            }}
        """)
        vis_btn.clicked.connect(lambda: self._toggle_fs_visibility(vis_btn))
        fs_lo.addWidget(vis_btn)
        self._fs_vis_btn = vis_btn
        
        # SALIR DE PANTALLA COMPLETA
        exit_fs_btn = QPushButton()
        exit_fs_btn.setIcon(fullscreen_exit_icon(size=(22, 22), color="#FFFFFF"))
        exit_fs_btn.setIconSize(QSize(22, 22))
        exit_fs_btn.setFixedSize(44, 44)
        exit_fs_btn.setToolTip("Salir de pantalla completa (Esc)")
        exit_fs_btn.setStyleSheet(f"""
            QPushButton {{ 
                background: rgba(255,255,255,0.05);
                color: {TEXT2}; 
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 22px;
            }}
            QPushButton:hover {{ 
                background: rgba(255,255,255,0.12);
                color: {ACCENT};
            }}
        """)
        exit_fs_btn.clicked.connect(self._exit_fullscreen)
        fs_lo.addWidget(exit_fs_btn)
        
        # Agregar control bar de fullscreen al layout
        self.layout().addWidget(self._fs_ctrl)
        
        # Cambiar icono del botón principal
        self._fullscreen_btn.setIcon(fullscreen_icon(size=(20, 20), color=TEXT2))
    
    def _exit_fullscreen(self):
        """Salir de modo pantalla completa."""
        self._is_fullscreen = False
        
        # Salir de pantalla completa del sistema
        self.showNormal()
        
        # Restaurar geometría anterior
        if hasattr(self, '_normal_geometry'):
            self.setGeometry(self._normal_geometry)
        
        # Mostrar todo de nuevo (no hay header)
        if self._timeline:
            self._timeline.show()
        self._normal_ctrl.show()
        self._info_bar.show()
        self._toolbar.show()
        self._notes_container.show()
        if hasattr(self, '_footer'):
            self._footer.show()  # Mostrar botón Salir al salir de fullscreen
        
        # Eliminar control bar de fullscreen
        if hasattr(self, '_fs_ctrl'):
            self._fs_ctrl.deleteLater()
            self._fs_ctrl = None
        
        self._fullscreen_btn.setIcon(fullscreen_icon(size=(20, 20), color=TEXT2))
    
    def _save_fs_name(self, edit):
        """Guardar nombre desde el modo fullscreen."""
        new_name = edit.text().strip()
        if new_name and new_name != self._item.name:
            state.update_pres_item(self._item.id, name=new_name)
            self._item.name = new_name
            self.setWindowTitle(new_name)
            if hasattr(self, '_title_lbl'):
                self._title_lbl.setText(new_name)
            self._name_edit.setText(new_name)
    
    def _toggle_fs_visibility(self, btn):
        """Toggle visibilidad desde fullscreen."""
        self._vis_state = not self._vis_state
        state.update_pres_item(self._item.id, visible=self._vis_state)
        self._item.visible = self._vis_state
        
        # Actualizar texto del botón
        vis_text = "Visible" if self._vis_state else "Oculto"
        btn.setText(vis_text)
        
        # Actualizar color
        vis_color = ACCENT if self._vis_state else DANGER
        btn.setStyleSheet(f"""
            QPushButton {{ 
                background: rgba(255,255,255,0.05);
                color: {vis_color}; 
                border: 1px solid {vis_color};
                border-radius: 22px;
                font-size: {fs(13)}px;
                font-weight: 600;
                padding: 0 16px;
            }}
            QPushButton:hover {{ 
                background: rgba(255,255,255,0.12);
            }}
        """)
        
        # Actualizar también el botón en modo normal si existe
        if hasattr(self, '_vis_btn'):
            self._vis_btn.setIcon(eye_icon(size=(16, 16), color=TEXT2) if self._vis_state else eye_off_icon(size=(16, 16), color=DANGER))
            self._vis_btn.setText(" Visible" if self._vis_state else " Oculto")


    def _goto_adjust(self):
        self._goto_adjust_flag = True
        self._safe_close()

    def _confirm_delete(self):
        from PySide6.QtWidgets import QMessageBox
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Eliminar de la presentación")
        dlg.setText(f'¿Eliminar "{self._item.name}"?')
        ok = dlg.addButton("Eliminar", QMessageBox.ButtonRole.DestructiveRole)
        dlg.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        dlg.exec()
        if dlg.clickedButton() == ok:
            self._deleted = True
            state.remove_pres_item(self._item.id)
            self._safe_close()

    def _safe_close(self):
        """Limpiar recursos del video player antes de cerrar."""
        if self._video_widget:
            # Detener timer primero
            try:
                if hasattr(self._video_widget, '_ui_timer'):
                    self._video_widget._ui_timer.stop()
            except (RuntimeError, AttributeError):
                pass
            
            # Desconectar señales solo si están conectadas
            try:
                self._video_widget.position_changed.disconnect()
            except (RuntimeError, TypeError):
                # TypeError: señal no estaba conectada
                # RuntimeError: widget ya destruido
                pass
            
            try:
                self._video_widget.file_loaded.disconnect()
            except (RuntimeError, TypeError):
                pass
            
            try:
                self._video_widget.playback_started.disconnect()
            except (RuntimeError, TypeError):
                pass
            
            try:
                self._video_widget.playback_paused.disconnect()
            except (RuntimeError, TypeError):
                pass
            
            # Pausar y terminar mpv
            if self._mpv_player:
                try:
                    self._mpv_player.pause = True
                except Exception:
                    pass
                
                try:
                    self._mpv_player.terminate()
                except Exception:
                    pass
                
                self._mpv_player = None
                self._video_widget._player = None
            
            # Ocultar el widget antes de destruirlo (reduce reparenting warnings)
            try:
                self._video_widget.hide()
                self._video_widget.setParent(None)
            except RuntimeError:
                pass
            
            self._video_widget = None
        
        self.accept()
    
    def showEvent(self, e):
        """Forzar tamaño al 90% cada vez que se muestra el diálogo."""
        super().showEvent(e)
        if self._parent_widget:
            parent_geo = self._parent_widget.geometry()
            width = int(parent_geo.width() * 0.9)
            height = int(parent_geo.height() * 0.9)
            self.resize(width, height)
            # Centrar en la ventana padre
            self.move(
                parent_geo.x() + (parent_geo.width() - width) // 2,
                parent_geo.y() + (parent_geo.height() - height) // 2
            )
        else:
            # Sin padre, tamaño grande por defecto y centrar en pantalla
            self.resize(1400, 900)
            from PySide6.QtGui import QGuiApplication
            screen = QGuiApplication.primaryScreen().geometry()
            self.move(
                (screen.width() - 1400) // 2,
                (screen.height() - 900) // 2
            )

    def closeEvent(self, e):
        self._safe_close()
        if e: e.ignore()


# ── Contenedor con drop indicator + selección ─────────────────────────────────

# ── DragDropListWidget ────────────────────────────────────────────────────────

class DragDropListWidget(QWidget):
    """
    Contenedor simple de filas con:
    - Multi-select: click (solo), Ctrl+click (toggle), Shift+click (rango)
    - Drag & drop de una o varias filas seleccionadas
    - Drop indicator visual
    """
    ROW_H = 38

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._insert_index  = -1
        self._selected_ids: set = set()
        self._last_idx      = -1
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._layout.addStretch()
        
        # Auto-scroll durante drag
        from PySide6.QtCore import QTimer
        self._auto_scroll_timer = QTimer(self)
        self._auto_scroll_timer.setInterval(30)  # ~33 fps para suavidad
        self._auto_scroll_timer.timeout.connect(self._do_auto_scroll)
        self._scroll_delta = 0

    def layout(self):
        return self._layout

    # ── Rows ──────────────────────────────────────────────────────────────────

    def _rows(self) -> list:
        result = []
        for i in range(self._layout.count()):
            w = self._layout.itemAt(i).widget()
            if w and isinstance(w, PresentationRowWidget):
                result.append(w)
        return result

    def _row_count(self) -> int:
        return len(self._rows())

    # ── Selection ─────────────────────────────────────────────────────────────

    def select(self, item_id: str, ctrl=False, shift=False):
        rows = self._rows()
        idx  = next((i for i, r in enumerate(rows) if r._item.id == item_id), -1)
        if shift and self._last_idx >= 0 and idx >= 0:
            lo, hi = sorted([self._last_idx, idx])
            self._selected_ids = {rows[i]._item.id for i in range(lo, hi+1)}
        elif ctrl:
            if item_id in self._selected_ids:
                self._selected_ids.discard(item_id)
            else:
                self._selected_ids.add(item_id)
        else:
            self._selected_ids = {item_id}
        if idx >= 0:
            self._last_idx = idx
        self.update()

    def is_selected(self, item_id: str) -> bool:
        return item_id in self._selected_ids

    def clear_selection(self):
        self._selected_ids.clear()
        self._last_idx = -1
        self.update()

    # ── Drop indicator ────────────────────────────────────────────────────────

    def _calc_insert_index(self, y: float) -> int:
        for i, row in enumerate(self._rows()):
            if y < row.y() + row.height() / 2:
                return i
        return self._row_count()

    def paintEvent(self, e):
        super().paintEvent(e)
        if self._insert_index < 0:
            return
        p = QPainter(self)
        rows = self._rows()
        n = len(rows)
        if n == 0:
            y = 1
        elif self._insert_index >= n:
            y = rows[-1].y() + rows[-1].height() - 1
        else:
            y = rows[self._insert_index].y()
        # Gold line indicator — simple and clean
        p.setPen(QPen(QColor(str(ACCENT)), 2))
        p.drawLine(8, y, self.width() - 8, y)
        # Small triangle markers at edges
        p.setBrush(QColor(str(ACCENT)))
        p.setPen(QPen(QColor(str(ACCENT)), 1))
        p.drawPolygon([QPoint(0, y-4), QPoint(0, y+4), QPoint(8, y)])
        p.drawPolygon([QPoint(self.width(), y-4), QPoint(self.width(), y+4), QPoint(self.width()-8, y)])

    # ── Drag & drop ───────────────────────────────────────────────────────────

    def dragEnterEvent(self, e):
        txt = e.mimeData().text() if e.mimeData().hasText() else ""
        if txt.startswith("pyscout/drag:"):
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        txt = e.mimeData().text() if e.mimeData().hasText() else ""
        if txt.startswith("pyscout/drag:"):
            self._insert_index = self._calc_insert_index(e.position().y())
            self.update()
            e.acceptProposedAction()
            
            # Auto-scroll: detectar si está cerca de los bordes del área visible
            scroll_area = self._find_scroll_area()
            if scroll_area:
                # Convertir posición del evento a coordenadas del viewport
                global_pos = self.mapToGlobal(e.position().toPoint())
                viewport_pos = scroll_area.viewport().mapFromGlobal(global_pos)
                viewport_y = viewport_pos.y()
                viewport_height = scroll_area.viewport().height()
                
                EDGE_THRESHOLD = 60   # píxeles desde el borde para activar
                SCROLL_SPEED = 20     # píxeles por tick (más rápido)
                
                if viewport_y < EDGE_THRESHOLD:
                    # Cerca del borde superior - scrollear hacia arriba
                    # Más rápido cuanto más cerca del borde
                    factor = 1.0 + (EDGE_THRESHOLD - viewport_y) / EDGE_THRESHOLD
                    self._scroll_delta = -int(SCROLL_SPEED * factor)
                    if not self._auto_scroll_timer.isActive():
                        self._auto_scroll_timer.start()
                elif viewport_y > viewport_height - EDGE_THRESHOLD:
                    # Cerca del borde inferior - scrollear hacia abajo
                    factor = 1.0 + (viewport_y - (viewport_height - EDGE_THRESHOLD)) / EDGE_THRESHOLD
                    self._scroll_delta = int(SCROLL_SPEED * factor)
                    if not self._auto_scroll_timer.isActive():
                        self._auto_scroll_timer.start()
                else:
                    # En el medio, detener auto-scroll
                    self._scroll_delta = 0
                    self._auto_scroll_timer.stop()

    def dragLeaveEvent(self, e):
        self._insert_index = -1
        self._scroll_delta = 0
        self._auto_scroll_timer.stop()
        self.update()

    def dropEvent(self, e):
        txt = e.mimeData().text() if e.mimeData().hasText() else ""
        if not txt.startswith("pyscout/drag:"):
            return
        target = self._insert_index
        self._insert_index = -1
        self.update()

        # Parse MIME: pyscout/drag:id1,id2,...:from_pres_idx
        parts = txt.split(":")
        sel_ids = set(parts[1].split(",")) if len(parts) > 1 else set()
        from_idx = int(parts[2]) if len(parts) > 2 else state.active_pres_idx

        rows = self._rows()
        selected_indices = [i for i, r in enumerate(rows) if r._item.id in sel_ids]
        if not selected_indices:
            return

        items = list(state.presentation)
        selected_items = [items[i] for i in selected_indices]
        remaining = [it for i, it in enumerate(items) if i not in set(selected_indices)]

        n_before = sum(1 for i in selected_indices if i < target)
        insert_at = max(0, min(target - n_before, len(remaining)))

        new_order = remaining[:insert_at] + selected_items + remaining[insert_at:]
        state.push_undo()
        state.presentation = new_order
        
        # Sincronizar con el slot activo
        if 0 <= state.active_pres_idx < len(state.presentations):
            state.presentations[state.active_pres_idx] = state.presentation
        
        state.presentation_changed.emit()
        e.acceptProposedAction()
        
        # Detener auto-scroll al soltar
        self._scroll_delta = 0
        self._auto_scroll_timer.stop()

    def _find_scroll_area(self):
        """Buscar el QScrollArea padre que contiene este widget."""
        from PySide6.QtWidgets import QScrollArea
        parent = self.parentWidget()
        while parent:
            if isinstance(parent, QScrollArea):
                return parent
            parent = parent.parentWidget()
        return None
    
    def _do_auto_scroll(self):
        """Ejecutar el scroll automático durante el drag."""
        if self._scroll_delta == 0:
            return
        scroll_area = self._find_scroll_area()
        if not scroll_area:
            return
        scrollbar = scroll_area.verticalScrollBar()
        if scrollbar:
            new_value = scrollbar.value() + self._scroll_delta
            scrollbar.setValue(new_value)
    
    def wheelEvent(self, e):
        """Scroll suave y sensible con la rueda del mouse."""
        scroll_area = self._find_scroll_area()
        if scroll_area:
            scrollbar = scroll_area.verticalScrollBar()
            if scrollbar:
                # Usar pixelDelta si está disponible (touchpad)
                if not e.pixelDelta().isNull():
                    delta = e.pixelDelta().y()
                else:
                    # Para rueda de mouse: convertir angleDelta a píxeles
                    # angleDelta.y() típicamente es ±120 por cada "click" de rueda
                    # Queremos que sea MUY sensible: cada click = 120 píxeles (3 filas de 40px)
                    angle = e.angleDelta().y()
                    delta = angle  # 1:1 - cada unidad de angle = 1 pixel
                    # Esto hace que cada click (120 unidades) = 120 píxeles
                
                # Aplicar el scroll de forma suave
                current = scrollbar.value()
                new_value = current - delta
                
                # Asegurar que está en rango válido
                new_value = max(scrollbar.minimum(), min(scrollbar.maximum(), new_value))
                scrollbar.setValue(new_value)
                
                e.accept()
                return
        super().wheelEvent(e)


# ── PresentationRowWidget ─────────────────────────────────────────────────────

class PresentationRowWidget(QWidget):
    delete_requested    = Signal(str)
    edit_requested      = Signal(str)
    duplicate_requested = Signal(str)
    visibility_changed  = Signal()

    ROW_H    = 38
    _C_HOVER = None
    _C_SEL   = None

    def __init__(self, item: PresentationItem, index: int, col_widths: dict = None, row_height: int = 38, parent=None):
        super().__init__(parent)
        self._item           = item
        self._index          = index
        self._col_widths     = col_widths or {}
        self._row_h          = row_height
        self._drag_start_pos = None
        self._hovered        = False
        self.setFixedHeight(row_height)
        self.setMouseTracking(True)
        if PresentationRowWidget._C_HOVER is None:
            PresentationRowWidget._C_HOVER = QColor(str(BG2))
            PresentationRowWidget._C_SEL   = QColor(201, 164, 74, 30)
        self._build()

    def _is_selected(self):
        p = self.parentWidget()
        while p and not isinstance(p, DragDropListWidget):
            p = p.parentWidget()
        return p and p.is_selected(self._item.id)

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, e):
        p = QPainter(self)
        if self._is_selected():
            p.fillRect(self.rect(), self._C_SEL)
            # Gold left accent bar only — no full border
            p.fillRect(0, 0, 3, self.height(), QColor(str(ACCENT)))
        elif self._hovered:
            p.fillRect(self.rect(), self._C_HOVER)

    def enterEvent(self, e):
        self._hovered = True; self.update()

    def leaveEvent(self, e):
        self._hovered = False; self.update()

    # ── Click → select ────────────────────────────────────────────────────────

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            # No iniciar selección/drag si el click fue sobre un botón hijo
            child = self.childAt(e.position().toPoint())
            if isinstance(child, QPushButton):
                return
            self._drag_start_pos = e.position().toPoint()
            self._did_drag = False
            ctrl  = bool(e.modifiers() & Qt.KeyboardModifier.ControlModifier)
            shift = bool(e.modifiers() & Qt.KeyboardModifier.ShiftModifier)
            p = self.parentWidget()
            while p and not isinstance(p, DragDropListWidget):
                p = p.parentWidget()
            if p:
                already_sel = p.is_selected(self._item.id)
                if ctrl or shift or not already_sel:
                    p.select(self._item.id, ctrl=ctrl, shift=shift)
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if (self._drag_start_pos is not None and
                e.buttons() & Qt.MouseButton.LeftButton and
                (e.position().toPoint() - self._drag_start_pos).manhattanLength() > QApplication.startDragDistance()):
            self._did_drag = True
            # Find container and get all selected ids
            container = self.parentWidget()
            while container and not isinstance(container, DragDropListWidget):
                container = container.parentWidget()
            if container and not container.is_selected(self._item.id):
                container.select(self._item.id)
            self._start_drag()
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and not getattr(self, '_did_drag', False):
            # Click sin drag: si no hubo modificadores, seleccionar solo este item
            ctrl  = bool(e.modifiers() & Qt.KeyboardModifier.ControlModifier)
            shift = bool(e.modifiers() & Qt.KeyboardModifier.ShiftModifier)
            if not ctrl and not shift:
                p = self.parentWidget()
                while p and not isinstance(p, DragDropListWidget):
                    p = p.parentWidget()
                if p and len(p._selected_ids) > 1:
                    p.select(self._item.id)
        self._drag_start_pos = None
        self._did_drag = False
        super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e):
        self.edit_requested.emit(self._item.id)

    def contextMenuEvent(self, e):
        menu = QMenu(self)
        act_detail = menu.addAction("Abrir detalle")
        act_dup    = menu.addAction("Duplicar registro")
        act_vis    = menu.addAction("Cambiar visibilidad")
        menu.addSeparator()
        act_del    = menu.addAction("Eliminar registro")
        chosen = menu.exec(e.globalPos())
        if chosen == act_detail:
            self.edit_requested.emit(self._item.id)
        elif chosen == act_dup:
            self.duplicate_requested.emit(self._item.id)
        elif chosen == act_vis:
            self._toggle_visibility()
        elif chosen == act_del:
            self.delete_requested.emit(self._item.id)

    def _start_drag(self):
        # Find DragDropListWidget container (may be several parents up)
        container = self.parentWidget()
        while container is not None and not isinstance(container, DragDropListWidget):
            container = container.parentWidget()

        if container and not container.is_selected(self._item.id):
            container.select(self._item.id)

        sel_rows = container._rows() if container else [self]
        sel_rows = [r for r in sel_rows if (container and container.is_selected(r._item.id))]
        if not sel_rows:
            sel_rows = [self]

        # MIME: encode item ids + source pres idx for cross-slot drop
        sel_ids = ",".join(r._item.id for r in sel_rows)
        from_idx = state.active_pres_idx
        mime_text = f"pyscout/drag:{sel_ids}:{from_idx}"

        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(mime_text)
        drag.setMimeData(mime)

        # Composite ghost pixmap
        rh = self._row_h
        ghost_h = rh * min(len(sel_rows), 4)
        pm = QPixmap(max(self.width(), 200), ghost_h)
        pm.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pm)
        painter.setOpacity(0.82)
        for i, row in enumerate(sel_rows[:4]):
            row_pm = QPixmap(row.size())
            row_pm.fill(QColor(0, 0, 0, 0))
            row.render(row_pm)
            painter.drawPixmap(0, i * rh, row_pm)
        if len(sel_rows) > 4:
            painter.setPen(QColor(str(ACCENT)))
            painter.drawText(8, ghost_h - 4, f"+{len(sel_rows) - 4} más")
        painter.end()

        drag.setPixmap(pm)
        drag.setHotSpot(self._drag_start_pos or QPoint(pm.width() // 2, rh // 2))
        
        # Ejecutar drag y restaurar cursor al terminar
        from PySide6.QtGui import QCursor
        drag.exec(Qt.DropAction.MoveAction)
        QApplication.restoreOverrideCursor()
        self.unsetCursor()
        if container:
            container.unsetCursor()

    # ── Build columns ─────────────────────────────────────────────────────────

    @staticmethod
    def _text_color_for(hex_color: str) -> str:
        try:
            h = hex_color.lstrip("#")
            r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
            return "#ffffff" if (0.299*r + 0.587*g + 0.114*b) < 128 else "#1a1714"
        except Exception:
            return "#ffffff"

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        w = self._col_widths

        # Guardar referencias para poder actualizar anchos después
        self._col_widgets = {}

        # #
        num = QLabel(f"{self._index + 1}")
        num.setFixedWidth(w.get("num", 24))
        num.setAlignment(Qt.AlignmentFlag.AlignCenter)
        num.setStyleSheet(f"color:{TEXT3}; font-size:{fs(11)}px; background:transparent; border:none;")
        layout.addWidget(num)
        layout.addSpacing(1)
        self._col_widgets["num"] = num

        # NOMBRE
        raw_color = self._item.color or ""
        _lc = raw_color.strip().lower()
        # Solo pintar fondo si el usuario eligió un color explícitamente desde el dialog
        _neutral = {"", "#1c1c1c", "#2a2a2a", "#2a2a30", "#e8821a", "#555555", "transparent"}
        has_accent = _lc != "" and _lc not in _neutral
        name_bg = raw_color if has_accent else "transparent"
        name_fg = self._text_color_for(raw_color) if has_accent else str(TEXT0)
        name_wrap = QWidget()
        name_wrap.setFixedWidth(w.get("name", 200))
        name_wrap.setFixedHeight(self._row_h)
        bg_style = f"background:{name_bg};" if has_accent else "background:transparent;"
        name_wrap.setStyleSheet(f"{bg_style} border:none;")
        nwl = QHBoxLayout(name_wrap)
        nwl.setContentsMargins(10, 0, 6, 0)
        nwl.setSpacing(0)
        name_lbl = QLabel(self._item.name)
        name_lbl.setStyleSheet(f"color:{name_fg}; font-size:{fs(13)}px; font-weight:500; background:transparent; border:none;")
        nwl.addWidget(name_lbl)
        layout.addWidget(name_wrap)
        layout.addSpacing(4)
        self._col_widgets["name"] = name_wrap

        # TIPO
        tipo_lbl = QLabel("Clip" if self._item.type == "clip" else "Img")
        tipo_lbl.setFixedWidth(w.get("tipo", 56))
        tipo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tipo_lbl.setStyleSheet(f"color:{TEXT3}; font-size:{fs(11)}px; background:transparent; border:none;")
        layout.addWidget(tipo_lbl)
        layout.addSpacing(1)
        self._col_widgets["tipo"] = tipo_lbl

        # TIEMPO
        meta_lbl = QLabel(self._item.timestamp or "—")
        meta_lbl.setFixedWidth(w.get("time", 80))
        meta_lbl.setStyleSheet(f"color:{TEXT2}; font-size:{fs(11)}px; background:transparent; border:none;")
        layout.addWidget(meta_lbl)
        layout.addSpacing(1)
        self._col_widgets["time"] = meta_lbl

        # FUENTE (carpeta/archivo)
        source_path = self._item.video_path or self._item.image_path or ""
        if source_path:
            import os as _os
            fname = _os.path.basename(source_path)
            parent = _os.path.basename(_os.path.dirname(source_path))
            source_text = f"{parent}/{fname}" if parent else fname
        else:
            source_text = "—"
        source_lbl = QLabel(source_text)
        source_lbl.setFixedWidth(w.get("source", 140))
        source_lbl.setStyleSheet(f"color:{TEXT3}; font-size:{fs(10)}px; background:transparent; border:none;")
        source_lbl.setToolTip(source_path)
        layout.addWidget(source_lbl)
        layout.addSpacing(1)
        self._col_widgets["source"] = source_lbl

        # NOTA — stretch
        note_lbl = QLabel((self._item.note or "")[:40])
        note_lbl.setStyleSheet(f"color:{TEXT1}; font-size:{fs(12)}px; background:transparent; border:none;")
        layout.addWidget(note_lbl, stretch=1)
        layout.addSpacing(1)

        # DURACIÓN
        dur_w = w.get("dur", 80)
        if self._item.type == "image":
            dur_wrap = QWidget()
            dur_wrap.setFixedWidth(dur_w)
            dh = QHBoxLayout(dur_wrap)
            dh.setContentsMargins(0,0,0,0)
            dh.setSpacing(2)
            spin = QSpinBox()
            spin.setRange(1, 30)
            spin.setValue(int(self._item.image_dur))
            spin.setFixedSize(42, 24)
            spin.setStyleSheet(f"""
                QSpinBox {{ background:{BG3}; color:{TEXT0}; border:none;
                    border-bottom:1px solid {BORDER2}; font-size:{fs(11)}px; padding:0 4px; }}
                QSpinBox:focus {{ border-bottom:1px solid {ACCENT}; }}
            """)
            spin.valueChanged.connect(lambda v, iid=self._item.id: state.update_pres_item(iid, image_dur=float(v)))
            dh.addWidget(spin)
            dh.addWidget(QLabel("s", styleSheet=f"color:{TEXT3}; font-size:{fs(10)}px; background:transparent; border:none;"))
            layout.addWidget(dur_wrap)
            self._col_widgets["dur"] = dur_wrap
        else:
            dur_lbl = QLabel(f"{self._item.duration:.1f}s")
            dur_lbl.setFixedWidth(dur_w)
            dur_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            dur_lbl.setStyleSheet(f"color:{ACCENT}; font-size:{fs(12)}px; font-weight:600; background:transparent; border:none;")
            layout.addWidget(dur_lbl)
            self._col_widgets["dur"] = dur_lbl

        # VISIBLE toggle
        vis_w = w.get("vis", 32)
        self._vis_state = self._item.visible
        self._vis_btn = QPushButton()
        self._vis_btn.setIcon(eye_icon(size=(16, 16), color=TEXT2) if self._vis_state else eye_off_icon(size=(16, 16), color=DANGER))
        self._vis_btn.setIconSize(QSize(16, 16))
        self._vis_btn.setFixedSize(vis_w, vis_w)
        self._vis_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; border:none; padding:0;"
            f" min-height:0; min-width:0; }}"
            f"QPushButton:hover {{ background:rgba(255,255,255,0.06); border-radius:4px; }}"
        )
        self._vis_btn.clicked.connect(self._toggle_visibility)
        layout.addWidget(self._vis_btn)

        # Apply initial opacity for hidden items
        if not self._vis_state:
            effect = QGraphicsOpacityEffect(self)
            effect.setOpacity(0.35)
            self.setGraphicsEffect(effect)

        # DELETE with confirm
        del_w = w.get("del", 28)
        del_btn = QPushButton("✕")
        del_btn.setFixedSize(del_w, del_w)
        del_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; color:{TEXT3}; border:none;"
            f" font-size:{fs(12)}px; min-height:0; min-width:0; padding:0; }}"
            f"QPushButton:hover {{ color:{DANGER}; }}"
        )
        del_btn.clicked.connect(self._confirm_delete)
        layout.addWidget(del_btn)

    def _confirm_delete(self):
        from PySide6.QtWidgets import QMessageBox
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Eliminar clip")
        dlg.setText(f"¿Eliminás '{self._item.name}' de la presentación?")
        ok  = dlg.addButton("Eliminar", QMessageBox.ButtonRole.DestructiveRole)
        can = dlg.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        dlg.exec()
        if dlg.clickedButton() == ok:
            self.delete_requested.emit(self._item.id)

    def _get_container(self):
        """Find parent DragDropListWidget."""
        p = self.parentWidget()
        while p and not isinstance(p, DragDropListWidget):
            p = p.parentWidget()
        return p

    def _toggle_visibility(self):
        """Toggle visibility. If this item is selected, toggle ALL selected items."""
        container = self._get_container()
        if container and container.is_selected(self._item.id) and len(container._selected_ids) > 1:
            # Batch toggle: use the OPPOSITE of current item's state for all
            new_state = not self._item.visible
            for row in container._rows():
                if container.is_selected(row._item.id):
                    row._item.visible = new_state
                    row._vis_state = new_state
                    row._vis_btn.setIcon(eye_icon(size=(16, 16), color=TEXT2) if new_state else eye_off_icon(size=(16, 16), color=DANGER))
                    effect = QGraphicsOpacityEffect(row)
                    effect.setOpacity(1.0 if new_state else 0.35)
                    row.setGraphicsEffect(effect)
        else:
            # Single toggle
            self._vis_state = not self._vis_state
            self._item.visible = self._vis_state
            self._vis_btn.setIcon(eye_icon(size=(16, 16), color=TEXT2) if self._vis_state else eye_off_icon(size=(16, 16), color=DANGER))
            effect = QGraphicsOpacityEffect(self)
            effect.setOpacity(1.0 if self._vis_state else 0.35)
            self.setGraphicsEffect(effect)
        self.visibility_changed.emit()
        state.presentation_changed.emit()

    def _apply_visibility_ui(self):
        pass  # handled in _toggle_visibility
    
    def update_column_widths(self, new_widths: dict):
        """Actualizar anchos de columnas sin recrear la fila - estilo Excel."""
        # Actualizar el diccionario interno
        self._col_widths = new_widths
        
        # Actualizar cada widget con su nuevo ancho
        if hasattr(self, '_col_widgets'):
            for key, widget in self._col_widgets.items():
                if widget and key in new_widths:
                    try:
                        widget.setFixedWidth(new_widths[key])
                    except RuntimeError:
                        # Widget ya fue destruido
                        pass



class TableHeader(QWidget):
    """Header de tabla con columnas resizables."""
    columns_resized = Signal()

    EDGE_PX = 6

    # Columnas en orden con sus keys
    COLS = ["num", "name", "tipo", "time", "source", "nota", "dur", "vis"]

    def __init__(self, col_widths: dict, parent=None):
        super().__init__(parent)
        self._widths = col_widths
        self._dragging = None
        self._drag_x0 = 0
        self._drag_w0 = 0
        self._labels: dict[str, QLabel] = {}
        self.setFixedHeight(32)
        self.setMouseTracking(True)
        self.setStyleSheet(f"""
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 {BG2}, stop:1 {BG1});
            border-bottom: 1px solid {ACCENT};
        """)
        self._build()

    def _lbl(self, text, width=None, align=Qt.AlignmentFlag.AlignLeft):
        l = QLabel(text)
        if width:
            l.setFixedWidth(width)
        l.setAlignment(align | Qt.AlignmentFlag.AlignVCenter)
        l.setStyleSheet(f"color:{ACCENT}; font-size:{fs(9)}px; font-weight:700;"
                        f" letter-spacing:1.5px; background:transparent; border:none;")
        return l

    def _sep(self):
        s = QFrame()
        s.setFixedWidth(1)
        s.setStyleSheet(f"background:rgba(255,255,255,0.08); border:none;")
        return s

    def _build(self):
        if self.layout():
            while self.layout().count():
                item = self.layout().takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            lo = self.layout()
        else:
            lo = QHBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(0)
        self._labels.clear()

        w = self._widths
        col_defs = [
            ("num",    "#",        w["num"],                Qt.AlignmentFlag.AlignCenter, False),
            ("name",   "NOMBRE",   w["name"],               Qt.AlignmentFlag.AlignLeft,   False),
            ("tipo",   "TIPO",     w.get("tipo", 56),       Qt.AlignmentFlag.AlignCenter, False),
            ("time",   "TIEMPO",   w.get("time", 80),       Qt.AlignmentFlag.AlignLeft,   False),
            ("source", "FUENTE",   w.get("source", 140),    Qt.AlignmentFlag.AlignLeft,   False),
            ("nota",   "NOTA",     None,                    Qt.AlignmentFlag.AlignLeft,   True),
            ("dur",    "DURACIÓN", w.get("dur", 100),       Qt.AlignmentFlag.AlignRight,  False),
            ("vis",    "",         w.get("vis", 40),        Qt.AlignmentFlag.AlignCenter, False),
        ]

        for i, (key, text, width, align, stretch) in enumerate(col_defs):
            if i > 0:
                lo.addWidget(self._sep())
            lbl = self._lbl(text, width, align)
            self._labels[key] = lbl
            if stretch:
                lo.addWidget(lbl, stretch=1)
            else:
                lo.addWidget(lbl)

        lo.addSpacing(w.get("del", 28))

    def rebuild(self):
        self._build()

    # ── Resize: solo actualizar anchos de labels, sin reconstruir ──────────

    def _col_x_ranges(self):
        """Calcular posición x acumulada de cada columna."""
        x = 0
        result = []
        for key in self.COLS:
            if key == "nota":
                continue  # nota es stretch, no tiene ancho fijo
            w = self._widths.get(key, 0)
            if w > 0:
                x += w + 1  # +1 por separador
                result.append((key, x))
        return result

    def _edge_at(self, mx):
        for key, right_x in self._col_x_ranges():
            if abs(mx - right_x) <= self.EDGE_PX:
                return key
        return None

    def mousePressEvent(self, e):
        key = self._edge_at(e.position().x())
        if key and e.button() == Qt.MouseButton.LeftButton:
            self._dragging = key
            self._drag_x0 = e.position().x()
            self._drag_w0 = self._widths.get(key, 80)
            self.grabMouse()

    def mouseMoveEvent(self, e):
        mx = e.position().x()
        if self._dragging:
            delta = mx - self._drag_x0
            new_w = max(40, int(self._drag_w0 + delta))
            if new_w != self._widths.get(self._dragging):
                self._widths[self._dragging] = new_w
                # Actualizar solo el label afectado
                if self._dragging in self._labels:
                    self._labels[self._dragging].setFixedWidth(new_w)
                self.columns_resized.emit()
        else:
            self.setCursor(Qt.CursorShape.SplitHCursor if self._edge_at(mx)
                           else Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, e):
        if self._dragging:
            self._dragging = None
            self.releaseMouse()
            mx = e.position().x()
            self.setCursor(Qt.CursorShape.SplitHCursor if self._edge_at(mx)
                           else Qt.CursorShape.ArrowCursor)

    def leaveEvent(self, e):
        if not self._dragging:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().leaveEvent(e)


# ── MultiPresBox ──────────────────────────────────────────────────────────────

class PresSlotWidget(QWidget):
    """Slot compacta de presentación."""
    clicked    = Signal(int)
    del_req    = Signal(int)
    rename_req = Signal(int)

    def __init__(self, idx: int, items: list, active: bool, name: str, parent=None):
        super().__init__(parent)
        self._idx    = idx
        self._active = active
        self.setAcceptDrops(True)
        self.setFixedHeight(34)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build(items, name)

    def _build(self, items, name):
        if self.layout():
            while self.layout().count():
                i = self.layout().takeAt(0)
                if i.widget(): i.widget().deleteLater()
            lo = self.layout()
        else:
            lo = QHBoxLayout(self)
        lo.setContentsMargins(8, 0, 4, 0)
        lo.setSpacing(4)

        dot = QWidget()
        dot.setFixedSize(5, 5)
        dot.setStyleSheet(f"background:{'#C9A44A' if self._active else 'transparent'}; border-radius:2px;")
        lo.addWidget(dot)

        display_name = name if name else f"Listado {self._idx + 1}"
        lbl = QLabel(display_name)
        lbl.setStyleSheet(
            f"color:{'#e8e4de' if self._active else '#7A7570'};"
            f" font-size:{fs(11)}px; font-weight:{'600' if self._active else '400'};"
            f" background:transparent; border:none;"
        )
        lo.addWidget(lbl, stretch=1)

        del_btn = QPushButton("✕")
        del_btn.setFixedSize(18, 18)
        del_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; color:#3E3C3A; border:none;"
            f" font-size:{fs(11)}px; padding:0; min-height:0; min-width:0; }}"
            f"QPushButton:hover {{ color:#c0392b; }}"
        )
        del_btn.clicked.connect(lambda: self.del_req.emit(self._idx))
        lo.addWidget(del_btn)

        bg = "rgba(255,255,255,0.04)" if self._active else "transparent"
        self.setObjectName("pres_slot")
        self.setStyleSheet(f"QWidget#pres_slot {{ background:{bg}; border:none; }}")

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(e.position().toPoint())
            if isinstance(child, QPushButton):
                return
            self.clicked.emit(self._idx)

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(e.position().toPoint())
            if not isinstance(child, QPushButton):
                self.rename_req.emit(self._idx)

    def dragEnterEvent(self, e):
        txt = e.mimeData().text() if e.mimeData().hasText() else ""
        if txt.startswith("pyscout/drag:"):
            self.setStyleSheet("QWidget#pres_slot { background:rgba(201,164,74,0.15); border:none; }")
            e.acceptProposedAction()

    def dragLeaveEvent(self, e):
        bg = "rgba(255,255,255,0.04)" if self._active else "transparent"
        self.setStyleSheet(f"QWidget#pres_slot {{ background:{bg}; border:none; }}")

    def dropEvent(self, e):
        bg = "rgba(255,255,255,0.04)" if self._active else "transparent"
        self.setStyleSheet(f"QWidget#pres_slot {{ background:{bg}; border:none; }}")
        txt = e.mimeData().text() if e.mimeData().hasText() else ""
        if not txt.startswith("pyscout/drag:"):
            return
        parts = txt.split(":")
        sel_ids = parts[1].split(",") if len(parts) > 1 else []
        from_idx = int(parts[2]) if len(parts) > 2 else state.active_pres_idx
        if self._idx == from_idx:
            e.ignore(); return
        # Copiar items al slot destino (no remover del origen)
        state.copy_items_to_slot(sel_ids, from_idx, self._idx)
        e.acceptProposedAction()


class MultiPresBox(QWidget):
    """Box con hasta 5 listados."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()
        state.presentations_changed.connect(self._rebuild)
        state.presentation_changed.connect(self._rebuild)
        state.project_changed.connect(self._rebuild)

    def _build(self):
        lo = QVBoxLayout(self)
        lo.setContentsMargins(0, 4, 0, 4)
        lo.setSpacing(0)

        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 4)
        lbl = QLabel("LISTADOS")
        lbl.setStyleSheet(f"color:{ACCENT}; font-size:{fs(9)}px; font-weight:700; letter-spacing:1.8px;")
        hdr.addWidget(lbl)
        hdr.addStretch()

        add_btn = QPushButton("+")
        add_btn.setFixedSize(22, 22)
        add_btn.setToolTip("Agregar listado a esta presentación")
        add_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; color:{ACCENT}; border:none;"
            f" font-size:{fs(14)}px; font-weight:700; padding:0; min-height:0; min-width:0; }}"
            f"QPushButton:hover {{ color:#ffffff; }}"
        )
        add_btn.clicked.connect(self._add_slot)
        hdr.addWidget(add_btn)

        # ELIMINADO: botón de "Abrir" (📂)
        # La lógica ahora es: cada presentación tiene sus propios listados
        # No se abren presentaciones externas
        
        lo.addLayout(hdr)

        self._slots_container = QWidget()
        self._slots_lo = QVBoxLayout(self._slots_container)
        self._slots_lo.setContentsMargins(0, 0, 0, 0)
        self._slots_lo.setSpacing(1)
        lo.addWidget(self._slots_container)

    def _get_slot_name(self, idx: int) -> str:
        names = state.presentation_names
        return names[idx] if idx < len(names) else ""

    def _rebuild(self):
        while self._slots_lo.count():
            item = self._slots_lo.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, items in enumerate(state.presentations):
            active = (i == state.active_pres_idx)
            name = self._get_slot_name(i)
            slot = PresSlotWidget(i, items, active, name)
            slot.clicked.connect(self._on_slot_clicked)
            slot.del_req.connect(self._on_del_slot)
            slot.rename_req.connect(self._on_rename_slot)
            self._slots_lo.addWidget(slot)

    def _add_slot(self):
        state.add_presentation_slot()

    def _on_slot_clicked(self, idx: int):
        state.set_active_presentation(idx)

    def _on_rename_slot(self, idx: int):
        from PySide6.QtWidgets import QDialog, QLineEdit, QPushButton, QVBoxLayout, QLabel
        current = self._get_slot_name(idx) or f"Listado {idx + 1}"
        dlg = QDialog(self)
        dlg.setWindowTitle("Renombrar listado")
        dlg.setFixedWidth(300)
        from utils.theme_helpers import BG1, BG2, ACCENT, ACCENT2, ACCENT3, TEXT0, TEXT3, BORDER2
        from styles.theme import fs
        dlg.setStyleSheet(f"background:{BG1}; color:{TEXT0};")
        vl = QVBoxLayout(dlg)
        vl.setContentsMargins(20, 20, 20, 20)
        vl.setSpacing(12)
        lbl = QLabel("Nombre del listado")
        lbl.setStyleSheet(f"color:{TEXT3}; font-size:{fs(10)}px; font-weight:600; letter-spacing:1px;")
        vl.addWidget(lbl)
        inp = QLineEdit(current)
        inp.setMaxLength(32)
        inp.selectAll()
        vl.addWidget(inp)
        btns_lo = QHBoxLayout()
        btns_lo.addStretch()
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(dlg.reject)
        btns_lo.addWidget(cancel_btn)
        ok_btn = QPushButton("Renombrar")
        ok_btn.setStyleSheet(
            f"QPushButton {{ background:qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            f"stop:0 {ACCENT3},stop:1 {ACCENT}); color:#1a1714; border:none;"
            f" border-bottom:2px solid {ACCENT2}; border-radius:2px;"
            f" padding:5px 16px; font-weight:600; }}"
            f"QPushButton:hover {{ background:{ACCENT3}; }}"
        )
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(dlg.accept)
        inp.returnPressed.connect(dlg.accept)
        btns_lo.addWidget(ok_btn)
        vl.addLayout(btns_lo)
        if dlg.exec() and inp.text().strip():
            state.rename_presentation_slot(idx, inp.text().strip())

    def _on_del_slot(self, idx: int):
        from PySide6.QtWidgets import QMessageBox
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Eliminar listado")
        name = self._get_slot_name(idx) or f"Listado {idx+1}"
        dlg.setText(f"¿Eliminás '{name}' y sus {len(state.presentations[idx])} clips?")
        ok  = dlg.addButton("Eliminar", QMessageBox.ButtonRole.DestructiveRole)
        can = dlg.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        dlg.exec()
        if dlg.clickedButton() == ok:
            state.remove_presentation_slot(idx)

    def showEvent(self, e):
        super().showEvent(e)
        self._rebuild()



# ── Pantalla principal ────────────────────────────────────────────────────────

class PresentationScreen(QWidget):
    navigate_to_adjust = Signal(str)  # clip category to select in adjust

    def __init__(self, parent=None):
        super().__init__(parent)
        self._render_thread = None
        self._col_widths = {
            "num": 28, "name": 180, "tipo": 44,
            "time": 72, "source": 130, "dur": 100, "vis": 40, "del": 28,
        }
        self._build_ui()
        self._connect_state()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Lista principal ───────────────────────────────────────────────────
        main = QWidget()

        ml = QVBoxLayout(main)
        ml.setContentsMargins(0, 0, 0, 0)
        ml.setSpacing(0)

        # Header de tabla — resizable
        self._table_hdr = TableHeader(self._col_widths)
        self._table_hdr.columns_resized.connect(self._on_columns_resized)
        ml.addWidget(self._table_hdr)

        # Scroll de filas
        self._list_scroll = QScrollArea()
        self._list_scroll.setWidgetResizable(True)
        self._list_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._list_scroll.setStyleSheet("background:transparent;")
        self._list_scroll.setAcceptDrops(True)
        
        # Configurar scroll suave y más sensible
        self._list_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._list_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Configurar scrollbar para single step más grande (más sensible)
        from PySide6.QtCore import QTimer
        def configure_scrollbar():
            vbar = self._list_scroll.verticalScrollBar()
            if vbar:
                vbar.setSingleStep(40)  # Cada step = 40 píxeles (más sensible)
                vbar.setPageStep(200)   # Page up/down = 200 píxeles
        QTimer.singleShot(100, configure_scrollbar)

        self._list_widget = DragDropListWidget()
        self._list_layout = self._list_widget.layout()

        self._empty_lbl = QLabel("\n\nEl listado está vacío\nAgregá clips desde Ajuste")
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_lbl.setStyleSheet(f"color:{TEXT3}; font-size:{fs(13)}px;")
        self._list_layout.insertWidget(0, self._empty_lbl)

        self._list_scroll.setWidget(self._list_widget)
        ml.addWidget(self._list_scroll, stretch=1)

        # Footer stats + zoom
        footer = QWidget()
        footer.setFixedHeight(28)
        footer.setStyleSheet(f"""
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 {BG1}, stop:1 {BG0});
            border-top: 1px solid rgba(255,255,255,0.05);
        """)
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(12, 0, 12, 0)
        fl.setSpacing(6)
        self._footer_lbl = QLabel("0 clips  ·  0 imágenes  ·  0:00")
        self._footer_lbl.setStyleSheet(f"color:{TEXT3}; font-size:{fs(10)}px; letter-spacing:0.5px;")
        fl.addWidget(self._footer_lbl)
        fl.addStretch()

        self._row_height = 38  # default

        zoom_out_btn = QPushButton("🔍−")
        zoom_out_btn.setFixedSize(32, 26)
        zoom_out_btn.setToolTip("Filas más chicas")
        zoom_out_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; color:{TEXT2}; border:1px solid {BORDER2};"
            f" font-size:{fs(12)}px; padding:0; min-height:0; min-width:0; border-radius:3px; }}"
            f"QPushButton:hover {{ color:{ACCENT}; border-color:{ACCENT}; background:{BG3}; }}"
        )
        zoom_out_btn.clicked.connect(lambda: self._set_row_height(-4))
        fl.addWidget(zoom_out_btn)

        zoom_in_btn = QPushButton("🔍+")
        zoom_in_btn.setFixedSize(32, 26)
        zoom_in_btn.setToolTip("Filas más grandes")
        zoom_in_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; color:{TEXT2}; border:1px solid {BORDER2};"
            f" font-size:{fs(12)}px; padding:0; min-height:0; min-width:0; border-radius:3px; }}"
            f"QPushButton:hover {{ color:{ACCENT}; border-color:{ACCENT}; background:{BG3}; }}"
        )
        zoom_in_btn.clicked.connect(lambda: self._set_row_height(4))
        fl.addWidget(zoom_in_btn)

        ml.addWidget(footer)

        layout.addWidget(main, stretch=1)

        # ── Sidebar ───────────────────────────────────────────────────────────
        sidebar = QWidget()
        sidebar.setFixedWidth(240)
        sidebar.setObjectName("sidebar_left")
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(14, 16, 14, 16)
        sl.setSpacing(12)

        # Botón producir — grande y prominente
        self._render_btn = QPushButton("Crear película")
        self._render_btn.setMinimumHeight(52)
        self._render_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {ACCENT3}, stop:1 {ACCENT});
                color: #1a1714;
                border: none;
                border-bottom: 3px solid {ACCENT2};
                border-radius: 0;
                font-size: {fs(14)}px;
                font-weight: 700;
                letter-spacing: 0.3px;
            }}
            QPushButton:hover {{ background: {ACCENT3}; }}
            QPushButton:pressed {{ border-bottom:none; padding-top:3px; }}
            QPushButton:disabled {{ background:{BG3}; color:{TEXT3}; border:none; }}
        """)
        self._render_btn.clicked.connect(self._start_render)
        sl.addWidget(self._render_btn)

        # Agregar imagen
        add_img_btn = QPushButton("+ Agregar imagen")
        add_img_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {TEXT2};
                border: none;
                border-bottom: 1px solid {BORDER2};
                font-size: {fs(12)}px;
                padding: 5px 0;
            }}
            QPushButton:hover {{ color:{TEXT0}; border-bottom:1px solid {ACCENT}; }}
        """)
        add_img_btn.clicked.connect(self._add_image)
        sl.addWidget(add_img_btn)

        sep = QFrame(); sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:rgba(255,255,255,0.06);")
        sl.addWidget(sep)

        def section_lbl(text):
            l = QLabel(text)
            l.setStyleSheet(f"color:{ACCENT}; font-size:{fs(9)}px; font-weight:700; letter-spacing:1.8px;")
            return l

        # Stats
        sl.addWidget(section_lbl("RESUMEN"))
        stats = QWidget(); stats.setStyleSheet("background:transparent;")
        sg = QHBoxLayout(stats); sg.setSpacing(4); sg.setContentsMargins(0,0,0,0)
        self._stat_clips = self._stat_card("Clips", "0")
        self._stat_dur   = self._stat_card("Total", "0s")
        self._stat_imgs  = self._stat_card("Imgs", "0")
        sg.addWidget(self._stat_clips[0])
        sg.addWidget(self._stat_dur[0])
        sg.addWidget(self._stat_imgs[0])
        sl.addWidget(stats)

        sep_pres = QFrame(); sep_pres.setFixedHeight(1)
        sep_pres.setStyleSheet(f"background:rgba(255,255,255,0.06);")
        sl.addWidget(sep_pres)

        # Multi-presentation box
        self._multi_pres = MultiPresBox()
        sl.addWidget(self._multi_pres)

        sep2 = QFrame(); sep2.setFixedHeight(1)
        sep2.setStyleSheet(f"background:rgba(255,255,255,0.06);")
        sl.addWidget(sep2)

        sl.addStretch()
        layout.addWidget(sidebar)

    def _stat_card(self, label, value):
        card = QWidget()
        card.setStyleSheet(f"""
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 {BG3}, stop:1 {BG2});
            border-bottom: 1px solid {BORDER2};
        """)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(8, 6, 8, 6)
        cl.setSpacing(1)
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color:{TEXT3}; font-size:{fs(9)}px; background:transparent; border:none;")
        val = QLabel(value)
        val.setStyleSheet(f"color:{TEXT0}; font-size:{fs(18)}px; font-weight:700; background:transparent; border:none;")
        cl.addWidget(lbl); cl.addWidget(val)
        return card, val

    def keyPressEvent(self, e):
        # Key 3 = add selected clip from adjust to presentation
        # This is handled in adjust.py directly via state.add_clip_to_presentation
        super().keyPressEvent(e)

    def _connect_state(self):
        state.presentation_changed.connect(self._refresh)
        state.overlay_changed.connect(lambda _: self._overlay_cb.setChecked(state.overlay_enabled))
        self._refresh()

    def _on_columns_resized(self):
        """Actualizar anchos de columnas en las filas existentes - SIN recrearlas."""
        # Obtener todas las filas existentes
        rows = []
        for i in range(self._list_layout.count()):
            widget = self._list_layout.itemAt(i).widget()
            if isinstance(widget, PresentationRowWidget):
                rows.append(widget)
        
        # Actualizar cada fila con los nuevos anchos
        for row in rows:
            row.update_column_widths(self._col_widths)

    def _refresh_stats(self):
        items = state.presentation
        visible_items = [p for p in items if p.visible]

        clips = sum(1 for p in visible_items if p.type == "clip")
        imgs  = sum(1 for p in visible_items if p.type == "image")
        total = sum(p.duration for p in visible_items)

        m = int(total // 60)
        s = int(total % 60)

        self._footer_lbl.setText(f"{clips} clips  ·  {imgs} imágenes  ·  {m}:{s:02d}")
        try:
            self._stat_clips[1].setText(str(clips))
            self._stat_dur[1].setText(fmt_dur(total))
            self._stat_imgs[1].setText(str(imgs))
        except RuntimeError:
            pass

    def _refresh(self):
        self._list_layout.removeWidget(self._empty_lbl)
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        col_widths = self._col_widths
        rh = self._row_height
        items = state.presentation
        if not items:
            self._list_layout.insertWidget(0, self._empty_lbl)
            self._empty_lbl.show()
        else:
            self._empty_lbl.hide()
            insert_pos = 0
            for i, item in enumerate(items):
                w = PresentationRowWidget(item, i, col_widths=col_widths, row_height=rh)
                w.delete_requested.connect(lambda iid: state.remove_pres_item(iid))
                w.edit_requested.connect(self._edit_item)
                w.duplicate_requested.connect(self._duplicate_item)
                w.visibility_changed.connect(self._refresh_stats)
                self._list_layout.insertWidget(insert_pos, w)
                insert_pos += 1
                if i < len(items) - 1:
                    sep = QFrame()
                    sep.setFixedHeight(1)
                    sep.setStyleSheet("background: rgba(255,255,255,0.10);")
                    sep.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
                    self._list_layout.insertWidget(insert_pos, sep)
                    insert_pos += 1

        self._refresh_stats()

    def _set_row_height(self, delta):
        self._row_height = max(24, min(56, self._row_height + delta))
        self._refresh()

    def _add_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar imagen",
            filter="Imagen (*.jpg *.jpeg *.png *.webp *.bmp)")
        if path:
            state.add_image_to_presentation(path)

    def _edit_item(self, item_id: str):
        items = state.presentation
        idx = next((i for i, p in enumerate(items) if p.id == item_id), -1)
        if idx < 0:
            return
        while True:
            item = items[idx]
            dlg = ClipDetailDialog(item, items, self)
            dlg.exec()
            if dlg._goto_adjust_flag and item.type == "clip":
                cat = item.category or item.name
                self.navigate_to_adjust.emit(cat)
                return
            if dlg._nav_delta != 0:
                new_idx = idx + dlg._nav_delta
                if 0 <= new_idx < len(items):
                    idx = new_idx
                    continue
            return

    def _duplicate_item(self, item_id: str):
        state.duplicate_pres_item(item_id)

    def _start_render(self):
        if not state.presentation:
            state.toast_requested.emit("Agregá clips primero"); return
        settings_dlg = RenderSettingsDialog(self)
        if settings_dlg.exec() != QDialog.DialogCode.Accepted: return

        # Filter out hidden items
        visible_items = [p for p in state.presentation if p.visible]
        if not visible_items:
            state.toast_requested.emit("Todos los items están ocultos"); return

        if settings_dlg.separate_files:
            self._render_separate(visible_items, settings_dlg)
        else:
            self._render_single(visible_items, settings_dlg)

    def _render_single(self, visible_items, settings_dlg):
        """Render normal: un solo MP4 concatenado."""
        path, _ = QFileDialog.getSaveFileName(self, "Exportar presentación",
            "presentacion.mp4", filter="Video MP4 (*.mp4)")
        if not path: return
        items = [{"type": p.type, "name": p.name,
                  "video_path": p.video_path, "image_path": p.image_path,
                  "clip_start": p.clip_start, "clip_dur": p.clip_dur,
                  "image_dur": p.image_dur}
                 for p in visible_items]
        total_dur = sum(p.duration for p in visible_items)
        self._render_btn.setEnabled(False)
        self._render_btn.setText("Procesando...")
        self._progress_dlg = RenderProgressDialog(total_dur, self)
        self._progress_dlg.set_output_path(path)  # Guardar path del video
        self._render_thread = RenderThread(items, path, settings_dlg.show_overlay,
            mute_audio=settings_dlg.mute_audio, crf=settings_dlg.crf, fps=settings_dlg.fps,
            transition=settings_dlg.transition, total_dur=total_dur)
        self._render_thread.progress.connect(self._progress_dlg.update_progress)
        self._render_thread.finished.connect(self._on_render_done)
        self._progress_dlg.cancel_requested.connect(self._cancel_render)
        self._render_thread.start()
        self._progress_dlg.exec()

    def _render_separate(self, visible_items, settings_dlg):
        """Render separado: un MP4 por cada registro."""
        import os
        folder = QFileDialog.getExistingDirectory(self, "Carpeta para archivos separados")
        if not folder: return
        self._render_btn.setEnabled(False)
        self._render_btn.setText("Procesando...")
        total_dur = sum(p.duration for p in visible_items)
        self._progress_dlg = RenderProgressDialog(total_dur, self)
        self._sep_items = visible_items
        self._sep_folder = folder
        self._sep_idx = 0
        self._sep_settings = settings_dlg
        self._sep_ok = 0
        self._sep_fail = 0
        self._progress_dlg.cancel_requested.connect(self._cancel_render)
        self._progress_dlg.show()
        self._render_next_separate()

    def _render_next_separate(self):
        import os
        if self._sep_idx >= len(self._sep_items):
            # Terminado
            self._progress_dlg.mark_done()
            from PySide6.QtCore import QTimer
            QTimer.singleShot(600, self._progress_dlg.accept)
            self._render_btn.setEnabled(True)
            self._render_btn.setText("Crear película")
            state.toast_requested.emit(
                f"{self._sep_ok} archivos exportados"
                + (f", {self._sep_fail} con error" if self._sep_fail else ""))
            return

        p = self._sep_items[self._sep_idx]
        # Nombre seguro para archivo
        safe_name = p.name.replace("/", "_").replace("\\", "_").replace(":", "_")
        safe_name = safe_name.replace('"', '').replace("'", "").replace("?", "").replace("*", "")
        filename = f"{self._sep_idx + 1:02d}_{safe_name}.mp4"
        out_path = os.path.join(self._sep_folder, filename)

        item_dict = {"type": p.type, "name": p.name,
                     "video_path": p.video_path, "image_path": p.image_path,
                     "clip_start": p.clip_start, "clip_dur": p.clip_dur,
                     "image_dur": p.image_dur}

        self._render_thread = RenderThread(
            [item_dict], out_path, state.overlay_enabled,
            mute_audio=self._sep_settings.mute_audio,
            crf=self._sep_settings.crf,
            transition="cut", total_dur=p.duration)
        self._render_thread.progress.connect(self._progress_dlg.update_progress)
        self._render_thread.finished.connect(self._on_separate_done)
        self._render_thread.start()

    def _on_separate_done(self, success, msg):
        if success:
            self._sep_ok += 1
        else:
            self._sep_fail += 1
            print(f"[RENDER SEP ERROR] item {self._sep_idx}: {msg}")
        self._sep_idx += 1
        self._render_next_separate()

    def _cancel_render(self):
        if self._render_thread and self._render_thread.isRunning():
            self._render_thread.cancel()
            self._render_thread.wait(5000)  # Esperar a que termine limpio
        if hasattr(self, '_progress_dlg'):
            self._progress_dlg.accept()
        self._render_btn.setEnabled(True)
        self._render_btn.setText("Crear película")

    def _on_render_done(self, success: bool, msg: str):
        self._render_btn.setEnabled(True)
        self._render_btn.setText("Crear película")
        if hasattr(self, '_progress_dlg'):
            if success:
                self._progress_dlg.mark_done()
                # NO cerrar automáticamente - dejar que el usuario elija
            else:
                self._progress_dlg.accept()
                state.toast_requested.emit(f"Error en el render: {msg}")
                print(f"[RENDER ERROR]\n{msg}")