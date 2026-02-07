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
        
        # 2. Validate libraries
        for name in self.manifest.libraries:
            if not (self.registry_path / "libraries" / f"{name}.yaml").exists():
                errors.append(f"Library '{name}' not found in registry")

        # 3. Validate library groups
        for group_name, group_cfg in self.manifest.library_groups.items():
            if not (self.registry_path / "library_groups" / f"{group_name}.yaml").exists():
                errors.append(f"Library group '{group_name}' not found in registry")
            
            selection = group_cfg.get("selection")
            if selection:
                selections = [selection] if isinstance(selection, str) else selection
                for s in selections:
                    if not (self.registry_path / "libraries" / f"{s}.yaml").exists():
                        errors.append(f"Selected library '{s}' in group '{group_name}' not found in registry")

        # 4. Validate services
        # Standalone services
        for name in self.manifest.services:
            if not (self.registry_path / "services" / f"{name}.yaml").exists():
                errors.append(f"Service '{name}' not found in registry")

        # Service groups
        for group_name, group_cfg in self.manifest.service_groups.items():
            if not (self.registry_path / "service_groups" / f"{group_name}.yaml").exists():
                errors.append(f"Service group '{group_name}' not found in registry")
            
            selection = group_cfg.get("selection")
            if selection:
                selections = [selection] if isinstance(selection, str) else selection
                for s in selections:
                    if not (self.registry_path / "services" / f"{s}.yaml").exists():
                        errors.append(f"Selected service '{s}' in group '{group_name}' not found in registry")

        if errors:
            for err in errors:
                logger.error(f"CHECK ERROR: {err}")
            raise ValueError(f"Validation failed with {len(errors)} errors")
        
        logger.info("All checks passed successfully.")