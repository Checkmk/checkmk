#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os

from tests.testlib.site import Site


def test_hooks(site: Site) -> None:
    hooks = [
        "ADMIN_MAIL",
        "APACHE_MODE",
        "APACHE_TCP_ADDR",
        "APACHE_TCP_PORT",
        "AUTOSTART",
        "CORE",
        "LIVESTATUS_TCP",
        "LIVESTATUS_TCP_ONLY_FROM",
        "LIVESTATUS_TCP_PORT",
        "LIVESTATUS_TCP_TLS",
        "AGENT_RECEIVER",
        "AGENT_RECEIVER_PORT",
        "MKEVENTD",
        "MKEVENTD_SNMPTRAP",
        "MKEVENTD_SYSLOG",
        "MKEVENTD_SYSLOG_TCP",
        "MULTISITE_AUTHORISATION",
        "MULTISITE_COOKIE_AUTH",
        "PIGGYBACK_HUB",
        "PNP4NAGIOS",
        "TMPFS",
        "TRACE_SEND",
        "TRACE_SEND_TARGET",
        "TRACE_SERVICE_NAMESPACE",
        "RABBITMQ_PORT",
        "RABBITMQ_ONLY_FROM",
        "RABBITMQ_MANAGEMENT_PORT",
        "RABBITMQ_DIST_PORT",
        "AUTOMATION_HELPER",
    ]

    if not site.version.is_raw_edition():
        hooks += [
            "LIVEPROXYD",
        ]

    if not site.version.is_saas_edition():
        hooks += [
            "TRACE_RECEIVE",
            "TRACE_RECEIVE_ADDRESS",
            "TRACE_RECEIVE_PORT",
            "TRACE_JAEGER_UI_PORT",
            "TRACE_JAEGER_ADMIN_PORT",
        ]

    if site.version.is_cloud_edition() or site.version.is_managed_edition():
        hooks += [
            "OPENTELEMETRY_COLLECTOR",
            "OPENTELEMETRY_COLLECTOR_SELF_MONITORING_PORT",
        ]

    installed_hooks = os.listdir(site.root / "lib" / "omd" / "hooks")

    assert sorted(hooks) == sorted(installed_hooks)
