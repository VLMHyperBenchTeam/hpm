from hyper_stack_manager.cli import app

def test_help(runner):
    """Test that --help works and shows basic info."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Hyper Stack Manager" in result.stdout

def test_init_basic(runner, tmp_path, monkeypatch):
    """Test basic project initialization."""
    project_dir = tmp_path / "new_project"
    project_dir.mkdir()

    # Change directory to project_dir
    monkeypatch.chdir(project_dir)

    # Run init command
    # Note: init might be interactive, so we provide input if needed
    result = runner.invoke(app, ["init", "--name", "test-project"])

    assert result.exit_code == 0
    assert (project_dir / "hsm.yaml").exists()