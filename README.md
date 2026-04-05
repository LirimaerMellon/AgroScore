# AgriScore

Система скоринга заявок на сельскохозяйственные субсидии на основе LightGBM с объяснимостью решений через SHAP.

---

## Стек технологий

- Python 3.10+
- FastAPI + Uvicorn (REST API)
- LightGBM (градиентный бустинг)
- SHAP (объяснимость решений)
- scikit-learn (метрики, кросс-валидация, LabelEncoder)
- pandas + openpyxl (работа с данными и Excel)
- SQLite (хранение данных)
- React + Vite + TypeScript (фронтенд)

---

## Как запустить

### Бэкенд

```bash
pip install -r requirements.txt
python run.py
```

Сервер: `http://127.0.0.1:8000`  
Swagger-документация: `http://127.0.0.1:8000/docs`

### Обучение модели (CLI)

```bash
python tests/train.py --input data/raw/файл.xlsx
```

### Обучение модели (API)

```bash
curl -X POST http://127.0.0.1:8000/api/train -F "file=@файл.xlsx"
```

### Скоринг заявок

```bash
curl -X POST http://127.0.0.1:8000/api/score -F "file=@заявки.xlsx"
```

### Фронтенд

```bash
cd front
npm install
npm run dev
```

Фронтенд: `http://localhost:5173`. API-запросы проксируются на бэкенд.

---

## Структура проекта

```
AgriScore/
├── run.py                     # Точка входа (uvicorn)
├── requirements.txt
├── app/
│   ├── main.py                # FastAPI-приложение, CORS, health-check
│   ├── config.py              # Пути, колонки, параметры модели, бизнес-правила
│   ├── schemas.py             # Pydantic-схемы запросов и ответов
│   ├── setup_dirs.py          # Инициализация директорий при старте
│   ├── pipeline/
│   │   ├── loader.py          # Загрузка данных (Excel/CSV/JSON)
│   │   ├── mapper.py          # Маппинг русских колонок в internal names
│   │   ├── validators.py      # Валидация значений ячеек
│   │   ├── cleaner.py         # Очистка данных, логирование ошибок в SQLite
│   │   ├── features.py        # Feature engineering (fit/transform)
│   │   ├── model.py           # LightGBM: обучение, скоринг, fairness
│   │   └── explainer.py       # SHAP-объяснения (калиброванные и legacy)
│   ├── services/
│   │   ├── training.py        # Оркестрация обучения
│   │   └── scoring.py         # Оркестрация скоринга
│   ├── database/
│   │   ├── connection.py      # SQLite: подключение, миграции, WAL-режим
│   │   ├── repository.py      # ErrorLogRepository (лог ошибок)
│   │   ├── model_repository.py    # ModelRepository (реестр моделей)
│   │   ├── app_repository.py      # ApplicationRepository (заявки)
│   │   ├── shap_repository.py     # ShapRepository (SHAP-данные)
│   │   └── threshold_repository.py # ThresholdRepository (пороги, бюджет)
│   └── routers/
│       ├── train.py           # POST /api/train, /api/train/json
│       ├── score.py           # POST /api/score, /api/score/json
│       ├── template.py        # GET  /api/template
│       ├── applications.py    # GET  /api/applications, /{id}, /{id}/shap
│       ├── analytics.py       # GET  /api/analytics/*
│       ├── models_rt.py       # GET  /api/models, POST /api/models/activate
│       ├── errors.py          # GET  /api/errors, /summary, /traces
│       ├── export.py          # GET  /api/export
│       ├── shortlist.py       # GET  /api/shortlist
│       └── thresholds.py      # GET/PUT /api/thresholds, /api/round-budget
├── data/                      # Данные и артефакты (не в git)
│   ├── agriscore.db
│   ├── raw/
│   ├── models/
│   ├── features/
│   ├── results/
│   └── debug/
├── front/                     # React + Vite фронтенд
└── tests/
    ├── test_api.py            # Интеграционный тест всех эндпоинтов
    └── train.py               # CLI-скрипт обучения
```

---

## API-эндпоинты

### Health

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/health` | Статус сервера и активной модели |

### Обучение

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/train` | Обучение из Excel/CSV файла |
| POST | `/api/train/json` | Обучение из JSON body |

**Параметры `/api/train`:**
- `file` (multipart) — Excel (.xlsx) или CSV файл с историческими данными

**Ответ** содержит: версию модели, метрики (AUC, F1, Precision, Recall, Gini), fairness-отчёт, важность признаков, `trace_id` для просмотра ошибок очистки.

### Скоринг

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/score` | Скоринг заявок из Excel/CSV |
| POST | `/api/score/json` | Скоринг заявок из JSON body |
| GET | `/api/template` | Скачать Excel-шаблон для заполнения |

**Параметры `/api/score`:**
- `file` (multipart) — файл по шаблону (без столбцов «Дата поступления», «Статус заявки», «Номер заявки»)
- `model_version` (опционально) — конкретная версия модели

**Ответ** содержит: список заявок с оценками (score 0–100), категориями (HIGH / MEDIUM / LOW), вероятностями и SHAP-объяснениями.

### Заявки

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/applications` | Список оценённых заявок (пагинация, фильтры) |
| GET | `/api/applications/{id}` | Детали заявки |
| GET | `/api/applications/{id}/shap` | SHAP-объяснение оценки |
| GET | `/api/applications/{id}/analysis` | Сравнение с аналогами, перцентиль |

**Фильтры для `/api/applications`:**
- `limit`, `offset` — пагинация
- `region`, `category`, `model_version` — фильтры
- `min_score`, `max_score` — диапазон скора
- `sort_by` (score / created_at / amount / normative), `sort_dir` (asc / desc)

### Аналитика

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/analytics/summary` | Сводная статистика |
| GET | `/api/analytics/distribution` | Гистограмма скоров |
| GET | `/api/analytics/features` | Важность признаков |
| GET | `/api/analytics/fairness` | Fairness-отчёт (disparate impact) |
| GET | `/api/analytics/by-month` | Динамика по месяцам |
| GET | `/api/analytics/avg-score-by-region` | Средний балл по регионам |
| GET | `/api/analytics/avg-score-by-direction` | Средний балл по направлениям |
| GET | `/api/analytics/available-years` | Доступные годы |

### Модели

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/models` | Список обученных моделей |
| POST | `/api/models/activate?version=...` | Активировать модель |

### Шорт-лист

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/shortlist` | Ранжирование заявок в рамках бюджета |

### Пороги и бюджет

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/thresholds` | Текущие пороги категорий |
| PUT | `/api/thresholds` | Обновить пороги |
| POST | `/api/thresholds/reset` | Сброс к дефолтным |
| POST | `/api/thresholds/preview` | Предпросмотр распределения |
| GET | `/api/round-budget` | Текущий бюджет раунда |
| PUT | `/api/round-budget` | Обновить бюджет |

### Ошибки данных

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/errors` | Лог невалидных строк |
| GET | `/api/errors/summary` | Сводка ошибок по типам и колонкам |
| GET | `/api/errors/traces` | Список загрузок с числом ошибок |

### Экспорт

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/export` | Экспорт заявок в Excel |

### Администрирование

| Метод | Путь | Описание |
|-------|------|----------|
| DELETE | `/api/admin/reset` | Очистка БД и удаление файлов моделей |

---

## Конфигурация

Все настройки находятся в `app/config.py`:

| Параметр | Описание |
|----------|----------|
| `MODEL_PARAMS` | Гиперпараметры LightGBM |
| `COLUMN_RENAME_MAP` | Маппинг русских заголовков в internal |
| `APPROVED_STATUSES` | Статусы, считающиеся одобренными |
| `REJECTED_STATUSES` | Статусы, считающиеся отклонёнными |
| `SCORE_MIN / SCORE_MAX` | Диапазон скоринга (0-100) |
| `TEMPLATE_COLUMNS` | Заголовки Excel-шаблона для скоринга |

---

## Требования к входным данным

### Для обучения

Excel-файл с русскими заголовками:

| Столбец | Тип | Описание |
|---------|-----|----------|
| Дата поступления | дата | Дата подачи заявки |
| Область | текст | Область подачи |
| Акимат | текст | Акимат |
| Номер заявки | текст | Уникальный номер |
| Направление водства | текст | Направление хозяйства |
| Наименование субсидирования | текст | Тип субсидии |
| Статус заявки | текст | Исполнена / Одобрена / Отклонена / Отозвано / Получена |
| Норматив | число | Нормативная стоимость (> 0) |
| Причитающая сумма | число | Запрашиваемая сумма (> 0) |
| Район хозяйства | текст | Район |

### Для скоринга

Файл по шаблону (`GET /api/template`), без столбцов «Дата поступления», «Статус заявки», «Номер заявки». Добавляется столбец «БИН/ИИН».

---

## Категории скоринга

| Категория | Диапазон | Описание |
|-----------|----------|----------|
| HIGH | 70-100 | Высокая вероятность одобрения |
| MEDIUM | 40-69 | Средняя вероятность |
| LOW | 0-39 | Низкая вероятность |

Пороги настраиваются через API (`PUT /api/thresholds`).

---

## Тестирование

```bash
python run.py
# В другом терминале:
python tests/test_api.py
```

Тест автоматически обучает модель из `.xlsx` файла в `data/raw/`, прогоняет скоринг и проверяет все эндпоинты.
