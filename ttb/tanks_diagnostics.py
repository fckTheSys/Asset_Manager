# -*- coding: utf-8 -*-
"""Read-only explanations of the existing Tanks folder requirements."""
import os


_LAYOUT = (
    "Режим Tanks ожидает структуру:\n"
    "TANKS / Имя_модели / FIN / модель.fbx\n"
    "Выбирать нужно корень TANKS, содержащий папки моделей."
)


def tanks_root_problem(root, tasks):
    """Return an actionable message when the existing scanner found no tasks."""
    if not root or not os.path.isdir(root):
        return "Папка TANKS не выбрана или не существует:\n%s\n\n%s" % (
            root or "(путь не указан)", _LAYOUT,
        )
    if tasks:
        return None

    root = os.path.normpath(root)
    lines = ["В выбранной папке не найдено ни одной модели Tanks:", root, "", _LAYOUT]
    if os.path.basename(root).lower() == "fin":
        lines.extend([
            "", "Выбрана сама папка FIN, а не корень TANKS.",
            "Для этой структуры выберите папку на два уровня выше:",
            os.path.dirname(os.path.dirname(root)),
        ])
    elif os.path.isdir(os.path.join(root, "FIN")):
        lines.extend([
            "", "Выбрана папка одной модели, содержащая FIN.",
            "Выберите её родительскую папку:", os.path.dirname(root),
        ])
    else:
        try:
            names = sorted(os.listdir(root))
            if any(name.lower().endswith(".fbx") and os.path.isfile(os.path.join(root, name)) for name in names):
                lines.extend(["", "FBX лежит прямо в выбранной папке. Поместите его в Имя_модели / FIN."])
            empty_fin_dirs = [
                os.path.join(root, name, "FIN") for name in names
                if os.path.isdir(os.path.join(root, name, "FIN"))
            ]
            if empty_fin_dirs:
                lines.extend(["", "Папки FIN найдены, но в них нет FBX-файлов (.fbx):"])
                lines.extend(empty_fin_dirs[:10])
                if len(empty_fin_dirs) > 10:
                    lines.append("… и ещё %s" % (len(empty_fin_dirs) - 10))
        except OSError as exc:
            lines.extend(["", "Не удалось прочитать содержимое папки: %s" % exc])
    return "\n".join(lines)


def tank_texture_problem(task):
    """Explain missing/unrecognized textures without accepting new layouts."""
    if task.get("groups"):
        return None
    name = task.get("tank", "?")
    tex_dir = task.get("tex_dir")
    if tex_dir:
        return (
            "%s: папка текстур найдена, но в ней нет распознанных карт:\n%s\n"
            "Проверьте файлы и обозначения карт: AM, AO, NM, MM, GM, RM и т. д."
        ) % (name, tex_dir)

    tank_dir = task["tank_dir"]
    fin_dir = task["fin_dir"]
    lines = [
        "%s: не найдена папка текстур Original_textures." % name,
        "Ожидается один из путей:",
        os.path.join(fin_dir, "Original_textures"),
        os.path.join(tank_dir, "Original_textures"),
    ]
    for parent in (fin_dir, tank_dir):
        alternative = os.path.join(parent, "TEX")
        if os.path.isdir(alternative):
            lines.append("Обнаружена папка TEX: %s" % alternative)
    lines.append("Поместите текстуры в Original_textures: режим Tanks ищет их только там.")
    return "\n".join(lines)


def tanks_textures_problem(tasks):
    problems = [problem for task in tasks if (problem := tank_texture_problem(task))]
    if not problems:
        return None
    return "Операция не запущена: проверьте структуру папок и текстуры.\n\n" + "\n\n".join(problems)
