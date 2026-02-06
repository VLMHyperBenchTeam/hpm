import pytest
from pathlib import Path
from typer.testing import CliRunner

@pytest.fixture
def runner():
    """Fixture for Typer CliRunner."""
    return CliRunner()

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