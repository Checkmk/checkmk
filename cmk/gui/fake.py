#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from types import ModuleType


def module(import_path: tuple[str, ...], module_name: str, attributes: dict[str, object]) -> None:
    if not import_path:
        return
    if import_path[0] != "cmk":
        return
    name = ".".join(import_path + (module_name,))
    m = ModuleType(module_name)
    m.__dict__.update(attributes)
    sys.modules[name] = m
