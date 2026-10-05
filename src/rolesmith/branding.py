import importlib.metadata

APP_NAME = "Rolesmith"
PKG = "rolesmith"
CLI = "rolesmith"
ENV_PREFIX = "ROLESMITH_"

try:
    __version__ = importlib.metadata.version(PKG)
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.1.0"
