# Task: Реализация EnvironmentInspector

## Контекст
Для надежного тестирования и валидации синхронизации нам нужен программный доступ к списку установленных пакетов и запущенных контейнеров.

## Шаги реализации
1.  **Создание модуля**:
    *   [ ] Создать `src/hyper_stack_manager/core/inspector.py`.
2.  **Реализация парсеров**:
    *   [ ] Реализовать `get_installed_packages` с поддержкой JSON формата для `uv`, `pixi`, `pip`.
    *   [ ] Реализовать `get_running_containers` через `docker compose ps --format json`.
    *   [ ] Реализовать `inspect_container_env` через `docker compose exec <service> env`.
3.  **Интеграция в Core**:
    *   [ ] Добавить `self.inspector = EnvironmentInspector()` в `HSMCore`.
    *   [ ] Добавить метод `HSMCore.verify_sync_results()`.
4.  **Интеграция в CLI**:
    *   [ ] Добавить флаг `--no-verify` в команду `hsm sync`.
    *   [ ] По умолчанию (если нет `--no-verify`) вызывать `verify_sync_results()` после синхронизации и выводить отчет.
5.  **Тестирование (Real-World Integration)**:
    *   [ ] **Unit**: Тестирование парсинга на статических JSON-дампах (uv, pixi, pip).
    *   [ ] **Integration**: Полный цикл в sandbox: `init` -> `package init` -> `sync` -> `inspector.get_installed_packages()`.
    *   [ ] **Docker Integration**: `sync` (с контейнером) -> `inspector.get_running_containers()` -> `inspector.inspect_container_env()`.

## Критерии готовности
- [ ] Инспектор корректно парсит JSON вывод всех трех менеджеров в реальном окружении.
- [ ] Метод `inspect_container_env` возвращает реальные переменные из контейнера.
- [ ] Команда `hsm sync` по умолчанию выводит отчет о верификации окружения.