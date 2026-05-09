"""
Sistema unificado de rutas de recursos.
Funciona tanto en desarrollo como con PyInstaller.
"""
import os
import sys


def get_resource_path(relative_path: str) -> str:
    """
    Obtener ruta absoluta a un recurso.
    
    Funciona en:
    - Desarrollo: rutas relativas desde el directorio del proyecto
    - PyInstaller: carpeta temporal _MEIPASS
    
    Args:
        relative_path: Ruta relativa al directorio raíz del proyecto
        
    Returns:
        Ruta absoluta al recurso
        
    Example:
        >>> get_resource_path("ico.ico")
        'C:/proyecto/ico.ico'  # En desarrollo
        'C:/Users/temp/_MEI123/ico.ico'  # Con PyInstaller
    """
    try:
        # PyInstaller crea una carpeta temporal _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # Desarrollo: usar directorio del archivo principal (main.py)
        # Asumimos que este archivo está en utils/ y main.py en la raíz
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    return os.path.join(base_path, relative_path)


# ══════════════════════════════════════════════════════════════════════════════
# Constantes de recursos principales
# ══════════════════════════════════════════════════════════════════════════════

# Iconos principales
ICO_PATH = get_resource_path("ico.ico")
ICO_4K_PATH = get_resource_path("ico_4k.png")

# Splash screen
SPLASH_PATH = get_resource_path("splash.png")

# Fuentes
FONT_ROBOTO_PATH = get_resource_path("fonts/Roboto-Regular.ttf")

# Librerías nativas
if sys.platform == "win32":
    LIBMPV_PATH = get_resource_path("libmpv-2.dll")
elif sys.platform == "darwin":
    LIBMPV_PATH = get_resource_path("libmpv.2.dylib")
else:
    LIBMPV_PATH = get_resource_path("libmpv.so")


# ══════════════════════════════════════════════════════════════════════════════
# Helpers para carpetas específicas
# ══════════════════════════════════════════════════════════════════════════════

def get_icon_path(icon_name: str) -> str:
    """
    Obtener ruta a un icono SVG en la carpeta icons/
    
    Args:
        icon_name: Nombre del archivo (ej: "play.svg")
        
    Returns:
        Ruta completa al icono
    """
    return get_resource_path(f"icons/{icon_name}")


def get_font_path(font_name: str) -> str:
    """
    Obtener ruta a una fuente en la carpeta fonts/
    
    Args:
        font_name: Nombre del archivo (ej: "Roboto-Bold.ttf")
        
    Returns:
        Ruta completa a la fuente
    """
    return get_resource_path(f"fonts/{font_name}")


def verify_resources() -> dict:
    """
    Verificar que todos los recursos críticos existan.
    
    Returns:
        Dict con recursos faltantes y presentes
        
    Example:
        >>> result = verify_resources()
        >>> if result['missing']:
        ...     print(f"Faltan: {result['missing']}")
    """
    critical_resources = {
        "ico.ico": ICO_PATH,
        "splash.png": SPLASH_PATH,
    }
    # Only check native lib on the current platform
    if sys.platform == "win32":
        critical_resources["libmpv-2.dll"] = LIBMPV_PATH
    elif sys.platform == "darwin":
        critical_resources["libmpv.2.dylib"] = LIBMPV_PATH
    
    optional_resources = {
        "ico_4k.png": ICO_4K_PATH,
        "Roboto-Regular.ttf": FONT_ROBOTO_PATH,
    }
    
    result = {
        "missing": [],
        "present": [],
        "optional_missing": []
    }
    
    for name, path in critical_resources.items():
        if os.path.exists(path):
            result["present"].append(name)
        else:
            result["missing"].append(name)
    
    for name, path in optional_resources.items():
        if not os.path.exists(path):
            result["optional_missing"].append(name)
    
    return result


# ══════════════════════════════════════════════════════════════════════════════
# Debugging
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 80)
    print("VERIFICACIÓN DE RECURSOS")
    print("=" * 80)
    print(f"\nDirectorio base: {os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}")
    print(f"\nRecursos principales:")
    print(f"  ICO: {ICO_PATH}")
    print(f"    Existe: {os.path.exists(ICO_PATH)}")
    print(f"  ICO_4K: {ICO_4K_PATH}")
    print(f"    Existe: {os.path.exists(ICO_4K_PATH)}")
    print(f"  SPLASH: {SPLASH_PATH}")
    print(f"    Existe: {os.path.exists(SPLASH_PATH)}")
    print(f"  LIBMPV: {LIBMPV_PATH}")
    print(f"    Existe: {os.path.exists(LIBMPV_PATH)}")
    
    print("\n" + "=" * 80)
    result = verify_resources()
    print("RESULTADO:")
    print(f"  ✅ Presentes: {len(result['present'])}")
    print(f"  ❌ Faltantes: {len(result['missing'])}")
    print(f"  ⚠️  Opcionales faltantes: {len(result['optional_missing'])}")
    
    if result['missing']:
        print(f"\n❌ CRÍTICO - Faltan recursos obligatorios:")
        for res in result['missing']:
            print(f"     - {res}")
    
    if result['optional_missing']:
        print(f"\n⚠️  Recursos opcionales faltantes:")
        for res in result['optional_missing']:
            print(f"     - {res}")
    
    print("=" * 80)