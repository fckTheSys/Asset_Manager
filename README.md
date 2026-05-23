# Asset Manager — Tank Tool Box (RS / CL)

**Cinema 4D** · Python command plugin · **v2.1.0** (см. `ttb/config.py`)

Репозиторий **Asset_Manager** — исходники плагина **Tank Tool Box**: пайплайн **FBX + текстуры → материалы Redshift и/или CentiLeo → назначение на объекты**, relink путей, вспомогательные утилиты.

Краткое описание для GitHub *About*:  
*Cinema 4D asset pipeline: FBX import, Redshift/CentiLeo materials from textures, apply by part name, relink, Camera Shake, duplicate finder.*

---

## Ключевые возможности

### Пайплайн материалов

- Режим **Tanks** — корень папки TANKS: в каждой модели `FIN/` + текстуры; части Hull, Turret, Track, Gun, Chassis; именование материалов `{модель}_{часть}`.
- Режим **Universal** — произвольный корень, рекурсивный поиск FBX и текстур; мягкое сопоставление слотов по именам файлов.
- **Redshift** и **CentiLeo** — выбор движков чекбоксами в диалоге; сборка нодовых материалов (`rs_graph`, `cl_graph`).
- **Импорт FBX**, **обновление шейдеров**, **применение материалов** по имени части объекта.
- **Fix '?' (relink)** — восстановление путей в RS TextureSampler и legacy Bitmap по индексу текстур.
- **Asset Browser** — список задач, выборочный Import / Shaders / Apply; фильтр, валидация выбора, отчёты.
- **Update existing materials only** — режим обновления без лишнего создания.
- **Self check** — node spaces, plugin ID; отчёты операций в **Script Log** и **`ttb_report.txt`**.

### Дополнительные команды

- **TTB Camera Shake** — отдельная команда: риг тряски, **встраиваемый Python Tag** (`camera_shake_tag_embedded.py`) для сцен без установленного плагина.
- **TTB Find Real Duplicates** — поиск групп с несколькими не-instance объектами под выбранным корнем.
- **TTB Rename Instances** — переименование Instance-объектов.

Подробнее: **[DOCS.md](DOCS.md)**, CentiLeo: **`ttb/CL_SPACE_README.txt`**, шпаргалка C4D: **[DOCS/C4D_2026_Plugin_Cheat_Sheet.md](DOCS/C4D_2026_Plugin_Cheat_Sheet.md)**.

---

## Требования

- **Cinema 4D** с **Python**.
- **Redshift** и/или **CentiLeo** — в зависимости от того, какие материалы вы собираете (нужны установленные рендереры и node spaces).
- Модуль **maxon** (стандарт для C4D) для нодовых материалов.

---

## Установка (кратко)

1. Склонируй репозиторий или скачай ZIP.
2. Скопируй **всю папку** `Asset_Manager` (или переименуй, например в `TankToolBox`) в каталог **plugins** C4D.
3. Внутри папки должны быть: `TankToolBox.pyp` и каталог `ttb\` (включая `texture_aliases.json`).
4. Перезапусти C4D.
5. В Script Log: `[TankToolBox] Tank Tool Box (RS/CL) v2.1.0`.

Детали: **[INSTALL.md](INSTALL.md)**.

---

## Использование (кратко)

1. Запусти команду **Tank Tool Box (RS/CL)** — главный диалог.
2. Укажи путь к **Tanks** или **Universal root**, при необходимости включи **Redshift** / **CentiLeo**.
3. **Инициализировать** — импорт FBX + сборка материалов (Tanks).
4. **Применить к моделькам** — текстурные теги по имени части.
5. **Fix** — relink путей к текстурам.
6. Утилиты Camera Shake / Duplicates / Instances — отдельные команды в том же плагине.

---

## Важно

- В `ttb/config.py` при **placeholder PLUGIN_ID** при старте выводится предупреждение в консоль — для распространения получите уникальный ID на **PluginCafe**.
- Экспорт сцен (FBX/OBJ) плагином не выполняется — только стандартными средствами C4D.

---

## Публикация на GitHub

См. **[GITHUB.md](GITHUB.md)**.

---

