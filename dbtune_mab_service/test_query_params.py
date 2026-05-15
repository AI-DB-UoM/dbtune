#!/usr/bin/env python3
"""Tests for query-related tuning parameters in configuration files."""

import os
import sys
from pathlib import Path

import pytest

# Add the parent directory to the import path.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config_loader import ConfigLoader, get_tuning_config, load_config


def _module_dir():
    return Path(__file__).resolve().parent


def _reset_loader():
    ConfigLoader._instance = None
    ConfigLoader._config = None


def _resolve_or_skip(relative_path):
    path = _module_dir() / relative_path
    if not path.exists():
        pytest.skip(f"Config file not found: {path}")
    return path


def _load_for_test(path):
    _reset_loader()
    load_config(str(path))
    return get_tuning_config()


def test_query_params_default():
    default_path = _module_dir() / "configs" / "config.yaml"
    fallback_path = _module_dir() / "configs" / "debug.yaml"
    path = default_path if default_path.exists() else fallback_path
    if not path.exists():
        pytest.skip(f"No default config available: {default_path} or {fallback_path}")

    tuning_config = _load_for_test(path)
    required_keys = ["queries_start", "batch_size", "offset"]
    for key in required_keys:
        assert key in tuning_config, f"Missing key: {key}"


def test_query_params_dev():
    path = _resolve_or_skip(Path("configs") / "config.yaml")
    tuning_config = _load_for_test(path)
    assert tuning_config["batch_size"] == 10


def test_query_params_prod():
    path = _resolve_or_skip(Path("configs") / "config.prod.yaml")
    tuning_config = _load_for_test(path)
    assert tuning_config["batch_size"] == 20


def test_query_params_test():
    path = _resolve_or_skip(Path("configs") / "config.test.yaml")
    tuning_config = _load_for_test(path)
    assert tuning_config["batch_size"] == 5


def test_query_params_default_config():
    path = _resolve_or_skip(Path("configs") / "config_default.yaml")
    tuning_config = _load_for_test(path)
    assert tuning_config["batch_size"] == 10


def test_all_tuning_params():
    default_path = _module_dir() / "configs" / "config.yaml"
    fallback_path = _module_dir() / "configs" / "debug.yaml"
    path = default_path if default_path.exists() else fallback_path
    if not path.exists():
        pytest.skip(f"No config available: {default_path} or {fallback_path}")

    tuning_config = _load_for_test(path)
    required_keys = [
        "hyp_check_rounds",
        "rounds",
        "super_static_context_size",
        "cluster_id_start",
        "queries_start",
        "batch_size",
        "offset",
    ]

    for key in required_keys:
        assert key in tuning_config, f"Missing key: {key}"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
