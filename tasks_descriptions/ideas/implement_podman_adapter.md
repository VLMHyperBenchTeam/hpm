# Idea: Реализация адаптера для Podman

## Суть
Добавить поддержку Podman в качестве альтернативы Docker для оркестрации контейнеров.

## Контекст
Podman является популярной бездемонной альтернативой Docker, особенно в корпоративных средах. HSM должен поддерживать его через систему адаптеров.

## Реализация
1.  Создать файл `src/hyper_stack_manager/adapters/container_podman.py`.
2.  Реализовать класс `PodmanAdapter`, наследующийся от `BaseContainerAdapter`.
3.  Реализовать методы:
    - `generate_config(services)`: Генерация YAML-манифеста.
    - `up(services)`: Вызов `podman-compose up`.
    - `down()`: Вызов `podman-compose down`.
4.  Зарегистрировать адаптер в `pyproject.toml` в секции `entry-points`.