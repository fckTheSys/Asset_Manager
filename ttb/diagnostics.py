# -*- coding: utf-8 -*-
import c4d

from .config import PLUGIN_ID, PLUGIN_NAME, PLUGIN_VERSION, ENGINES


def _has_redshift_space() -> bool:
    try:
        import maxon
        from .config import RS_SPACE
        return bool(RS_SPACE) and isinstance(RS_SPACE, maxon.Id)
    except Exception:
        return False


def _active_nodespace_label() -> str:
    try:
        return str(c4d.GetActiveNodeSpaceId())
    except Exception:
        return "(unknown)"


def run_self_check() -> list[str]:
    lines = ["%s v%s self check" % (PLUGIN_NAME, PLUGIN_VERSION)]
    if PLUGIN_ID == 10698765:
        lines.append("WARNING: PLUGIN_ID uses placeholder 10698765.")
    lines.append("Engines configured: " + ", ".join(ENGINES))
    lines.append("Redshift node space config: %s" % ("OK" if _has_redshift_space() else "MISSING"))
    lines.append("Active node space: " + _active_nodespace_label())
    try:
        from .cl_graph import CL_SPACE_CANDIDATES
        lines.append("CentiLeo candidates: %s" % len(CL_SPACE_CANDIDATES))
    except Exception as e:
        lines.append("WARNING: CentiLeo config import failed: %s" % e)
    for name in ("AddCheckbox", "AddEditText", "AddButton"):
        lines.append("GeDialog.%s: %s" % (name, "OK" if hasattr(c4d.gui.GeDialog, name) else "MISSING"))
    return lines


def summarize_tasks(tasks: list[dict], mode: str) -> str:
    name_key = "tank" if mode == "tanks" else "name"
    total_groups = 0
    total_maps = 0
    missing_tex = 0
    lines = ["Tasks: %s (%s)" % (len(tasks), mode)]
    for task in tasks:
        groups = task.get("groups") or {}
        total_groups += len(groups)
        for maps in groups.values():
            total_maps += len(maps or {})
        if not task.get("tex_dir"):
            missing_tex += 1
    lines.append("Material groups: %s" % total_groups)
    lines.append("Texture maps: %s" % total_maps)
    lines.append("Tasks without texture dir: %s" % missing_tex)
    if tasks:
        preview = ", ".join(str(t.get(name_key, "?")) for t in tasks[:10])
        lines.append("Preview: " + preview)
    return "\n".join(lines)
