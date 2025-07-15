#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Test utilities module provides functionality for managing plugin registries and dynamic
module importing.
"""

import contextlib
import importlib.machinery
import importlib.util
import os
import sys
from collections.abc import Iterator
from types import ModuleType
from typing import Any

from cmk.ccc.plugin_registry import Registry
from tests.testlib.common.repo import repo_path


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


def import_module_hack(pathname: str) -> ModuleType:
    """Return the module loaded from `pathname`.

    `pathname` is a path relative to the top-level directory
    of the repository.

    This function loads the module at `pathname` even if it does not have
    the ".py" extension.

    See: https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly
    """
    name = os.path.splitext(os.path.basename(pathname))[0]
    location = os.path.join(repo_path(), pathname)
    loader = importlib.machinery.SourceFileLoader(name, location)
    spec = importlib.machinery.ModuleSpec(name, loader, origin=location)
    spec.has_location = True
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module
