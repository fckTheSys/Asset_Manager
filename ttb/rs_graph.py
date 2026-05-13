# -*- coding: utf-8 -*-
import c4d
import maxon

from .config import (
    RS_SPACE,
    NODE_TEX, NODE_BUMP, NODE_INV, NODE_DISP,
    P_BASE, P_MET, P_ROU, P_BMP, P_EMISSION, P_OPACITY, P_STD_OUT, P_OUT_SURF, P_OUT_DISP,
    P_TEX0, P_OUTC, P_AO_MUL, P_TEX0_PATH, P_TEX0_COLORSPACE,
    P_BUMP_IN, P_BUMP_OUT, P_BUMP_TYPE, BUMP_TANGENT_SPACE_NORMAL,
    P_INV_IN, P_INV_OUT,
    P_DISP_TEX, P_DISP_OUT,
    CS_RAW, CS_SRGB,
)

# --- optional: RG support even if MAP_TYPES not updated yet ---
# maps dict может содержать "RG" — мы просто обработаем, даже если MAP_TYPES не включает.


def uniq_material_name(doc, base: str) -> str:
    names = {m.GetName() for m in doc.GetMaterials()}
    if base not in names:
        return base
    i = 2
    while f"{base}_{i}" in names:
        i += 1
    return f"{base}_{i}"


def find_or_create_material(doc, name: str):
    for m in doc.GetMaterials():
        if m.GetName() == name:
            return m
    mat = c4d.BaseMaterial(c4d.Mmaterial)
    mat.SetName(uniq_material_name(doc, name))
    doc.InsertMaterial(mat)
    return mat


def find_material(doc, name: str):
    for m in doc.GetMaterials():
        if m.GetName() == name:
            return m
    return None


def rs_find_std_out(graph):
    std_nodes, out_nodes = [], []
    maxon.GraphModelHelper.FindNodesByAssetId(
        graph, maxon.Id("com.redshift3d.redshift4c4d.nodes.core.standardmaterial"), True, std_nodes
    )
    maxon.GraphModelHelper.FindNodesByAssetId(
        graph, maxon.Id("com.redshift3d.redshift4c4d.node.output"), True, out_nodes
    )
    if not std_nodes or not out_nodes:
        raise RuntimeError("StandardMaterial/Output not found in RS graph.")
    return std_nodes[0], out_nodes[0]


def _try_find(container, pid):
    if container is None:
        return None
    try:
        return container.FindChild(pid)
    except Exception:
        return None


def _connect(out_port, in_port) -> bool:
    if out_port is None or in_port is None:
        return False
    try:
        out_port.Connect(in_port)
        return True
    except Exception:
        return False


def rs_add_texture(graph, filepath: str, colorspace: str):
    """
    Важно: colorspace живёт в tex0 как 'colorspace' и ставится через SetDefaultValue().
    Порты ищем через _try_find для устойчивости к разным версиям Redshift.
    """
    shader = graph.AddChild("", maxon.Id(NODE_TEX), maxon.DataDictionary())
    tex0 = _try_find(shader.GetInputs(), P_TEX0)
    if tex0 is not None:
        path_port = _try_find(tex0, P_TEX0_PATH)
        if path_port is not None:
            path_port.SetDefaultValue(filepath)
        cs_port = _try_find(tex0, P_TEX0_COLORSPACE)
        if cs_port is not None:
            cs_port.SetDefaultValue(colorspace)
    return shader


def rs_rebuild_graph(nm):
    """
    Самый стабильный способ: CreateDefaultGraph(RS) -> чистый граф.
    """
    try:
        nm.CreateDefaultGraph(RS_SPACE)
        graph = nm.GetGraph(RS_SPACE)
    except Exception as e:
        raise RuntimeError(
            "Redshift node space is not available. "
            "Check that Redshift is installed and enabled."
        ) from e
    if graph is None:
        raise RuntimeError(
            "Failed to obtain Redshift node graph. "
            "Check that Redshift is installed and enabled."
        )
    return graph


def build_material_graph(graph, maps: dict):
    std, out = rs_find_std_out(graph)
    std_inputs = std.GetInputs()
    base  = _try_find(std_inputs, P_BASE)
    metal = _try_find(std_inputs, P_MET)
    rough = _try_find(std_inputs, P_ROU)
    bump  = _try_find(std_inputs, P_BMP)

    with graph.BeginTransaction() as t:
        # Standard -> Output
        _connect(
            _try_find(std.GetOutputs(), P_STD_OUT),
            _try_find(out.GetInputs(), P_OUT_SURF)
        )

        # AM -> Base Color (sRGB)
        am_node = None
        am_out = None
        if maps.get("AM") and base is not None:
            am_node = rs_add_texture(graph, maps["AM"], CS_SRGB)
            am_out = _try_find(am_node.GetOutputs(), P_OUTC)
            _connect(am_out, base)

        # AO -> AM.color_multiplier (RAW) (safe)
        if maps.get("AO") and am_node is not None:
            ao_node = rs_add_texture(graph, maps["AO"], CS_RAW)
            ao_out = _try_find(ao_node.GetOutputs(), P_OUTC)
            ao_mul = _try_find(am_node.GetInputs(), P_AO_MUL)
            # если порта нет — просто пропустим AO, но не упадём
            _connect(ao_out, ao_mul)

        # MM -> Metalness (RAW)
        if maps.get("MM") and metal is not None:
            mm_node = rs_add_texture(graph, maps["MM"], CS_RAW)
            _connect(_try_find(mm_node.GetOutputs(), P_OUTC), metal)

        # NM -> Bump(Tangent Space Normal) -> Bump input (RAW)
        if maps.get("NM") and bump is not None:
            nm_node = rs_add_texture(graph, maps["NM"], CS_RAW)
            bump_node = graph.AddChild("", maxon.Id(NODE_BUMP), maxon.DataDictionary())
            bump_type = _try_find(bump_node.GetInputs(), P_BUMP_TYPE)
            if bump_type is not None:
                bump_type.SetPortValue(BUMP_TANGENT_SPACE_NORMAL)
            _connect(_try_find(nm_node.GetOutputs(), P_OUTC), _try_find(bump_node.GetInputs(), P_BUMP_IN))
            _connect(_try_find(bump_node.GetOutputs(), P_BUMP_OUT), bump)

        # Roughness: RM/RG — напрямую; GM (gloss) — через инверт
        if rough is not None:
            if maps.get("RM"):
                rm_node = rs_add_texture(graph, maps["RM"], CS_RAW)
                _connect(_try_find(rm_node.GetOutputs(), P_OUTC), rough)
            elif maps.get("RG"):
                rg_node = rs_add_texture(graph, maps["RG"], CS_RAW)
                _connect(_try_find(rg_node.GetOutputs(), P_OUTC), rough)
            elif maps.get("GM"):
                gm_node = rs_add_texture(graph, maps["GM"], CS_RAW)
                inv_node = graph.AddChild("", maxon.Id(NODE_INV), maxon.DataDictionary())
                _connect(_try_find(gm_node.GetOutputs(), P_OUTC), _try_find(inv_node.GetInputs(), P_INV_IN))
                _connect(_try_find(inv_node.GetOutputs(), P_INV_OUT), rough)

        # EM -> Emission Color (sRGB); OP -> Opacity (RAW, non-color data)
        emission_port = _try_find(std.GetInputs(), P_EMISSION)
        if maps.get("EM") and emission_port is not None:
            em_node = rs_add_texture(graph, maps["EM"], CS_SRGB)
            _connect(_try_find(em_node.GetOutputs(), P_OUTC), emission_port)
        opacity_port = _try_find(std.GetInputs(), P_OPACITY)
        if maps.get("OP") and opacity_port is not None:
            op_node = rs_add_texture(graph, maps["OP"], CS_RAW)
            _connect(_try_find(op_node.GetOutputs(), P_OUTC), opacity_port)

        # HM (height/displacement) -> Displacement node -> Output.displacement
        out_inputs = out.GetInputs()
        disp_port = _try_find(out_inputs, P_OUT_DISP)
        if maps.get("HM") and disp_port is not None:
            hm_node = rs_add_texture(graph, maps["HM"], CS_RAW)
            disp_node = graph.AddChild("", maxon.Id(NODE_DISP), maxon.DataDictionary())
            disp_in = _try_find(disp_node.GetInputs(), P_DISP_TEX)
            disp_out = _try_find(disp_node.GetOutputs(), P_DISP_OUT)
            if disp_in is not None and disp_out is not None:
                _connect(_try_find(hm_node.GetOutputs(), P_OUTC), disp_in)
                _connect(disp_out, disp_port)

        t.Commit()


def create_or_update_rs_material(doc, mat_name: str, maps: dict, update_existing_only: bool = False):
    mat = find_material(doc, mat_name) if update_existing_only else find_or_create_material(doc, mat_name)
    if mat is None:
        return None

    nm = mat.GetNodeMaterialReference()
    if nm is None:
        raise RuntimeError("NodeMaterialReference is None")

    graph = rs_rebuild_graph(nm)
    build_material_graph(graph, maps)
    return mat
