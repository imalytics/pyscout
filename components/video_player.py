"""
MpvWidget: reproductor de video nativo usando libmpv.

CAMBIO DE ARQUITECTURA:
- Antes: property_observer("time-pos") disparaba una señal PyQt por CADA FRAME
  (25-60 veces/seg). Esto saturaba el event loop con marshaling de señales
  entre el thread de mpv y el thread de Qt.

- Ahora: mpv solo actualiza variables internas (_position, _duration).
  Un QTimer a 12fps lee esas variables y emite position_changed.
  El event loop solo procesa 12 actualizaciones/seg en lugar de 60.
  
  Para seek y play/pause usamos observadores solo de esas propiedades
  (cambian raramente → no saturan nada).
"""
import os
import sys
from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import Qt, Signal, QTimer

try:
    import mpv
except Exception as _mpv_err:
    mpv = None


class MpvWidget(QWidget):
    duration_changed = Signal(float)
    position_changed = Signal(float)
    file_loaded      = Signal()
    playback_started = Signal()
    playback_paused  = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DontCreateNativeAncestors)
        self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)
        self.setMinimumSize(320, 180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("background-color: black;")

        self._duration  = 0.0
        self._position  = 0.0
        self._loaded    = False
        self._paused    = True
        self._last_emitted_pos = -1.0
        self._player    = None
        self._ui_timer  = None
        self._pending_seek: float | None = None
        self._seek_timer = QTimer(self)
        self._seek_timer.setSingleShot(True)
        self._seek_timer.setInterval(40)  # max 25 seeks/seg
        self._seek_timer.timeout.connect(self._flush_seek)

        if mpv is None:
            print(f"[MpvWidget] libmpv no disponible")
            return

        wid = str(int(self.winId()))
        _configs = []
        if sys.platform == "darwin":
            _configs = [
                dict(vo="libmpv", hwdec="auto-safe"),
            ]
        else:
            _configs = [
                dict(vo="gpu",      hwdec="auto-safe"),
                dict(vo="gpu",      hwdec="no"),
                dict(vo="direct3d", hwdec="no"),
                dict(vo="gpu-next", hwdec="auto-safe", gpu_api="d3d11"),
                dict(vo="software", hwdec="no"),
            ]

        for cfg in _configs:
            try:
                self._player = mpv.MPV(
                    wid=wid,
                    keep_open="yes",
                    pause=True,
                    log_handler=self._mpv_log,
                    loglevel="error",
                    **cfg,
                )
                print(f"[MpvWidget] OK: {cfg}")
                break
            except Exception as e:
                print(f"[MpvWidget] fallback {cfg}: {e}")
                self._player = None

        if self._player is None:
            return

        # ── Solo observar propiedades que cambian raramente ───────────────────
        # "time-pos" NO — lo leemos con el timer
        # "duration" solo cambia al cargar un archivo
        # "pause" solo cambia al play/pause

        @self._player.property_observer("duration")
        def _on_dur(name, value):
            if value is not None:
                self._duration = float(value)
                self.duration_changed.emit(self._duration)

        @self._player.property_observer("pause")
        def _on_pause(name, value):
            self._paused = bool(value)
            if value:
                self.playback_paused.emit()
            else:
                self.playback_started.emit()

        @self._player.property_observer("playback-time")
        def _on_pb(name, value):
            # Solo actualizar _position aquí, sin emitir señal
            if value is not None:
                self._position = float(value)
                if not self._loaded:
                    self._loaded = True
                    self.file_loaded.emit()

        # ── Timer que emite position_changed a 12fps ──────────────────────────
        # 12fps es más que suficiente para la barra de progreso y el playhead.
        # El rendering de video corre a su propio fps — este timer solo actualiza la UI.
        self._ui_timer = QTimer(self)
        self._ui_timer.setInterval(83)  # ~12fps
        self._ui_timer.timeout.connect(self._tick)
        self._ui_timer.start()

        # Escuchar mute global
        from store.state import state
        state.global_mute_changed.connect(self._on_global_mute)
        if state.global_mute and self._player:
            self._player.mute = True

    def _tick(self):
        """Emitir posición actual a la UI — corre en el hilo principal a 12fps."""
        if not self._player or not self._loaded:
            return
        # Leer desde la variable interna (ya actualizada por el observer thread)
        pos = self._position
        # Solo emitir si cambió más de 0.05s (evitar spam cuando está pausado)
        if abs(pos - self._last_emitted_pos) >= 0.05:
            self._last_emitted_pos = pos
            self.position_changed.emit(pos)

    def _mpv_log(self, level, component, message):
        if level in ("error", "fatal"):
            print(f"[mpv/{component}] {message.strip()}")

    # ── API pública ───────────────────────────────────────────────────────────

    def load(self, path: str):
        if not self._player:
            return
        self._loaded   = False
        self._duration = 0.0
        self._position = 0.0
        self._last_emitted_pos = -1.0
        # Aplicar global mute si está activo
        from store.state import state
        if state.global_mute:
            self._player.mute = True
        self._player.play(path)

    def play(self):
        if self._player:
            self._player.pause = False

    def pause(self):
        if self._player:
            self._player.pause = True

    def stop(self):
        if self._player:
            self._player.command('stop')

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.toggle_play()
            e.accept()
            return
        super().mousePressEvent(e)

    def toggle_play(self):
        if self._player:
            self._player.pause = not self._player.pause

    def is_paused(self) -> bool:
        return self._paused

    def seek(self, seconds: float):
        """Seek con debounce de 40ms — evita saturar el event loop de mpv."""
        if not self._player:
            return
        t = max(0.0, seconds)
        if self._duration > 0:
            t = min(t, self._duration - 0.05)
        self._pending_seek = t
        if not self._seek_timer.isActive():
            self._seek_timer.start()

    def _flush_seek(self):
        if self._pending_seek is None or not self._player:
            return
        try:
            self._player.seek(self._pending_seek, "absolute+exact")
        except Exception:
            pass
        self._pending_seek = None

    def seek_relative(self, delta: float):
        if not self._player:
            return
        try:
            self._player.seek(delta, "relative+exact")
        except Exception:
            pass

    def set_speed(self, speed: float):
        if self._player:
            try:
                self._player.speed = speed
            except Exception:
                pass

    def toggle_mute(self) -> bool:
        if not self._player:
            return False
        try:
            self._player.mute = not self._player.mute
            return bool(self._player.mute)
        except Exception:
            return False

    def _on_global_mute(self, muted: bool):
        """Responder al cambio de mute global."""
        if self._player:
            try:
                self._player.mute = muted
            except Exception:
                pass

    @property
    def duration(self) -> float:
        return self._duration

    @property
    def position(self) -> float:
        return self._position

    def closeEvent(self, event):
        if hasattr(self, '_ui_timer') and self._ui_timer:
            try: self._ui_timer.stop()
            except Exception: pass
        if getattr(self, '_player', None):
            try: self._player.terminate()
            except Exception: pass
        super().closeEvent(event)