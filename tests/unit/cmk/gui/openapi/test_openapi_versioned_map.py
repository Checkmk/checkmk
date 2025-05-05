#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.openapi.framework.api_config import APIConfig


def test_openapi_api_config_previous_version_raises_exception() -> None:
    """As the map builder works recursively, we need to ensure that when requesting the
    previous version of the first available version a ValueError exception is raised.
    """
    available_versions = APIConfig.get_released_versions()

    if len(available_versions) > 1:
        assert (
            APIConfig.get_previous_released_version(available_versions[-1])
            == available_versions[-2]
        )

    with pytest.raises(ValueError):
        APIConfig.get_previous_released_version(available_versions[0])
