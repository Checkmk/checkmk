#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
For version 2.2.* mcafee plugins have been migrated (and modified) only as an mk package.
Further breaking changes to the plugins (e.g. changes in versions 2.3 onwards) should not be backported
to this version 2.2.* in order to keep the mkp in question functional.

Relevant tickets:
- https://jira.lan.tribe29.com/browse/SUP-17218
- https://jira.lan.tribe29.com/browse/SUP-17842
"""


from ..agent_based_api.v1 import contains

DETECT_EMAIL_GATEWAY = contains(".1.3.6.1.2.1.1.1.0", "mcafee email gateway")
