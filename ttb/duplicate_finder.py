# -*- coding: utf-8 -*-
import re
from typing import List, Tuple

import c4d


INSTANCE_TYPE = c4d.Oinstance


def get_base_name(name: str) -> str:
    return re.sub(r"\.\d+$", "", name or "")


def iter_scene_hierarchy(root: c4d.BaseObject):
    child = root.GetDown()
    while child:
        yield child
        for sub in iter_scene_hierarchy(child):
            yield sub
        child = child.GetNext()


def is_instance(obj: c4d.BaseObject) -> bool:
    return obj is not None and obj.GetType() == INSTANCE_TYPE


def find_real_duplicates(root: c4d.BaseObject) -> Tuple[int, List[str]]:
    """
    Find groups with multiple real (non-instance) objects under root.
    Root and all descendants are considered.
    Returns (count of such groups, list of report lines for console).
    """
    if root is None:
        return 0, []

    objs = [root]
    objs.extend(list(iter_scene_hierarchy(root)))

    groups = {}
    for obj in objs:
        key = (get_base_name(obj.GetName()), obj.GetType())
        groups.setdefault(key, []).append(obj)

    report_lines = []
    found = 0

    for key, items in groups.items():
        non_instances = [o for o in items if not is_instance(o)]
        instances = [o for o in items if is_instance(o)]

        if len(non_instances) > 1:
            found += 1
            report_lines.append("GROUP: {} | type: {}".format(key[0], key[1]))
            report_lines.append("  real objects: {}".format(len(non_instances)))
            report_lines.append("  instances   : {}".format(len(instances)))
            for o in non_instances:
                report_lines.append("    OBJ : {}".format(o.GetName()))

    if found == 0:
        return 0, []
    report_lines.insert(0, "=== ГРУППЫ С РЕАЛЬНЫМИ ДУБЛЯМИ ===")
    return found, report_lines
