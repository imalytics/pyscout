from __future__ import annotations
import uuid, json
from dataclasses import dataclass, field, asdict
from typing import Optional
from PySide6.QtCore import QObject, Signal


@dataclass
class Button:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    label: str = ""
    color: str = "#E8821A"
    hotkey: str = ""
    pad_before: int = -1
    pad_after: int = -1


@dataclass
class VideoSource:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    path: str = ""
    name: str = ""
    last_pos: float = 0.0   # última posición del playhead para restaurar al volver


@dataclass
class Clip:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    category: str = ""     # categoría base (ej: "Poste") — para filtros
    color: str = "#E8821A"
    video_path: str = ""
    video_name: str = ""
    timestamp: str = "0:00:00"
    time_sec: float = 0.0
    start_sec: float = 0.0
    end_sec: float = 10.0
    note: str = ""
    in_presentation: bool = False

    @property
    def duration(self) -> float:
        return max(0.1, self.end_sec - self.start_sec)


@dataclass
class PresentationItem:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = "clip"
    name: str = ""
    category: str = ""     # categoría original (para filtros en Ajuste)
    color: str = "#E8821A"
    note: str = ""
    video_path: str = ""
    video_name: str = ""
    timestamp: str = ""
    clip_start: float = 0.0
    clip_dur: float = 10.0
    show_overlay: bool = False
    image_path: str = ""
    image_dur: float = 3.0
    visible: bool = True

    @property
    def duration(self) -> float:
        return self.image_dur if self.type == "image" else self.clip_dur


class AppState(QObject):
    buttons_changed      = Signal()
    clips_changed        = Signal()
    presentation_changed = Signal()
    presentations_changed = Signal()  # multi-pres box changed
    sources_changed      = Signal()          # lista de fuentes cambió
    active_source_changed = Signal(str, str) # path, name
    project_changed      = Signal(str)
    overlay_changed      = Signal(bool)
    toast_requested      = Signal(str)
    undo_redo_changed    = Signal(bool, bool) # can_undo, can_redo
    global_mute_changed  = Signal(bool)       # True = all players muted

    MAX_UNDO = 50

    def __init__(self):
        super().__init__()
        self.project_name: str = "Sin título"
        self.buttons: list[Button] = []
        self.video_sources: list[VideoSource] = []
        self.active_source_idx: int = -1
        self.clips: list[Clip] = []
        self.presentation: list[PresentationItem] = []
        self.presentations: list[list[PresentationItem]] = [[]]
        self.presentation_names: list[str] = []
        self.active_pres_idx: int = 0
        self.default_pad: float = 5.0
        self.overlay_enabled: bool = False
        self.global_mute: bool = False
        self._undo_stack: list[dict] = []
        self._redo_stack: list[dict] = []

    # ── Undo / Redo ───────────────────────────────────────────────────────────

    def _snapshot(self) -> dict:
        return {
            "buttons": [asdict(b) for b in self.buttons],
            "clips": [asdict(c) for c in self.clips],
            "presentation": [asdict(p) for p in self.presentation],
            "presentations": [[asdict(p) for p in slot] for slot in self.presentations],
            "presentation_names": list(self.presentation_names),
            "active_pres_idx": self.active_pres_idx,
        }

    def _restore_snapshot(self, snap: dict):
        self.buttons = [Button(**b) for b in snap.get("buttons", [])]
        self.clips   = [Clip(**c) for c in snap.get("clips", [])]

        # Restaurar multi-presentación completa
        self.presentation_names = list(snap.get("presentation_names", []))
        raw_pres = snap.get("presentations")
        if raw_pres is not None:
            self.presentations = [
                [PresentationItem(**p) for p in slot] for slot in raw_pres
            ]
            self.active_pres_idx = snap.get("active_pres_idx", 0)
            if self.presentations and 0 <= self.active_pres_idx < len(self.presentations):
                self.presentation = self.presentations[self.active_pres_idx]
            else:
                self.presentation = []
                self.presentations = [[]]
                self.active_pres_idx = 0
        else:
            # Compatibilidad con snapshots viejos sin multi-presentación
            self.presentation = [PresentationItem(**p) for p in snap.get("presentation", [])]
            self.presentations = [self.presentation]
            self.active_pres_idx = 0

        self.buttons_changed.emit()
        self.clips_changed.emit()
        self.presentation_changed.emit()
        self.presentations_changed.emit()

    def push_undo(self):
        """Guardar snapshot antes de una operación destructiva."""
        self._undo_stack.append(self._snapshot())
        if len(self._undo_stack) > self.MAX_UNDO:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        self.undo_redo_changed.emit(True, False)

    def undo(self):
        if not self._undo_stack:
            return
        self._redo_stack.append(self._snapshot())
        snap = self._undo_stack.pop()
        self._restore_snapshot(snap)
        self.undo_redo_changed.emit(bool(self._undo_stack), True)
        self.toast_requested.emit("Deshacer")

    def redo(self):
        if not self._redo_stack:
            return
        self._undo_stack.append(self._snapshot())
        snap = self._redo_stack.pop()
        self._restore_snapshot(snap)
        self.undo_redo_changed.emit(True, bool(self._redo_stack))
        self.toast_requested.emit("Rehacer")

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    # ── Propiedades del source activo ─────────────────────────────────────────
    @property
    def active_video_path(self) -> str:
        s = self._active_source()
        return s.path if s else ""

    @property
    def active_video_name(self) -> str:
        s = self._active_source()
        return s.name if s else ""

    def _active_source(self) -> Optional[VideoSource]:
        if 0 <= self.active_source_idx < len(self.video_sources):
            return self.video_sources[self.active_source_idx]
        return None

    # ── Video sources ─────────────────────────────────────────────────────────
    def add_video_source(self, path: str) -> int:
        """Agrega una fuente y la activa. Devuelve el índice."""
        # Si ya existe, solo activarla
        for i, vs in enumerate(self.video_sources):
            if vs.path == path:
                self._switch_source(i)
                return i
        if len(self.video_sources) >= 10:
            self.toast_requested.emit("Máximo 10 videos fuente")
            return self.active_source_idx
        name = path.replace("\\", "/").split("/")[-1]
        vs = VideoSource(path=path, name=name)
        self.video_sources.append(vs)
        idx = len(self.video_sources) - 1
        self._switch_source(idx)
        self.sources_changed.emit()
        return idx

    def remove_video_source(self, idx: int):
        if not (0 <= idx < len(self.video_sources)):
            return
        self.video_sources.pop(idx)
        # Ajustar índice activo
        if not self.video_sources:
            self.active_source_idx = -1
            self.active_source_changed.emit("", "")
        else:
            new_idx = min(idx, len(self.video_sources) - 1)
            self._switch_source(new_idx)
        self.sources_changed.emit()

    def switch_source(self, idx: int):
        if 0 <= idx < len(self.video_sources):
            self._switch_source(idx)

    def _switch_source(self, idx: int):
        self.active_source_idx = idx
        vs = self.video_sources[idx]
        self.active_source_changed.emit(vs.path, vs.name)

    def save_source_position(self, position: float):
        """Guarda la posición actual del video antes de cambiar de source."""
        s = self._active_source()
        if s:
            s.last_pos = position

    # ── Botones ───────────────────────────────────────────────────────────────
    def add_button(self, label: str, color: str = "#1c1c1c") -> Button:
        self.push_undo()
        btn = Button(label=label, color=color)
        self.buttons.append(btn)
        self.buttons_changed.emit()
        return btn

    def remove_button(self, btn_id: str):
        self.push_undo()
        self.buttons = [b for b in self.buttons if b.id != btn_id]
        self.buttons_changed.emit()

    # ── Clips ─────────────────────────────────────────────────────────────────
    def add_clip(self, button: Button, time_sec: float, video_duration: float = 0.0) -> Clip:
        self.push_undo()
        from utils.time_utils import fmt_time
        pad_b = getattr(button, 'pad_before', -1); pad_b = pad_b if pad_b >= 0 else self.default_pad
        pad_a = getattr(button, 'pad_after',  -1); pad_a = pad_a if pad_a >= 0 else self.default_pad
        # Auto-numeración: contar clips existentes con la misma categoría
        base_label = button.label
        count = sum(1 for c in self.clips if c.category == base_label)
        display_name = f"{base_label} #{count + 1}"
        end = time_sec + pad_a
        if video_duration > 0:
            end = min(end, video_duration)
        clip = Clip(
            name=display_name,
            category=base_label,
            color=button.color,
            video_path=self.active_video_path,
            video_name=self.active_video_name,
            timestamp=fmt_time(time_sec), time_sec=time_sec,
            start_sec=max(0, time_sec - pad_b),
            end_sec=end,
        )
        self.clips.append(clip)
        self.clips_changed.emit()
        self.toast_requested.emit(f"{display_name} registrado — {clip.timestamp}")
        return clip

    def update_clip(self, clip_id: str, **kwargs):
        for c in self.clips:
            if c.id == clip_id:
                for k, v in kwargs.items():
                    setattr(c, k, v)
        self.clips_changed.emit()

    def remove_clip(self, clip_id: str):
        self.push_undo()
        self.clips = [c for c in self.clips if c.id != clip_id]
        self.clips_changed.emit()

    # ── Presentación ──────────────────────────────────────────────────────────
    def add_clip_to_presentation(self, clip: Clip, clip_start: float, clip_dur: float):
        self.push_undo()
        item = PresentationItem(
            type="clip", name=clip.name,
            category=getattr(clip, 'category', '') or clip.name,
            color="", note=clip.note,
            video_path=clip.video_path, video_name=clip.video_name,
            timestamp=clip.timestamp, clip_start=clip_start, clip_dur=clip_dur,
            show_overlay=self.overlay_enabled,
        )
        # Agregar al slot activo, no siempre al 0
        self.presentations[self.active_pres_idx].append(item)
        self.presentation = self.presentations[self.active_pres_idx]
        clip.in_presentation = True
        self.presentation_changed.emit()
        self.presentations_changed.emit()
        self.toast_requested.emit(f'"{clip.name}" agregado a la presentación')

    def add_image_to_presentation(self, image_path: str, dur: float = 3.0):
        self.push_undo()
        name = image_path.replace("\\", "/").split("/")[-1].rsplit(".", 1)[0]
        item = PresentationItem(type="image", name=name, color="",
                                image_path=image_path, image_dur=dur)
        self.presentation.append(item)
        self.presentations[self.active_pres_idx] = self.presentation
        self.presentation_changed.emit()
        self.presentations_changed.emit()
        self.toast_requested.emit(f'Imagen "{name}" agregada')

    def update_pres_item(self, item_id: str, **kwargs):
        for p in self.presentation:
            if p.id == item_id:
                # Solo push_undo si algo cambió realmente
                changed = any(getattr(p, k, None) != v for k, v in kwargs.items() if hasattr(p, k))
                if changed:
                    self.push_undo()
                    for k, v in kwargs.items():
                        if hasattr(p, k):
                            setattr(p, k, v)
                    self._sync_active_slot()
                break
        self.presentation_changed.emit()

    def remove_pres_item(self, item_id: str):
        self.push_undo()
        self.presentation = [p for p in self.presentation if p.id != item_id]
        self._sync_active_slot()
        self.presentation_changed.emit()

    def remove_pres_items(self, ids: set):
        if not ids:
            return
        self.push_undo()
        self.presentation = [p for p in self.presentation if p.id not in ids]
        self._sync_active_slot()
        self.presentation_changed.emit()

    def duplicate_pres_item(self, item_id: str):
        """Duplica un item de la presentación activa, insertándolo justo después."""
        item = next((p for p in self.presentation if p.id == item_id), None)
        if not item:
            return
        self.push_undo()
        clone = PresentationItem(**{k: v for k, v in asdict(item).items()})
        clone.id = str(uuid.uuid4())
        idx = self.presentation.index(item)
        self.presentation.insert(idx + 1, clone)
        self.presentations[self.active_pres_idx] = self.presentation
        self.presentation_changed.emit()
        self.toast_requested.emit(f'"{item.name}" duplicado')

    def reorder_presentation(self, from_idx: int, to_idx: int):
        self.push_undo()
        item = self.presentation.pop(from_idx)
        self.presentation.insert(to_idx, item)
        self._sync_active_slot()
        self.presentation_changed.emit()

    # ── Multi-presentación ────────────────────────────────────────────────────

    def _sync_active_slot(self):
        """Mantener presentations[active_pres_idx] = presentation siempre."""
        if 0 <= self.active_pres_idx < len(self.presentations):
            self.presentations[self.active_pres_idx] = self.presentation

    def active_presentation(self) -> list:
        """La presentación activa en el box (siempre sincronizada con self.presentation)."""
        if 0 <= self.active_pres_idx < len(self.presentations):
            return self.presentations[self.active_pres_idx]
        return self.presentations[0]

    def add_presentation_slot(self) -> bool:
        if len(self.presentations) >= 5:
            self.toast_requested.emit("Máximo 5 listados")
            return False
        self.push_undo()
        self.presentations.append([])
        self.presentation_names.append("")
        self.presentations_changed.emit()
        return True

    def remove_presentation_slot(self, idx: int):
        if len(self.presentations) <= 1:
            self.toast_requested.emit("Debe quedar al menos un listado")
            return
        if not (0 <= idx < len(self.presentations)):
            return
        self.push_undo()
        self.presentations.pop(idx)
        if idx < len(self.presentation_names):
            self.presentation_names.pop(idx)
        self.active_pres_idx = min(self.active_pres_idx, len(self.presentations) - 1)
        self._sync_presentation()
        self.presentations_changed.emit()

    def rename_presentation_slot(self, idx: int, name: str):
        if not (0 <= idx < len(self.presentations)):
            return
        self.push_undo()
        while len(self.presentation_names) <= idx:
            self.presentation_names.append("")
        self.presentation_names[idx] = name.strip()
        self.presentations_changed.emit()

    def set_active_presentation(self, idx: int):
        if 0 <= idx < len(self.presentations):
            self.active_pres_idx = idx
            self._sync_presentation()
            self.presentations_changed.emit()

    def _sync_presentation(self):
        """Mantiene self.presentation sincronizada con el slot activo."""
        self.presentation = self.active_presentation()
        self.presentation_changed.emit()

    def move_item_between_slots(self, item_id: str, from_idx: int, to_idx: int):
        """Mueve un item de una presentación a otra."""
        if from_idx == to_idx: return
        if not (0 <= from_idx < len(self.presentations)): return
        if not (0 <= to_idx < len(self.presentations)): return
        src_list = self.presentations[from_idx]
        item = next((p for p in src_list if p.id == item_id), None)
        if not item: return
        self.push_undo()
        src_list.remove(item)
        self.presentations[to_idx].append(item)
        self._sync_presentation()
        self.presentations_changed.emit()

    def copy_items_to_slot(self, item_ids: list[str], from_idx: int, to_idx: int):
        """Copia items de una presentación a otra (no los remueve del origen)."""
        if from_idx == to_idx:
            return
        if not (0 <= from_idx < len(self.presentations)):
            return
        if not (0 <= to_idx < len(self.presentations)):
            return
        src_list = self.presentations[from_idx]
        items = [p for p in src_list if p.id in set(item_ids)]
        if not items:
            return
        self.push_undo()
        import copy
        for item in items:
            clone = PresentationItem(**{
                k: v for k, v in asdict(item).items()
            })
            clone.id = str(uuid.uuid4())  # nuevo ID para la copia
            self.presentations[to_idx].append(clone)
        self._sync_presentation()
        self.presentations_changed.emit()
        self.toast_requested.emit(
            f'{len(items)} item{"s" if len(items) > 1 else ""} copiado{"s" if len(items) > 1 else ""} a listado {to_idx + 1}'
        )

    def set_overlay(self, enabled: bool):
        self.overlay_enabled = enabled
        self.overlay_changed.emit(enabled)

    # ── Persistencia ──────────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "project_name": self.project_name,
            "default_pad": self.default_pad,
            "overlay_enabled": self.overlay_enabled,
            "buttons": [asdict(b) for b in self.buttons],
            "video_sources": [asdict(v) for v in self.video_sources],
            "active_source_idx": self.active_source_idx,
            "clips": [asdict(c) for c in self.clips],
            "presentation": [asdict(p) for p in self.presentation],
            "presentations": [[asdict(p) for p in slot] for slot in self.presentations],
            "presentation_names": list(self.presentation_names),
            "active_pres_idx": self.active_pres_idx,
        }

    def from_dict(self, data: dict):
        self.project_name    = data.get("project_name", "Sin título")
        self.default_pad     = data.get("default_pad", 5.0)
        self.overlay_enabled = data.get("overlay_enabled", False)
        self.buttons         = [Button(**b) for b in data.get("buttons", [])]
        self.video_sources   = [VideoSource(**v) for v in data.get("video_sources", [])]
        self.active_source_idx = data.get("active_source_idx", -1)
        self.clips           = [Clip(**c) for c in data.get("clips", [])]
        self.presentation    = [PresentationItem(**p) for p in data.get("presentation", [])]
        
        # Cargar todos los listados (presentations)
        presentations_data = data.get("presentations", [[]])
        self.presentations = [[PresentationItem(**p) for p in slot] for slot in presentations_data]
        self.presentation_names = list(data.get("presentation_names", []))
        self.active_pres_idx = data.get("active_pres_idx", 0)
        
        # Sincronizar presentation con el listado activo
        if self.presentations and 0 <= self.active_pres_idx < len(self.presentations):
            self.presentation = self.presentations[self.active_pres_idx]
        
        self.buttons_changed.emit()
        self.clips_changed.emit()
        self.presentation_changed.emit()
        self.presentations_changed.emit()  # Emitir para actualizar la UI de listados
        self.sources_changed.emit()
        if self._active_source():
            vs = self._active_source()
            self.active_source_changed.emit(vs.path, vs.name)
        self.project_changed.emit(self.project_name)

    def save_to_file(self, path: str) -> bool:
        """Guardar proyecto — escritura atómica para evitar corrupción."""
        import os
        try:
            data = self.to_dict()
            folder = os.path.dirname(path)
            if folder:
                os.makedirs(folder, exist_ok=True)
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)  # Atómico en la mayoría de los OS
            return True
        except Exception as e:
            print(f"[state] save error: {e}")
            # Intentar limpiar el .tmp
            try:
                if os.path.exists(tmp): os.unlink(tmp)
            except Exception:
                pass
            return False

    def load_from_file(self, path: str) -> bool:
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.from_dict(json.load(f))
            return True
        except Exception as e:
            print(f"[state] load error: {e}"); return False


state = AppState()