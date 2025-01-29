#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Find all directories that are part of the given implicit namespace package."""

import importlib
import os


def find_namespace_package_paths(namespace_name: str) -> list[str]:
    try:
        namespace_module = importlib.import_module(namespace_name)
    except ModuleNotFoundError:
        return []

    if not hasattr(namespace_module, "__path__"):
        return []  # not a namespace package

    return [os.path.abspath(path) for path in namespace_module.__path__]


print("\n".join(find_namespace_package_paths("cmk")))
