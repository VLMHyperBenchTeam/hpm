# Задача: Реализация адаптера для Podman

## Контекст
Необходимо добавить поддержку Podman в качестве альтернативы Docker для оркестрации контейнеров.

## Шаги реализации
1.  Создать файл `hsm/src/hyper_stack_manager/adapters/container_podman.py`.
2.  Реализовать класс `PodmanAdapter`, наследующийся от `BaseContainerAdapter`.
3.  Реализовать методы:
    - `generate_config(services)`: Генерация YAML-манифеста.
    - `up(services)`: Вызов `podman-compose up`.
    - `down()`: Вызов `podman-compose down`.
4.  Зарегистрировать адаптер в `hsm/pyproject.toml` в секции `entry-points`.

## Критерии готовности
- Команда `hsm sync` работает при выборе `container_engine: podman` в `hsm.yaml`.