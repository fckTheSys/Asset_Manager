# -*- coding: utf-8 -*-
import math
import os
from typing import Dict, List, Optional, Tuple

import c4d


RIG_NAME = "TTB_CameraShake_Rig"
TAG_CODE = "# TTB Camera Shake Tag"


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


def _iter_all_objects(doc: c4d.documents.BaseDocument):
    op = doc.GetFirstObject()
    while op:
        yield op
        child = op.GetDown()
        if child:
            for sub in _iter_all_children(child):
                yield sub
        op = op.GetNext()


def _iter_all_children(op: c4d.BaseObject):
    while op:
        yield op
        child = op.GetDown()
        if child:
            for sub in _iter_all_children(child):
                yield sub
        op = op.GetNext()


def find_cameras(doc: c4d.documents.BaseDocument) -> List[c4d.BaseObject]:
    """Return all camera objects in the document."""
    cams: List[c4d.BaseObject] = []
    for op in _iter_all_objects(doc):
        if _is_camera_object(op):
            cams.append(op)
    return cams


def find_selected_cameras(doc: c4d.documents.BaseDocument) -> List[c4d.BaseObject]:
    """Return selected camera objects, including selected children."""
    try:
        selected = doc.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_CHILDREN)
    except Exception:
        selected = []

    cams: List[c4d.BaseObject] = []
    seen = set()
    for op in selected or []:
        if not _is_camera_object(op):
            continue
        try:
            guid = int(op.GetGUID())
        except Exception:
            guid = id(op)
        if guid in seen:
            continue
        seen.add(guid)
        cams.append(op)
    return cams


def get_or_create_shake_rig(doc: c4d.documents.BaseDocument) -> c4d.BaseObject:
    """Find existing rig null or create new one."""
    for op in _iter_all_objects(doc):
        if op.GetName() == RIG_NAME and op.GetType() == c4d.Onull:
            return op

    rig = c4d.BaseObject(c4d.Onull)
    rig.SetName(RIG_NAME)
    doc.InsertObject(rig)
    c4d.EventAdd()
    return rig


def _find_ud_by_name(obj: c4d.BaseObject, name: str) -> Optional[c4d.DescID]:
    """Find user data DescID by display name."""
    for did, bc in obj.GetUserDataContainer():
        try:
            n = bc[c4d.DESC_NAME] or ""
        except Exception:
            n = ""
        if n == name:
            return did
    return None


def _add_group(obj: c4d.BaseObject, name: str) -> c4d.DescID:
    bc = c4d.GetCustomDataTypeDefault(c4d.DTYPE_GROUP)
    bc[c4d.DESC_NAME] = name
    desc_id = obj.AddUserData(bc)
    return desc_id


def _add_real(
    obj: c4d.BaseObject,
    name: str,
    parent: Optional[c4d.DescID],
    default: float,
    minimum: float,
    maximum: float,
    step: float,
) -> c4d.DescID:
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


def _add_bool(
    obj: c4d.BaseObject,
    name: str,
    parent: Optional[c4d.DescID],
    default: bool,
) -> c4d.DescID:
    bc = c4d.GetCustomDataTypeDefault(c4d.DTYPE_BOOL)
    bc[c4d.DESC_NAME] = name
    if parent is not None:
        bc[c4d.DESC_PARENTGROUP] = parent
    desc_id = obj.AddUserData(bc)
    obj[desc_id] = bool(default)
    return desc_id


def setup_shake_userdata(rig: c4d.BaseObject) -> Dict[str, c4d.DescID]:
    """
    Ensure User Data for camera shake exists on rig.
    Returns mapping from logical keys to DescID.
    """
    existing = {}
    for did, bc in rig.GetUserDataContainer():
        try:
            n = bc[c4d.DESC_NAME] or ""
        except Exception:
            n = ""
        if not n:
            continue
        existing[n] = did

    group = existing.get("Camera Shake")
    if group is None:
        group = _add_group(rig, "Camera Shake")

    def ensure_real(
        ui_name: str,
        key: str,
        default: float,
        minimum: float,
        maximum: float,
        step: float,
    ):
        did = existing.get(ui_name)
        if did is None:
            did = _add_real(rig, ui_name, group, default, minimum, maximum, step)
        ids[key] = did

    def ensure_bool(ui_name: str, key: str, default: bool):
        did = existing.get(ui_name)
        if did is None:
            did = _add_bool(rig, ui_name, group, default)
        ids[key] = did

    ids: Dict[str, c4d.DescID] = {}
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


def create_shake_camera_for_source(
    doc: c4d.documents.BaseDocument,
    src_cam: c4d.BaseObject,
    rig: c4d.BaseObject,
) -> Optional[c4d.BaseObject]:
    """Create a shake camera for given source camera and copy parameters."""
    if not _is_camera_object(src_cam):
        return None

    base_name = src_cam.GetName()
    shake_name = f"{base_name}_Shake"

    # Check if already exists as child of rig or source
    for op in _iter_all_objects(doc):
        if _is_camera_object(op) and op.GetName() == shake_name:
            return op

    shake_cam = c4d.BaseObject(c4d.Ocamera)
    shake_cam.SetName(shake_name)

    # Copy transform
    try:
        shake_cam.SetMg(src_cam.GetMg())
    except Exception:
        pass

    # Copy core camera parameters where possible
    for param_id in (
        c4d.CAMERAOBJECT_FOV,
        c4d.CAMERAOBJECT_APERTURE,
        c4d.CAMERAOBJECT_FOCUS,
        c4d.CAMERAOBJECT_NEAR_CLIPPING,
        c4d.CAMERAOBJECT_FAR_CLIPPING,
        c4d.CAMERAOBJECT_PROJECTION,
    ):
        try:
            shake_cam[param_id] = src_cam[param_id]
        except Exception:
            continue

    # Parent under rig to keep all shake cameras grouped
    doc.InsertObject(shake_cam)
    shake_cam.InsertUnderLast(rig)
    c4d.EventAdd()
    return shake_cam


def _noise_1d(t: float, seed: int) -> float:
    """Simple pseudo-noise based on sin/cos; output in [-1, 1]."""
    v = math.sin(t * 12.9898 + seed * 78.233) * 43758.5453
    return 2.0 * (v - math.floor(v + 0.5))


def generate_shake_offset(
    time_sec: float,
    cfg: Dict[str, float],
) -> Tuple[c4d.Vector, c4d.Vector]:
    """
    Compute position and rotation offsets based on config.

    Returns:
        (pos_offset, rot_offset) – both in scene units / degrees.
    """
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


def apply_shake_to_cameras(
    doc: c4d.documents.BaseDocument,
    rig: c4d.BaseObject,
    frame: int,
) -> None:
    """
    Runtime application of shake to all shake cameras under rig.
    Intended to be called from a Python Tag.
    """
    if rig is None:
        return

    data_ids = setup_shake_userdata(rig)
    cfg = _read_config(rig, data_ids)

    enable = bool(cfg.get("enable", True))
    if not enable:
        # Reset offsets to zero
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


def ensure_python_tag(rig: c4d.BaseObject) -> c4d.BaseTag:
    """
    Ensure a Python Tag exists on rig with code that calls apply_shake_to_cameras().
    """
    tag = rig.GetFirstTag()
    while tag:
        if tag.CheckType(c4d.Tpython):
            try:
                code = tag[c4d.TPYTHON_CODE] or ""
            except Exception:
                code = ""
            if TAG_CODE in code:
                return tag
        tag = tag.GetNext()

    tag = c4d.BaseTag(c4d.Tpython)
    tag.SetName("TTB_CameraShake")

    base = os.path.dirname(os.path.abspath(__file__))
    emb_path = os.path.join(base, "camera_shake_tag_embedded.py")
    try:
        with open(emb_path, "r", encoding="utf-8") as f:
            code = f.read()
    except OSError:
        code = (
            f"{TAG_CODE}\n"
            "import c4d\n"
            "def main():\n"
            "    pass  # TTB: missing camera_shake_tag_embedded.py\n"
        )
    try:
        tag[c4d.TPYTHON_CODE] = code
    except Exception:
        pass

    rig.InsertTag(tag)
    c4d.EventAdd()
    return tag


def build_shake_rig_for_cameras(
    doc: c4d.documents.BaseDocument,
    cameras: List[c4d.BaseObject],
) -> c4d.BaseObject:
    """
    High-level helper: create rig, user data, Python tag and shake cameras for given sources.
    """
    rig = get_or_create_shake_rig(doc)
    setup_shake_userdata(rig)
    ensure_python_tag(rig)
    for cam in cameras:
        create_shake_camera_for_source(doc, cam, rig)
    c4d.EventAdd()
    return rig

