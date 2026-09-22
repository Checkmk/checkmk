#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

r"""
Scope
-----

This API provides the types needed to create a monitoring config plug-in: a plug-in
that turns the resolved configuration into one part of the active monitoring
configuration. The configuration of a monitoring core is the most prominent one.

NOTE: this is not (yet) a plug-in API package in the sense of
``packages/cmk-plugin-apis``. It still names types from ``cmk.base``
(``ConfigCache``, ``CoreObjectsConfig``), so it is deliberately kept out of the
``@plugin_apis`` group -- see ``module_layers.toml``.
"""

from ._builder import IntermediateMonitoringConfig, MonitoringConfigBuilder

__all__ = [
    "MonitoringConfigBuilder",
    "IntermediateMonitoringConfig",
]
