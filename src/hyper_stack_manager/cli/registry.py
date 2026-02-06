import typer
import yaml
from pathlib import Path
from typing import Optional, List
from prompt_toolkit import prompt as pt_prompt
from prompt_toolkit.completion import WordCompleter, PathCompleter
from rich.tree import Tree

from ..core.engine import HSMCore
from .utils import console, complete_registry_packages, complete_registry_groups, complete_registry_containers

registry_app = typer.Typer(help="Manage the HSM global registry")

package_app = typer.Typer(help="Manage packages in the registry")
registry_app.add_typer(package_app, name="package")

group_app = typer.Typer(help="Manage groups in the registry")
registry_app.add_typer(group_app, name="group")

container_app = typer.Typer(help="Manage containers in the registry")
registry_app.add_typer(container_app, name="container")

path_app = typer.Typer(help="Manage registry path configuration")
registry_app.add_typer(path_app, name="path")

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

@path_app.command(name="set")
def registry_path_set(
    path: str = typer.Argument(..., help="Path to the registry directory"),
):
    """Set the global registry path."""
    hsm = HSMCore()
    hsm.set_registry_path(path)
    console.print(f"[green]Registry path set to {path}[/green]")

@package_app.command(name="add")
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
    """Add a new package to the registry."""
    hsm = HSMCore(registry_path=registry)
    try:
        if name is None:
            if no_input: raise typer.BadParameter("Name is required")
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

@package_app.command(name="remove")
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

@group_app.command(name="add")
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

@group_app.command(name="remove")
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

@group_app.command(name="add-option")
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

@group_app.command(name="remove-option")
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

@container_app.command(name="add")
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

@container_app.command(name="remove")
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