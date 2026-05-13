# -*- coding: utf-8 -*-
import os

import c4d

from .config import PLUGIN_ID, PLUGIN_NAME, PLUGIN_VERSION
from .io_scan import (
    collect_tasks,
    build_texture_index,
    is_dir,
    normpath,
    collect_universal_tasks,
)
from .rs_graph import create_or_update_rs_material
from .cl_graph import create_or_update_cl_material
from .scene_ops import (
    import_fbx,
    apply_materials_to_tank,
    collect_mats_by_part,
    collect_mats_for_model,
    apply_materials_generic,
)
from .relink import fix_node_texturesampler_paths, fix_legacy_bitmap_shaders
from .asset_browser import AssetBrowserDialog
from .diagnostics import run_self_check, summarize_tasks
from .log import info as log
from . import ui_help

# Layout / tabs (no Command handlers — structural ids only unless needed)
ID_GROUP_ENGINES = 1160
ID_MAIN_TABS = 1161
ID_TAB_PAGE_TANKS = 1162
ID_TAB_PAGE_UNIVERSAL = 1163
ID_GRP_TANKS_ROOT = 1164
ID_GRP_TANKS_ACTIONS = 1165
ID_GRP_TANKS_BROWSER = 1166
ID_GRP_UNI_ROOT = 1167
ID_GRP_UNI_ACTIONS = 1168
ID_GRP_UNI_BROWSER = 1169

# UI IDs (Tanks)
ID_PATH = 1001
ID_BROWSE = 1002
ID_INIT = 2001
ID_UPDATE_SHADERS = 2002
ID_APPLY = 2003
ID_FIX = 2004
ID_UPDATE_EXISTING_ONLY = 2005
ID_SELF_CHECK = 2006

# UI IDs (Universal)
ID_UNI_PATH = 1101
ID_UNI_BROWSE = 1102
ID_UNI_IMPORT = 2101
ID_UNI_SHADERS = 2102
ID_UNI_APPLY = 2103

# Asset Browser
ID_ASSET_BROWSER_TANKS = 2201
ID_ASSET_BROWSER_UNI = 2202

# Engine checkboxes (Redshift / CentiLeo)
ID_ENGINE_RS = 1050
ID_ENGINE_CL = 1051

# Справка по вкладкам
ID_HELP_TANKS = 2301
ID_HELP_UNIVERSAL = 2302


def _get_create_material_fn(engine: str):
    if engine == "centileo":
        return create_or_update_cl_material
    return create_or_update_rs_material

# (method_name, needs_doc) for Command dispatch
_COMMAND_HANDLERS = {
    ID_BROWSE: ("_browse", False),
    ID_UNI_BROWSE: ("_browse_uni", False),
    ID_INIT: ("_initialize", True),
    ID_UPDATE_SHADERS: ("_update_shaders", True),
    ID_APPLY: ("_apply", True),
    ID_FIX: ("_fix", True),
    ID_SELF_CHECK: ("_self_check", False),
    ID_UNI_IMPORT: ("_uni_import", True),
    ID_UNI_SHADERS: ("_uni_update_shaders", True),
    ID_UNI_APPLY: ("_uni_apply", True),
    ID_ASSET_BROWSER_TANKS: ("_open_asset_browser_tanks", False),
    ID_ASSET_BROWSER_UNI: ("_open_asset_browser_uni", False),
    ID_HELP_TANKS: ("_help_tanks", False),
    ID_HELP_UNIVERSAL: ("_help_universal", False),
}


class TankToolDialog(c4d.gui.GeDialog):
    def __init__(self):
        super().__init__()
        self.root_path = ""
        self.uni_root_path = ""
        self.asset_browser_dlg = None

    def CreateLayout(self):
        self.SetTitle("%s v%s" % (PLUGIN_NAME, PLUGIN_VERSION))
        self.GroupBorderSpace(10, 10, 10, 10)

        _border_title = c4d.BORDER_GROUP_IN | c4d.BORDER_WITH_TITLE_BOLD
        _border_plain = c4d.BORDER_GROUP_IN | c4d.BORDER_WITH_TITLE

        # --- Глобально: движки (вне вкладок) ---
        self.GroupBegin(
            ID_GROUP_ENGINES,
            c4d.BFH_SCALEFIT | _border_title,
            cols=1,
            rows=0,
            title="Материалы / движки",
            groupflags=0,
        )
        self.AddStaticText(0, c4d.BFH_LEFT, name="Собирать материалы для:")
        self.GroupBegin(0, c4d.BFH_SCALEFIT, cols=2, rows=1)
        self.AddCheckbox(ID_ENGINE_RS, c4d.BFH_LEFT, initw=0, inith=0, name="Redshift")
        self.AddCheckbox(ID_ENGINE_CL, c4d.BFH_LEFT, initw=0, inith=0, name="CentiLeo")
        self.GroupEnd()
        self.AddCheckbox(
            ID_UPDATE_EXISTING_ONLY,
            c4d.BFH_LEFT,
            initw=0,
            inith=0,
            name="Только обновлять существующие материалы (не создавать новые)",
        )
        self.AddStaticText(
            0,
            c4d.BFH_LEFT,
            name="Подсказка: если ни один движок не отмечен, используется Redshift.",
        )
        self.GroupEnd()

        # --- Вкладки Tanks | Universal ---
        self.TabGroupBegin(ID_MAIN_TABS, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, c4d.TAB_TABS)

        # Вкладка Tanks
        self.GroupBegin(
            ID_TAB_PAGE_TANKS,
            c4d.BFH_SCALEFIT | c4d.BFV_TOP,
            cols=1,
            rows=0,
            title="Tanks",
            groupflags=0,
        )
        self.GroupBegin(
            ID_GRP_TANKS_ROOT,
            c4d.BFH_SCALEFIT | _border_plain,
            cols=1,
            rows=0,
            title="Корень",
            groupflags=0,
        )
        self.AddStaticText(0, c4d.BFH_LEFT, name="Папка TANKS:")
        self.GroupBegin(0, c4d.BFH_SCALEFIT, cols=2, rows=1)
        self.AddEditText(ID_PATH, c4d.BFH_SCALEFIT, initw=420)
        self.AddButton(ID_BROWSE, c4d.BFH_RIGHT, name="...")
        self.GroupEnd()
        self.GroupEnd()

        self.GroupBegin(
            ID_GRP_TANKS_ACTIONS,
            c4d.BFH_SCALEFIT | _border_plain,
            cols=1,
            rows=0,
            title="Действия",
            groupflags=0,
        )
        self.AddButton(ID_INIT, c4d.BFH_SCALEFIT, name="Инициализировать (Import + Shaders)")
        self.AddButton(ID_UPDATE_SHADERS, c4d.BFH_SCALEFIT, name="Обновить шейдеры (только материалы)")
        self.AddButton(ID_APPLY, c4d.BFH_SCALEFIT, name="Применить к моделькам (по имени части)")
        self.AddButton(ID_FIX, c4d.BFH_SCALEFIT, name="Fix '?' (relink путей к текстурам)")
        self.AddStaticText(
            0,
            c4d.BFH_LEFT,
            name="Порядок: Инициализировать → при необходимости Обновить шейдеры → Применить → Fix при «?» в превью.",
        )
        self.GroupEnd()

        self.GroupBegin(
            ID_GRP_TANKS_BROWSER,
            c4d.BFH_SCALEFIT | _border_plain,
            cols=1,
            rows=0,
            title="Обзор",
            groupflags=0,
        )
        self.GroupBegin(0, c4d.BFH_SCALEFIT, cols=2, rows=1)
        self.AddButton(ID_ASSET_BROWSER_TANKS, c4d.BFH_SCALEFIT, name="Открыть Asset Browser…")
        self.AddButton(ID_HELP_TANKS, c4d.BFH_RIGHT, initw=120, inith=0, name="Справка…")
        self.GroupEnd()
        self.GroupEnd()
        self.GroupEnd()

        # Вкладка Universal
        self.GroupBegin(
            ID_TAB_PAGE_UNIVERSAL,
            c4d.BFH_SCALEFIT | c4d.BFV_TOP,
            cols=1,
            rows=0,
            title="Universal",
            groupflags=0,
        )
        self.GroupBegin(
            ID_GRP_UNI_ROOT,
            c4d.BFH_SCALEFIT | _border_plain,
            cols=1,
            rows=0,
            title="Корень",
            groupflags=0,
        )
        self.AddStaticText(0, c4d.BFH_LEFT, name="Universal root:")
        self.GroupBegin(0, c4d.BFH_SCALEFIT, cols=2, rows=1)
        self.AddEditText(ID_UNI_PATH, c4d.BFH_SCALEFIT, initw=420)
        self.AddButton(ID_UNI_BROWSE, c4d.BFH_RIGHT, name="...")
        self.GroupEnd()
        self.GroupEnd()

        self.GroupBegin(
            ID_GRP_UNI_ACTIONS,
            c4d.BFH_SCALEFIT | _border_plain,
            cols=1,
            rows=0,
            title="Действия",
            groupflags=0,
        )
        self.AddButton(ID_UNI_IMPORT, c4d.BFH_SCALEFIT, name="Импорт моделей")
        self.AddButton(ID_UNI_SHADERS, c4d.BFH_SCALEFIT, name="Сборка / обновление шейдеров")
        self.AddButton(ID_UNI_APPLY, c4d.BFH_SCALEFIT, name="Применить материалы")
        self.AddStaticText(
            0,
            c4d.BFH_LEFT,
            name="Порядок: Импорт → Шейдеры → Применить. Пути к FBX и текстурам берутся из сканирования корня.",
        )
        self.GroupEnd()

        self.GroupBegin(
            ID_GRP_UNI_BROWSER,
            c4d.BFH_SCALEFIT | _border_plain,
            cols=1,
            rows=0,
            title="Обзор",
            groupflags=0,
        )
        self.GroupBegin(0, c4d.BFH_SCALEFIT, cols=2, rows=1)
        self.AddButton(ID_ASSET_BROWSER_UNI, c4d.BFH_SCALEFIT, name="Открыть Asset Browser…")
        self.AddButton(ID_HELP_UNIVERSAL, c4d.BFH_RIGHT, initw=120, inith=0, name="Справка…")
        self.GroupEnd()
        self.GroupEnd()
        self.GroupEnd()

        self.GroupEnd()

        self.AddSeparatorH(c4d.BFH_SCALEFIT)
        self.AddButton(ID_SELF_CHECK, c4d.BFH_SCALEFIT, name="Self check / диагностика")

        return True

    def InitValues(self):
        try:
            self.SetBool(ID_ENGINE_RS, True)
            self.SetBool(ID_ENGINE_CL, False)
        except Exception:
            pass
        try:
            self.SetBool(ID_UPDATE_EXISTING_ONLY, False)
        except Exception:
            pass
        return True

    def _get_engines(self):
        result = []
        try:
            if self.GetBool(ID_ENGINE_RS):
                result.append("redshift")
            if self.GetBool(ID_ENGINE_CL):
                result.append("centileo")
        except Exception:
            pass
        return tuple(result) if result else ("redshift",)

    def _update_existing_only(self):
        try:
            return bool(self.GetBool(ID_UPDATE_EXISTING_ONLY))
        except Exception:
            return False

    def _browse(self):
        p = c4d.storage.LoadDialog(title="Выбери папку TANKS", flags=c4d.FILESELECT_DIRECTORY)
        if p:
            self.root_path = normpath(p)
            self.SetString(ID_PATH, self.root_path)

    def _get_root(self):
        return normpath(self.GetString(ID_PATH).strip())

    def _browse_uni(self):
        p = c4d.storage.LoadDialog(title="Select universal root", flags=c4d.FILESELECT_DIRECTORY)
        if p:
            self.uni_root_path = normpath(p)
            self.SetString(ID_UNI_PATH, self.uni_root_path)

    def _get_uni_root(self):
        return normpath(self.GetString(ID_UNI_PATH).strip())

    def _get_tasks_for_root(self, root, collect_fn, msg_invalid_path, msg_empty):
        if not is_dir(root):
            c4d.gui.MessageDialog(msg_invalid_path)
            return None
        tasks = collect_fn(root)
        if not tasks:
            c4d.gui.MessageDialog(msg_empty)
            return None
        return tasks

    def _get_tasks(self):
        return self._get_tasks_for_root(
            self._get_root(),
            collect_tasks,
            "Путь к папке TANKS неверный.",
            "Не найдено ни одного танка.",
        )

    def _get_uni_tasks(self):
        return self._get_tasks_for_root(
            self._get_uni_root(),
            collect_universal_tasks,
            "Universal root path is invalid.",
            "No models found in universal root.",
        )

    def _run_update_shaders_for_tasks(self, doc, tasks, name_key, log_prefix=""):
        engines = self._get_engines()
        created_or_updated = 0
        skipped = 0
        errors = 0
        update_only = self._update_existing_only()
        for t in tasks:
            name = t[name_key]
            for part, maps in t["groups"].items():
                mat_name = f"{name}_{part}"
                for engine in engines:
                    try:
                        mat = _get_create_material_fn(engine)(
                            doc,
                            mat_name,
                            maps,
                            update_existing_only=update_only,
                        )
                        if mat is None:
                            skipped += 1
                        else:
                            created_or_updated += 1
                    except Exception as e:
                        errors += 1
                        log(f"[ERROR]{log_prefix} {engine} {name}/{part}: {e}")
            c4d.EventAdd()
        return {
            "materials": created_or_updated,
            "skipped": skipped,
            "errors": errors,
            "engines": ",".join(engines),
        }

    def _export_report(self, root: str, title: str, body: str):
        if not root or not is_dir(root):
            return
        path = os.path.join(root, "ttb_report.txt")
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write("\n=== %s ===\n%s\n" % (title, body))
        except Exception as e:
            log("[ERROR] report export failed: %s" % e)

    def _self_check(self):
        c4d.gui.MessageDialog("\n".join(run_self_check()))

    def _help_tanks(self):
        c4d.gui.MessageDialog(ui_help.HELP_TANKS_TAB)

    def _help_universal(self):
        c4d.gui.MessageDialog(ui_help.HELP_UNIVERSAL_TAB)

    def _initialize(self, doc):
        tasks = self._get_tasks()
        if not tasks:
            return

        # Import FBX
        log("--- INIT: Import ---")
        for t in tasks:
            ok = import_fbx(doc, t["tank"], t["fbx"])
            log(f"Import {t['tank']}: {ok}")
            c4d.EventAdd()

        log("--- INIT: Shaders ---")
        stats = self._run_update_shaders_for_tasks(doc, tasks, "tank")
        report = summarize_tasks(tasks, "tanks")
        report += "\nMaterials processed: {materials}\nSkipped existing-only: {skipped}\nErrors: {errors}".format(**stats)
        self._export_report(self._get_root(), "INIT Tanks", report)
        c4d.gui.MessageDialog("Готово: импорт + материалы.")

    def _uni_import(self, doc):
        tasks = self._get_uni_tasks()
        if not tasks:
            return

        log("--- UNIVERSAL: Import ---")
        imported = 0
        for t in tasks:
            name = t["name"]
            ok = import_fbx(doc, name, t["fbx"])
            if ok:
                imported += 1
            log(f"Import {name}: {ok}")
            c4d.EventAdd()
        report = summarize_tasks(tasks, "universal") + "\nImported: %s" % imported
        self._export_report(self._get_uni_root(), "Import Universal", report)

    def _update_shaders(self, doc):
        tasks = self._get_tasks()
        if not tasks:
            return
        log("--- UPDATE SHADERS ---")
        stats = self._run_update_shaders_for_tasks(doc, tasks, "tank")
        report = summarize_tasks(tasks, "tanks")
        report += "\nMaterials processed: {materials}\nSkipped existing-only: {skipped}\nErrors: {errors}".format(**stats)
        self._export_report(self._get_root(), "Update Shaders Tanks", report)
        c4d.gui.MessageDialog("Шейдеры обновлены.\n" + report)

    def _uni_update_shaders(self, doc):
        tasks = self._get_uni_tasks()
        if not tasks:
            return
        log("--- UNIVERSAL: Shaders ---")
        stats = self._run_update_shaders_for_tasks(doc, tasks, "name", "[UNI] ")
        report = summarize_tasks(tasks, "universal")
        report += "\nMaterials processed: {materials}\nSkipped existing-only: {skipped}\nErrors: {errors}".format(**stats)
        self._export_report(self._get_uni_root(), "Update Shaders Universal", report)
        c4d.gui.MessageDialog("Universal shaders updated.\n" + report)

    def _apply(self, doc):
        tasks = self._get_tasks()
        if not tasks:
            return

        total = 0
        for t in tasks:
            tank = t["tank"]
            mats_by_part = collect_mats_by_part(doc, tank)
            total += apply_materials_to_tank(doc, tank, mats_by_part)

        c4d.EventAdd()
        self._export_report(self._get_root(), "Apply Tanks", "Tasks: %s\nTags: %s" % (len(tasks), total))
        c4d.gui.MessageDialog(f"Материалы назначены. Тегов: {total}")

    def _uni_apply(self, doc):
        tasks = self._get_uni_tasks()
        if not tasks:
            return

        total = 0
        for t in tasks:
            name = t["name"]
            mats_by_part = collect_mats_for_model(doc, name)
            # Для универсального режима используем более мягкую логику назначения
            total += apply_materials_generic(doc, name, mats_by_part)

        c4d.EventAdd()
        self._export_report(self._get_uni_root(), "Apply Universal", "Tasks: %s\nTags: %s" % (len(tasks), total))
        c4d.gui.MessageDialog(f"Universal materials applied. Tags: {total}")

    def _open_asset_browser_tanks(self):
        root = self._get_root()
        if not root:
            c4d.gui.MessageDialog("Сначала выберите корень (Tanks) в поле выше.")
            return
        self.asset_browser_dlg = AssetBrowserDialog(
            root,
            "tanks",
            engines=self._get_engines(),
            update_existing_only=self._update_existing_only(),
        )
        self.asset_browser_dlg.Open(c4d.DLG_TYPE_ASYNC, PLUGIN_ID + 1, defaultw=680, defaulth=560)

    def _open_asset_browser_uni(self):
        root = self._get_uni_root()
        if not root:
            c4d.gui.MessageDialog("Сначала выберите корень (Universal) в поле выше.")
            return
        self.asset_browser_dlg = AssetBrowserDialog(
            root,
            "universal",
            engines=self._get_engines(),
            update_existing_only=self._update_existing_only(),
        )
        self.asset_browser_dlg.Open(c4d.DLG_TYPE_ASYNC, PLUGIN_ID + 1, defaultw=680, defaulth=560)

    def _fix(self, doc):
        tasks = self._get_tasks()
        if not tasks:
            return

        idx = {}
        for t in tasks:
            tex_dir = t.get("tex_dir")
            if tex_dir:
                idx.update(build_texture_index(tex_dir))

        engines = self._get_engines()
        fixed_node = fix_node_texturesampler_paths(doc, idx, engines=engines)
        fixed_old = fix_legacy_bitmap_shaders(doc, idx)

        c4d.EventAdd()
        self._export_report(
            self._get_root(),
            "Fix Tanks",
            "Tasks: %s\nNode relink: %s\nBitmap relink: %s" % (len(tasks), fixed_node, fixed_old),
        )
        c4d.gui.MessageDialog(f"Fix done:\nNode relink: {fixed_node}\nBitmap relink: {fixed_old}")

    def Command(self, wid, msg):
        entry = _COMMAND_HANDLERS.get(wid)
        if entry is not None:
            method_name, needs_doc = entry
            handler = getattr(self, method_name)
            if needs_doc:
                doc = c4d.documents.GetActiveDocument()
                handler(doc)
            else:
                handler()
            return True
        return True


class TankToolCommand(c4d.plugins.CommandData):
    dlg = None

    def Execute(self, doc):
        if self.dlg is None:
            self.dlg = TankToolDialog()
        return self.dlg.Open(c4d.DLG_TYPE_ASYNC, PLUGIN_ID, defaultw=560, defaulth=0)

    def RestoreLayout(self, sec_ref):
        if self.dlg is None:
            self.dlg = TankToolDialog()
        return self.dlg.Restore(PLUGIN_ID, sec_ref)
