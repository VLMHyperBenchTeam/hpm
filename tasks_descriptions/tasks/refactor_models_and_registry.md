# Task: Рефакторинг моделей и структуры реестра (ADR-002)

## Контекст
Согласно ADR-002, нам необходимо перейти от технологического разделения (пакеты/контейнеры) к функциональному (библиотеки/сервисы) и добавить поддержку рантаймов. Проект находится в стадии Alpha, поэтому обратная совместимость со старыми именами секций не требуется.

## Шаги реализации
1.  **Models (`src/hyper_stack_manager/models.py`)**:
    - [x] Добавить `RuntimeType` (Enum: docker, podman, uv, pixi, venv).
    - [x] Переименовать `PackageManifest` -> `LibraryManifest`.
    - [x] Переименовать `ContainerManifest` -> `ServiceManifest`.
    - [x] Обновить `DeploymentProfile`: добавить `runtime`, `command`, `path`.
2.  **Manifest (`src/hyper_stack_manager/manifest.py`)**:
    - [x] Обновить парсинг `hsm.yaml` для поддержки новой секции `services.groups` и `services.standalone`.
    - [x] Удалить поддержку старых секций (`container_groups`, `packages` в старом формате).
3.  **Registry Structure**:
    - [x] Обновить `RegistryManager` для работы с новыми папками: `libraries/`, `services/`, `library_groups/`, `service_groups/`.
4.  **CLI**:
    - [x] Обновить команду `hsm list` для отображения рантаймов сервисов.

## Критерии готовности
- [x] Все тесты `tests/test_registry_logic.py` проходят (после обновления под новую структуру).
- [x] `hsm list` корректно отображает дерево проекта с учетом новых имен секций.

## Отчет о реализации
- **Что сделано**: Полный рефакторинг моделей данных, логики манифеста и менеджера реестра для перехода на архитектуру VES (ADR-002).
- **Как реализовано**:
    - В `models.py` внедрен `RuntimeType` и обновлены основные манифесты.
    - В `manifest.py` реализована поддержка иерархии `libraries` и `services`.
    - `RegistryManager`, `SyncEngine` и `Validator` обновлены для работы с новыми путями реестра.
    - CLI команды переименованы для соответствия функциональному разделению (library/service).
- **Отклонения от плана**: Нет. Все пункты выполнены согласно ADR-002.
