# -*- coding: utf-8 -*-
import c4d


def _process_object(op):
    while op:
        if op.GetType() == c4d.Oinstance:
            name = op.GetName() or ""
            if "Instance" in name:
                name = name.replace("Instance", "Inst")
            else:
                if not name.endswith("Inst"):
                    name = name + " Inst"
            op.SetName(name)
        _process_object(op.GetDown())
        op = op.GetNext()


def rename_instances_in_doc(doc):
    """Rename all Instance objects in document: 'Instance' -> 'Inst', or append ' Inst'."""
    if doc is None:
        return
    first = doc.GetFirstObject()
    if first is None:
        return
    doc.StartUndo()
    try:
        _process_object(first)
    finally:
        doc.EndUndo()
        c4d.EventAdd()
