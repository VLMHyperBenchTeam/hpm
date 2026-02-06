import yaml
from hyper_stack_manager.cli import app

def test_registry_package_crud(runner, hsm_sandbox):
    """Test adding and removing packages from registry."""
    # Add package
    result = runner.invoke(app, [
        "registry", "package", "add", "test-pkg",
        "--version", "1.2.3",
        "--prod-type", "git",
        "--prod-url", "https://github.com/test/test",
        "--no-input"
    ])
    assert result.exit_code == 0
    
    pkg_yaml = hsm_sandbox / "hsm-registry" / "packages" / "test-pkg.yaml"
    assert pkg_yaml.exists()
    
    with open(pkg_yaml) as f:
        data = yaml.safe_load(f)
        assert data["name"] == "test-pkg"
        assert data["version"] == "1.2.3"

    # Search
    result = runner.invoke(app, ["registry", "search", "test"])
    assert result.exit_code == 0
    assert "test-pkg" in result.stdout

    # Remove
    result = runner.invoke(app, ["registry", "package", "remove", "test-pkg", "--yes"])
    assert result.exit_code == 0
    assert not pkg_yaml.exists()

def test_registry_group_logic(runner, hsm_sandbox):
    """Test group management in registry."""
    # Add group
    result = runner.invoke(app, [
        "registry", "group", "add", "db-group",
        "--type", "package_group",
        "--strategy", "1-of-N",
        "--option", "pg-client",
        "--option", "mysql-client",
        "--no-input"
    ])
    assert result.exit_code == 0
    
    group_yaml = hsm_sandbox / "hsm-registry" / "package_groups" / "db-group.yaml"
    assert group_yaml.exists()

    # Add option to group
    result = runner.invoke(app, ["registry", "group", "add-option", "db-group", "sqlite-client"])
    assert result.exit_code == 0
    
    with open(group_yaml) as f:
        data = yaml.safe_load(f)
        options = [opt["name"] for opt in data["options"]]
        assert "sqlite-client" in options