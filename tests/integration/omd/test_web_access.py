#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import CMKWebSession
from tests.testlib.site import Site

from cmk.utils import version as cmk_version


@pytest.mark.parametrize(
    "file_path,url",
    [
        ("var/www/testfile", "/%s/testfile"),
        ("local/share/check_mk/web/htdocs/testfile", "/%s/check_mk/local/testfile"),
    ],
)
def test_www_dir(site: Site, file_path: str, url: str) -> None:
    web = CMKWebSession(site)

    url = url % site.id
    # unauthenticated = denied
    web.get(url, expected_code=401)
    web.get(url, auth=("cmkadmin", site.admin_password), expected_code=404)

    try:
        site.write_text_file(file_path, "123")
        assert web.get(url, auth=("cmkadmin", site.admin_password)).text == "123"
    finally:
        site.delete_file(file_path)


def test_base_path_redirects(site: Site) -> None:
    web = CMKWebSession(site)
    expected_target = "%s://%s:%d/%s/check_mk/" % (
        site.http_proto,
        site.http_address,
        site.apache_port,
        site.id,
    )

    web.check_redirect("/%s" % site.id, expected_target=expected_target)
    web.check_redirect("/%s/" % site.id, expected_target=expected_target)
    web.check_redirect("/%s/check_mk" % site.id, expected_target=expected_target)


def test_base_path_access(site: Site) -> None:
    web = CMKWebSession(site)
    expected_target = "/%s/check_mk/login.py?_origtarget=index.py" % site.id

    # TODO: Figure out if which status code we *really* expect here: 301 or 302?
    web.check_redirect("/%s/check_mk/" % site.id, expected_target=expected_target)

    web.check_redirect("/%s/check_mk/index.py" % site.id, expected_target=expected_target)


def test_cmk_agents_access(site: Site) -> None:
    web = CMKWebSession(site)
    body = web.get("/%s/check_mk/agents" % site.id).text
    assert "Index of" in body


def test_cmk_local_agents_access(site: Site) -> None:
    web = CMKWebSession(site)
    body = web.get("/%s/check_mk/local/agents" % site.id).text
    assert "Index of" in body


def test_cmk_sounds(site: Site) -> None:
    web = CMKWebSession(site)
    response = web.get("/%s/check_mk/sounds/ok.wav" % site.id)
    assert response.headers["Content-Type"] == "audio/x-wav"


def test_cmk_automation(site: Site) -> None:
    web = CMKWebSession(site)
    response = web.get("/%s/check_mk/automation.py" % site.id)
    assert response.text == "Missing secret for automation command."


@pytest.mark.skipif(cmk_version.is_raw_edition(), reason="agent deployment not supported on CRE")
def test_cmk_deploy_agent(site: Site) -> None:
    web = CMKWebSession(site)
    response = web.get("/%s/check_mk/deploy_agent.py" % site.id)
    assert response.text.startswith("ERROR: Missing")


def test_cmk_run_cron(site: Site) -> None:
    web = CMKWebSession(site)
    web.get("/%s/check_mk/run_cron.py" % site.id)


def test_cmk_pnp_template(site: Site) -> None:
    web = CMKWebSession(site)
    web.get("/%s/check_mk/pnp_template.py" % site.id)


def test_cmk_ajax_graph_images(site: Site) -> None:
    web = CMKWebSession(site)
    response = web.get("/%s/check_mk/ajax_graph_images.py" % site.id)
    assert response.text == ""


def test_trace_disabled(site: Site) -> None:
    web = CMKWebSession(site)
    # TRACE is disabled by using "TraceEnable Off" in apache config
    web.request("TRACE", "/", expected_code=405)


def test_track_disabled(site: Site) -> None:
    web = CMKWebSession(site)
    # all methods but GET, POST, HEAD are disabled in the apache config.
    web.request("TRACK", "/", expected_code=405)


def test_options_disabled(site: Site) -> None:
    web = CMKWebSession(site)
    # all methods but GET, POST, HEAD are disabled in the apache config.
    web.request("OPTIONS", "/", expected_code=405)
