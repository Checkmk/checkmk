#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
JSON parsing for Kubernetes API objects.

This file contains helper functions to parse JSON received from the Kubernetes
API into version independent data structures defined in `schemata.api`. This
parsing is an alternate approach to the Kubernetes client. The Kubernetes
client could no longer be upgraded, because v1.23.3 would reject valid
API data, see CMK-10826.
"""
