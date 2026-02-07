from .root import app
from .registry import registry_app
from .project import library_app, group_app, service_app, python_manager_app

# Register sub-apps
app.add_typer(registry_app, name="registry")
app.add_typer(library_app, name="library")
app.add_typer(group_app, name="group")
app.add_typer(service_app, name="service")
app.add_typer(python_manager_app, name="python-manager")

__all__ = ["app"]