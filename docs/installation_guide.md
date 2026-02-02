# HPM Installation Guide

Этот документ описывает способы установки **Hyper Package Manager (HPM)** для различных сценариев.

## 1. Режим разработки (Editable Install)

Используйте этот метод, если вы планируете вносить изменения в сам код HPM. В этом режиме изменения в исходном коде HPM будут мгновенно отражаться на работе команды `hpm` без необходимости переустановки.

### Установка через uv (рекомендуется)
```bash
# Из корня репозитория, где находится папка hpm/
uv pip install -e ./hpm
```

### Проверка
```bash
hpm --help
```

## 2. Режим эксплуатации (Remote Install)

Используйте этот метод для установки стабильной версии HPM в ваш проект напрямую из репозитория GitHub.

### Установка через uv
```bash
uv pip install git+https://github.com/VLMHyperBenchTeam/hpm.git
```

### Установка конкретной версии (тега)
```bash
uv pip install git+https://github.com/VLMHyperBenchTeam/hpm.git@v0.1.0
```

## 3. Использование через uv run (без установки)

Если вы не хотите устанавливать HPM в окружение, вы можете запускать его напрямую:

```bash
uv run --path ./hpm/src/hyper_package_manager/cli.py --help
```

Или, если вы добавили entry point в `hpm/pyproject.toml`, вы можете запускать его как модуль, если пакет находится в `PYTHONPATH`.