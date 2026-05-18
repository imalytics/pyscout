"""
PyScout — main.py
Arranque con Splash Screen + Flujo correcto de Licencias.
"""
import sys
import os
import ctypes

APP_VERSION = "1.0.3"

# ── Rutas unificadas de recursos ─────────────────────────────────────────────
try:
    from utils.resource_paths import (
        get_resource_path, ICO_PATH, SPLASH_PATH, LIBMPV_PATH
    )
except ImportError:
    def get_resource_path(path):
        _DIR = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(_DIR, path)
    ICO_PATH = get_resource_path("ico.ico")
    SPLASH_PATH = get_resource_path("splash.png")
    LIBMPV_PATH = get_resource_path("libmpv-2.dll")

# ── Carga de libmpv multiplataforma ──────────────────────────────────────────
def _load_libmpv():
    """Carga libmpv según el sistema operativo."""
    _DIR = os.path.dirname(os.path.abspath(__file__))
    os.environ["PATH"] = _DIR + os.pathsep + os.environ.get("PATH", "")
    
    if sys.platform == "darwin":
        os.environ["DYLD_LIBRARY_PATH"] = _DIR + os.pathsep + os.environ.get("DYLD_LIBRARY_PATH", "")
    
    paths_to_try = []
    if sys.platform == "win32":
        if os.path.exists(LIBMPV_PATH): paths_to_try.append(LIBMPV_PATH)
    elif sys.platform == "darwin":
        bundle_dylib = os.path.join(_DIR, "libmpv.2.dylib")
        if os.path.exists(bundle_dylib): paths_to_try.append(bundle_dylib)
        else:
            for hb_path in ["/opt/homebrew/lib/libmpv.dylib", "/usr/local/lib/libmpv.dylib"]:
                if os.path.exists(hb_path): paths_to_try.append(hb_path); break
    
    loaded = False
    for lib_path in paths_to_try:
        try:
            ctypes.CDLL(lib_path)
            print(f"[libmpv] ✓ Cargado: {lib_path}")
            loaded = True
            break
        except Exception as e:
            print(f"[libmpv] ✗ Falló {lib_path}: {e}")
            
    if not loaded:
        print("[libmpv] ⚠ Advertencia: libmpv no cargado.")

_load_libmpv()

# ── Fix DPI awareness (Windows) ─────────────────────────────────────────────────
if sys.platform == "win32":
    try: ctypes.windll.user32.SetProcessDPIAware()
    except Exception: pass

# ── Crear estructura de carpetas en Documentos ───────────────────────────────
from pathlib import Path as _Path

def _ensure_project_folders():
    """Crear carpeta PyScout en Documentos con subcarpetas."""
    if sys.platform == "win32":
        docs = _Path(os.path.expanduser("~/Documents"))
    elif sys.platform == "darwin":
        docs = _Path.home() / "Documents"
    else:
        docs = _Path.home() / "Documents"
    root = docs / "PyScout"
    for sub in ("Proyectos", "Botoneras", "Exportados"):
        try:
            (root / sub).mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
    return str(root)

PYSCOUT_DOCS = _ensure_project_folders()

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPalette, QPixmap, QIcon
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QFrame, QProgressBar,
)

class SplashScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyScout")
        self.setFixedSize(600, 400)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        if os.path.exists(ICO_PATH):
            self.setWindowIcon(QIcon(ICO_PATH))
            
        self._build_ui()
        self._center_on_screen()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(0)
        card = QFrame()
        card.setObjectName("splashCard")
        card.setStyleSheet("QFrame#splashCard { background: #0a0a0a; border: 1px solid rgba(212, 172, 78, 0.38); border-radius: 14px; }")
        root.addWidget(card)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(10)
        
        self.image_label = QLabel()
        self.image_label.setFixedHeight(240)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background:#000; border-radius:10px; border:1px solid rgba(255,255,255,0.06);")
        if os.path.exists(SPLASH_PATH):
            pm = QPixmap(SPLASH_PATH)
            if not pm.isNull():
                self.image_label.setPixmap(pm.scaled(560, 240, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
        lay.addWidget(self.image_label)

        title = QLabel("PyScout")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #d4ac4e; font-size: 26px; font-weight: 700; letter-spacing: 0.5px; background: transparent;")
        lay.addWidget(title)

        self.status_label = QLabel("Initializing...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: rgba(235,235,255,0.78); font-size: 12px; background: transparent;")
        lay.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(10)
        self.progress.setStyleSheet("QProgressBar { background: #121212; border: 1px solid rgba(255,255,255,0.08); border-radius: 5px; } QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #b8932d, stop:1 #e2c15f); border-radius: 4px; }")
        lay.addWidget(self.progress)

        bottom = QHBoxLayout()
        bottom.setContentsMargins(2, 0, 2, 0)
        footer = QLabel("Sports Video Analysis")
        footer.setStyleSheet("color: rgba(255,255,255,0.45); font-size: 10px; background: transparent;")
        bottom.addWidget(footer)
        bottom.addStretch()
        self.percent_label = QLabel("0%")
        self.percent_label.setStyleSheet("color: rgba(212, 172, 78, 0.92); font-size: 10px; font-weight: 600; background: transparent;")
        bottom.addWidget(self.percent_label)
        lay.addLayout(bottom)

    def _center_on_screen(self):
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + (geo.height() - self.height()) // 2
            self.move(x, y)

    def set_progress(self, value: int, text: str):
        value = max(0, min(100, int(value)))
        self.progress.setValue(value)
        self.percent_label.setText(f"{value}%")
        self.status_label.setText(text)
        QApplication.processEvents()

def _apply_theme(app: QApplication):
    from styles.theme import load_saved_theme, build_style, BG0, BG1, BG2, TEXT0, ACCENT
    load_saved_theme()
    app.setApplicationName("PyScout")
    app.setApplicationVersion("1.0")
    app.setStyle("Fusion")
    if os.path.exists(ICO_PATH): app.setWindowIcon(QIcon(ICO_PATH))
    
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor(BG0))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(TEXT0))
    pal.setColor(QPalette.ColorRole.Base, QColor(BG1))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor(BG2))
    pal.setColor(QPalette.ColorRole.Text, QColor(TEXT0))
    pal.setColor(QPalette.ColorRole.Button, QColor(BG2))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT0))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(ACCENT))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("white"))
    app.setPalette(pal)
    app.setStyleSheet(build_style())

def main():
    if sys.platform == "win32":
        try: ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("PyScout.Desktop.App.1")
        except Exception: pass

    app = QApplication(sys.argv)

    from utils.i18n import detect_and_load
    detect_and_load()

    splash = SplashScreen()
    splash.show()

    steps = [
        (6,  "Loading theme...", 220),
        (14, "Applying palette...", 220),
        (24, "Preparing interface...", 260),
        (36, "Loading modules...", 260),
        (48, "Starting workspace...", 280),
        (62, "Checking video engine...", 300),
        (76, "Opening project shell...", 320),
        (88, "Finalizing...", 340),
    ]

    state = {"index": 0, "win": None}

    def run_step():
        idx = state["index"]
        if idx >= len(steps):
            splash.set_progress(94, "Launching PyScout...")
            QTimer.singleShot(380, startup_sequence)
            return

        value, text, delay = steps[idx]
        if idx == 0: _apply_theme(app)
        splash.set_progress(value, text)
        state["index"] += 1
        QTimer.singleShot(delay, run_step)

    def startup_sequence():
        """Secuencia: splash → StartDialog (con licencia) → MainWindow."""
        try:
            splash.close()

            # Importar StartDialog
            try:
                from components.dialogs import StartDialog
            except ImportError:
                from dialogs import StartDialog

            # Crear MainWindow oculta
            from app import MainWindow
            state["win"] = MainWindow()
            state["win"].hide()
            if os.path.exists(ICO_PATH):
                try: state["win"].setWindowIcon(QIcon(ICO_PATH))
                except: pass

            # StartDialog muestra licencia + proyectos
            start_dlg = StartDialog()

            def on_project_selected(path):
                if hasattr(state["win"], '_load_project_path'):
                    state["win"]._load_project_path(path)

            start_dlg.project_selected.connect(on_project_selected)
            result = start_dlg.exec()

            if not result:
                app.quit()
                return

            try: state["win"].showMaximized()
            except:
                try: state["win"].show()
                except: pass

        except Exception as e:
            print(f"[CRASH] {e}")
            import traceback; traceback.print_exc()

    QTimer.singleShot(120, run_step)
    sys.exit(app.exec())

if __name__ == "__main__":
    main()