import logging
import os
import yaml
import importlib.metadata
from pathlib import Path
from typing import List, Dict, Optional, Any, Union, Type

from ..manifest import HSMProjectManifest
from ..adapters.base import BasePackageManagerAdapter, BaseContainerAdapter
from .registry_manager import RegistryManager
from .sync_engine import SyncEngine
from .validator import Validator

logger = logging.getLogger(__name__)

class HSMCore:
    """Core logic for Hyper Stack Manager (hsm) - Facade implementation."""

    def __init__(self, project_root: Optional[Path] = None, registry_path: Optional[Path] = None):
        """Initialize HSMCore Facade."""
        self.project_root = project_root or Path.cwd()
        self.manifest = HSMProjectManifest(self.project_root / "hsm.yaml")
        
        # Initialize adapters
        self.package_adapter = self._get_package_adapter()
        self.container_adapter = self._get_container_adapter()
        
        # Registry Path resolution
        env_registry_path = os.environ.get("HSM_REGISTRY_PATH")
        self.registry_path = registry_path or (Path(env_registry_path) if env_registry_path else self.project_root / "hsm-registry")

        # Initialize Sub-Managers
        self.registry = RegistryManager(self.registry_path)
        self.sync_engine = SyncEngine(
            self.project_root, self.manifest, self.registry_path,
            self.package_adapter, self.container_adapter
        )
        self.validator = Validator(self.manifest, self.registry_path)

    def _get_package_adapter(self) -> BasePackageManagerAdapter:
        """Get the appropriate package manager adapter using entry points."""
        manager = self.manifest.manager
        eps = importlib.metadata.entry_points(group="hsm.package_managers")
        
        for ep in eps:
            if ep.name == manager:
                adapter_class: Type[BasePackageManagerAdapter] = ep.load()
                return adapter_class(self.project_root)
                
        raise ValueError(f"Unsupported package manager: {manager}. Available: {[ep.name for ep in eps]}")

    def _get_container_adapter(self) -> BaseContainerAdapter:
        """Get the appropriate container adapter using entry points."""
        engine = self.manifest.data.get("project", {}).get("container_engine", "docker")
        eps = importlib.metadata.entry_points(group="hsm.container_engines")
        
        for ep in eps:
            if ep.name == engine:
                adapter_class: Type[BaseContainerAdapter] = ep.load()
                return adapter_class(self.project_root)
                
        raise ValueError(f"Unsupported container engine: {engine}. Available: {[ep.name for ep in eps]}")

    # --- Delegated Methods ---

    def init_project(self, name: Optional[str] = None):
        """Initialize a new HSM project."""
        if not name:
            name = self.project_root.name
        
        logger.info(f"Initializing HSM project: {name}")
        
        if not self.manifest.path.exists():
            self.manifest.data["project"]["name"] = name
            self.manifest.save()
            logger.info(f"Created {self.manifest.path}")

        # Ensure registry structure
        for sub_dir in ["packages", "containers", "package_groups", "container_groups"]:
            path = self.registry_path / sub_dir
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured registry directory: {path}")

    def sync(self, frozen: bool = False):
        """Sync project state with the manifest."""
        self.sync_engine.sync(frozen=frozen)

    def check(self):
        """Perform a dry-run validation."""
        self.validator.check()

    def search_registry(self, query: str) -> Dict[str, List[str]]:
        return self.registry.search(query)

    def add_package_to_registry(self, *args, **kwargs):
        self.registry.add_package(*args, **kwargs)

    def add_container_to_registry(self, *args, **kwargs):
        self.registry.add_container(*args, **kwargs)

    def add_group_to_registry(self, *args, **kwargs):
        self.registry.add_group(*args, **kwargs)

    def remove_from_registry(self, name: str):
        self.registry.remove(name)

    def add_option_to_registry_group(self, group_name: str, option: str):
        self.registry.add_option_to_group(group_name, option)

    def remove_option_from_registry_group(self, group_name: str, option: str):
        self.registry.remove_option_from_group(group_name, option)

    def get_component_details(self, name: str) -> Optional[Dict[str, Any]]:
        return self.registry.get_details(name)

    # --- Project Management Methods (to be moved to ProjectManager later if needed) ---

    def set_python_manager(self, manager_name: str):
        self.manifest.set_manager(manager_name)
        self.manifest.save()
        logger.info(f"Set python package manager to {manager_name}")

    def set_registry_path(self, path: str):
        self.registry_path = Path(path)
        self.registry.registry_path = self.registry_path
        logger.info(f"Registry path set to {path}")

    def set_package_mode(self, name: str, mode: str):
        self.manifest.set_package_mode(name, mode)
        self.manifest.save()
        logger.info(f"Set mode for package {name} to {mode}")

    def set_global_mode(self, mode: str):
        # 1. Standalone packages
        for pkg in self.manifest.packages:
            name = pkg.get("name") if isinstance(pkg, dict) else pkg
            self.manifest.set_package_mode(name, mode)
        
        # 2. Package groups
        for group_name in self.manifest.package_groups:
            self.manifest.set_package_mode(group_name, mode)

        # 3. Container groups
        container_groups = self.manifest.data.get("services", {}).get("container_groups", {})
        for group_name in container_groups:
            self.manifest.set_package_mode(group_name, mode)

        # 4. Standalone containers
        standalone_containers = self.manifest.data.get("services", {}).get("containers", [])
        for cont in standalone_containers:
            name = cont.get("name") if isinstance(cont, dict) else cont
            self.manifest.set_package_mode(name, mode)
        
        self.manifest.save()
        logger.info(f"Set global project mode to {mode}")

    def add_package(self, name: str):
        self.manifest.add_package(name)
        self.manifest.save()
        logger.info(f"Added package {name} to hsm.yaml")

    def remove_package(self, name: str):
        self.manifest.remove_package(name)
        self.manifest.save()
        logger.info(f"Removed package {name} from hsm.yaml")

    def remove_package_group(self, group_name: str, option: str):
        self.manifest.remove_from_group(group_name, option)
        self.manifest.save()
        logger.info(f"Removed {option} from group {group_name} in hsm.yaml")

    def remove_group(self, group_name: str):
        self.manifest.remove_group(group_name)
        self.manifest.save()
        logger.info(f"Removed group {group_name} from hsm.yaml")

    def add_package_group(self, group_name: str, option: str):
        # Logic for adding group selection (reused from old core.py)
        from ..models import RegistryGroup
        group_type = "package_group"
        group_path = self.registry_path / "package_groups" / f"{group_name}.yaml"
        if not group_path.exists():
            group_path = self.registry_path / "container_groups" / f"{group_name}.yaml"
            group_type = "container_group"
            
        if not group_path.exists():
            raise FileNotFoundError(f"Group {group_name} not found in registry")
            
        with open(group_path, "r") as f:
            data = yaml.safe_load(f)
            group = RegistryGroup(**data)
            
        comment = data.get("comment")
            
        if group_type == "package_group":
            self.manifest.set_package_group(
                group_name=group_name,
                selection=option,
                strategy=group.strategy,
                comment=comment
            )
        else:
            services = self.manifest.data.setdefault("services", {})
            groups = services.setdefault("container_groups", {})
            groups[group_name] = {
                "strategy": group.strategy,
                "selection": option
            }

        # Handle Implies
        selected_opt = next((opt for opt in group.options if opt.name == option), None)
        if selected_opt and selected_opt.implies:
            logger.info(f"Option '{option}' implies additional dependencies: {selected_opt.implies}")
            for target_type_group, target_option in selected_opt.implies.items():
                if ":" in target_type_group:
                    _, target_group_name = target_type_group.split(":", 1)
                    if isinstance(target_option, list):
                        for opt in target_option:
                            self.add_group_option(target_group_name, opt)
                    else:
                        self.add_group_option(target_group_name, target_option)

        self.manifest.save()
        logger.info(f"Added group {group_name} with selection {option} to hsm.yaml")

    def add_group_option(self, group_name: str, option: str):
        group_path = self.registry_path / "package_groups" / f"{group_name}.yaml"
        if not group_path.exists():
            raise FileNotFoundError(f"Group {group_name} not found in registry")
            
        with open(group_path, "r") as f:
            data = yaml.safe_load(f)
            strategy = data.get("strategy", "1-of-N")

        self.manifest.add_option_to_group(group_name, option, strategy)
        self.manifest.save()
        logger.info(f"Added option {option} to group {group_name} in hsm.yaml")

    def remove_group_option(self, group_name: str, option: str):
        self.manifest.remove_from_group(group_name, option)
        self.manifest.save()
        logger.info(f"Removed option {option} from group {group_name} in hsm.yaml")

    def init_package(self, name: str, path: Optional[Path] = None, register: bool = True):
        if path is None:
            path = self.project_root / "packages" / name
        
        if not path.is_absolute():
            path = self.project_root / path

        logger.info(f"Initializing package '{name}' at {path}")
        self.package_adapter.init_lib(path)

        if register:
            rel_path = os.path.relpath(path, self.project_root)
            self.add_package_to_registry(
                name=name,
                version="0.1.0",
                description=f"Local package {name}",
                prod_source={"type": "local", "path": rel_path},
                dev_source={"type": "local", "path": rel_path, "editable": True}
            )