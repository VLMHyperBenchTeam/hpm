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
            # Note: This is a simplified way to add a comment above a key
            groups.yaml_set_comment_before_after_key(group_name, before=comment)
