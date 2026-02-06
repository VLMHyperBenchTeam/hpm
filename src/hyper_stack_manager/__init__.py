"""Hyper Stack Manager (hsm) - A meta-orchestrator for dynamic Python and Docker environments."""

__version__ = "0.1.0"

from .core.engine import HSMCore

__all__ = ["HSMCore"]