"""utils/updater.py — Verificar y aplicar actualizaciones en background."""
import os, sys, threading, tempfile
from PySide6.QtCore import QObject, Signal

CURRENT_VERSION = "1.0.5"
UPDATE_URL = "https://imalytics.github.io/pyscout/version.json"


def get_install_dir() -> str:
    """Directorio donde está instalado main.exe."""
    return os.path.dirname(os.path.abspath(sys.argv[0]))


class UpdateChecker(QObject):
    update_available = Signal(str, str, str)  # version, download_url, changelog
    no_update = Signal()
    check_failed = Signal(str)

    def check(self):
        threading.Thread(target=self._check_bg, daemon=True).start()

    def _check_bg(self):
        try:
            import requests
            r = requests.get(UPDATE_URL, timeout=5)
            if r.status_code != 200:
                self.check_failed.emit(f"HTTP {r.status_code}")
                return
            data = r.json()
            latest = data.get("version", CURRENT_VERSION)
            download_url = data.get("download_url", "")
            changelog = data.get("changelog", "")
            if self._is_newer(latest, CURRENT_VERSION):
                self.update_available.emit(latest, download_url, changelog)
            else:
                self.no_update.emit()
        except Exception as e:
            self.check_failed.emit(str(e))

    @staticmethod
    def _is_newer(latest: str, current: str) -> bool:
        try:
            return [int(x) for x in latest.split(".")] > [int(x) for x in current.split(".")]
        except Exception:
            return False


class UpdateDownloader(QObject):
    progress = Signal(int, int)   # bytes_done, bytes_total
    finished = Signal(str)        # ruta local del instalador descargado
    failed = Signal(str)          # mensaje de error

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self._url = url
        self._cancelled = False

    def start(self):
        self._cancelled = False
        threading.Thread(target=self._download_bg, daemon=True).start()

    def cancel(self):
        self._cancelled = True

    def _download_bg(self):
        try:
            import requests
            dest = os.path.join(tempfile.gettempdir(), "pyscout_setup.exe")
            r = requests.get(self._url, stream=True, timeout=60)
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            done = 0
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=65536):
                    if self._cancelled:
                        return
                    if chunk:
                        f.write(chunk)
                        done += len(chunk)
                        self.progress.emit(done, total)
            self.finished.emit(dest)
        except Exception as e:
            self.failed.emit(str(e))


def apply_update(installer_path: str):
    """Lanza el instalador silencioso y cierra la app. El user no hace nada."""
    import subprocess
    if sys.platform == "win32":
        # /SILENT: instala sin UI (solo barra de progreso)
        # /CLOSEAPPLICATIONS: cierra procesos que usen los archivos
        # /RESTARTAPPLICATIONS: reinicia la app al terminar
        subprocess.Popen(
            [installer_path, "/SILENT", "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS"],
            close_fds=True,
        )
    elif sys.platform == "darwin":
        subprocess.Popen(["open", installer_path], close_fds=True)
    sys.exit(0)
