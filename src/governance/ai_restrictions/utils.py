"""Small configuration, directory, logging, and project-location utilities."""

import logging
from pathlib import Path
from typing import Any, Iterable

import yaml

AI_ADOPTION_PANEL_RELATIVE_PATH = Path("data/interim/panels/ai_adoption_fy2020_2025")


def find_project_root(start: Path | None = None) -> Path:
    """Find this project's root from a file or directory."""
    current = (start if start is not None else Path(__file__)).resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").is_file() and (
            candidate / "config" / "project.yaml"
        ).is_file():
            return candidate
    raise FileNotFoundError("Project root not found.")


def load_config(path: Path) -> dict[str, Any]:
    """Load a YAML mapping, rejecting empty or non-mapping configuration."""
    with path.open(encoding="utf-8") as stream:
        config = yaml.safe_load(stream)
    if not isinstance(config, dict):
        raise ValueError(f"Expected a YAML mapping: {path}")
    return config


def ensure_directories(paths: Iterable[Path]) -> None:
    """Create directories without modifying existing file contents."""
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def configure_logging(level: int = logging.INFO) -> None:
    """Configure console logging."""
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")
