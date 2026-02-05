import yaml
import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from .base import BaseContainerAdapter

logger = logging.getLogger(__name__)

class DockerComposeAdapter(BaseContainerAdapter):
    """Adapter for Docker Compose orchestration."""

    def __init__(self, project_root: Path):
        super().__init__(project_root)
        self.compose_path = project_root / "docker-compose.hsm.yml"

    def generate_config(self, services: List[Dict[str, Any]]):
        """Generate docker-compose.hsm.yml file."""
        compose_data = {
            "services": {}
        }
        for s in services:
            compose_data["services"].update(s)
            
        with open(self.compose_path, "w") as f:
            yaml.dump(compose_data, f, sort_keys=False)
        logger.info(f"Generated {self.compose_path}")

    def up(self, services: Optional[List[str]] = None):
        """Start services using docker compose."""
        cmd = ["docker", "compose", "-f", str(self.compose_path), "up", "-d"]
        if services:
            cmd.extend(services)
        
        try:
            subprocess.run(cmd, check=True, cwd=self.project_root)
        except subprocess.CalledProcessError as e:
            logger.error(f"docker compose up failed: {e}")
            raise

    def down(self):
        """Stop services using docker compose."""
        cmd = ["docker", "compose", "-f", str(self.compose_path), "down"]
        try:
            subprocess.run(cmd, check=True, cwd=self.project_root)
        except subprocess.CalledProcessError as e:
            logger.error(f"docker compose down failed: {e}")
            raise