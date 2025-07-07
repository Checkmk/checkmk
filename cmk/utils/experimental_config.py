#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping
from pathlib import Path

_BASE_NAME = "experimental.mk"


def load_experimental_config(config_dir: Path) -> Mapping[str, object]:
    """Returns file with experimental settings to be used.
    Used to enable features that are "in development" and not good enough to be enabled by default.
    Example of experimental.mk:
    {"config_storage_format": "raw"}
    """
    try:
        raw = (config_dir / _BASE_NAME).read_text()
    except FileNotFoundError:
        return {}
    return {str(k): v for k, v in json.loads(raw).items()}
