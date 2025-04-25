#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from __future__ import annotations

from collections.abc import Iterator

import pytest
from flask import Flask
from pytest_mock import MockerFixture

from tests.unit.cmk.web_test_app import (
    WebTestAppForCMK,
)

from cmk.ccc.user import UserId

import cmk.utils.log

import cmk.gui.config as config_module
import cmk.gui.watolib.password_store
from cmk.gui import hooks, http, main_modules
from cmk.gui.utils import get_failed_plugins
from cmk.gui.utils.script_helpers import session_wsgi_app


def create_flask_app() -> Iterator[Flask]:
    """Initialize a Flask app for testing purposes.

    Register a global htmllib.html() instance, just like in the regular GUI.
    """
    app = session_wsgi_app(debug=False, testing=True)
    with app.test_request_context():
        app.preprocess_request()
        yield app
        app.process_response(http.Response())


def create_wsgi_app(flask_app: Flask) -> Iterator[WebTestAppForCMK]:
    """Yield a Flask test client."""
    flask_app.test_client_class = WebTestAppForCMK
    with flask_app.test_client() as client:
        if isinstance(client, WebTestAppForCMK):
            yield client
        else:
            raise TypeError(
                f"Expected flask client of type: 'WebTestAppForCMK' and not '{type(client)}'!"
            )


def create_aut_user_auth_wsgi_app(
    wsgi_app: WebTestAppForCMK,
    with_automation_user: tuple[UserId, str],
) -> WebTestAppForCMK:
    username, secret = with_automation_user
    wsgi_app.set_authorization(("Bearer", f"{username} {secret}"))
    return wsgi_app


def validate_background_job_annotation(
    request: pytest.FixtureRequest, mocker: MockerFixture
) -> None:
    """Unannotated background job call

    Tests must not execute logic in background job processes, which may continue to run
    independently of the test case.

    If your test shall execute a background job, the default is to annotate your test with the
    `inline_background_jobs` fixture above. It makes the background job run synchronously so that
    the test code waits for the job to complete. In many cases this is the desired behavior and
    makes it easier to deal with the jobs in the tests.

    However, in some cases you actually want to have a backrgound job being executed as in the
    production environment. In that case, you need to define a local  klacono-op finamed
    "inline_background_jobs" to override these global fixtures.xture

    This autoload fixture is here to make you aware of the fact that you are calling a background
    job and that you have to decide explicitly which behavior you want to have.
    """
    if (
        "inline_background_jobs" in request.fixturenames
        or "allow_background_jobs" in request.fixturenames
    ):
        return

    mocker.patch(
        "cmk.gui.background_job._base.BackgroundJob.start",
        side_effect=RuntimeError(validate_background_job_annotation.__doc__),
    )


def perform_gui_cleanup_after_test(
    mocker: MockerFixture,
) -> Iterator[None]:
    # deactivate_search_index_building_at_requenst_end.
    mocker.patch("cmk.gui.watolib.search.updates_requested", return_value=False)
    yield
    # In case some tests use @request_memoize but don't use the request context, we'll emit the
    # clear event after each request.
    hooks.call("request-end")


def perform_load_config() -> Iterator[None]:
    old_root_log_level = cmk.utils.log.logger.getEffectiveLevel()
    config_module.initialize()
    yield
    cmk.utils.log.logger.setLevel(old_root_log_level)


def perform_load_plugins() -> None:
    main_modules.load_plugins()
    if errors := get_failed_plugins():
        raise Exception(f"The following errors occured during plug-in loading: {errors}")
