"""Load and validate project configuration from config.yaml."""

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.yaml"


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """Read config.yaml and return as dict."""
    path = config_path or DEFAULT_CONFIG_PATH
    logger.info("Loading config from %s", path)
    with open(path, "r") as f:
        cfg = yaml.safe_load(f)
    return cfg


def resolve_path(cfg: dict[str, Any], key: str) -> Path:
    """Resolve a relative path from config.paths against project root."""
    rel = cfg["paths"][key]
    return PROJECT_ROOT / rel
