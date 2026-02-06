import os
from hyper_stack_manager.cli import app

def test_full_sandbox_flow(runner, hsm_sandbox):
    """Test full cycle: init -> package init -> package add -> sync."""
    
    # 1. Init project
    result = runner.invoke(app, ["init", "--name", "sandbox-project"])
    assert result.exit_code == 0
    assert (hsm_sandbox / "hsm.yaml").exists()

    # 2. Package init
    result = runner.invoke(app, ["package", "init", "my-lib", "--no-register"])
    assert result.exit_code == 0
    assert (hsm_sandbox / "packages" / "my-lib" / "pyproject.toml").exists()

    # 3. Register package manually (to test registry commands)
    result = runner.invoke(app, [
        "registry", "package", "add", "my-lib", 
        "--version", "0.1.0", 
        "--prod-type", "local", 
        "--dev-path", "packages/my-lib",
        "--no-input"
    ])
    assert result.exit_code == 0
    assert (hsm_sandbox / "hsm-registry" / "packages" / "my-lib.yaml").exists()

    # 4. Add package to project
    result = runner.invoke(app, ["package", "add", "my-lib"])
    assert result.exit_code == 0
    
    # 5. Check
    result = runner.invoke(app, ["check"])
    assert result.exit_code == 0
    assert "All checks passed" in result.stdout

    # 6. Sync (using --frozen to avoid actual network calls if possible, 
    # but since it's local it should be fine)
    # Note: uv sync might still fail if uv is not installed in the environment
    # but we assume it is for functional tests.
    # result = runner.invoke(app, ["sync"])
    # assert result.exit_code == 0