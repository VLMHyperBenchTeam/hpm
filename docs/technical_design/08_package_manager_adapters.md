# Technical Design: Package Manager Adapters

## 1. Обзор
Концепция адаптеров позволяет HPM быть независимым от конкретного инструмента управления пакетами. HPM управляет "намерениями" (какие группы и пакеты выбраны), а адаптеры отвечают за "материализацию" этих намерений в конкретной среде.

## 2. Архитектура
Все адаптеры должны наследоваться от базового абстрактного класса `BasePackageManagerAdapter`.

### 2.1. Интерфейс `BasePackageManagerAdapter`
```python
class BasePackageManagerAdapter(ABC):
    @abstractmethod
    def sync(self, requirements: List[PackageRequirement], frozen: bool = False):
        """Применяет требования к текущему окружению."""
        pass

    @abstractmethod
    def lock(self):
        """Фиксирует текущее состояние зависимостей."""
        pass

    @abstractmethod
    def init_project(self, path: Path):
        """Инициализирует специфичные для менеджера файлы."""
        pass
```

## 3. Реализованные адаптеры

### 3.1. UvAdapter (Основной)
Использует мощь `uv` для мгновенной установки и разрешения зависимостей.
*   **Механизм**: Обновляет секцию `[project.dependencies]` в `pyproject.toml`.
*   **Команды**: Вызывает `uv sync` и `uv lock`.
*   **Преимущества**: Высокая скорость, нативная поддержка `pyproject.toml`.

## 4. Планируемые адаптеры

### 4.1. PixiAdapter
Для проектов, требующих управления не только Python-пакетами, но и системными зависимостями (C++, CUDA и т.д.).
*   **Механизм**: Обновляет `[tool.pixi.dependencies]`.
*   **Команды**: Вызывает `pixi install`.

### 4.2. PipAdapter
Для обеспечения совместимости с классическими окружениями.
*   **Механизм**: Генерирует или обновляет `requirements.txt`.
*   **Команды**: Вызывает `pip install -r requirements.txt`.

## 5. Выбор адаптера
Адаптер выбирается на основе значения `tool.hpm.manager` в `pyproject.toml`. Если значение не указано, по умолчанию используется `uv`.