import subprocess
import logging
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

class UVManager:
    """Wrapper around uv CLI commands."""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def _get_base_cmd(self) -> List[str]:
        """Determines if --system flag is needed."""
        import os
        if os.getenv("HPM_USE_SYSTEM") == "1":
            return ["uv", "--system"]
        return ["uv"]

    def pip_install_editable(self, path: Path):
        """Installs a package in editable mode using uv."""
        logger.info(f"Installing {path} in editable mode...")
        cmd = self._get_base_cmd() + ["pip", "install", "-e", str(path)]
        try:
            subprocess.run(cmd, check=True, cwd=self.project_root)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install {path}: {e}")
            raise

    def sync(self, frozen: bool = False):
        """Syncs the project environment using uv sync."""
        logger.info("Syncing environment with uv...")
        cmd = ["uv", "sync"]
        if frozen:
            cmd.append("--frozen")
        
        try:
            subprocess.run(cmd, check=True, cwd=self.project_root)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to sync environment: {e}")
            raise

    def run_command(self, command: List[str]):
        """Runs a command in the uv environment context."""
        logger.info(f"Running command: {' '.join(command)}")
        # Note: In a real implementation we might want to use os.execvp
        # but for a library/CLI tool subprocess is often safer for tests.
        try:
            subprocess.run(command, check=True, cwd=self.project_root)
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {e}")
            raise