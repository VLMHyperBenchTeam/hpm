import logging
from pathlib import Path
from typing import List
from ..manifest import HSMProjectManifest

logger = logging.getLogger(__name__)

class Validator:
    """Handles validation and dry-run checks for HSM projects."""

    def __init__(self, manifest: HSMProjectManifest, registry_path: Path):
        self.manifest = manifest
        self.registry_path = registry_path

    def check(self):
        """Perform a dry-run validation of the project and registry."""
        logger.info("Starting HSM check (dry-run)...")
        errors = []

        # 1. Check hsm.yaml existence and basic syntax
        if not self.manifest.path.exists():
            errors.append(f"Manifest file not found: {self.manifest.path}")
        
        # 2. Validate packages
        for pkg in self.manifest.packages:
            name = pkg.get("name") if isinstance(pkg, dict) else pkg
            if not (self.registry_path / "packages" / f"{name}.yaml").exists():
                errors.append(f"Package '{name}' not found in registry")

        # 3. Validate package groups
        for group_name, group_cfg in self.manifest.package_groups.items():
            if not (self.registry_path / "package_groups" / f"{group_name}.yaml").exists():
                errors.append(f"Package group '{group_name}' not found in registry")
            
            selection = group_cfg.get("selection")
            if selection:
                selections = [selection] if isinstance(selection, str) else selection
                for s in selections:
                    if not (self.registry_path / "packages" / f"{s}.yaml").exists():
                        errors.append(f"Selected package '{s}' in group '{group_name}' not found in registry")

        # 4. Validate services
        services = self.manifest.data.get("services", {})
        
        # Standalone containers
        for cont in services.get("containers", []):
            name = cont.get("name") if isinstance(cont, dict) else cont
            if not (self.registry_path / "containers" / f"{name}.yaml").exists():
                errors.append(f"Container '{name}' not found in registry")

        # Container groups
        for group_name, group_cfg in services.get("container_groups", {}).items():
            if not (self.registry_path / "container_groups" / f"{group_name}.yaml").exists():
                errors.append(f"Container group '{group_name}' not found in registry")
            
            selection = group_cfg.get("selection")
            if selection:
                selections = [selection] if isinstance(selection, str) else selection
                for s in selections:
                    if not (self.registry_path / "containers" / f"{s}.yaml").exists():
                        errors.append(f"Selected container '{s}' in group '{group_name}' not found in registry")

        if errors:
            for err in errors:
                logger.error(f"CHECK ERROR: {err}")
            raise ValueError(f"Validation failed with {len(errors)} errors")
        
        logger.info("All checks passed successfully.")