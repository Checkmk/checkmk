#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import importlib.util
import os
import os.path
import types
from importlib._bootstrap_external import SourceFileLoader  # type: ignore[import]

import flask
import pytest
import webtest  # type: ignore[import]
from flask import request
from werkzeug.test import create_environ

from tests.unit.cmk.gui.conftest import WebTestAppForCMK

from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection
from cmk.utils.site import omd_site
from cmk.utils.user import UserId


def search_up(search_path: str, start_path: str) -> str:
    current_path = start_path

    while True:
        full_path = os.path.join(current_path, search_path)
        if os.path.exists(full_path):
            return os.path.abspath(full_path)

        new_path = os.path.dirname(current_path)

        if new_path == current_path:
            raise ValueError(f"Path {search_path!r} not found starting from {start_path!r}")

        current_path = new_path


def test_wsgi_app() -> None:
    app_file = search_up("cmk/gui/wsgi/applications/index.wsgi", os.path.dirname(__file__))
    imported = _import_file(app_file)
    wsgi_app = imported.Application
    env = create_environ()

    def start_response(status, response_headers, exc_info=None):
        pass

    assert wsgi_app.config_loader.mode == "default"
    wsgi_app(env, start_response)
    assert wsgi_app.config_loader.mode == "imported"


def _import_file(file_name: str) -> types.ModuleType:
    loader: SourceFileLoader = SourceFileLoader("index", file_name)
    file_spec = importlib.util.spec_from_file_location(
        "index",
        file_name,
        loader=loader,
    )
    if file_spec is None:
        raise ValueError(f"Module {file_name} could not be found.")

    file_spec.loader = loader
    imported = importlib.util.module_from_spec(file_spec)

    assert file_spec.loader is not None
    file_spec.loader.exec_module(imported)
    return imported


def test_request_url(flask_app: flask.Flask) -> None:
    url = "/NO_SITE/check_mk/api/1.0/objects/activation_run/123/actions/wait-for-completion/invoke"
    with flask_app.test_request_context(
        environ_overrides={
            "apache.version": "foo",
            "PATH_INFO": url,
            "SCRIPT_NAME": url,
        },
    ):
        flask_app.preprocess_request()
        assert request.url == f"http://localhost{url}"


def test_webserver_auth(wsgi_app: WebTestAppForCMK, with_user: tuple[UserId, str]) -> None:
    username, _ = with_user
    wsgi_app.get(
        "/NO_SITE/check_mk/api/1.0/version",
        headers={"Accept": "application/json"},
        status=401,
    )

    wsgi_app.get(
        "/NO_SITE/check_mk/api/1.0/version",
        headers={"Accept": "application/json"},
        status=401,
        extra_environ={"REMOTE_USER": "unknown_random_dude"},
    )

    wsgi_app.get(
        "/NO_SITE/check_mk/api/1.0/version",
        headers={"Accept": "application/json"},
        status=200,
        extra_environ={"REMOTE_USER": str(username)},
    )

    wsgi_app.set_authorization(("Basic", ("unknown_random_dude", "foobazbar")))
    wsgi_app.get(
        "/NO_SITE/check_mk/api/1.0/version",
        headers={"Accept": "application/json"},
        status=401,
        extra_environ={"REMOTE_USER": str(username)},
    )


def test_normal_auth(base: str, wsgi_app: WebTestAppForCMK, with_user: tuple[UserId, str]) -> None:
    username, password = with_user
    wsgi_app.get(f"{base}/version", headers={"Accept": "application/json"}, status=401)

    # Add a failing Basic Auth to check if the other types will succeed.
    wsgi_app.set_authorization(("Basic", ("foobazbar", "foobazbar")))

    login: webtest.TestResponse = wsgi_app.get("/NO_SITE/check_mk/login.py", status=200)
    login.form["_username"] = username
    login.form["_password"] = password
    resp = login.form.submit("_login", index=1)

    assert "Invalid credentials." not in resp.text

    wsgi_app.set_authorization(None)
    wsgi_app.get(
        "/NO_SITE/check_mk/api/1.0/version",
        headers={"Accept": "application/json"},
        status=200,
    )


def test_openapi_version(
    wsgi_app: WebTestAppForCMK, with_automation_user: tuple[UserId, str]
) -> None:
    username, secret = with_automation_user
    wsgi_app.set_authorization(("Bearer", username + " " + secret))
    resp = wsgi_app.get(
        "/NO_SITE/check_mk/api/1.0/version",
        headers={"Accept": "application/json"},
        status=200,
    )
    assert resp.json["site"] == omd_site()


def test_openapi_app_exception(
    wsgi_app_debug_off: WebTestAppForCMK, with_automation_user: tuple[UserId, str]
) -> None:
    wsgi_app = wsgi_app_debug_off
    username, secret = with_automation_user
    wsgi_app.set_authorization(("Bearer", username + " " + secret))
    resp = wsgi_app.get(
        "/NO_SITE/check_mk/api/1.0/version?fail=1",
        headers={"Accept": "application/json"},
        status=500,
    )
    assert "detail" in resp.json
    assert "title" in resp.json
    assert "crash_report_url" in resp.json["ext"]["details"]
    assert "check_mk" in resp.json["ext"]["details"]["crash_report_url"]["href"]
    assert "id" in resp.json["ext"]


def test_cmk_run_cron(
    wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    with mock_livestatus():
        # 'execute_deprecation_tests_and_notify_users' connects via livestatus
        wsgi_app.get("/NO_SITE/check_mk/run_cron.py", status=200)


def test_cmk_automation(wsgi_app: WebTestAppForCMK) -> None:
    response = wsgi_app.get("/NO_SITE/check_mk/automation.py", status=200)
    assert response.text == "Missing secret for automation command."


def test_cmk_ajax_graph_images(wsgi_app: WebTestAppForCMK) -> None:
    resp = wsgi_app.get("/NO_SITE/check_mk/ajax_graph_images.py", status=200)
    assert resp.text.startswith("You are not allowed")

    resp = wsgi_app.get(
        "/NO_SITE/check_mk/ajax_graph_images.py",
        status=200,
        extra_environ={"REMOTE_ADDR": "127.0.0.1"},
    )
    assert resp.text == ""


def test_options_disabled(wsgi_app: WebTestAppForCMK) -> None:
    # Should be 403 in integration test.
    wsgi_app.options("/", status=404)


@pytest.mark.usefixtures("suppress_license_expiry_header", "suppress_license_banner")
def test_pnp_template(wsgi_app: WebTestAppForCMK) -> None:
    # This got removed some time ago and "Not found" pages are 404 now.
    resp = wsgi_app.get("/NO_SITE/check_mk/pnp_template.py", status=404)
    assert "Page not found" in resp.text
    assert "page_menu_bar" in resp.text
