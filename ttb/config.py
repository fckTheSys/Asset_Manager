# -*- coding: utf-8 -*-
import maxon

# !!! Поменяй на свой уникальный ID (если будешь распространять)
PLUGIN_ID = 10698765
PLUGIN_SLUG = "tanktoolbox"
PLUGIN_VERSION = "2.1.0"
PLUGIN_BUILD_DATE = "2026-05-08"
PLUGIN_NAME = "Tank Tool Box (RS/CL)"

# Выбор движков для сборки материалов в UI (см. ui_dialog)
ENGINES = ("redshift", "centileo")

# Redshift node space
if PLUGIN_ID == 10698765:
    print("[TankToolBox] WARNING: PLUGIN_ID uses placeholder 10698765. "
          "Register and set your unique Maxon plugin ID in ttb.config.")

RS_SPACE = maxon.Id("com.redshift3d.redshift4c4d.class.nodespace")

# Maps / Parts (RM = roughness; GM = gloss→invert; EM = emission; OP = opacity; HM = height/displacement)
MAP_TYPES = ("AM", "AO", "NM", "MM", "GM", "RM", "EM", "OP", "HM")

PART_KEYS = {
    "hull": "Hull",
    "turret": "Turret",
    "track": "Track",
    "gun": "Gun",
    "chassis": "Chassis",
}
VALID_PARTS = set(PART_KEYS.values())

# Universal texture aliases config (relative to ttb package)
TEXTURE_ALIASES_FILE = "texture_aliases.json"

# Extensions
TEX_EXT = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".exr", ".tga", ".bmp", ".dds"}

# Crash rule
CRASH_TOKEN = "crash"
CRUSH_TOKEN = "crush"

# Redshift nodes (asset ids)
NODE_TEX  = "com.redshift3d.redshift4c4d.nodes.core.texturesampler"
NODE_BUMP = "com.redshift3d.redshift4c4d.nodes.core.bumpmap"
NODE_INV  = "com.redshift3d.redshift4c4d.nodes.core.rsmathinvcolor"
NODE_DISP = "com.redshift3d.redshift4c4d.nodes.core.displacement"

# StandardMaterial ports
P_BASE     = "com.redshift3d.redshift4c4d.nodes.core.standardmaterial.base_color"
P_MET      = "com.redshift3d.redshift4c4d.nodes.core.standardmaterial.metalness"
P_ROU      = "com.redshift3d.redshift4c4d.nodes.core.standardmaterial.refl_roughness"
P_BMP      = "com.redshift3d.redshift4c4d.nodes.core.standardmaterial.bump_input"
P_EMISSION = "com.redshift3d.redshift4c4d.nodes.core.standardmaterial.emission_color"
P_OPACITY  = "com.redshift3d.redshift4c4d.nodes.core.standardmaterial.opacity"
P_STD_OUT  = "com.redshift3d.redshift4c4d.nodes.core.standardmaterial.outcolor"
P_OUT_SURF = "com.redshift3d.redshift4c4d.node.output.surface"
P_OUT_DISP = "com.redshift3d.redshift4c4d.node.output.displacement"

# TextureSampler ports
P_TEX0 = "com.redshift3d.redshift4c4d.nodes.core.texturesampler.tex0"
P_OUTC = "com.redshift3d.redshift4c4d.nodes.core.texturesampler.outcolor"
P_AO_MUL = "com.redshift3d.redshift4c4d.nodes.core.texturesampler.color_multiplier"
P_TEX0_PATH = "path"
P_TEX0_COLORSPACE = "colorspace"  # !!! важно: лежит внутри tex0

# Bump ports
P_BUMP_IN   = "com.redshift3d.redshift4c4d.nodes.core.bumpmap.input"
P_BUMP_OUT  = "com.redshift3d.redshift4c4d.nodes.core.bumpmap.out"
P_BUMP_TYPE = "com.redshift3d.redshift4c4d.nodes.core.bumpmap.inputtype"
BUMP_TANGENT_SPACE_NORMAL = 1  # Tangent Space Normal = 1 (ты уточнил)

# Invert ports
P_INV_IN  = "com.redshift3d.redshift4c4d.nodes.core.rsmathinvcolor.input"
P_INV_OUT = "com.redshift3d.redshift4c4d.nodes.core.rsmathinvcolor.outcolor"

# Displacement node ports (texture -> disp.texmap; disp.out -> output.displacement)
P_DISP_TEX  = "com.redshift3d.redshift4c4d.nodes.core.displacement.texmap"
P_DISP_OUT  = "com.redshift3d.redshift4c4d.nodes.core.displacement.out"



# ColorSpace values (strings)
CS_AUTO = ""  # Auto
CS_RAW  = "RS_INPUT_COLORSPACE_RAW"
CS_SRGB = "sRGB"

# ---------------------------------------------------------------------------
# CENTILEO — см. ttb/CL_SPACE_README.txt
# ---------------------------------------------------------------------------

CL_SPACE_CANDIDATES = [
    maxon.Id("com.centileo.class.nodespace"),
    maxon.Id("com.centileo.nodespace.cntl"),
]

CL_NODEID_MATERIAL = "material_node"
CL_NODEID_OUTPUT = "output_node"

CL_P_DIFFUSE_COLOR = "diffuse_color"
CL_P_DIFFUSE_ROUGH = "diffuse_rough"
CL_P_DIFFUSE_METAL = "diffuse_metalness"
CL_P_BUMP_MAP = "bump_map"
CL_P_ALPHA_MAP = "alpha_map"

CL_P_MATERIAL_OUT = "result"

CL_P_OUT_SURF = "surface_material"
CL_P_OUT_DISP = "displacement_map"

CL_P_EMISSION_COLOR = "emission_color"
CL_P_DISP_MAP = "displacement_map"
CL_P_DISP_OUT = "result"

CL_P_FILENAME = "filename"
CL_P_COLORSPACE = "colorspace"
CL_P_BITMAP_RESULT = "result"
CL_P_BITMAP_ALPHA = "result_alpha"

CL_P_MATH_A = "math_a"
CL_P_MATH_TYPE = "math_type"
CL_P_MATH_RESULT = "result"

CL_CS_SRGB = "sRGB"
CL_CS_RAW = "Raw"

CL_BITMAP_ASSET_CANDIDATES = (
    "bitmap",
    "Bitmap",
    "net.centileo.c4d.nodes.bitmap",
    "com.centileo.c4d.nodes.bitmap",
    "com.centileo.class.node.bitmap",
    "com.centileo.nodes.bitmap",
    "com.centileo.nodespace.cntl.node.bitmap",
    "com.centileo.c4d.nodes.core.bitmap",
    "com.centileo.c4d.nodes.core.texturesampler",
    "cntl.node.bitmap",
    "centileo.bitmap",
    "com.centileo.c4d.node.bitmap",
    "net.centileo.nodes.bitmap",
    "com.centileo.nodes.core.bitmap",
    "com.centileo.nodes.texture",
    "com.centileo.node.bitmap",
    "texture",
    "Texture",
    "texturesampler",
)
CL_NODE_BITMAP = CL_BITMAP_ASSET_CANDIDATES[0]

CL_MATH_ASSET_CANDIDATES = (
    "net.centileo.c4d.nodes.math",
    "com.centileo.c4d.nodes.math",
)
