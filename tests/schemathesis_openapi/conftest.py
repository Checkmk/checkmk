#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest


def pytest_collection_modifyitems(items: list[pytest.Function]) -> None:
    """Mark collected tests as type "schemathesis_openapi".

    NOTE: The global collection logic does not work for these dynamically generated tests!
    """
    for item in items:
        item.add_marker(pytest.mark.type.with_args("schemathesis_openapi"))
