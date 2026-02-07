# Task: Рефакторинг моделей и структуры реестра (ADR-002)

## Контекст
Согласно ADR-002, нам необходимо перейти от технологического разделения (пакеты/контейнеры) к функциональному (библиотеки/сервисы) и добавить поддержку рантаймов. Проект находится в стадии Alpha, поэтому обратная совместимость со старыми именами секций не требуется.

## Шаги реализации
1.  **Models (`src/hyper_stack_manager/models.py`)**:
    - [ ] Добавить `RuntimeType` (Enum: docker, podman, uv, pixi, venv).
    - [ ] Переименовать `PackageManifest` -> `LibraryManifest`.
    - [ ] Переименовать `ContainerManifest` -> `ServiceManifest`.
    - [ ] Обновить `DeploymentProfile`: добавить `runtime`, `command`, `path`.
2.  **Manifest (`src/hyper_stack_manager/manifest.py`)**:
    - [ ] Обновить парсинг `hsm.yaml` для поддержки новой секции `services.groups` и `services.standalone`.
    - [ ] Удалить поддержку старых секций (`container_groups`, `packages` в старом формате).
3.  **Registry Structure**:
    - [ ] Обновить `RegistryManager` для работы с новыми папками: `libraries/`, `services/`, `library_groups/`, `service_groups/`.
4.  **CLI**:
    - [ ] Обновить команду `hsm list` для отображения рантаймов сервисов.

## Критерии готовности
- [ ] Все тесты `tests/test_registry_logic.py` проходят (после обновления под новую структуру).
- [ ] `hsm list` корректно отображает дерево проекта с учетом новых имен секций.

## Отчет о реализации
*(Заполняется инстансом после завершения задачи)*
- **Что сделано**: ...
- **Как реализовано**: ...
- **Отклонения от плана**: ...
