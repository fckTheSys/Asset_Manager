# -*- coding: utf-8 -*-
"""
CentiLeo node material graph builder (C4D 2026 safe).

Contract:
    create_or_update_cl_material(doc, mat_name, maps)
"""

import c4d
import maxon

from .rs_graph import uniq_material_name, find_or_create_material, find_material, _try_find, _connect
from .config import (
    CL_SPACE_CANDIDATES,
    CL_NODEID_MATERIAL, CL_NODEID_OUTPUT,
    CL_BITMAP_ASSET_CANDIDATES, CL_MATH_ASSET_CANDIDATES,

    CL_P_DIFFUSE_COLOR, CL_P_DIFFUSE_ROUGH, CL_P_DIFFUSE_METAL,
    CL_P_BUMP_MAP, CL_P_ALPHA_MAP, CL_P_MATERIAL_OUT,
    CL_P_OUT_SURF, CL_P_OUT_DISP,

    CL_P_EMISSION_COLOR,
    CL_P_DISP_MAP, CL_P_DISP_OUT,

    CL_P_FILENAME, CL_P_COLORSPACE, CL_P_BITMAP_RESULT,
    CL_P_MATH_A, CL_P_MATH_TYPE, CL_P_MATH_RESULT,

    CL_CS_SRGB, CL_CS_RAW,
)


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

from .log import info as _log_info


def _log(msg):
    _log_info("[CL] " + str(msg))


def _iter_nodes(graph):
    root = graph.GetViewRoot()
    try:
        children = root.GetChildren()
    except Exception:
        children = []
    for n in children:
        try:
            if n.GetKind() != maxon.NODE_KIND.NODE:
                continue
        except Exception:
            pass
        yield n


def _find_node_by_id(graph, node_id):
    for n in _iter_nodes(graph):
        if str(n.GetId()) == node_id:
            return n
    return None


def _find_node_by_ports(graph, in_ports=(), out_ports=()):
    for n in _iter_nodes(graph):
        ins = n.GetInputs()
        outs = n.GetOutputs()
        ok = True
        for pid in in_ports:
            if _try_find(ins, pid) is None:
                ok = False
                break
        if not ok:
            continue
        for pid in out_ports:
            if _try_find(outs, pid) is None:
                ok = False
                break
        if ok:
            return n
    return None


def _add_node_by_asset_candidates(graph, candidates):
    last_err = None
    for aid in candidates:
        for child_id in ("", maxon.Id()):
            try:
                node = graph.AddChild(child_id, maxon.Id(aid), maxon.DataDictionary())
                if node and not node.IsNullValue():
                    return node
            except Exception as e:
                last_err = e
                continue

    # Fallback: find an existing bitmap-like node in the graph and use its asset ID
    ref_id = _get_bitmap_asset_id_from_graph(graph)
    if ref_id:
        try:
            node = graph.AddChild("", maxon.Id(ref_id), maxon.DataDictionary())
            if node and not node.IsNullValue():
                _log("Bitmap node created via fallback ID: " + ref_id)
                return node
        except Exception as e:
            last_err = e

    _log("CL Bitmap: no candidate worked. Existing node IDs in graph:")
    for n in _iter_nodes(graph):
        try:
            _log("  node Id: " + str(n.GetId()))
        except Exception:
            pass
    if last_err is not None:
        _log("Last AddChild error: " + str(last_err))
    _log("Tip: In C4D enable g_developerNodeEditorFunctions, open Node Editor, find Bitmap asset and copy its ID; add it as first item in config.CL_BITMAP_ASSET_CANDIDATES.")
    return None


def _get_bitmap_asset_id_from_graph(graph):
    """Find a bitmap-like node; return the type part of GetId() (e.g. 'bitmap' from 'bitmap@xxx') for AddChild."""
    for n in _iter_nodes(graph):
        try:
            ins = n.GetInputs()
            outs = n.GetOutputs()
            if ins is None or outs is None:
                continue
            path_in = _try_find_many(ins, CL_P_FILENAME, "path", "file", "filepath", "filename", "url")
            result_out = _try_find_many(outs, CL_P_BITMAP_RESULT, "result", "out", "outcolor", "color")
            if path_in is not None and result_out is not None:
                nid = n.GetId()
                if nid is None:
                    continue
                sid = str(nid)
                if "@" in sid:
                    type_part = sid.split("@")[0].strip()
                    if type_part:
                        return type_part
                if "." in sid and ("bitmap" in sid.lower() or "texture" in sid.lower() or "image" in sid.lower() or "file" in sid.lower()):
                    return sid
                if "." in sid and len(sid) > 8:
                    return sid
        except Exception:
            continue
    return None


def _set_bitmap_path(port, filepath):
    if port is None:
        return False
    try:
        port.SetDefaultValue(filepath)
        return True
    except Exception:
        pass
    try:
        port.SetDefaultValue(maxon.Url(filepath))
        return True
    except Exception:
        pass
    return False


def _set_colorspace(port, value):
    if port is None:
        return False
    try:
        port.SetDefaultValue(value)
        return True
    except Exception:
        pass
    try:
        port.SetDefaultValue(maxon.Id(str(value)))
        return True
    except Exception:
        pass
    return False


def _try_find_many(container, *port_ids):
    for pid in port_ids:
        p = _try_find(container, pid)
        if p is not None:
            return p
    return None


# ---------------------------------------------------------------------
# Graph core
# ---------------------------------------------------------------------

def cl_find_material_output(graph):
    """
    In C4D 2026 CentiLeo default graph:
        node.GetId() == 'material_node'
        node.GetId() == 'output_node'
    """
    material_node = _find_node_by_id(graph, CL_NODEID_MATERIAL)
    output_node   = _find_node_by_id(graph, CL_NODEID_OUTPUT)

    if material_node is None:
        material_node = _find_node_by_ports(
            graph,
            in_ports=(CL_P_DIFFUSE_COLOR, CL_P_DIFFUSE_ROUGH, CL_P_DIFFUSE_METAL),
            out_ports=(CL_P_MATERIAL_OUT,)
        )

    if output_node is None:
        output_node = _find_node_by_ports(
            graph,
            in_ports=(CL_P_OUT_SURF, CL_P_OUT_DISP),
            out_ports=()
        )

    if material_node is None or output_node is None:
        raise RuntimeError("Material or Output node not found in CentiLeo graph.")

    return material_node, output_node


def cl_rebuild_graph(nm):
    # First try known CL node spaces from config, then fallback to active space.
    for space_id in CL_SPACE_CANDIDATES:
        try:
            graph = nm.CreateDefaultGraph(space_id)
            if graph is None or graph.IsNullValue():
                continue
            cl_find_material_output(graph)
            _log("Using CL node space: " + str(space_id))
            return graph
        except Exception:
            continue

    active_space = c4d.GetActiveNodeSpaceId()
    _log("Fallback to active node space: " + str(active_space))
    if not active_space:
        raise RuntimeError("No suitable CentiLeo node space found.")

    graph = nm.CreateDefaultGraph(active_space)
    if graph is None or graph.IsNullValue():
        raise RuntimeError("CreateDefaultGraph failed.")

    # Verify graph actually looks like CentiLeo before using it.
    cl_find_material_output(graph)
    return graph


# ---------------------------------------------------------------------
# Bitmap
# ---------------------------------------------------------------------

def cl_add_texture(graph, filepath, colorspace):
    node = _add_node_by_asset_candidates(graph, CL_BITMAP_ASSET_CANDIDATES)
    if node is None:
        raise RuntimeError("Failed to create CentiLeo Bitmap node.")

    inputs = node.GetInputs()

    # Different CL builds may expose different input ids for bitmap path/colorspace.
    path_port = _try_find_many(inputs, CL_P_FILENAME, "path", "file", "filepath", "url")
    cs_port = _try_find_many(inputs, CL_P_COLORSPACE, "color_space", "cs", "input_colorspace")

    path_ok = _set_bitmap_path(path_port, filepath)
    cs_ok = _set_colorspace(cs_port, colorspace)

    # Some graphs expose nested tex input group (similar to RS tex0.path/colorspace).
    if not path_ok or not cs_ok:
        tex_group = _try_find_many(inputs, "tex0", "texture", "input")
        if tex_group is not None:
            if not path_ok:
                path_ok = _set_bitmap_path(_try_find_many(tex_group, CL_P_FILENAME, "path", "file", "filepath", "url"), filepath)
            if not cs_ok:
                cs_ok = _set_colorspace(_try_find_many(tex_group, CL_P_COLORSPACE, "color_space", "cs", "input_colorspace"), colorspace)

    if not path_ok:
        _log("WARN: Bitmap path port not found/set for: " + str(filepath))

    return node


def _bitmap_out(node):
    outs = node.GetOutputs()
    return _try_find_many(outs, CL_P_BITMAP_RESULT, "outcolor", "color", "out", "result_color")


# ---------------------------------------------------------------------
# Build graph
# ---------------------------------------------------------------------

def build_material_graph_cl(graph, maps):
    _log("Build graph: " + (", ".join(maps.keys()) if maps else "no maps"))

    material_node, output_node = cl_find_material_output(graph)

    mat_in = material_node.GetInputs()
    mat_out = material_node.GetOutputs()

    p_diffuse = _try_find(mat_in, CL_P_DIFFUSE_COLOR)
    p_rough   = _try_find(mat_in, CL_P_DIFFUSE_ROUGH)
    p_metal   = _try_find(mat_in, CL_P_DIFFUSE_METAL)
    p_bump    = _try_find(mat_in, CL_P_BUMP_MAP)
    p_alpha   = _try_find(mat_in, CL_P_ALPHA_MAP)

    mat_result = _try_find(mat_out, CL_P_MATERIAL_OUT)

    out_in = output_node.GetInputs()
    out_surf = _try_find(out_in, CL_P_OUT_SURF)
    out_disp = _try_find(out_in, CL_P_OUT_DISP)

    # optional nodes
    emission_node = _find_node_by_ports(graph, in_ports=(CL_P_EMISSION_COLOR,))
    disp_node     = _find_node_by_ports(graph, in_ports=(CL_P_DISP_MAP,), out_ports=(CL_P_DISP_OUT,))

    with graph.BeginTransaction() as t:

        # material -> output
        if mat_result and out_surf:
            _connect(mat_result, out_surf)

        # AM
        if maps.get("AM") and p_diffuse:
            n = cl_add_texture(graph, maps["AM"], CL_CS_SRGB)
            _connect(_bitmap_out(n), p_diffuse)

        # MM
        if maps.get("MM") and p_metal:
            n = cl_add_texture(graph, maps["MM"], CL_CS_RAW)
            _connect(_bitmap_out(n), p_metal)

        # NM
        if maps.get("NM") and p_bump:
            n = cl_add_texture(graph, maps["NM"], CL_CS_RAW)
            _connect(_bitmap_out(n), p_bump)

        # Roughness
        if p_rough:
            if maps.get("RM"):
                n = cl_add_texture(graph, maps["RM"], CL_CS_RAW)
                _connect(_bitmap_out(n), p_rough)

            elif maps.get("GM"):
                tex = cl_add_texture(graph, maps["GM"], CL_CS_RAW)
                math = _add_node_by_asset_candidates(graph, CL_MATH_ASSET_CANDIDATES)
                if math:
                    mt = _try_find(math.GetInputs(), CL_P_MATH_TYPE)
                    if mt:
                        try: mt.SetDefaultValue(1)
                        except: pass
                    _connect(_bitmap_out(tex), _try_find(math.GetInputs(), CL_P_MATH_A))
                    _connect(_try_find(math.GetOutputs(), CL_P_MATH_RESULT), p_rough)

        # OP
        if maps.get("OP") and p_alpha:
            n = cl_add_texture(graph, maps["OP"], CL_CS_SRGB)
            _connect(_bitmap_out(n), p_alpha)

        # EM
        if maps.get("EM") and emission_node:
            port = _try_find(emission_node.GetInputs(), CL_P_EMISSION_COLOR)
            if port:
                n = cl_add_texture(graph, maps["EM"], CL_CS_SRGB)
                _connect(_bitmap_out(n), port)

        # HM
        if maps.get("HM") and disp_node and out_disp:
            disp_in  = _try_find(disp_node.GetInputs(), CL_P_DISP_MAP)
            disp_out = _try_find(disp_node.GetOutputs(), CL_P_DISP_OUT)
            if disp_in and disp_out:
                n = cl_add_texture(graph, maps["HM"], CL_CS_RAW)
                _connect(_bitmap_out(n), disp_in)
                _connect(disp_out, out_disp)

        t.Commit()


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------

def create_or_update_cl_material(doc, mat_name, maps, update_existing_only=False):
    _log("Create/update: " + mat_name)

    mat = find_material(doc, mat_name) if update_existing_only else find_or_create_material(doc, mat_name)
    if mat is None:
        return None

    nm = mat.GetNodeMaterialReference()
    if nm is None:
        raise RuntimeError("Material is not node-based.")

    graph = cl_rebuild_graph(nm)
    build_material_graph_cl(graph, maps)

    return mat
