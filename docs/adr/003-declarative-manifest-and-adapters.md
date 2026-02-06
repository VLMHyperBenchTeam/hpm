# ADR 003: Манифест hsm.yaml и архитектура адаптеров

## Статус
Accepted

## Контекст
1.  **Декларативность**: Требуется четкое разделение между "намерением" (hpm.yaml) и "реализацией" (pyproject.toml, docker-compose.yml).
2.  **Атомарность**: Использование hpm.yaml как Single Source of Truth позволяет избежать сломанных состояний в основных конфигах проекта.
3.  **Meta-Orchestrator**: HPM должен управлять как Python-пакетами, так и Docker-сервисами, обеспечивая бесшовный переход между Dev и Prod режимами.

## Решение

### 1. Манифест `hsm.yaml`
Файл `hsm.yaml` становится основным источником правды. Для его редактирования используется библиотека `ruamel.yaml`, что позволяет сохранять комментарии и форматирование пользователя.

### 2. Структура Реестра (Registry)
Реестр разделяется на независимые сущности для обеспечения чистоты метаданных:
*   `packages/`: Манифесты Python-пакетов.
*   `containers/`: Манифесты Docker-контейнеров.
*   `package_groups/`: Группы выбора для Python-пакетов.
*   `container_groups/`: Группы выбора для сервисов/контейнеров.

### 3. Архитектура адаптеров
HPM делегирует выполнение синхронизации специализированным адаптерам:
*   **UvAdapter**: Транслирует зависимости в `pyproject.toml` и вызывает `uv sync`.
*   **DockerAdapter**: Использует механизм **Profiles** (Docker Compose v2) для активации групп сервисов и генерирует `docker-compose.hsm.yml`.

### 4. Поддержка Docker (Dev Mode)
Для контейнеров в режиме `dev` поддерживается множественное монтирование томов (volumes). HPM автоматически подменяет `image` на `build` и инжектирует `volumes` в override-файл.

**Пример манифеста контейнера в реестре:**
```yaml
name: "qdrant"
type: "container"
orchestration:
  service_name: "vector-db"
sources:
  prod:
    type: "docker-image"
    image: "qdrant/qdrant:latest"
  dev:
    type: "git"
    url: "https://github.com/qdrant/qdrant.git"
    volumes:
      - "./data:/var/lib/qdrant"
      - "./config:/etc/qdrant"
```

### 5. CLI Структура
*   **Project**: `hsm init`, `hsm sync`, `hsm check`, `hsm list`.
*   **Edit**: `hsm package add/remove`, `hsm group add/remove`.
*   **Registry**: `hsm registry ...` (справочная информация).

## Последствия
*   **Плюсы**: Чистый `pyproject.toml`, автоматизация сложных Docker-воркфлоу, сохранение комментариев в конфигах, четкое разделение типов компонентов.
*   **Минусы**: Усложнение структуры реестра, необходимость поддержки нескольких типов групп.