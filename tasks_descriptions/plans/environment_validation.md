# Plan: Environment Validation & Inspection

## Цель
Создать универсальный механизм для инспекции текущего состояния окружения (Python пакеты и Docker контейнеры). Этот механизм будет использоваться как для автоматизированного тестирования, так и для пользовательских команд (`hsm check`, `hsm sync --verify`).

## Архитектура
Центральным компонентом станет класс `EnvironmentInspector`, который инкапсулирует логику вызова внешних инструментов и парсинга их вывода.

### Интерфейс `EnvironmentInspector`
- `get_installed_packages(manager: str) -> Dict[str, str]`:
    - Вызывает `uv pip list --format json`, `pixi list --json` или `pip list --format json`.
    - Возвращает словарь `{ "имя-пакета": "версия" }`.
- `get_running_containers() -> List[Dict[str, Any]]`:
    - Вызывает `docker compose ps --format json`.
    - Возвращает список запущенных сервисов и их состояние.
- `inspect_container_env(service_name: str) -> Dict[str, str]`:
    - Вызывает `docker compose exec <service> env`.
    - Парсит вывод и возвращает словарь переменных окружения.

## Интеграция
1.  **HSMCore**: Добавление метода `verify_environment()`, который сопоставляет желаемое состояние (из `hsm.yaml`) с фактическим (через `Inspector`).
2.  **CLI**: Добавление флага `--verify` в команду `hsm sync`.
3.  **Tests**: Использование `Inspector` в `Assert` блоках для исключения "валидации на глаз".

## Ожидаемое поведение
Пользователь запускает `hsm sync --verify`, и после завершения установки HSM подтверждает: "Все пакеты и контейнеры соответствуют манифесту".