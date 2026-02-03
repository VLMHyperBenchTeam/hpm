import logging
import yaml
from pathlib import Path
from typing import List, Dict, Optional, Any, Union
from .models import PackageManifest, ContainerManifest, RegistryGroup, HSMDependency
from .manifest import HSMProjectManifest
from .adapters import UvAdapter, BasePackageManagerAdapter

logger = logging.getLogger(__name__)

class HSMCore:
    """Core logic for Hyper Stack Manager (hsm)."""

    def __init__(self, project_root: Optional[Path] = None, registry_path: Optional[Path] = None):
        """Initialize HSMCore.

        Args:
            project_root: Root directory of the project.
            registry_path: Path to the global registry.
        """
        self.project_root = project_root or Path.cwd()
        self.manifest = HSMProjectManifest(self.project_root / "hsm.yaml")
        
        # Initialize adapter based on manifest
        self.adapter = self._get_adapter()
        
        self.registry_path = registry_path or self.project_root / "hsm-registry"

    def _get_adapter(self) -> BasePackageManagerAdapter:
        """Get the appropriate package manager adapter.

        Returns:
            An instance of BasePackageManagerAdapter.
        """
        manager = self.manifest.manager
        if manager == "uv":
            return UvAdapter(self.project_root)
        raise ValueError(f"Unsupported package manager: {manager}")

    def init_project(self, name: Optional[str] = None):
        """Initialize a new HSM project.

        Args:
            name: Project name.
        """
        if not name:
            name = self.project_root.name
        
        logger.info(f"Initializing HSM project: {name}")
        
        # Create hsm.yaml if not exists
        if not self.manifest.path.exists():
            self.manifest.data["project"]["name"] = name
            self.manifest.save()
            logger.info(f"Created {self.manifest.path}")

        # Create registry structure
        for sub_dir in ["packages", "containers", "package_groups", "container_groups"]:
            path = self.registry_path / sub_dir
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured registry directory: {path}")

    def sync(self, frozen: bool = False):
        """Sync project state with the manifest.

        Args:
            frozen: If True, use frozen dependencies (no updates).
        """
        logger.info("Starting HSM sync...")
        
        packages_to_sync = []
        
        # 1. Resolve packages from groups
        for group_name, group_cfg in self.manifest.package_groups.items():
            selection = group_cfg.get("selection")
            if not selection:
                continue
                
            if isinstance(selection, str):
                selections = [selection]
            else:
                selections = selection
            
            for pkg_name in selections:
                pkg_req = self._resolve_package_requirement(pkg_name)
                if pkg_req:
                    packages_to_sync.append(pkg_req)

        # 2. Resolve standalone packages
        for pkg_name in self.manifest.packages:
            pkg_req = self._resolve_package_requirement(pkg_name)
            if pkg_req:
                packages_to_sync.append(pkg_req)

        # 3. Delegate to adapter
        if packages_to_sync:
            self.adapter.sync(packages_to_sync, frozen=frozen)
            logger.info("Sync completed successfully.")
        else:
            logger.info("No packages to sync.")

    def _resolve_package_requirement(self, name: str) -> Optional[str]:
        """Resolve a package name to a requirement string (path or git url).

        Args:
            name: Package name.

        Returns:
            Requirement string for the package manager.
        """
        pkg_path = self.registry_path / "packages" / f"{name}.yaml"
        if not pkg_path.exists():
            logger.warning(f"Package {name} not found in registry")
            return None

        with open(pkg_path, "r") as f:
            data = yaml.safe_load(f)
            manifest = PackageManifest(**data)
        
        # For now, we use 'prod' source by default
        source = manifest.sources.prod
        if not source:
            return None

        if source.type == "local":
            return str(self.project_root / source.path)
        elif source.type == "git":
            req = f"git+{source.url}"
            if source.ref:
                req += f"@{source.ref}"
            return req
        
        return None

    def add_package(self, name: str):
        """Add a standalone package to the manifest.

        Args:
            name: Package name.
        """
        self.manifest.add_package(name)
        self.manifest.save()
        logger.info(f"Added package {name} to hsm.yaml")

    def remove_package(self, name: str):
        """Remove a package from the manifest.

        Args:
            name: Package name.
        """
        self.manifest.remove_package(name)
        self.manifest.save()
        logger.info(f"Removed package {name} from hsm.yaml")

    def remove_package_group(self, group_name: str, option: str):
        """Remove a package group selection from the manifest.

        Args:
            group_name: Name of the group.
            option: Option name to remove.
        """
        self.manifest.remove_from_group(group_name, option)
        self.manifest.save()
        logger.info(f"Removed {option} from group {group_name} in hsm.yaml")

    def add_package_group(self, group_name: str, option: str):
        """Add a package group selection to the manifest.

        Args:
            group_name: Name of the group.
            option: Selected option name.
        """
        # Load group from registry to get strategy and comment
        group_path = self.registry_path / "package_groups" / f"{group_name}.yaml"
        if not group_path.exists():
            raise FileNotFoundError(f"Group {group_name} not found in registry")
            
        with open(group_path, "r") as f:
            data = yaml.safe_load(f)
            group = RegistryGroup(**data)
            
        comment = data.get("comment")
            
        self.manifest.set_package_group(
            group_name=group_name,
            selection=option,
            strategy=group.strategy,
            comment=comment
        )
        self.manifest.save()
        logger.info(f"Added group {group_name} with selection {option} to hsm.yaml")

    def search_registry(self, query: str) -> Dict[str, List[str]]:
        """Search the registry for components.

        Args:
            query: Search query.

        Returns:
            Dictionary with search results.
        """
        results = {"packages": [], "containers": [], "groups": []}
        query = query.lower()
        
        for category in ["packages", "containers", "package_groups", "container_groups"]:
            path = self.registry_path / category
            if path.exists():
                for f in path.glob("*.yaml"):
                    if query in f.stem.lower():
                        key = "groups" if "group" in category else category
                        results[key].append(f.stem)
        return results

    def add_package_to_registry(self, name: str, version: str, description: Optional[str] = None, 
                               prod_source: Optional[Dict] = None, dev_source: Optional[Dict] = None):
        """Add a package manifest to the registry.

        Args:
            name: Package name.
            version: Package version.
            description: Optional description.
            prod_source: Production source data.
            dev_source: Development source data.
        """
        packages_dir = self.registry_path / "packages"
        packages_dir.mkdir(parents=True, exist_ok=True)

        manifest_data = {
            "name": name,
            "version": version,
            "description": description,
            "type": "library",
            "sources": {
                "prod": prod_source,
                "dev": dev_source
            }
        }

        manifest_file = packages_dir / f"{name}.yaml"
        with open(manifest_file, "w") as f:
            yaml.dump(manifest_data, f, sort_keys=False)
        
        logger.info(f"Package '{name}' added to registry at {manifest_file}")

    def get_component_details(self, name: str) -> Optional[Dict[str, Any]]:
        """Get detailed metadata for a component from the registry.

        Args:
            name: Component name.

        Returns:
            Metadata dictionary or None if not found.
        """
        for category in ["packages", "containers", "package_groups", "container_groups"]:
            path = self.registry_path / category / f"{name}.yaml"
            if path.exists():
                with open(path, "r") as f:
                    return yaml.safe_load(f)
        return None
