import pytest
import os
from pathlib import Path
from typer.testing import CliRunner

@pytest.fixture
def runner():
    """Fixture for Typer CliRunner."""
    return CliRunner()

@pytest.fixture
def hsm_sandbox(tmp_path, monkeypatch):
    """Fixture to create a temporary HSM sandbox with isolated registry."""
    sandbox_dir = tmp_path / "hsm_sandbox"
    sandbox_dir.mkdir()
    
    registry_dir = sandbox_dir / "hsm-registry"
    registry_dir.mkdir()
    
    # Set environment variable for isolated registry
    monkeypatch.setenv("HSM_REGISTRY_PATH", str(registry_dir))
    
    # Change directory to sandbox
    monkeypatch.chdir(sandbox_dir)
    
    return sandbox_dir

@pytest.fixture
def temp_project(tmp_path):
    """Fixture to create a temporary HSM project structure."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    
    # Create a basic hsm.yaml
    hsm_yaml = project_dir / "hsm.yaml"
    hsm_yaml.write_text("""
project:
  name: test_project
  manager: uv
""")
    
    return project_dir