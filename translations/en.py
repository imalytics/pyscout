"""
translations/en.py — English translations for PyScout.
To add a new language, copy this file and translate the VALUES (never the keys).
"""

STRINGS: dict[str, str] = {

    # ── app.py — navigation ───────────────────────────────────────────────
    "Observación": "Observation",
    "Ajuste": "Adjust",
    "Presentación": "Presentation",
    "↩ Deshacer": "↩ Undo",
    "Rehacer ↪": "Redo ↪",

    # ── File menu ─────────────────────────────────────────────────────────
    "Archivo": "File",
    "Nuevo proyecto": "New project",
    "Abrir proyecto...": "Open project...",
    "Recientes": "Recent",
    "Guardar": "Save",
    "Guardar como...": "Save as...",
    "Limpiar recientes": "Clear recent",

    # ── Options menu ──────────────────────────────────────────────────────
    "Opciones": "Options",
    "Activar autoguardado": "Enable autosave",
    "Silenciar todos los videos": "Mute all videos",
    "Silenciar video final por defecto": "Mute final video by default",
    "Tamaño del texto": "Text size",
    "Normal (100%)": "Normal (100%)",
    "Grande (150%)": "Large (150%)",
    "Muy grande (200%)": "Extra large (200%)",

    # ── Button board menu ─────────────────────────────────────────────────
    "Botonera": "Button board",
    "Nueva botonera": "New button board",
    "Abrir botonera...": "Open button board...",
    "Guardar botonera...": "Save button board...",

    # ── Window menu ───────────────────────────────────────────────────────
    "Ventana": "Window",
    "Pantalla completa": "Full screen",
    "Restaurar disposición": "Restore layout",

    # ── Settings menu ─────────────────────────────────────────────────────
    "Configuraciones": "Settings",
    "Buscar actualizaciones": "Check for updates",
    "Instalar códecs": "Install codecs",

    # ── Help menu ─────────────────────────────────────────────────────────
    "Ayuda": "Help",
    "¿Cómo funciona?": "How does it work?",
    "Reiniciar tour de bienvenida": "Restart welcome tour",
    "Feedback": "Feedback",
    "Acerca de PyScout": "About PyScout",

    # ── Project dialogs ───────────────────────────────────────────────────
    "¿Guardás el proyecto actual?": "Save the current project?",
    "Sin guardar": "Don't save",
    "Cancelar": "Cancel",
    "Nombre del proyecto:": "Project name:",
    "Sin título": "Untitled",
    "Guardar proyecto": "Save project",
    "Abrir proyecto": "Open project",

    # ── Button board dialogs ──────────────────────────────────────────────
    "Esto eliminará los {} botones actuales.": "This will delete the {} current buttons.",
    "Continuar": "Continue",
    "Guardar botonera": "Save button board",
    "Abrir botonera": "Open button board",
    "Ya tenés {} botones. ¿Reemplazar o agregar?": "You have {} buttons. Replace or add?",
    "Reemplazar": "Replace",
    "Agregar": "Add",

    # ── Toasts ────────────────────────────────────────────────────────────
    "Guardado": "Saved",
    '"{}" guardado': '"{}" saved',
    '"{}" cargado': '"{}" loaded',
    'Proyecto "{}" creado': 'Project "{}" created',
    "Botonera vacía": "Empty button board",
    "Botonera guardada ({} botones)": "Button board saved ({} buttons)",
    "Modo silencio activado": "Mute mode on",
    "Audio activado": "Audio on",
    "Preferencias restablecidas": "Preferences reset",
    "Escala: {}%": "Scale: {}%",
    "Archivo no encontrado": "File not found",
    "Idioma": "Language",
    "Reiniciá la app para aplicar el idioma": "Restart the app to apply the language",

    # ── Help / About dialogs ──────────────────────────────────────────────
    "¿Cómo funciona PyScout?": "How does PyScout work?",
    "CONTENIDO": "CONTENTS",
    "Flujo de trabajo": "Workflow",
    "1. Observación": "1. Observation",
    "2. Ajuste": "2. Adjust",
    "3. Presentación": "3. Presentation",
    "Atajos de teclado": "Keyboard shortcuts",
    "Preguntas frecuentes": "FAQ",
    "Versión": "Version",
    "Desarrollado por": "Developed by",

    # ── Update dialog ─────────────────────────────────────────────────────
    "Nueva versión disponible": "New version available",
    "Descargar ahora": "Download now",
    "Más tarde": "Later",

    # ── components/dialogs.py — ClipEditDialog ────────────────────────────
    "Editar clip": "Edit clip",
    "NOMBRE DEL CLIP": "CLIP NAME",
    "COLOR": "COLOR",
    "NOTA": "NOTE",
    "Agregar nota...": "Add note...",
    "Guardar": "Save",

    # ── StartDialog ───────────────────────────────────────────────────────
    "RECIENTES": "RECENT",
    "Crear proyecto": "New project",
    # ── components/onboarding.py — tour UI ───────────────────────────────────
    "PASO {} DE {}": "STEP {} OF {}",
    "Finalizar": "Finish",
    "Siguiente  →": "Next  →",

    # ── Onboarding tour steps ─────────────────────────────────────────────────
    "Bienvenido a PyScout": "Welcome to PyScout",
    "Este tour rápido te muestra las 3 pantallas y las funciones clave. "
    "Avanzá con Siguiente o saltealo con ✕.":
        "This quick tour shows you the 3 main screens and key features. "
        "Press Next to advance or ✕ to skip.",
    "Hacé clic aquí para cargar el video del partido. "
    "Podés tener hasta 10 videos abiertos al mismo tiempo, cada uno en su pestaña.":
        "Click here to load the match video. "
        "You can have up to 10 videos open at once, each in its own tab.",
    "Crear botones de categoría": "Create category buttons",
    "Con el '+' creás un botón por tipo de jugada: PNR, Transición, Tiro libre... "
    "Asignales color y tecla de atajo para registrar sin mouse.":
        "Use '+' to create a button for each play type: PNR, Transition, Free throw... "
        "Assign a color and a hotkey to record without using the mouse.",
    "Pantalla Ajuste": "Adjust screen",
    "Cuando tengas registros, pasá a Ajuste para afinar el inicio y fin "
    "de cada clip con el timeline interactivo.":
        "Once you have records, go to Adjust to fine-tune the start and end "
        "of each clip with the interactive timeline.",
    "Aquí aparecerán tus registros": "Your records will appear here",
    "Cada clip marcado en Observación se lista aquí. "
    "Seleccioná uno y ajustá sus bordes en el timeline.":
        "Every clip marked in Observation is listed here. "
        "Select one and adjust its edges on the timeline.",
    "Pantalla Presentación": "Presentation screen",
    "Desde Ajuste, enviás clips a Presentación para construir el video final.":
        "From Adjust, you send clips to Presentation to build the final video.",
    "Aquí aparecerán tus clips": "Your clips will appear here",
    "Los clips de tu presentación se listan aquí. "
    "Arrastrá las filas para reordenarlos.":
        "Your presentation clips are listed here. "
        "Drag rows to reorder them.",
    "Intercalar imágenes": "Insert images",
    "Agregá imágenes estáticas —pizarrones, diagramas— entre los clips "
    "para enriquecer tu presentación táctica.":
        "Add static images —whiteboards, diagrams— between clips "
        "to enrich your tactical presentation.",
    "Producí un MP4 con todos los clips concatenados, listo para el equipo. "
    "Elegís resolución, calidad, transiciones y si incluir audio.":
        "Produce an MP4 with all clips concatenated, ready for your team. "
        "Choose resolution, quality, transitions, and whether to include audio.",
    "Autoguardado y deshacer": "Autosave and undo",
    "Cada cambio se guarda automáticamente. "
    "Ctrl+Z deshace cualquier acción. "
    "Usá F11 para pantalla completa durante las presentaciones.":
        "Every change is saved automatically. "
        "Ctrl+Z undoes any action. "
        "Use F11 for full screen during presentations.",

    # ── components/feedback.py ────────────────────────────────────────────────
    "Tu opinión": "Your feedback",
    "¿Cómo quedó tu película?": "How did your movie turn out?",
    "¿Cómo vas con PyScout?": "How are you finding PyScout?",
    "Tu feedback nos ayuda a mejorar.": "Your feedback helps us improve.",
    "SUGERENCIAS (OPCIONAL)": "SUGGESTIONS (OPTIONAL)",
    "¿Qué mejorarías? ¿Qué extrañás? ¿Qué funciona perfecto?":
        "What would you improve? What's missing? What works great?",
    "Ahora no": "Not now",
    "Enviar feedback": "Send feedback",
    "Muy malo": "Very bad",
    "Malo": "Bad",
    "Regular": "Average",
    "Bueno": "Good",
    "¡Excelente!": "Excellent!",

    # ── app.py — What's new ───────────────────────────────────────────────────
    "Novedades": "What's new",
    "¡PyScout actualizado!": "PyScout updated!",
    "Esto es lo que hay de nuevo en esta versión:": "Here's what's new in this version:",
    "Entendido": "Got it",
    "Versión {}": "Version {}",
    "Corrección en el ajuste de clips desde el detalle de presentación":
        "Fixed clip adjustment from the presentation detail",
    "Tour de bienvenida interactivo de 10 pasos":
        "Interactive 10-step welcome tour",
    "Feedback integrado — calificá la app después de producir una película":
        "Built-in feedback — rate the app after producing a movie",
    "Logging automático en Documentos/PyScout/pyscout.log":
        "Automatic logging to Documents/PyScout/pyscout.log",
    "Dialog de error cuando ocurre un crash inesperado":
        "Error dialog when an unexpected crash occurs",

    "Activar licencia": "Activate license",
    "Prueba gratuita": "Free trial",
    "Días restantes: {}": "Days remaining: {}",
    "Trial expirado": "Trial expired",
    "Licencia activa": "License active",
    "Sin conexión": "Offline",
    "Verificando...": "Checking...",
    "Ingresá tu clave de licencia": "Enter your license key",
    "Activar": "Activate",
    "Clave inválida": "Invalid key",
    "Licencia activada correctamente": "License activated successfully",
    "Comprar": "Buy",
    "NOMBRE DEL PROYECTO": "PROJECT NAME",
    "Ej: Semifinal Liga Nacional...": "E.g.: National League Semifinal...",
    "Crear": "Create",
    "Salir": "Exit",

    # ── screens/observation.py ────────────────────────────────────────────
    "BOTONES": "BUTTONS",
    "Nuevo botón": "New button",
    "Configurar botones": "Configure buttons",
    "NOMBRE DEL BOTÓN": "BUTTON NAME",
    "Ej: PNR, Poste bajo, Transición...": "E.g.: PNR, Post, Transition...",
    "Enter = Crear otro": "Enter = Create another",
    "Listo": "Done",
    "Crear otro": "Create another",
    "BOTÓN": "BUTTON",
    "ANTES (s)": "BEFORE (s)",
    "DESPUÉS (s)": "AFTER (s)",
    "HOTKEY": "HOTKEY",
    "Pad: tiempo antes/después del click  ·  Hotkey: tecla para registrar sin mouse":
        "Pad: time before/after the click  ·  Hotkey: key to record without mouse",
    "Personalizado": "Custom",
    "Escribí una tecla (no F, M, Esc, Space)": "Press a key (not F, M, Esc, Space)",
    "🎲 Hotkeys random": "🎲 Random hotkeys",
    "Asigna una tecla distinta a cada botón de forma aleatoria": "Assigns a unique random key to each button",
    "Hotkey duplicada": "Duplicate hotkey",
    "La tecla '{}' está asignada a más de un botón.\nCambiá una antes de guardar.":
        "Key '{}' is assigned to more than one button.\nChange one before saving.",
    "Creá tu primer botón\ncon el  +  de arriba": "Create your first button\nwith the  +  above",
    "Agregar video fuente": "Add source video",
    "MP4 · MOV · AVI · MKV": "MP4 · MOV · AVI · MKV",
    "REGISTROS ({})": "RECORDS ({})",
    "Presioná un botón mientras el video corre": "Press a button while the video plays",
    "Pantalla completa (F)": "Full screen (F)",
    "Nuevo botón": "New button",
    "Nombre:": "Name:",
    "Hotkey:": "Hotkey:",
    "Pad antes:": "Pad before:",
    "Pad después:": "Pad after:",
    "Eliminar": "Delete",
    "Aceptar": "OK",

    # ── screens/adjust.py ─────────────────────────────────────────────────
    "Todos": "All",
    "Nombre del clip": "Clip name",
    "Nota...": "Note...",
    "Nota": "Note",
    "Agregar nota": "Add note",
    "+ Agregar a presentación": "+ Add to presentation",
    "Ya en presentación": "Already in presentation",
    "Zoom +": "Zoom +",
    "Zoom −": "Zoom −",
    "Recentrar": "Recenter",
    "Clip actualizado": "Clip updated",
    'Clip "{}" en presentación': 'Clip "{}" added to presentation',
    "Clip ya está en la presentación": "Clip already in presentation",
    "Seleccioná un clip para editar": "Select a clip to edit",

    # ── screens/presentation.py ───────────────────────────────────────────
    "NOMBRE": "NAME",
    "TIPO": "TYPE",
    "TIEMPO": "TIME",
    "FUENTE": "SOURCE",
    "NOTA ": "NOTE ",
    "DUR.": "DUR.",
    "Clip": "Clip",
    "Img": "Img",
    "Abrir detalle": "Open detail",
    "Duplicar registro": "Duplicate record",
    "Cambiar visibilidad": "Toggle visibility",
    "Eliminar registro": "Delete record",
    "Eliminar clip": "Delete clip",
    "¿Eliminás '{}' de la presentación?": "Remove '{}' from the presentation?",
    '¿Eliminar "{}"?': 'Remove "{}"?',
    "Eliminar de la presentación": "Remove from presentation",
    "+{} más": "+{} more",
    "Presentación {}": "Presentation {}",
    "Sin clips": "No clips",
    "{} clip": "{} clip",
    "{} clips": "{} clips",
    "Total:": "Total:",
    "Duración:": "Duration:",
    "Imágenes:": "Images:",
    "+ Imagen portada": "+ Cover image",
    "Crear película": "Create movie",
    "Exportar clips separados": "Export separate clips",
    "Procesando video...": "Processing video...",
    "Calculando tiempo restante...": "Calculating remaining time...",
    "Tiempo restante: {}m {}s": "Time remaining: {}m {}s",
    "✓ Película creada exitosamente": "✓ Movie created successfully",
    "Vista previa no disponible": "Preview not available",
    " Anterior": " Previous",
    "Siguiente ": "Next ",
    "Color:": "Color:",
    " Visible": " Visible",
    " Oculto": " Hidden",
    "Visible": "Visible",
    "Oculto": "Hidden",
    "Cargando...": "Loading...",
    "Renombrar listado": "Rename list",
    "Nombre del listado": "List name",
    "Renombrar": "Rename",
    "Eliminar listado": "Delete list",
    "¿Eliminás '{}' y sus {} clips?": "Remove '{}' and its {} clips?",
    "LISTADOS": "LISTS",
    "Agregar listado a esta presentación": "Add list to this presentation",
    "\n\nEl listado está vacío\nAgregá clips desde Ajuste": "\n\nThe list is empty\nAdd clips from Adjust",
    "0 clips  ·  0 imágenes  ·  0:00": "0 clips  ·  0 images  ·  0:00",
    "{} clips  ·  {} imágenes  ·  {}:{}": "{} clips  ·  {} images  ·  {}:{}",
    "RESUMEN": "SUMMARY",
    "Clips": "Clips",
    "Total": "Total",
    "Imgs": "Imgs",
    "DURACIÓN": "DURATION",
    "+ Agregar imagen": "+ Add image",
    "Modo pantalla completa": "Full screen mode",
    "Anterior (←)": "Previous (←)",
    "Siguiente (→)": "Next (→)",
    "Alternar visibilidad": "Toggle visibility",
    "Salir de pantalla completa (Esc)": "Exit full screen (Esc)",
    "Filas más chicas": "Smaller rows",
    "Filas más grandes": "Larger rows",
    "Seleccionar imagen": "Select image",
    "Exportar presentación": "Export presentation",
    "Carpeta para archivos separados": "Folder for separate files",
    "Listado": "List",
    "Notas...": "Notes...",
    "Procesando...": "Processing...",
    "Cancelado": "Cancelled",
    "Error en el render: {}": "Render error: {}",
    "Agregá clips primero": "Add clips first",
    "Todos los items están ocultos": "All items are hidden",
    "{} archivos exportados": "{} files exported",
    ", {} con error": ", {} with error",
    "Abrir carpeta": "Open folder",
    "Cerrar": "Close",
    "Produciendo presentación...": "Producing presentation...",
    "Configuración de exportación": "Export settings",
    "CALIDAD": "QUALITY",
    "Alta (60fps)": "High (60fps)",
    "Alta (30fps)": "High (30fps)",
    "Media (60fps)": "Medium (60fps)",
    "Media (30fps)": "Medium (30fps)",
    "Baja": "Low",
    "TRANSICIÓN": "TRANSITION",
    "Corte directo": "Hard cut",
    "Fade negro (0.5s)": "Black fade (0.5s)",
    "Fade negro (1s)": "Black fade (1s)",
    "OPCIONES DE VIDEO": "VIDEO OPTIONS",
    "Mostrar nombre del clip en el video": "Show clip name in video",
    "Transición entre clips:": "Transition between clips:",
    "OPCIONES DE AUDIO": "AUDIO OPTIONS",
    "Crear archivos separados": "Create separate files",
    "Cada registro se exporta como un MP4 individual": "Each record is exported as an individual MP4",
    "Fade": "Fade",
    "OPCIONES": "OPTIONS",
    "Silenciar audio": "Mute audio",
    "Overlay de nombre": "Name overlay",
    "Archivos separados": "Separate files",
    "Exportar": "Export",
    "Detalle del clip": "Clip detail",
    "Inicio:": "Start:",
    "Fin:": "End:",
    "Transición:": "Transition:",
    "Corte": "Cut",
    "Overlay:": "Overlay:",
    "Sí": "Yes",
    "No": "No",

    # ── app.py — About / Help ─────────────────────────────────────────────
    "Acerca de PyScout": "About PyScout",
    "Análisis de video deportivo": "Sports video analysis",
    "Versión 1.0": "Version 1.0",
    "PyScout es una herramienta para entrenadores y analistas deportivos. "
    "Marcá jugadas en tiempo real mientras mirás el partido, recortá cada clip "
    "con precisión, armá listados tácticos y producí video editado listo para presentar al equipo.":
        "PyScout is a tool for coaches and sports analysts. "
        "Mark plays in real time while watching the match, trim each clip "
        "with precision, build tactical playlists, and produce edited video ready to present to your team.",
    "Sin conexión a internet  ·  Sin límite de proyectos  ·  Sin nube":
        "No internet required  ·  Unlimited projects  ·  No cloud",
    "Formatos de video:  MP4  ·  MOV  ·  MKV  ·  AVI  ·  WebM  ·  MTS":
        "Video formats:  MP4  ·  MOV  ·  MKV  ·  AVI  ·  WebM  ·  MTS",
    "© 2026 PyScout. Todos los derechos reservados.":
        "© 2026 PyScout. All rights reserved.",
    "¿Cómo funciona PyScout?": "How does PyScout work?",
    "Flujo de trabajo": "Workflow",
    "1. Observación": "1. Observation",
    "2. Ajuste": "2. Adjust",
    "3. Presentación": "3. Presentation",
    "Atajos de teclado": "Keyboard shortcuts",
    "Preguntas frecuentes": "FAQ",
    "PyScout te guía por tres pantallas que se encadenan naturalmente:<br><br>"
    "<b>① Observación</b> — Mirás el partido y marcás momentos clave con un clic.<br>"
    "<b>② Ajuste</b> — Revisás cada registro y afinás el inicio y fin del clip.<br>"
    "<b>③ Presentación</b> — Ordenás los clips, armás listados y producís el video final.":
        "PyScout guides you through three screens that flow naturally:<br><br>"
        "<b>① Observation</b> — Watch the match and mark key moments with one click.<br>"
        "<b>② Adjust</b> — Review each record and fine-tune the start and end of the clip.<br>"
        "<b>③ Presentation</b> — Order clips, build playlists, and produce the final video.",
    "Cargá uno o varios videos fuente con el botón <b>+</b> de la barra de pestañas "
    "(hasta 10 simultáneos). En el sidebar izquierdo creá los botones de categoría "
    "que necesitás: PNR, Transición, Tiro libre, etc.":
        "Load one or more source videos with the <b>+</b> button in the tab bar "
        "(up to 10 at once). In the left sidebar create the category buttons "
        "you need: PNR, Transition, Free throw, etc.",
    "Mientras el video corre, presioná el botón en el momento exacto. "
    "PyScout registra el clip con un margen automático antes y después del instante marcado. "
    "Podés ajustar ese margen por categoría con el ícono <b>⚙</b>, y asignar una tecla de atajo "
    "para registrar sin usar el mouse.":
        "While the video plays, press the button at the exact moment. "
        "PyScout records the clip with an automatic margin before and after the marked instant. "
        "You can adjust that margin per category with the <b>⚙</b> icon, and assign a hotkey "
        "to record without using the mouse.",
    "La lista de <b>Registros</b> en la parte inferior muestra todo lo marcado en el video activo. "
    "Clic en un registro para ir al instante; doble clic para editar nombre, nota y color.":
        "The <b>Records</b> list at the bottom shows everything marked in the active video. "
        "Click a record to jump to that instant; double-click to edit name, note, and color.",
    "El sidebar muestra todos tus registros con filtro por categoría. "
    "Seleccioná uno para cargarlo en el reproductor.":
        "The sidebar shows all your records with a category filter. "
        "Select one to load it in the player.",
    "El <b>timeline</b> muestra el clip en contexto. Arrastrá el handle izquierdo o derecho "
    "para mover el inicio o fin del clip. Arrastrá el cuerpo para desplazarlo completo. "
    "El playhead (línea blanca) es tu referencia de posición — los handles se pegan a él "
    "automáticamente cuando se acercan. Usá <b>🔍+ / 🔍−</b> para hacer zoom en el timeline.":
        "The <b>timeline</b> shows the clip in context. Drag the left or right handle "
        "to move the start or end of the clip. Drag the body to shift it entirely. "
        "The playhead (white line) is your position reference — handles snap to it "
        "automatically when close. Use <b>🔍+ / 🔍−</b> to zoom the timeline.",
    "Cuando el clip está listo, presioná <b>+ Agregar a presentación</b> "
    "para sumarlo al listado activo.":
        "When the clip is ready, press <b>+ Add to presentation</b> "
        "to add it to the active playlist.",
    "Cada proyecto puede tener hasta <b>5 listados independientes</b> — útil para separar "
    "ofensiva, defensiva, o distintos jugadores. Cambiá entre ellos con las pestañas del "
    "panel superior; renombrá cualquiera con doble clic.":
        "Each project can have up to <b>5 independent playlists</b> — useful for separating "
        "offense, defense, or different players. Switch between them with the tabs in the "
        "top panel; double-click any to rename it.",
    "Arrastrá las filas para reordenar los clips. Podés intercalar imágenes estáticas, "
    "configurar la transición de cada clip (corte directo o fade), y activar el overlay "
    "de nombre sobre el video.":
        "Drag rows to reorder clips. You can insert static images, "
        "configure the transition for each clip (hard cut or fade), and enable the name overlay on video.",
    "Presioná <b>Producir presentación</b> para exportar un MP4 con todos los clips "
    "concatenados. Podés elegir resolución, calidad y si incluir audio. "
    "También podés exportar cada clip por separado.":
        "Press <b>Produce presentation</b> to export an MP4 with all clips "
        "concatenated. You can choose resolution, quality, and whether to include audio. "
        "You can also export each clip separately.",
    "Reproducción": "Playback",
    "Space  play / pausa\n← / →  retroceder / avanzar 5 s\n↑ / ↓  avanzar / retroceder 10 s\nShift + ← / →  ±1 minuto":
        "Space  play / pause\n← / →  back / forward 5 s\n↑ / ↓  forward / back 10 s\nShift + ← / →  ±1 minute",
    "Ventana": "Window",
    "F  pantalla completa (video en Observación)\nF11  pantalla completa de la aplicación\nM  silenciar":
        "F  full screen (video in Observation)\nF11  full screen app\nM  mute",
    "Proyecto": "Project",
    "Ctrl+Z  deshacer\nCtrl+Shift+Z  rehacer\nCtrl+S  guardar\nCtrl+O  abrir proyecto\nCtrl+N  nuevo proyecto":
        "Ctrl+Z  undo\nCtrl+Shift+Z  redo\nCtrl+S  save\nCtrl+O  open project\nCtrl+N  new project",
    "¿Qué formatos de video acepta?": "What video formats are supported?",
    "MP4, MOV, MKV, AVI, WebM y MTS. La mayoría de cámaras de acción, "
    "drones y captura de pantalla generan alguno de estos formatos.":
        "MP4, MOV, MKV, AVI, WebM and MTS. Most action cameras, "
        "drones, and screen recorders produce one of these formats.",
    "¿Necesito conexión a internet?": "Do I need an internet connection?",
    "No. PyScout funciona completamente offline. La única conexión que puede "
    "necesitar es al activar o renovar la licencia.":
        "No. PyScout works completely offline. The only connection needed "
        "is when activating or renewing the license.",
    "¿Dónde se guardan los proyectos?": "Where are projects saved?",
    "En Documentos / PyScout / Projects. Cada proyecto es un único archivo .scout "
    "que contiene todos tus botones, registros y listados.":
        "In Documents / PyScout / Projects. Each project is a single .scout file "
        "that contains all your buttons, records, and playlists.",
    "¿Puedo trabajar con varios videos del mismo partido?": "Can I work with multiple videos of the same match?",
    "Sí. Podés cargar hasta 10 videos fuente simultáneos y cambiar entre ellos "
    "con las pestañas. Los clips de cada video quedan asociados a su fuente.":
        "Yes. You can load up to 10 source videos at once and switch between them "
        "with the tabs. Clips from each video stay linked to their source.",
    "¿Puedo deshacer cambios accidentales?": "Can I undo accidental changes?",
    "Sí. Ctrl+Z deshace y Ctrl+Shift+Z rehace. El historial cubre "
    "registros, ajustes de clips y cambios en los listados de presentación.":
        "Yes. Ctrl+Z undoes and Ctrl+Shift+Z redoes. The history covers "
        "records, clip adjustments, and changes to presentation playlists.",
    "¿Qué pasa si cierro la app sin guardar?": "What happens if I close the app without saving?",
    "PyScout tiene autoguardado activo por defecto. Cualquier cambio se escribe "
    "al archivo del proyecto automáticamente, sin necesidad de guardar manualmente.":
        "PyScout has autosave enabled by default. Any change is written "
        "to the project file automatically, with no need to save manually.",
    "Autoguardado activado": "Autosave enabled",
    "Autoguardado desactivado": "Autosave disabled",
    "Guardado automáticamente": "Saved automatically",
    "(vacío)": "(empty)",

    # ── utils/updater.py ──────────────────────────────────────────────────
    "Actualización disponible: v{}": "Update available: v{}",
    "Ya tenés la última versión": "You're up to date",
    "Error al verificar actualizaciones": "Error checking for updates",
    "Descargando actualización...": "Downloading update...",
    "Instalando actualización...": "Installing update...",

    # ── adjust.py ─────────────────────────────────────────────────────────────
    "Editar detalle": "Edit detail",
    "Duración: —": "Duration: —",
    "Duración: {}s": "Duration: {}s",
    '¿Eliminar "{}" ({})?': 'Remove "{}" ({})?',
    "Esta acción se puede deshacer con Ctrl+Z.": "This action can be undone with Ctrl+Z.",

    # ── app.py — updates / codecs ─────────────────────────────────────────────
    "{} botones cargados": "{} buttons loaded",
    "Buscando actualizaciones...": "Checking for updates...",
    "Sin conexión a internet": "No internet connection",
    "Estás al día (v{})": "You're up to date (v{})",
    "Servidor no disponible (HTTP {})": "Server unavailable (HTTP {})",
    "Actualización disponible": "Update available",
    "Descargar y actualizar": "Download and install",
    "Descargando PyScout {}": "Downloading PyScout {}",
    "Descargando PyScout {}...": "Downloading PyScout {}...",
    "Conectando...": "Connecting...",
    "Error al descargar: {}": "Download error: {}",
    "Módulo de actualizaciones no disponible": "Updates module not available",
    "Actualización lista": "Update ready",
    "PyScout {} listo para instalar.\n\nLa app se cerrará y se reiniciará automáticamente.\n¿Continuar?":
        "PyScout {} is ready to install.\n\nThe app will close and restart automatically.\nContinue?",
    "Códecs no encontrados": "Codecs not found",
    "FFmpeg no está instalado.\nEs necesario para exportar videos.\n\n¿Ir a la página de descarga?":
        "FFmpeg is not installed.\nRequired to export videos.\n\nGo to the download page?",
    "Estado de componentes": "Component status",
    "Componentes de video": "Video components",
    "cargado": "loaded",
    "No encontrado — reinstalá PyScout": "Not found — reinstall PyScout",
    "Todos los componentes están instalados correctamente.": "All components are installed correctly.",
    "Algunos componentes faltan. Reinstalá PyScout para reparar.": "Some components are missing. Reinstall PyScout to repair.",

    # ── dialogs.py — licencias ────────────────────────────────────────────────
    "Pro (offline) — {}h de gracia": "Pro (offline) — {}h grace",
    "Prueba: {} días restantes": "Trial: {} days remaining",
    "Prueba: {}h restantes": "Trial: {}h remaining",
    "Prueba: {}min restantes": "Trial: {}min remaining",
    "Prueba: {}s restantes": "Trial: {}s remaining",
    "Período de gracia — activá tu licencia": "Grace period — activate your license",
    "Modo desarrollo": "Development mode",
    "Prueba expirada — activá tu licencia": "Trial expired — activate your license",
    "Licencia de otro equipo": "License belongs to another device",
    "Reloj del sistema manipulado": "System clock tampered",
    "Archivo de licencia dañado": "License file corrupted",
    "Sin licencia": "No license",
    "Clave vacía": "Empty key",
    "Pegá una clave de licencia válida.": "Enter a valid license key.",
    "Activado": "Activated",
    "Licencia requerida": "License required",
    "No encontrado": "Not found",
    "Tu período de prueba expiró. Activá una licencia para continuar.":
        "Your trial has expired. Activate a license to continue.",
    "Esta licencia pertenece a otro equipo.": "This license belongs to another device.",
    "Se detectó una manipulación del reloj del sistema.": "System clock tampering detected.",
    "El archivo de licencia está dañado. Activá una licencia.":
        "The license file is corrupted. Activate a license.",
    "Activá tu licencia para continuar.": "Activate your license to continue.",

    # ── Strings faltantes — detectados en auditoría mayo 2026 ─────────────────

    # Licencias — course keys
    "Acceso de curso activado — {} días": "Course access activated — {} days",
    "Acceso de curso — {} días": "Course access — {} days",
    "Código ya activado — {} días restantes": "Already activated — {} days remaining",

    # Observation — botonera
    "Borrar botón": "Delete button",
    "Cambiar color": "Change color",
    "Cambiar color ({} clips)": "Change color ({} clips)",
    "Cargar preset de deporte": "Load sport preset",
    "Cargar preset...": "Load preset...",
    "Reemplazar botonera actual": "Replace current button board",
    "Elegí un deporte:": "Pick a sport:",
    "El botón '{}' tiene {}.\n¿Borrar igual?": "Button '{}' has {}.\nDelete anyway?",

    # Observation — clips y exportación
    "Agregar a presentación": "Add to presentation",
    "Ya está en la presentación": "Already in presentation",
    "{} en presentación": "{} in presentation",
    "Abrir en Ajuste": "Open in Adjust",
    "Exportar clip": "Export clip",
    "Guardar clip como": "Save clip as",
    "Exportando {}...": "Exporting {}...",
    "Exportado: {}": "Exported: {}",
    "Error al exportar": "Export error",
    "Preparando exportación...": "Preparing export...",
    "Cargar": "Load",

    # Presentation
    "Sin clips visibles en la presentación": "No visible clips in the presentation",
    "El listado está vacío\nAgregá clips desde Ajuste": "The list is empty\nAdd clips from Adjust",
    "Vista previa": "Preview",
    "Imagen no encontrada": "Image not found",
    "{} clip{}": "{} clip{}",

    # Video player — resume dialog
    "Reanudar": "Resume",
    "¿Continuar desde {}?": "Resume from {}?",

    # Feedback
    "Tu opinión nos ayuda a mejorar PyScout.": "Your feedback helps us improve PyScout.",
    "¡Gracias por tu feedback!": "Thanks for your feedback!",

    # Color picker
    "Elegir color": "Choose color",

    "  No encontrado — reinstalá PyScout": "  Not found — reinstall PyScout",
    "▶  Vista previa": "▶  Preview",
}
