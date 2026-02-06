# План: Расширение набора адаптеров (Pixi, Podman)

## Цель
Обеспечить поддержку альтернативных инструментов управления пакетами (Pixi) и контейнерами (Podman), сохраняя единый интерфейс взаимодействия через `HSMCore`.

## Архитектура
Благодаря проведенному рефакторингу и использованию паттерна **Ports and Adapters**, добавление новых инструментов сводится к реализации абстрактных классов в `hsm/src/hyper_stack_manager/adapters/`.

### 1. Pixi Adapter (`BasePackageManagerAdapter`)
- **Инструмент**: [Pixi](https://pixi.sh/) (современный менеджер на базе conda/mamba).
- **Особенности**: Работа с `pixi.toml`, поддержка нескольких окружений.
- **Реализация**:
    - Метод `sync()`: Вызов `pixi install`.
    - Метод `lock()`: Вызов `pixi lock`.
    - Метод `init_lib()`: Вызов `pixi init`.

### 2. Podman Adapter (`BaseContainerAdapter`)
- **Инструмент**: Podman / Podman Compose.
- **Особенности**: Бездемонный режим, совместимость с Docker Compose CLI.
- **Реализация**:
    - Метод `generate_config()`: Генерация `docker-compose.hsm.yml` (совместим с Podman).
    - Метод `up()` / `down()`: Вызов `podman-compose`.

## Регистрация
Новые адаптеры должны регистрироваться через `entry-points` в `pyproject.toml`:
```toml
[project.entry-points."hsm.package_managers"]
pixi = "hyper_stack_manager.adapters.python_pixi:PixiAdapter"

[project.entry-points."hsm.container_engines"]
podman = "hyper_stack_manager.adapters.container_podman:PodmanAdapter"