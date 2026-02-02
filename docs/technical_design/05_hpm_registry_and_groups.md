# Technical Design: HPM Registry & Group Management

Этот документ переопределяет роль HPM на основе обратной связи: HPM не разрешает зависимости (это делает `uv`), а управляет **составом** этих зависимостей на основе высокоуровневых абстракций (Группы, Виртуальные пакеты).

## 1. Концепция

HPM работает как **Configuration Generator** для `uv`.
1.  **Registry**: База знаний о доступных пакетах и их группах.
2.  **Project Manifest**: Декларация желаемого состояния ("Хочу группу `inference` с реализацией `vllm`").
3.  **Output**: Команда `uv add pkg1 pkg2 ...` или генерация `pyproject.toml`.

## 2. Структура Реестра (Registry Layout)

Реестр — это директория с манифестами.

```yaml
# registry/groups/inference.yaml
name: "inference"
type: "group"
strategy: "1-of-N" # Mutually exclusive (Virtual Package)
options:
  - name: "vlm-adapter-qwen"
  - name: "vlm-adapter-deepseek"
  - name: "vllm-backend"

# registry/groups/metrics.yaml
name: "metrics"
type: "group"
strategy: "M-of-N" # Feature set
default: ["accuracy", "latency"]
options:
  - name: "metric-accuracy"
  - name: "metric-latency"
  - name: "metric-bleu"
```

## 3. CLI Workflow

### 3.1. Инициализация группы
```bash
hpm group add inference --option vlm-adapter-qwen
```
*   **Действие:** HPM читает `registry/groups/inference.yaml`.
*   **Проверка:** Убеждается, что `vlm-adapter-qwen` является валидной опцией для этой группы.
*   **Результат:** Обновляет `hpm.lock` (или секцию в `pyproject.toml`):
    ```toml
    [tool.hpm.groups]
    inference = "vlm-adapter-qwen"
    ```

### 3.2. Синхронизация (Materialization)
```bash
hpm sync
```
*   **Действие:**
    1.  Читает текущую конфигурацию (`tool.hpm.groups`).
    2.  Резолвит конкретные пакеты (находит их `git` url или локальный путь в реестре).
    3.  Формирует список зависимостей для `uv`.
    4.  Вызывает `uv add package1 @ git+... package2 @ path/to/local`.

## 4. Преимущества подхода
1.  **Делегирование сложности:** `uv` сам разрулит конфликты версий `numpy` между `package1` и `package2`.
2.  **Абстракция:** Пользователь оперирует понятиями "Инференс", а не списком из 50 библиотек.
3.  **Гибкость:** Легко переключить `inference = "vlm-adapter-deepseek"` и сделать `hpm sync`, чтобы полностью сменить бэкенд.

## 5. План реализации (Revised)
1.  **Registry Parser**: Чтение `groups/*.yaml`.
2.  **Config Manager**: Чтение/Запись `[tool.hpm]` в `pyproject.toml`.
3.  **UV Driver**: Генерация команд `uv add` на основе конфига.