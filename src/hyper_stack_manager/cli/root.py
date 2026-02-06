import typer
from pathlib import Path
from typing import Optional
from rich.tree import Tree

from ..core.engine import HSMCore
from .utils import console

app = typer.Typer(
    help="Hyper Stack Manager (hsm) CLI - Modern Environment Orchestrator",
    add_completion=True
)

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
def check():
    """Perform a dry-run validation of the project and registry."""
    hsm = HSMCore()
    try:
        hsm.check()
        console.print("[green]All checks passed successfully.[/green]")
    except Exception as e:
        console.print(f"[red]Check failed: {e}[/red]")
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