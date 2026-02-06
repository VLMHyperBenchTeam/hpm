# Technical Design: Сложные кейсы конфигурации HSM

Этот документ описывает продвинутые сценарии использования HSM, демонстрирующие гибкость системы при работе с инфраструктурой и зависимостями.

## Кейс 1: "Один на всех" (Shared Service)

Сценарий, когда несколько компонентов системы используют один и тот же физический или логический ресурс.

### 1.1. Слияние в Managed режиме (Shared Container)
**Проблема**: Несколько пакетов требуют одну и ту же СУБД. Мы хотим запустить один контейнер, но создать в нем разные базы.

```mermaid
graph TD
    subgraph Project [1. hsm.yaml]
        PkgA[Package: auth-service]
        PkgB[Package: billing-service]
    end
    
    subgraph Registry [2. HSM Registry]
        PkgA -->|implies| DB[Service: Postgres]
        PkgB -->|implies| DB
        
        DB -.->|params| P1[db_name: auth]
        DB -.->|params| P2[db_name: billing]
    end
    
    subgraph HSM_Core [3. HSM Core: Implication Merging]
        Merged[Merged Config: DB_LIST=auth,billing]
    end
    
    subgraph Runtime [4. Environment]
        Docker[Single Container: Postgres]
    end
    
    Merged -->|generates| Docker
```

### 1.2. Общий доступ в External режиме (Shared Remote DB)
**Проблема**: Много пакетов должны подключиться к одной удаленной БД, параметры которой описаны в реестре.

```mermaid
graph TD
    subgraph Project [1. hsm.yaml]
        PkgA[Package A]
        PkgB[Package B]
        Profile[Profile: external-corp]
    end
    
    subgraph Registry [2. HSM Registry]
        Profile --> ExtConfig[Host: 10.0.0.50, Port: 5432]
    end
    
    subgraph Runtime [3. Environment]
        EnvA[ENV for Pkg A: DB_HOST=10.0.0.50]
        EnvB[ENV for Pkg B: DB_HOST=10.0.0.50]
        RemoteDB[(Remote Postgres Server)]
    end
    
    ExtConfig --> EnvA
    ExtConfig --> EnvB
    EnvA -->|connects| RemoteDB
    EnvB -->|connects| RemoteDB
```

---

## Кейс 2: "Гибридное облако" (Hybrid BYOI)

**Проблема**: Разработчик хочет использовать локальный Chunker (в Docker), но подключаться к мощной векторной БД в облаке (External).

```mermaid
graph TD
    subgraph Project [hsm.yaml]
        Chunker[Service: Chunker]
        VectorDB[Service: Vector DB]
    end
    
    subgraph Profiles [Registry Profiles]
        Managed[Profile: managed-dev]
        External[Profile: external-prod]
    end
    
    Chunker -->|uses| Managed
    VectorDB -->|uses| External
    
    subgraph Runtime [Environment]
        LocalDocker[Local Docker: Chunker Container]
        CloudDB[(Cloud: Qdrant Managed Service)]
    end
    
    Managed -->|starts| LocalDocker
    External -->|injects connection to| CloudDB
```

---

## Кейс 3: "Симметричная разработка" (Editable Stack)

**Проблема**: Нужно одновременно вносить изменения в два зависимых пакета (например, в ядро системы и в плагин).

**Решение**: Использование **Editable Sources** в реестре. При выполнении `hsm sync`, HSM (через `uv`) установит пакет как ссылку на локальную папку. Любое изменение кода мгновенно отразится на работе всего стэка.

---

## Кейс 4: "Секреты без утечек" (Zero-Leak Secrets)

**Проблема**: Нужно передать API ключи в контейнеры и пакеты, не сохраняя их в Git.

**Решение**: **Variable Interpolation**. HSM считывает значение из системного окружения или `.env` файла в момент синхронизации (`${MY_SECRET}`). В YAML-файлах остаются только ссылки.