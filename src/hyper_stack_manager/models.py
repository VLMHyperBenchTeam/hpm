from typing import Dict, List, Optional, Union, Literal
from pydantic import BaseModel, Field

class GroupOption(BaseModel):
    name: str
    description: Optional[str] = None
    implies: Dict[str, Union[str, List[str]]] = Field(default_factory=dict)

class RegistryGroup(BaseModel):
    name: str
    type: Literal["package_group", "container_group"]
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

class PackageManifest(BaseModel):
    name: str
    version: str
    description: Optional[str] = None
    type: Literal["library", "service", "virtual"] = "library"
    sources: ManifestSources
    dependencies: List[Union[str, HSMDependency]] = Field(default_factory=list)
    entrypoints: Dict[str, str] = Field(default_factory=dict)

class ContainerManifest(BaseModel):
    name: str
    description: Optional[str] = None
    type: Literal["container"] = "container"
    # Common orchestration settings
    container_name: Optional[str] = None
    network_aliases: List[str] = Field(default_factory=list)
    ports: List[str] = Field(default_factory=list)
    volumes: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)
    sources: ManifestSources