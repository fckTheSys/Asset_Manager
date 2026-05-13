# Tank Tool Box (RS / CentiLeo) — краткая документация

Версия в коде: `ttb/config.py` (`PLUGIN_VERSION`). Обзор репозитория: **[README.md](README.md)**.

## Назначение

Плагин для Cinema 4D автоматизирует работу с танковыми (и универсальными) ассетами в пайплайне: **импорт FBX**, **сборка материалов** (Redshift и/или CentiLeo — чекбоксы в диалоге) по текстурам и **назначение материалов по имени частей**. Поддерживается **relink** путей к текстурам («Fix»).

В версии 2.1.0 добавлены diagnostics/self check, отчёты операций, режим **Update existing materials only**, фильтр и валидация выбранных ассетов в Asset Browser.

### Портируемые сцены

Основной пайплайн (FBX / материалы / Apply / Fix) не оставляет в файле ссылки на папку плагина.

**TTB Camera Shake:** при создании рига в Python Tag записывается полный скрипт из `ttb/camera_shake_tag_embedded.py` — сцена воспроизводится на машине **без** установленного TankToolBox.

CentiLeo: см. `ttb/CL_SPACE_README.txt` (активный рендерер CentiLeo в Render Settings).


Важно: в текущей версии плагина **нет отдельной функции экспорта** (FBX/OBJ и т.п.). Экспорт выполняется стандартными средствами Cinema 4D.

---

## Два режима работы

| Режим | Корень | Структура | Применение материалов |
|-------|--------|-----------|------------------------|
| **Tanks** | Папка TANKS | В каждой подпапке: `FIN/` с FBX, `Original_textures/` (или в FIN) | Строго по частям: Hull, Turret, Track, Gun, Chassis |
| **Universal** | Любая папка | Рекурсивный обход; задача = папка с FBX, текстуры — в корне модели | По частям + fallback. Если стандартная часть не найдена, используются слоты из имени текстур (например `Model_Glass__Color` → слот `Glass`) |

---

## Основные понятия

### Части (Parts)

Определяются по ключевым словам в имени объекта/файла: `hull`, `turret`, `track`, `gun`, `chassis`.  
Материалы именуются: `{имя_модели}_{часть}` (например `T34_Hull`, `T34_Turret`).

В режиме Universal, если стандартная часть не найдена, плагин пытается выделить имя слота из текстуры по суффиксу карты:
- `Model_Glass__Color` → `Glass`
- `Model_Tracks__Roughness` → `Tracks`

### Типы карт (Map Types)

По имени файла текстуры определяется тип и строится граф Redshift:

| Код | Назначение в материале |
|-----|------------------------|
| AM | Base Color (Albedo) |
| AO | Ambient Occlusion → multiplier к Base |
| NM | Normal (Tangent Space) → Bump |
| MM | Metalness |
| RM / RG | Roughness |
| GM | Gloss → инвертируется в Roughness |
| EM | Emission |
| OP | Opacity (RAW, non-color) |
| HM | Height → Displacement |

Алиасы типов задаются в `ttb/texture_aliases.json` (например Gloss, Spec, ORM → GM).

### Задача (Task)

- **Tanks:** `tank`, `tank_dir`, `fin_dir`, `fbx`, `tex_dir`, `groups` (Part → MapType → путь к файлу).
- **Universal:** `name`, `fbx`, `tex_dir`, `groups`.

---

## Принципы и пайплайн

1. **Сканирование** — плагин обходит папки, ищет FBX и папки с текстурами, по именам файлов определяет Part и MapType.
2. **Импорт** — FBX мержится в сцену, новые объекты группируются под Null с именем модели, дочерние объекты переименовываются с префиксом `{модель}_`.
3. **Шейдеры** — в главном диалоге включите нужные движки (**Redshift** и/или **CentiLeo**). Для каждой пары (модель, часть) создаётся/обновляется материал выбранного типа: для Redshift граф пересоздаётся (`CreateDefaultGraph`), затем подключаются Texture Sampler (и при необходимости Bump, Invert, Displacement) к Standard Material и Output; для CentiLeo — отдельная сборка графа (`cl_graph.py`).
   - Color-карты: `AM`, `EM` подключаются как `sRGB`.
   - Data-карты: `AO`, `NM`, `MM`, `RM/RG`, `GM`, `OP`, `HM` подключаются как `RAW`.
4. **Применение** — по имени объекта выводится часть (`infer_part_from_name`), ищется материал `{модель}_{часть}` и вешается Texture Tag с UVW.
5. **Fix** — строится индекс текстур (basename → полный путь) по `tex_dir` всех задач; в материалах исправляются пути в Redshift TextureSampler и в старых Bitmap Shader (Xbitmap).

---

## Модули

| Модуль | Назначение |
|--------|------------|
| `config.py` | ID плагина, Redshift/CentiLeo константы, MAP_TYPES, PART_KEYS, пути к алиасам, расширения текстур |
| `io_scan.py` | `normpath`, `is_dir`; `collect_tasks` (Tanks), `collect_universal_tasks`; `scan_textures`, `build_texture_index`; `detect_part`, `detect_map_type` (в т.ч. через texture_aliases.json); исключение proxy/crash (если не crush) |
| `rs_graph.py` | Redshift: `create_or_update_rs_material`, `build_material_graph` (StandardMaterial + TextureSampler, Bump, Invert, Displacement), ColorSpace (sRGB/RAW) |
| `cl_graph.py` | CentiLeo: сборка/обновление материалов и узлов по тем же группам текстур |
| `scene_ops.py` | `import_fbx`, `find_tank_null`, `infer_part_from_name`, `ensure_texture_tag`, `apply_materials_to_tank`, `apply_materials_generic`, `collect_mats_by_part` |
| `relink.py` | `fix_node_texturesampler_paths`, `fix_legacy_bitmap_shaders` по индексу basename→path |
| `ui_dialog.py` | Главный диалог: пути Tanks/Universal, чекбоксы RS/CL, кнопки Init/Update Shaders/Apply/Fix и Universal Import/Shaders/Apply, открытие Asset Browser |
| `asset_browser.py` | Диалог списка моделей (по корню Tanks или Universal), выбор задач, действия Import / Build shaders / Apply для выбранных |
| `diagnostics.py` | Self check node spaces, plugin ID и сводка задач |
| `camera_shake.py`, `camera_shake_dialog.py`, `camera_shake_tag_embedded.py` | Инструмент TTB Camera Shake: диалог, сборка рига, встраиваемый скрипт для портируемых сцен |
| `duplicate_finder.py` | Поиск групп с несколькими реальными (не instance) объектами под выбранным корнем |
| `instance_renamer.py` | Переименование Instance-объектов по шаблону |

---

## Важные детали

- **Proxy-текстуры** — файлы с «proxy» в имени пропускаются при сканировании.
- **Crash-текстуры** — учитываются только для танков с «crush» в имени.
- **Имена материалов** — уникализация при создании: при повторе добавляется суффикс `_2`, `_3` и т.д.
- **PLUGIN_ID** — в `config.py` задаётся константа; для распространения нужен зарегистрированный ID от Maxon (иначе в консоли предупреждение).

---

## Быстрый старт (Tanks)

1. Указать папку TANKS (в каждой подпапке — папка FIN с FBX и при необходимости Original_textures).
2. **Инициализировать** — импорт FBX + построение шейдеров по текстурам (в диалоге отметьте **Redshift** и/или **CentiLeo** под ваш активный пайплайн).
3. **Применить к моделькам** — назначение материалов по имени частей.
4. При сломанных путях — **Fix '?'** (relink по basename в найденных текстурах).

Для Universal: указать Universal root → Import / Build shaders / Apply materials (Universal).  
Asset Browser позволяет выбрать подмножество моделей и выполнить для них те же действия.
