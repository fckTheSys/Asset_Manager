# -*- coding: utf-8 -*-
import c4d

from .camera_shake import (
    find_cameras,
    find_selected_cameras,
    build_shake_rig_for_cameras,
    get_or_create_shake_rig,
    setup_shake_userdata,
)
from .config import PLUGIN_ID


ID_CAM_LIST = 4000
ID_REFRESH = 4001
ID_CREATE_RIG = 4002
ID_ADD_SHAKE = 4003
ID_CLOSE = 4004


class CameraShakeDialog(c4d.gui.GeDialog):
    def __init__(self):
        super().__init__()
        self._cams = []
        self._using_selected = False

    def CreateLayout(self):
        self.SetTitle("TTB Camera Shake")
        self.GroupBorderSpace(10, 10, 10, 10)

        self.AddStaticText(0, c4d.BFH_LEFT, name="Selected cameras first, otherwise all scene cameras:")
        self.GroupBegin(0, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, cols=1, rows=2)
        self.AddMultiLineEditText(ID_CAM_LIST, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, inith=140, style=c4d.DR_MULTILINE_READONLY)
        self.GroupEnd()

        self.AddSeparatorH(c4d.BFH_SCALEFIT)

        self.GroupBegin(0, c4d.BFH_SCALEFIT, cols=4, rows=1)
        self.AddButton(ID_REFRESH, c4d.BFH_LEFT, name="Refresh list")
        self.AddButton(ID_CREATE_RIG, c4d.BFH_LEFT, name="Create/Select Rig")
        self.AddButton(ID_ADD_SHAKE, c4d.BFH_LEFT, name="Add Shake For Selected")
        self.AddButton(ID_CLOSE, c4d.BFH_RIGHT, name="Close")
        self.GroupEnd()

        return True

    def InitValues(self):
        self._refresh_cameras()
        return True

    def _refresh_cameras(self):
        doc = c4d.documents.GetActiveDocument()
        if not doc:
            self._cams = []
            self._using_selected = False
            self.SetString(ID_CAM_LIST, "No active document.")
            return

        selected_cams = find_selected_cameras(doc)
        if selected_cams:
            self._cams = selected_cams
            self._using_selected = True
        else:
            self._cams = find_cameras(doc)
            self._using_selected = False

        if not self._cams:
            self.SetString(
                ID_CAM_LIST,
                "No camera objects found.\nSelect one or more cameras and press Refresh, or make sure real camera objects exist in the scene.",
            )
            return
        lines = []
        mode = "Selected cameras" if self._using_selected else "Scene cameras"
        lines.append(f"{mode}: {len(self._cams)}")
        lines.append("")
        for idx, cam in enumerate(self._cams):
            lines.append(f"{idx}: {cam.GetName()}")
        self.SetString(ID_CAM_LIST, "\n".join(lines))

    def _parse_selected_indices(self):
        text = self.GetString(ID_CAM_LIST) or ""
        # Simple heuristic: treat numbers at line start before ':' as selected indices if user edits text.
        indices = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                before_colon = line.split(":", 1)[0]
                idx = int(before_colon.strip())
                if 0 <= idx < len(self._cams):
                    indices.append(idx)
            except Exception:
                continue
        return indices

    def _selected_cameras(self):
        idxs = self._parse_selected_indices()
        if not idxs:
            # If user didn't edit text, default to all cameras
            return list(self._cams)
        return [self._cams[i] for i in idxs if 0 <= i < len(self._cams)]

    def Command(self, wid, msg):
        if wid == ID_REFRESH:
            self._refresh_cameras()
            return True
        if wid == ID_CREATE_RIG:
            doc = c4d.documents.GetActiveDocument()
            if not doc:
                c4d.gui.MessageDialog("No active document.")
                return True
            rig = get_or_create_shake_rig(doc)
            setup_shake_userdata(rig)
            c4d.EventAdd()
            c4d.gui.MessageDialog("Camera Shake Rig created/selected.\nAdjust parameters in Attribute Manager.")
            return True
        if wid == ID_ADD_SHAKE:
            doc = c4d.documents.GetActiveDocument()
            if not doc:
                c4d.gui.MessageDialog("No active document.")
                return True
            cams = self._selected_cameras()
            if not cams:
                c4d.gui.MessageDialog("No cameras found. Select one or more cameras and press Refresh.")
                return True
            rig = build_shake_rig_for_cameras(doc, cams)
            c4d.gui.MessageDialog(f"Shake rig set up for {len(cams)} camera(s).\nUse rig User Data to control shake.")
            return True
        if wid == ID_CLOSE:
            self.Close()
            return True
        return True


class CameraShakeCommand(c4d.plugins.CommandData):
    dlg = None

    def Execute(self, doc):
        if self.dlg is None:
            self.dlg = CameraShakeDialog()
        return self.dlg.Open(c4d.DLG_TYPE_ASYNC, PLUGIN_ID + 2, defaultw=520, defaulth=260)

    def RestoreLayout(self, sec_ref):
        if self.dlg is None:
            self.dlg = CameraShakeDialog()
        return self.dlg.Restore(PLUGIN_ID + 2, sec_ref)

