"""
Helper para cargar iconos SVG en PyScout.
Los SVGs se cargan dinámicamente y se pueden cambiar de color.
"""

from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import QByteArray, QSize
import os, sys

def _resolve_icons_dir():
    # En Nuitka/PyInstaller los archivos de datos quedan al lado del .exe
    base = os.path.dirname(os.path.abspath(sys.argv[0]))
    candidate = os.path.join(base, "icons")
    if os.path.isdir(candidate):
        return candidate
    # Fallback dev: junto a este archivo fuente
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")

ICONS_DIR = _resolve_icons_dir()

def get_icon(name: str, color: str = "#FFFFFF", size: tuple = (24, 24)) -> QIcon:
    """
    Cargar un icono SVG con color personalizado.
    
    Args:
        name: Nombre del archivo sin extensión (ej: "play", "pause")
        color: Color en formato hex (ej: "#E8821A")
        size: Tupla (width, height) en píxeles
    
    Returns:
        QIcon listo para usar en botones
    
    Ejemplo:
        play_icon = get_icon("play", "#E8821A", (20, 20))
        btn.setIcon(play_icon)
    """
    svg_path = os.path.join(ICONS_DIR, f"{name}.svg")
    
    if not os.path.exists(svg_path):
        print(f"Warning: Icon not found: {svg_path}")
        return QIcon()
    
    # Leer SVG
    with open(svg_path, 'r', encoding='utf-8') as f:
        svg_content = f.read()
    
    # Convertir color a string (por si es un ThemeProxy u otro objeto)
    color_str = str(color)
    
    # Reemplazar currentColor con el color deseado
    svg_colored = svg_content.replace('currentColor', color_str)
    
    # Renderizar SVG a QPixmap
    svg_bytes = QByteArray(svg_colored.encode('utf-8'))
    renderer = QSvgRenderer(svg_bytes)
    
    pixmap = QPixmap(QSize(*size))
    pixmap.fill(QColor(0, 0, 0, 0))  # Transparente real (ARGB)
    
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    
    return QIcon(pixmap)


def set_icon_color(button, icon_name: str, color: str, size: tuple = (20, 20)):
    """
    Helper para setear icono con color en un botón.
    
    Args:
        button: QPushButton
        icon_name: Nombre del icono (sin extensión)
        color: Color hex
        size: Tamaño del icono
    
    Ejemplo:
        set_icon_color(play_btn, "play", "#E8821A", (20, 20))
    """
    icon = get_icon(icon_name, color, size)
    button.setIcon(icon)
    button.setIconSize(QSize(*size))


# Atajo para iconos comunes con colores de la app
# Importar estos en lugar de recrear cada vez

def play_icon(size=(20, 20), color="#8C8C8C"):
    return get_icon("play", color, size)

def pause_icon(size=(20, 20), color="#8C8C8C"):
    return get_icon("pause", color, size)

def fullscreen_icon(size=(20, 20), color="#8C8C8C"):
    return get_icon("fullscreen", color, size)

def fullscreen_exit_icon(size=(20, 20), color="#8C8C8C"):
    return get_icon("fullscreen_exit", color, size)

def previous_icon(size=(16, 16), color="#8C8C8C"):
    return get_icon("previous", color, size)

def next_icon(size=(16, 16), color="#8C8C8C"):
    return get_icon("next", color, size)

def mute_icon(size=(18, 18), color="#8C8C8C"):
    return get_icon("mute", color, size)

def volume_icon(size=(18, 18), color="#8C8C8C"):
    return get_icon("volume", color, size)

def eye_icon(size=(18, 18), color="#8C8C8C"):
    return get_icon("eye", color, size)

def eye_off_icon(size=(18, 18), color="#8C8C8C"):
    return get_icon("eye_off", color, size)