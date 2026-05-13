# -*- coding: utf-8 -*-
import os
import re
import json
from .config import TEX_EXT, MAP_TYPES, PART_KEYS, CRASH_TOKEN, CRUSH_TOKEN, TEXTURE_ALIASES_FILE
from .log import info as _log_info

_ALIASES_CACHE = None

# Set True to log textures that were skipped (map type not detected) for debugging
DEBUG_SCAN_VERBOSE = False

def normpath(p: str) -> str:
    return os.path.normpath(p) if p else p

def is_dir(p: str) -> bool:
    try:
        return p and os.path.isdir(p)
    except OSError:
        return False

def is_file(p: str) -> bool:
    try:
        return p and os.path.isfile(p)
    except OSError:
        return False


def _iter_texture_files(tex_dir: str):
    """Yield (root, filename) for each texture file under tex_dir (TEX_EXT, skip proxy)."""
    if not is_dir(tex_dir):
        return
    for root, _, files in os.walk(tex_dir):
        for f in files:
            if os.path.splitext(f)[1].lower() not in TEX_EXT:
                continue
            if is_proxy_texture(f):
                continue
            yield root, f

def _load_texture_aliases():
    global _ALIASES_CACHE
    if _ALIASES_CACHE is not None:
        return _ALIASES_CACHE

    aliases = {m: [m.lower()] for m in MAP_TYPES}
    try:
        here = os.path.dirname(__file__)
        path = os.path.join(here, TEXTURE_ALIASES_FILE)
        if is_file(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f) or {}

            for key, vals in data.items():
                if not isinstance(vals, list):
                    continue

                norm_vals = [str(v).lower() for v in vals]

                # Основные поддерживаемые типы карт
                target = key
                if target not in MAP_TYPES:
                    # Сопоставляем дополнительные ключи: gloss/spec/packed → GM
                    if key in ("SP", "ORM", "ARM", "RMA", "MRA"):
                        target = "GM"
                    else:
                        # Типы из JSON, не используемые в RS-графе (HM, SSS, THK, COAT и т.д.), пропускаем
                        continue

                # Расширяем список алиасов для целевого типа
                base = aliases.setdefault(target, [])
                for v in norm_vals:
                    if v not in base:
                        base.append(v)
    except Exception:
        # Fallback to defaults if anything goes wrong
        pass

    _ALIASES_CACHE = aliases
    return _ALIASES_CACHE

def _extract_dynamic_part(filename: str):
    """
    Для Universal: пытаемся извлечь "слот материала" из имени файла, если
    стандартная часть (Hull/Turret/...) не найдена.
    Примеры:
    - Model_Glass__Color -> Glass
    - Model_Tracks__Roughness -> Tracks
    """
    name = os.path.splitext(os.path.basename(filename))[0]
    lower_name = name.lower()

    # 1) Явные суффиксы вида __Color / __Roughness / __DisplaceHeightField
    for suffix, _ in _SUFFIX_MAP:
        if lower_name.endswith(suffix):
            prefix = name[: len(name) - len(suffix)]
            prefix = prefix.rstrip("_-. ")
            if not prefix:
                return None
            tokens = [t for t in re.split(r"[_\-\.\s]+", prefix) if t]
            if not tokens:
                return None
            return tokens[-1]

    # 2) Гибкий разбор по последнему сегменту карты: ...___Color
    segments = [s for s in re.split(r"_+", lower_name) if s]
    if segments and segments[-1] in _LAST_SEGMENT_MAP:
        original_segments = [s for s in re.split(r"_+", name) if s]
        if len(original_segments) >= 2:
            return original_segments[-2]

    return None


def detect_part(filename: str, dynamic_fallback: bool = False) -> str:
    low = filename.lower()
    for k, v in PART_KEYS.items():
        if k in low:
            return v
    if dynamic_fallback:
        dyn = _extract_dynamic_part(filename)
        if dyn:
            return dyn
    return "Hull"

# Explicit suffix -> map type for Universal-style names (e.g. ...__Color, ...__DisplaceHeightField)
# Checked first; longest suffixes first so __DisplaceHeightField wins over __Height
_SUFFIX_MAP = (
    ("__displaceheightfield", "HM"),
    ("__displacementheightfield", "HM"),
    ("__heightfield", "HM"),
    ("__displacement", "HM"),
    ("__height", "HM"),
    ("__emissioncolor", "EM"),
    ("__emission", "EM"),
    ("__opacitycolor", "OP"),
    ("__opacity", "OP"),
    ("__roughness", "RM"),
    ("__metalness", "MM"),
    ("__metalness_map", "MM"),
    ("__metal", "MM"),
    ("__normal", "NM"),
    ("__normals", "NM"),
    ("__color", "AM"),
    ("__basecolor", "AM"),
    ("__albedo", "AM"),
    ("__diffuse", "AM"),
    ("__gloss", "GM"),
    ("__glossiness", "GM"),
    ("__ambientocclusion", "AO"),
    ("__occlusion", "AO"),
)
# Last segment after underscores (e.g. "name___Color" -> "color") for flexible underscore count
_LAST_SEGMENT_MAP = {
    "displaceheightfield": "HM",
    "displacementheightfield": "HM",
    "heightfield": "HM",
    "displacement": "HM",
    "height": "HM",
    "emissioncolor": "EM",
    "emission": "EM",
    "opacitycolor": "OP",
    "opacity": "OP",
    "roughness": "RM",
    "metalness": "MM",
    "metal": "MM",
    "normal": "NM",
    "normals": "NM",
    "color": "AM",
    "basecolor": "AM",
    "albedo": "AM",
    "diffuse": "AM",
    "gloss": "GM",
    "glossiness": "GM",
    "ambientocclusion": "AO",
    "occlusion": "AO",
}


def detect_map_type(filename: str):
    """
    Определяем тип карты (AM/AO/NM/MM/GM/RM/EM/OP/HM) по имени файла.
    Сначала проверяются явные суффиксы (__Color, __Metalness, __DisplaceHeightField и т.д.),
    затем MAP_TYPES и алиасы из texture_aliases.json.
    """
    name = os.path.splitext(os.path.basename(filename))[0]
    upper_name = name.upper()
    lower_name = name.lower()

    # Explicit suffix check for Universal-style names (e.g. Plane_env_hg_platform_for_tanks__Color)
    for suffix, mtype in _SUFFIX_MAP:
        if lower_name.endswith(suffix):
            return mtype
    # Last segment (handles ...___Color, ...___DisplaceHeightField with any number of underscores)
    segments = [s for s in re.split(r"_+", lower_name) if s]
    if segments and segments[-1] in _LAST_SEGMENT_MAP:
        return _LAST_SEGMENT_MAP[segments[-1]]

    # Старая логика по MAP_TYPES (для обратной совместимости)
    for m in MAP_TYPES:
        if re.search(rf"(^|[_\-\.\s]){m}($|[_\-\.\s])", upper_name) or upper_name.endswith(m):
            return m
    # Явно ловим NORMAL как слово (_Normal, Something_Normal и т.д.)
    if re.search(r"(^|[_\-\.\s])NORMAL($|[_\-\.\s])", upper_name) or upper_name.endswith("NORMAL"):
        return "NM"
    for m in MAP_TYPES:
        if m in upper_name:
            return m

    # Новая логика: алиасы из конфига; выбираем совпадение с максимальной длиной алиаса,
    # чтобы EmissionColor → EM, OpacityColor → OP, а не AM из-за "color"
    aliases = _load_texture_aliases()
    tokens = re.split(r"[_\-\.\s]+", lower_name)
    best_match = None
    best_len = 0
    for map_type, keys in aliases.items():
        for k in keys:
            if not k:
                continue
            if k in tokens or lower_name.endswith(k):
                if len(k) > best_len:
                    best_len = len(k)
                    best_match = map_type
    return best_match

def tank_is_crush(tank: str) -> bool:
    t = tank.lower()
    return (CRUSH_TOKEN in t) or t.endswith(CRUSH_TOKEN)

def is_crash_texture(filename: str) -> bool:
    return CRASH_TOKEN in filename.lower()

def is_proxy_texture(filename: str) -> bool:
    """
    Прокси-текстуры по договорённости помечаются словом 'Proxy' в имени.
    Такие файлы нужно игнорировать при сканировании/копировании.
    """
    return "proxy" in (filename or "").lower()

def find_fbx(fin_dir: str):
    if not is_dir(fin_dir):
        return None
    for f in os.listdir(fin_dir):
        if f.lower().endswith(".fbx"):
            return os.path.join(fin_dir, f)
    return None

def find_textures_dir(tank_dir: str, fin_dir: str):
    a = os.path.join(tank_dir, "Original_textures")
    b = os.path.join(fin_dir, "Original_textures")
    if is_dir(b): return b
    if is_dir(a): return a
    return None

def scan_textures(tex_dir: str, tank_name: str, dynamic_parts: bool = False):
    """
    Returns {Part: {MapType: filepath}}
    """
    allow_crash = tank_is_crush(tank_name)
    out = {}
    for root, f in _iter_texture_files(tex_dir):
        if is_crash_texture(f) and not allow_crash:
            continue
        mtype = detect_map_type(f)
        if not mtype:
            if DEBUG_SCAN_VERBOSE:
                _log_info("scan skip (no map type): %s" % f)
            continue
        part = detect_part(f, dynamic_fallback=dynamic_parts)
        out.setdefault(part, {})[mtype] = os.path.join(root, f)
    return out

def build_texture_index(tex_dir: str):
    """
    basename(lower) -> fullpath
    """
    idx = {}
    for root, f in _iter_texture_files(tex_dir):
        idx[f.lower()] = os.path.join(root, f)
    return idx

def collect_tasks(root_tanks: str):
    """
    Task = dict(tank, tank_dir, fin_dir, fbx, tex_dir, groups)
    """
    tasks = []
    if not is_dir(root_tanks):
        return tasks

    for name in os.listdir(root_tanks):
        tank_dir = os.path.join(root_tanks, name)
        if not is_dir(tank_dir):
            continue

        fin_dir = os.path.join(tank_dir, "FIN")
        if not is_dir(fin_dir):
            continue

        fbx = find_fbx(fin_dir)
        if not fbx:
            continue

        tex_dir = find_textures_dir(tank_dir, fin_dir)
        groups = scan_textures(tex_dir, name) if tex_dir else {}

        tasks.append({
            "tank": name,
            "tank_dir": tank_dir,
            "fin_dir": fin_dir,
            "fbx": fbx,
            "tex_dir": tex_dir,
            "groups": groups
        })

    return tasks


def collect_universal_tasks(root_universal: str):
    """
    Универсальный сканер:
    - Рекурсивно обходит root_universal
    - Для каждой папки, где есть .fbx, создаёт задачу.
    Task = dict(name, fbx, tex_dir, groups)
    """
    tasks = []
    if not is_dir(root_universal):
        return tasks

    root_universal = normpath(root_universal)

    for dirpath, _, files in os.walk(root_universal):
        fbx_files = [f for f in files if f.lower().endswith(".fbx")]
        if not fbx_files:
            continue

        dirpath = normpath(dirpath)
        rel = os.path.relpath(dirpath, root_universal)

        # Определяем корневую папку модели относительно universal-root
        if rel in (".", ""):
            # FBX лежит прямо в корне – считаем имя модели по имени файла
            for fbx_name in fbx_files:
                model_name = os.path.splitext(fbx_name)[0]
                fbx_path = os.path.join(dirpath, fbx_name)
                tex_dir = root_universal
                groups = scan_textures(tex_dir, model_name, dynamic_parts=True) if tex_dir else {}

                tasks.append({
                    "name": model_name,
                    "fbx": fbx_path,
                    "tex_dir": tex_dir,
                    "groups": groups,
                })
            continue

        # Первый компонент пути от universal-root – это логическое имя модели
        top = rel.split(os.sep)[0]
        model_name = top
        model_root_dir = os.path.join(root_universal, top)

        # Уникальное имя на задачу: если несколько FBX в дереве модели — различаем по имени файла
        for fbx_name in fbx_files:
            fbx_stem = os.path.splitext(fbx_name)[0]
            task_name = model_name if len(fbx_files) == 1 else f"{model_name}_{fbx_stem}"
            fbx_path = os.path.join(dirpath, fbx_name)
            tex_dir = model_root_dir  # текстуры ищем во всей подпапке модели
            groups = scan_textures(tex_dir, model_name, dynamic_parts=True) if tex_dir else {}

            tasks.append({
                "name": task_name,
                "fbx": fbx_path,
                "tex_dir": tex_dir,
                "groups": groups,
            })

    return tasks