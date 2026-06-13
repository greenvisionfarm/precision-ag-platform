# Makefile для Field Mapper E2E тестов

.PHONY: help test test-e2e test-e2e-headed test-e2e-debug test-e2e-report clean-e2e install-e2e

# Цвета для вывода
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

help: ## Показать эту справку
	@echo "$(BLUE)=== Field Mapper E2E Tests ===$(NC)"
	@echo ""
	@echo "Доступные команды:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

install: ## Установить зависимости
	@echo "$(YELLOW)Установка зависимостей...$(NC)"
	npm install
	npx playwright install chromium
	@echo "$(GREEN)✅ Готово!$(NC)"

install-all: ## Установить все браузеры
	@echo "$(YELLOW)Установка всех браузеров...$(NC)"
	npx playwright install
	@echo "$(GREEN)✅ Готово!$(NC)"

test: ## Запустить все тесты (unit + E2E)
	@echo "$(YELLOW)Запуск всех тестов...$(NC)"
	npm test && npm run test:e2e

test-e2e: ## Запустить E2E тесты (headless)
	@echo "$(YELLOW)Запуск E2E тестов (headless)...$(NC)"
	npm run test:e2e
	@echo "$(GREEN)✅ Тесты завершены!$(NC)"

test-e2e-headed: ## Запустить E2E тесты с открытым браузером (headed)
	@echo "$(YELLOW)Запуск E2E тестов (с браузером)...$(NC)"
	npm run test:e2e:headed

test-e2e-debug: ## Запустить E2E тесты в режиме отладки
	@echo "$(YELLOW)Запуск E2E тестов (debug)...$(NC)"
	npm run test:e2e:debug

test-e2e-report: ## Показать HTML отчёт по тестам
	@echo "$(YELLOW)Открытие HTML отчёта...$(NC)"
	npm run test:e2e:report

test-e2e-mobile: ## Запустить только мобильные тесты
	@echo "$(YELLOW)Запуск мобильных E2E тестов...$(NC)"
	npx playwright test --project="Mobile Chrome"

test-e2e-auth: ## Запустить только тесты авторизации
	@echo "$(YELLOW)Запуск тестов авторизации...$(NC)"
	npx playwright test e2e/tests/auth.spec.ts

test-e2e-fields: ## Запустить только тесты полей
	@echo "$(YELLOW)Запуск тестов полей...$(NC)"
	npx playwright test e2e/tests/fields.spec.ts

test-e2e-owners: ## Запустить только тесты владельцев
	@echo "$(YELLOW)Запуск тестов владельцев...$(NC)"
	npx playwright test e2e/tests/owners.spec.ts

test-e2e-upload: ## Запустить только тесты загрузки
	@echo "$(YELLOW)Запуск тестов загрузки...$(NC)"
	npx playwright test e2e/tests/upload.spec.ts

test-e2e-ui: ## Запустить только UI тесты
	@echo "$(YELLOW)Запуск UI тестов...$(NC)"
	npx playwright test e2e/tests/ui.spec.ts

clean-e2e: ## Очистить результаты E2E тестов
	@echo "$(YELLOW)Очистка результатов тестов...$(NC)"
	rm -rf e2e-results/
	rm -rf e2e/results/*.png
	rm -rf test-results/
	@echo "$(GREEN)✅ Очистка завершена!$(NC)"

clean-all: clean-e2e ## Очистить всё (кэш, результаты, node_modules)
	@echo "$(YELLOW)Полная очистка...$(NC)"
	rm -rf node_modules/
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	rm -rf venv/
	@echo "$(GREEN)✅ Очистка завершена!$(NC)"

start-server: ## Запустить сервер для тестов
	@echo "$(YELLOW)Запуск сервера...$(NC)"
	FIELD_MAPPER_ENV=test python3 app.py

docker-test: ## Запустить E2E тесты в Docker
	@echo "$(YELLOW)Запуск E2E тестов в Docker...$(NC)"
	docker-compose run --rm e2e-tests

ci: ## Запустить тесты в CI режиме
	@echo "$(YELLOW)CI режим...$(NC)"
	CI=true npm run test:e2e

# Генерация тестовых данных
seed-test-data: ## Создать тестовые данные
	@echo "$(YELLOW)Создание тестовых данных...$(NC)"
	python seed_db.py
	@echo "$(GREEN)✅ Готово!$(NC)"

# Деплой на домашний сервер
# Конфигурация загружается из .deploy.env (не коммитится в git!)
-include .deploy.env

DEPLOY_SERVER ?= vbuianov@192.168.31.196
DEPLOY_DIR ?= ~/field_mapper
DEPLOY_COMPOSE ?= docker-compose.server.yml
APP_CONTAINER ?= app
HEALTH_URL ?= http://$(shell echo $(DEPLOY_SERVER) | cut -d@ -f2):8080
HEALTH_RETRIES ?= 10
HEALTH_INTERVAL ?= 5

define remote
	ssh $(DEPLOY_SERVER) "cd $(DEPLOY_DIR) && $(1)"
endef

define container_exec
	ssh $(DEPLOY_SERVER) "cd $(DEPLOY_DIR) && docker compose -f $(DEPLOY_COMPOSE) exec -T $(APP_CONTAINER) $(1)"
endef

deploy: ## Задеплоить на домашний сервер (pre-check → build → migrate → health)
	@echo "$(YELLOW)═══ Деплой на $(DEPLOY_SERVER) ═══$(NC)"
	@echo "$(BLUE)1/7 Pre-deploy checks...$(NC)"
	@PYTHONPYCACHEPREFIX=/tmp/pycache ./venv/bin/python -m pytest tests/test_raster_upload.py tests/test_isoxml_export.py tests/test_auth.py -q 2>&1 | tail -3
	@node -c static/js/modules/api.js && node -c static/js/modules/field-detail.js && echo "$(GREEN)JS OK$(NC)"
	@echo "$(BLUE)2/7 Push в GitHub...$(NC)"
	@git push upstream master 2>/dev/null || echo "$(YELLOW)⚠️  Push пропущен$(NC)"
	@echo "$(BLUE)3/7 Backup БД + Git pull...$(NC)"
	$(call remote,docker compose -f $(DEPLOY_COMPOSE) exec -T $(APP_CONTAINER) cp /app/data/fields.db /app/data/fields.db.bak 2>/dev/null || true)
	$(call remote,git pull --rebase)
	@echo "$(BLUE)4/7 Fix permissions...$(NC)"
	$(call remote,mkdir -p data uploads && chmod 777 data uploads 2>/dev/null || true)
	@echo "$(BLUE)5/7 Docker build + up...$(NC)"
	$(call remote,docker compose -f $(DEPLOY_COMPOSE) up -d --build)
	@echo "$(BLUE)6/7 Миграция БД...$(NC)"
	$(call container_exec,/opt/venv/bin/python src/db_migrate.py) || echo "$(YELLOW)⚠️  Миграция не требуется$(NC)"
	@echo "$(BLUE)7/7 Health check ($(HEALTH_RETRIES) попыток)...$(NC)"
	@i=0; while [ $$i -lt $(HEALTH_RETRIES) ]; do \
		i=$$((i+1)); \
		sleep $(HEALTH_INTERVAL); \
		if curl -sf $(HEALTH_URL)/ > /dev/null 2>&1; then \
			echo "$(GREEN)✅ Сервер отвечает (попытка $$i/$(HEALTH_RETRIES))$(NC)"; \
			break; \
		fi; \
		echo "$(YELLOW) ⏳ Попытка $$i/$(HEALTH_RETRIES)...$(NC)"; \
	done; \
	curl -sf $(HEALTH_URL)/ > /dev/null 2>&1 || echo "$(RED)❌ Сервер не отвечает — проверь логи$(NC)"
	$(call remote,docker image prune -f 2>/dev/null || true)
	@echo "$(GREEN)═══ Деплой завершён! $(HEALTH_URL) ═══$(NC)"

deploy-quick: ## Быстрый деплой без build (только pull + restart)
	@echo "$(YELLOW)Быстрый деплой...$(NC)"
	$(call remote,git pull --rebase)
	$(call remote,docker compose -f $(DEPLOY_COMPOSE) restart)
	@sleep 3; curl -sf $(HEALTH_URL)/ > /dev/null && echo "$(GREEN)✅ OK$(NC)" || echo "$(YELLOW)⚠️  Проверь логи$(NC)"

deploy-rollback: ## Откатить на предыдущий коммит
	@echo "$(YELLOW)Откат...$(NC)"
	$(call remote,git log --oneline -1)
	$(call remote,git reset --hard HEAD~1)
	$(call remote,docker compose -f $(DEPLOY_COMPOSE) up -d --build)
	$(call remote,docker compose -f $(DEPLOY_COMPOSE) exec -T $(APP_CONTAINER) cp /app/data/fields.db.bak /app/data/fields.db 2>/dev/null || true)
	@sleep 3; curl -sf $(HEALTH_URL)/ > /dev/null && echo "$(GREEN)✅ Откат завершён$(NC)" || echo "$(RED)❌ Проблемы$(NC)"

deploy-migrate: ## Запустить миграцию БД на сервере
	$(call container_exec,/opt/venv/bin/python src/db_migrate.py)
	@echo "$(GREEN)✅ Миграция завершена!$(NC)"

deploy-seed: ## Запустить seed данные на сервере
	$(call remote,docker compose -f $(DEPLOY_COMPOSE) run --rm $(APP_CONTAINER) /opt/venv/bin/python seed_auth.py)
	@echo "$(GREEN)✅ Seed завершён!$(NC)"

deploy-logs: ## Показать логи приложения на сервере
	ssh $(DEPLOY_SERVER) "docker logs $(APP_CONTAINER) --tail 50"

deploy-logs-live: ## Логи в реальном времени (Ctrl+C для выхода)
	ssh $(DEPLOY_SERVER) "docker logs -f $(APP_CONTAINER)"

deploy-status: ## Статус контейнеров на сервере
	ssh $(DEPLOY_SERVER) "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"

deploy-restart: ## Перезапустить приложение на сервере
	$(call remote,docker compose -f $(DEPLOY_COMPOSE) restart)
	@echo "$(GREEN)✅ Перезапуск завершён!$(NC)"

deploy-rebuild: ## Пересобрать без кэша и перезапустить
	$(call remote,docker compose -f $(DEPLOY_COMPOSE) build --no-cache)
	$(call remote,docker compose -f $(DEPLOY_COMPOSE) up -d)
	@echo "$(GREEN)✅ Пересборка завершён!$(NC)"

deploy-dry: ## Показать что будет сделано (без реального деплоя)
	@echo "$(YELLOW)═══ Dry Run ═══$(NC)"
	@echo "Server: $(DEPLOY_SERVER)"
	@echo "Dir:    $(DEPLOY_DIR)"
	@echo "Compose: $(DEPLOY_COMPOSE)"
	@echo ""
	@echo "Steps:"
	@echo "  1. Pre-deploy checks (pytest + js lint)"
	@echo "  2. git push upstream master"
	@echo "  3. Backup fields.db → fields.db.bak"
	@echo "  4. git pull --rebase"
	@echo "  5. Fix permissions on data/ uploads/"
	@echo "  6. docker compose up -d --build"
	@echo "  7. db_migrate.py"
	@echo "  8. Health check ($(HEALTH_RETRIES) x $(HEALTH_INTERVAL)s)"
	@echo "  9. docker image prune"

# Быстрые алиасы
t: test-e2e
th: test-e2e-headed
td: test-e2e-debug
tr: test-e2e-report
