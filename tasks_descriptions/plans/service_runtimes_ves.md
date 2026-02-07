# Plan: Service Runtimes & Virtual Environment Services (ADR-002)

## 1. Цель
Трансформация HSM в универсальный гипервизор. Реализация поддержки «мягкой» изоляции (Virtual Environments) наравне с «жесткой» (Containers). Обеспечение 100% воспроизводимости через «Service as a Repository».

## 2. Архитектурные изменения

### 2.1. Реестр (Universal Registry)
Переход от технологического к функциональному разделению:
- `packages/` -> `libraries/` (библиотеки для общего venv проекта).
- `containers/` -> `services/` (автономные компоненты: docker, uv, node).
- `package_groups/` -> `library_groups/`.
- `container_groups/` -> `service_groups/`.

### 2.2. Модели данных (`models.py`)
- **`RuntimeType`**: Enum (`docker`, `podman`, `uv`, `pixi`, `venv`).
- **`ServiceManifest`**:
    - Наследует логику профилей развертывания.
    - Поле `runtime` в профиле определяет используемый адаптер.
    - Поля `command` и `working_dir` для venv-рантаймов.
- **`Source`**: Поддержка `git` и `local` для всех типов сервисов.

### 2.3. Логика материализации (Sync Engine)
1.  **Библиотеки**: Устанавливаются в корень проекта (текущая логика `UvAdapter`).
2.  **Сервисы (Isolated)**:
    - HSM определяет `target_path` (например, `./services/<name>`).
    - Если `source: git` — клонирует репозиторий.
    - Вызывает `RuntimeAdapter.sync(target_path)`.
    - Для `uv` это запуск `uv sync --no-workspace` внутри `target_path`.

### 2.4. Команда `hsm service init`
Аналог `package init`, но:
- Создает папку в `./services/`.
- Выполняет `uv init --no-workspace`.
- Регистрирует в реестре как `type: service`.

## 3. Протокол приемки (Acceptance Protocol)

### L1: Unit (Logic)
- Проверка `SyncEngine`: корректное вычисление путей для venv-сервисов.
- Проверка `Implication Merging`: слияние параметров для сервисов с разными рантаймами.

### L2: Integration (Filesystem)
- Тест `service init`: проверка создания изолированного `pyproject.toml` (без привязки к воркспейсу).
- Тест `sync`: проверка генерации `docker-compose.hsm.yml` только для `runtime: docker` и игнорирование venv-сервисов в нем.

### L3: Real-World (Sandbox)
- **Scenario**: Создание venv-сервиса -> Sync -> Проверка через `EnvironmentInspector`.
- **Критерий**: В папке сервиса есть свой `.venv`, пакеты установлены согласно его `uv.lock`, основной проект не содержит этих пакетов.

## 4. Этапы реализации
1.  **Task 1**: Рефакторинг моделей и структуры реестра.
2.  **Task 2**: Реализация `UvRuntimeAdapter` (изолированный sync).
3.  **Task 3**: Реализация CLI команды `hsm service init`.
4.  **Task 4**: Обновление `SyncEngine` (оркестрация материализации).
5.  **Task 5**: Миграция тестов и обновление Memory Bank.