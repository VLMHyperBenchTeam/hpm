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

registry_container_app = typer.Typer(help="Manage containers in the registry")
registry_app.add_typer(registry_container_app, name="container")

registry_path_app = typer.Typer(help="Manage registry path configuration")
registry_app.add_typer(registry_path_app, name="path")

# --- Project Subgroups ---
package_app = typer.Typer(help="Manage packages in the current project")
app.add_typer(package_app, name="package")

group_app = typer.Typer(help="Manage groups in the current project")
app.add_typer(group_app, name="group")

container_app = typer.Typer(help="Manage containers in the current project")
app.add_typer(container_app, name="container")

python_manager_app = typer.Typer(help="Manage python package manager settings")
app.add_typer(python_manager_app, name="python-manager")

# --- Autocompletion Helpers ---

def complete_registry_packages(ctx: typer.Context, incomplete: str):
    registry_path = Path("hsm-registry")
    if not registry_path.exists(): return []
    return [p.stem for p in registry_path.glob("packages/*.yaml") if p.stem.startswith(incomplete)]

def complete_registry_groups(ctx: typer.Context, incomplete: str):
    registry_path = Path("hsm-registry")
    if not registry_path.exists(): return []
    groups = []
    for p in registry_path.glob("package_groups/*.yaml"):
        if p.stem.startswith(incomplete): groups.append(p.stem)
    for p in registry_path.glob("container_groups/*.yaml"):
        if p.stem.startswith(incomplete): groups.append(p.stem)
    return groups

def complete_registry_containers(ctx: typer.Context, incomplete: str):
    registry_path = Path("hsm-registry")
    if not registry_path.exists(): return []
    return [p.stem for p in registry_path.glob("containers/*.yaml") if p.stem.startswith(incomplete)]

def complete_project_packages(ctx: typer.Context, incomplete: str):
    hsm = HSMCore()
    return [p for p in hsm.manifest.packages if p.startswith(incomplete)]

def complete_project_groups(ctx: typer.Context, incomplete: str):
    hsm = HSMCore()
    groups = list(hsm.manifest.package_groups.keys())
    container_groups = hsm.manifest.data.get("services", {}).get("container_groups", {})
    groups.extend(container_groups.keys())
    return [g for g in groups if g.startswith(incomplete)]

def complete_project_containers(ctx: typer.Context, incomplete: str):
    hsm = HSMCore()
    containers = hsm.manifest.data.get("services", {}).get("containers", [])
    return [c for c in containers if c.startswith(incomplete)]

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
    no_input: bool = typer.Option(False, "--no-input", help="Disable interactive wizard"),
    registry: Optional[Path] = typer.Option(None, "--registry", "-r"),
):
    """Add a new package to the registry (Interactive Wizard supported)."""
    hsm = HSMCore(registry_path=registry)
    try:
        if name is None:
            if no_input: raise typer.BadParameter("Name is required in no-input mode")
            name = pt_prompt("Package Name: ")
            if not name: raise typer.Exit(1)
        
        if no_input:
            if version is None: version = "0.1.0"
            if prod_type is None: prod_type = "git"
        else:
            if version is None: version = pt_prompt("Version: ", default="0.1.0")
            if description is None: description = pt_prompt("Description: ")
            if prod_type is None:
                prod_type = pt_prompt("Prod Type (git/pypi/local): ", completer=WordCompleter(["git", "pypi", "local"]), default="git")
            if prod_url is None and prod_type != "local":
                prod_url = pt_prompt("Prod URL/Name: ")
            if dev_path is None:
                dev_path = pt_prompt("Dev Path [optional]: ", completer=PathCompleter(only_directories=True))

        if prod_type == "local":
            prod_source = {"type": "local", "path": dev_path}
        else:
            prod_source = {"type": prod_type, "url" if prod_type == "git" else "name": prod_url}
            
        dev_source = {"type": "local", "path": dev_path, "editable": True} if dev_path else None

        hsm.add_package_to_registry(name, version, description, prod_source, dev_source)
        console.print(f"[green]Package '{name}' added to registry.[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

@registry_package_app.command(name="remove")
def registry_package_remove(
    name: str = typer.Argument(..., help="Package name to remove", autocompletion=complete_registry_packages),
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
    no_input: bool = typer.Option(False, "--no-input"),
    registry: Optional[Path] = typer.Option(None, "--registry", "-r"),
):
    """Add a new group to the registry."""
    hsm = HSMCore(registry_path=registry)
    try:
        if name is None:
            if no_input: raise typer.BadParameter("Name is required")
            name = pt_prompt("Group Name: ")
            if not name: raise typer.Exit(1)
            
        if no_input:
            if group_type is None: group_type = "package_group"
            if strategy is None: strategy = "1-of-N"
            if options is None: options = []
        else:
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
    name: str = typer.Argument(..., help="Group name to remove", autocompletion=complete_registry_groups),
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
    group: str = typer.Argument(..., help="Group name", autocompletion=complete_registry_groups),
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
    group: str = typer.Argument(..., help="Group name", autocompletion=complete_registry_groups),
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

# --- Registry Container Commands ---

@registry_container_app.command(name="add")
def registry_container_add(
    name: Optional[str] = typer.Argument(None, help="Container name"),
    image: Optional[str] = typer.Option(None, "--image"),
    build_path: Optional[str] = typer.Option(None, "--build-path"),
    dockerfile: Optional[str] = typer.Option(None, "--dockerfile"),
    ports: Optional[List[str]] = typer.Option(None, "--port", "-p"),
    volumes: Optional[List[str]] = typer.Option(None, "--volume", "-v"),
    env: Optional[List[str]] = typer.Option(None, "--env", "-e"),
    description: Optional[str] = typer.Option(None, "--description", "-d"),
    no_input: bool = typer.Option(False, "--no-input"),
    registry: Optional[Path] = typer.Option(None, "--registry", "-r"),
):
    """Add a new container to the registry."""
    hsm = HSMCore(registry_path=registry)
    try:
        if name is None:
            if no_input: raise typer.BadParameter("Name is required")
            name = pt_prompt("Container Name: ")
            if not name: raise typer.Exit(1)

        if not no_input:
            if image is None and build_path is None:
                image = pt_prompt("Image [optional]: ")
                if not image:
                    build_path = pt_prompt("Build Path [optional]: ")
            if description is None:
                description = pt_prompt("Description [optional]: ")

        env_dict = {}
        if env:
            for e in env:
                if "=" in e:
                    k, v = e.split("=", 1)
                    env_dict[k] = v

        prod_source = {"type": "docker-image", "image": image} if image else None
        dev_source = {"type": "build", "path": build_path, "dockerfile": dockerfile} if build_path else None

        hsm.add_container_to_registry(
            name=name,
            description=description,
            prod_source=prod_source,
            dev_source=dev_source,
            ports=ports,
            volumes=volumes,
            env=env_dict
        )
        console.print(f"[green]Container '{name}' added to registry.[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

@registry_container_app.command(name="remove")
def registry_container_remove(
    name: str = typer.Argument(..., help="Container name to remove", autocompletion=complete_registry_containers),
    yes: bool = typer.Option(False, "--yes", "-y"),
    registry: Optional[Path] = typer.Option(None, "--registry", "-r"),
):
    """Remove a container from the registry."""
    if not yes and not typer.confirm(f"Are you sure you want to remove container '{name}'?"):
        raise typer.Abort()
    hsm = HSMCore(registry_path=registry)
    try:
        hsm.remove_from_registry(name)
        console.print(f"[green]Container '{name}' removed from registry.[/green]")
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

@app.command(name="list")
def cli_list():
    """Show current project stack."""
    hsm = HSMCore()
    manifest = hsm.manifest
    tree = Tree(f"[bold blue]Project: {manifest.data.get('project', {}).get('name', 'unknown')}[/bold blue]")
    
    def get_mode_str(name: str):
        mode = manifest.get_package_mode(name)
        icon = "🛠️ " if mode == "dev" else "📦"
        return f"[dim]({mode} {icon})[/dim]"

    # 1. Dependencies (Packages)
    deps = tree.add("Dependencies (Packages)")
    
    # Groups
    groups_node = deps.add("Groups")
    for g_name, group_cfg in manifest.package_groups.items():
        selection = group_cfg.get("selection", "none")
        strategy = group_cfg.get("strategy", "unknown")
        g_node = groups_node.add(f"{g_name} [dim]({strategy})[/dim]")
        if isinstance(selection, (list, tuple)):
            for s in selection:
                g_node.add(f"[green]{s}[/green] {get_mode_str(s)}")
        else:
            g_node.add(f"[green]{selection}[/green] {get_mode_str(selection)}")
            
    # Standalone
    pkgs_node = deps.add("Standalone")
    for p in manifest.packages:
        name = p.get("name") if isinstance(p, dict) else p
        pkgs_node.add(f"{name} {get_mode_str(name)}")

    # 2. Services (Containers)
    services = tree.add("Services (Containers)")
    
    # Groups
    c_groups_data = manifest.data.get("services", {}).get("container_groups", {})
    c_groups_node = services.add("Groups")
    for g_name, group_cfg in c_groups_data.items():
        selection = group_cfg.get("selection", "none")
        strategy = group_cfg.get("strategy", "unknown")
        g_node = c_groups_node.add(f"{g_name} [dim]({strategy})[/dim]")
        if isinstance(selection, (list, tuple)):
            for s in selection:
                g_node.add(f"[green]{s}[/green] {get_mode_str(s)}")
        else:
            g_node.add(f"[green]{selection}[/green] {get_mode_str(selection)}")
            
    # Standalone
    containers_data = manifest.data.get("services", {}).get("containers", [])
    containers_node = services.add("Standalone")
    for c in containers_data:
        name = c.get("name") if isinstance(c, dict) else c
        containers_node.add(f"{name} {get_mode_str(name)}")

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
            hsm.add_package_group(group, name) # Reusing add_package_group as it handles both types
        else:
            # TODO: Implement add_standalone_container in core if needed,
            # currently manifest supports standalone containers in services.containers
            # For now, let's assume we add it to a default group or standalone list
            # But core.py doesn't have add_container method for project yet.
            # Let's implement a basic add_container to manifest in core or reuse logic.
            # For MVP, let's just warn or use a default group.
            console.print("[yellow]Adding standalone containers is not fully supported yet. Please use groups.[/yellow]")
            # hsm.add_container(name)
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
             # hsm.remove_container(name)
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
        hsm.set_package_mode(name, mode) # Reusing set_package_mode as it sets mode by name
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

if __name__ == "__main__":
    app()
