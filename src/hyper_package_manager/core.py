import yaml
import logging
try:
    import tomllib
except ImportError:
    import tomli as tomllib
import tomli_w
from pathlib import Path
from typing import List, Dict, Optional
from .models import Manifest, Source, RegistryGroup
from .uv_manager import UVManager

logger = logging.getLogger(__name__)

class HPMCore:
    """Core logic for HyperPackageManager."""

    def __init__(self, project_root: Optional[Path] = None, registry_path: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.uv = UVManager(self.project_root)
        
        # Try to load registry path from pyproject.toml
        self.registry_path = registry_path
        if not self.registry_path:
            self.registry_path = self._get_registry_path_from_config()
        
        if not self.registry_path:
            self.registry_path = self.project_root / "registry"

    def _get_registry_path_from_config(self) -> Optional[Path]:
        pyproject_path = self.project_root / "pyproject.toml"
        if pyproject_path.exists():
            with open(pyproject_path, "rb") as f:
                config = tomllib.load(f)
            path_str = config.get("tool", {}).get("hpm", {}).get("registry")
            if path_str:
                return self.project_root / path_str
        return None

    def init_project(self, name: Optional[str] = None, version: Optional[str] = None, description: Optional[str] = None, python_version: Optional[str] = None, registry_dir: str = "hpm-registry"):
        """Initializes a new project with HPM support."""
        pyproject_path = self.project_root / "pyproject.toml"
        
        if not pyproject_path.exists():
            if not name:
                name = self.project_root.name
            logger.info(f"pyproject.toml does not exist. Initializing new uv project: {name}")
            # Use uv init to create base structure
            self.uv.run_command(["uv", "init", "--name", name, "--no-workspace"])
        else:
            logger.info("pyproject.toml already exists. Using existing configuration as base.")
        
        # Read current config
        with open(pyproject_path, "rb") as f:
            config = tomllib.load(f)
        
        # Update project metadata if provided or if missing
        if "project" not in config:
            config["project"] = {}
        
        if name:
            config["project"]["name"] = name
        if version:
            config["project"]["version"] = version
        if description:
            config["project"]["description"] = description
        if python_version:
            config["project"]["requires-python"] = python_version
        
        # Add HPM configuration
        if "tool" not in config:
            config["tool"] = {}
        if "hpm" not in config["tool"]:
            logger.info(f"Adding HPM configuration to [tool.hpm] in pyproject.toml")
            config["tool"]["hpm"] = {}
        
        if config["tool"]["hpm"].get("registry") != registry_dir:
            logger.info(f"Setting HPM registry path to: {registry_dir}")
            config["tool"]["hpm"]["registry"] = registry_dir
        
        # Ensure build-system uses uv_build as requested
        if "build-system" not in config:
            config["build-system"] = {}
        config["build-system"]["requires"] = ["uv_build>=0.9.26"]
        config["build-system"]["build-backend"] = "uv_build"

        # Write back updated config
        with open(pyproject_path, "wb") as f:
            tomli_w.dump(config, f)
        
        # Create directory structure
        reg_path = self.project_root / registry_dir
        for sub_dir in ["groups", "packages"]:
            path = reg_path / sub_dir
            if not path.exists():
                logger.info(f"Creating registry directory: {path}")
                path.mkdir(parents=True, exist_ok=True)
        
        pkg_dir = self.project_root / "packages"
        if not pkg_dir.exists():
            logger.info(f"Creating plugins directory: {pkg_dir}")
            pkg_dir.mkdir(parents=True, exist_ok=True)

        # Ensure .gitignore exists
        gitignore_path = self.project_root / ".gitignore"
        if not gitignore_path.exists():
            logger.info("Creating default .gitignore")
            default_ignore = [
                ".venv/",
                "__pycache__/",
                "*.py[cod]",
                "*$py.class",
                ".hpm/",
                "dist/",
                "build/",
                "*.egg-info/",
            ]
            with open(gitignore_path, "w") as f:
                f.write("\n".join(default_ignore) + "\n")
        
        logger.info(f"HPM project '{name}' initialized successfully.")

    def load_group(self, group_name: str) -> RegistryGroup:
        """Loads a group definition from the registry."""
        group_file = self.registry_path / "groups" / f"{group_name}.yaml"
        if not group_file.exists():
            raise FileNotFoundError(f"Group definition not found: {group_file}")
        
        with open(group_file, "r") as f:
            data = yaml.safe_load(f)
        
        return RegistryGroup(**data)

    def list_groups(self) -> List[RegistryGroup]:
        """Lists all groups in the registry."""
        groups_dir = self.registry_path / "groups"
        if not groups_dir.exists():
            return []
        
        groups = []
        for f in groups_dir.glob("*.yaml"):
            with open(f, "r") as file:
                data = yaml.safe_load(file)
                groups.append(RegistryGroup(**data))
        return groups

    def search_registry(self, query: str) -> Dict[str, List[str]]:
        """Searches for groups and packages in the registry."""
        results = {"groups": [], "packages": []}
        query = query.lower()

        # Search groups
        groups_dir = self.registry_path / "groups"
        if groups_dir.exists():
            for f in groups_dir.glob("*.yaml"):
                if query in f.stem.lower():
                    results["groups"].append(f.stem)

        # Search packages
        packages_dir = self.registry_path / "packages"
        if packages_dir.exists():
            for f in packages_dir.glob("*.yaml"):
                if query in f.stem.lower():
                    results["packages"].append(f.stem)
        
        return results

    def add_package_to_registry(self, name: str, source_type: str, url_or_path: str, version: str = "0.1.0"):
        """Adds a package manifest to the registry."""
        packages_dir = self.registry_path / "packages"
        packages_dir.mkdir(parents=True, exist_ok=True)

        from .models import ManifestSources, Source
        
        source_data = {"type": source_type}
        if source_type == "git":
            source_data["url"] = url_or_path
        else:
            source_data["path"] = url_or_path
            source_data["editable"] = True

        manifest_data = {
            "name": name,
            "version": version,
            "sources": ManifestSources(prod=Source(**source_data)),
        }

        manifest_file = packages_dir / f"{name}.yaml"
        with open(manifest_file, "w") as f:
            yaml.dump(manifest_data, f)
        
        logger.info(f"Package '{name}' added to registry at {manifest_file}")

    def load_manifest(self, path: Path) -> Manifest:
        """Loads and parses an hpm.yaml manifest."""
        if not path.exists():
            raise FileNotFoundError(f"Manifest not found: {path}")
        
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        
        return Manifest(**data)

    def add_group_option(self, group_name: str, option_name: str):
        """Adds a group option to the project configuration in pyproject.toml."""
        group = self.load_group(group_name)
        
        # Validate option
        valid_options = [opt.name for opt in group.options]
        if option_name not in valid_options:
            raise ValueError(f"Invalid option '{option_name}' for group '{group_name}'. Valid options: {valid_options}")

        pyproject_path = self.project_root / "pyproject.toml"
        if not pyproject_path.exists():
            # Create a minimal pyproject.toml if it doesn't exist (though it should in our context)
            config = {}
        else:
            with open(pyproject_path, "rb") as f:
                config = tomllib.load(f)

        if "tool" not in config:
            config["tool"] = {}
        if "hpm" not in config["tool"]:
            config["tool"]["hpm"] = {}
        if "groups" not in config["tool"]["hpm"]:
            config["tool"]["hpm"]["groups"] = {}

        if group.strategy == "1-of-N":
            config["tool"]["hpm"]["groups"][group_name] = option_name
        else:
            current = config["tool"]["hpm"]["groups"].get(group_name, [])
            if not isinstance(current, list):
                current = [current]
            if option_name not in current:
                current.append(option_name)
            config["tool"]["hpm"]["groups"][group_name] = current

        with open(pyproject_path, "wb") as f:
            tomli_w.dump(config, f)
        
        logger.info(f"Added option '{option_name}' to group '{group_name}' in pyproject.toml")

    def check(self):
        """Validates if current group configuration is resolvable using uv lock --dry-run."""
        pyproject_path = self.project_root / "pyproject.toml"
        if not pyproject_path.exists():
            raise FileNotFoundError(f"pyproject.toml not found at {pyproject_path}")

        with open(pyproject_path, "rb") as f:
            config = tomllib.load(f)

        hpm_config = config.get("tool", {}).get("hpm", {})
        groups_config = hpm_config.get("groups", {})

        if not groups_config:
            logger.info("No HPM groups to check")
            return

        logger.info("Checking dependency resolution (Dry Run)...")
        # uv lock --dry-run checks if dependencies can be resolved without changing the lockfile
        # Note: In some uv versions it might be just 'uv lock' if it's already fast or 'uv sync --dry-run'
        # According to ADR, we use 'uv lock' for validation.
        self.uv.run_command(["uv", "lock"])
        logger.info("Resolution check successful")

    def sync(self):
        """Materializes groups into uv dependencies."""
        pyproject_path = self.project_root / "pyproject.toml"
        if not pyproject_path.exists():
            raise FileNotFoundError(f"pyproject.toml not found at {pyproject_path}")

        with open(pyproject_path, "rb") as f:
            config = tomllib.load(f)

        hpm_config = config.get("tool", {}).get("hpm", {})
        groups_config = hpm_config.get("groups", {})

        if not groups_config:
            logger.info("No HPM groups configured in pyproject.toml")
            return

        packages_to_add = []
        for group_name, options in groups_config.items():
            if isinstance(options, str):
                options = [options]
            
            for opt_name in options:
                # Find package in registry
                pkg_manifest_path = self.registry_path / "packages" / f"{opt_name}.yaml"
                if not pkg_manifest_path.exists():
                    logger.warning(f"Package manifest not found for option '{opt_name}' in group '{group_name}'")
                    continue
                
                manifest = self.load_manifest(pkg_manifest_path)
                # For now, we assume 'prod' source and 'local' or 'git'
                source = manifest.sources.prod
                if not source:
                    continue

                if source.type == "local":
                    # Path relative to registry or absolute?
                    # Usually relative to the manifest file
                    abs_path = pkg_manifest_path.parent / source.path
                    packages_to_add.append(str(abs_path))
                elif source.type == "git":
                    git_url = f"git+{source.url}"
                    if source.ref:
                        git_url += f"@{source.ref}"
                    packages_to_add.append(git_url)

        if packages_to_add:
            logger.info(f"Syncing packages: {packages_to_add}")
            # Use uv add to update pyproject.toml dependencies and lock file
            self.uv.run_command(["uv", "add"] + packages_to_add)
        else:
            logger.info("No packages to sync")

    def install_plugin(self, manifest_path: Path, mode: str = "prod"):
        """Installs a plugin based on its manifest and mode."""
        manifest = self.load_manifest(manifest_path)
        logger.info(f"Installing plugin: {manifest.name} (version: {manifest.version}) in {mode} mode")

        source = getattr(manifest.sources, mode)
        if not source:
            raise ValueError(f"Source for mode '{mode}' not defined in manifest for {manifest.name}")

        if source.type == "local":
            plugin_path = manifest_path.parent / source.path
            if source.editable:
                self.uv.pip_install_editable(plugin_path)
            else:
                # Basic implementation: just use uv pip install
                self.uv.run_command(["uv", "pip", "install", str(plugin_path)])
        elif source.type == "git":
            # uv supports git urls directly
            git_url = f"git+{source.url}"
            if source.ref:
                git_url += f"@{source.ref}"
            self.uv.run_command(["uv", "pip", "install", git_url])
        else:
            raise NotImplementedError(f"Source type '{source.type}' not yet supported in HPM Lite")

    def run_entrypoint(self, manifest_path: Path, entrypoint_name: str):
        """Runs a command defined in the manifest entrypoints."""
        manifest = self.load_manifest(manifest_path)
        if entrypoint_name not in manifest.entrypoints:
            raise KeyError(f"Entrypoint '{entrypoint_name}' not found in manifest for {manifest.name}")
        
        command_str = manifest.entrypoints[entrypoint_name]
        command = command_str.split()
        self.uv.run_command(command)