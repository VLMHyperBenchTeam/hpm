from .root import app
from .registry import registry_app
from .project import package_app, group_app, container_app, python_manager_app

# Register sub-apps
app.add_typer(registry_app, name="registry")
app.add_typer(package_app, name="package")
app.add_typer(group_app, name="group")
app.add_typer(container_app, name="container")
app.add_typer(python_manager_app, name="python-manager")

__all__ = ["app"]