# Задача: Реализация адаптера для Pixi

## Контекст
Необходимо добавить поддержку пакетного менеджера Pixi в качестве альтернативы uv.

## Шаги реализации
1.  Создать файл `hsm/src/hyper_stack_manager/adapters/python_pixi.py`.
2.  Реализовать класс `PixiAdapter`, наследующийся от `BasePackageManagerAdapter`.
3.  Реализовать методы:
    - `sync(packages, frozen)`: Вызов `pixi add` или прямая правка `pixi.toml` + `pixi install`.
    - `lock()`: Вызов `pixi lock`.
    - `init_lib(path)`: Вызов `pixi init`.
4.  Зарегистрировать адаптер в `hsm/pyproject.toml` в секции `entry-points`.

## Критерии готовности
- Команда `hsm python-manager set pixi` работает.
- Команда `hsm sync` корректно вызывает `pixi`.