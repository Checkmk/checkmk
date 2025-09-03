#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import pathlib


def create_relay_config(
    base_dir: pathlib.Path,
    task_ttl: float = 1.0,
) -> pathlib.Path:
    """Helper function to create relay configuration files."""
    config_data = {"task_ttl": task_ttl}

    # Create the config file with the exact name expected by RelayConfig.load()
    config_file = base_dir / "relay_config.json"
    with config_file.open("w", encoding="utf-8") as f:
        json.dump(config_data, f)

    return config_file
