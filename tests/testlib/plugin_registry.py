#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
from collections.abc import Iterator
from typing import Any

from cmk.utils.plugin_registry import Registry


@contextlib.contextmanager
def reset_registries(registries: list[Registry[Any]]) -> Iterator[None]:
    """Reset the given registries after completing"""
    defaults_per_registry = [(registry, list(registry)) for registry in registries]
    try:
        yield
    finally:
        for registry, defaults in defaults_per_registry:
            for entry in list(registry):
                if entry not in defaults:
                    registry.unregister(entry)
