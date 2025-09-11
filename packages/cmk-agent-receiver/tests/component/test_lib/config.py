#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pathlib

from cmk.agent_receiver.config import Config, get_config


def create_relay_config(
    *,
    task_ttl: float = 1.0,
    max_number_of_tasks: int = 5,
) -> pathlib.Path:
    """Helper function to create relay configuration files."""
    config = Config(task_ttl=task_ttl, max_tasks_per_relay=max_number_of_tasks)
    config_file = config.config_file
    config_file.write_text(config.model_dump_json())
    get_config.cache_clear()

    return config_file
