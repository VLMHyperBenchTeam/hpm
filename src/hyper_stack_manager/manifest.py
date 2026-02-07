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
                "libraries": {
                    "package_manager": "uv",
                    "groups": {},
                    "standalone": [],
                },
                "services": {
                    "groups": {},
                    "standalone": [],
                },
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
        return self.data.get("libraries", {}).get("package_manager", "uv")

    @property
    def library_groups(self) -> Dict[str, Any]:
        """Get the configured library groups.

        Returns:
            Dictionary of group names and their configurations.
        """
        return self.data.get("libraries", {}).get("groups", {})

    @property
    def service_groups(self) -> Dict[str, Any]:
        """Get the configured service groups.

        Returns:
            Dictionary of group names and their configurations.
        """
        return self.data.get("services", {}).get("groups", {})

    def set_manager(self, manager_name: str):
        """Set the package manager for the project.

        Args:
            manager_name: Name of the manager (e.g., 'uv').
        """
        libs = self.data.setdefault("libraries", {})
        libs["package_manager"] = manager_name

    @property
    def libraries(self) -> List[str]:
        """Get the list of standalone libraries.

        Returns:
            List of library names.
        """
        pkgs = self.data.get("libraries", {}).get("standalone", [])
        result = []
        for pkg in pkgs:
            if isinstance(pkg, str):
                result.append(pkg)
            elif isinstance(pkg, dict) and "name" in pkg:
                result.append(pkg["name"])
        return result

    @property
    def services(self) -> List[str]:
        """Get the list of standalone services.

        Returns:
            List of service names.
        """
        srvs = self.data.get("services", {}).get("standalone", [])
        result = []
        for srv in srvs:
            if isinstance(srv, str):
                result.append(srv)
            elif isinstance(srv, dict) and "name" in srv:
                result.append(srv["name"])
        return result

    def add_library(self, name: str):
        """Add a standalone library to the manifest.

        Args:
            name: Library name.
        """
        libs = self.data.setdefault("libraries", {})
        pkgs = libs.setdefault("standalone", [])
        if name not in pkgs:
            pkgs.append(name)

    def add_service(self, name: str):
        """Add a standalone service to the manifest.

        Args:
            name: Service name.
        """
        srvs_root = self.data.setdefault("services", {})
        srvs = srvs_root.setdefault("standalone", [])
        if name not in srvs:
            srvs.append(name)

    def remove_library(self, name: str):
        """Remove a standalone library from the manifest.

        Args:
            name: Library name.
        """
        pkgs = self.data.get("libraries", {}).get("standalone", [])
        if name in pkgs:
            pkgs.remove(name)

    def remove_service(self, name: str):
        """Remove a standalone service from the manifest.

        Args:
            name: Service name.
        """
        srvs = self.data.get("services", {}).get("standalone", [])
        if name in srvs:
            srvs.remove(name)

    def remove_from_group(self, group_name: str, option: str):
        """Remove an option from a library or service group.

        Args:
            group_name: Name of the group.
            option: Option name to remove.
        """
        # Check libraries
        groups = self.data.get("libraries", {}).get("groups", {})
        if group_name not in groups:
            # Check services
            groups = self.data.get("services", {}).get("groups", {})
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
        """Remove a library or service group entirely from the manifest.

        Args:
            group_name: Name of the group.
        """
        # Check libraries
        groups = self.data.get("libraries", {}).get("groups", {})
        if group_name in groups:
            del groups[group_name]
            return

        # Check services
        groups = self.data.get("services", {}).get("groups", {})
        if group_name in groups:
            del groups[group_name]

    def add_option_to_group(self, group_name: str, option: str, strategy: str, is_service: bool = False):
        """Add or set an option in a library or service group.

        Args:
            group_name: Name of the group.
            option: Option name to add/set.
            strategy: Group strategy (1-of-N or M-of-N).
            is_service: Whether this is a service group.
        """
        root_key = "services" if is_service else "libraries"
        root = self.data.setdefault(root_key, {})
        groups = root.setdefault("groups", {})
        
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

    def set_group(
        self,
        group_name: str,
        selection: Union[str, List[str]],
        strategy: str,
        is_service: bool = False,
        comment: Optional[str] = None,
    ):
        """Set or update a library or service group in the manifest.

        Args:
            group_name: Name of the group.
            selection: Selected option(s).
            strategy: Selection strategy (1-of-N or M-of-N).
            is_service: Whether this is a service group.
            comment: Optional comment to place above the group.
        """
        root_key = "services" if is_service else "libraries"
        root = self.data.setdefault(root_key, {})
        groups = root.setdefault("groups", {})

        group_data = {"strategy": strategy, "selection": selection}

        groups[group_name] = group_data

        if comment:
            # Add comment using ruamel.yaml API
            groups.yaml_set_comment_before_after_key(group_name, before=comment)

    def set_mode(self, name: str, mode: str):
        """Set the mode (dev/prod) for a component or group in the manifest.

        Args:
            name: Component or group name.
            mode: Mode ('dev' or 'prod').
        """
        # 1. Check library groups
        groups = self.data.get("libraries", {}).get("groups", {})
        if name in groups:
            groups[name]["mode"] = mode
            return

        # 2. Check standalone libraries
        pkgs = self.data.get("libraries", {}).get("standalone", [])
        for i, pkg in enumerate(pkgs):
            if isinstance(pkg, str) and pkg == name:
                pkgs[i] = {"name": name, "mode": mode}
                return
            elif isinstance(pkg, dict) and pkg.get("name") == name:
                pkg["mode"] = mode
                return

        # 3. Check service groups
        s_groups = self.data.get("services", {}).get("groups", {})
        if name in s_groups:
            s_groups[name]["mode"] = mode
            return

        # 4. Check standalone services
        services = self.data.get("services", {}).get("standalone", [])
        for i, srv in enumerate(services):
            if isinstance(srv, str) and srv == name:
                services[i] = {"name": name, "mode": mode}
                return
            elif isinstance(srv, dict) and srv.get("name") == name:
                srv["mode"] = mode
                return
        
        # Fallback: store in a generic modes section if not found in structure
        modes = self.data.setdefault("modes", {})
        modes[name] = mode

    def get_mode(self, name: str) -> str:
        """Get the mode for a component or group. Defaults to 'prod'."""
        # 1. Check library groups
        groups = self.data.get("libraries", {}).get("groups", {})
        if name in groups and "mode" in groups[name]:
            return groups[name]["mode"]
        
        # Check if name is a selection in any library group
        for g_cfg in groups.values():
            selection = g_cfg.get("selection")
            if selection == name or (isinstance(selection, (list, tuple)) and name in selection):
                return g_cfg.get("mode", "prod")

        # 2. Check standalone libraries
        pkgs = self.data.get("libraries", {}).get("standalone", [])
        for pkg in pkgs:
            if isinstance(pkg, dict) and pkg.get("name") == name:
                return pkg.get("mode", "prod")

        # 3. Check service groups
        s_groups = self.data.get("services", {}).get("groups", {})
        if name in s_groups and "mode" in s_groups[name]:
            return s_groups[name]["mode"]
            
        # Check if name is a selection in any service group
        for g_cfg in s_groups.values():
            selection = g_cfg.get("selection")
            if selection == name or (isinstance(selection, (list, tuple)) and name in selection):
                return g_cfg.get("mode", "prod")

        # 4. Check standalone services
        services = self.data.get("services", {}).get("standalone", [])
        for srv in services:
            if isinstance(srv, dict) and srv.get("name") == name:
                return srv.get("mode", "prod")

        # 5. Check generic modes section
        return self.data.get("modes", {}).get(name, "prod")
