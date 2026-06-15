import os, re, sys, subprocess, tempfile, threading, queue, time
from typing import Optional, Callable


def _short_path(path: str) -> str:
    """Convert to Windows 8.3 short path to avoid non-ASCII crashes in FFmpeg."""
    if sys.platform != "win32":
        return path
    path = os.path.normpath(path)
    if not os.path.exists(path):
        return path
    try:
        import ctypes
        buf = ctypes.create_unicode_buffer(512)
        r = ctypes.windll.kernel32.GetShortPathNameW(path, buf, 512)
        if r > 0:
            return buf.value
    except Exception:
        pass
    return path


def get_ffmpeg() -> str:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # Directorio del ejecutable (Nuitka y PyInstaller onedir)
    exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    candidates = [
        os.path.join(exe_dir, "ffmpeg.exe"),
        os.path.join(exe_dir, "ffmpeg"),
        os.path.join(root, "ffmpeg.exe"),
        os.path.join(root, "ffmpeg"),
    ]
    if getattr(sys, '_MEIPASS', None):
        candidates.insert(0, os.path.join(sys._MEIPASS, "ffmpeg.exe"))
    if sys.platform == "darwin":
        candidates += ["/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg"]
    candidates.append("ffmpeg")
    for c in candidates:
        if os.path.exists(c):
            return c
    return "ffmpeg"


def get_ffprobe() -> str:
    """Buscar ffprobe junto a ffmpeg."""
    ffmpeg = get_ffmpeg()
    probe = ffmpeg.replace("ffmpeg", "ffprobe")
    if os.path.exists(probe):
        return probe
    return "ffprobe"


def has_audio(path: str) -> bool:
    """Verificar si un archivo de video tiene stream de audio."""
    try:
        r = subprocess.run(
            [get_ffprobe(), "-v", "quiet", "-select_streams", "a",
             "-show_entries", "stream=codec_type", "-of", "csv=p=0",
             _short_path(path)],
            capture_output=True, text=True, timeout=5
        )
        return "audio" in r.stdout.lower()
    except Exception:
        return True  # Asumir que tiene audio si no podemos verificar


def _safe_drawtext(name: str) -> str:
    safe = name.replace("\\","").replace("'","").replace('"',"")
    safe = safe.replace(":"," ").replace("["," ").replace("]"," ")
    safe = safe.replace(","," ").replace(";"," ")
    return safe.strip()


def _run_ffmpeg(args: list) -> tuple[int, str]:
    """Corre FFmpeg capturando stderr. Maneja unicode en Windows."""
    ffmpeg_env = os.environ.copy()
    ffmpeg_env["AV_LOG_FORCE_NOCOLOR"] = "1"
    if os.path.exists(args[0]):
        fdir = os.path.dirname(os.path.abspath(args[0]))
        ffmpeg_env["PATH"] = fdir + os.pathsep + ffmpeg_env.get("PATH", "")

    if sys.platform == "win32":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0
        proc = subprocess.Popen(
            args,
            stderr=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            startupinfo=si,
            env=ffmpeg_env,
        )
    else:
        proc = subprocess.Popen(
            args,
            stderr=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            env=ffmpeg_env,
        )

    stderr_bytes = proc.communicate()[1]
    try:
        stderr = stderr_bytes.decode("utf-8", errors="replace")
    except Exception:
        try:
            stderr = stderr_bytes.decode("cp1252", errors="replace")
        except Exception:
            stderr = repr(stderr_bytes)

    return proc.returncode, stderr


def render_presentation(
    items: list[dict],
    output_path: str,
    show_overlay: bool = False,
    mute_audio: bool = False,
    crf: int = 23,
    fps: int = 30,
    transition: str = "cut",
    progress_cb: Optional[Callable[[str], None]] = None,
) -> bool:
    ffmpeg    = _short_path(get_ffmpeg())
    inputs    = []
    vfilters  = []
    afilters  = []
    durations = []

    fade_dur = {"cut": 0.0, "fade05": 0.5, "fade10": 1.0}.get(transition, 0.0)
    n = len(items)

    for i, item in enumerate(items):
        if item["type"] == "image":
            dur = float(item.get("image_dur", 3.0))
            img_path = _short_path(item["image_path"])
            inputs += ["-loop", "1", "-t", str(dur), "-i", img_path]
            vfilters.append(
                f"[{i}:v]scale=1920:1080:force_original_aspect_ratio=decrease,"
                f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps},settb=1/{fps}[v{i}]"
            )
            if not mute_audio:
                afilters.append(f"aevalsrc=0:c=stereo:s=44100:d={dur}[a{i}]")
            durations.append(dur)
        else:
            dur   = float(item.get("clip_dur", 5.0))
            start = float(item.get("clip_start", 0.0))
            vid_path = _short_path(item["video_path"])
            inputs += ["-ss", str(start), "-t", str(dur), "-i", vid_path]
            vf = (
                f"[{i}:v]scale=1920:1080:force_original_aspect_ratio=decrease,"
                f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps},settb=1/{fps}"
            )
            if show_overlay and item.get("name"):
                safe = _safe_drawtext(item["name"])
                # Buscar Roboto en carpeta fonts de la app
                app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                roboto_app = os.path.join(app_root, "fonts", "Roboto-Regular.ttf")
                
                if sys.platform == "win32":
                    # Prioridad: 1) carpeta app, 2) Windows Fonts, 3) Arial fallback
                    if os.path.exists(roboto_app):
                        # Usar Roboto de la app
                        # Convertir a forward slashes y escapar para FFmpeg
                        roboto_normalized = roboto_app.replace("\\", "/")
                        # Escapar los dos puntos después de la letra de unidad
                        roboto_escaped = roboto_normalized.replace(":", "\\:")
                        fp = f"fontfile='{roboto_escaped}':"
                    elif os.path.exists("C:/Windows/Fonts/Roboto-Regular.ttf"):
                        fp = "fontfile='C\\:/Windows/Fonts/Roboto-Regular.ttf':"
                    else:
                        # Fallback a Arial
                        fp = "fontfile='C\\:/Windows/Fonts/arial.ttf':"
                else:
                    # Linux/Mac: usar Roboto de la app si existe
                    if os.path.exists(roboto_app):
                        fp = f"fontfile='{roboto_app}':"
                    else:
                        fp = "font=Roboto:"  # Buscar en sistema
                
                # Overlay estilo profesional: barra completa en bottom
                # Altura reducida 30%: de 100px a 70px
                vf += (
                    f",drawbox=x=0:y=ih-70:w=iw:h=70:color=black@0.7:t=fill"
                    f",drawtext={fp}text='{safe}':fontsize=42:fontcolor=white"
                    f":x=40:y=h-50"  # 40px desde izquierda, 50px desde abajo
                )
            vfilters.append(f"{vf}[v{i}]")
            if not mute_audio:
                if has_audio(vid_path):
                    afilters.append(
                        f"[{i}:a]aformat=sample_fmts=fltp:sample_rates=44100:"
                        f"channel_layouts=stereo[a{i}]"
                    )
                else:
                    # Video sin audio → generar silencio de la misma duración
                    afilters.append(
                        f"anullsrc=channel_layout=stereo:sample_rate=44100,"
                        f"atrim=0:{dur:.3f},asetpts=PTS-STARTPTS[a{i}]"
                    )
            durations.append(dur)

    all_filters = vfilters + afilters

    # Video pipeline
    if fade_dur > 0 and n > 1:
        offset = max(0.05, durations[0] - fade_dur)
        all_filters.append(
            f"[v0][v1]xfade=transition=fade:duration={fade_dur}:offset={offset:.3f}[xf1]"
        )
        for i in range(2, n):
            offset += max(0.05, durations[i-1] - fade_dur)
            out_label = "[vout]" if i == n-1 else f"[xf{i}]"
            all_filters.append(
                f"[xf{i-1}][v{i}]xfade=transition=fade:"
                f"duration={fade_dur}:offset={offset:.3f}{out_label}"
            )
        if n == 2:
            all_filters[-1] = all_filters[-1].replace("[xf1]", "[vout]")
    else:
        concat_v = "".join(f"[v{i}]" for i in range(n))
        all_filters.append(f"{concat_v}concat=n={n}:v=1:a=0[vout]")

    # Audio pipeline
    if mute_audio:
        map_args   = ["-map", "[vout]"]
        audio_args = ["-an"]
    else:
        concat_a = "".join(f"[a{i}]" for i in range(n))
        all_filters.append(f"{concat_a}concat=n={n}:v=0:a=1[aout]")
        map_args   = ["-map", "[vout]", "-map", "[aout]"]
        audio_args = ["-c:a", "aac", "-b:a", "192k"]

    filter_complex = ";".join(all_filters)

    # ── Escribir filter_complex a archivo temporal ────────────────────────────
    # Evita el límite de ~8K caracteres de Windows y problemas de escaping
    fc_file = tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", prefix="scout_fc_",
        delete=False, encoding="utf-8")
    fc_file.write(filter_complex)
    fc_file.close()
    fc_path = fc_file.name

    try:
        out = os.path.normpath(output_path)

        # Verify all input files exist
        for item in items:
            if item["type"] == "image":
                p = item["image_path"]
            else:
                p = item["video_path"]
            if not os.path.isfile(p):
                raise RuntimeError(f"Archivo no encontrado: {p}")

        args = [
            ffmpeg, "-y",
            *inputs,
            "-filter_complex_script", fc_path,
            *map_args,
            "-c:v", "libx264", "-preset", "fast", "-crf", str(crf),
            "-pix_fmt", "yuv420p",
            *audio_args,
            "-movflags", "+faststart",
            out,
        ]

        print("[FFmpeg CMD]", " ".join(str(a) for a in args))
        print(f"[FFmpeg filter_complex_script] {fc_path} ({len(filter_complex)} chars)")

        extra = {}
        env = os.environ.copy()
        env["AV_LOG_FORCE_NOCOLOR"] = "1"
        # Ensure ffmpeg can find its DLLs
        if os.path.exists(ffmpeg):
            fdir = os.path.dirname(os.path.abspath(ffmpeg))
            env["PATH"] = fdir + os.pathsep + env.get("PATH", "")

        if sys.platform == "win32":
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = 0
            extra = {"startupinfo": si}
        proc = subprocess.Popen(
            args, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL,
            env=env,
            **extra,
        )

        # Leer stderr en un hilo auxiliar para permitir timeout de stall.
        # Si FFmpeg se cuelga sin cerrarse, detectamos la inactividad y lo matamos.
        stderr_q: queue.Queue = queue.Queue()

        def _pipe_reader(pipe, q):
            try:
                while True:
                    chunk = pipe.read(256)
                    if not chunk:
                        break
                    q.put(chunk)
            finally:
                q.put(None)  # centinela: pipe cerrado

        _t = threading.Thread(target=_pipe_reader, args=(proc.stderr, stderr_q), daemon=True)
        _t.start()

        STALL_TIMEOUT = 120  # segundos sin progreso antes de matar FFmpeg
        stderr_buf = ""
        partial = b""
        last_progress = time.monotonic()

        while True:
            try:
                chunk = stderr_q.get(timeout=1.0)
            except queue.Empty:
                if time.monotonic() - last_progress > STALL_TIMEOUT:
                    proc.kill()
                    raise RuntimeError(
                        "FFmpeg no respondió por más de 2 minutos. "
                        "El proceso fue terminado para evitar un bloqueo."
                    )
                continue

            if chunk is None:
                break

            partial += chunk
            # Split on \r o \n — FFmpeg usa \r para las líneas de progreso
            while b"\r" in partial or b"\n" in partial:
                ri = partial.find(b"\r")
                ni = partial.find(b"\n")
                if ri == -1: ri = len(partial)
                if ni == -1: ni = len(partial)
                pos = min(ri, ni)
                line_bytes = partial[:pos]
                partial = partial[pos+1:]
                try:
                    line = line_bytes.decode("utf-8", errors="replace")
                except Exception:
                    line = ""
                if line.strip():
                    stderr_buf += line + "\n"
                    m = re.search(r"time=(\d+:\d+:\d+[\.\d]*)", line)
                    if m:
                        last_progress = time.monotonic()
                        if progress_cb:
                            progress_cb(m.group(1))

        proc.wait()

        print(f"[FFmpeg returncode] {proc.returncode}")
        if proc.returncode != 0:
            print(f"[FFMPEG FULL STDERR]\n{stderr_buf}")
            cmd = " ".join(f'"{a}"' if " " in str(a) else str(a) for a in args)
            if not stderr_buf.strip():
                hint = (
                    "\n\nFFmpeg crasheó sin output (0x{:08X}). "
                    "Posibles causas:\n"
                    "- FFmpeg corrupto o incompatible con tu sistema\n"
                    "- DLLs faltantes (probá correr ffmpeg -version desde cmd)\n"
                    "- Algún archivo de entrada no existe o no es accesible"
                ).format(proc.returncode & 0xFFFFFFFF)
            else:
                hint = f"\n\nSTDERR:\n{stderr_buf[-2000:]}"
            raise RuntimeError(
                f"CMD:\n{cmd}\n\n"
                f"FILTER ({len(filter_complex)} chars):\n{filter_complex[:500]}"
                f"{hint}")
        return True

    finally:
        # Limpiar archivo temporal
        try:
            os.unlink(fc_path)
        except Exception:
            pass


def extract_frames(video_path, start_sec, duration, fps=15, width=960):
    tmp_dir = tempfile.mkdtemp(prefix="scout_frames_")
    out_pattern = os.path.join(tmp_dir, "f%05d.jpg")
    args = [
        _short_path(get_ffmpeg()),
        "-ss", str(max(0.0, start_sec)), "-t", str(duration + 1.0),
        "-i", _short_path(video_path),
        "-vf", f"fps={fps},scale={width}:-2",
        "-q:v", "3", "-f", "image2", out_pattern, "-y",
    ]
    rc, err = _run_ffmpeg(args)
    if rc != 0:
        raise RuntimeError(err[-300:])
    paths = sorted([os.path.join(tmp_dir, f)
                    for f in os.listdir(tmp_dir) if f.endswith(".jpg")])
    return paths, tmp_dir, fps


def export_clip(clip_dict: dict, output_path: str,
                crf: int = 20, fps: int = 30,
                mute_audio: bool = False,
                show_overlay: bool = False,
                clip_name: str = "") -> bool:
    """Exportar un clip individual con configuración de calidad."""
    ffmpeg = _short_path(get_ffmpeg())
    start  = float(clip_dict.get("clip_start", 0.0))
    dur    = float(clip_dict.get("clip_dur",   5.0))
    vid    = _short_path(clip_dict["video_path"])
    out    = os.path.normpath(output_path)

    os.makedirs(os.path.dirname(out), exist_ok=True)

    if mute_audio:
        audio_args = ["-an"]
    else:
        audio_args = ["-c:a", "aac", "-b:a", "192k"] if has_audio(vid) else ["-an"]

    vf = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2"
    if show_overlay and clip_name:
        escaped = clip_name.replace("'", "\\'").replace(":", "\\:").replace(",", "\\,")
        vf += (
            f",drawtext=text='{escaped}':fontcolor=white:fontsize=32"
            f":x=20:y=20:box=1:boxcolor=black@0.5:boxborderw=6"
        )

    args = [
        ffmpeg, "-y",
        "-ss", str(max(0.0, start)), "-t", str(max(0.1, dur)), "-i", vid,
        "-c:v", "libx264", "-preset", "fast", "-crf", str(crf),
        "-r", str(fps),
        "-pix_fmt", "yuv420p",
        "-vf", vf,
        *audio_args,
        "-movflags", "+faststart",
        out,
    ]
    rc, _err = _run_ffmpeg(args)
    return rc == 0


def delete_frame_dir(tmp_dir: str):
    try:
        for f in os.listdir(tmp_dir):
            try: os.unlink(os.path.join(tmp_dir, f))
            except: pass
        os.rmdir(tmp_dir)
    except: pass