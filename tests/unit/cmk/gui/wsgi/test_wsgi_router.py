#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import os
import typing

import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.site import omd_site

if typing.TYPE_CHECKING:
    import webtest  # type: ignore[import] # pylint: disable=unused-import


def test_profiling(wsgi_app) -> None:
    var_dir = cmk.utils.paths.var_dir
    assert not os.path.exists(var_dir + "/multisite.py")
    assert not os.path.exists(var_dir + "/multisite.profile")
    assert not os.path.exists(var_dir + "/multisite.cachegrind")

    store.save_mk_file(
        cmk.utils.paths.default_config_dir + "/multisite.d/wato/global.mk", "profile = True\n"
    )

    _ = wsgi_app.get("/NO_SITE/check_mk/login.py")

    assert os.path.exists(var_dir + "/multisite.py")
    assert os.path.exists(var_dir + "/multisite.profile")
    assert os.path.exists(var_dir + "/multisite.cachegrind")


def test_webserver_auth(wsgi_app, with_user) -> None:
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
        extra_environ={"REMOTE_USER": username},
    )

    wsgi_app.set_authorization(("Basic", ("unknown_random_dude", "foobazbar")))
    wsgi_app.get(
        "/NO_SITE/check_mk/api/1.0/version",
        headers={"Accept": "application/json"},
        status=401,
        extra_environ={"REMOTE_USER": username},
    )


def test_normal_auth(wsgi_app, with_user) -> None:
    username, password = with_user
    wsgi_app.get(
        "/NO_SITE/check_mk/api/1.0/version", headers={"Accept": "application/json"}, status=401
    )

    # Add a failing Basic Auth to check if the other types will succeed.
    wsgi_app.set_authorization(("Basic", ("foobazbar", "foobazbar")))

    login: "webtest.TestResponse" = wsgi_app.get("/NO_SITE/check_mk/login.py")
    login.form["_username"] = username
    login.form["_password"] = password
    resp = login.form.submit("_login", index=1)

    assert "Invalid credentials." not in resp.text

    wsgi_app.get(
        "/NO_SITE/check_mk/api/1.0/version", headers={"Accept": "application/json"}, status=200
    )


def test_openapi_version(wsgi_app, with_automation_user) -> None:
    username, secret = with_automation_user
    wsgi_app.set_authorization(("Bearer", username + " " + secret))
    resp = wsgi_app.get(
        "/NO_SITE/check_mk/api/1.0/version", headers={"Accept": "application/json"}, status=200
    )
    assert resp.json["site"] == omd_site()


def test_openapi_app_exception(wsgi_app_debug_off, with_automation_user) -> None:
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
    assert "crash_report" in resp.json["ext"]
    assert "check_mk" in resp.json["ext"]["crash_report"]["href"]
    assert "crash_id" in resp.json["ext"]


def test_cmk_run_cron(wsgi_app) -> None:
    wsgi_app.get("/NO_SITE/check_mk/run_cron.py", status=200)


def test_cmk_automation(wsgi_app) -> None:
    response = wsgi_app.get("/NO_SITE/check_mk/automation.py", status=200)
    assert response.text == "Missing secret for automation command."


def test_cmk_ajax_graph_images(wsgi_app) -> None:
    resp = wsgi_app.get("/NO_SITE/check_mk/ajax_graph_images.py", status=200)
    assert resp.text.startswith("You are not allowed")

    resp = wsgi_app.get(
        "/NO_SITE/check_mk/ajax_graph_images.py",
        status=200,
        extra_environ={"REMOTE_ADDR": "127.0.0.1"},
    )
    assert resp.text == ""


def test_options_disabled(wsgi_app) -> None:
    # Should be 403 in integration test.
    wsgi_app.options("/", status=404)
