# Task: Реализация UvRuntimeAdapter и команды service init

## Контекст
Для поддержки VES нам нужен адаптер, умеющий создавать изолированные venv и выполнять в них sync.

## Шаги реализации
1.  **Adapter (`src/hyper_stack_manager/adapters/python_uv.py`)**:
    - [ ] Реализовать `init_service(path)`: вызов `uv init --no-workspace`.
    - [ ] Реализовать `sync_service(path)`: вызов `uv sync` внутри указанной папки.
2.  **CLI (`src/hyper_stack_manager/cli/project.py`)**:
    - [ ] Добавить группу команд `hsm service`.
    - [ ] Реализовать `hsm service init <name> --runtime uv`.
3.  **Core (`src/hyper_stack_manager/core/engine.py`)**:
    - [ ] Добавить метод `init_service` в `HSMCore`.

## Критерии готовности
- [ ] Команда `hsm service init` создает папку с изолированным `pyproject.toml`.
- [ ] В реестре появляется запись о новом сервисе.

## Отчет о реализации
*(Заполняется инстансом после завершения задачи)*
- **Что сделано**: ...
- **Как реализовано**: ...
- **Отклонения от плана**: ...