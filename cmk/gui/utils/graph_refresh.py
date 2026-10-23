#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final

# The intervals the global time picker's refresh control offers, and so the ones a user
# profile can preselect. The REST API offers the same intervals; tests/openapi keeps the
# two in sync.
GRAPH_REFRESH_INTERVALS_SECONDS: Final = (30, 60, 90)
