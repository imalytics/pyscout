"""
Acceso a colores del tema como constantes simples.

SIMPLIFICADO: Ya no hay modo claro, solo importaciones directas de constantes.

Uso:
    from utils.theme_helpers import BG0, ACCENT, TEXT0
    widget.setStyleSheet(f"background:{BG0}; color:{ACCENT};")
"""

# Importación directa de todas las constantes
from styles.theme import (
    # Backgrounds
    BG0, BG1, BG2, BG3, BG4,
    
    # Acentos
    ACCENT, ACCENT2, ACCENT3,
    
    # Estados
    DANGER, GREEN,
    
    # Textos
    TEXT0, TEXT1, TEXT2, TEXT3,
    
    # Bordes y sombras
    BORDER, BORDER2, SHADOW,
    
    # Otros
    CLIP_COLORS, FONT, FONT_HEAD,
)

# Re-exportar todo para compatibilidad
__all__ = [
    "BG0", "BG1", "BG2", "BG3", "BG4",
    "ACCENT", "ACCENT2", "ACCENT3",
    "DANGER", "GREEN",
    "TEXT0", "TEXT1", "TEXT2", "TEXT3",
    "BORDER", "BORDER2", "SHADOW",
    "CLIP_COLORS", "FONT", "FONT_HEAD",
]