# -*- coding: utf-8 -*-
"""
Asset Browser dialog: list models by root (Tanks or Universal), multi-select,
actions Import / Build shaders / Apply materials for selected only.
"""
import os
import c4d

from .io_scan import collect_tasks, collect_universal_tasks, is_dir, normpath
from .scene_ops import (
    import_fbx,
    apply_materials_to_tank,
    apply_materials_generic,
    collect_mats_by_part,
    collect_mats_for_model,
)
from .rs_graph import create_or_update_rs_material
from .cl_graph import create_or_update_cl_material


def _mat_builder(engine: str):
    if engine == "centileo":
        return create_or_update_cl_material
    return create_or_update_rs_material

# --- IDs: separate range from ui_dialog (3000–3599) ---
ID_ROOT_LABEL = 3000
ID_REFRESH = 3001
ID_SCROLL = 3002
ID_GROUP_LIST = 3003
ID_PLACEHOLDER = 3004
ID_TEX_PREVIEW = 3005
ID_FILTER = 3006
ID_SELECTED_COUNT = 3007
ID_SELECT_ALL = 3010
ID_DESELECT_ALL = 3011
ID_IMPORT = 3012
ID_SHADERS = 3013
ID_APPLY = 3014
ID_CLOSE = 3015
ID_VALIDATE = 3016
ID_TASK_CHECK_START = 3100  # 3100..3599 → up to 500 tasks


from .log import info as _log_info


def _log(msg: str):
    _log_info(msg)


def _task_name(task: dict, mode: str) -> str:
    return task["tank"] if mode == "tanks" else task["name"]


def _short_path(path: str, max_len: int = 50) -> str:
    if not path or len(path) <= max_len:
        return path or ""
    return "..." + path[-(max_len - 3) :]


class AssetBrowserDialog(c4d.gui.GeDialog):
    def __init__(self, root_path: str, mode: str, engines=("redshift",), update_existing_only=False):
        super().__init__()
        self._root_path = normpath(root_path or "").strip()
        self._mode = "tanks" if mode == "tanks" else "universal"
        self._tasks = []
        self._visible_tasks = []
        self._engines = engines if engines else ("redshift",)
        self._update_existing_only = bool(update_existing_only)

    def CreateLayout(self):
        self.SetTitle("Asset Browser — " + ("Tanks" if self._mode == "tanks" else "Universal"))
        self.GroupBorderSpace(10, 10, 10, 10)

        # Root + Refresh
        self.AddStaticText(0, c4d.BFH_LEFT, name="Root:")
        self.GroupBegin(0, c4d.BFH_SCALEFIT, cols=2, rows=1)
        self.AddStaticText(ID_ROOT_LABEL, c4d.BFH_SCALEFIT, name=_short_path(self._root_path, 60) or "(none)")
        self.AddButton(ID_REFRESH, c4d.BFH_RIGHT, initw=80, inith=0, name="Refresh")
        self.GroupEnd()

        self.AddSeparatorH(c4d.BFH_SCALEFIT)
        self.GroupBegin(0, c4d.BFH_SCALEFIT, cols=2, rows=1)
        self.AddStaticText(0, c4d.BFH_LEFT, name="Filter:")
        self.AddEditText(ID_FILTER, c4d.BFH_SCALEFIT, initw=320)
        self.GroupEnd()
        self.AddStaticText(ID_SELECTED_COUNT, c4d.BFH_LEFT, name="Selected: 0")

        self.AddSeparatorH(c4d.BFH_SCALEFIT)

        # Action bar: always visible above the list
        self.AddStaticText(0, c4d.BFH_LEFT, name="Actions:")
        self.GroupBegin(0, c4d.BFH_SCALEFIT, cols=6, rows=1)
        self.AddButton(ID_SELECT_ALL, c4d.BFH_LEFT, initw=90, inith=0, name="Select all")
        self.AddButton(ID_DESELECT_ALL, c4d.BFH_LEFT, initw=100, inith=0, name="Deselect all")
        self.AddButton(ID_VALIDATE, c4d.BFH_LEFT, initw=110, inith=0, name="Validate selected")
        self.AddButton(ID_IMPORT, c4d.BFH_LEFT, initw=110, inith=0, name="Import selected")
        self.AddButton(ID_SHADERS, c4d.BFH_LEFT, initw=120, inith=0, name="Build shaders")
        self.AddButton(ID_APPLY, c4d.BFH_LEFT, initw=100, inith=0, name="Apply materials")
        self.GroupEnd()

        self.AddSeparatorH(c4d.BFH_SCALEFIT)

        # List area (plain group so LayoutFlushGroup + GroupBegin refill works reliably in C4D 2026)
        self.GroupBegin(ID_GROUP_LIST, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, cols=1, rows=0, initw=520, inith=280)
        self.AddStaticText(ID_PLACEHOLDER, c4d.BFH_LEFT, name="Press Refresh to load models.")
        self.GroupEnd()

        self.AddSeparatorH(c4d.BFH_SCALEFIT)

        # Texture preview for selected row (optional)
        self.AddStaticText(0, c4d.BFH_LEFT, name="Textures (selected model):")
        self.AddMultiLineEditText(ID_TEX_PREVIEW, c4d.BFH_SCALEFIT | c4d.BFV_SCALE, inith=50, style=c4d.DR_MULTILINE_READONLY)

        self.AddSeparatorH(c4d.BFH_SCALEFIT)

        self.AddButton(ID_CLOSE, c4d.BFH_SCALEFIT, initw=0, inith=0, name="Close")

        return True

    def InitValues(self):
        self._load_tasks()
        self._fill_list()
        return True

    def _load_tasks(self):
        if not self._root_path or not is_dir(self._root_path):
            self._tasks = []
            return
        if self._mode == "tanks":
            self._tasks = collect_tasks(self._root_path)
        else:
            self._tasks = collect_universal_tasks(self._root_path)
        self._apply_filter()

    def _apply_filter(self):
        try:
            needle = self.GetString(ID_FILTER).strip().lower()
        except Exception:
            needle = ""
        if not needle:
            self._visible_tasks = list(self._tasks)
            return
        self._visible_tasks = [
            t for t in self._tasks
            if needle in _task_name(t, self._mode).lower()
            or needle in str(t.get("fbx", "")).lower()
        ]

    def _fill_list(self):
        self.LayoutFlushGroup(ID_GROUP_LIST)
        display_root = _short_path(self._root_path, 60) or "(none)"
        self.SetString(ID_ROOT_LABEL, display_root)

        # Re-open the list group so new elements become its children (C4D requirement after FlushGroup)
        self.GroupBegin(ID_GROUP_LIST, c4d.BFH_LEFT | c4d.BFV_TOP, cols=1, rows=0)

        if not self._visible_tasks:
            self.AddStaticText(ID_PLACEHOLDER, c4d.BFH_LEFT, name="No models found. Press Refresh to reload.")
            self.GroupEnd()
            self.LayoutChanged(ID_GROUP_LIST)
            self._update_selected_count()
            return

        # Header row
        self.GroupBegin(0, c4d.BFH_LEFT | c4d.BFV_TOP, cols=4, rows=1)
        self.AddStaticText(0, c4d.BFH_LEFT, name="")
        self.AddStaticText(0, c4d.BFH_SCALEFIT, name="Name")
        self.AddStaticText(0, c4d.BFH_SCALEFIT, name="FBX")
        self.AddStaticText(0, c4d.BFH_RIGHT, name="Tex")
        self.GroupEnd()

        max_tasks = 500
        for i, task in enumerate(self._visible_tasks):
            if i >= max_tasks:
                self.AddStaticText(0, c4d.BFH_LEFT, name=f"... and {len(self._visible_tasks) - max_tasks} more")
                break
            name = _task_name(task, self._mode)
            fbx = task.get("fbx", "")
            tex_count = sum(len(maps) for maps in task.get("groups", {}).values())
            gid = ID_TASK_CHECK_START + i
            self.GroupBegin(0, c4d.BFH_LEFT | c4d.BFV_TOP, cols=4, rows=1)
            self.AddCheckbox(gid, c4d.BFH_LEFT, initw=20, inith=0, name="")
            self.AddStaticText(0, c4d.BFH_SCALEFIT, name=name)
            self.AddStaticText(0, c4d.BFH_SCALEFIT, name=_short_path(fbx, 45))
            self.AddStaticText(0, c4d.BFH_RIGHT, name=str(tex_count))
            self.GroupEnd()

        self.GroupEnd()
        self.LayoutChanged(ID_GROUP_LIST)
        self._update_selected_count()

    def _get_selected_tasks(self):
        for i, task in enumerate(self._visible_tasks):
            if i >= 500:
                break
            try:
                if self.GetBool(ID_TASK_CHECK_START + i):
                    yield task
            except Exception:
                continue

    def _get_selected_list_indices(self):
        out = []
        for i in range(min(len(self._visible_tasks), 500)):
            try:
                if self.GetBool(ID_TASK_CHECK_START + i):
                    out.append(i)
            except Exception:
                continue
        return out

    def _update_tex_preview(self):
        sel = self._get_selected_list_indices()
        if len(sel) != 1 or not self._visible_tasks:
            self.SetString(ID_TEX_PREVIEW, "")
            self._update_selected_count()
            return
        task = self._visible_tasks[sel[0]]
        lines = []
        for part, maps in task.get("groups", {}).items():
            lines.append("[%s]" % part)
            for typ, path in (maps or {}).items():
                lines.append(f"  {typ}: {path}")
        self.SetString(ID_TEX_PREVIEW, "\n".join(lines) if lines else "(no textures)")
        self._update_selected_count()

    def _update_selected_count(self):
        count = len(list(self._get_selected_tasks()))
        try:
            self.SetString(ID_SELECTED_COUNT, "Selected: %s / %s" % (count, len(self._visible_tasks)))
        except Exception:
            pass

    def _report_path(self):
        return os.path.join(self._root_path, "ttb_asset_browser_report.txt")

    def _write_report(self, title, body):
        try:
            with open(self._report_path(), "a", encoding="utf-8") as f:
                f.write("\n=== %s ===\n%s\n" % (title, body))
        except Exception as e:
            _log("[ERROR] report export failed: %s" % e)

    def _validate_selected(self):
        selected = list(self._get_selected_tasks())
        if not selected:
            c4d.gui.MessageDialog("Select at least one model.")
            return
        lines = ["Validate selected: %s" % len(selected)]
        ok_count = 0
        for task in selected:
            name = _task_name(task, self._mode)
            problems = []
            if not task.get("fbx") or not os.path.isfile(task.get("fbx", "")):
                problems.append("missing FBX")
            if not task.get("groups"):
                problems.append("no texture groups")
            if problems:
                lines.append("%s: %s" % (name, ", ".join(problems)))
            else:
                ok_count += 1
                lines.append("%s: OK" % name)
        lines.append("OK: %s / %s" % (ok_count, len(selected)))
        report = "\n".join(lines)
        self._write_report("Validate selected", report)
        c4d.gui.MessageDialog(report)

    def _action_import(self):
        doc = c4d.documents.GetActiveDocument()
        if not doc:
            c4d.gui.MessageDialog("No active document.")
            return
        selected = list(self._get_selected_tasks())
        if not selected:
            c4d.gui.MessageDialog("Select at least one model (check the boxes in the list).")
            return
        _log("--- Asset Browser: Import selected ---")
        imported = 0
        for task in selected:
            name = _task_name(task, self._mode)
            fbx = task.get("fbx", "")
            if fbx:
                ok = import_fbx(doc, name, fbx)
                if ok:
                    imported += 1
                _log(f"Import {name}: {ok}")
                c4d.EventAdd()
        report = f"Imported {imported} of {len(selected)} model(s)."
        self._write_report("Import selected", report)
        c4d.gui.MessageDialog(report)

    def _action_shaders(self):
        doc = c4d.documents.GetActiveDocument()
        if not doc:
            c4d.gui.MessageDialog("No active document.")
            return
        selected = list(self._get_selected_tasks())
        if not selected:
            c4d.gui.MessageDialog("Select at least one model.")
            return
        _log("--- Asset Browser: Build shaders selected ---")
        processed = 0
        skipped = 0
        errors = 0
        for task in selected:
            name = _task_name(task, self._mode)
            for part, maps in task.get("groups", {}).items():
                mat_name = f"{name}_{part}"
                for engine in self._engines:
                    try:
                        mat = _mat_builder(engine)(
                            doc,
                            mat_name,
                            maps,
                            update_existing_only=self._update_existing_only,
                        )
                        if mat is None:
                            skipped += 1
                        else:
                            processed += 1
                    except Exception as e:
                        errors += 1
                        _log(f"[ERROR] {engine} {name}/{part}: {e}")
            c4d.EventAdd()
        report = "Shaders updated.\nMaterials: %s\nSkipped existing-only: %s\nErrors: %s" % (
            processed,
            skipped,
            errors,
        )
        self._write_report("Build shaders selected", report)
        c4d.gui.MessageDialog(report)

    def _action_apply(self):
        doc = c4d.documents.GetActiveDocument()
        if not doc:
            c4d.gui.MessageDialog("No active document.")
            return
        selected = list(self._get_selected_tasks())
        if not selected:
            c4d.gui.MessageDialog("Select at least one model.")
            return
        _log("--- Asset Browser: Apply materials selected ---")
        total = 0
        for task in selected:
            name = _task_name(task, self._mode)
            mats_by_part = collect_mats_by_part(doc, name) if self._mode == "tanks" else collect_mats_for_model(doc, name)
            if self._mode == "tanks":
                total += apply_materials_to_tank(doc, name, mats_by_part)
            else:
                total += apply_materials_generic(doc, name, mats_by_part)
        c4d.EventAdd()
        report = f"Materials applied. Tags: {total}"
        self._write_report("Apply selected", report)
        c4d.gui.MessageDialog(report)

    def Command(self, wid, msg):
        if wid == ID_REFRESH:
            self._load_tasks()
            self._fill_list()
            return True
        if wid == ID_FILTER:
            self._apply_filter()
            self._fill_list()
            return True
        if wid == ID_SELECT_ALL:
            for i in range(min(len(self._visible_tasks), 500)):
                try:
                    self.SetBool(ID_TASK_CHECK_START + i, True)
                except Exception:
                    pass
            self._update_tex_preview()
            return True
        if wid == ID_DESELECT_ALL:
            for i in range(min(len(self._visible_tasks), 500)):
                try:
                    self.SetBool(ID_TASK_CHECK_START + i, False)
                except Exception:
                    pass
            self.SetString(ID_TEX_PREVIEW, "")
            self._update_selected_count()
            return True
        if wid == ID_VALIDATE:
            self._validate_selected()
            return True
        if wid == ID_IMPORT:
            self._action_import()
            return True
        if wid == ID_SHADERS:
            self._action_shaders()
            return True
        if wid == ID_APPLY:
            self._action_apply()
            return True
        if wid == ID_CLOSE:
            self.Close()
            return True
        # Checkbox toggled → update texture preview
        if ID_TASK_CHECK_START <= wid < ID_TASK_CHECK_START + 500:
            self._update_tex_preview()
            return True
        return True
