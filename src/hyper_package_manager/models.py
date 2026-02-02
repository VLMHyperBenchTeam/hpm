from typing import Dict, List, Optional, Union, Literal
from pydantic import BaseModel, Field

class GroupOption(BaseModel):
    name: str
    description: Optional[str] = None

class RegistryGroup(BaseModel):
    name: str
    type: Literal["group"] = "group"
    strategy: Literal["1-of-N", "M-of-N"]
    options: List[GroupOption]
    default: Optional[List[str]] = None

class Source(BaseModel):
    type: str  # "git", "local", "pypi"
    url: Optional[str] = None
    ref: Optional[str] = None
    path: Optional[str] = None
    editable: bool = False
    subdirectory: Optional[str] = None

class ManifestSources(BaseModel):
    prod: Optional[Source] = None
    dev: Optional[Source] = None

class HPMDependency(BaseModel):
    name: str
    version: str = "*"

class Manifest(BaseModel):
    name: str
    version: str
    description: Optional[str] = None
    type: str = "library"  # "library", "service", "virtual"
    sources: ManifestSources
    dependencies: List[Union[str, HPMDependency]] = Field(default_factory=list)
    entrypoints: Dict[str, str] = Field(default_factory=dict)