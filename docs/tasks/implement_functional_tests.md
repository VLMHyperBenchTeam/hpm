# Задача: Реализация Функциональных тестов (Level 1.1 - 1.3)

## Контекст
Необходимо реализовать полную базу тестов согласно стратегии в `hsm/docs/technical_design/11_testing_strategy.md`, используя паттерн "Self-Bootstrapping Sandbox".

## Шаги реализации
1.  **conftest.py**:
    *   Реализовать фикстуру `hsm_sandbox`.
    *   Фикстура должна создавать временную папку и устанавливать `HSM_REGISTRY_PATH`.
2.  **Happy Path Test**:
    *   Создать тест, который проходит полный цикл: `init` -> `package init` -> `package add` -> `sync`.
3.  **Logic Tests**:
    *   Покрыть тестами все команды `registry` (add, remove, list, search).
    *   Покрыть тестами команды переключения режимов (`mode`).
4.  **System Validation**:
    *   Добавить проверку `docker compose config` в тесте синхронизации.

## Критерии готовности
*   `uv run pytest` проходит успешно.
*   Покрытие кода тестами (coverage) составляет не менее 90% для CLI и Core.