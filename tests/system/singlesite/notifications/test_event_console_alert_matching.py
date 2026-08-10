#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Iterator, Mapping

import pytest

from cmk.automations import results
from cmk.automations.results import SerializedResult
from cmk.ccc.hostaddress import HostName
from tests.testlib.site import Site

_RULE_DESCRIPTION = "Do not match Event Console alerts"


@pytest.fixture(name="ec_alert_matching_host")
def fixture_ec_alert_matching_host(site: Site) -> Iterator[HostName]:
    hostname = HostName("ec-alert-matching-host")
    site.openapi.hosts.create(hostname, attributes={"ipaddress": "127.0.0.1"})
    site.activate_changes_and_wait_for_core_reload()

    try:
        yield hostname
    finally:
        site.openapi.hosts.delete(hostname)
        site.activate_changes_and_wait_for_core_reload()


@pytest.fixture(name="rule_excluding_ec_alerts")
def fixture_rule_excluding_ec_alerts(site: Site) -> Iterator[None]:
    rules_file = "etc/check_mk/conf.d/wato/notifications.mk"
    rule = {
        "rule_id": "0f5f1f27-0b3e-4a55-9f5d-7f4a9c2e6b10",
        "description": _RULE_DESCRIPTION,
        "comment": "",
        "docu_url": "",
        "disabled": False,
        "allow_disable": True,
        "contact_object": True,
        "contact_all": False,
        "contact_all_with_email": False,
        "match_ec": False,
        "notify_plugin": ("mail", {}),
    }
    previous = site.read_file(rules_file) if site.file_exists(rules_file) else None

    site.write_file(rules_file, f"# Written by Checkmk store\n\nnotification_rules += [{rule!r}]\n")
    try:
        yield
    finally:
        if previous is None:
            site.delete_file(rules_file)
        else:
            site.write_file(rules_file, previous)


def _verdict(site: Site, context: Mapping[str, str]) -> tuple[str, str]:
    """Ask the notification analysis how the rule under test treats this context"""
    # An empty dispatch keeps the analysis from actually sending the notification.
    completed = site.run(["cmk", "--automation", "notification-test", json.dumps(context), ""])
    result = results.NotificationTestResult.deserialize(SerializedResult(completed.stdout))
    assert result.result is not None, f"Notification analysis returned nothing for {context}"

    rule_info, _plugin_info = result.result
    for state, rule, why_not in rule_info:
        if rule["description"] == _RULE_DESCRIPTION:
            return state, why_not
    raise AssertionError(f"Rule {_RULE_DESCRIPTION!r} was not considered: {rule_info}")


@pytest.mark.usefixtures("rule_excluding_ec_alerts")
def test_rule_excluding_ec_alerts_matches_only_host_notifications(
    ec_alert_matching_host: HostName, site: Site
) -> None:
    ec_alert_context = {
        "CONTACTS": "",
        "HOSTNAME": ec_alert_matching_host,
        "SERVICEDESC": "Event Console",
        "SERVICESTATE": "CRITICAL",
        "LASTSERVICESTATE": "OK",
        "EC_ID": "1",
    }
    host_problem_context = {
        "CONTACTS": "",
        "HOSTNAME": ec_alert_matching_host,
        "HOSTSTATE": "DOWN",
    }

    assert _verdict(site, ec_alert_context) == (
        "miss",
        "Notification has been created by the Event Console.",
    )
    assert _verdict(site, host_problem_context) == ("match", "")
