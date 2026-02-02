import typer
import logging
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table
from rich.tree import Tree
from prompt_toolkit import prompt as pt_prompt
from prompt_toolkit.completion import WordCompleter, PathCompleter
from .core import HPMCore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)

logger = logging.getLogger("hpm")
console = Console()
app = typer.Typer(
    help="HyperPackageManager (hpm) CLI",
    add_completion=False # We handle completion flags manually to hide unwanted ones
)

@app.callback()
def main(
    ctx: typer.Context,
    install_completion: bool = typer.Option(
        False,
        "--install-completion",
        help="Install completion for the current shell.",
        is_flag=True
    ),
    show_completion: bool = typer.Option(
        False,
        "--show-completion",
        help="Show completion for the current shell.",
        is_flag=True,
        hidden=True # This hides it from --help
    ),
):
    """
    HyperPackageManager (hpm) CLI
    """
    if install_completion:
        import typer.completion
        shell, path = typer.completion.install()
        console.print(f"Completion installed for {shell} at {path}")
        raise typer.Exit()
    
    if show_completion:
        import typer.completion
        console.print(typer.completion.get_completion_script())
        raise typer.Exit()

@app.command()
def init(
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Name of the project"),
    version: Optional[str] = typer.Option(None, "--version", "-v", help="Project version"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Project description"),
    python_version: Optional[str] = typer.Option(None, "--python", "-p", help="Required Python version"),
    registry_dir: str = typer.Option("hpm-registry", "--registry-dir", help="Directory for the HPM registry"),
):
    """Initializes a new HPM project."""
    hpm = HPMCore()
    pyproject_path = hpm.project_root / "pyproject.toml"
    
    # Defaults from existing pyproject.toml
    existing_config = {}
    if pyproject_path.exists():
        import tomllib
        with open(pyproject_path, "rb") as f:
            existing_config = tomllib.load(f).get("project", {})

    # Determine metadata: prioritize CLI args > existing config > prompts
    if name is None:
        if "name" in existing_config:
            name = existing_config["name"]
        else:
            name = typer.prompt("Project Name", default=hpm.project_root.name)
            
    if version is None:
        if "version" in existing_config:
            version = existing_config["version"]
        else:
            version = typer.prompt("Version", default="0.1.0")
            
    if description is None:
        if "description" in existing_config:
            description = existing_config["description"]
        else:
            description = typer.prompt("Description", default="")
            
    if python_version is None:
        if "requires-python" in existing_config:
            python_version = existing_config["requires-python"]
        else:
            python_version = typer.prompt("Python version", default=">=3.13")

    try:
        hpm.init_project(name, version, description, python_version, registry_dir)
        console.print(f"[green]Project '{name}' initialized with HPM support.[/green]")
    except Exception as e:
        console.print(f"[red]Error during initialization: {e}[/red]")
        raise typer.Exit(code=1)

@app.command()
def install(
    manifest: Path = typer.Option(Path("hpm.yaml"), help="Path to hpm.yaml"),
    mode: str = typer.Option("prod", help="Run mode (prod or dev)"),
):
    """Installs a plugin and its dependencies."""
    hpm = HPMCore()
    try:
        hpm.install_plugin(manifest, mode=mode)
        console.print(f"[green]Successfully installed plugin from {manifest}[/green]")
    except Exception as e:
        console.print(f"[red]Error during installation: {e}[/red]")
        raise typer.Exit(code=1)

@app.command(name="group")
def group_cmd(
    action: str = typer.Argument(..., help="Action to perform: add"),
    group_name: str = typer.Argument(..., help="Name of the group"),
    option: str = typer.Option(..., "--option", "-o", help="Option to add to the group"),
    registry: Optional[Path] = typer.Option(None, "--registry", "-r", help="Path to the registry"),
):
    """Manages package groups."""
    hpm = HPMCore(registry_path=registry)
    try:
        if action == "add":
            hpm.add_group_option(group_name, option)
            console.print(f"[green]Successfully added option '{option}' to group '{group_name}'[/green]")
        else:
            console.print(f"[red]Unknown action: {action}[/red]")
            raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

@app.command()
def check(
    registry: Optional[Path] = typer.Option(None, "--registry", "-r", help="Path to the registry"),
):
    """Validates dependency resolution for configured groups."""
    hpm = HPMCore(registry_path=registry)
    try:
        hpm.check()
        console.print("[green]Check passed: Dependencies are resolvable[/green]")
    except Exception as e:
        console.print(f"[red]Check failed: {e}[/red]")
        raise typer.Exit(code=1)

@app.command()
def list(
    registry: Optional[Path] = typer.Option(None, "--registry", "-r", help="Path to the registry"),
):
    """Lists all groups and current project configuration."""
    hpm = HPMCore(registry_path=registry)
    try:
        groups = hpm.list_groups()
        
        # Project config
        pyproject_path = hpm.project_root / "pyproject.toml"
        active_groups = {}
        if pyproject_path.exists():
            import tomllib
            with open(pyproject_path, "rb") as f:
                config = tomllib.load(f)
            active_groups = config.get("tool", {}).get("hpm", {}).get("groups", {})

        tree = Tree("[bold blue]HPM Project Configuration[/bold blue]")
        groups_node = tree.add("Groups")
        
        for group in groups:
            status = ""
            if group.name in active_groups:
                val = active_groups[group.name]
                status = f" [green](active: {val})[/green]"
            
            groups_node.add(f"{group.name} [dim]({group.strategy})[/dim]{status}")
        
        console.print(tree)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

@app.command()
def show(
    group_name: str = typer.Argument(..., help="Name of the group to show"),
    registry: Optional[Path] = typer.Option(None, "--registry", "-r", help="Path to the registry"),
):
    """Shows details for a specific group."""
    hpm = HPMCore(registry_path=registry)
    try:
        group = hpm.load_group(group_name)
        console.print(f"[bold blue]Group:[/bold blue] {group.name}")
        console.print(f"[bold blue]Strategy:[/bold blue] {group.strategy}")
        
        table = Table(title="Available Options")
        table.add_column("Option Name", style="cyan")
        table.add_column("Description", style="magenta")
        
        for opt in group.options:
            table.add_row(opt.name, opt.description or "")
        
        console.print(table)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    registry: Optional[Path] = typer.Option(None, "--registry", "-r", help="Path to the registry"),
):
    """Searches the registry for groups and packages."""
    hpm = HPMCore(registry_path=registry)
    try:
        results = hpm.search_registry(query)
        
        if results["groups"]:
            console.print("[bold green]Found Groups:[/bold green]")
            for g in results["groups"]:
                console.print(f"  - {g}")
        
        if results["packages"]:
            console.print("[bold green]Found Packages:[/bold green]")
            for p in results["packages"]:
                console.print(f"  - {p}")
        
        if not results["groups"] and not results["packages"]:
            console.print(f"[yellow]No results found for '{query}'[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

registry_app = typer.Typer(help="Manage the HPM registry")
app.add_typer(registry_app, name="registry")

@registry_app.command(name="add")
def registry_add(
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Name of the package"),
    source_type: Optional[str] = typer.Option(None, "--type", "-t", help="Source type (git/local)"),
    url_or_path: Optional[str] = typer.Option(None, "--url-path", "-u", help="Source URL or local path"),
    version: Optional[str] = typer.Option(None, "--version", "-v", help="Package version"),
    registry: Optional[Path] = typer.Option(None, "--registry", "-r", help="Path to the registry"),
):
    """Adds a new package to the registry with interactive autocompletion."""
    hpm = HPMCore(registry_path=registry)
    
    try:
        # Interactive prompts with autocompletion if not provided via CLI
        if name is None:
            name = pt_prompt("Package Name: ")
            if not name:
                console.print("[red]Package name is required[/red]")
                raise typer.Exit(code=1)

        if source_type is None:
            type_completer = WordCompleter(["git", "local"], ignore_case=True)
            source_type = pt_prompt("Source Type (git/local): ", completer=type_completer)
            if source_type not in ["git", "local"]:
                console.print("[red]Invalid source type. Must be 'git' or 'local'[/red]")
                raise typer.Exit(code=1)

        if url_or_path is None:
            if source_type == "local":
                path_completer = PathCompleter(only_directories=True, expanduser=True)
                url_or_path = pt_prompt("Local Path: ", completer=path_completer)
            else:
                url_or_path = pt_prompt("Git URL: ")
            
            if not url_or_path:
                console.print("[red]URL or Path is required[/red]")
                raise typer.Exit(code=1)

        if version is None:
            version = pt_prompt("Version: ", default="0.1.0")

        hpm.add_package_to_registry(name, source_type, url_or_path, version)
        console.print(f"[green]Successfully added package '{name}' to registry[/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

@app.command()
def sync(
    registry: Optional[Path] = typer.Option(None, "--registry", "-r", help="Path to the registry"),
):
    """Syncs configured groups with uv dependencies."""
    hpm = HPMCore(registry_path=registry)
    try:
        hpm.sync()
        console.print("[green]Successfully synced groups[/green]")
    except Exception as e:
        console.print(f"[red]Error during sync: {e}[/red]")
        raise typer.Exit(code=1)

@app.command()
def run(
    manifest: Path = typer.Option(Path("hpm.yaml"), help="Path to hpm.yaml"),
    entrypoint: str = typer.Option(..., "--entrypoint", "-e", help="Entrypoint name to run"),
):
    """Runs a plugin entrypoint."""
    hpm = HPMCore()
    try:
        hpm.run_entrypoint(manifest, entrypoint)
    except Exception as e:
        console.print(f"[red]Error running entrypoint: {e}[/red]")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()