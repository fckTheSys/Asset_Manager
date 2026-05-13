# -*- coding: utf-8 -*-
import os, sys
import c4d
from c4d import plugins

this_dir = os.path.dirname(__file__)
if this_dir not in sys.path:
    sys.path.insert(0, this_dir)

from ttb.config import PLUGIN_ID, PLUGIN_NAME, PLUGIN_VERSION
from ttb.log import info as ttb_log_info
from ttb.ui_dialog import TankToolCommand
from ttb.camera_shake_dialog import CameraShakeCommand
from ttb.duplicate_finder import find_real_duplicates
from ttb.instance_renamer import rename_instances_in_doc


class DuplicateFinderCommand(c4d.plugins.CommandData):
    def Execute(self, doc):
        doc = c4d.documents.GetActiveDocument()
        if not doc:
            c4d.gui.MessageDialog("Нет активного документа")
            return True
        root = doc.GetActiveObject()
        if not root:
            c4d.gui.MessageDialog("Выберите родительский объект")
            return True
        count, report_lines = find_real_duplicates(root)
        if count == 0:
            c4d.gui.MessageDialog("Реальных дублей не найдено")
        else:
            for line in report_lines:
                print(line)
            c4d.gui.MessageDialog("Найдено групп с реальными дублями: {}".format(count))
        return True

    def RestoreLayout(self, sec_ref):
        return True


class InstanceRenameCommand(c4d.plugins.CommandData):
    def Execute(self, doc):
        doc = c4d.documents.GetActiveDocument()
        if not doc:
            c4d.gui.MessageDialog("Нет активного документа")
            return True
        rename_instances_in_doc(doc)
        c4d.gui.MessageDialog("Instance-объекты переименованы.")
        return True

    def RestoreLayout(self, sec_ref):
        return True


def PluginStart():
    try:
        ttb_log_info("%s v%s" % (PLUGIN_NAME, PLUGIN_VERSION))
    except Exception:
        print("[TankToolBox]", PLUGIN_NAME, PLUGIN_VERSION)

    ok = plugins.RegisterCommandPlugin(
        id=PLUGIN_ID,
        str=PLUGIN_NAME,
        info=0,
        icon=None,
        help="Tank Tool Box: Import FBX, build Redshift/CentiLeo shaders, relink textures, apply materials",
        dat=TankToolCommand(),
    )

    # Register separate command for Camera Shake tool (uses PLUGIN_ID + 2 in dialog/layout only).
    ok2 = plugins.RegisterCommandPlugin(
        id=PLUGIN_ID + 10,
        str="TTB Camera Shake",
        info=0,
        icon=None,
        help="TTB Camera Shake: build shake rig; portable Python Tag embedded in scene",
        dat=CameraShakeCommand(),
    )

    ok3 = plugins.RegisterCommandPlugin(
        id=PLUGIN_ID + 11,
        str="TTB Find Real Duplicates",
        info=0,
        icon=None,
        help="Find groups with multiple real (non-instance) objects under selected root",
        dat=DuplicateFinderCommand(),
    )

    ok4 = plugins.RegisterCommandPlugin(
        id=PLUGIN_ID + 12,
        str="TTB Rename Instances",
        info=0,
        icon=None,
        help="Rename Instance objects to * Inst / *Inst",
        dat=InstanceRenameCommand(),
    )
    return ok and ok2 and ok3 and ok4


if __name__ == "__main__":
    PluginStart()