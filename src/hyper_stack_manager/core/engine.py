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
from .inspector import EnvironmentInspector

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
        self.inspector = EnvironmentInspector()

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
        for sub_dir in ["libraries", "services", "library_groups", "service_groups"]:
            path = self.registry_path / sub_dir
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured registry directory: {path}")

        # Initialize package manager in root if needed
        if not (self.project_root / "pyproject.toml").exists():
            logger.info(f"Initializing package manager '{self.manifest.manager}' in project root")
            self.package_adapter.init_project(self.project_root)

    def sync(self, frozen: bool = False):
        """Sync project state with the manifest."""
        self.sync_engine.sync(frozen=frozen)

    def verify_sync_results(self) -> Dict[str, Any]:
        """Verify that the current environment matches the manifest."""
        logger.info("Verifying environment...")
        results = {
            "packages": {"status": "ok", "missing": [], "mismatch": []},
            "containers": {"status": "ok", "missing": [], "not_running": []}
        }

        # 1. Verify Packages
        installed = self.inspector.get_installed_packages(self.manifest.manager)
        # Note: This is a simplified verification.
        # In a real scenario, we'd resolve the full expected list.
        # For now, we check if the explicitly requested packages are present.
        for pkg_name in self.manifest.libraries:
            if pkg_name not in installed:
                results["packages"]["missing"].append(pkg_name)
                results["packages"]["status"] = "error"

        # 2. Verify Services (Containers)
        running = self.inspector.get_running_containers()
        running_names = []
        for c in running:
            # Handle different docker compose ps formats
            name = c.get("Service") or c.get("service") or c.get("Name") or c.get("name")
            if name:
                running_names.append(name)

        # Check standalone services
        standalone_services = self.manifest.services
        for name in standalone_services:
            if name not in running_names:
                results["containers"]["missing"].append(name)
                results["containers"]["status"] = "error"

        return results

    def check(self):
        """Perform a dry-run validation."""
        self.validator.check()

    def search_registry(self, query: str) -> Dict[str, List[str]]:
        return self.registry.search(query)

    def add_library_to_registry(self, *args, **kwargs):
        self.registry.add_library(*args, **kwargs)

    def add_service_to_registry(self, *args, **kwargs):
        self.registry.add_service(*args, **kwargs)

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

    def set_mode(self, name: str, mode: str):
        self.manifest.set_mode(name, mode)
        self.manifest.save()
        logger.info(f"Set mode for {name} to {mode}")

    def set_global_mode(self, mode: str):
        # 1. Standalone libraries
        for name in self.manifest.libraries:
            self.manifest.set_mode(name, mode)
        
        # 2. Library groups
        for group_name in self.manifest.library_groups:
            self.manifest.set_mode(group_name, mode)

        # 3. Service groups
        for group_name in self.manifest.service_groups:
            self.manifest.set_mode(group_name, mode)

        # 4. Standalone services
        for name in self.manifest.services:
            self.manifest.set_mode(name, mode)
        
        self.manifest.save()
        logger.info(f"Set global project mode to {mode}")

    def add_library(self, name: str):
        self.manifest.add_library(name)
        self.manifest.save()
        logger.info(f"Added library {name} to hsm.yaml")

    def add_service(self, name: str):
        self.manifest.add_service(name)
        self.manifest.save()
        logger.info(f"Added service {name} to hsm.yaml")

    def remove_library(self, name: str):
        self.manifest.remove_library(name)
        self.manifest.save()
        logger.info(f"Removed library {name} from hsm.yaml")

    def remove_service(self, name: str):
        self.manifest.remove_service(name)
        self.manifest.save()
        logger.info(f"Removed service {name} from hsm.yaml")

    def remove_group_option(self, group_name: str, option: str):
        self.manifest.remove_from_group(group_name, option)
        self.manifest.save()
        logger.info(f"Removed {option} from group {group_name} in hsm.yaml")

    def remove_group(self, group_name: str):
        self.manifest.remove_group(group_name)
        self.manifest.save()
        logger.info(f"Removed group {group_name} from hsm.yaml")

    def add_group(self, group_name: str, option: str):
        # Logic for adding group selection
        from ..models import RegistryGroup
        group_type = "library_group"
        group_path = self.registry_path / "library_groups" / f"{group_name}.yaml"
        if not group_path.exists():
            group_path = self.registry_path / "service_groups" / f"{group_name}.yaml"
            group_type = "service_group"
            
        if not group_path.exists():
            raise FileNotFoundError(f"Group {group_name} not found in registry")
            
        with open(group_path, "r") as f:
            data = yaml.safe_load(f)
            group = RegistryGroup(**data)
            
        comment = data.get("comment")
        is_service = group_type == "service_group"
            
        self.manifest.set_group(
            group_name=group_name,
            selection=option,
            strategy=group.strategy,
            is_service=is_service,
            comment=comment
        )

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
        group_path = self.registry_path / "library_groups" / f"{group_name}.yaml"
        is_service = False
        if not group_path.exists():
            group_path = self.registry_path / "service_groups" / f"{group_name}.yaml"
            is_service = True
            
        if not group_path.exists():
            raise FileNotFoundError(f"Group {group_name} not found in registry")
            
        with open(group_path, "r") as f:
            data = yaml.safe_load(f)
            strategy = data.get("strategy", "1-of-N")

        self.manifest.add_option_to_group(group_name, option, strategy, is_service=is_service)
        self.manifest.save()
        logger.info(f"Added option {option} to group {group_name} in hsm.yaml")

    def init_library(self, name: str, path: Optional[Path] = None, register: bool = True):
        if path is None:
            path = self.project_root / "packages" / name
        
        if not path.is_absolute():
            path = self.project_root / path

        logger.info(f"Initializing package '{name}' at {path}")
        self.package_adapter.init_lib(path)

        if register:
            rel_path = os.path.relpath(path, self.project_root)
            self.add_library_to_registry(
                name=name,
                version="0.1.0",
                description=f"Local library {name}",
                prod_source={"type": "local", "path": rel_path},
                dev_source={"type": "local", "path": rel_path, "editable": True}
            )