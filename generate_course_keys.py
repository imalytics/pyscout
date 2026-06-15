#!/usr/bin/env python3
"""
Generador de códigos de curso para PyScout.

Uso:
  python generate_course_keys.py [cantidad] [dias]

Ejemplos:
  python generate_course_keys.py 20 90    # 20 códigos de 90 días
  python generate_course_keys.py 1 30     # 1 código de 30 días (para probar)
  python generate_course_keys.py          # 20 códigos de 90 días (defaults)

El archivo generado se puede mandar directamente a los alumnos por email.
Cada código es de un solo uso por dispositivo (se liga al HWID al activar).
"""
import sys, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from utils.license_manager import generate_course_key


def main():
    n    = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 90

    keys = [generate_course_key(days) for _ in range(n)]

    date_str  = datetime.date.today().strftime("%Y%m%d")
    out_path  = Path(f"curso_keys_{date_str}_{n}x{days}d.txt")

    header = (
        f"PyScout — Códigos de Acceso de Curso\n"
        f"Generado : {datetime.date.today()}\n"
        f"Duración : {days} días por código\n"
        f"Cantidad : {n} código(s)\n"
        f"{'=' * 44}\n\n"
        f"INSTRUCCIONES PARA EL ALUMNO:\n"
        f"  1. Abrir PyScout\n"
        f"  2. En el launcher, hacer clic en 'Activar licencia'\n"
        f"  3. Pegar el código y hacer clic en 'Activar'\n"
        f"  4. ¡Listo! El acceso dura {days} días desde la activación.\n\n"
        f"{'=' * 44}\n\n"
    )

    lines = "\n".join(f"{i:2d}.  {k}" for i, k in enumerate(keys, 1))
    out_path.write_text(header + lines + "\n", encoding="utf-8")

    print(f"\n  PyScout — {n} código(s) de curso ({days} días)\n")
    for i, k in enumerate(keys, 1):
        print(f"  {i:2d}.  {k}")
    print(f"\n  Guardado en: {out_path.resolve()}\n")


if __name__ == "__main__":
    main()
