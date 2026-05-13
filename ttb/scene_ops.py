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

def _polygon_selection_tag_type():
    """ID тега полигонального выделения (SelectionTag, полигоны)."""
    return getattr(c4d, "Tpolygonselection", None)


def _is_polygon_selection_tag(tag):
    tps = _polygon_selection_tag_type()
    if tps is None or tag is None:
        return False
    return tag.GetType() == tps


def _iter_polygon_selection_tags(obj):
    out = []
    tag = obj.GetFirstTag()
    while tag:
        if _is_polygon_selection_tag(tag):
            out.append(tag)
        tag = tag.GetNext()
    return out


def _polygon_selection_has_any_polygons(tag):
    """Пропускаем пустые выделения (нет полигонов в BaseSelect)."""
    try:
        bs = tag.GetBaseSelect()
        if bs is None:
            return False
        return int(bs.GetCount()) > 0
    except Exception:
        return True


def _strip_texture_tags(obj):
    tag = obj.GetFirstTag()
    while tag:
        nxt = tag.GetNext()
        if tag.CheckType(c4d.Ttexture):
            tag.Remove()
        tag = nxt


def _resolve_part_for_selection_or_object(
    root_name,
    obj_name,
    label,
    mats_by_part,
    use_default_if_no_part,
):
    """
    label — имя тега полигонального выделения.
    Сначала сопоставляем по имени выделения (и префиксу корня), затем по имени объекта как раньше.
    """
    part = None
    if label:
        part = infer_part_from_name(f"{root_name}_{label}")
        if part is None:
            part = infer_part_from_name(label)
        if part is None and use_default_if_no_part:
            part = infer_part_by_material_keys(label, mats_by_part)
        if part is None and use_default_if_no_part:
            part = infer_part_by_material_keys(f"{root_name}_{label}", mats_by_part)
    if part is None:
        name_full = f"{root_name}_{obj_name}"
        part = infer_part_from_name(name_full)
        if part is None and use_default_if_no_part:
            part = infer_part_by_material_keys(name_full, mats_by_part)
    return part


def ensure_texture_tag(obj, mat, restriction=""):
    """
    Добавить или обновить Material Tag.
    restriction — имя тега полигонального выделения для TEXTURETAG_RESTRICTION, иначе пусто (весь меш).
    """
    want = (restriction or "").strip()
    tag = obj.GetFirstTag()
    while tag:
        if tag.CheckType(c4d.Ttexture) and tag.GetMaterial() == mat:
            cur = ""
            try:
                cur = (tag[c4d.TEXTURETAG_RESTRICTION] or "").strip()
            except Exception:
                pass
            if cur == want:
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
        if want:
            t[c4d.TEXTURETAG_RESTRICTION] = want
    except Exception:
        pass
    obj.InsertTag(t)
    return t


def _apply_materials_for_polygon_selections(root, obj, mats_by_part, use_default_if_no_part):
    """
    Если на полигональном объекте есть непустые теги полигонального выделения,
    подбираем материал по имени выделения и вешаем отдельные Material Tag с ограничением.
    Возвращает (count_tags, used_selections).
    """
    root_name = root.GetName()
    obj_name = obj.GetName()
    seltags = _iter_polygon_selection_tags(obj)
    if not seltags:
        return 0, False

    matched = []
    for st in seltags:
        if not _polygon_selection_has_any_polygons(st):
            continue
        label = st.GetName()
        part = _resolve_part_for_selection_or_object(
            root_name,
            obj_name,
            label,
            mats_by_part,
            use_default_if_no_part,
        )
        mat = mats_by_part.get(part) if part else None
        if not mat:
            continue
        matched.append((label, mat))

    if not matched:
        return 0, False

    count = 0
    for label, mat in matched:
        ensure_texture_tag(obj, mat, restriction=label)
        count += 1
    return count, True


def _apply_materials_to_root(doc, root, mats_by_part: dict, use_default_if_no_part: bool = False):
    root_name = root.GetName()
    default_mat = None
    if use_default_if_no_part:
        default_mat = mats_by_part.get("Hull")
        if not default_mat and mats_by_part:
            default_mat = next(iter(mats_by_part.values()))

    count = 0
    for o in iter_objects(root.GetDown()):
        _strip_texture_tags(o)

        # Полигональные выделения на мешах: отдельные Material Tag с Selection
        if o.GetType() == c4d.Opolygon and _polygon_selection_tag_type() is not None:
            n_sel, used_sel = _apply_materials_for_polygon_selections(
                root, o, mats_by_part, use_default_if_no_part
            )
            if used_sel:
                count += n_sel
                continue

        name_for_part = f"{root_name}_{o.GetName()}"
        part = infer_part_from_name(name_for_part)
        if part is None and use_default_if_no_part:
            part = infer_part_by_material_keys(name_for_part, mats_by_part)
        if not use_default_if_no_part and not part:
            continue
        mat = mats_by_part.get(part) if part else default_mat
        if not mat:
            continue
        ensure_texture_tag(o, mat, restriction="")
        count += 1
    return count


def apply_materials_to_tank(doc, tank_name: str, mats_by_part: dict):
    """
    Назначает материалы объектам под null танка.
    Для c4d.Opolygon: если есть непустые теги полигонального выделения (Tpolygonselection),
    имена которых удаётся сопоставить с частями (Hull, Turret, …), вешаются отдельные
    Material Tag с ограничением по выделению; иначе — один тег на объект по имени как раньше.
    """
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
    Универсальное назначение: null по имени model_name; при отсутствии part — Hull или первый материал.
    Полигональные выделения на мешах обрабатываются так же, как в apply_materials_to_tank
    (имя выделения сопоставляется с ключами материалов model_*).
    """
    root = find_tank_null(doc, model_name)
    if root is None:
        return 0
    return _apply_materials_to_root(doc, root, mats_by_part, use_default_if_no_part=True)