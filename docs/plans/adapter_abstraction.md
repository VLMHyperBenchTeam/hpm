# Архитектурный план: Абстракция Адаптеров (Python & Containers)

## Цель
Обеспечить независимость ядра HSM от конкретных инструментов (uv, docker) и позволить легко добавлять новые бекенды (pixi, podman).

## Проектируемая структура

### 1. Python Package Adapters
**Базовый класс**: `BasePackageManagerAdapter`
- `sync(requirements: List[str], frozen: bool)`: Синхронизация окружения.
- `lock()`: Генерация lock-файла.
- `add_dependency(name: str, version: str)`: Добавление в конфиг.

**Реализации**:
- `UvAdapter` (текущий)
- `PixiAdapter` (планируется)
- `PipAdapter` (планируется)

### 2. Container Service Adapters
**Базовый класс**: `BaseContainerAdapter`
- `generate_config(services: List[ContainerManifest])`: Создание `docker-compose.hsm.yml`.
- `up(services: List[str])`: Запуск.
- `down()`: Остановка.

**Реализации**:
- `DockerComposeAdapter` (текущий)
- `PodmanComposeAdapter` (планируется)

### 3. Регистрация и Загрузка
- Адаптеры регистрируются через `project.entry-points` в `pyproject.toml` HSM.
- `HSMCore` загружает их динамически на основе `hsm.yaml`.

## Схема
```mermaid
flowchart TD
    HSMCore --> PythonBridge
    HSMCore --> ContainerBridge
    PythonBridge --> UvAdapter
    ContainerBridge --> DockerAdapter