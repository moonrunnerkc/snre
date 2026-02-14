"""
SNRE Interface Package -- legacy interfaces.
"""

__all__ = ["CLIInterface", "APIInterface", "IntegrationHook"]


def __getattr__(name: str):
    """Lazy imports -- avoid hard flask dep at module collection time."""
    if name == "APIInterface":
        from .api import APIInterface

        return APIInterface
    if name == "CLIInterface":
        from .cli import CLIInterface

        return CLIInterface
    if name == "IntegrationHook":
        from .integration_hook import IntegrationHook

        return IntegrationHook
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
