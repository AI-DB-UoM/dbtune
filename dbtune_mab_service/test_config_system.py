#!/usr/bin/env python3
"""Tests for the configuration system."""

import os
import sys
from pathlib import Path

import pytest
import yaml

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _candidate_config_paths():
    module_dir = Path(__file__).resolve().parent
    return [
        module_dir / "configs" / "config.yaml",
        module_dir / "configs" / "debug.yaml",
        Path("config.yaml"),
        module_dir / "config.yaml",
        module_dir.parent / "config.yaml",
    ]


def _resolve_config_path():
    for path in _candidate_config_paths():
        if path.exists():
            return path
    pytest.skip(f"No config file found. Tried: {[str(p) for p in _candidate_config_paths()]}")


def test_config_file_exists():
    config_path = _resolve_config_path()
    assert config_path.exists()


def test_yaml_parsing():
    config_path = _resolve_config_path()
    with config_path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    assert config is not None
    assert isinstance(config, dict)


def test_config_loader_import():
    from config_loader import (
        get_bandit_config,
        get_config,
        get_db_config,
        get_logging_config,
        get_system_config,
        get_tuning_config,
        load_config,
    )

    assert callable(load_config)
    assert callable(get_config)
    assert callable(get_db_config)
    assert callable(get_system_config)
    assert callable(get_tuning_config)
    assert callable(get_bandit_config)
    assert callable(get_logging_config)


def test_config_loading():
    from config_loader import get_config, load_config

    config_path = _resolve_config_path()
    loaded = load_config(str(config_path))

    required_sections = ["database", "system", "tuning", "bandit", "logging"]
    for section in required_sections:
        assert section in loaded, f"Missing section: {section}"

    assert get_config() == loaded


def test_database_config():
    from config_loader import get_db_config, load_config

    load_config(str(_resolve_config_path()))
    db_config = get_db_config()

    required_fields = ["dbname", "user", "host", "port"]
    for field in required_fields:
        assert field in db_config, f"Missing field: {field}"


def test_system_config():
    from config_loader import get_system_config, load_config

    load_config(str(_resolve_config_path()))
    system_config = get_system_config()

    required_fields = ["enable_tune", "with_mv", "mv", "max_memory", "hyp_file"]
    for field in required_fields:
        assert field in system_config, f"Missing field: {field}"

    assert isinstance(system_config["enable_tune"], bool)
    assert isinstance(system_config["max_memory"], int)


def test_tuning_config():
    from config_loader import get_tuning_config, load_config

    load_config(str(_resolve_config_path()))
    tuning_config = get_tuning_config()

    required_fields = ["hyp_check_rounds", "rounds", "super_static_context_size", "cluster_id_start"]
    for field in required_fields:
        assert field in tuning_config, f"Missing field: {field}"
        assert isinstance(tuning_config[field], int), f"{field} should be integer"

    assert tuning_config["rounds"] > 0


def test_bandit_config():
    from config_loader import get_bandit_config, load_config

    load_config(str(_resolve_config_path()))
    bandit_config = get_bandit_config()

    required_fields = ["input_alpha", "input_lambda"]
    for field in required_fields:
        assert field in bandit_config, f"Missing field: {field}"

    assert 0 <= bandit_config["input_alpha"] <= 1
    assert isinstance(bandit_config["input_lambda"], (int, float))


def test_logging_config():
    from config_loader import get_logging_config, load_config

    load_config(str(_resolve_config_path()))
    logging_config = get_logging_config()

    required_fields = ["log_file", "log_level"]
    for field in required_fields:
        assert field in logging_config, f"Missing field: {field}"

    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    assert logging_config["log_level"] in valid_levels


def test_singleton_pattern():
    from config_loader import ConfigLoader

    loader1 = ConfigLoader()
    loader2 = ConfigLoader()
    assert loader1 is loader2


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))

