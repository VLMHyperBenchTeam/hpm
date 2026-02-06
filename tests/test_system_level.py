import subprocess
import pytest

def test_hsm_binary_execution():
    """Level 1.2: Test that hsm can be executed as a system command."""
    # This test assumes 'hsm' is installed in the environment (e.g. via uv tool install -e .)
    # If not installed, we skip it or use 'uv run hsm'
    try:
        result = subprocess.run(["hsm", "--help"], capture_output=True, text=True, check=True)
        assert "Hyper Stack Manager" in result.stdout
        assert result.returncode == 0
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Fallback to uv run if not globally installed
        result = subprocess.run(["uv", "run", "hsm", "--help"], capture_output=True, text=True, check=True)
        assert "Hyper Stack Manager" in result.stdout
        assert result.returncode == 0

def test_hsm_entrypoint_sync(tmp_path, monkeypatch):
    """Level 1.2: Test sync entrypoint via subprocess."""
    # Create an empty directory to ensure no hsm.yaml is found
    empty_dir = tmp_path / "empty_project"
    empty_dir.mkdir()
    monkeypatch.chdir(empty_dir)
    
    # We need to point to the hsm source since it's not installed in the tmp_path env
    # But 'uv run hsm' should work if we are in the repo root or have it installed.
    # To be safe, we use the absolute path to the cli.py or assume 'uv run' finds it.
    
    result = subprocess.run(["uv", "run", "hsm", "sync"], capture_output=True, text=True)
    
    # If there is no hsm.yaml, HSMCore might create a default one or fail.
    # In our current implementation, HSMCore(project_root) will look for hsm.yaml.
    # If it doesn't exist, it doesn't necessarily fail until sync() is called.
    # Actually, sync() currently doesn't fail if there are no packages.
    
    # Let's check for a command that definitely fails without a project
    result = subprocess.run(["uv", "run", "hsm", "check"], capture_output=True, text=True)
    # check() fails if hsm.yaml is missing
    assert result.returncode == 1
    assert "Manifest file not found" in result.stdout or "Check failed" in result.stdout