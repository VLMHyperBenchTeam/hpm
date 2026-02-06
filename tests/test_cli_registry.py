import pytest
from hyper_stack_manager.cli import app
from pathlib import Path

def test_registry_list_empty(runner, tmp_path):
    """Test listing registry when it's empty."""
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir()
    
    result = runner.invoke(app, ["registry", "list", "--registry", str(registry_dir)])
    assert result.exit_code == 0
    assert "HSM Global Registry" in result.stdout

def test_registry_package_add_no_input(runner, tmp_path):
    """Test adding a package to registry in no-input mode."""
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir()
    
    result = runner.invoke(app, [
        "registry", "package", "add", "test-pkg",
        "--version", "1.2.3",
        "--description", "Test description",
        "--prod-type", "git",
        "--prod-url", "https://github.com/test/test.git",
        "--no-input",
        "--registry", str(registry_dir)
    ])
    
    assert result.exit_code == 0
    assert "Package 'test-pkg' added to registry" in result.stdout
    assert (registry_dir / "packages" / "test-pkg.yaml").exists()

def test_registry_search(runner, tmp_path):
    """Test searching in registry."""
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir()
    pkg_dir = registry_dir / "packages"
    pkg_dir.mkdir()
    (pkg_dir / "my-cool-pkg.yaml").write_text("name: my-cool-pkg")
    
    result = runner.invoke(app, ["registry", "search", "cool", "--registry", str(registry_dir)])
    assert result.exit_code == 0
    assert "my-cool-pkg" in result.stdout

def test_registry_show(runner, tmp_path):
    """Test showing component details."""
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir()
    pkg_dir = registry_dir / "packages"
    pkg_dir.mkdir()
    (pkg_dir / "test-show.yaml").write_text("name: test-show\nversion: 1.0.0")
    
    result = runner.invoke(app, ["registry", "show", "test-show", "--registry", str(registry_dir)])
    assert result.exit_code == 0
    assert "test-show" in result.stdout
    assert "1.0.0" in result.stdout

def test_registry_package_remove(runner, tmp_path):
    """Test removing a package from registry."""
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir()
    pkg_dir = registry_dir / "packages"
    pkg_dir.mkdir()
    pkg_file = pkg_dir / "to-remove.yaml"
    pkg_file.write_text("name: to-remove")
    
    result = runner.invoke(app, ["registry", "package", "remove", "to-remove", "--yes", "--registry", str(registry_dir)])
    assert result.exit_code == 0
    assert "Package 'to-remove' removed from registry" in result.stdout
    assert not pkg_file.exists()

def test_registry_group_add_no_input(runner, tmp_path):
    """Test adding a group to registry."""
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir()
    
    result = runner.invoke(app, [
        "registry", "group", "add", "test-group",
        "--type", "package_group",
        "--strategy", "1-of-N",
        "--option", "opt1",
        "--option", "opt2",
        "--no-input",
        "--registry", str(registry_dir)
    ])
    
    assert result.exit_code == 0
    assert "Group 'test-group' added to registry" in result.stdout
    assert (registry_dir / "package_groups" / "test-group.yaml").exists()

def test_registry_container_add_no_input(runner, tmp_path):
    """Test adding a container to registry."""
    registry_dir = tmp_path / "registry"
    registry_dir.mkdir()
    
    result = runner.invoke(app, [
        "registry", "container", "add", "test-cont",
        "--image", "nginx:latest",
        "--port", "80:80",
        "--no-input",
        "--registry", str(registry_dir)
    ])
    
    assert result.exit_code == 0
    assert "Container 'test-cont' added to registry" in result.stdout
    assert (registry_dir / "containers" / "test-cont.yaml").exists()