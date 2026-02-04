import typer
import logging
import yaml
from pathlib import Path
from typing import Optional, List, Dict
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table
from rich.tree import Tree
from prompt_toolkit import prompt as pt_prompt
from prompt_toolkit.completion import WordCompleter, PathCompleter
from .core import HSMCore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)

logger = logging.getLogger("hsm")
console = Console()

app = typer.Typer(
    help="Hyper Stack Manager (hsm) CLI - Modern Environment Orchestrator",
    add_completion=True
)

# --- Registry Subgroups ---
registry_app = typer.Typer(help="Manage the HSM global registry")
app.add_typer(registry_app, name="registry")

registry_package_app = typer.Typer(help="Manage packages in the registry")
registry_app.add_typer(registry_package_app, name="package")

registry_group_app = typer.Typer(help="Manage groups in the registry")
registry_app.add_typer(registry_group_app, name="group")

registry_path_app = typer.Typer(help="Manage registry path configuration")
registry_app.add_typer(registry_path_app, name="path")

# --- Project Subgroups ---
package_app = typer.Typer(help="Manage packages in the current project")
app.add_typer(package_app, name="package")

group_app = typer.Typer(help="Manage groups in the current project")
app.add_typer(group_app, name="group")

python_manager_app = typer.Typer(help="Manage python package manager settings")
app.add_typer(python_manager_app, name="python-manager")

# --- Registry Top-Level Commands ---

@registry_app.command(name="search")
def registry_search(
    query: str = typer.Argument(..., help="Search query for components"),
    registry: Optional[Path] = typer.Option(None, "--registry", "-r", help="Path to the registry"),
):
    """Search for packages, containers, and groups in the registry."""
    hsm = HSMCore(registry_path=registry)
    results = hsm.search_registry(query)
    
    for category, items in results.items():
        if items:
            console.print(f"[bold green]Found {category.capitalize()}:[/bold green]")
            for item in items:
                console.print(f"  - {item}")
    
    if not any(results.values()):
        console.print(f"[yellow]No results found for '{query}'[/yellow]")

@registry_app.command(name="list")
def registry_list(
    registry: Optional[Path] = typer.Option(None, "--registry", "-r", help="Path to the registry"),
):
    """List all available components in the registry."""
    hsm = HSMCore(registry_path=registry)
    results = hsm.search_registry("")
    
    tree = Tree("[bold blue]HSM Global Registry[/bold blue]")
    for category, items in results.items():
        node = tree.add(category.capitalize())
        for item in items:
            node.add(item)
    console.print(tree)

@registry_app.command(name="show")
def registry_show(
    name: str = typer.Argument(..., help="Name of the component to show"),
    registry: Optional[Path] = typer.Option(None, "--registry", "-r", help="Path to the registry"),
):
    """Show detailed information for a component in the registry."""
    hsm = HSMCore(registry_path=registry)
    details = hsm.get_component_details(name)
    
    if not details:
        console.print(f"[red]Component '{name}' not found in registry.[/red]")
        raise typer.Exit(code=1)
        
    console.print(f"[bold blue]Component: {name}[/bold blue]")
    console.print(yaml.dump(details, sort_keys=False))

# --- Registry Path Commands ---

@registry_path_app.command(name="set")
def registry_path_set(
    path: str = typer.Argument(..., help="Path to the registry directory"),
):
    """Set the global registry path."""
    hsm = HSMCore()
    hsm.set_registry_path(path)
    console.print(f"[green]Registry path set to {path}[/green]")

# --- Registry Package Commands ---

@registry_package_app.command(name="add")
def registry_package_add(
    name: Optional[str] = typer.Argument(None, help="Package name"),
    version: Optional[str] = typer.Option(None, "--version", "-v"),
    description: Optional[str] = typer.Option(None, "--description", "-d"),
    prod_type: Optional[str] = typer.Option(None, "--prod-type"),
    prod_url: Optional[str] = typer.Option(None, "--prod-url"),
    dev_path: Optional[str] = typer.Option(None, "--dev-path"),
    registry: Optional[Path] = typer.Option(None, "--registry", "-r"),
):
    """Add a new package to the registry (Interactive Wizard supported)."""
    hsm = HSMCore(registry_path=registry)
    try:
        if name is None:
            name = pt_prompt("Package Name: ")
            if not name:
                raise typer.Exit(1)
        if version is None:
            version = pt_prompt("Version: ", default="0.1.0")
        if description is None:
            description = pt_prompt("Description: ")
        if prod_type is None:
            prod_type = pt_prompt("Prod Type (git/pypi): ", completer=WordCompleter(["git", "pypi"]), default="git")
        if prod_url is None:
            prod_url = pt_prompt("Prod URL/Name: ")
        if dev_path is None:
            dev_path = pt_prompt("Dev Path [optional]: ", completer=PathCompleter(only_directories=True))

        prod_source = {"type": prod_type, "url" if prod_type == "git" else "name": prod_url}
        dev_source = {"type": "local", "path": dev_path, "editable": True} if dev_path else None

        hsm.add_package_to_registry(name, version, description, prod_source, dev_source)
        console.print(f"[green]Package '{name}' added to registry.[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

@registry_package_app.command(name="remove")
def registry_package_remove(
    name: str = typer.Argument(..., help="Package name to remove"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Confirm without prompt"),
    registry: Optional[Path] = typer.Option(None, "--registry", "-r"),
):
    """Remove a package from the registry."""
    if not yes and not typer.confirm(f"Are you sure you want to remove package '{name}' from registry?"):
        raise typer.Abort()
    hsm = HSMCore(registry_path=registry)
    try:
        hsm.remove_from_registry(name)
        console.print(f"[green]Package '{name}' removed from registry.[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

# --- Registry Group Commands ---

@registry_group_app.command(name="add")
def registry_group_add(
    name: Optional[str] = typer.Argument(None, help="Group name"),
    group_type: Optional[str] = typer.Option(None, "--type", "-t"),
    strategy: Optional[str] = typer.Option(None, "--strategy", "-s"),
    options: Optional[List[str]] = typer.Option(None, "--option", "-o"),
    description: Optional[str] = typer.Option(None, "--description", "-d"),
    registry: Optional[Path] = typer.Option(None, "--registry", "-r"),
):
    """Add a new group to the registry."""
    hsm = HSMCore(registry_path=registry)
    try:
        if name is None: name = pt_prompt("Group Name: ")
        if not name: raise typer.Exit(1)
        if group_type is None:
            group_type = pt_prompt("Group Type (package_group/container_group): ", 
                                   completer=WordCompleter(["package_group", "container_group"]), default="package_group")
        if strategy is None:
            strategy = pt_prompt("Strategy (1-of-N/M-of-N): ", 
                                 completer=WordCompleter(["1-of-N", "M-of-N"]), default="1-of-N")
        if not options:
            options_str = pt_prompt("Options (comma separated): ")
            options = [opt.strip() for opt in options_str.split(",") if opt.strip()]
        if description is None:
            description = pt_prompt("Description [optional]: ")

        hsm.add_group_to_registry(name, group_type, strategy, options, description)
        console.print(f"[green]Group '{name}' added to registry.[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

@registry_group_app.command(name="remove")
def registry_group_remove(
    name: str = typer.Argument(..., help="Group name to remove"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Confirm without prompt"),
    registry: Optional[Path] = typer.Option(None, "--registry", "-r"),
):
    """Remove a group from the registry."""
    if not yes and not typer.confirm(f"Are you sure you want to remove group '{name}' from registry?"):
        raise typer.Abort()
    hsm = HSMCore(registry_path=registry)
    try:
        hsm.remove_from_registry(name)
        console.print(f"[green]Group '{name}' removed from registry.[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

@registry_group_app.command(name="add-option")
def registry_group_add_option(
    group: str = typer.Argument(..., help="Group name"),
    option: str = typer.Argument(..., help="Option name to add"),
    registry: Optional[Path] = typer.Option(None, "--registry", "-r"),
):
    """Add an option to a group in the registry."""
    hsm = HSMCore(registry_path=registry)
    try:
        hsm.add_option_to_registry_group(group, option)
        console.print(f"[green]Added option '{option}' to group '{group}' in registry.[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

@registry_group_app.command(name="remove-option")
def registry_group_remove_option(
    group: str = typer.Argument(..., help="Group name"),
    option: str = typer.Argument(..., help="Option name to remove"),
    registry: Optional[Path] = typer.Option(None, "--registry", "-r"),
):
    """Remove an option from a group in the registry."""
    hsm = HSMCore(registry_path=registry)
    try:
        hsm.remove_option_from_registry_group(group, option)
        console.print(f"[green]Removed option '{option}' from group '{group}' in registry.[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

# --- Top Level Project Commands ---

@app.command()
def init(
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Name of the project"),
):
    """Initialize a new HSM project."""
    hsm = HSMCore()
    try:
        hsm.init_project(name=name)
        console.print(f"[green]Project initialized with HSM support.[/green]")
    except Exception as e:
        console.print(f"[red]Error during initialization: {e}[/red]")
        raise typer.Exit(code=1)

@app.command()
def sync(
    frozen: bool = typer.Option(False, "--frozen", help="Do not update dependencies, use lock file"),
):
    """Sync project state with the manifest."""
    hsm = HSMCore()
    try:
        hsm.sync(frozen=frozen)
        console.print("[green]Environment synced successfully.[/green]")
    except Exception as e:
        console.print(f"[red]Sync failed: {e}[/red]")
        raise typer.Exit(code=1)

@app.command()
def list():
    """Show current project stack."""
    hsm = HSMCore()
    manifest = hsm.manifest
    tree = Tree(f"[bold blue]Project: {manifest.data.get('project', {}).get('name', 'unknown')}[/bold blue]")
    deps = tree.add("Dependencies")
    groups = deps.add("Groups")
    for g_name, group_cfg in manifest.package_groups.items():
        selection = group_cfg.get("selection", "none")
        strategy = group_cfg.get("strategy", "unknown")
        groups.add(f"{g_name} [dim]({strategy})[/dim]: [green]{selection}[/green]")
    pkgs = deps.add("Standalone Packages")
    for p in manifest.packages:
        mode = manifest.get_package_mode(p)
        pkgs.add(f"{p} [dim]({mode})[/dim]")
    console.print(tree)

@app.command()
def mode(
    mode: str = typer.Argument(..., help="Global mode to set (dev/prod)"),
):
    """Set global project mode."""
    hsm = HSMCore()
    try:
        hsm.set_global_mode(mode)
        console.print(f"[green]Global mode set to {mode}. Run 'hsm sync' to apply.[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

# --- Project Package Commands ---

@package_app.command(name="add")
def project_package_add(
    name: str = typer.Argument(..., help="Package name"),
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
    name: str = typer.Argument(..., help="Group name"),
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
    group: str = typer.Argument(..., help="Group name"),
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
    group: str = typer.Argument(..., help="Group name"),
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

if __name__ == "__main__":
    app()
