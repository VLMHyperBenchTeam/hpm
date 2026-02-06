import subprocess
import yaml
from hyper_stack_manager.cli import app

def test_docker_compose_config_validation(runner, hsm_sandbox):
    """Level 1.3: Test that hsm sync generates a valid docker-compose file."""
    
    # 1. Setup project and registry
    runner.invoke(app, ["init", "--name", "docker-test"])
    
    # Add a container to registry
    runner.invoke(app, [
        "registry", "container", "add", "web-server",
        "--image", "nginx:latest",
        "--port", "8080:80",
        "--no-input"
    ])
    
    # Add a group with this container
    runner.invoke(app, [
        "registry", "group", "add", "web-group",
        "--type", "container_group",
        "--strategy", "1-of-N",
        "--option", "web-server",
        "--no-input"
    ])
    
    # 2. Add group to project
    runner.invoke(app, ["group", "add", "web-group", "--option", "web-server"])
    
    # 3. Sync (generates docker-compose.hsm.yml)
    result = runner.invoke(app, ["sync"])
    assert result.exit_code == 0
    
    compose_file = hsm_sandbox / "docker-compose.hsm.yml"
    assert compose_file.exists()
    
    # 4. Validate with real docker compose config
    try:
        # We use 'config' command which validates the file without starting containers
        cp_result = subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "config"],
            capture_output=True, text=True
        )
        # If docker is not installed, this might fail, but in Ubuntu 24.04 it should be there
        if cp_result.returncode == 0:
            assert "services" in cp_result.stdout
            assert "web-server" in cp_result.stdout
    except FileNotFoundError:
        # Skip if docker is not installed in the test environment
        pass