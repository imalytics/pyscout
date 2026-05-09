# PYSCOUT — DOCUMENTACIÓN TÉCNICA COMPLETA
# Versión: Mayo 2026
# Uso: Este archivo es el contexto completo del proyecto para agentes de IA
#      (Claude Code, Claude Projects, etc.)
# Última actualización: sesión de desarrollo del 4 de mayo 2026

################################################################################
# 1. VISIÓN GENERAL
################################################################################

PyScout es una aplicación de escritorio para análisis de video deportivo.
Permite a entrenadores y analistas observar partidos, marcar jugadas,
recortarlas con precisión, armar presentaciones tácticas y exportar video
editado. Todo offline, sin dependencias cloud.

Stack técnico:
  - Python 3.14
  - PySide6 (Qt 6) para la interfaz gráfica
  - libmpv (via python-mpv) para reproducción de video
  - FFmpeg para exportación y render
  - Polar.sh para licenciamiento online

Plataformas: Windows 10/11 (principal), macOS (compatible), Linux (parcial)

Modelo de negocio: Suscripción mensual a $3 USD vía Polar.sh
  - Trial gratuito: 7 días
  - Activación por dispositivo (1 slot por clave)
  - Renovación automática, Polar cobra y maneja pagos

Distribución:
  - Desarrollo: PyInstaller (rápido, fácil debug)
  - Producción: Nuitka (compila a C, anti-decompilación)
  - Instalador: Inno Setup con imágenes lateral.png y chica.png
  - Se instala en %APPDATA%\PyScout (no pide admin)

################################################################################
# 2. ESTRUCTURA DE ARCHIVOS
################################################################################

scoutapp/
├── main.py                    # Arranque, splash screen, carga de libmpv
├── app.py                     # MainWindow — menúbar, navegación, autosave
├── store/
│   ├── __init__.py
│   └── state.py               # AppState singleton — TODA la lógica de datos
├── screens/
│   ├── __init__.py
│   ├── observation.py          # Pantalla 1: video + botonera + registros
│   ├── adjust.py               # Pantalla 2: timeline + recorte + filtros
│   └── presentation.py         # Pantalla 3: listado + render + export
├── components/
│   ├── __init__.py
│   ├── dialogs.py              # StartDialog (launcher) + ClipEditDialog
│   ├── video_player.py         # MpvWidget — wrapper de libmpv
│   ├── timeline.py             # ClipTimeline + ScrubBar (NLE-style)
│   └── toast.py                # Notificaciones flotantes
├── utils/
│   ├── __init__.py
│   ├── license_manager.py      # Polar.sh + trial + 5 archivos + registro
│   ├── ffmpeg.py               # Wrapper de FFmpeg para render
│   ├── resource_paths.py       # Rutas a ico, splash, libmpv
│   ├── theme_helpers.py        # Helpers para el tema
│   └── time_utils.py           # fmt_time, parse_time
├── styles/
│   ├── __init__.py
│   └── theme.py                # Paleta de colores, fuentes, estilos CSS
├── ico.ico                     # Ícono de la app (Windows)
├── ico_4k.png                  # Ícono alta resolución (StartDialog)
├── splash.png                  # Imagen del splash screen
├── lateral.png                 # Wizard lateral para Inno Setup
├── chica.png                   # Wizard chico para Inno Setup
├── libmpv-2.dll                # Motor de video (Windows)
├── ffmpeg.exe                  # Encoder de video (Windows)
├── installer.iss               # Script de Inno Setup
└── CLAUDE.md                   # Instrucciones para Claude Code

ARCHIVOS A BORRAR (muertos):
  - analyze_theme_usage.py      # Script de migración viejo
  - migrate_to_pyside6.py       # Script de migración viejo
  - code_bundler.py             # Herramienta auxiliar, no parte de la app
  - components/ram_scrubber.py  # Pre-carga de frames, no se usa

################################################################################
# 3. ARQUITECTURA
################################################################################

La app sigue el patrón Singleton State + Signals:

  AppState (store/state.py)
    ├── buttons: list[Button]          # Botonera personalizable
    ├── clips: list[Clip]              # Clips registrados
    ├── video_sources: list[VideoSource]  # Videos cargados
    ├── presentation: list[PresentationItem]  # Presentación activa
    ├── presentations: list[list[PresentationItem]]  # Multi-presentación (hasta 5)
    └── Signals → conectados a autosave + UI refresh

Flujo de datos:
  1. El usuario interactúa con la UI (botón, slider, drag)
  2. La UI llama a un método de AppState (add_clip, remove_pres_item, etc.)
  3. AppState muta la lista interna y emite un Signal
  4. Todas las pantallas conectadas al Signal se refrescan
  5. El autosave escucha los mismos Signals y guarda a disco

Navegación entre pantallas:
  MainWindow tiene un QStackedWidget con 3 pantallas:
    - índice 0: ObservationScreen
    - índice 1: AdjustScreen
    - índice 2: PresentationScreen
  Se cambia con _switch_screen(idx) desde los botones del toolbar

################################################################################
# 4. DATACLASSES (store/state.py)
################################################################################

@dataclass
class Button:
    id: str          # UUID4 auto-generado
    label: str       # Nombre visible ("Pick & Roll")
    color: str       # Hex color ("#E8821A")
    hotkey: str      # Tecla de atajo ("P")
    pad_before: int  # Segundos antes del momento marcado (default -1 = usar default_pad)
    pad_after: int   # Segundos después (default -1 = usar default_pad)

@dataclass
class VideoSource:
    path: str            # Ruta absoluta al archivo de video
    name: str            # Nombre para mostrar
    last_position: float # Última posición del playhead (para restaurar)

@dataclass
class Clip:
    id: str          # UUID4
    name: str        # Nombre con número ("Poste #3")
    category: str    # Categoría base ("Poste") — para filtros en Adjust
    color: str       # Heredado del Button
    video_path: str  # De qué video proviene
    video_name: str  # Nombre del video fuente
    timestamp: str   # Momento formateado ("1:23:45")
    time_sec: float  # Momento en segundos
    start_sec: float # Inicio del clip (time_sec - pad_before)
    end_sec: float   # Fin del clip (time_sec + pad_after)
    note: str        # Nota del analista
    in_presentation: bool  # Si ya fue agregado a la presentación

    IMPORTANTE — name vs category:
      name = "Poste #3" (lo que ve el usuario, único)
      category = "Poste" (para agrupar en filtros)
      Siempre usar getattr(clip, 'category', clip.name) para filtros
      (compatibilidad con proyectos viejos que no tienen category)

@dataclass
class PresentationItem:
    id: str
    type: str            # "clip" o "image"
    name: str            # Nombre visible
    category: str        # Categoría base
    color: str
    note: str
    video_path: str
    start_sec: float
    end_sec: float
    transition: str      # "cut" o "fade"
    show_overlay: bool   # Mostrar nombre sobre el video
    visible: bool        # Si está habilitado en el render
    image_path: str      # Solo para type="image"
    image_dur: float     # Duración de la imagen en segundos

################################################################################
# 5. SIGNALS (store/state.py)
################################################################################

AppState emite estos signals:

  buttons_changed()        # Botonera modificada (add/remove/edit)
  clips_changed()          # Clips modificados (add/remove/edit)
  presentation_changed()   # Presentación activa modificada
  presentations_changed()  # Multi-pres (slots) modificados
  sources_changed()        # Videos fuente agregados/removidos
  active_source_changed(str, str)  # Cambio de video activo (path, name)
  project_changed(str)     # Nombre del proyecto cambió
  overlay_changed(bool)    # Toggle de overlay activado/desactivado
  toast_requested(str)     # Mostrar notificación
  undo_redo_changed(bool, bool)  # Estado de undo/redo (can_undo, can_redo)
  global_mute_changed(bool)      # Mute global (todos los players)

Autosave se conecta a:
  buttons_changed, clips_changed, presentation_changed,
  sources_changed, presentations_changed, overlay_changed

NO se conecta a (no son cambios de datos):
  active_source_changed, project_changed, toast_requested,
  undo_redo_changed, global_mute_changed

################################################################################
# 6. PANTALLA 1: OBSERVACIÓN (screens/observation.py)
################################################################################

Clase: ObservationScreen(QWidget)
Layout: QSplitter horizontal — sidebar izquierdo (180-400px) | panel derecho

SIDEBAR IZQUIERDO:
  - Header con botón "+" para agregar categorías
  - Botones de categorías (AddButtonDialog para crear)
  - Cada botón muestra: nombre, color, hotkey, badge con cantidad de clips
  - Configuración de botonera (nuevo, guardar, cargar)

PANEL DERECHO:
  - Tabs de videos fuente (hasta 10)
  - MpvWidget (reproductor de video)
  - Controles: play/pause, velocidad, volumen
  - ScrubBar (barra de posición)
  - Lista de "Registros" (clips del video actual)

FLUJO DE REGISTRO:
  1. User presiona botón (click o hotkey)
  2. → _register_clip(btn) → state.add_clip(btn, current_time)
  3. → add_clip() cuenta clips con misma categoría → auto-numera
  4. → "Poste #1", "Poste #2", etc.
  5. → clips_changed signal → _sync_clips() → UI se actualiza

AUTO-NUMERACIÓN:
  En state.add_clip():
    base_label = button.label  # "Poste"
    count = sum(1 for c in self.clips if c.category == base_label)
    display_name = f"{base_label} #{count + 1}"  # "Poste #3"
    clip = Clip(name=display_name, category=base_label, ...)

CONTEO EN BADGES:
  En observation.py _sync_buttons():
    count = sum(1 for c in state.clips
                if getattr(c, 'category', c.name) == btn.label)
  NUNCA usar c.name == btn.label (no matchea "Poste #1" con "Poste")

################################################################################
# 7. PANTALLA 2: AJUSTE (screens/adjust.py)
################################################################################

Clase: AdjustScreen(QWidget)
Layout: sidebar izquierdo (lista de clips) | panel derecho (video + timeline)

SIDEBAR:
  - Barra de filtro por categoría (usa clip.category, no clip.name)
  - Lista de clips con: nombre, timestamp, color, nota
  - Click en clip → carga en el reproductor

PANEL DERECHO:
  - MpvWidget con el clip seleccionado
  - ClipTimeline (timeline NLE con handlers de inicio/fin)
  - Controles: zoom, recenter, guardar nombre, nota, agregar a presentación

FILTRO:
  _rebuild_filter_bar():
    cats = list(dict.fromkeys(
        getattr(c, 'category', '') or c.name for c in state.clips
    ))
  _get_filtered():
    return [c for c in state.clips
            if (getattr(c, 'category', '') or c.name) == self._filter_cat]

NAVEGACIÓN DESDE PRESENTATION:
  app.py _goto_adjust(category):
    Busca el primer clip cuya category == category
    Cambia a pantalla Adjust y selecciona ese clip

################################################################################
# 8. TIMELINE (components/timeline.py)
################################################################################

Dos widgets:

ScrubBar: barra simple de posición (usada en Observation)
  - Click → seek
  - Drag → scrub

ClipTimeline: timeline NLE profesional (usado en Adjust)
  - Regla de tiempo con timestamps
  - Playhead vertical (línea roja)
  - Clip body con color del clip
  - Handlers de inicio y fin (triángulos arrastrables)
  - Zoom configurable (window_sec de 6 a 120 segundos)

MAGNETISMO:
  SNAP_PX = 10 (distancia en píxeles para snap)

  Handler drag (start/end):
    - El handler se pega al playhead cuando pasa a menos de SNAP_PX
    - El playhead NUNCA se mueve por interacción con handlers

  Body drag (clip entero):
    - Si el borde izquierdo o derecho del clip pasa cerca del playhead, se pega
    - Prioridad: primero chequea start, después end

  Regla click:
    - Click en la regla (arriba) → seek inmediato al punto clickeado
    - Esto SÍ mueve el playhead

  REGLA CRÍTICA:
    El playhead SOLO se mueve por:
      1. Click en la regla
      2. Click en el playhead y drag
      3. Reproducción normal del video
    NUNCA se mueve por interacción con handlers o body del clip

MOUSE EVENTS:
  mousePressEvent:
    - _hit_test() detecta qué se tocó: 'start', 'end', 'body', 'playhead', None
    - Si es 'playhead' → seek inmediato
  mouseMoveEvent:
    - Drag según qué se está arrastrando
    - Aplica magnetismo al playhead
    - Emite start_changed o end_changed signals
  mouseReleaseEvent:
    - Solo limpia self._dragging = None
    - NO mueve el playhead (esto era un bug anterior)

################################################################################
# 9. PANTALLA 3: PRESENTACIÓN (screens/presentation.py)
################################################################################

Clase: PresentationScreen(QWidget)
Clases auxiliares: RenderThread, RenderProgressDialog, RenderSettingsDialog,
                   ClipDetailDialog, PresentationRow, TableHeader,
                   PresSlotWidget, MultiPresBox

LAYOUT:
  - MultiPresBox arriba (selector de hasta 5 presentaciones)
  - TableHeader (columnas redimensionables)
  - Lista de items (drag-and-drop para reordenar)
  - Panel de estadísticas (total clips, duración, imágenes)
  - Botón "Crear película" → RenderSettingsDialog → render

MULTI-PRESENTACIÓN:
  - Hasta 5 slots (presentaciones independientes)
  - Cada slot tiene nombre editable
  - state.presentations = lista de listas
  - state.active_pres_idx = índice del slot activo
  - state.presentation = alias de presentations[active_pres_idx]
  - _sync_active_slot() mantiene el alias sincronizado

RENDER:
  - RenderSettingsDialog: resolución, CRF, FPS, transición, audio
  - RenderThread(QThread): ejecuta render en background
  - Cancelación: flag _cancelled + InterruptedError en callback
  - NO usar QThread.terminate() — deja procesos zombie
  - FFmpeg genera MP4 con filter_complex + concat + xfade

RENDER SEPARADO:
  - Opción de exportar cada clip como archivo individual
  - Exporta a Documentos/PyScout/Exportados/

################################################################################
# 10. VIDEO PLAYER (components/video_player.py)
################################################################################

Clase: MpvWidget(QWidget)
Motor: libmpv via python-mpv

IMPORT SEGURO:
  try:
      import mpv
  except Exception:
      mpv = None
  Si mpv es None, el widget se crea pero no reproduce (muestra pantalla negra)

INIT:
  Windows: vo="gpu", hwdec="auto"
  Mac: vo="libmpv", hwdec="auto-safe"

SIGNALS:
  duration_changed(float)  # Cuando se carga un video
  position_changed(float)  # Cada ~83ms (12fps de actualización)
  file_loaded()            # Video listo para reproducir
  playback_started()
  playback_paused()

MUTE GLOBAL:
  state.global_mute_changed signal → _on_global_mute()
  Cada MpvWidget se conecta al signal al inicializarse
  Toggle desde el toolbar de MainWindow

CLOSEEVENT:
  Protegido con hasattr para _ui_timer y getattr para _player
  (ambos pueden ser None si libmpv no cargó)

################################################################################
# 11. LAUNCHER / START DIALOG (components/dialogs.py)
################################################################################

Clase: StartDialog(QDialog)

DISEÑO: Estilo Adobe — bordes rectos, accent line dorado, fondo gradiente oscuro
  - Header: logo + "PYSCOUT" + subtítulo
  - Contenido: 2 columnas (acciones izq | recientes der)
  - Barra de licencia: abajo (estado + activar + comprar)
  - Ventana frameless, arrastrable, con botón X

LICENCIA EN EL LAUNCHER:
  _load_license():
    - Llama check_license() del license_manager
    - Si es "no_license" → auto-start trial con start_trial()
    - Tipos: pro, trial, grace, expired, wrong_pc, tampered, corrupted, dev
  _build_license_bar():
    - Punto de color + texto de estado
    - Botón "Activar licencia" → expande input + botón Activar
    - Botón "Comprar" → abre URL de Polar checkout
  _tick():
    - Timer cada 1s para trial/grace
    - Decrementa contador, actualiza label
    - Cuando llega a 0 → _load_license() + _apply_license_permissions()
  _apply_license_permissions():
    - Habilita/deshabilita Nuevo, Abrir, y todos los Recientes
    - Pro/dev → todo habilitado
    - Expired/tampered/wrong_pc → todo deshabilitado

NUEVO PROYECTO (modal, no File Explorer):
  _action_new():
    1. QDialog frameless con input de nombre
    2. Sin botón X (solo Cancelar o Crear)
    3. Enter funciona como Crear
    4. Sanitiza nombre para filename
    5. Crea en Documentos/PyScout/Proyectos/{nombre}.scout
    6. Si ya existe, agrega (1), (2), etc.
    7. Emite project_selected signal → MainWindow._create_new_project()
    8. El archivo .scout se crea INMEDIATAMENTE (no espera a que el user guarde)

RECIENTES:
  - Lee de QSettings("ScoutApp", "prefs") → "recent_projects"
  - Filtra archivos que ya no existen
  - Los QLabel dentro del QPushButton tienen WA_TransparentForMouseEvents
  - clicked.connect usa lambda checked=False, p=path (para evitar que
    la señal pase checked como path)

################################################################################
# 12. AUTOSAVE Y PERSISTENCIA (app.py)
################################################################################

AUTOSAVE:
  - Conectado a: buttons_changed, clips_changed, presentation_changed,
    sources_changed, presentations_changed, overlay_changed
  - Guarda a self._current_path si existe
  - _autosave_locked evita guardar durante load/create

CREAR PROYECTO NUEVO:
  _create_new_project(path):
    1. Limpia todo el estado (buttons, clips, presentations)
    2. Crea el archivo .scout inmediatamente con state.save_to_file(path)
    3. Setea _current_path → autosave funciona desde el primer cambio
    4. Agrega a recientes
    5. Emite todas las signals para refrescar UI

SAVE ATÓMICO:
  state.save_to_file(path):
    1. Serializa a JSON
    2. Escribe a path.tmp
    3. fsync()
    4. os.replace(tmp, path) — atómico en la mayoría de OS
    Si crashea durante escritura, el .scout original queda intacto

TÍTULO DINÁMICO:
  _on_project_changed(name):
    self.setWindowTitle(f"{name} — PyScout" if name else "PyScout")

CARPETAS EN DOCUMENTOS:
  main.py _ensure_project_folders():
    Crea Documentos/PyScout/ con: Proyectos, Botoneras, Presentaciones, Exportados
  app.py _docs_folder(sub):
    Helper que devuelve la ruta a cualquier subcarpeta
  Todos los FileDialog abren en la subcarpeta correspondiente

################################################################################
# 13. UNDO/REDO (store/state.py)
################################################################################

SISTEMA:
  - _undo_stack: lista de snapshots (hasta 50)
  - _redo_stack: lista de snapshots
  - push_undo(): guarda snapshot actual antes de cada mutación
  - undo(): restaura desde _undo_stack, guarda actual en _redo_stack
  - redo(): restaura desde _redo_stack, guarda actual en _undo_stack

SNAPSHOT INCLUYE:
  - buttons (lista completa)
  - clips (lista completa)
  - presentations (TODAS las presentaciones, no solo la activa)
  - active_pres_idx (índice del slot activo)

_restore_snapshot():
  - Restaura buttons, clips
  - Restaura presentations + active_pres_idx
  - Recalcula presentation = presentations[active_pres_idx]
  - Emite: buttons_changed, clips_changed, presentation_changed,
    presentations_changed

MÉTODOS QUE HACEN PUSH_UNDO:
  add_button, remove_button, add_clip, add_clip_to_presentation,
  add_image_to_presentation, remove_pres_item, reorder_presentation,
  update_pres_item (solo si algo cambió realmente)

_sync_active_slot():
  Helper que mantiene presentations[active_pres_idx] = presentation
  Se llama desde: remove_pres_item, reorder_presentation, update_pres_item

################################################################################
# 14. SISTEMA DE LICENCIAS (utils/license_manager.py)
################################################################################

PROVEEDOR: Polar.sh
  ORG_ID: a3608077-32b8-47d8-a701-8572f59ff9fd
  PRODUCT_ID: 9109ea62-ae1c-4548-8820-761e589ab8e2
  CHECKOUT_URL: https://buy.polar.sh/polar_cl_sW9U1zjSOQZ7vhN4JzRPyrLJyy4q7VKz8IE6N0CQfvq

TRIAL: 7 días (TRIAL_SECONDS = 7 * 86400)
GRACE: 0 segundos (configurable)
PRECIO: $3 USD/mes

ALMACENAMIENTO — 5 ARCHIVOS + REGISTRO:
  Windows:
    1. %APPDATA%/PyScout/.pyscout_license.dat
    2. %LOCALAPPDATA%/PyScout/.ps_cache.dat
    3. %PROGRAMDATA%/PyScout/.ps_sys.dat
    4. %USERPROFILE%/.pyscout/.config.dat
    5. %APPDATA%/Microsoft/Protect/.ps_pref.dat
    6. Registro: HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\{7A3F2B1C-...}
       Valor: "InstallDate" (nombre inocuo que se mezcla con claves del sistema)
  Mac:
    1. ~/Library/Application Support/PyScout/.pyscout_license.dat
    2. ~/Library/Preferences/.pyscout_pref.dat
    3. ~/Library/Caches/PyScout/.ps_cache.dat
    4. ~/.pyscout/.config.dat
    5. ~/Library/Logs/PyScout/.ps_sys.dat

CIFRADO:
  - Clave derivada del HWID: sha256(BASE_KEY + HWID)[:20]
  - Cada máquina tiene clave diferente → .dat de una PC no sirve en otra
  - XOR con la clave derivada + base64
  - Formato en disco: "checksum:data" donde checksum = sha256(data)[:16]
  - Si alguien edita el .dat, el checksum no coincide → _load() lo ignora

HARDWARE ID:
  get_hwid():
    Combina: MAC address + CPU processor + volumen serial (Windows) o
    serial number (Mac) o machine-id (Linux)
    sha256 → 16 chars uppercase

ANTI-TAMPER:
  - Si borrás 1 archivo, _load() lo restaura desde los otros 4
  - Trial usa el trial_start MÁS ANTIGUO entre todas las copias
  - start_trial() verifica que no exista trial previo antes de crear uno nuevo
  - Heartbeat: cada check actualiza last_check. Si el reloj retrocedió >2h,
    incrementa clock_tamper. Con 3 strikes → bloqueado

API POLAR — ENDPOINTS PÚBLICOS (no necesitan OAT):
  POST /customer-portal/license-keys/activate
    - Consume 1 slot de activación
    - Requiere "Limit activations" habilitado en el Benefit de Polar
    - label: "PyScout-{HWID}"
    - Respuesta 200: {"id": "activation-uuid", "license_key": {...}}
    - Respuesta 403: "License key activation limit already reached"

  POST /customer-portal/license-keys/validate
    - Verifica la clave (con activation_id opcional)
    - NO consume slot
    - Respuesta 200: {"status": "granted", "activation": {...}}

  POST /customer-portal/license-keys/deactivate
    - Libera 1 slot de activación
    - Requiere activation_id

FLUJOS:
  Primera vez:
    check_license() → "no_license" → StartDialog llama start_trial()
    → crea .dat con type="trial" + trial_start

  Activación:
    activate_license(key):
      1. polar_validate(key) → verificar que la clave existe
      2. Si ya hay activation_id local para esta key+HWID → revalidar
      3. Si no → polar_activate(key) → consume 1 slot
      4. Si LIMIT_REACHED → rechazar con mensaje claro
      5. Si activate no es necesario (benefit sin limit) → solo validate
      6. Guardar .dat con type="pro" + activation_id

  Cada apertura:
    check_license():
      - Lee .dat → verifica HWID, clock_tamper
      - Si pro: recheck cada 7 días con polar_validate
      - Si trial: verifica que no hayan pasado TRIAL_SECONDS
      - Si sin internet y pro: tolera hasta 30 días offline

  Cancelación:
    - User cancela suscripción en Polar
    - Polar revoca la clave
    - Próximo recheck: validate devuelve "revoked" → expired

  Mudar de equipo:
    deactivate_license():
      - polar_deactivate(key, activation_id) → libera slot
      - Borra todos los .dat locales
      - El user puede activar en otro equipo

CONFIGURACIÓN PENDIENTE EN POLAR:
  - Habilitar "Limit activations" en el Benefit (sin esto, infinitos dispositivos)

################################################################################
# 15. FFMPEG (utils/ffmpeg.py)
################################################################################

get_ffmpeg(): Busca ffmpeg.exe en: sys._MEIPASS (PyInstaller), raíz del proyecto,
  Homebrew (Mac), PATH del sistema

get_ffprobe(): Busca ffprobe junto a ffmpeg

has_audio(path): Usa ffprobe para verificar si un video tiene stream de audio
  Si no tiene → render usa anullsrc (genera silencio)

render_presentation(items, output_path, ...):
  - Genera filter_complex con todos los clips
  - Videos sin audio: anullsrc con la duración del clip
  - Transiciones: "cut" (directo) o "fade" (xfade)
  - Overlay: drawtext con el nombre del clip
  - Resolución: configurable (default 1920x1080)
  - CRF: configurable (default 23)
  - Audio: AAC 192k o mute (-an)

extract_frames(): Extrae frames como imágenes (para canvas/preview)
delete_frame_dir(): Limpia directorio temporal de frames

################################################################################
# 16. TEMA VISUAL (styles/theme.py)
################################################################################

PALETA:
  Fondos: BG0=#0C0C0E  BG1=#111115  BG2=#18181D  BG3=#1F1F26  BG4=#26262F
  Acento: ACCENT=#C9A44A  ACCENT2=#A8852E  ACCENT3=#E0BB6A
  Texto:  TEXT0=#F0EDE8  TEXT1=#C4BEB5  TEXT2=#7A7570  TEXT3=#3E3C3A
  Bordes: BORDER=rgba(255,252,248,0.05)  BORDER2=rgba(255,252,248,0.09)
  Danger: #C0392B   Green: #27AE60

FONT SCALE:
  fs(size) multiplica el tamaño por _font_scale (default 1.0)
  Configurable desde Preferencias en el menú

build_style(): genera el stylesheet CSS global para toda la app

################################################################################
# 17. REGLAS DE CÓDIGO
################################################################################

PySide6:
  - QAction está en PySide6.QtGui, NO en QtWidgets
  - Signals son Signal (no pyqtSignal)
  - file_loaded signal acumula conexiones — siempre disconnect() antes de connect()
  - setStyleSheet() sin selector propaga a TODOS los children
  - mousePressEvent = lambda e: e.accept() ROMPE clicked de QPushButton
  - QImage.bits() devuelve memoryview — usar bytes(img.constBits())

Fuentes:
  - Usar fs(n) siempre, nunca hardcodear px

Clips:
  - Filtros SIEMPRE por getattr(clip, 'category', clip.name)
  - Nunca c.name == btn.label para contar (no matchea "Poste #1" con "Poste")

State:
  - push_undo() ANTES de mutar cualquier lista
  - _sync_active_slot() después de mutar presentation
  - save_to_file() es atómico (.tmp → fsync → os.replace)

Videos:
  - import mpv protegido con try/except
  - closeEvent protegido con hasattr/_ui_timer y getattr/_player
  - has_audio() antes de generar filtros de audio en FFmpeg

Licencias:
  - winreg importado condicionalmente: if sys.platform == "win32": try: import winreg
  - NUNCA referenciar winreg antes de importarlo
  - Clave derivada del HWID, no estática

Cancelación de render:
  - Flag _cancelled + InterruptedError en callback
  - NUNCA QThread.terminate()

Carpetas:
  - Documentos/PyScout/ con: Proyectos, Botoneras, Presentaciones, Exportados
  - FileDialogs abren en la subcarpeta correspondiente

Título de ventana:
  - "NombreProyecto — PyScout"
  - Se actualiza via _on_project_changed()

Nuevo proyecto:
  - Modal con input de nombre, NO explorador de Windows
  - Crea archivo .scout INMEDIATAMENTE
  - Autosave activo desde el primer cambio

################################################################################
# 18. BUILDS Y DISTRIBUCIÓN
################################################################################

PYINSTALLER (desarrollo):
  python -m PyInstaller --name PyScout --onedir --windowed --icon=ico.ico \
    --add-data "ico.ico;." --add-data "ico_4k.png;." --add-data "splash.png;." \
    --add-data "icons;icons" --add-data "fonts;fonts" --add-data "libmpv-2.dll;." \
    --hidden-import=PySide6 --hidden-import=PySide6.QtCore \
    --hidden-import=PySide6.QtGui --hidden-import=PySide6.QtWidgets \
    --hidden-import=PySide6.QtSvg --hidden-import=requests \
    --hidden-import=store.state --hidden-import=screens.observation \
    --hidden-import=screens.adjust --hidden-import=screens.presentation \
    --hidden-import=components.video_player --hidden-import=components.toast \
    --hidden-import=components.timeline --hidden-import=utils.license_manager \
    --hidden-import=utils.resource_paths --hidden-import=utils.theme_helpers \
    --hidden-import=styles.theme main.py

  NO usar --collect-all=PySide6 (incluye módulos 3D, WebEngine, etc. — 500MB+)

NUITKA (producción):
  python -m nuitka --standalone --enable-plugin=pyside6 \
    --windows-icon-from-ico=ico.ico --windows-console-mode=disable \
    --include-data-files=ico.ico=ico.ico \
    --include-data-files=ico_4k.png=ico_4k.png \
    --include-data-files=splash.png=splash.png \
    --include-data-files=libmpv-2.dll=libmpv-2.dll \
    --include-data-dir=icons=icons --include-data-dir=fonts=fonts \
    --output-dir=build main.py

  Primera vez: descarga compilador C (~400MB), tarda 15-30 min
  Puede necesitar Python 3.12 (3.14 es muy nuevo para Nuitka)

INNO SETUP:
  Archivo: installer.iss
  Imágenes: lateral.png (164x314), chica.png (55x58)
  Idiomas: español + inglés
  Instala en: %APPDATA%\PyScout (sin admin)
  Compilar: "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
  Resultado: dist/PyScout-Setup.exe

CHECKLIST PRE-RELEASE:
  [ ] TRIAL_SECONDS = 7 * 86400
  [ ] "Limit activations" habilitado en Polar
  [ ] Probado .exe desde dist/PyScout/
  [ ] Probado instalador en PC limpia
  [ ] Trial funciona
  [ ] Activación con Polar funciona
  [ ] Licencia persiste al cerrar/abrir
  [ ] FFmpeg exporta correctamente
  [ ] Videos se reproducen (libmpv)
  [ ] Archivos muertos borrados

################################################################################
# 19. PENDIENTES PRIORIZADOS
################################################################################

INMEDIATOS (antes del curso):
  1. Habilitar "Limit activations" en Polar
  2. Borrar archivos muertos
  3. Compilar con Nuitka
  4. Probar en PC limpia
  5. Generar keys para alumnos

CORTO PLAZO (mes 1):
  6. Debounce en autosave (timer 500ms)
  7. Logging a archivo (Documentos/PyScout/pyscout.log)
  8. Página web con paleta de la app

MEDIANO PLAZO (mes 2-3):
  9. Modo fullscreen en Ajustes (timeline mini + sidebar mini)
  10. GitHub + CI/CD
  11. Supabase + Polar (dashboard admin de licencias)
  12. Certificado de firma de código (eliminar SmartScreen)

################################################################################
# 20. HISTORIAL DE SESIONES DE DESARROLLO
################################################################################

Sesión 1 (abril 2026):
  - Creación de la app desde cero
  - SVG icons, screens, canvas NLE
  - Column resize, auto-numbering, render settings

Sesión 2 (abril 2026):
  - Canvas YOLO detection, trapezoid removal
  - StartDialog redesign, global mute
  - Mac compatibility, license system (Polar)
  - Distribution (PyInstaller/Inno Setup)
  - Security hardening, responsive layout
  - Timeline magnetism, autosave, auto-numbering
  - Full code audit

Sesión 3 (mayo 2026):
  - Migración de Lemon Squeezy a Polar.sh completa
  - Fix de recientes clickeables (WA_TransparentForMouseEvents)
  - StartDialog arrastrable + licencia integrada
  - 12 flujos de licencia cubiertos
  - 5 archivos redundantes + registro Windows
  - Clave derivada del HWID + checksum SHA256
  - Registro oculto en Uninstall GUID
  - Fix winreg import condicional
  - P0 del code review: undo/redo, presentation sync, atomic save
  - FFmpeg: has_audio + anullsrc fallback
  - RenderThread: cancelación limpia sin terminate()
  - video_player: safe import mpv + closeEvent guards
  - Observation responsive con QSplitter
  - Título dinámico en barra de tareas
  - Nuevo proyecto: modal con input, crea archivo inmediatamente
  - Carpetas en Documentos/PyScout/
  - FileDialogs abren en subcarpetas
  - Conteo de clips por category
  - Eliminado badge "Pro" del titlebar
  - Eliminado menú "Activar licencia"
  - Body drag con magnetismo al playhead
  - SNAP_PX restaurado a 10
  - Playhead nunca atraído por handlers

################################################################################
# 21. MÉTODOS CRÍTICOS — REFERENCIA DETALLADA
################################################################################

# ── state.py ──────────────────────────────────────────────────────────────────

add_clip(button, time_sec):
  1. push_undo()
  2. Calcula pad_before y pad_after (del botón o default_pad)
  3. Cuenta clips existentes con misma category → auto-numera
  4. Crea Clip con name="Label #N", category="Label"
  5. Append a self.clips
  6. Emite clips_changed
  7. Emite toast con nombre y timestamp

add_clip_to_presentation(clip, clip_start, clip_dur):
  1. push_undo()
  2. Crea PresentationItem con category=clip.category (no clip.name)
  3. Append a presentations[active_pres_idx]
  4. Sincroniza self.presentation = presentations[active_pres_idx]
  5. clip.in_presentation = True
  6. Emite presentation_changed + presentations_changed

remove_pres_item(item_id):
  1. push_undo()
  2. Filtra la lista quitando el item
  3. _sync_active_slot()
  4. Emite presentation_changed

reorder_presentation(from_idx, to_idx):
  1. push_undo()
  2. Pop + insert en la lista
  3. _sync_active_slot()
  4. Emite presentation_changed

update_pres_item(item_id, **kwargs):
  1. Busca el item por id
  2. Verifica si algo REALMENTE cambió (evita undo innecesario)
  3. Si cambió: push_undo() → setattr de cada kwarg → _sync_active_slot()
  4. Emite presentation_changed

save_to_file(path):
  1. Serializa todo a dict con to_dict()
  2. Crea directorio padre si no existe
  3. Escribe a path.tmp
  4. fsync() para forzar flush a disco
  5. os.replace(tmp, path) — operación atómica
  6. Si falla, intenta limpiar el .tmp

load_from_file(path):
  1. Lee JSON del archivo
  2. Reconstruye buttons, clips, presentation desde dicts
  3. Restaura presentations + active_pres_idx
  4. Retorna True/False

to_dict():
  Serializa: project_name, default_pad, overlay_enabled,
  buttons, video_sources, clips, presentations, active_pres_idx

# ── app.py ────────────────────────────────────────────────────────────────────

_create_new_project(path):
  1. Lock autosave
  2. Limpiar buttons, video_sources, clips, presentation
  3. Reset presentations = [[]], active_pres_idx = 0
  4. Unlock autosave
  5. Set project_name del basename
  6. os.makedirs del directorio padre
  7. state.save_to_file(path) — CREA EL ARCHIVO INMEDIATAMENTE
  8. Set _current_path → autosave funciona desde ahora
  9. Agrega a recientes
  10. Emite todos los signals para refrescar UI

_autosave():
  1. Si _autosave_locked → return
  2. Si _current_path existe → save_to_file(_current_path)
  3. Si no, busca _autosave_path (temporal)
  4. Si no hay ninguno → no guarda (no debería pasar)

_load_project_path(path):
  1. Si el archivo existe → cargar con state.load_from_file(path)
  2. Si NO existe → _create_new_project(path)
  (Esto permite que StartDialog emita un path nuevo que aún no existe)

# ── license_manager.py ────────────────────────────────────────────────────────

_save(data):
  1. Cifra data con _enc()
  2. Genera checksum SHA256 de los datos cifrados
  3. Escribe "checksum:data" en cada uno de los 5 archivos
  4. Si es Windows, también escribe en el registro

_load():
  1. Lee de los 5 archivos + registro
  2. Verifica checksum de cada uno (ignora los que no coinciden)
  3. Si hay un "pro", lo usa y restaura en todos los demás
  4. Si hay trials, usa el trial_start más antiguo (más restrictivo)
  5. Si faltan copias, las restaura desde las que existen

check_license():
  1. _load() datos
  2. Verifica HWID (wrong_pc si no coincide)
  3. Verifica clock_tamper (tampered si ≥ 3)
  4. _heartbeat() — actualiza last_check, detecta reloj atrás
  5. Si pro: recheck cada 7 días con polar_validate
  6. Si pro offline: tolera hasta 30 días sin validación
  7. Si trial: calcula elapsed desde trial_start
  8. Retorna (válido, segundos_restantes, tipo)

activate_license(key):
  1. Validar que la clave existe (polar_validate sin activation_id)
  2. Si ya hay activation_id local para esta key+HWID → revalidar
  3. Si no → polar_activate (consume slot)
  4. Si LIMIT_REACHED → mensaje claro de "otro dispositivo"
  5. Si activate no necesario (benefit sin limit) → solo validate
  6. Guardar como pro con activation_id

# ── ffmpeg.py ─────────────────────────────────────────────────────────────────

render_presentation(items, output_path, ...):
  1. Genera inputs (-i para cada video)
  2. Para cada clip: trim filter + scale + fps
  3. Si tiene audio: aformat filter
  4. Si NO tiene audio: anullsrc (genera silencio)
  5. Si transición="fade": xfade entre clips
  6. Si transición="cut": concat directo
  7. Si show_overlay: drawtext con nombre del clip
  8. Ejecuta FFmpeg con subprocess
  9. Parsea progreso vía stderr (time=HH:MM:SS)
  10. Llama progress_cb con el timestamp (que puede lanzar
      InterruptedError si se canceló)

# ── timeline.py ───────────────────────────────────────────────────────────────

_hit_test(x, y):
  Detecta qué elemento se tocó:
  - 'start': handle izquierdo (triángulo)
  - 'end': handle derecho
  - 'body': cuerpo del clip (entre handlers)
  - 'playhead': línea del playhead
  - None: regla u otro lugar

mouseMoveEvent (dragging == 'body'):
  1. Calcula desplazamiento en porcentaje
  2. Mueve start_pct y end_pct manteniendo el ancho
  3. Magnetismo: si start o end está a menos de SNAP_PX del playhead → snap
  4. Emite start_changed + end_changed

mouseMoveEvent (dragging == 'start' o 'end'):
  1. Calcula nuevo porcentaje del handler
  2. Magnetismo: si está a menos de SNAP_PX del playhead → snap
  3. Seek al punto del handler
  4. Emite start_changed o end_changed

################################################################################
# 22. ERRORES COMUNES Y SOLUCIONES
################################################################################

ERROR: "name 'winreg' is not defined"
  CAUSA: import winreg antes de verificar plataforma
  FIX: if sys.platform == "win32": try: import winreg

ERROR: "No module named 'PySide6'" en el .exe
  CAUSA: PyInstaller no incluyó PySide6
  FIX: agregar --hidden-import=PySide6 --hidden-import=PySide6.QtCore etc.

ERROR: "Módulo de licencias no encontrado"
  CAUSA: app.py importaba components.license_dialog que no existía
  FIX: eliminado badge Pro y menú Activar licencia de app.py

ERROR: Conteo de clips siempre en 0
  CAUSA: c.name == btn.label no matchea "Poste #1" con "Poste"
  FIX: getattr(c, 'category', c.name) == btn.label

ERROR: Playhead se mueve al hacer click en handler
  CAUSA: mouseReleaseEvent movía playhead a la posición del handler
  FIX: mouseReleaseEvent solo hace self._dragging = None

ERROR: FFmpeg falla con "No audio stream"
  CAUSA: Video sin stream de audio
  FIX: has_audio() + anullsrc fallback

ERROR: "Archivo de licencia dañado"
  CAUSA: .dat cifrado con clave anterior (antes de derivar del HWID)
  FIX: python utils/license_manager.py limpiar

ERROR: Proyecto nuevo no guarda
  CAUSA: _current_path no se seteaba hasta que el user guardaba manualmente
  FIX: _create_new_project() crea el archivo y setea _current_path inmediatamente

ERROR: Trial se resetea al borrar un archivo
  CAUSA: solo había 1 archivo de licencia
  FIX: 5 archivos + registro + _load() restaura desde los que quedan

################################################################################
# FIN DEL DOCUMENTO
################################################################################
