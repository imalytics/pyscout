from PySide6.QtCore import QSettings

# ══════════════════════════════════════════════════════════════════════════════
# TEMA OSCURO - Negro grafito + oro
# ══════════════════════════════════════════════════════════════════════════════
# SIMPLIFICADO: Ya no hay modo claro, solo constantes fijas

# Backgrounds
BG0 = "#0C0C0E"
BG1 = "#111115"
BG2 = "#18181D"
BG3 = "#1F1F26"
BG4 = "#26262F"

# Acentos
ACCENT = "#C9A44A"
ACCENT2 = "#A8852E"
ACCENT3 = "#E0BB6A"

# Estados
DANGER = "#C0392B"
GREEN = "#27AE60"

# Textos
TEXT0 = "#F0EDE8"
TEXT1 = "#C4BEB5"
TEXT2 = "#7A7570"
TEXT3 = "#3E3C3A"

# Bordes y sombras
BORDER = "rgba(255,252,248,0.05)"
BORDER2 = "rgba(255,252,248,0.09)"
SHADOW = "rgba(0,0,0,0.6)"

# Colores de clips
CLIP_COLORS = [
    "#C9A44A", "#4A90D9", "#27AE60", "#9B59B6",
    "#E67E22", "#E74C3C", "#1ABC9C", "#8BC34A",
]

# Fuentes
FONT = '"DM Sans", "Segoe UI Variable", "Segoe UI", system-ui, sans-serif'
FONT_HEAD = '"DM Sans", "Segoe UI Variable Display", system-ui, sans-serif'

# Font scaling
_font_scale = 1.0


def get_font_scale() -> float:
    """Obtener el factor de escala actual de fuentes."""
    return _font_scale


def set_font_scale(s: float):
    """Establecer factor de escala de fuentes."""
    global _font_scale
    _font_scale = s


def fs(size: int) -> int:
    """
    Escalar tamaño de fuente por factor actual.
    
    Args:
        size: Tamaño base en px
    
    Returns:
        Tamaño escalado (mínimo 8px)
    """
    return max(8, int(size * _font_scale))


def load_saved_theme():
    """
    Cargar preferencias de tema guardadas.
    NOTA: Ya no hay modo claro, pero mantenemos esto por compatibilidad.
    """
    # Leer preferencia guardada (por si acaso)
    QSettings("ScoutApp", "prefs").value("theme", "dark")
    # Pero siempre usamos dark de todas formas


def build_style():
    """
    Construir stylesheet completo de la aplicación.
    
    Returns:
        String CSS con todos los estilos
    """
    # Gradientes para elementos elevados
    grad_panel = f"qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 {BG2}, stop:1 {BG1})"
    grad_btn = f"qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 {BG3}, stop:1 {BG2})"
    grad_btn_hover = f"qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 {BG4}, stop:1 {BG3})"
    grad_primary = f"qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 {ACCENT3}, stop:1 {ACCENT})"

    return f"""
/* ═══════════════════════════════════════════
   BASE
═══════════════════════════════════════════ */
* {{
    font-family: {FONT};
    font-size: {fs(13)}px;
    outline: none;
}}
QMainWindow, QWidget {{
    background: {BG0};
    color: {TEXT0};
}}
QLabel {{
    color: {TEXT1};
    background: transparent;
    border: none;
}}

/* ═══════════════════════════════════════════
   BOTONES — diseño plano con elevación sutil
   Sin tocar bordes laterales con separadores
═══════════════════════════════════════════ */
QPushButton {{
    background: {grad_btn};
    color: {TEXT1};
    border: 1px solid {BORDER2};
    border-radius: 0px;
    padding: 6px 16px;
    font-family: {FONT};
    font-size: {fs(12)}px;
    font-weight: 500;
    letter-spacing: 0.3px;
    min-height: 28px;
}}
QPushButton:hover {{
    background: {grad_btn_hover};
    color: {TEXT0};
    border-color: {ACCENT};
    border-bottom: 2px solid {ACCENT};
}}
QPushButton:pressed {{
    background: {BG1};
    border-color: {ACCENT2};
    border-bottom: 1px solid {ACCENT2};
    padding-top: 7px;
    padding-bottom: 5px;
}}
QPushButton:disabled {{
    background: {BG1};
    color: {TEXT3};
    border-color: {BORDER};
}}

/* ── Primario ── */
QPushButton#primary {{
    background: {grad_primary};
    color: #1A1714;
    border: none;
    border-bottom: 2px solid {ACCENT2};
    font-weight: 600;
    letter-spacing: 0.4px;
}}
QPushButton#primary:hover {{
    background: {ACCENT3};
    border-bottom: 2px solid {ACCENT};
    color: #1A1714;
}}
QPushButton#primary:pressed {{
    background: {ACCENT2};
    border-bottom: 1px solid {ACCENT2};
    padding-top: 7px;
}}
QPushButton#primary:disabled {{
    background: {BG3};
    color: {TEXT3};
    border: none;
}}

/* ── Tabs: solo subrayado, sin bordes laterales ── */
QPushButton#tab {{
    background: transparent;
    color: {TEXT2};
    border: none;
    border-bottom: 3px solid transparent;
    border-radius: 0;
    padding: 0 24px;
    font-size: {fs(13)}px;
    font-weight: 400;
    letter-spacing: 0.2px;
    min-height: 46px;
}}
QPushButton#tab:hover {{
    color: {TEXT0};
    background: {BORDER};
    border-bottom: 3px solid {BORDER2};
}}
QPushButton#tab_active {{
    background: transparent;
    color: {ACCENT};
    border: none;
    border-bottom: 3px solid {ACCENT};
    border-radius: 0;
    padding: 0 24px;
    font-size: {fs(13)}px;
    font-weight: 600;
    letter-spacing: 0.2px;
    min-height: 46px;
}}

/* ── Ícono ── */
QPushButton#icon_btn {{
    background: transparent;
    color: {TEXT2};
    border: 1px solid {BORDER2};
    border-radius: 0;
    min-width: 30px; max-width: 30px;
    min-height: 30px; max-height: 30px;
    padding: 0;
    font-size: {fs(16)}px;
    font-weight: 700;
}}
QPushButton#icon_btn:hover {{
    color: {ACCENT};
    border-color: {ACCENT};
    background: {BORDER};
}}

/* ── Control bar (play, skip, speed) ── */
QPushButton#ctrl_btn {{
    background: transparent;
    color: {TEXT2};
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0;
    padding: 4px 14px;
    font-size: {fs(12)}px;
    font-weight: 500;
    letter-spacing: 0.3px;
    min-height: 26px;
}}
QPushButton#ctrl_btn:hover {{
    color: {ACCENT};
    background: transparent;
    border-bottom: 2px solid {ACCENT};
}}
QPushButton#ctrl_btn:pressed {{
    color: {ACCENT2};
    border-bottom: 2px solid {ACCENT2};
}}

/* ── Acción de sidebar (botones de categoría) ── */
QPushButton#action_btn {{
    background: transparent;
    color: {TEXT1};
    border: none;
    border-left: 2px solid transparent;
    border-radius: 0;
    padding: 8px 14px 8px 12px;
    font-size: {fs(13)}px;
    font-weight: 500;
    text-align: left;
    min-height: 36px;
}}
QPushButton#action_btn:hover {{
    background: {BORDER};
    color: {TEXT0};
    border-left: 2px solid {BORDER2};
}}
QPushButton#action_btn:pressed {{
    border-left: 2px solid {ACCENT};
    color: {ACCENT};
}}

/* ═══════════════════════════════════════════
   INPUTS
═══════════════════════════════════════════ */
QLineEdit, QTextEdit {{
    background: {BG1};
    color: {TEXT0};
    border: none;
    border-bottom: 1px solid {BORDER2};
    border-radius: 0;
    padding: 7px 10px;
    font-size: {fs(13)}px;
    selection-background-color: {ACCENT};
    selection-color: #1A1714;
}}
QLineEdit:focus, QTextEdit:focus {{
    border-bottom: 2px solid {ACCENT};
    background: {BG2};
    padding-bottom: 6px;
}}
QSpinBox {{
    background: {BG1};
    color: {TEXT0};
    border: none;
    border-bottom: 1px solid {BORDER2};
    border-radius: 0;
    padding: 5px 8px;
    font-size: {fs(12)}px;
    min-height: 24px;
}}
QSpinBox:focus {{ border-bottom: 2px solid {ACCENT}; padding-bottom: 4px; }}
QSpinBox::up-button, QSpinBox::down-button {{
    width: 14px; border: none; background: transparent;
}}

/* ═══════════════════════════════════════════
   SCROLLBARS — casi invisibles
═══════════════════════════════════════════ */
QScrollBar:vertical {{
    background: transparent; width: 7px; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER2}; border-radius: 2px; min-height: 28px;
}}
QScrollBar::handle:vertical:hover {{ background: {ACCENT}; width: 7px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 7px; }}
QScrollBar::handle:horizontal {{
    background: {BORDER2}; border-radius: 2px; min-height: 28px;
}}
QScrollBar::handle:horizontal:hover {{ background: {ACCENT}; }}

/* ═══════════════════════════════════════════
   COMBOS
═══════════════════════════════════════════ */
QComboBox {{
    background: {BG1};
    color: {TEXT0};
    border: none;
    border-bottom: 1px solid {BORDER2};
    border-radius: 0;
    padding: 5px 10px;
    font-size: {fs(13)}px;
    min-height: 26px;
}}
QComboBox:hover {{ border-bottom: 2px solid {ACCENT3}; padding-bottom: 4px; }}
QComboBox:focus {{ border-bottom: 2px solid {ACCENT}; padding-bottom: 4px; }}
QComboBox::drop-down {{ border: none; width: 18px; }}
QComboBox QAbstractItemView {{
    background: {BG2};
    color: {TEXT0};
    border: 1px solid {BORDER2};
    border-top: none;
    selection-background-color: {BG3};
    selection-color: {ACCENT};
    padding: 2px;
    outline: none;
}}

/* ═══════════════════════════════════════════
   MISC
═══════════════════════════════════════════ */
QProgressBar {{
    background: {BG3};
    border: none;
    border-radius: 0;
    max-height: 3px;
}}
QProgressBar::chunk {{ background: {ACCENT}; }}

QDialog {{
    background: {BG1};
    border: 1px solid {BORDER2};
    border-radius: 0;
}}

QMenu {{
    background: {BG2};
    border: 1px solid {BORDER2};
    border-top: 2px solid {ACCENT};
    border-radius: 0;
    padding: 4px 0;
}}
QMenu::item {{
    padding: 9px 24px;
    color: {TEXT1};
    font-size: {fs(13)}px;
    border-left: 2px solid transparent;
}}
QMenu::item:selected {{
    background: {BG3};
    color: {ACCENT};
    border-left: 2px solid {ACCENT};
}}
QMenu::separator {{
    height: 1px; background: {BORDER2}; margin: 3px 0;
}}

QCheckBox {{ color: {TEXT0}; spacing: 10px; font-size: {fs(13)}px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border: 1px solid {BORDER2};
    border-radius: 2px;
    background: {BG1};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT}; border-color: {ACCENT};
}}
QRadioButton {{ color: {TEXT0}; spacing: 10px; font-size: {fs(13)}px; }}
QRadioButton::indicator {{
    width: 16px; height: 16px;
    border: 1px solid {BORDER2};
    border-radius: 8px;
    background: {BG1};
}}
QRadioButton::indicator:checked {{
    background: {ACCENT}; border-color: {ACCENT};
}}

QFrame {{ border: none; }}
QScrollArea {{ border: none; background: transparent; }}

/* Named containers */
QWidget#sidebar_left {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #0e0e12, stop:1 {BG1});
}}
QWidget#ctrl_bar {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 {BG2}, stop:1 {BG1});
    border-top: 1px solid rgba(255,255,255,0.06);
}}
QWidget#tab_bar_widget {{
    background: {BG1};
    border-bottom: 1px solid rgba(255,255,255,0.06);
}}
QWidget#reg_header {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 {BG2}, stop:1 {BG1});
    border-top: 1px solid rgba(255,255,255,0.06);
}}
QSplitter::handle {{ background: {BORDER}; width: 1px; height: 1px; }}
"""