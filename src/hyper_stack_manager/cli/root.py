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
    verify: bool = typer.Option(True, "--verify/--no-verify", help="Verify environment after sync"),
):
    """Sync project state with the manifest."""
    hsm = HSMCore()
    try:
        hsm.sync(frozen=frozen)
        console.print("[green]Environment synced successfully.[/green]")
        
        if verify:
            results = hsm.verify_sync_results()
            if results["packages"]["status"] == "ok" and results["containers"]["status"] == "ok":
                console.print("[bold green]Verification: OK[/bold green]")
            else:
                console.print("[bold yellow]Verification: Issues found![/bold yellow]")
                if results["packages"]["missing"]:
                    console.print(f"[red]Missing packages: {', '.join(results['packages']['missing'])}[/red]")
                if results["containers"]["missing"]:
                    console.print(f"[red]Missing containers: {', '.join(results['containers']['missing'])}[/red]")
                    
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
        mode = manifest.get_mode(name)
        icon = "🛠️ " if mode == "dev" else "📦"
        return f"[dim]({mode} {icon})[/dim]"

    def get_runtime_info(name: str):
        details = hsm.get_component_details(name)
        if not details:
            return ""
        
        mode = manifest.get_mode(name)
        # Check if it's a service manifest
        if details.get("type") == "service":
            profiles = details.get("deployment_profiles", {})
            profile = profiles.get(mode, profiles.get("prod", {}))
            runtime = profile.get("runtime", "docker")
            return f" [blue]<{runtime}>[/blue]"
        return ""

    # 1. Libraries
    libs_root = tree.add("Libraries")
    
    # Groups
    groups_node = libs_root.add("Groups")
    for g_name, group_cfg in manifest.library_groups.items():
        selection = group_cfg.get("selection", "none")
        strategy = group_cfg.get("strategy", "unknown")
        g_node = groups_node.add(f"{g_name} [dim]({strategy})[/dim]")
        if isinstance(selection, (list, tuple)):
            for s in selection:
                g_node.add(f"[green]{s}[/green] {get_mode_str(s)}")
        else:
            g_node.add(f"[green]{selection}[/green] {get_mode_str(selection)}")
            
    # Standalone
    pkgs_node = libs_root.add("Standalone")
    for name in manifest.libraries:
        pkgs_node.add(f"{name} {get_mode_str(name)}")

    # 2. Services
    services_root = tree.add("Services")
    
    # Groups
    s_groups_node = services_root.add("Groups")
    for g_name, group_cfg in manifest.service_groups.items():
        selection = group_cfg.get("selection", "none")
        strategy = group_cfg.get("strategy", "unknown")
        g_node = s_groups_node.add(f"{g_name} [dim]({strategy})[/dim]")
        if isinstance(selection, (list, tuple)):
            for s in selection:
                g_node.add(f"[green]{s}[/green]{get_runtime_info(s)} {get_mode_str(s)}")
        else:
            g_node.add(f"[green]{selection}[/green]{get_runtime_info(selection)} {get_mode_str(selection)}")
            
    # Standalone
    standalone_node = services_root.add("Standalone")
    for name in manifest.services:
        standalone_node.add(f"{name}{get_runtime_info(name)} {get_mode_str(name)}")

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