#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pathlib

import pytest
import werkzeug.test

from tests.unit.cmk.web_test_app import SetConfig

from cmk.gui.config import active_config
from cmk.gui.wsgi.applications.profile_switcher import (
    LazyImportProfilingMiddleware,
    ProfileConfigLoader,
    ProfileSetting,
)


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
    request_context: None,
) -> None:
    with set_config(**setting):
        environ = werkzeug.test.create_environ(url, method="GET")
        profile_setting = ProfileSetting(
            mode=active_config.profile,  # type: ignore[arg-type]
            cachegrind_file=pathlib.Path(".") / "multisite.cachegrind",
            profile_file=pathlib.Path(".") / "multisite.profile",
            accumulate=False,
            discard_first_request=False,
        )
        middleware = LazyImportProfilingMiddleware(
            app_factory_module="cmk.gui.wsgi.app",
            app_factory_name="make_wsgi_app",
            app_factory_args=(True,),
            app_factory_kwargs={},
            config_loader=ProfileConfigLoader(
                fetch_actual_config=lambda: profile_setting,
                fetch_default_config=lambda: profile_setting,
            ),
        )
        should_profile = middleware.should_profile(environ)
        assert profiling_enabled_expected == should_profile
