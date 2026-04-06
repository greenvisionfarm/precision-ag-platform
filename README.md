# Field Mapper

> Open-source precision agriculture platform for drone NDVI analysis and prescription maps

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/greenvisionfarm/precision-ag-platform/blob/master/LICENSE)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![Node](https://img.shields.io/badge/node-20-green.svg)](https://nodejs.org/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://docs.docker.com/)
[![Docs](https://img.shields.io/badge/docs-online-green.svg)](https://greenvisionfarm.github.io/precision-ag-platform/)
![Status](https://img.shields.io/badge/status-active%20development-orange.svg)

---

> ⚠️ **Внимание:** Платформа находится в **активной разработке** и **ещё не протестирована в полной мере в production-условиях**. Мы активно работаем над стабильностью. Используйте на свой страх и риск. Сообщайте о багах через [Issues](https://github.com/greenvisionfarm/precision-ag-platform/issues).

---

**Field Mapper** — веб-платформа для фермеров и агрономов, которая превращает данные с дронов (DJI Mavic 3M, NDVI снимки) в карты предписаний для сельскохозяйственной техники.

![Field Mapper Interface](docs/assets/screenshot.png)

---

## 🚀 Features

| 🌱 **Field Management** | 🚁 **NDVI Analysis** | 📤 **Export** | 🚜 **Prescription Maps** |
|-------------------------|---------------------|---------------|-------------------------|
| Field boundaries on map | GeoTIFF upload | **ISOXML** (John Deere, Claas) | Auto norm calculation |
| Owners & cadastre | Automatic zoning | DJI KMZ (WPML 1.0.6) | 3 productivity zones |
| KMZ import/export | Large aggregated zones | Shapefile | Norms: 150/250/350 kg/ha |
| Statistics & reports | **Scan history** | Bulk ZIP export | Zone statistics |
| | **Scan deletion** | | |
| | **Fullscreen mode** | | |

---

## ⚡ Quick Start

### Docker (recommended)

```bash
docker-compose up -d --build
```

Open [http://localhost](http://localhost)

### Local

```bash
python3.12 -m venv venv && source venv/bin/activate
pip install -r requirements.txt && npm install
python app.py
```

Open [http://localhost:8888](http://localhost:8888)

📖 **Full guide:** [docs/getting-started/installation.md](docs/getting-started/installation.md)

---

## 📚 Documentation

| Section | Description |
|---------|-------------|
| [🚀 Quick Start](docs/getting-started/installation.md) | Installation & setup |
| [👤 User Guide](docs/user-guide/fields.md) | Fields, NDVI, export |
| [🚜 Prescription Maps](docs/user-guide/isoxml.md) | ISOXML export, application rates |
| [👨‍💻 Developer Guide](docs/developer-guide/architecture.md) | Architecture, API, testing |
| [📋 Changelog](docs/changelog/CHANGELOG.md) | Release history |
| [🤖 AI Contexts](.ai-contexts/) | Context for AI assistants |

🌐 **Online docs:** https://greenvisionfarm.github.io/precision-ag-platform/

---

## 🏗️ Architecture

```
┌─────────────┐     ┌─────────────┐
│   Nginx     │────▶│   Tornado   │
│  (80/443)   │     │   (8888)    │
└─────────────┘     └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   SQLite    │
                    │   /Postgres │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Redis+Huey │
                    │  (Queue)    │
                    └─────────────┘
```

**Stack:**
- **Backend:** Python 3.12 (Tornado, Peewee, Huey, GDAL, Rasterio, Scikit-learn)
- **Frontend:** jQuery, Leaflet, DataTables, Chart.js, ES6 Modules
- **Infrastructure:** Docker, Redis, Nginx

---

## 🔐 Authentication

Платформа поддерживает **мульти-тенантность** — каждая компания изолирована и видит только свои данные.

### Self-service регистрация
1. Откройте `http://localhost:80` (или `http://localhost:8888` без Docker)
2. Нажмите **"Регистрация"** на странице входа
3. Введите email, пароль и название компании
4. Вы автоматически войдёте как владелец компании

### Тестовый доступ (Docker)
```bash
# Запустите Docker
docker compose up -d

# Войдите с тестовым пользователем
Email: admin@fieldmapper.test
Password: admin
```

### API Authentication
```bash
# 1. Логин
curl -X POST http://localhost:80/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@fieldmapper.test","password":"admin"}' \
  -c cookies.txt

# 2. Запрос с cookie
curl http://localhost:80/api/fields -b cookies.txt
```

---

## ✅ Testing

```bash
# Backend
FIELD_MAPPER_ENV=test ./venv/bin/pytest tests/

# Frontend
npm test

# In Docker
docker-compose run --rm -e FIELD_MAPPER_ENV=test app pytest tests/
docker-compose run --rm app npm test
```

**Status:** 32 passed, 1 skipped | **Coverage:** ~65% (backend)

---

## 🗺️ Roadmap

Track progress on [GitHub Projects](https://github.com/orgs/greenvisionfarm/projects) and [Issues](https://github.com/greenvisionfarm/precision-ag-platform/issues).

### Upcoming Releases

| Milestone | Focus | Target |
|-----------|-------|--------|
| **v2026.3** | Orthomosaic from drone photos, mobile UI | Apr 2026 |
| **v2026.4** | NDVI time series, yield prediction, OneSoil | May 2026 |
| **v2027.1** | PostgreSQL/PostGIS, CI/CD, monitoring | Jan 2027 |

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

- 🐛 [Bug Reports](https://github.com/greenvisionfarm/precision-ag-platform/issues/new?template=bug_report.yml)
- ✨ [Feature Requests](https://github.com/greenvisionfarm/precision-ag-platform/issues/new?template=feature_request.yml)
- 🔧 Pull Requests

> 🤖 **AI-Assisted Development:** This project is built and actively developed with the help of AI agents (Qwen Code, etc.). This is a feature, not a bug — it allows us to move fast while maintaining quality.

---

## 📊 Project Metrics

| Metric | Value |
|--------|-------|
| **Tests** | 32 passed, 1 skipped |
| **Coverage** | ~65% (backend) |
| **Image Size** | ~1.5 GB (with GIS) |
| **Build Time** | ~6 min (~2 min with cache) |

---

## 🔗 Links

- **GitHub:** [greenvisionfarm/precision-ag-platform](https://github.com/greenvisionfarm/precision-ag-platform)
- **Docs:** [GitHub Pages](https://greenvisionfarm.github.io/precision-ag-platform/)
- **Issues:** [Bug Reports & Features](https://github.com/greenvisionfarm/precision-ag-platform/issues)
- **Projects:** [GitHub Projects](https://github.com/orgs/greenvisionfarm/projects)
- **License:** [MIT](LICENSE)
- **Security:** [SECURITY.md](SECURITY.md)

---

*Last updated: April 6, 2026*  
*Built with ❤️ and AI agents 🤖*
