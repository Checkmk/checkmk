#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Temporary compatibility layer for m365_service_health-1.2.1.mkp"""

from cmk.agent_based.v1.type_defs import StringTable  # pylint: disable=unused-import

Parameters = object  # not even used by the plugin
