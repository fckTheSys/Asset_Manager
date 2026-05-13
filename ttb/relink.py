# -*- coding: utf-8 -*-
import os
import c4d
import maxon
from .config import (
    RS_SPACE, P_TEX0, P_TEX0_PATH,
    CL_SPACE_CANDIDATES, CL_NODE_BITMAP, CL_P_FILENAME,
    ENGINES,
)
from .log import error as _log_error


def fix_legacy_bitmap_shaders(doc, texture_index: dict):
    fixed = 0
    for mat in doc.GetMaterials():
        sh = mat.GetFirstShader()
        while sh:
            if sh.CheckType(c4d.Xbitmap):
                fn = sh[c4d.BITMAPSHADER_FILENAME]
                if fn and os.path.isfile(fn):
                    sh = sh.GetNext()
                    continue
                base = os.path.basename(fn).lower() if fn else ""
                new_path = texture_index.get(base)
                if new_path and os.path.isfile(new_path):
                    sh[c4d.BITMAPSHADER_FILENAME] = new_path
                    fixed += 1
            sh = sh.GetNext()
    return fixed


def _fix_path_in_port(path_port, texture_index: dict):
    """Update path_port from texture_index by basename; return True if updated."""
    if path_port is None:
        return False
    try:
        cur = path_port.GetDefaultValue()
        cur_str = str(cur) if cur is not None else ""
        cur_str = cur_str.replace("file://", "").strip()
        if cur_str and os.path.isfile(cur_str):
            return False
        base = os.path.basename(cur_str).lower() if cur_str else ""
        if not base:
            return False
        new_path = texture_index.get(base)
        if new_path and os.path.isfile(new_path):
            path_port.SetDefaultValue(new_path)
            return True
    except Exception:
        pass
    return False


def fix_node_texturesampler_paths(doc, texture_index: dict, engines=None):
    """
    Fix texture paths in node materials for the given engines.
    engines: None = all (redshift, centileo), or sequence e.g. ("redshift",) or ("centileo",).
    """
    if engines is None:
        engines = ENGINES
    fixed = 0

    for mat in doc.GetMaterials():
        nm = mat.GetNodeMaterialReference()
        if nm is None:
            continue

        for engine in engines:
            if engine == "redshift":
                try:
                    graph = nm.GetGraph(RS_SPACE)
                except Exception as e:
                    _log_error(f"Failed to get RS graph for material '{mat.GetName()}': {e}")
                    continue
                if graph is None:
                    continue
                nodes = []
                try:
                    maxon.GraphModelHelper.FindNodesByAssetId(
                        graph, maxon.Id("com.redshift3d.redshift4c4d.nodes.core.texturesampler"), True, nodes
                    )
                except Exception as e:
                    _log_error(f"Failed to enumerate RS texture nodes for material '{mat.GetName()}': {e}")
                    continue
                try:
                    with graph.BeginTransaction() as t:
                        changed = False
                        for n in nodes:
                            tex0 = n.GetInputs().FindChild(P_TEX0)
                            if tex0 is None:
                                continue
                            path_port = tex0.FindChild(P_TEX0_PATH)
                            if _fix_path_in_port(path_port, texture_index):
                                fixed += 1
                                changed = True
                        if changed:
                            t.Commit()
                except Exception as e:
                    _log_error(f"RS relink transaction failed for material '{mat.GetName()}': {e}")

            elif engine == "centileo":
                for space_id in CL_SPACE_CANDIDATES:
                    try:
                        graph = nm.GetGraph(space_id)
                    except Exception:
                        continue
                    if graph is None:
                        continue
                    nodes = []
                    try:
                        maxon.GraphModelHelper.FindNodesByAssetId(
                            graph, maxon.Id(CL_NODE_BITMAP), True, nodes
                        )
                    except Exception:
                        continue
                    if not nodes:
                        continue
                    try:
                        with graph.BeginTransaction() as t:
                            changed = False
                            for n in nodes:
                                path_port = n.GetInputs().FindChild(CL_P_FILENAME)
                                if _fix_path_in_port(path_port, texture_index):
                                    fixed += 1
                                    changed = True
                            if changed:
                                t.Commit()
                    except Exception as e:
                        _log_error(f"CentiLeo relink transaction failed for material '{mat.GetName()}': {e}")
                    break

    return fixed
