#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

RENAMED_GRAPH_TEMPLATES: Mapping[str, str] = {
    "if_errors": "if_errors_discards",
    "robotmk_test_runtime": "METRIC_robotmk_test_runtime",
}
