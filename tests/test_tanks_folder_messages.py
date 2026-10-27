# -*- coding: utf-8 -*-
"""Exercise the real scanner/dialog handlers with only the C4D boundary stubbed."""
import importlib
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch


def load_dialog_modules(plugin_root):
    package_name = "_ttb_folder_message_tests"
    package = types.ModuleType(package_name)
    package.__path__ = [str(plugin_root / "ttb")]
    c4d = types.ModuleType("c4d")
    c4d.gui = types.SimpleNamespace(GeDialog=object, MessageDialog=Mock())
    c4d.plugins = types.SimpleNamespace(CommandData=object)
    c4d.documents = types.SimpleNamespace(GetActiveDocument=Mock(return_value=object()))
    c4d.EventAdd = Mock()
    maxon = types.ModuleType("maxon")
    maxon.Id = str
    modules = {package_name: package, "c4d": c4d, "maxon": maxon}
    boundaries = {
        "rs_graph": ("create_or_update_rs_material",),
        "cl_graph": ("create_or_update_cl_material",),
        "scene_ops": (
            "import_fbx", "apply_materials_to_tank", "collect_mats_by_part",
            "collect_mats_for_model", "apply_materials_generic",
        ),
        "relink": ("fix_node_texturesampler_paths", "fix_legacy_bitmap_shaders"),
    }
    for name, attributes in boundaries.items():
        module = types.ModuleType(package_name + "." + name)
        for attribute in attributes:
            setattr(module, attribute, Mock())
        modules[module.__name__] = module
    with patch.dict(sys.modules, modules):
        dialog = importlib.import_module(package_name + ".ui_dialog")
        browser = importlib.import_module(package_name + ".asset_browser")
    return dialog, browser, c4d


PLUGIN_ROOT = Path(os.environ.get("TTB_TEST_PLUGIN_ROOT", Path(__file__).resolve().parents[1]))
ui, browser, host = load_dialog_modules(PLUGIN_ROOT)


class TanksFolderMessagesTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "TANKS"
        self.fin = self.root / "Tank" / "FIN"
        self.fin.mkdir(parents=True)
        (self.fin / "VNII_100LT.fbx").touch()
        self.dialog = ui.TankToolDialog()
        self.dialog._get_root = lambda: str(self.root)
        self.dialog._export_report = Mock()
        self.dialog._run_update_shaders_for_tasks = Mock(return_value={
            "materials": 0, "skipped": 0, "errors": 0,
        })
        host.gui.MessageDialog.reset_mock()
        host.EventAdd.reset_mock()
        ui.import_fbx.reset_mock()

    def message(self):
        return host.gui.MessageDialog.call_args.args[0]

    def add_textures(self, directory="Original_textures", filename="Tank_hull_AM.tga"):
        folder = self.fin / directory
        folder.mkdir(exist_ok=True)
        (folder / filename).touch()
        return folder

    def test_fin_path_explains_expected_structure_and_root(self):
        self.dialog._get_root = lambda: str(self.fin)
        self.assertIsNone(self.dialog._get_tasks())
        self.assertIn(str(self.fin), self.message())
        self.assertIn(str(self.root), self.message())
        self.assertIn("TANKS", self.message())
        self.assertIn("FIN", self.message())

    def test_model_path_suggests_parent_root(self):
        self.dialog._get_root = lambda: str(self.fin.parent)
        self.assertIsNone(self.dialog._get_tasks())
        self.assertIn(str(self.root), self.message())

    def test_missing_root_message_contains_the_actual_path(self):
        missing = self.root / "missing"
        self.dialog._get_root = lambda: str(missing)
        self.assertIsNone(self.dialog._get_tasks())
        self.assertIn(str(missing), self.message())

    def test_empty_root_explains_model_fin_fbx_structure(self):
        empty = self.root / "Empty"
        empty.mkdir()
        self.dialog._get_root = lambda: str(empty)
        self.assertIsNone(self.dialog._get_tasks())
        self.assertIn("FIN", self.message())
        self.assertIn(".fbx", self.message())

    def test_missing_fbx_identifies_fin_folder(self):
        (self.fin / "VNII_100LT.fbx").unlink()
        self.assertIsNone(self.dialog._get_tasks())
        self.assertIn(str(self.fin), self.message())
        self.assertIn("FBX", self.message())

    def test_initialize_reports_tex_folder_before_import(self):
        tex = self.add_textures("TEX")
        self.dialog._initialize(object())
        ui.import_fbx.assert_not_called()
        self.dialog._run_update_shaders_for_tasks.assert_not_called()
        self.dialog._export_report.assert_not_called()
        self.assertIn("Original_textures", self.message())
        self.assertIn(str(tex), self.message())

    def test_shader_update_explains_missing_texture_directory(self):
        self.dialog._update_shaders(object())
        self.dialog._run_update_shaders_for_tasks.assert_not_called()
        self.assertIn(str(self.fin / "Original_textures"), self.message())
        self.assertIn(str(self.fin.parent / "Original_textures"), self.message())

    def test_empty_texture_directory_has_distinct_message(self):
        tex = self.add_textures(filename="notes.txt")
        self.dialog._update_shaders(object())
        self.dialog._run_update_shaders_for_tasks.assert_not_called()
        self.assertIn(str(tex), self.message())
        self.assertIn("распознан", self.message())

    def test_valid_layout_keeps_scanner_result_unchanged(self):
        self.add_textures()
        expected = ui.collect_tasks(str(self.root))
        self.assertEqual(self.dialog._get_tasks(), expected)
        host.gui.MessageDialog.assert_not_called()

    def test_valid_initialize_still_imports_and_builds_materials(self):
        self.add_textures()
        document = object()
        self.dialog._initialize(document)
        ui.import_fbx.assert_called_once_with(document, "Tank", str(self.fin / "VNII_100LT.fbx"))
        self.dialog._run_update_shaders_for_tasks.assert_called_once()
        self.dialog._export_report.assert_called_once()

    def test_texture_directory_beside_fin_remains_valid(self):
        tex = self.fin.parent / "Original_textures"
        tex.mkdir()
        (tex / "Tank_hull_AM.tga").touch()
        self.dialog._update_shaders(object())
        self.dialog._run_update_shaders_for_tasks.assert_called_once()

    def test_material_apply_task_lookup_does_not_require_textures(self):
        tasks = self.dialog._get_tasks()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["groups"], {})
        host.gui.MessageDialog.assert_not_called()

    def test_one_invalid_model_stops_batch_before_any_import(self):
        self.add_textures()
        other = self.root / "Other" / "FIN"
        other.mkdir(parents=True)
        (other / "Other.fbx").touch()
        self.dialog._initialize(object())
        ui.import_fbx.assert_not_called()
        self.assertIn("Other", self.message())

    def test_asset_browser_validation_explains_missing_texture_layout(self):
        tex = self.add_textures("TEX")
        dlg = browser.AssetBrowserDialog(str(self.root), "tanks")
        dlg._get_selected_tasks = lambda: iter(ui.collect_tasks(str(self.root)))
        dlg._write_report = Mock()
        dlg._validate_selected()
        self.assertIn("Original_textures", self.message())
        self.assertIn(str(tex), self.message())

    def test_asset_browser_shaders_warn_before_processing(self):
        self.add_textures("TEX")
        dlg = browser.AssetBrowserDialog(str(self.root), "tanks")
        dlg._get_selected_tasks = lambda: iter(ui.collect_tasks(str(self.root)))
        dlg._write_report = Mock()
        dlg._action_shaders()
        dlg._write_report.assert_not_called()
        host.EventAdd.assert_not_called()
        self.assertIn("Original_textures", self.message())

    def test_asset_browser_empty_list_displays_root_diagnosis(self):
        dlg = browser.AssetBrowserDialog(str(self.fin), "tanks")
        dlg._load_tasks()
        self.assertIn(str(self.root), dlg._root_problem)
        self.assertEqual(dlg._visible_tasks, [])
        dlg.SetString = Mock()
        dlg._update_tex_preview()
        dlg.SetString.assert_any_call(browser.ID_TEX_PREVIEW, dlg._root_problem)

    def test_asset_browser_refresh_does_not_keep_stale_tasks(self):
        dlg = browser.AssetBrowserDialog(str(self.root), "tanks")
        dlg._load_tasks()
        self.assertEqual(len(dlg._visible_tasks), 1)
        dlg._root_path = str(self.root / "missing")
        dlg._load_tasks()
        self.assertEqual(dlg._visible_tasks, [])
        self.assertIn(dlg._root_path, dlg._root_problem)

    def test_universal_root_keeps_existing_behavior(self):
        self.dialog._get_uni_root = lambda: str(self.fin)
        tasks = self.dialog._get_uni_tasks()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["name"], "VNII_100LT")
        host.gui.MessageDialog.assert_not_called()


if __name__ == "__main__":
    unittest.main()
