# ScoutApp — Native Desktop

App de análisis de video deportivo. Reemplaza Nacsport Scout Plus con una interfaz moderna y scrubbing frame-exact nativo.

**Stack:** Python · PyQt6 · libmpv · FFmpeg

---

## Instalación en Windows

### 1. Instalar Python
Descargá Python 3.11 o 3.12 desde https://www.python.org  
✅ Marcá "Add to PATH" durante la instalación

### 2. Instalar dependencias Python
Abrí una terminal en la carpeta `scoutapp_native` y ejecutá:
```
pip install PyQt6 python-mpv
```

### 3. Instalar libmpv (DLL)
- Ir a: https://github.com/shinchiro/mpv-winbuild-cmake/releases
- Bajar el archivo `mpv-dev-x86_64-FECHA.7z`
- Extraer `libmpv-2.dll` y copiarlo a la carpeta `scoutapp_native`

### 4. Instalar FFmpeg
- Ir a: https://github.com/BtbN/FFmpeg-Builds/releases
- Bajar `ffmpeg-master-latest-win64-gpl.zip`
- Extraer `ffmpeg.exe` y copiarlo a la carpeta `scoutapp_native`

### 5. Correr la app
```
python main.py
```

---

## Instalación en Mac

```bash
brew install mpv ffmpeg
pip install PyQt6 python-mpv
python main.py
```

---

## Estructura del proyecto

```
scoutapp_native/
├── main.py                  # Entry point
├── app.py                   # Ventana principal + navegación
├── screens/
│   ├── observation.py       # Pantalla 1: Observación
│   ├── adjust.py            # Pantalla 2: Ajuste de clips
│   └── presentation.py      # Pantalla 3: Presentación final
├── components/
│   ├── video_player.py      # MpvWidget — reproductor nativo
│   ├── timeline.py          # ScrubBar + ClipTimeline con handles
│   ├── ram_scrubber.py      # Pre-carga frames para scrub instantáneo
│   ├── dialogs.py           # Modal de edición de clip
│   └── toast.py             # Notificaciones flotantes
├── store/
│   └── state.py             # Estado global con señales PyQt6
├── utils/
│   ├── ffmpeg.py            # Extracción de frames + render final
│   └── time_utils.py        # Formateo de tiempo
├── styles/
│   └── theme.py             # Design system: colores + QSS
├── libmpv-2.dll             # ← copiá aquí (Windows)
├── ffmpeg.exe               # ← copiá aquí (Windows)
└── requirements.txt
```

---

## Flujo de uso

### Pantalla 1 — Observación
1. Cargá un video con "Cargar video fuente"
2. Creá botones con el "+" (ej: "PNR", "Transición", "Poste bajo")
3. Mientras el video corre, presioná un botón para registrar un clip
4. Los registros aparecen abajo con timestamp y color

### Pantalla 2 — Ajuste
1. Seleccioná un clip de la lista izquierda
2. El video salta al timestamp del clip
3. Los frames se cargan en RAM — cuando aparece "⚡ X frames listos" el scrubbing es instantáneo
4. Arrastrá los handles naranjas del timeline para ajustar inicio y fin
5. "Agregar a presentación" lo envía a la pantalla 3

### Pantalla 3 — Presentación
1. Los clips aparecen en orden
2. Usá ▲▼ para reordenar
3. Agregá imágenes de portada con "+ Imagen portada"
4. Activá "Nombre sobre el clip" para overlay en el video final
5. "Producir presentación" → FFmpeg genera el MP4 final

---

## Guardar / cargar proyectos

- **Ctrl+S** o botón "Guardar" → genera un archivo `.scout` (JSON)
- Botón "Abrir" → carga un proyecto guardado
- El proyecto guarda: botones, clips, presentación y configuración

---

## Notas técnicas

**Scrubbing:** el sistema pre-extrae frames JPEG del clip seleccionado usando FFmpeg y los carga como `QPixmap` en RAM. Durante el drag de los handles, `QLabel.setPixmap()` muestra el frame — es una operación de textura GPU de ~0.05ms.

**Reproducción:** libmpv con `hwdec=auto` usa DXVA2 en Windows y VideoToolbox en Mac para decodificación por hardware.

**Render:** FFmpeg con `filter_complex` para concatenar clips e imágenes. El render corre en un `QThread` para no bloquear la UI.
