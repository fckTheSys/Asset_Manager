# Changelog — Asset Manager (Tank Tool Box)

## Unreleased

- Tanks: сообщения с ожидаемой структурой папок, выбранным путём и подсказкой корня при выборе модели или FIN.
- Проверка текстур перед инициализацией/сборкой шейдеров: пути Original_textures, подсказка при обнаружении TEX, отдельное сообщение для нераспознанных карт.
- Asset Browser: причины отсутствия моделей/текстур в списке, предпросмотре и проверке выбранных моделей.

## 2.1.0 (2026-05-08)

- Self check для node spaces и plugin ID.
- Режим **Update existing materials only**.
- Asset Browser: фильтр, счётчик выбранного, Validate selected, экспорт отчётов.
- Краткий отчёт операций в `ttb_report.txt`.

## 2.0.0 (2026-05-08)

- Модуль `ttb/log.py` — единый вывод в Script Log с префиксом `[TankToolBox]`.
- Логирование в `cl_graph`, `asset_browser`, `relink`, `io_scan` через `ttb.log` вместо `print`.
