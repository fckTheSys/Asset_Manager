# -*- coding: utf-8 -*-
import c4d
from .config import PART_KEYS, VALID_PARTS

def collect_root_objects(doc):
    res = []
    op = doc.GetFirstObject()
    while op:
        res.append(op)
        op = op.GetNext()
    return res

def iter_objects(op):
    while op:
        yield op
        child = op.GetDown()
        if child:
            for x in iter_objects(child):
                yield x
        op = op.GetNext()

def import_fbx(doc, tank_name: str, fbx_path: str):
    before = collect_root_objects(doc)
    before_set = set(before)
    ok = bool(c4d.documents.MergeDocument(doc, fbx_path, c4d.SCENEFILTER_OBJECTS))

    after = collect_root_objects(doc)
    new_roots = [o for o in after if o not in before_set]

    if new_roots:
        null = c4d.BaseObject(c4d.Onull)
        null.SetName(tank_name)
        doc.InsertObject(null)

        for o in new_roots:
            o.SetName(f"{tank_name}_{o.GetName()}")
            o.InsertUnder(null)

    return ok

def find_tank_null(doc, tank_name: str):
    for o in iter_objects(doc.GetFirstObject()):
        if o.GetType() == c4d.Onull and o.GetName() == tank_name:
            return o
    return None

def infer_part_from_name(name: str):
    low = name.lower()
    for k, v in PART_KEYS.items():
        if k in low:
            return v
    # Если ни одно ключевое слово не найдено, часть не определяется.
    # В таком случае материал не назначаем.
    return None


def infer_part_by_material_keys(name: str, mats_by_part: dict):
    """
    Fallback для Universal:
    если часть не распознана стандартными ключами, пробуем найти совпадение
    по произвольным ключам материалов (например Glass, Body, Tracks).
    """
    low = (name or "").lower()
    for key in mats_by_part.keys():
        if key and key.lower() in low:
            return key
    return None

def ensure_texture_tag(obj, mat):
    tag = obj.GetFirstTag()
    while tag:
        if tag.CheckType(c4d.Ttexture) and tag.GetMaterial() == mat:
            # Гарантируем UVW-проекцию даже для уже существующего тега
            try:
                tag[c4d.TEXTURETAG_PROJECTION] = c4d.TEXTURETAG_PROJECTION_UVW
            except Exception:
                pass
            return tag
        tag = tag.GetNext()

    t = c4d.TextureTag()
    t.SetMaterial(mat)
    try:
        t[c4d.TEXTURETAG_PROJECTION] = c4d.TEXTURETAG_PROJECTION_UVW
    except Exception:
        pass
    obj.InsertTag(t)
    return t


def _apply_materials_to_root(doc, root, mats_by_part: dict, use_default_if_no_part: bool = False):
    root_name = root.GetName()
    default_mat = None
    if use_default_if_no_part:
        default_mat = mats_by_part.get("Hull")
        if not default_mat and mats_by_part:
            default_mat = next(iter(mats_by_part.values()))

    count = 0
    for o in iter_objects(root.GetDown()):
        tag = o.GetFirstTag()
        while tag:
            next_tag = tag.GetNext()
            if tag.CheckType(c4d.Ttexture):
                tag.Remove()
            tag = next_tag

        name_for_part = f"{root_name}_{o.GetName()}"
        part = infer_part_from_name(name_for_part)
        if part is None and use_default_if_no_part:
            part = infer_part_by_material_keys(name_for_part, mats_by_part)
        if not use_default_if_no_part and not part:
            continue
        mat = mats_by_part.get(part) if part else default_mat
        if not mat:
            continue
        ensure_texture_tag(o, mat)
        count += 1
    return count


def apply_materials_to_tank(doc, tank_name: str, mats_by_part: dict):
    root = find_tank_null(doc, tank_name)
    if root is None:
        return 0
    return _apply_materials_to_root(doc, root, mats_by_part, use_default_if_no_part=False)


def collect_mats_by_part(doc, tank_name: str):
    mats = {}
    for part in VALID_PARTS:
        wanted = f"{tank_name}_{part}"
        for m in doc.GetMaterials():
            if m.GetName() == wanted:
                mats[part] = m
                break
    return mats


def collect_mats_for_model(doc, model_name: str):
    """
    Универсальный сбор: берём все материалы с префиксом '{model_name}_'
    и используем хвост имени как ключ части/слота.
    """
    mats = {}
    prefix = f"{model_name}_"
    for m in doc.GetMaterials():
        name = m.GetName()
        if not name.startswith(prefix):
            continue
        key = name[len(prefix):]
        if not key:
            continue
        mats[key] = m
    return mats

def apply_materials_generic(doc, model_name: str, mats_by_part: dict):
    """
    Универсальное назначение материалов: null по имени model_name,
    при отсутствии part — дефолт Hull или первый из mats_by_part.
    """
    root = find_tank_null(doc, model_name)
    if root is None:
        return 0
    return _apply_materials_to_root(doc, root, mats_by_part, use_default_if_no_part=True)