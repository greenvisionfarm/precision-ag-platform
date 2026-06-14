# Field Mapper Roadmap 🚀

## 🎯 Текущая цель: Orthomosaic (Полная реализация)
- [x] **orthomosaic_service.py** — cv2.Stitcher + EXIF GPS + геореференсирование
- [x] **Huey task** — фоновая обработка склейки
- [x] **Handler endpoints** — загрузка + статус (processing_mode routing)
- [x] **Frontend toggle** — fast/orthomosaic mode + прогресс
- [x] **Tests** — unit + integration (22 tests)
- [x] **Документация** — исправлены stale docs

## 📋 Следующие цели
- [ ] **Chunked reading** для очень больших GeoTIFF (>10GB)
- [ ] **Кэширование результатов кластеризации** (ускорение повторного анализа)
- [ ] **Progressive loading** геометрий на frontend (для полей с 1000+ полигонами)

## 💡 Идеи на будущее (Backlog)
- [ ] Отправка тяжелой обработки в Cloud (для слабых ноутбуков)
- [ ] Поддержка новых форматов экспорта (Shapefile, GeoJSON)
- [ ] Интеграция с метеостанциями

## ✅ Завершено (Архив достижений)
- [x] Рефакторинг на ES6 модули и Tornado Handlers (Март 2026)
- [x] Оптимизация RAM (Windowed reading, WAL mode)
- [x] Покрытие критических путей тестами (NDVI, VRA, Zoning)
