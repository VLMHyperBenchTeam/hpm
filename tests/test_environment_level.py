import os
import yaml
import pytest
from hyper_stack_manager.cli import app

def test_case_1_implication_merging(runner, hsm_sandbox):
    """Case 1: Shared Service (Implication Merging).
    Two packages imply the same container with different params.
    """
    # 1. Setup Registry
    # Container: postgres
    runner.invoke(app, [
        "registry", "container", "add", "postgres",
        "--image", "postgres:16-alpine",
        "--env", "POSTGRES_MULTIPLE_DATABASES=${HSM_MERGED_PARAMS.db_name}",
        "--no-input"
    ])
    
    # Package: auth-service
    # We need to manually add implies because CLI might not support it yet via arguments
    auth_path = hsm_sandbox / "hsm-registry" / "packages" / "auth-service.yaml"
    runner.invoke(app, [
        "registry", "package", "add", "auth-service",
        "--version", "1.0.0",
        "--prod-type", "git",
        "--prod-url", "https://github.com/org/auth",
        "--no-input"
    ])
    with open(auth_path, "r") as f:
        data = yaml.safe_load(f)
    data["implies"] = {"container:postgres": {"params": {"db_name": "auth_db"}}}
    with open(auth_path, "w") as f:
        yaml.dump(data, f)

    # Package: billing-service
    billing_path = hsm_sandbox / "hsm-registry" / "packages" / "billing-service.yaml"
    runner.invoke(app, [
        "registry", "package", "add", "billing-service",
        "--version", "1.0.0",
        "--prod-type", "git",
        "--prod-url", "https://github.com/org/billing",
        "--no-input"
    ])
    with open(billing_path, "r") as f:
        data = yaml.safe_load(f)
    data["implies"] = {"container:postgres": {"params": {"db_name": "billing_db"}}}
    with open(billing_path, "w") as f:
        yaml.dump(data, f)

    # 2. Setup Project
    runner.invoke(app, ["init", "--name", "shared-service-project"])
    runner.invoke(app, ["package", "add", "auth-service"])
    runner.invoke(app, ["package", "add", "billing-service"])

    # 3. Sync
    # Используем --no-verify, так как в песочнице мы проверяем логику резолвинга, а не реальное состояние системы
    result = runner.invoke(app, ["sync", "--no-verify"])
    assert result.exit_code == 0

    # 4. Validate docker-compose.hsm.yml
    compose_path = hsm_sandbox / "docker-compose.hsm.yml"
    assert compose_path.exists()
    with open(compose_path, "r") as f:
        compose_data = yaml.safe_load(f)
    
    postgres_svc = compose_data["services"]["postgres"]
    env = postgres_svc["environment"]
    # HSM_MERGED_PARAMS.db_name should be "auth_db,billing_db" or "billing_db,auth_db"
    assert "auth_db" in env["POSTGRES_MULTIPLE_DATABASES"]
    assert "billing_db" in env["POSTGRES_MULTIPLE_DATABASES"]
    assert "," in env["POSTGRES_MULTIPLE_DATABASES"]

def test_case_2_hybrid_cloud(runner, hsm_sandbox):
    """Case 2: Hybrid Cloud (Managed + External).
    One service is managed (docker), another is external (remote host).
    """
    # 1. Setup Registry
    # Container: chunker (managed)
    runner.invoke(app, [
        "registry", "container", "add", "local-chunker",
        "--image", "my-chunker:latest",
        "--no-input"
    ])
    
    # Container: qdrant (external profile)
    qdrant_path = hsm_sandbox / "hsm-registry" / "containers" / "qdrant.yaml"
    runner.invoke(app, [
        "registry", "container", "add", "qdrant",
        "--image", "qdrant/qdrant:latest",
        "--no-input"
    ])
    with open(qdrant_path, "r") as f:
        data = yaml.safe_load(f)
    data["deployment_profiles"] = {
        "external-prod": {
            "mode": "external",
            "external": {
                "host": "10.0.0.50",
                "port": 6333
            }
        }
    }
    with open(qdrant_path, "w") as f:
        yaml.dump(data, f)

    # 2. Setup Project
    runner.invoke(app, ["init", "--name", "hybrid-cloud-project"])
    
    # Add chunker to a group
    runner.invoke(app, ["registry", "group", "add", "chunker-service", "--type", "container_group", "--option", "local-chunker", "--no-input"])
    runner.invoke(app, ["group", "add", "chunker-service", "--option", "local-chunker"])
    
    # Add qdrant to a group
    runner.invoke(app, ["registry", "group", "add", "vector-db-service", "--type", "container_group", "--option", "qdrant", "--no-input"])
    runner.invoke(app, ["group", "add", "vector-db-service", "--option", "qdrant"])
    
    # Set profile for qdrant
    hsm_yaml_path = hsm_sandbox / "hsm.yaml"
    with open(hsm_yaml_path, "r") as f:
        hsm_data = yaml.safe_load(f)
    hsm_data["services"]["container_groups"]["vector-db-service"]["profile"] = "external-prod"
    with open(hsm_yaml_path, "w") as f:
        yaml.dump(hsm_data, f)

    # 3. Sync
    result = runner.invoke(app, ["sync", "--no-verify"])
    assert result.exit_code == 0

    # 4. Validate
    compose_path = hsm_sandbox / "docker-compose.hsm.yml"
    assert compose_path.exists()
    with open(compose_path, "r") as f:
        compose_data = yaml.safe_load(f)
    
    # local-chunker should be in compose
    assert "local-chunker" in compose_data["services"]
    # qdrant should NOT be in compose because it's external
    # Note: Current implementation of SyncEngine might still add it if it doesn't check profile mode.
    # Let's check SyncEngine._resolve_container_config
    # It doesn't seem to handle 'external' mode yet in the provided code.
    # If it's not implemented, this test will fail, which is good for identifying gaps.
    assert "qdrant" not in compose_data["services"]

def test_case_4_editable_stack(runner, hsm_sandbox):
    """Case 4: Editable Stack.
    Package and container from local sources.
    """
    # 1. Create local sources
    pkg_dir = hsm_sandbox / "libs" / "neo4j-client"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "pyproject.toml").write_text('[project]\nname="neo4j-client"\nversion="0.1.0"')
    
    svc_dir = hsm_sandbox / "services" / "graph-builder"
    svc_dir.mkdir(parents=True)
    (svc_dir / "Dockerfile.dev").write_text("FROM alpine")

    # 2. Setup Registry
    runner.invoke(app, [
        "registry", "package", "add", "neo4j-client",
        "--version", "0.1.0",
        "--prod-type", "local",
        "--dev-path", "libs/neo4j-client",
        "--no-input"
    ])
    
    runner.invoke(app, [
        "registry", "container", "add", "graph-builder-service",
        "--build-path", "services/graph-builder",
        "--dockerfile", "Dockerfile.dev",
        "--no-input"
    ])

    # 3. Setup Project
    runner.invoke(app, ["init", "--name", "editable-project"])
    runner.invoke(app, ["package", "add", "neo4j-client"])
    runner.invoke(app, ["package", "mode", "neo4j-client", "dev"])
    
    runner.invoke(app, ["registry", "group", "add", "graph-services", "--type", "container_group", "--option", "graph-builder-service", "--no-input"])
    runner.invoke(app, ["group", "add", "graph-services", "--option", "graph-builder-service"])
    runner.invoke(app, ["container", "mode", "graph-builder-service", "dev"])

    # 4. Sync
    result = runner.invoke(app, ["sync", "--no-verify"])
    assert result.exit_code == 0

    # 5. Validate
    # Check package requirement (should be @ file://...)
    # This is harder to check without looking at uv files, but we can check HSMCore logic
    
    # Check compose
    compose_path = hsm_sandbox / "docker-compose.hsm.yml"
    assert compose_path.exists()
    with open(compose_path, "r") as f:
        compose_data = yaml.safe_load(f)
    
    svc = compose_data["services"]["graph-builder-service"]
    assert "build" in svc
    assert "Dockerfile.dev" in svc["build"]["dockerfile"]

def test_case_5_secrets(runner, hsm_sandbox, monkeypatch):
    """Case 5: Zero-Leak Secrets.
    Interpolation of environment variables.
    """
    monkeypatch.setenv("NEO4J_PROD_PASSWORD", "secret123")
    monkeypatch.setenv("NEO4J_PROD_PORT", "7687")

    # 1. Setup Registry
    runner.invoke(app, [
        "registry", "container", "add", "graph-builder-service",
        "--image", "graph-builder:latest",
        "--port", "${NEO4J_PROD_PORT}:7474",
        "--env", "DB_PASSWORD=${NEO4J_PROD_PASSWORD}",
        "--no-input"
    ])

    # 2. Setup Project
    runner.invoke(app, ["init", "--name", "secrets-project"])
    runner.invoke(app, ["registry", "group", "add", "graph-services", "--type", "container_group", "--option", "graph-builder-service", "--no-input"])
    runner.invoke(app, ["group", "add", "graph-services", "--option", "graph-builder-service"])

    # 3. Sync
    result = runner.invoke(app, ["sync", "--no-verify"])
    assert result.exit_code == 0

    # 4. Validate
    compose_path = hsm_sandbox / "docker-compose.hsm.yml"
    assert compose_path.exists()
    with open(compose_path, "r") as f:
        compose_data = yaml.safe_load(f)
    
    svc = compose_data["services"]["graph-builder-service"]
    # If interpolation is NOT implemented, this will fail.
    # Docker Compose itself handles ${VAR} if they are in the environment when running docker compose.
    # But HSM should probably resolve them if it wants to be "Atomic Sync".
    # Actually, if we leave them as ${VAR}, docker compose will resolve them.
    assert svc["environment"]["DB_PASSWORD"] == "${NEO4J_PROD_PASSWORD}"
    assert "${NEO4J_PROD_PORT}:7474" in svc["ports"]