import logging
from pathlib import Path
from rich.console import Console
from rich.logging import RichHandler
from . .core.engine import HSMCore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)

logger = logging.getLogger("hsm")
console = Console()

# --- Autocompletion Helpers ---

def complete_registry_packages(ctx, incomplete: str):
    hsm = HSMCore()
    registry_path = hsm.registry_path
    if not registry_path.exists(): return []
    return [p.stem for p in registry_path.glob("packages/*.yaml") if p.stem.startswith(incomplete)]

def complete_registry_groups(ctx, incomplete: str):
    hsm = HSMCore()
    registry_path = hsm.registry_path
    if not registry_path.exists(): return []
    groups = []
    for p in registry_path.glob("package_groups/*.yaml"):
        if p.stem.startswith(incomplete): groups.append(p.stem)
    for p in registry_path.glob("container_groups/*.yaml"):
        if p.stem.startswith(incomplete): groups.append(p.stem)
    return groups

def complete_registry_containers(ctx, incomplete: str):
    hsm = HSMCore()
    registry_path = hsm.registry_path
    if not registry_path.exists(): return []
    return [p.stem for p in registry_path.glob("containers/*.yaml") if p.stem.startswith(incomplete)]

def complete_project_packages(ctx, incomplete: str):
    hsm = HSMCore()
    return [p for p in hsm.manifest.packages if p.startswith(incomplete)]

def complete_project_groups(ctx, incomplete: str):
    hsm = HSMCore()
    groups = list(hsm.manifest.package_groups.keys())
    container_groups = hsm.manifest.data.get("services", {}).get("container_groups", {})
    groups.extend(container_groups.keys())
    return [g for g in groups if g.startswith(incomplete)]

def complete_project_containers(ctx, incomplete: str):
    hsm = HSMCore()
    containers = hsm.manifest.data.get("services", {}).get("containers", [])
    return [c for c in containers if c.startswith(incomplete)]