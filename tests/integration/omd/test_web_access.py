#!/usr/bin/env python
# encoding: utf-8

from testlib import CMKWebSession


def test_www_dir(site):
    web = CMKWebSession(site)

    # unauthenticated = denied
    web.get("/%s/testfile" % site.id, expected_code=401)

    try:
        site.write_file("var/www/testfile.html", "123")
        assert web.get("/%s/testfile.html" % site.id, auth=("cmkadmin", "cmk")).text == "123"
    finally:
        site.delete_file("var/www/testfile.html")


def test_base_path_redirects(site):
    web = CMKWebSession(site)
    expected_target = '%s://%s:%d/%s/check_mk/' % \
        (site.http_proto, site.http_address, site.apache_port, site.id)

    web.check_redirect("/%s" % site.id, expected_target=expected_target)
    web.check_redirect("/%s/" % site.id, expected_target=expected_target)
    web.check_redirect("/%s/check_mk" % site.id, expected_target=expected_target)


def test_cmk_base_path_access(site):
    web = CMKWebSession(site)
    expected_target = "/%s/check_mk/login.py?_origtarget=index.py" % site.id

    # TODO: Figure out if which status code we *really* expect here: 301 or 302?
    web.check_redirect("/%s/check_mk/" % site.id, expected_target=expected_target)

    web.check_redirect("/%s/check_mk/index.py" % site.id, expected_target=expected_target)


def test_cmk_agents_access(site):
    web = CMKWebSession(site)
    body = web.get("/%s/check_mk/agents" % site.id).text
    assert "Index of" in body


def test_cmk_local_agents_access(site):
    web = CMKWebSession(site)
    body = web.get("/%s/check_mk/local/agents" % site.id).text
    assert "Index of" in body


def test_cmk_sounds(site):
    web = CMKWebSession(site)
    response = web.get("/%s/check_mk/sounds/ok.wav" % site.id)
    assert response.headers["Content-Type"] == "audio/x-wav"


def test_cmk_automation(site):
    web = CMKWebSession(site)
    response = web.get("/%s/check_mk/automation.py" % site.id)
    assert response.text == "Missing secret for automation command."


def test_cmk_deploy_agent(site):
    web = CMKWebSession(site)
    response = web.get("/%s/check_mk/deploy_agent.py" % site.id)
    assert response.text.startswith("ERROR: Missing")


def test_cmk_run_cron(site):
    web = CMKWebSession(site)
    web.get("/%s/check_mk/run_cron.py" % site.id)


def test_cmk_pnp_template(site):
    web = CMKWebSession(site)
    web.get("/%s/check_mk/pnp_template.py" % site.id)


def test_cmk_ajax_graph_images(site):
    web = CMKWebSession(site)
    response = web.get("/%s/check_mk/ajax_graph_images.py" % site.id)
    assert response.text == ""


def test_trace_disabled(site):
    web = CMKWebSession(site)
    # TRACE is disabled by using "TraceEnable Off" in apache config
    web._request("TRACE", "/", expected_code=405)


def test_track_disabled(site):
    web = CMKWebSession(site)
    # TRACE is not supported by apache at all by apache, so there is no need to
    # disable this. The HTTP code is just different from TRACE.
    web._request("TRACK", "/", expected_code=403)


def test_options_disabled(site):
    web = CMKWebSession(site)
    web._request("OPTIONS", "/", expected_code=403)
