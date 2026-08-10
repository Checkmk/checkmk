#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from tests.testlib.site import Site
from tests.testlib.web_session import CMKWebSession


def test_www_dir(site: Site) -> None:
    web = CMKWebSession(site)

    # unauthenticated = denied
    web.get("/%s/testfile.html" % site.id, expected_code=401)

    try:
        site.write_file("var/www/testfile.html", "123")
        assert web.get("/%s/testfile.html" % site.id, auth=("cmkadmin", "cmk")).text == "123"
    finally:
        site.delete_file("var/www/testfile.html")


def test_checkmk_htdocs(site: Site) -> None:
    web = CMKWebSession(site)

    web.get(f"/{site.id}/check_mk/local/foobar.txt", expected_code=404)

    try:
        site.write_file("local/share/check_mk/web/htdocs/foobar.txt", "123")
        assert web.get(f"/{site.id}/check_mk/local/foobar.txt").text == "123"
    finally:
        site.delete_file("local/share/check_mk/web/htdocs/foobar.txt")


def test_checkmk_htdocs_local_overwrite(site: Site) -> None:
    web = CMKWebSession(site)

    response = web.get("/%s/check_mk/images/icons/core.png" % site.id)
    assert response.headers["Content-Type"] == "image/png"
    assert response.text != "123"

    try:
        site.makedirs("local/share/check_mk/web/htdocs/images/icons/")
        site.write_file("local/share/check_mk/web/htdocs/images/icons/core.png", "123")

        response = web.get("/%s/check_mk/images/icons/core.png" % site.id)
        assert response.text == "123"
    finally:
        site.delete_file("local/share/check_mk/web/htdocs/images/icons/core.png")

    response = web.get("/%s/check_mk/images/icons/core.png" % site.id)
    assert response.headers["Content-Type"] == "image/png"
    assert response.text != "123"


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


@pytest.mark.skip_if_not_edition("cloud", "ultimate", "ultimatemt")
def test_cmk_relay_installation_script_access(site: Site) -> None:
    web = CMKWebSession(site)
    response = web.get("/%s/check_mk/relays/install_relay.sh" % site.id)
    assert response.headers["Content-Type"] in [
        "text/x-sh",
        "application/x-shellscript",
        "application/x-sh",
    ]
    # Verify it's a shell script
    assert response.text.startswith("#!")


@pytest.mark.skip_if_not_edition("cloud", "ultimate", "ultimatemt")
@pytest.mark.skip_if_faked_artifacts
def test_cmk_relay_msi_access(site: Site) -> None:
    # OLE compound document signature; every genuine MSI starts with these bytes.
    _MSI_OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

    web = CMKWebSession(site)
    response = web.get(f"/{site.id}/check_mk/relays/CheckmkRelayInstaller.msi")

    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/x-msi"
    # Verify the body is a genuine MSI (OLE compound document magic).
    assert response.content[:8] == _MSI_OLE_MAGIC


def test_cmk_local_agents_access(site: Site) -> None:
    web = CMKWebSession(site)
    body = web.get("/%s/check_mk/local/agents" % site.id, expected_code=404).text
    assert "Not Found" in body


def test_plugin_apis_access(site: Site) -> None:
    web = CMKWebSession(site)
    body = web.get("/%s/check_mk/plugin-api" % site.id).text
    assert "Plugin APIs" in body


def test_cmk_sounds(site: Site) -> None:
    web = CMKWebSession(site)
    response = web.get("/%s/check_mk/sounds/ok.wav" % site.id)
    assert response.headers["Content-Type"] == "audio/x-wav"


def test_cmk_automation(site: Site) -> None:
    web = CMKWebSession(site)
    response = web.get("/%s/check_mk/automation.py" % site.id)
    assert response.text == "Missing secret for automation command."


@pytest.mark.skip_if_edition("community")
def test_cmk_deploy_agent(site: Site) -> None:
    web = CMKWebSession(site)
    response = web.get("/%s/check_mk/deploy_agent.py" % site.id)
    assert response.json()["result"].startswith("Missing")


def test_cmk_webapi_removed(site: Site) -> None:
    """Regression test pinning the current apache.conf behaviour for the removed
    legacy webapi endpoint. It documents what apache.conf does today, not a
    business requirement, and may be deleted if those requirements change."""
    web = CMKWebSession(site)
    web.get("/%s/check_mk/webapi.py" % site.id, expected_code=410)
    web.get("/%s/check_mk/webapi.py?foo=bar" % site.id, expected_code=410)


def test_cmk_pnp_template_removed(site: Site) -> None:
    web = CMKWebSession(site)
    web.get("/%s/check_mk/pnp_template.py" % site.id, expected_code=404)


def test_cmk_ajax_graph_images(site: Site) -> None:
    web = CMKWebSession(site)
    response = web.get(
        "/%s/check_mk/ajax_graph_images.py?host=nonexistent" % site.id,
        headers={
            "Authorization": f"InternalToken {site.get_site_internal_secret().b64_str}",
        },
    )
    assert response.json() == {"result_code": 0, "result": [], "severity": "success"}


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


def test_content_security_policy_header(site: Site) -> None:
    """The Content-Security-Policy for GUI pages is set by the Checkmk GUI
    (Python); for content served directly by Apache (NagVis, static HTML) the
    site Apache sets the same legacy policy as a fallback (CMK-31353). See
    cmk.gui.http.LEGACY_CONTENT_SECURITY_POLICY, the GUI wsgi app and
    omd/packages/apache-omd/skel/etc/apache/conf.d/security.conf.

    Consequences:
    - Static assets (js/css/images/...) carry no CSP - unchanged.
    - Responses generated by Apache itself (e.g. the 405 for disallowed
      methods) carry no CSP.
    - GUI pages carry the policy emitted by the wsgi app.
    - Other Apache-served documents carry the Apache fallback policy."""
    web = CMKWebSession(site)

    # Mirrors cmk.gui.http.LEGACY_CONTENT_SECURITY_POLICY.serialize() and the
    # fallback in security.conf (the two must stay identical).
    default_csp = (
        "default-src 'self' 'unsafe-inline' 'unsafe-eval' ssh: rdp:; "
        "img-src 'self' data: https://*.tile.openstreetmap.org/; "
        "connect-src 'self' https://crash.checkmk.com/; "
        "frame-ancestors 'self'; "
        "base-uri 'self'; "
        "form-action 'self' javascript: 'unsafe-inline'; "
        "object-src 'self'; "
        "worker-src 'self' blob:"
    )

    # No CSP for static assets (stripped in security.conf)
    response = web.get("/%s/check_mk/sounds/ok.wav" % site.id)
    assert response.headers["Content-Type"] == "audio/x-wav"
    assert response.headers.get("Content-Security-Policy") is None

    # No CSP for Apache-generated error responses (do not reach the wsgi app)
    response = web.request("OPTIONS", "/", expected_code=405)
    assert response.headers.get("Content-Security-Policy") is None

    # Apache fallback: a document served directly by Apache (not the wsgi app)
    # still carries the legacy policy.
    response = web.get("/%s/check_mk/agents" % site.id)
    assert response.headers["Content-Security-Policy"] == default_csp

    # "CSP for successful pages" causes ConnectionError for Checkmk Cloud with auth provider in CI
    # See CMK-22347 for details.
    if site.edition.is_cloud_edition():
        return

    # CSP set by the GUI for a rendered page
    response = web.get("/%s/check_mk/login.py?_origtarget=index.py" % site.id)
    assert response.headers["Content-Security-Policy"] == default_csp
