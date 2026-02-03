# Technical Design: Package Manager Adapters

## 1. Обзор
Концепция адаптеров позволяет HSM быть независимым от конкретного инструмента управления пакетами. HSM управляет "намерениями" (какие группы и пакеты выбраны в `hsm.yaml`), а адаптеры отвечают за "материализацию" этих намерений в конкретной среде (например, обновление `pyproject.toml` и вызов `uv sync`).

## 2. Архитектура
Все адаптеры должны наследоваться от базового абстрактного класса `BasePackageManagerAdapter`.

### 2.1. Интерфейс `BasePackageManagerAdapter`
```python
class BasePackageManagerAdapter(ABC):
    @abstractmethod
    def sync(self, packages: List[str], frozen: bool = False):
        """Materialize dependencies into the environment."""
        pass

    @abstractmethod
    def lock(self):
        """Generate lock file."""
        pass
```

## 3. Реализованные адаптеры

### 3.1. UvAdapter (Основной)
Использует мощь `uv` для мгновенной установки и разрешения зависимостей.
*   **Механизм**: Обновляет секцию `[project.dependencies]` в `pyproject.toml` с использованием `tomlkit` для сохранения форматирования.
*   **Команды**: Вызывает `uv sync` и `uv lock`.
*   **Преимущества**: Высокая скорость, нативная поддержка стандартов Python.

## 4. Планируемые адаптеры

### 4.1. DockerAdapter
Для управления инфраструктурными сервисами.
*   **Механизм**: Генерирует `docker-compose.hsm.yml` и использует Docker Profiles.
*   **Команды**: Вызывает `docker compose`.

### 4.2. PixiAdapter
Для проектов, требующих управления системными зависимостями (C++, CUDA).
*   **Механизм**: Обновляет `[tool.pixi.dependencies]`.

## 5. Выбор адаптера
Адаптер выбирается на основе значения `dependencies.manager` в `hsm.yaml`. Если значение не указано, по умолчанию используется `uv`.