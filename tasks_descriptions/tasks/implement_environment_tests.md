# Task: Реализация Environment Level тестов

## Контекст
Необходимо реализовать тесты для `website/docs/core-concepts/complex-configurations.md`. Текущая реализация содержит баги в ядре и требует перехода на Real-World Testing.

## Шаги реализации

### 1. Исправление багов Core (Priority: High)
*   [ ] **Manifest Fix**: Модифицировать `HSMProjectManifest.packages`, чтобы он всегда возвращал список строк (имен), даже если в YAML пакеты заданы как словари с метаданными.
*   [ ] **Models Update**: Добавить поддержку `deployment_profiles` в `ContainerManifest`.
*   [ ] **SyncEngine Fix**: Реализовать учет `mode: external` в `_resolve_container_config`. Если профиль внешний — контейнер не должен попадать в `docker-compose`.

### 2. Обновление инфраструктуры тестов
*   [ ] **GitHub Integration**: Использовать реальные репозитории из организации `hsm-testing-components` для prod-версий пакетов.
*   [ ] **External Simulation**: В тестах для `external` режима реализовать запуск "фейкового" сервиса (например, `python -m http.server` или `nc`) для проверки доступности.

### 3. Реализация тестовых сценариев (`tests/test_environment_level.py`)
*   [ ] **Case 1 (Shared)**: Implication Merging + проверка через `Inspector.get_installed_packages()`.
*   [ ] **Case 2 (Hybrid Cloud)**: Проверка отсутствия внешнего контейнера в конфиге + симуляция внешнего сервиса.
*   [ ] **Case 3 (Hybrid Stack)**: Смешивание реального GitHub репозитория и локального пакета.
*   [ ] **Case 4 (Editable)**: Проверка установки в режиме редактирования.
*   [ ] **Case 5 (Secrets)**: Проверка интерполяции переменных окружения.

## Критерии готовности
- [ ] Все баги в Core исправлены.
- [ ] Все 5 кейсов проходят успешно в реальном окружении.
- [ ] Тесты используют `EnvironmentInspector` для валидации (вместо ручного парсинга YAML).