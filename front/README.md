# AgriScore — Фронтенд

Веб-интерфейс для системы скоринга сельскохозяйственных субсидий **AgriScore KZ**.

---

## Технологии

| Технология | Назначение |
|------------|------------|
| **React 19** | UI-библиотека |
| **TypeScript** | Типизация |
| **Vite** | Сборщик и dev-сервер |
| **MUI (Material UI) 7** | Компонентная библиотека |
| **Recharts** | Графики и диаграммы |
| **Tailwind CSS 4** | Утилитарные стили |
| **React Router 7** | Маршрутизация |

---

## Структура

```
front/src/
├── main.tsx               # Точка входа, маршруты, провайдеры
├── theme.ts               # MUI-тема (цвета, типографика, компоненты)
├── index.css              # Tailwind, шрифты, глобальные стили
│
├── data/
│   ├── api.ts             # API-клиент (fetch-обёртки для всех эндпоинтов)
│   ├── auth.tsx           # AuthProvider, демо-пользователи, роли, guard
│   └── types.ts           # TypeScript-типы (ApplicationRow, ShapFactor)
│
├── components/
│   ├── Layout.tsx         # Sidebar + AppBar + профиль пользователя
│   ├── ScoreBadge.tsx     # Цветной бейдж балла (0–100)
│   ├── ScoreGauge.tsx     # SVG-индикатор балла (кольцо)
│   ├── ShapWaterfall.tsx  # Горизонтальная SHAP-диаграмма
│   └── BudgetBar.tsx      # Прогресс-бар бюджета
│
└── pages/
    ├── Login.tsx          # Авторизация (демо-аккаунты)
    ├── Register.tsx       # Регистрация
    ├── Dashboard.tsx      # Обзор: KPI, графики, быстрые действия
    ├── Registry.tsx       # Реестр заявок (таблица, фильтры, сортировка, пагинация)
    ├── AppDetail.tsx      # Детали заявки + SHAP-объяснение
    ├── Shortlist.tsx      # Скоринг: загрузка файла, результаты
    ├── Analytics.tsx      # Аналитика: важность факторов, метрики, fairness
    ├── ErrorLogs.tsx      # Лог ошибок валидации данных
    └── Settings.tsx       # Управление моделями, обучение
```

---

## Быстрый старт

### 1. Установка зависимостей

```bash
cd front
npm install
```

### 2. Запуск dev-сервера

```bash
npm run dev
```

Фронтенд запустится на `http://localhost:5173`.
API-запросы автоматически проксируются на `http://127.0.0.1:8000` (настроено в `vite.config.ts`).

> **Важно:** для корректной работы бэкенд должен быть запущен (`python run.py` из корня проекта).

### 3. Сборка для продакшена

```bash
npm run build
```

Собранные файлы будут в папке `front/dist/`.

---

## Демо-аккаунты

| Роль | Email | Пароль |
|------|-------|--------|
| Член комиссии | `commission@minagri.kz` | `123456` |

---

## Конфигурация прокси

В `vite.config.ts` настроен прокси для dev-режима:

```ts
server: {
  proxy: {
    "/api":    { target: "http://127.0.0.1:8000", changeOrigin: true },
    "/health": { target: "http://127.0.0.1:8000", changeOrigin: true },
  },
}
```

Все запросы к `/api/*` и `/health` перенаправляются на FastAPI-бэкенд.
