# -*- coding: utf-8 -*-
"""Единый вывод в консоль C4D (Script Log) для TankToolBox."""
import c4d

_PREFIX = "[TankToolBox]"


def info(msg: str) -> None:
    try:
        c4d.GePrint("%s %s" % (_PREFIX, msg))
    except Exception:
        print(_PREFIX, msg)


def warn(msg: str) -> None:
    try:
        c4d.GePrint("%s WARNING: %s" % (_PREFIX, msg))
    except Exception:
        print(_PREFIX, "WARNING:", msg)


def error(msg: str) -> None:
    try:
        c4d.GePrint("%s ERROR: %s" % (_PREFIX, msg))
    except Exception:
        print(_PREFIX, "ERROR:", msg)
