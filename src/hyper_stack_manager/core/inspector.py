import json
import subprocess
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class EnvironmentInspector:
    """Inspects the current environment (packages and containers)."""

    def get_installed_packages(self, manager: str) -> Dict[str, str]:
        """
        Get installed packages and their versions.
        
        Args:
            manager: Package manager to use (uv, pixi, pip).
            
        Returns:
            Dict of {package_name: version}.
        """
        try:
            if manager == "uv":
                result = subprocess.run(
                    ["uv", "pip", "list", "--format", "json"],
                    capture_output=True, text=True, check=True
                )
                data = json.loads(result.stdout)
                return {pkg["name"]: pkg["version"] for pkg in data}
            
            elif manager == "pixi":
                result = subprocess.run(
                    ["pixi", "list", "--json"],
                    capture_output=True, text=True, check=True
                )
                data = json.loads(result.stdout)
                return {pkg["name"]: pkg["version"] for pkg in data}
            
            elif manager == "pip":
                result = subprocess.run(
                    ["pip", "list", "--format", "json"],
                    capture_output=True, text=True, check=True
                )
                data = json.loads(result.stdout)
                return {pkg["name"]: pkg["version"] for pkg in data}
            
            else:
                logger.warning(f"Unsupported manager for inspection: {manager}")
                return {}
                
        except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Failed to get packages from {manager}: {e}")
            return {}

    def get_running_containers(self) -> List[Dict[str, Any]]:
        """
        Get running containers via docker compose.
        
        Returns:
            List of container info dicts.
        """
        try:
            # Try to find docker-compose.hsm.yml first, fallback to default
            cmd = ["docker", "compose"]
            if (subprocess.run(["ls", "docker-compose.hsm.yml"], capture_output=True).returncode == 0):
                cmd.extend(["-f", "docker-compose.hsm.yml"])
            
            cmd.extend(["ps", "--format", "json"])
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # docker compose ps --format json might return multiple JSON objects (one per line)
            # or a single JSON array depending on the version.
            output = result.stdout.strip()
            if not output:
                return []
                
            try:
                return json.loads(output)
            except json.JSONDecodeError:
                # Try line by line
                containers = []
                for line in output.splitlines():
                    if line.strip():
                        containers.append(json.loads(line))
                return containers
                
        except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Failed to get running containers: {e}")
            return []

    def inspect_container_env(self, service_name: str) -> Dict[str, str]:
        """
        Get environment variables from a running container.
        
        Args:
            service_name: Name of the service in docker-compose.
            
        Returns:
            Dict of env variables.
        """
        try:
            cmd = ["docker", "compose"]
            if (subprocess.run(["ls", "docker-compose.hsm.yml"], capture_output=True).returncode == 0):
                cmd.extend(["-f", "docker-compose.hsm.yml"])
            
            cmd.extend(["exec", service_name, "env"])
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            env_vars = {}
            for line in result.stdout.splitlines():
                if "=" in line:
                    key, val = line.split("=", 1)
                    env_vars[key] = val
            return env_vars
            
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error(f"Failed to inspect container env for {service_name}: {e}")
            return {}