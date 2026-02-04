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
        containers_to_sync = []
        
        # 1. Resolve packages from groups
        for group_name, group_cfg in self.manifest.package_groups.items():
            selection = group_cfg.get("selection")
            if not selection:
                continue
                
            selections = [selection] if isinstance(selection, str) else selection
            
            for pkg_name in selections:
                pkg_req = self._resolve_package_requirement(pkg_name)
                if pkg_req:
                    packages_to_sync.append(pkg_req)

        # 2. Resolve standalone packages
        for pkg_name in self.manifest.packages:
            pkg_req = self._resolve_package_requirement(pkg_name)
            if pkg_req:
                packages_to_sync.append(pkg_req)

        # 3. Resolve containers from groups
        container_groups = self.manifest.data.get("services", {}).get("container_groups", {})
        for group_name, group_cfg in container_groups.items():
            selection = group_cfg.get("selection")
            if not selection:
                continue
            selections = [selection] if isinstance(selection, str) else selection
            for cont_name in selections:
                cont_cfg = self._resolve_container_config(cont_name)
                if cont_cfg:
                    containers_to_sync.append(cont_cfg)

        # 4. Resolve standalone containers
        standalone_containers = self.manifest.data.get("services", {}).get("containers", [])
        for cont_name in standalone_containers:
            cont_cfg = self._resolve_container_config(cont_name)
            if cont_cfg:
                containers_to_sync.append(cont_cfg)

        # 5. Delegate to adapter for packages
        if packages_to_sync:
            self.adapter.sync(packages_to_sync, frozen=frozen)
        
        # 6. Generate docker-compose.hsm.yml
        if containers_to_sync:
            self._generate_docker_compose(containers_to_sync)
            logger.info("Docker Compose manifest generated.")

        logger.info("Sync completed successfully.")

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

    def _resolve_container_config(self, name: str) -> Optional[Dict[str, Any]]:
        """Resolve a container name to a docker-compose service config.

        Args:
            name: Container name.

        Returns:
            Service configuration dictionary.
        """
        cont_path = self.registry_path / "containers" / f"{name}.yaml"
        if not cont_path.exists():
            logger.warning(f"Container {name} not found in registry")
            return None

        with open(cont_path, "r") as f:
            data = yaml.safe_load(f)
            manifest = ContainerManifest(**data)
        
        mode = self.manifest.get_package_mode(name)
        source = manifest.sources.dev if mode == "dev" and manifest.sources.dev else manifest.sources.prod
        
        if not source:
            return None

        service_cfg = {
            "container_name": source.container_name or manifest.container_name or name,
            "environment": {**manifest.env, **source.env},
            "ports": list(set(manifest.ports + source.ports)),
            "volumes": list(set(manifest.volumes + source.volumes)),
        }
        
        if manifest.network_aliases or source.network_aliases:
            service_cfg["networks"] = {
                "default": {
                    "aliases": list(set(manifest.network_aliases + source.network_aliases))
                }
            }

        if source.type == "docker-image":
            service_cfg["image"] = source.image
        elif source.type == "build":
            service_cfg["build"] = {
                "context": str(self.project_root / source.path),
            }
            if source.dockerfile:
                service_cfg["build"]["dockerfile"] = source.dockerfile
        elif source.type == "local": # For containers, local might mean build context
             service_cfg["build"] = {"context": str(self.project_root / source.path)}

        return {name: service_cfg}

    def _generate_docker_compose(self, services: List[Dict[str, Any]]):
        """Generate docker-compose.hsm.yml file.

        Args:
            services: List of service configurations.
        """
        compose_data = {
            "version": "3.8",
            "services": {}
        }
        for s in services:
            compose_data["services"].update(s)
            
        compose_path = self.project_root / "docker-compose.hsm.yml"
        with open(compose_path, "w") as f:
            yaml.dump(compose_data, f, sort_keys=False)

    def set_python_manager(self, manager_name: str):
        """Set the python package manager for the project.

        Args:
            manager_name: Name of the manager (e.g., 'uv').
        """
        self.manifest.set_manager(manager_name)
        self.manifest.save()
        logger.info(f"Set python package manager to {manager_name}")

    def set_registry_path(self, path: str):
        """Set the path to the global registry.

        Args:
            path: Path to the registry.
        """
        # This might need to be stored in a user config or project manifest
        # For now, let's assume we update the instance and maybe save to manifest if desired
        self.registry_path = Path(path)
        logger.info(f"Registry path set to {path}")

    def set_package_mode(self, name: str, mode: str):
        """Set the mode for a specific package.

        Args:
            name: Package name.
            mode: Mode ('dev' or 'prod').
        """
        self.manifest.set_package_mode(name, mode)
        self.manifest.save()
        logger.info(f"Set mode for package {name} to {mode}")

    def set_global_mode(self, mode: str):
        """Set the mode for all packages in the project.

        Args:
            mode: Mode ('dev' or 'prod').
        """
        # 1. Standalone packages
        for pkg in self.manifest.packages:
            self.manifest.set_package_mode(pkg, mode)
        
        # 2. Group packages
        for group_name, group_cfg in self.manifest.package_groups.items():
            selection = group_cfg.get("selection")
            if isinstance(selection, str):
                self.manifest.set_package_mode(selection, mode)
            elif isinstance(selection, list):
                for pkg in selection:
                    self.manifest.set_package_mode(pkg, mode)
        
        self.manifest.save()
        logger.info(f"Set global project mode to {mode}")

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

    def remove_group(self, group_name: str):
        """Remove a package group from the project manifest.

        Args:
            group_name: Name of the group.
        """
        self.manifest.remove_group(group_name)
        self.manifest.save()
        logger.info(f"Removed group {group_name} from hsm.yaml")

    def add_package_group(self, group_name: str, option: str):
        """Add a package group selection to the manifest.

        Args:
            group_name: Name of the group.
            option: Selected option name.
        """
        # Try both package and container groups
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
            # Handle container group in manifest
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
                # target_type_group format: "package_group:name" or "container_group:name"
                if ":" in target_type_group:
                    _, target_group_name = target_type_group.split(":", 1)
                    # Recursively add implied group option
                    # Note: This is a simple implementation, might need more robust handling for lists
                    if isinstance(target_option, list):
                        for opt in target_option:
                            self.add_group_option(target_group_name, opt)
                    else:
                        self.add_group_option(target_group_name, target_option)

        self.manifest.save()
        logger.info(f"Added group {group_name} with selection {option} to hsm.yaml")

    def add_group_option(self, group_name: str, option: str):
        """Add an option to a group in the project manifest.

        Args:
            group_name: Name of the group.
            option: Option name to add.
        """
        # Load group from registry to get strategy
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
        """Remove an option from a group in the project manifest.

        Args:
            group_name: Name of the group.
            option: Option name to remove.
        """
        self.manifest.remove_from_group(group_name, option)
        self.manifest.save()
        logger.info(f"Removed option {option} from group {group_name} in hsm.yaml")

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

    def add_container_to_registry(self, name: str, description: Optional[str] = None,
                                 prod_source: Optional[Dict] = None, dev_source: Optional[Dict] = None,
                                 ports: List[str] = None, volumes: List[str] = None, env: Dict[str, str] = None,
                                 container_name: Optional[str] = None, network_aliases: List[str] = None):
        """Add a container manifest to the registry.

        Args:
            name: Container name.
            description: Optional description.
            prod_source: Production source data.
            dev_source: Development source data.
            ports: Common ports.
            volumes: Common volumes.
            env: Common environment variables.
            container_name: Common container name.
            network_aliases: Common network aliases.
        """
        containers_dir = self.registry_path / "containers"
        containers_dir.mkdir(parents=True, exist_ok=True)

        manifest_data = {
            "name": name,
            "description": description,
            "type": "container",
            "container_name": container_name,
            "network_aliases": network_aliases or [],
            "ports": ports or [],
            "volumes": volumes or [],
            "env": env or {},
            "sources": {
                "prod": prod_source,
                "dev": dev_source
            }
        }

        manifest_file = containers_dir / f"{name}.yaml"
        with open(manifest_file, "w") as f:
            yaml.dump(manifest_data, f, sort_keys=False)
        
        logger.info(f"Container '{name}' added to registry at {manifest_file}")

    def add_group_to_registry(self, name: str, group_type: str, strategy: str, options: List[Union[str, Dict]],
                             description: Optional[str] = None, comment: Optional[str] = None):
        """Add a group manifest to the registry.

        Args:
            name: Group name.
            group_type: Type of group (package_group or container_group).
            strategy: Selection strategy (1-of-N or M-of-N).
            options: List of option names (package or container names).
            description: Optional description.
            comment: Optional comment for the manifest.
        """
        category = "package_groups" if group_type == "package_group" else "container_groups"
        groups_dir = self.registry_path / category
        groups_dir.mkdir(parents=True, exist_ok=True)

        processed_options = []
        for opt in options:
            if isinstance(opt, str):
                processed_options.append({"name": opt})
            else:
                processed_options.append(opt)

        manifest_data = {
            "name": name,
            "type": group_type,
            "strategy": strategy,
            "options": processed_options,
        }
        if description:
            manifest_data["description"] = description
        if comment:
            manifest_data["comment"] = comment

        manifest_file = groups_dir / f"{name}.yaml"
        with open(manifest_file, "w") as f:
            yaml.dump(manifest_data, f, sort_keys=False)
        
        logger.info(f"Group '{name}' added to registry at {manifest_file}")

    def remove_from_registry(self, name: str):
        """Remove a component (package, container, or group) from the registry.

        Args:
            name: Component name.
        """
        found = False
        for category in ["packages", "containers", "package_groups", "container_groups"]:
            path = self.registry_path / category / f"{name}.yaml"
            if path.exists():
                path.unlink()
                logger.info(f"Removed {name} from registry ({category})")
                found = True
        
        if not found:
            raise FileNotFoundError(f"Component '{name}' not found in registry")

    def add_option_to_registry_group(self, group_name: str, option: str):
        """Add an option to a group in the registry.

        Args:
            group_name: Name of the group.
            option: Option name to add.
        """
        # Try both package and container groups
        for category in ["package_groups", "container_groups"]:
            path = self.registry_path / category / f"{group_name}.yaml"
            if path.exists():
                with open(path, "r") as f:
                    data = yaml.safe_load(f)
                
                options = data.setdefault("options", [])
                if not any(opt.get("name") == option for opt in options):
                    options.append({"name": option})
                    with open(path, "w") as f:
                        yaml.dump(data, f, sort_keys=False)
                    logger.info(f"Added option {option} to group {group_name} in registry")
                return
        raise FileNotFoundError(f"Group {group_name} not found in registry")

    def remove_option_from_registry_group(self, group_name: str, option: str):
        """Remove an option from a group in the registry.

        Args:
            group_name: Name of the group.
            option: Option name to remove.
        """
        for category in ["package_groups", "container_groups"]:
            path = self.registry_path / category / f"{group_name}.yaml"
            if path.exists():
                with open(path, "r") as f:
                    data = yaml.safe_load(f)
                
                options = data.get("options", [])
                new_options = [opt for opt in options if opt.get("name") != option]
                if len(new_options) != len(options):
                    data["options"] = new_options
                    with open(path, "w") as f:
                        yaml.dump(data, f, sort_keys=False)
                    logger.info(f"Removed option {option} from group {group_name} in registry")
                return
        raise FileNotFoundError(f"Group {group_name} not found in registry")

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
