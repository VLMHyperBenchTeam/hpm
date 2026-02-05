# Задача: Рефакторинг адаптеров HSM

## Контекст
Текущая реализация адаптеров находится в `hsm/src/hyper_stack_manager/adapters.py`. Логика Docker частично смешана с `core.py`. Нужно провести разделение согласно плану в `hsm/docs/plans/adapter_abstraction.md`.

## Шаги реализации
1. **Создать структуру**:
   - `hsm/src/hyper_stack_manager/adapters/base.py` (абстрактные классы).
   - `hsm/src/hyper_stack_manager/adapters/python_uv.py`.
   - `hsm/src/hyper_stack_manager/adapters/container_docker.py`.
2. **Перенос логики**:
   - Перенести `UvAdapter` в новый файл.
   - Вынести логику генерации Compose из `core.py` в `DockerComposeAdapter`.
3. **Обновление Core**:
   - Реализовать `AdapterFactory` для динамической загрузки.
   - Обновить `HSMCore.__init__` для инициализации обоих типов адаптеров.
4. **Тестирование**:
   - Выполнить `hsm sync` в проекте `rag4code` и убедиться, что артефакты генерируются корректно.

## Ожидаемый результат
Код `core.py` очищен от специфики инструментов, вся работа с внешними командами делегирована адаптерам.