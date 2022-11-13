#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Module to hold shared code for internals and the plugins"""

from typing import Any

InventoryHintSpec = dict[str, Any]


# TODO: Refactor to plugin_registries
view_hooks: dict = {}
inventory_displayhints: dict[str, InventoryHintSpec] = {}
# For each view a function can be registered that has to return either True
# or False to show a view as context link
view_is_enabled: dict = {}
