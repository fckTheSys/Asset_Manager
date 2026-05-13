Tank Tool Box (Redshift / CentiLeo) — Cinema 4D
================================================

Структура плагина для установки:

TankToolBox/
  TankToolBox.pyp
  ttb/
    __init__.py
    config.py
    io_scan.py
    rs_graph.py
    cl_graph.py
    relink.py
    scene_ops.py
    ui_dialog.py
    asset_browser.py
    camera_shake.py
    camera_shake_dialog.py
    camera_shake_tag_embedded.py
    duplicate_finder.py
    instance_renamer.py
    texture_aliases.json
    ...

Файл TankToolBox.pyp должен лежать в корне папки TankToolBox; рядом — каталог ttb.


Установка в Cinema 4D
---------------------

1. Скопируйте всю папку TankToolBox в каталог plugins Cinema 4D.

2. Перезапустите Cinema 4D.

3. В меню плагинов появятся команды:
   - Tank Tool Box (RS/CL) — основной диалог: FBX, шейдеры Redshift и/или CentiLeo, Apply, Fix paths
   - TTB Camera Shake — процедурная тряска камеры (портируемый Python Tag из camera_shake_tag_embedded.py)
   - TTB Find Real Duplicates
   - TTB Rename Instances


Документация
------------

Подробнее: DOCS.md в этой папке, CentiLeo: ttb/CL_SPACE_README.txt.


PLUGIN_ID
---------

В ttb/config.py задайте свой Plugin ID с PluginCafe для распространения.
