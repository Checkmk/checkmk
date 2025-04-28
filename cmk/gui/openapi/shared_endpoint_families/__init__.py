#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Collection of endpoint families

The structure with `shared_endpoint_families` is temporary while there are still legacy_endpoints
present in the codebase. Once all endpoints have been migrated, the endpoint families should be
moved to the respective endpoint modules.
"""
