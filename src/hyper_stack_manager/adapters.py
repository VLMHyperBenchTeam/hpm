from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Union
import subprocess
import logging
import tomlkit

logger = logging.getLogger(__name__)

class BasePackageManagerAdapter(ABC):
    """Abstract base class for package manager adapters."""

    @abstractmethod
    def sync(self, packages: List[str], frozen: bool = False):
        """Materialize dependencies into the environment.

        Args:
            packages: List of package requirement strings.
            frozen: If True, do not update dependencies, use lock file.
        """
        pass

    @abstractmethod
    def lock(self):
        """Generate lock file."""
        pass

class UvAdapter(BasePackageManagerAdapter):
    """Adapter for the uv package manager."""

    def __init__(self, project_root: Path):
        """Initialize UvAdapter.

        Args:
            project_root: Root directory of the project.
        """
        self.project_root = project_root
        self.pyproject_path = project_root / "pyproject.toml"

    def _get_base_cmd(self) -> List[str]:
        """Get the base uv command with optional --system flag.

        Returns:
            List of command parts.
        """
        import os
        if os.getenv("HSM_USE_SYSTEM") == "1":
            return ["uv", "--system"]
        return ["uv"]

    def sync(self, packages: List[str], frozen: bool = False):
        """Sync dependencies using uv.

        Args:
            packages: List of package requirement strings.
            frozen: If True, use --frozen flag.
        """
        logger.info(f"Syncing {len(packages)} packages with uv...")
        
        # 1. Update pyproject.toml dependencies
        if self.pyproject_path.exists():
            with open(self.pyproject_path, "r") as f:
                config = tomlkit.parse(f.read())
            
            # Ensure project section exists
            project = config.setdefault("project", tomlkit.table())
            project["dependencies"] = packages
            
            with open(self.pyproject_path, "w") as f:
                f.write(tomlkit.dumps(config))

        # 2. Run uv sync
        cmd = self._get_base_cmd() + ["sync"]
        if frozen:
            cmd.append("--frozen")
        
        try:
            subprocess.run(cmd, check=True, cwd=self.project_root)
        except subprocess.CalledProcessError as e:
            logger.error(f"uv sync failed: {e}")
            raise

    def lock(self):
        """Generate uv.lock file."""
        cmd = self._get_base_cmd() + ["lock"]
        try:
            subprocess.run(cmd, check=True, cwd=self.project_root)
        except subprocess.CalledProcessError as e:
            logger.error(f"uv lock failed: {e}")
            raise