# Руководство пользователя HSM: Управление Стеком

**hsm (Hyper Stack Manager)** — это инструмент для декларативного управления окружением проекта, объединяющий Python-пакеты и Docker-сервисы.

## 1. Манифест hsm.yaml
Файл `hsm.yaml` в корне вашего проекта описывает желаемое состояние стека.

```yaml
project:
  name: "my-rag-app"

# Группы Python-пакетов
dependencies:
  package_groups:
    vector-db:
      strategy: 1-of-N
      selection: qdrant-adapter
      mode: dev

# Группы Docker-сервисов
services:
  container_groups:
    infra:
      strategy: M-of-N
      selection: ["postgres", "redis"]
      mode: prod
```

## 2. Команды управления проектом

### hsm init
Инициализирует новый проект, создавая `hsm.yaml` на основе существующего `pyproject.toml`.

### hsm sync
Материализует намерения из `hsm.yaml` в реальные конфиги и окружение.
*   Обновляет `pyproject.toml`.
*   Генерирует `docker-compose.hsm.yml`.
*   Вызывает `uv sync`.
*   **Транзакционность**: Если синхронизация не удалась, HSM откатит изменения в `pyproject.toml`.

### hsm list
Показывает текущий состав вашего стека: активные группы, пакеты и их режимы.

## 3. Редактирование стека

### hsm add / hsm remove
Позволяют быстро добавлять или удалять компоненты из манифеста.
```bash
hsm add qdrant-adapter # Добавит пакет в корень манифеста
hsm add group vector-db --option qdrant-adapter # Добавит в группу
```

### hsm mode
Глобальное переключение режима для всего проекта.
```bash
hsm mode dev
```

### hsm package mode / hsm container mode
Атомарное переключение режима для конкретного пакета или сервиса.
```bash
hsm package mode qdrant-adapter dev
hsm container mode postgres prod
```

## 4. Работа с Реестром
Реестр — это база знаний о доступных компонентах.

### hsm registry search <query>
Поиск пакетов, контейнеров и групп в глобальном реестре.

### hsm registry show <name>
Просмотр детальной информации о компоненте (источники, версии, зависимости).

## 5. Командная работа и CI/CD
Для воспроизводимости в CI/CD используйте:
```bash
hsm sync --frozen
```
Это гарантирует, что окружение будет собрано строго по зафиксированным версиям без попыток обновления.