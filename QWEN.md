## Qwen Added Memories
- Сервер для деплоя: 192.168.31.196. На этот сервер деплоится проект field_mapper и там запускаются тесты.
- У проекта field_mapper есть GitHub Pages. URL: https://github.com/greenvisionfarm/precision-ag-platform (репозиторий precision-ag-platform). Нужно взаимодействовать с GitHub Pages при деплое и CI.
- В проекте field_mapper есть локальный venv. Все Python команды (pytest, pip install и т.д.) нужно запускать через него: `source venv/bin/activate && ...` или `venv/bin/python ...`. Ничего не устанавливать в системный Python.
