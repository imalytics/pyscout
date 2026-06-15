"""
PyScout License Manager — Polar.sh + 5 archivos redundantes anti-tamper.

Los datos de licencia se guardan en 5 ubicaciones diferentes.
Para resetear el trial, el user tendría que encontrar y borrar las 5.
Si falta alguna pero otras existen, se restaura desde las que quedan.
Si hay inconsistencia (una dice trial, otra dice expired), se usa la más restrictiva.
"""

from __future__ import annotations

import base64, datetime, hashlib, hmac as _hmac, json, os, platform, secrets, sys, uuid
from pathlib import Path

if sys.platform == "win32":
    try:
        import winreg
    except ImportError:
        winreg = None
else:
    winreg = None

try:
    import requests
except ImportError:
    requests = None

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════════════════════

POLAR_ORG_ID = "a3608077-32b8-47d8-a701-8572f59ff9fd"
POLAR_PRODUCT_ID = "9109ea62-ae1c-4548-8820-761e589ab8e2"
POLAR_CHECKOUT_URL = "https://polar.sh/checkout/polar_c_jFRXBrcZ7BX5NqIDRk1pItlSgOZFGP1pjf4iP0f5QWT"
API = "https://api.polar.sh/v1/customer-portal/license-keys"

TRIAL_SECONDS = 7 * 86400   # 7 días
GRACE_SECONDS = 0

# Código de curso — clave secreta para firmar (nunca cambiarlo o las keys viejas dejan de funcionar)
_COURSE_SECRET = "PyScoutCurso2026!xK9#mQ7@zP3"

# ══════════════════════════════════════════════════════════════════════════════
#  5 UBICACIONES DE ARCHIVOS (Windows + Mac + Linux)
# ══════════════════════════════════════════════════════════════════════════════

def _get_paths() -> list[Path]:
    """5 rutas distintas donde guardar el estado de licencia."""
    paths = []

    if sys.platform == "win32" and winreg:
        # 1. AppData/Roaming/PyScout
        paths.append(Path(os.environ.get("APPDATA", "")) / "PyScout" / ".pyscout_license.dat")
        # 2. AppData/Local/PyScout
        paths.append(Path(os.environ.get("LOCALAPPDATA", "")) / "PyScout" / ".ps_cache.dat")
        # 3. ProgramData (oculto, requiere explorar manualmente)
        paths.append(Path(os.environ.get("PROGRAMDATA", "C:/ProgramData")) / "PyScout" / ".ps_sys.dat")
        # 4. Carpeta de usuario oculta
        paths.append(Path.home() / ".pyscout" / ".config.dat")
        # 5. Temp persistente (no se borra en cada reinicio)
        paths.append(Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Protect" / ".ps_pref.dat")

    elif sys.platform == "darwin":
        # 1. Application Support
        paths.append(Path.home() / "Library" / "Application Support" / "PyScout" / ".pyscout_license.dat")
        # 2. Preferences
        paths.append(Path.home() / "Library" / "Preferences" / ".pyscout_pref.dat")
        # 3. Caches
        paths.append(Path.home() / "Library" / "Caches" / "PyScout" / ".ps_cache.dat")
        # 4. Hidden en home
        paths.append(Path.home() / ".pyscout" / ".config.dat")
        # 5. Logs (nadie mira ahí)
        paths.append(Path.home() / "Library" / "Logs" / "PyScout" / ".ps_sys.dat")

    else:  # Linux
        paths.append(Path.home() / ".pyscout" / ".pyscout_license.dat")
        paths.append(Path.home() / ".config" / "pyscout" / ".ps_cache.dat")
        paths.append(Path.home() / ".local" / "share" / "pyscout" / ".ps_sys.dat")
        paths.append(Path.home() / ".cache" / "pyscout" / ".config.dat")
        paths.append(Path("/tmp") / ".ps_pref.dat")  # se pierde en reboot, pero suma

    # Filtrar paths vacíos
    return [p for p in paths if str(p.parent) != ""]


_PATHS = _get_paths()
_K_BASE = "PyScout2025!xK9#mQ7@"

def _derive_key() -> str:
    """Derivar clave de cifrado del HWID — cada máquina tiene clave diferente."""
    hwid = get_hwid()
    return hashlib.sha256(f"{_K_BASE}-{hwid}".encode()).hexdigest()[:20]

# Registro de Windows: usar clave que se mezcla con las del sistema
_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\{7A3F2B1C-4D5E-6F78-9A0B-C2D3E4F5A6B8}"
_REG_VALUE = "InstallDate"  # Nombre inocuo


# ══════════════════════════════════════════════════════════════════════════════
#  HARDWARE ID
# ══════════════════════════════════════════════════════════════════════════════

def get_hwid() -> str:
    mac = uuid.getnode()
    cpu = platform.processor()
    vol = "x"
    try:
        if sys.platform == "win32" and winreg:
            r = os.popen("vol C:").read()
            vol = r.strip().split()[-1] if r.strip() else "x"
        elif sys.platform == "darwin":
            r = os.popen("ioreg -rd1 -c IOPlatformExpertDevice | grep IOPlatformSerialNumber").read()
            vol = r.split('"')[-2] if '"' in r else "x"
        else:
            vol = os.popen("cat /etc/machine-id 2>/dev/null || echo x").read().strip()
    except Exception:
        pass
    return hashlib.sha256(f"{mac}-{cpu}-{vol}".encode()).hexdigest()[:16].upper()


# ══════════════════════════════════════════════════════════════════════════════
#  CRYPTO
# ══════════════════════════════════════════════════════════════════════════════

def _enc(d: dict) -> str:
    raw = json.dumps(d, default=str).encode()
    kb = _derive_key().encode()
    return base64.b64encode(bytes(b ^ kb[i % len(kb)] for i, b in enumerate(raw))).decode()

def _dec(t: str) -> dict:
    x = base64.b64decode(t.encode())
    kb = _derive_key().encode()
    return json.loads(bytes(b ^ kb[i % len(kb)] for i, b in enumerate(x)).decode())


# ══════════════════════════════════════════════════════════════════════════════
#  MULTI-FILE SAVE/LOAD — Guardar en 5 lugares + registro Windows
# ══════════════════════════════════════════════════════════════════════════════

def _save(d: dict):
    """Guardar en 5 ubicaciones + registro + checksum SHA256."""
    encoded = _enc(d)
    checksum = hashlib.sha256(encoded.encode()).hexdigest()[:16]
    payload = f"{checksum}:{encoded}"  # checksum:data
    saved = 0
    for p in _PATHS:
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(payload, encoding="utf-8")
            saved += 1
        except Exception:
            pass

    if sys.platform == "win32" and winreg:
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, _REG_KEY)
            winreg.SetValueEx(key, _REG_VALUE, 0, winreg.REG_SZ, payload)
            winreg.CloseKey(key)
            saved += 1
        except Exception:
            pass


def _load() -> dict | None:
    """Leer de cualquier ubicación. Verificar checksum. Restaurar faltantes."""
    candidates = []

    for p in _PATHS:
        try:
            if p.exists():
                raw = p.read_text(encoding="utf-8").strip()
                if ":" in raw:
                    chk, encoded = raw.split(":", 1)
                    # Verificar checksum — si fue editado manualmente, no matchea
                    if hashlib.sha256(encoded.encode()).hexdigest()[:16] == chk:
                        candidates.append(_dec(encoded))
                else:
                    # Formato viejo sin checksum (compatibilidad)
                    candidates.append(_dec(raw))
        except Exception:
            pass

    if sys.platform == "win32" and winreg:
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY)
            val, _ = winreg.QueryValueEx(key, _REG_VALUE)
            winreg.CloseKey(key)
            raw = val.strip()
            if ":" in raw:
                chk, encoded = raw.split(":", 1)
                if hashlib.sha256(encoded.encode()).hexdigest()[:16] == chk:
                    candidates.append(_dec(encoded))
            else:
                candidates.append(_dec(raw))
        except Exception:
            pass

    if not candidates:
        return None

    # Pro tiene prioridad
    for c in candidates:
        if c.get("type") == "pro":
            _save(c)
            return c

    # Course: segundo en prioridad — usar el que expire más tarde
    courses = [c for c in candidates if c.get("type") == "course" and c.get("course_expires")]
    if courses:
        best = max(courses, key=lambda c: c.get("course_expires", ""))
        _save(best)
        return best

    # Trial: usar el más antiguo (más restrictivo)
    trials = [c for c in candidates if c.get("type") == "trial" and c.get("trial_start")]
    if trials:
        best = min(trials, key=lambda t: t["trial_start"])
        if len(candidates) < len(_PATHS):
            _save(best)
        return best

    return candidates[0]


# ══════════════════════════════════════════════════════════════════════════════
#  POLAR API
# ══════════════════════════════════════════════════════════════════════════════

def _post(endpoint: str, payload: dict) -> requests.Response:
    if requests is None:
        raise ImportError("Instalar: pip install requests")
    return requests.post(f"{API}/{endpoint}", json=payload,
                         headers={"Content-Type": "application/json"}, timeout=10)


def polar_activate(key: str, label: str) -> tuple[bool, str, dict]:
    try:
        r = _post("activate", {"key": key.strip(), "organization_id": POLAR_ORG_ID, "label": label})
        if r.status_code == 200:
            return True, "OK", r.json()
        if r.status_code in (403, 422):
            try:
                detail = str(r.json().get("detail", "")).lower()
            except Exception:
                detail = ""
            if any(w in detail for w in ("limit", "reached", "maximum")):
                return False, "LIMIT_REACHED", {}
            return False, f"Error: {detail}", {}
        if r.status_code == 404:
            return False, "Licencia no encontrada", {}
        return False, f"Error HTTP {r.status_code}", {}
    except requests.exceptions.ConnectionError:
        return False, "Sin conexión a internet", {}
    except requests.exceptions.Timeout:
        return False, "Tiempo de espera agotado", {}
    except ImportError as e:
        return False, str(e), {}
    except Exception as e:
        return False, f"Error: {e}", {}


def polar_validate(key: str, activation_id: str | None = None) -> tuple[bool, str, dict]:
    payload = {"key": key.strip(), "organization_id": POLAR_ORG_ID}
    if activation_id:
        payload["activation_id"] = activation_id
    try:
        r = _post("validate", payload)
        if r.status_code == 200:
            data = r.json()
            status = data.get("status", "")
            if status in ("revoked", "disabled"):
                return False, f"Licencia {status}", data
            return True, "OK", data
        if r.status_code == 404:
            return False, "Licencia no encontrada", {}
        return False, f"Error HTTP {r.status_code}", {}
    except requests.exceptions.ConnectionError:
        return False, "Sin conexión a internet", {}
    except requests.exceptions.Timeout:
        return False, "Tiempo de espera agotado", {}
    except ImportError as e:
        return False, str(e), {}
    except Exception as e:
        return False, f"Error: {e}", {}


def polar_deactivate(key: str, activation_id: str) -> tuple[bool, str]:
    try:
        r = _post("deactivate", {"key": key.strip(), "organization_id": POLAR_ORG_ID,
                                  "activation_id": activation_id})
        return (True, "Slot liberado") if r.status_code in (200, 204) else (False, f"Error HTTP {r.status_code}")
    except Exception as e:
        return False, f"Error: {e}"


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _now(): return datetime.datetime.now()
def _now_s(): return _now().isoformat()
def _dt(s): return datetime.datetime.fromisoformat(s)

def format_seconds_compact(s: int) -> str:
    s = max(0, int(s)); m, s = divmod(s, 60); h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

def _heartbeat(d: dict) -> dict:
    now = _now()
    last = d.get("last_check")
    if last and now < _dt(last) - datetime.timedelta(hours=2):
        d["clock_tamper"] = d.get("clock_tamper", 0) + 1
    d["last_check"] = _now_s()
    return d


# ══════════════════════════════════════════════════════════════════════════════
#  CÓDIGOS DE CURSO
# ══════════════════════════════════════════════════════════════════════════════

def _course_sign(body: str) -> str:
    """4 chars de HMAC-SHA256 para firmar el cuerpo de la key de curso."""
    return _hmac.new(_COURSE_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()[:4].upper()

def generate_course_key(days: int = 90) -> str:
    """Genera una key de curso que otorga N días de acceso. Solo correr en desarrollo."""
    p1 = secrets.token_hex(2).upper()
    p2 = secrets.token_hex(2).upper()
    body = f"CURSO-{days:03d}-{p1}-{p2}"
    return f"{body}-{_course_sign(body)}"

def _validate_course_key(key: str) -> tuple[bool, int]:
    """Verifica firma de la key. Retorna (válida, días)."""
    parts = key.strip().upper().split("-")
    # Formato esperado: CURSO-NNN-XXXX-XXXX-SIG4 (5 partes)
    if len(parts) != 5 or parts[0] != "CURSO":
        return False, 0
    try:
        days = int(parts[1])
        if not (1 <= days <= 999):
            return False, 0
    except ValueError:
        return False, 0
    body = "-".join(parts[:4])
    if parts[4] != _course_sign(body):
        return False, 0
    return True, days

def activate_course_key(key: str) -> tuple[bool, str]:
    """Activa un código de curso. Sin internet, sin Polar."""
    valid, days = _validate_course_key(key)
    if not valid:
        return False, "Código de curso inválido"

    existing = _load()
    key_upper = key.strip().upper()
    if (existing and existing.get("type") == "course"
            and existing.get("license_key") == key_upper
            and existing.get("hwid") == get_hwid()):
        try:
            rem = int((_dt(existing["course_expires"]) - _now()).total_seconds())
            if rem > 0:
                return True, _("Código ya activado — {} días restantes").format(rem // 86400)
        except Exception:
            pass

    expires = (_now() + datetime.timedelta(days=days)).isoformat()
    _save({
        "type": "course",
        "hwid": get_hwid(),
        "license_key": key_upper,
        "activated": _now_s(),
        "last_check": _now_s(),
        "clock_tamper": 0,
        "course_expires": expires,
        "course_days": days,
    })
    return True, _("Acceso de curso activado — {} días").format(days)


# ══════════════════════════════════════════════════════════════════════════════
#  CHECK PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

def check_license() -> tuple[bool, int, str]:
    data = _load()
    now = _now()

    if data is None:
        return False, 0, "no_license"
    if data.get("hwid") != get_hwid():
        return False, 0, "wrong_pc"
    if data.get("clock_tamper", 0) >= 3:
        return False, 0, "tampered"

    data = _heartbeat(data)
    _save(data)

    # PRO
    if data.get("type") == "pro":
        if data.get("offline_expires"):
            try:
                rem = int((_dt(data["offline_expires"]) - now).total_seconds())
                return (True, rem, "pro") if rem > 0 else (False, 0, "expired")
            except Exception:
                return False, 0, "expired"

        key = data.get("license_key", "")
        act_id = data.get("activation_id")
        last_val = data.get("last_validate", "")

        recheck = True
        if last_val:
            try: recheck = (now - _dt(last_val)).days >= 7
            except Exception: pass

        if recheck and key:
            ok, msg, resp = polar_validate(key, activation_id=act_id)
            if ok:
                act_in = (resp.get("activation") or {}).get("id")
                if act_in:
                    data["activation_id"] = act_in
                data["last_validate"] = _now_s()
                _save(data)
                return True, 999999, "pro"
            if "revoc" in msg.lower() or "disabled" in msg.lower():
                return False, 0, "expired"
            if last_val:
                hours_off = (now - _dt(last_val)).total_seconds() / 3600
                if hours_off < 48:
                    remaining_grace = int((48 - hours_off) * 3600)
                    return True, remaining_grace, "pro_offline"
            return False, 0, "expired"

        return True, 999999, "pro"

    # COURSE
    if data.get("type") == "course":
        expires = data.get("course_expires")
        if expires:
            try:
                rem = int((_dt(expires) - now).total_seconds())
                return (True, rem, "course") if rem > 0 else (False, 0, "expired")
            except Exception:
                pass
        return False, 0, "expired"

    # TRIAL
    if data.get("type") == "trial":
        elapsed = int((now - _dt(data["trial_start"])).total_seconds())
        rem = max(0, TRIAL_SECONDS - elapsed)
        if rem > 0:
            return True, rem, "trial"
        return False, 0, "expired"

    return False, 0, "expired"


# ══════════════════════════════════════════════════════════════════════════════
#  ACCIONES
# ══════════════════════════════════════════════════════════════════════════════

def start_trial() -> int:
    # Verificar que no haya trial previo en ningún archivo
    existing = _load()
    if existing and existing.get("type") == "trial":
        # Ya existe trial → no resetear, devolver lo que queda
        elapsed = int((_now() - _dt(existing["trial_start"])).total_seconds())
        return max(0, TRIAL_SECONDS - elapsed)

    _save({"type": "trial", "hwid": get_hwid(), "trial_start": _now_s(),
           "last_check": _now_s(), "clock_tamper": 0})
    return TRIAL_SECONDS


def activate_license(license_key: str) -> tuple[bool, str]:
    key = license_key.strip()
    if not key:
        return False, "Pegá una licencia válida"

    # Código de curso — no va a Polar
    if key.upper().startswith("CURSO-"):
        return activate_course_key(key)

    # Ya activada localmente?
    existing = _load()
    if (existing and existing.get("type") == "pro"
            and existing.get("license_key") == key
            and existing.get("hwid") == get_hwid()
            and existing.get("activation_id")):
        ok, _, _ = polar_validate(key, activation_id=existing["activation_id"])
        if ok:
            existing["last_check"] = _now_s()
            existing["last_validate"] = _now_s()
            _save(existing)
            return True, "Licencia ya activada en este equipo"

    # Intentar activate
    act_ok, act_msg, act_data = polar_activate(key, label=f"PyScout-{get_hwid()}")
    activation_id = None

    if act_ok:
        activation_id = act_data.get("id")
    elif act_msg == "LIMIT_REACHED":
        return False, (
            "Esta licencia ya está activada en otro dispositivo.\n\n"
            "Cada licencia permite 1 activación.\n"
            "Desactivala desde Polar (Purchases → License Keys → Deactivate)\n"
            "o contactá soporte.")
    elif "no encontrada" in act_msg.lower():
        return False, "Licencia no encontrada"
    elif "conexión" in act_msg.lower() or "timeout" in act_msg.lower():
        return False, act_msg
    else:
        # Benefit sin activation limit → solo validate
        val_ok, val_msg, val_data = polar_validate(key)
        if not val_ok:
            return False, val_msg
        if val_data.get("status") != "granted":
            return False, f"Licencia no habilitada: {val_data.get('status')}"
        _save({"type": "pro", "hwid": get_hwid(), "license_key": key,
               "activation_id": None, "activated": _now_s(), "last_check": _now_s(),
               "last_validate": _now_s(), "clock_tamper": 0})
        return True, "Licencia activada correctamente"

    # Validate con activation_id
    val_ok, val_msg, val_data = polar_validate(key, activation_id=activation_id)
    if not val_ok:
        return False, val_msg
    if val_data.get("status") != "granted":
        return False, f"Licencia no habilitada: {val_data.get('status')}"

    _save({"type": "pro", "hwid": get_hwid(), "license_key": key,
           "activation_id": activation_id, "activated": _now_s(),
           "last_check": _now_s(), "last_validate": _now_s(), "clock_tamper": 0})
    return True, "Licencia activada correctamente"


def deactivate_license() -> tuple[bool, str]:
    data = _load()
    if not data or data.get("type") != "pro":
        return False, "No hay licencia activa"
    key, act_id = data.get("license_key", ""), data.get("activation_id", "")
    if not key:
        return False, "Datos incompletos"
    if act_id:
        ok, msg = polar_deactivate(key, act_id)
        if not ok:
            return False, msg
    # Borrar TODOS los archivos
    for p in _PATHS:
        try: p.unlink()
        except Exception: pass
    if sys.platform == "win32" and winreg:
        try:
            key_r = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key_r, _REG_VALUE)
            winreg.CloseKey(key_r)
        except Exception:
            pass
    return True, "Licencia desactivada."


def get_license_info() -> dict:
    data = _load()
    valid, remaining, typ = check_license()
    if not data:
        return {"type": "none", "hwid": get_hwid(), "valid": False, "remaining_seconds": 0}
    return {"type": typ, "hwid": get_hwid(), "valid": valid,
            "remaining_seconds": remaining,
            "remaining_text": format_seconds_compact(remaining) if typ in ("trial", "grace") else "",
            "activation_id": data.get("activation_id", "")}


def get_checkout_url() -> str:
    return POLAR_CHECKOUT_URL


# ══════════════════════════════════════════════════════════════════════════════
#  OFFLINE
# ══════════════════════════════════════════════════════════════════════════════

def generate_offline_license(hwid: str, days: int) -> str:
    return _enc({"hwid": hwid, "expires": (_now() + datetime.timedelta(days=days)).isoformat(),
                 "issued": _now_s(), "days": days, "type": "offline"})

def install_offline_license(lic_text: str) -> tuple[bool, str]:
    try:
        d = _dec(lic_text.strip())
        if d.get("hwid") != get_hwid():
            return False, f"Licencia para otro equipo.\nTu HWID: {get_hwid()}"
        _save({"type": "pro", "hwid": get_hwid(), "license_key": "OFFLINE",
               "activation_id": None, "activated": _now_s(), "last_check": _now_s(),
               "last_validate": _now_s(), "offline_expires": d["expires"], "clock_tamper": 0})
        return True, f"Licencia instalada. {max(0, (_dt(d['expires']) - _now()).days)} días."
    except Exception as e:
        return False, f"Licencia inválida: {e}"


# ══════════════════════════════════════════════════════════════════════════════
#  CLI
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"\n  PyScout License Manager (7 días trial, 5 archivos)")
        print(f"  HWID: {get_hwid()}")
        print(f"\n  Ubicaciones:")
        for i, p in enumerate(_PATHS, 1):
            exists = "✓" if p.exists() else "✗"
            print(f"    {i}. [{exists}] {p}")
        if sys.platform == "win32" and winreg:
            try:
                k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY)
                winreg.CloseKey(k)
                print(f"    6. [✓] Registro: HKCU\\{_REG_KEY}")
            except Exception:
                print(f"    6. [✗] Registro: HKCU\\{_REG_KEY}")
        print(f"\n  Comandos: verificar | trial | activar <KEY> | desactivar | generar <HWID> <dias> | curso <N> <dias> | limpiar")
        sys.exit(0)

    c = sys.argv[1].lower()

    if c == "verificar":
        v, r, t = check_license()
        print(f"\n  {t} | válida={v} | restante={format_seconds_compact(r) if t in ('trial','grace') else r}\n")

    elif c == "trial":
        r = start_trial()
        print(f"\n  Trial: {r}s ({format_seconds_compact(r)})\n")

    elif c == "activar" and len(sys.argv) >= 3:
        ok, m = activate_license(sys.argv[2])
        print(f"\n  {'OK' if ok else 'FAIL'}: {m}\n")

    elif c == "desactivar":
        ok, m = deactivate_license()
        print(f"\n  {'OK' if ok else 'FAIL'}: {m}\n")

    elif c == "generar" and len(sys.argv) >= 4:
        h, d = sys.argv[2].upper(), int(sys.argv[3])
        Path(f"license_{h[:8]}.lic").write_text(generate_offline_license(h, d), encoding="utf-8")
        print(f"\n  Generado: license_{h[:8]}.lic ({d} días)\n")

    elif c == "curso":
        n    = int(sys.argv[2]) if len(sys.argv) >= 3 else 20
        days = int(sys.argv[3]) if len(sys.argv) >= 4 else 90
        print(f"\n  PyScout — {n} código(s) de curso ({days} días)\n")
        lines = []
        for i in range(1, n + 1):
            k = generate_course_key(days)
            print(f"  {i:2d}. {k}")
            lines.append(k)
        date_str = datetime.datetime.now().strftime("%Y%m%d")
        out = Path(f"curso_keys_{date_str}_{n}x{days}d.txt")
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\n  Guardado en: {out}\n")

    elif c == "limpiar":
        # Borrar TODOS los archivos (para testing)
        for p in _PATHS:
            try: p.unlink(); print(f"  Borrado: {p}")
            except Exception: print(f"  No existe: {p}")
        if sys.platform == "win32" and winreg:
            try:
                k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_SET_VALUE)
                winreg.DeleteValue(k, _REG_VALUE)
                winreg.CloseKey(k)
                print(f"  Borrado: Registro")
            except Exception:
                print(f"  No existe: Registro")
        print()

    else:
        print(f"  Desconocido: {c}")