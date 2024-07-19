#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.plugin_registry import Registry

from .base import Dashlet


class DashletRegistry(Registry[type[Dashlet]]):
    """The management object for all available plugins."""

    def plugin_name(self, instance):
        return instance.type_name()


dashlet_registry = DashletRegistry()
