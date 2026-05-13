# Changelog — Asset Manager (Tank Tool Box)

## 2.1.0 (2026-05-08)

- Self check для node spaces и plugin ID.
- Режим **Update existing materials only**.
- Asset Browser: фильтр, счётчик выбранного, Validate selected, экспорт отчётов.
- Краткий отчёт операций в `ttb_report.txt`.

## 2.0.0 (2026-05-08)

- Модуль `ttb/log.py` — единый вывод в Script Log с префиксом `[TankToolBox]`.
- Логирование в `cl_graph`, `asset_browser`, `relink`, `io_scan` через `ttb.log` вместо `print`.
