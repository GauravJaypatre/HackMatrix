"""Loading for deterministic detection-rule configuration."""

import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional


DEFAULT_CONFIG_PATH = Path(__file__).with_name("config.json")


def load_rule_configuration(
    path: Optional[Path] = None,
) -> Dict[str, Dict[str, Any]]:
    """Load the configured rules mapping from JSON."""
    config_path = path or DEFAULT_CONFIG_PATH
    try:
        with config_path.open("r", encoding="utf-8") as config_file:
            document = json.load(config_file)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Unable to load rule configuration: {config_path}") from error

    if not isinstance(document, Mapping):
        raise ValueError("Rule configuration must be a JSON object")
    rules = document.get("rules")
    if not isinstance(rules, Mapping):
        raise ValueError("Rule configuration must contain a 'rules' object")
    if not all(isinstance(rule_id, str) and isinstance(value, Mapping)
               for rule_id, value in rules.items()):
        raise ValueError("Each configured rule must map to an object")
    return {str(rule_id): dict(value) for rule_id, value in rules.items()}