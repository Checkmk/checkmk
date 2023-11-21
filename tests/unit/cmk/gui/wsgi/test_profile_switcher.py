#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest
import werkzeug.test

from tests.unit.cmk.gui.conftest import SetConfig

from cmk.gui.wsgi import profiling


@pytest.mark.parametrize(
    "setting, url, profiling_enabled_expected",
    [
        (
            {"profile": True},
            "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
            True,
        ),
        (
            {"profile": False},
            "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
            False,
        ),
        (
            {"profile": "enable_by_var"},
            "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all?_profile=1",
            True,
        ),
        (
            {"profile": "enable_by_var"},
            "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
            False,
        ),
    ],
)
def test_profile_switcher_under_various_settings(
    setting: dict[str, bool | str],
    url: str,
    profiling_enabled_expected: bool,
    set_config: SetConfig,
) -> None:
    with set_config(**setting):
        environ = werkzeug.test.create_environ(url, method="GET")
        assert profiling_enabled_expected == profiling._profiling_enabled(environ)
