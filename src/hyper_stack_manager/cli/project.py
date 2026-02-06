import typer
from pathlib import Path
from typing import Optional
from ..core.engine import HSMCore
from .utils import (
    console,
    complete_registry_packages,
    complete_registry_containers,
    complete_project_groups,
    complete_project_containers
)

package_app = typer.Typer(help="Manage packages in the current project")
group_app = typer.Typer(help="Manage groups in the current project")
container_app = typer.Typer(help="Manage containers in the current project")
python_manager_app = typer.Typer(help="Manage python package manager settings")

# --- Project Package Commands ---

@package_app.command(name="add")
def project_package_add(
    name: str = typer.Argument(..., help="Package name", autocompletion=complete_registry_packages),
    group: Optional[str] = typer.Option(None, "--group", "-g"),
):
    """Add a package to the project."""
    hsm = HSMCore()
    try:
        if group:
            hsm.add_package_group(group, name)
        else:
            hsm.add_package(name)
        console.print(f"[green]Added package '{name}' to project. Run 'hsm sync' to apply.[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

@package_app.command(name="remove")
def project_package_remove(
    name: str = typer.Argument(..., help="Package name"),
    group: Optional[str] = typer.Option(None, "--group", "-g"),
):
    """Remove a package from the project."""
    hsm = HSMCore()
    try:
        if group:
            hsm.remove_package_group(group, name)
        else:
            hsm.remove_package(name)
        console.print(f"[green]Removed package '{name}' from project. Run 'hsm sync' to apply.[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

@package_app.command(name="mode")
def project_package_mode(
    name: str = typer.Argument(..., help="Package name"),
    mode: str = typer.Argument(..., help="Mode (dev/prod)"),
):
    """Set mode for a specific package."""
    hsm = HSMCore()
    try:
        hsm.set_package_mode(name, mode)
        console.print(f"[green]Mode for '{name}' set to {mode}. Run 'hsm sync' to apply.[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

@package_app.command(name="init")
def project_package_init(
    name: str = typer.Argument(..., help="Package name"),
    path: Optional[Path] = typer.Option(None, "--path", "-p", help="Path to create the package"),
    register: bool = typer.Option(True, "--register/--no-register", help="Automatically register in registry"),
):
    """Initialize a new package in the project."""
    hsm = HSMCore()
    try:
        hsm.init_package(name, path=path, register=register)
        console.print(f"[green]Package '{name}' initialized successfully.[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

# --- Project Group Commands ---

@group_app.command(name="add")
def project_group_add(
    name: str = typer.Argument(..., help="Group name"),
    option: str = typer.Option(..., "--option", "-o"),
):
    """Add a group to the project."""
    hsm = HSMCore()
    try:
        hsm.add_package_group(name, option)
        console.print(f"[green]Added group '{name}' with selection '{option}'. Run 'hsm sync' to apply.[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

@group_app.command(name="remove")
def project_group_remove(
    name: str = typer.Argument(..., help="Group name", autocompletion=complete_project_groups),
):
    """Remove a group from the project."""
    hsm = HSMCore()
    try:
        hsm.remove_group(name)
        console.print(f"[green]Removed group '{name}' from project. Run 'hsm sync' to apply.[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

@group_app.command(name="add-option")
def project_group_add_option(
    group: str = typer.Argument(..., help="Group name", autocompletion=complete_project_groups),
    option: str = typer.Argument(..., help="Option name"),
):
    """Add an option to a project group."""
    hsm = HSMCore()
    try:
        hsm.add_group_option(group, option)
        console.print(f"[green]Added option '{option}' to group '{group}'. Run 'hsm sync' to apply.[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

@group_app.command(name="remove-option")
def project_group_remove_option(
    group: str = typer.Argument(..., help="Group name", autocompletion=complete_project_groups),
    option: str = typer.Argument(..., help="Option name"),
):
    """Remove an option from a project group."""
    hsm = HSMCore()
    try:
        hsm.remove_group_option(group, option)
        console.print(f"[green]Removed option '{option}' from group '{group}'. Run 'hsm sync' to apply.[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

# --- Project Container Commands ---

@container_app.command(name="add")
def project_container_add(
    name: str = typer.Argument(..., help="Container name", autocompletion=complete_registry_containers),
    group: Optional[str] = typer.Option(None, "--group", "-g"),
):
    """Add a container to the project."""
    hsm = HSMCore()
    try:
        if group:
            hsm.add_package_group(group, name)
        else:
            console.print("[yellow]Adding standalone containers is not fully supported yet. Please use groups.[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

@container_app.command(name="remove")
def project_container_remove(
    name: str = typer.Argument(..., help="Container name", autocompletion=complete_project_containers),
    group: Optional[str] = typer.Option(None, "--group", "-g"),
):
    """Remove a container from the project."""
    hsm = HSMCore()
    try:
        if group:
            hsm.remove_package_group(group, name)
        else:
             console.print("[yellow]Removing standalone containers is not fully supported yet.[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

@container_app.command(name="mode")
def project_container_mode(
    name: str = typer.Argument(..., help="Container name", autocompletion=complete_project_containers),
    mode: str = typer.Argument(..., help="Mode (dev/prod)"),
):
    """Set mode for a specific container."""
    hsm = HSMCore()
    try:
        hsm.set_package_mode(name, mode)
        console.print(f"[green]Mode for '{name}' set to {mode}. Run 'hsm sync' to apply.[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

# --- Project Python Manager Commands ---

@python_manager_app.command(name="set")
def project_python_manager_set(
    manager: str = typer.Argument(..., help="Manager name (uv/pixi/pip)"),
):
    """Set the python package manager."""
    hsm = HSMCore()
    try:
        hsm.set_python_manager(manager)
        console.print(f"[green]Python manager set to {manager}.[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)