from importlib import metadata


try:
    __version__ = metadata.version("nanana")
except metadata.PackageNotFoundError:  # pragma: no cover - best effort for local runs.
    __version__ = "0.0.0+local"


def hello() -> str:
    return "Hello from nanana!"


__all__ = ["hello", "__version__"]
