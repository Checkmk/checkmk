#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pathlib
import threading
from collections.abc import Iterable
from wsgiref.types import StartResponse, WSGIEnvironment

import pytest
import werkzeug.test

from cmk.gui.config import active_config
from cmk.gui.wsgi.applications.profile_switcher import (
    DirectWrappingProfilingMiddleware,
    LazyImportProfilingMiddleware,
    ProfileConfigLoader,
    ProfileSetting,
)
from tests.testlib.unit.gui.web_test_app import SetConfig


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
@pytest.mark.usefixtures("request_context")
def test_profile_switcher_under_various_settings(
    setting: dict[str, bool | str],
    url: str,
    profiling_enabled_expected: bool,
    set_config: SetConfig,
) -> None:
    with set_config(**setting):
        environ = werkzeug.test.create_environ(url, method="GET")
        profile_setting = ProfileSetting(
            mode=active_config.profile,  # type: ignore[arg-type]
            cachegrind_file=pathlib.Path(".") / "multisite.cachegrind",
            profile_file=pathlib.Path(".") / "multisite.profile",
            accumulate=False,
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
        should_profile = middleware.should_profile(profile_setting, environ)
        assert profiling_enabled_expected == should_profile


def test_a_profiled_request_waits_for_the_running_requests(tmp_path: pathlib.Path) -> None:
    request_running = threading.Event()
    end_request = threading.Event()
    events: list[str] = []

    def app(environ: WSGIEnvironment, _start_response: StartResponse) -> Iterable[bytes]:
        if "_profile" in environ["QUERY_STRING"]:
            events.append("profiled request")
        else:
            events.append("request started")
            request_running.set()
            end_request.wait(timeout=10)
            events.append("request ended")
        return []

    setting = ProfileSetting(
        mode="enable_by_var",
        cachegrind_file=tmp_path / "multisite.cachegrind",
        profile_file=tmp_path / "multisite.profile",
    )
    middleware = DirectWrappingProfilingMiddleware(
        app,
        ProfileConfigLoader(
            fetch_actual_config=lambda: setting, fetch_default_config=lambda: setting
        ),
    )

    def call(url: str) -> None:
        middleware(werkzeug.test.create_environ(url), lambda *_args: lambda _data: None)

    request = threading.Thread(target=call, args=("/NO_SITE/check_mk/index.py",))
    profiled_request = threading.Thread(
        target=call, args=("/NO_SITE/check_mk/index.py?_profile=1",)
    )
    request.start()
    request_running.wait(timeout=10)
    profiled_request.start()
    # Give the profiled request the chance to start while the other request is running
    profiled_request.join(timeout=0.2)
    end_request.set()
    request.join()
    profiled_request.join()

    assert events == ["request started", "request ended", "profiled request"]
