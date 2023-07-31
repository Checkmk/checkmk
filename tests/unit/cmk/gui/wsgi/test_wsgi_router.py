#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import os

import flask
import pytest
import webtest  # type: ignore[import]
from flask import request

from tests.unit.cmk.gui.conftest import WebTestAppForCMK

import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.site import omd_site
from cmk.utils.user import UserId


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


@pytest.mark.skip(reason="flaky")
@pytest.mark.parametrize(
    "setting, url, profiling_files_exist",
    [
        ("profile = True", "/NO_SITE/check_mk/login.py", True),
        ("profile = False", "/NO_SITE/check_mk/login.py", False),
        ('profile = "enable_by_var"', "/NO_SITE/check_mk/login.py?_profile=1", True),
        ('profile = "enable_by_var"', "/NO_SITE/check_mk/login.py", False),
    ],
)
def test_profiling(
    wsgi_app: WebTestAppForCMK, setting: str, url: str, profiling_files_exist: bool
) -> None:
    var_dir = cmk.utils.paths.var_dir
    assert not os.path.exists(var_dir + "/multisite.py")
    assert not os.path.exists(var_dir + "/multisite.profile")
    assert not os.path.exists(var_dir + "/multisite.cachegrind")

    store.save_mk_file(
        cmk.utils.paths.default_config_dir + "/multisite.d/wato/global.mk", f"{setting}\n"
    )

    _ = wsgi_app.get(url, status=200)

    assert os.path.exists(var_dir + "/multisite.py") == profiling_files_exist
    assert os.path.exists(var_dir + "/multisite.profile") == profiling_files_exist
    assert os.path.exists(var_dir + "/multisite.cachegrind") == profiling_files_exist


@pytest.mark.skip(reason="flaky")
@pytest.mark.parametrize(
    "setting, url, profiling_files_exist",
    [
        (
            "profile = True",
            "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
            True,
        ),
        (
            "profile = False",
            "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
            False,
        ),
        (
            'profile = "enable_by_var"',
            "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all?_profile=1",
            True,
        ),
        (
            'profile = "enable_by_var"',
            "/NO_SITE/check_mk/api/1.0/domain-types/folder_config/collections/all",
            False,
        ),
    ],
)
def test_rest_api_profiling(
    logged_in_admin_wsgi_app: WebTestAppForCMK, setting: str, url: str, profiling_files_exist: bool
) -> None:
    var_dir = cmk.utils.paths.var_dir
    assert not os.path.exists(var_dir + "/multisite.py")
    assert not os.path.exists(var_dir + "/multisite.profile")
    assert not os.path.exists(var_dir + "/multisite.cachegrind")

    store.save_mk_file(
        cmk.utils.paths.default_config_dir + "/multisite.d/wato/global.mk", f"{setting}\n"
    )

    _ = logged_in_admin_wsgi_app.get(url, status=200, headers={"Accept": "application/json"})

    assert os.path.exists(var_dir + "/multisite.py") == profiling_files_exist
    assert os.path.exists(var_dir + "/multisite.profile") == profiling_files_exist
    assert os.path.exists(var_dir + "/multisite.cachegrind") == profiling_files_exist


def test_webserver_auth(wsgi_app: WebTestAppForCMK, with_user: tuple[UserId, str]) -> None:
    username, _ = with_user
    wsgi_app.get(
        "/NO_SITE/check_mk/api/1.0/version", headers={"Accept": "application/json"}, status=401
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
        "/NO_SITE/check_mk/api/1.0/version", headers={"Accept": "application/json"}, status=200
    )


def test_openapi_version(
    wsgi_app: WebTestAppForCMK, with_automation_user: tuple[UserId, str]
) -> None:
    username, secret = with_automation_user
    wsgi_app.set_authorization(("Bearer", username + " " + secret))
    resp = wsgi_app.get(
        "/NO_SITE/check_mk/api/1.0/version", headers={"Accept": "application/json"}, status=200
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


def test_cmk_run_cron(wsgi_app: WebTestAppForCMK) -> None:
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


@pytest.mark.usefixtures("suppress_license_expiry_header")
def test_pnp_template(wsgi_app: WebTestAppForCMK) -> None:
    # This got removed some time ago and "Not found" pages are 404 now.
    resp = wsgi_app.get("/NO_SITE/check_mk/pnp_template.py", status=404)
    assert "Page not found" in resp.text
    assert "page_menu_bar" in resp.text
