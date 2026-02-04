from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from ruamel.yaml import YAML
from .models import HSMDependency


class HSMProjectManifest:
    """Handles hsm.yaml project manifest with round-trip preservation."""

    def __init__(self, path: Path):
        """Initialize HSMProjectManifest.

        Args:
            path: Path to the hsm.yaml file.
        """
        self.path = path
        self.yaml = YAML()
        self.yaml.indent(mapping=2, sequence=4, offset=2)
        self.yaml.preserve_quotes = True
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        """Load manifest data from file.

        Returns:
            Dictionary with manifest data.
        """
        if not self.path.exists():
            return {
                "project": {"name": "new-project", "version": "0.1.0"},
                "dependencies": {
                    "package_manager": "uv",
                    "package_groups": {},
                    "packages": [],
                },
                "services": {"container_groups": {}},
            }
        with open(self.path, "r") as f:
            return self.yaml.load(f)

    def save(self):
        """Save manifest data back to file."""
        with open(self.path, "w") as f:
            self.yaml.dump(self.data, f)

    @property
    def manager(self) -> str:
        """Get the package manager name.

        Returns:
            Manager name (e.g., 'uv').
        """
        return self.data.get("dependencies", {}).get("package_manager", "uv")

    @property
    def package_groups(self) -> Dict[str, Any]:
        """Get the configured package groups.

        Returns:
            Dictionary of group names and their configurations.
        """
        return self.data.get("dependencies", {}).get("package_groups", {})

    def set_manager(self, manager_name: str):
        """Set the package manager for the project.

        Args:
            manager_name: Name of the manager (e.g., 'uv').
        """
        deps = self.data.setdefault("dependencies", {})
        deps["package_manager"] = manager_name

    @property
    def packages(self) -> List[str]:
        """Get the list of standalone packages.

        Returns:
            List of package names.
        """
        return self.data.get("dependencies", {}).get("packages", [])

    def add_package(self, name: str):
        """Add a standalone package to the manifest.

        Args:
            name: Package name.
        """
        deps = self.data.setdefault("dependencies", {})
        pkgs = deps.setdefault("packages", [])
        if name not in pkgs:
            pkgs.append(name)

    def remove_package(self, name: str):
        """Remove a standalone package from the manifest.

        Args:
            name: Package name.
        """
        pkgs = self.data.get("dependencies", {}).get("packages", [])
        if name in pkgs:
            pkgs.remove(name)

    def remove_from_group(self, group_name: str, option: str):
        """Remove an option from a package group.

        Args:
            group_name: Name of the group.
            option: Option name to remove.
        """
        groups = self.data.get("dependencies", {}).get("package_groups", {})
        if group_name not in groups:
            return

        group_cfg = groups[group_name]
        selection = group_cfg.get("selection")

        if isinstance(selection, list):
            if option in selection:
                selection.remove(option)
        elif selection == option:
            # If it's 1-of-N and we remove the selection, what happens?
            # For now, we just clear it or remove the group entry
            del groups[group_name]

    def remove_group(self, group_name: str):
        """Remove a package group entirely from the manifest.

        Args:
            group_name: Name of the group.
        """
        groups = self.data.get("dependencies", {}).get("package_groups", {})
        if group_name in groups:
            del groups[group_name]

    def add_option_to_group(self, group_name: str, option: str, strategy: str):
        """Add or set an option in a package group.

        Args:
            group_name: Name of the group.
            option: Option name to add/set.
            strategy: Group strategy (1-of-N or M-of-N).
        """
        deps = self.data.setdefault("dependencies", {})
        groups = deps.setdefault("package_groups", {})
        
        group_cfg = groups.setdefault(group_name, {"strategy": strategy, "selection": None})
        
        if strategy == "1-of-N":
            group_cfg["selection"] = option
        else:
            selection = group_cfg.get("selection")
            if selection is None:
                group_cfg["selection"] = [option]
            elif isinstance(selection, str):
                group_cfg["selection"] = [selection, option]
            elif isinstance(selection, list):
                if option not in selection:
                    selection.append(option)

    def set_package_group(
        self,
        group_name: str,
        selection: Union[str, List[str]],
        strategy: str,
        comment: Optional[str] = None,
    ):
        """Set or update a package group in the manifest.

        Args:
            group_name: Name of the group.
            selection: Selected option(s).
            strategy: Selection strategy (1-of-N or M-of-N).
            comment: Optional comment to place above the group.
        """
        deps = self.data.setdefault("dependencies", {})
        groups = deps.setdefault("package_groups", {})

        group_data = {"strategy": strategy, "selection": selection}

        groups[group_name] = group_data

        if comment:
            # Add comment using ruamel.yaml API
            groups.yaml_set_comment_before_after_key(group_name, before=comment)

    def set_package_mode(self, name: str, mode: str):
        """Set the mode (dev/prod) for a package in the manifest.

        Args:
            name: Package name.
            mode: Mode ('dev' or 'prod').
        """
        # This assumes a structure where packages can have modes.
        # For now, let's store it in a 'modes' section or similar if needed,
        # or just update the package entry if it's a dict.
        # HSM specification says hsm.yaml tracks intent.
        modes = self.data.setdefault("modes", {})
        modes[name] = mode

    def get_package_mode(self, name: str) -> str:
        """Get the mode for a package. Defaults to 'prod'."""
        return self.data.get("modes", {}).get(name, "prod")
