import os
from pathlib import Path


def _xdg_config_home() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg)
    return Path.home() / ".config"


def _xdg_data_home() -> Path:
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg)
    return Path.home() / ".local" / "share"


CONFIG_DIR = _xdg_config_home() / "yt-music-cli"
DATA_DIR = _xdg_data_home() / "yt-music-cli"
OAUTH_FILE = CONFIG_DIR / "oauth.json"
CONFIG_FILE = CONFIG_DIR / "config.toml"
ERROR_LOG = DATA_DIR / "errors.log"
CACHE_DIR = DATA_DIR / "cache"
HISTORY_FILE = DATA_DIR / "history.json"


def ensure_dirs() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
