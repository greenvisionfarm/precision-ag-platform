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

DEPLOY_SERVER ?= user@localhost
DEPLOY_DIR ?= ~/field_mapper
DEPLOY_COMPOSE ?= docker-compose.server.yml

deploy: ## Задеплоить на домашний сервер
	@echo "$(YELLOW)Деплой на $(DEPLOY_SERVER)...$(NC)"
	@echo "$(BLUE)1. Push в GitHub...$(NC)"
	git push upstream master
	@echo "$(BLUE)2. Git pull и restart на сервере...$(NC)"
	ssh $(DEPLOY_SERVER) "cd $(DEPLOY_DIR) && git pull --rebase && docker compose -f $(DEPLOY_COMPOSE) up -d --build"
	@echo "$(GREEN)✅ Деплой завершён! http://$(shell echo $(DEPLOY_SERVER) | cut -d@ -f2):8080$(NC)"

deploy-seed: ## Запустить seed данные на сервере
	@echo "$(YELLOW)Запуск seed данных на сервере...$(NC)"
	ssh $(DEPLOY_SERVER) "cd $(DEPLOY_DIR) && docker compose -f $(DEPLOY_COMPOSE) run --rm app /opt/venv/bin/python seed_auth.py"
	@echo "$(GREEN)✅ Seed завершён!$(NC)"

deploy-logs: ## Показать логи приложения на сервере
	@echo "$(YELLOW)Логи приложения:$(NC)"
	ssh $(DEPLOY_SERVER) "docker logs field-mapper-app --tail 50"

deploy-status: ## Статус контейнеров на сервере
	@echo "$(YELLOW)Статус контейнеров:$(NC)"
	ssh $(DEPLOY_SERVER) "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"

deploy-restart: ## Перезапустить приложение на сервере
	@echo "$(YELLOW)Перезапуск...$(NC)"
	ssh $(DEPLOY_SERVER) "cd $(DEPLOY_DIR) && docker compose -f $(DEPLOY_COMPOSE) restart"
	@echo "$(GREEN)✅ Перезапуск завершён!$(NC)"

deploy-rebuild: ## Пересобрать и перезапустить (после изменений Dockerfile)
	@echo "$(YELLOW)Пересборка...$(NC)"
	ssh $(DEPLOY_SERVER) "cd $(DEPLOY_DIR) && git pull && docker compose -f $(DEPLOY_COMPOSE) up -d --build"
	@echo "$(GREEN)✅ Пересборка завершён!$(NC)"

# Быстрые алиасы
t: test-e2e
th: test-e2e-headed
td: test-e2e-debug
tr: test-e2e-report
