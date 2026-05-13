# -*- coding: utf-8 -*-
# TTB Camera Shake Tag — встраивается в сцену; соответствует TankToolBox PLUGIN_VERSION 2.0.0
import math
from typing import Dict, List, Optional, Tuple

import c4d

TAG_MARKER = "# TTB Camera Shake Tag"
RIG_NAME = "TTB_CameraShake_Rig"


def _is_camera_object(op: Optional[c4d.BaseObject]) -> bool:
    if op is None:
        return False
    try:
        return bool(op.CheckType(c4d.Ocamera))
    except Exception:
        try:
            return op.GetType() == c4d.Ocamera
        except Exception:
            return False


def _iter_all_children(op: c4d.BaseObject):
    while op:
        yield op
        child = op.GetDown()
        if child:
            for sub in _iter_all_children(child):
                yield sub
        op = op.GetNext()


def _iter_all_objects(doc: c4d.documents.BaseDocument):
    op = doc.GetFirstObject()
    while op:
        yield op
        child = op.GetDown()
        if child:
            for sub in _iter_all_children(child):
                yield sub
        op = op.GetNext()


def _add_group(obj: c4d.BaseObject, name: str) -> c4d.DescID:
    bc = c4d.GetCustomDataTypeDefault(c4d.DTYPE_GROUP)
    bc[c4d.DESC_NAME] = name
    return obj.AddUserData(bc)


def _add_real(obj, name, parent, default, minimum, maximum, step):
    bc = c4d.GetCustomDataTypeDefault(c4d.DTYPE_REAL)
    bc[c4d.DESC_NAME] = name
    bc[c4d.DESC_MIN] = minimum
    bc[c4d.DESC_MAX] = maximum
    bc[c4d.DESC_STEP] = step
    if parent is not None:
        bc[c4d.DESC_PARENTGROUP] = parent
    gui_id = getattr(c4d, "CUSTOMGUI_REALSLIDER", None)
    if gui_id is not None:
        bc[c4d.DESC_CUSTOMGUI] = gui_id
    desc_id = obj.AddUserData(bc)
    obj[desc_id] = float(default)
    return desc_id


def _add_bool(obj, name, parent, default):
    bc = c4d.GetCustomDataTypeDefault(c4d.DTYPE_BOOL)
    bc[c4d.DESC_NAME] = name
    if parent is not None:
        bc[c4d.DESC_PARENTGROUP] = parent
    desc_id = obj.AddUserData(bc)
    obj[desc_id] = bool(default)
    return desc_id


def setup_shake_userdata(rig: c4d.BaseObject) -> Dict[str, c4d.DescID]:
    existing = {}
    for did, bc in rig.GetUserDataContainer():
        try:
            n = bc[c4d.DESC_NAME] or ""
        except Exception:
            n = ""
        if n:
            existing[n] = did

    group = existing.get("Camera Shake")
    if group is None:
        group = _add_group(rig, "Camera Shake")

    ids: Dict[str, c4d.DescID] = {}

    def ensure_real(ui_name, key, default, minimum, maximum, step):
        did = existing.get(ui_name)
        if did is None:
            did = _add_real(rig, ui_name, group, default, minimum, maximum, step)
        ids[key] = did

    def ensure_bool(ui_name, key, default):
        did = existing.get(ui_name)
        if did is None:
            did = _add_bool(rig, ui_name, group, default)
        ids[key] = did

    ensure_bool("Enable", "enable", True)
    ensure_real("Amplitude_Pos", "amp_pos", 5.0, 0.0, 100.0, 0.1)
    ensure_real("Amplitude_Rot", "amp_rot", 1.0, 0.0, 45.0, 0.1)
    ensure_real("Frequency", "freq", 1.5, 0.0, 10.0, 0.1)
    ensure_real("Seed", "seed", 1.0, 0.0, 9999.0, 1.0)
    return ids


def _read_config(rig: c4d.BaseObject, ids: Dict[str, c4d.DescID]) -> Dict[str, float]:
    res: Dict[str, float] = {}
    for key, did in ids.items():
        try:
            res[key] = rig[did]
        except Exception:
            continue
    return res


def _noise_1d(t: float, seed: int) -> float:
    v = math.sin(t * 12.9898 + seed * 78.233) * 43758.5453
    return 2.0 * (v - math.floor(v + 0.5))


def generate_shake_offset(time_sec: float, cfg: Dict[str, float]) -> Tuple[c4d.Vector, c4d.Vector]:
    amp_pos = float(cfg.get("amp_pos", 0.0))
    amp_rot = float(cfg.get("amp_rot", 0.0))
    freq = float(cfg.get("freq", 0.0))
    seed_val = int(cfg.get("seed", 0))

    if amp_pos <= 0.0 and amp_rot <= 0.0:
        return c4d.Vector(0), c4d.Vector(0)

    if freq <= 0.0:
        freq = 0.001

    t = time_sec * freq

    def n(axis_seed: int) -> float:
        return _noise_1d(t, seed_val + axis_seed)

    pos = c4d.Vector(
        amp_pos * n(11),
        amp_pos * n(17),
        amp_pos * n(23),
    )
    rot_deg = c4d.Vector(
        amp_rot * n(31),
        amp_rot * n(37),
        amp_rot * n(41),
    )
    return pos, rot_deg


def _is_shake_camera(op: c4d.BaseObject) -> bool:
    try:
        return _is_camera_object(op) and op.GetName().endswith("_Shake")
    except Exception:
        return False


def _collect_shake_cameras(rig: c4d.BaseObject) -> List[c4d.BaseObject]:
    cams: List[c4d.BaseObject] = []
    child = rig.GetDown()
    while child:
        if _is_shake_camera(child):
            cams.append(child)
        child = child.GetNext()
    return cams


def apply_shake_to_cameras(doc: c4d.documents.BaseDocument, rig: c4d.BaseObject, frame: int) -> None:
    if rig is None:
        return

    data_ids = setup_shake_userdata(rig)
    cfg = _read_config(rig, data_ids)

    enable = bool(cfg.get("enable", True))
    if not enable:
        for cam in _collect_shake_cameras(rig):
            try:
                cam.SetRelPos(c4d.Vector(0))
                cam.SetRelRot(c4d.Vector(0))
            except Exception:
                continue
        return

    fps = max(1.0, float(doc.GetFps() or 30.0))
    time_sec = float(frame) / fps

    for cam in _collect_shake_cameras(rig):
        try:
            pos_off, rot_off_deg = generate_shake_offset(time_sec, cfg)
            cam.SetRelPos(pos_off)
            rot_rad = c4d.Vector(
                math.radians(rot_off_deg.x),
                math.radians(rot_off_deg.y),
                math.radians(rot_off_deg.z),
            )
            cam.SetRelRot(rot_rad)
        except Exception:
            continue


def main() -> None:
    doc = c4d.documents.GetActiveDocument()
    if doc is None:
        return
    obj = op.GetObject()
    if obj is None:
        return
    frame = doc.GetTime().GetFrame(doc.GetFps())
    apply_shake_to_cameras(doc, obj, frame)
