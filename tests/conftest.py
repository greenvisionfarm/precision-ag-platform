# tests/conftest.py

import pytest

# Указываем pytest-asyncio использовать режим "auto" для автоматического обнаружения асинхронных тестов
# Это эквивалентно pytest_plugins = "pytest_asyncio" в каждом файле, но более централизованно.
# Также можно использовать "strict" или "legacy" в зависимости от потребностей.
def pytest_configure(config):
    config.option.asyncio_mode = "auto"

# Если вы хотите явно загрузить плагин, хотя asyncio_mode обычно достаточно
# pytest_plugins = ["pytest_asyncio"]
