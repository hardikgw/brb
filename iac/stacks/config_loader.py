from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"


def _deep_merge(base: dict, override: dict) -> dict:
    result: dict[str, Any] = dict(base)
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(env_name: str) -> dict:
    common_path = CONFIG_DIR / "common.yml"
    env_path = CONFIG_DIR / f"{env_name}.yml"

    if not env_path.exists():
        raise FileNotFoundError(
            f"Config not found for env '{env_name}': {env_path}"
        )

    common = yaml.safe_load(common_path.read_text()) or {}
    env = yaml.safe_load(env_path.read_text()) or {}
    return _deep_merge(common, env)
