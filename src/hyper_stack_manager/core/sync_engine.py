import logging
import yaml
from pathlib import Path
from typing import List, Dict, Optional, Any
from ..models import LibraryManifest, ServiceManifest
from ..manifest import HSMProjectManifest
from ..adapters.base import BasePackageManagerAdapter, BaseContainerAdapter

logger = logging.getLogger(__name__)

class SyncEngine:
    """Handles dependency resolution and environment synchronization."""

    def __init__(self, project_root: Path, manifest: HSMProjectManifest, 
                 registry_path: Path, package_adapter: BasePackageManagerAdapter,
                 container_adapter: BaseContainerAdapter):
        self.project_root = project_root
        self.manifest = manifest
        self.registry_path = registry_path
        self.package_adapter = package_adapter
        self.container_adapter = container_adapter

    def sync(self, frozen: bool = False):
        """Sync project state with the manifest."""
        logger.info("Starting HSM sync...")
        
        packages_to_sync = {} # Use dict to ensure uniqueness by name
        containers_to_sync = []
        
        # Implication Merging: registry_id -> list of params
        merged_implies_params: Dict[str, List[Dict[str, Any]]] = {}

        def collect_implies(implies: Dict[str, Any]):
            for target, config in implies.items():
                params = {}
                if isinstance(config, dict):
                    params = config.get("params", {})
                
                if target not in merged_implies_params:
                    merged_implies_params[target] = []
                merged_implies_params[target].append(params)

        # 1. Resolve libraries from groups
        for group_name, group_cfg in self.manifest.library_groups.items():
            selection = group_cfg.get("selection")
            if not selection:
                continue
                
            selections = [selection] if isinstance(selection, str) else selection
            
            for pkg_name in selections:
                pkg_req = self._resolve_package_requirement(pkg_name)
                if pkg_req:
                    packages_to_sync[pkg_name] = pkg_req
                    # Collect implies from group selection
                    group_path = self.registry_path / "library_groups" / f"{group_name}.yaml"
                    if group_path.exists():
                        with open(group_path, "r") as f:
                            g_data = yaml.safe_load(f)
                            opt = next((o for o in g_data.get("options", []) if o["name"] == pkg_name), None)
                            if opt and "implies" in opt:
                                collect_implies(opt["implies"])

        # 2. Resolve standalone libraries
        for pkg_name in self.manifest.libraries:
            pkg_req = self._resolve_package_requirement(pkg_name)
            if pkg_req:
                packages_to_sync[pkg_name] = pkg_req
                # Collect implies from standalone library
                pkg_manifest_path = self.registry_path / "libraries" / f"{pkg_name}.yaml"
                if pkg_manifest_path.exists():
                    with open(pkg_manifest_path, "r") as f:
                        p_data = yaml.safe_load(f)
                        if "implies" in p_data:
                            collect_implies(p_data["implies"])

        # 3. Resolve services from groups
        for group_name, group_cfg in self.manifest.service_groups.items():
            selection = group_cfg.get("selection")
            if not selection:
                continue
            selections = [selection] if isinstance(selection, str) else selection
            for cont_name in selections:
                cont_cfg = self._resolve_container_config(cont_name)
                if cont_cfg:
                    containers_to_sync.append(cont_cfg)

        # 4. Resolve standalone services
        for cont_name in self.manifest.services:
            cont_cfg = self._resolve_container_config(cont_name)
            if cont_cfg:
                containers_to_sync.append(cont_cfg)

        # 4.5 Process Merged Implies
        for target, params_list in merged_implies_params.items():
            if ":" in target:
                target_type, target_name = target.split(":", 1)
                if target_type == "service":
                    # Merge params
                    merged_params = {}
                    for p in params_list:
                        for k, v in p.items():
                            if k not in merged_params:
                                merged_params[k] = []
                            if v not in merged_params[k]:
                                merged_params[k].append(v)
                    
                    # Resolve container with merged params
                    cont_cfg = self._resolve_container_config(target_name, merged_params)
                    if cont_cfg:
                        containers_to_sync.append(cont_cfg)

        # 5. Delegate to adapter for packages
        if packages_to_sync:
            self.package_adapter.sync(list(packages_to_sync.values()), frozen=frozen)
        
        # 6. Generate docker-compose.hsm.yml
        if containers_to_sync:
            self.container_adapter.generate_config(containers_to_sync)
            logger.info("Docker Compose manifest generated.")

        logger.info("Sync completed successfully.")

    def _resolve_package_requirement(self, name: str) -> Optional[str]:
        """Resolve a library name to a requirement string."""
        pkg_path = self.registry_path / "libraries" / f"{name}.yaml"
        if not pkg_path.exists():
            logger.warning(f"Library {name} not found in registry")
            return None

        with open(pkg_path, "r") as f:
            data = yaml.safe_load(f)
            manifest = LibraryManifest(**data)
        
        mode = self.manifest.get_mode(name)
        source = manifest.sources.dev if mode == "dev" and manifest.sources.dev else manifest.sources.prod
        
        if not source:
            return None

        if source.type == "local":
            path = Path(source.path)
            if not path.is_absolute():
                path = self.project_root / path
            return f"{name} @ {path.as_uri()}"
        elif source.type == "git":
            req = f"{name} @ git+{source.url}"
            if source.ref:
                req += f"@{source.ref}"
            return req
        
        return None

    def _resolve_container_config(self, name: str, merged_params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Resolve a service name to a docker-compose service config."""
        cont_path = self.registry_path / "services" / f"{name}.yaml"
        if not cont_path.exists():
            logger.warning(f"Service {name} not found in registry")
            return None

        with open(cont_path, "r") as f:
            data = yaml.safe_load(f)
            manifest = ServiceManifest(**data)
        
        # Check for profile in manifest
        profile_name = None
        # Check service groups
        for g_cfg in self.manifest.service_groups.values():
            selection = g_cfg.get("selection")
            if selection == name or (isinstance(selection, (list, tuple)) and name in selection):
                profile_name = g_cfg.get("profile")
                break
        
        # Check standalone services
        if not profile_name:
            srvs = self.manifest.data.get("services", {}).get("standalone", [])
            for srv in srvs:
                if isinstance(srv, dict) and srv.get("name") == name:
                    profile_name = srv.get("profile")
                    break

        if profile_name and profile_name in manifest.deployment_profiles:
            profile = manifest.deployment_profiles[profile_name]
            if profile.mode == "external":
                logger.info(f"Service {name} is in external mode (profile: {profile_name}), skipping docker-compose.")
                return None

        mode = self.manifest.get_mode(name)
        source = manifest.sources.dev if mode == "dev" and manifest.sources.dev else manifest.sources.prod
        
        if not source:
            return None

        # Prepare environment with merged params support
        env = {**manifest.env, **source.env}
        if merged_params:
            for k, v in merged_params.items():
                # Support ${HSM_MERGED_PARAMS.key}
                placeholder = f"${{HSM_MERGED_PARAMS.{k}}}"
                val_str = ",".join(map(str, v))
                
                # Replace in env values
                for env_k, env_v in env.items():
                    if isinstance(env_v, str) and placeholder in env_v:
                        env[env_k] = env_v.replace(placeholder, val_str)

        service_cfg = {
            "container_name": source.container_name or manifest.container_name or name,
            "environment": env,
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