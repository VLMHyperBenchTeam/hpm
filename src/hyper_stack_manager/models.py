from typing import Dict, List, Optional, Union, Literal, Any
from enum import Enum
from pydantic import BaseModel, Field

class RuntimeType(str, Enum):
    DOCKER = "docker"
    PODMAN = "podman"
    UV = "uv"
    PIXI = "pixi"
    VENV = "venv"

class GroupOption(BaseModel):
    name: str
    description: Optional[str] = None
    implies: Dict[str, Any] = Field(default_factory=dict)

class RegistryGroup(BaseModel):
    name: str
    type: Literal["library_group", "service_group"]
    strategy: Literal["1-of-N", "M-of-N"]
    options: List[GroupOption]
    default: Optional[List[str]] = None
    comment: Optional[str] = None

class Source(BaseModel):
    type: str  # "git", "local", "pypi", "docker-image", "build"
    url: Optional[str] = None
    ref: Optional[str] = None
    path: Optional[str] = None
    editable: bool = False
    subdirectory: Optional[str] = None
    image: Optional[str] = None
    # Docker specific
    container_name: Optional[str] = None
    network_aliases: List[str] = Field(default_factory=list)
    ports: List[str] = Field(default_factory=list)
    volumes: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)
    dockerfile: Optional[str] = None

class ManifestSources(BaseModel):
    prod: Optional[Source] = None
    dev: Optional[Source] = None

class HSMDependency(BaseModel):
    name: str
    version: str = "*"

class LibraryManifest(BaseModel):
    name: str
    version: str
    description: Optional[str] = None
    type: Literal["library", "virtual"] = "library"
    sources: ManifestSources
    dependencies: List[Union[str, HSMDependency]] = Field(default_factory=list)
    implies: Dict[str, Any] = Field(default_factory=dict)
    entrypoints: Dict[str, str] = Field(default_factory=dict)

class DeploymentProfile(BaseModel):
    mode: Literal["managed", "external"] = "managed"
    runtime: RuntimeType = RuntimeType.DOCKER
    external: Optional[Dict[str, Any]] = None
    env: Dict[str, str] = Field(default_factory=dict)
    command: Optional[str] = None
    working_dir: Optional[str] = None

class ServiceManifest(BaseModel):
    name: str
    description: Optional[str] = None
    type: Literal["service"] = "service"
    # Common orchestration settings (mostly for docker/podman)
    container_name: Optional[str] = None
    network_aliases: List[str] = Field(default_factory=list)
    ports: List[str] = Field(default_factory=list)
    volumes: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)
    sources: ManifestSources
    deployment_profiles: Dict[str, DeploymentProfile] = Field(default_factory=dict)