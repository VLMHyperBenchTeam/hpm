# Technical Design: CLI & Manifest Management Architecture

**Status**: Draft
**Date**: 2026-02-02

## 1. Обзор

Этот документ описывает архитектуру CLI для управления реестром и конфигурацией проекта, основываясь на лучших практиках 2025-2026 годов (Declarative configuration, Interactive DX, Observability).

## 2. Принципы

1.  **Декларативность + Императивность**:
    *   Основной источник правды — файлы (`registry/**/*.yaml`, `pyproject.toml`).
    *   CLI-команды — это удобные обертки (shortcuts) для редактирования этих файлов.
2.  **Прозрачность (Observability)**:
    *   Пользователь всегда должен видеть, что происходит с его конфигурацией.
    *   Команды типа `list`, `show`, `diff` обязательны.
3.  **Валидация на лету**:
    *   Любое изменение конфигурации должно проверяться на корректность до применения (`check`/`dry-run`).

## 3. Управление Реестром (`hpm registry`)

Реестр — это набор YAML-файлов. Ручное редактирование возможно, но чревато ошибками.

### 3.1. Добавление пакета (`hpm registry add`)
Интерактивный визард для создания нового манифеста пакета.

**Workflow:**
1.  `hpm registry add package`
2.  Prompt: "Package Name?" -> `my-lib`
3.  Prompt: "Source Type?" -> `[Git / Local / PyPI]`
4.  Prompt (if Git): "Repo URL?" -> `https://github.com/...`
5.  Prompt: "Version?" -> `1.0.0`
6.  **Результат**: Создается файл `registry/packages/my-lib.yaml`.

### 3.2. Добавление группы (`hpm registry add group`)
Визард для создания новой группы.

**Workflow:**
1.  `hpm registry add group`
2.  Prompt: "Group Name?" -> `inference`
3.  Prompt: "Strategy?" -> `[1-of-N / M-of-N]`
4.  Prompt: "Select Options?" -> (Список доступных пакетов из реестра)
5.  **Результат**: Создается файл `registry/groups/inference.yaml`.

### 3.3. Валидация (`hpm registry validate`)
Проверяет целостность реестра:
*   Все ссылки в группах ведут на существующие пакеты.
*   YAML валиден согласно схемам Pydantic.

## 4. Управление Проектом (`hpm project` / `hpm group`)

Конфигурация проекта живет в `pyproject.toml`.

### 4.1. Просмотр состояния (`hpm list`)
Выводит дерево текущей конфигурации с типами групп.

**Пример вывода:**
```text
Project: vlmhyperbench
├── Groups
│   ├── inference (1-of-N)
│   │   └── vlm-adapter-qwen (active)
│   └── metrics (M-of-N)
│       ├── accuracy (active)
│       └── latency (active)
└── Dependencies
    └── (Managed by uv)
```

### 4.2. Детали группы (`hpm show <group>`)
Показывает доступные опции для группы.

**Пример вывода:**
```text
Group: inference
Strategy: 1-of-N (Select one)
Description: Backend for VLM inference.

Options:
  * vlm-adapter-qwen (Installed) - Adapter for Qwen-VL
    vlm-adapter-deepseek       - Adapter for DeepSeek-VL
    vllm-backend               - High-performance vLLM backend
```

### 4.3. Поиск (`hpm search <query>`)
Поиск по реестру. Ищет в названиях групп, пакетов и описаниях.

## 5. Взаимодействие с `pyproject.toml`

Мы поддерживаем два режима работы:

1.  **Human-Edit (Декларативный)**:
    *   Пользователь открывает `pyproject.toml` в IDE.
    *   Правит секцию `[tool.hpm.groups]`.
    *   Запускает `hpm sync`.
    *   *Плюс*: Полный контроль, привычно для GitOps.

2.  **CLI-Edit (Императивный)**:
    *   Пользователь запускает `hpm group add inference --option vllm`.
    *   HPM валидирует ввод.
    *   HPM обновляет `pyproject.toml`.
    *   HPM запускает `sync` (опционально или автоматически).
    *   *Плюс*: Быстро, меньше ошибок в названиях.

## 6. План реализации (Next Steps)

1.  Реализовать **Discovery Commands**: `hpm list`, `hpm show`, `hpm search`.
    *   Это закроет потребность в "наблюдаемости".
2.  Реализовать **Registry Management**: `hpm registry add`.
    *   Это упростит наполнение реестра.