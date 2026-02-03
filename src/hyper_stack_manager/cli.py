import typer
import logging
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
    help="Hyper Stack Manager (hsm) CLI",
    add_completion=True
)

# --- Registry Subgroup ---
registry_app = typer.Typer(help="Manage the HSM global registry")
app.add_typer(registry_app, name="registry")

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
    import yaml
    console.print(yaml.dump(details, sort_keys=False))

@registry_app.command(name="add")
def registry_add(
    name: Optional[str] = typer.Argument(None, help="Name of the package"),
    version: Optional[str] = typer.Option(None, "--version", "-v", help="Package version"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Package description"),
    prod_type: Optional[str] = typer.Option(None, "--prod-type", help="Production source type (git/pypi)"),
    prod_url: Optional[str] = typer.Option(None, "--prod-url", help="Production source URL"),
    prod_ref: Optional[str] = typer.Option(None, "--prod-ref", help="Production source ref (tag/branch)"),
    dev_path: Optional[str] = typer.Option(None, "--dev-path", help="Development local path"),
    registry: Optional[Path] = typer.Option(None, "--registry", "-r", help="Path to the registry"),
):
    """Add a new package to the registry with interactive wizard support."""
    hsm = HSMCore(registry_path=registry)
    
    try:
        # Interactive Wizard if arguments are missing
        if name is None:
            name = pt_prompt("Package Name: ")
            if not name:
                console.print("[red]Package name is required[/red]")
                raise typer.Exit(code=1)

        if version is None:
            version = pt_prompt("Version: ", default="0.1.0")

        if description is None:
            description = pt_prompt("Description: ")

        if prod_type is None:
            type_completer = WordCompleter(["git", "pypi"], ignore_case=True)
            prod_type = pt_prompt("Production Source Type (git/pypi): ", completer=type_completer, default="git")

        if prod_url is None:
            if prod_type == "git":
                prod_url = pt_prompt("Git URL: ")
            else:
                prod_url = pt_prompt("PyPI Package Name: ")
            
            if not prod_url:
                console.print("[red]Production URL/Name is required[/red]")
                raise typer.Exit(code=1)

        if prod_type == "git" and prod_ref is None:
            prod_ref = pt_prompt("Git Ref (tag/branch/commit) [optional]: ")

        if dev_path is None:
            path_completer = PathCompleter(only_directories=True, expanduser=True)
            dev_path = pt_prompt("Development Local Path [optional]: ", completer=path_completer)

        # Prepare sources
        prod_source = {"type": prod_type, "url" if prod_type == "git" else "name": prod_url}
        if prod_type == "git" and prod_ref:
            prod_source["ref"] = prod_ref

        dev_source = None
        if dev_path:
            dev_source = {
                "type": "local",
                "path": dev_path,
                "editable": True
            }

        hsm.add_package_to_registry(
            name=name,
            version=version,
            description=description,
            prod_source=prod_source,
            dev_source=dev_source
        )
        console.print(f"[green]Successfully added package '{name}' to registry.[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

# --- Project Commands (Top Level) ---

@app.command()
def init(
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Name of the project"),
):
    """Initialize a new HSM project (creates hsm.yaml)."""
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
    """Materialize hsm.yaml into pyproject.toml and environment."""
    hsm = HSMCore()
    try:
        hsm.sync(frozen=frozen)
        console.print("[green]Environment synced successfully.[/green]")
    except Exception as e:
        console.print(f"[red]Sync failed: {e}[/red]")
        raise typer.Exit(code=1)

@app.command()
def list():
    """Show current project stack from hsm.yaml."""
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
        pkgs.add(p)
        
    console.print(tree)

# --- Edit Commands ---

@app.command(name="add")
def add_component(
    name: str = typer.Argument(..., help="Name of the package to add"),
    group: Optional[str] = typer.Option(None, "--group", "-g", help="Add to a specific group"),
):
    """Add a package or group selection to hsm.yaml."""
    hsm = HSMCore()
    try:
        if group:
            hsm.add_package_group(group, name)
            console.print(f"[green]Added {name} to group {group} in manifest. Run 'hsm sync' to apply.[/green]")
        else:
            hsm.add_package(name)
            console.print(f"[green]Added {name} to manifest. Run 'hsm sync' to apply.[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

@app.command(name="remove")
def remove_component(
    name: str = typer.Argument(..., help="Name of the package to remove"),
    group: Optional[str] = typer.Option(None, "--group", "-g", help="Remove from a specific group"),
):
    """Remove a package or group selection from hsm.yaml."""
    hsm = HSMCore()
    try:
        if group:
            hsm.remove_package_group(group, name)
            console.print(f"[green]Removed {name} from group {group} in manifest. Run 'hsm sync' to apply.[/green]")
        else:
            hsm.remove_package(name)
            console.print(f"[green]Removed {name} from manifest. Run 'hsm sync' to apply.[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
