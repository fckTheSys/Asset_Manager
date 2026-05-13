# Установка — Asset Manager (Tank Tool Box)

## 1. Куда копировать

Скопируйте каталог репозитория целиком в **plugins** Cinema 4D:

- `...\MAXON\Cinema 4D 2026_xxxxxxxx\plugins\Asset_Manager\`

или любое имя папки, например `TankToolBox`.

**Содержимое папки плагина:**

- `TankToolBox.pyp` — точка входа
- `ttb\` — пакет Python (`config.py`, `ui_dialog.py`, …)
- `ttb\texture_aliases.json` — алиасы типов карт (не удалять)

## 2. Перезапуск C4D

Полностью закройте и откройте Cinema 4D.

## 3. Проверка

В **Script Log** ожидается строка вида:

```text
[TankToolBox] Tank Tool Box (RS/CL) v2.1.0
```

Предупреждение о **PLUGIN_ID** (placeholder `10698765`) означает, что для публичного релиза нужно заменить ID в `ttb/config.py`.

## 4. Команды плагина

После загрузки регистрируются несколько команд (ищите по префиксу **TTB** или **Tank**):

| Команда | Назначение |
|---------|------------|
| Tank Tool Box (RS/CL) | Главный диалог пайплайна |
| TTB Camera Shake | Риг тряски камеры |
| TTB Find Real Duplicates | Поиск дублей |
| TTB Rename Instances | Переименование Instance |

## 5. Redshift / CentiLeo

Убедитесь, что нужный рендерер установлен и в **Render Settings** может быть выбран. Для CentiLeo см. `ttb/CL_SPACE_README.txt`.

## 6. Обновление

Удалите старую папку плагина, скопируйте новую версию целиком (избегаете мусора в `__pycache__`).
