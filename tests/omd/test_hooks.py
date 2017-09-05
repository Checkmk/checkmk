#!/usr/bin/env python
# encoding: utf-8

import os
import stat

def test_hooks(site):
    hooks = [
        "ADMIN_MAIL",
        "APACHE_MODE",
        "APACHE_TCP_ADDR",
        "APACHE_TCP_PORT",
        "AUTOSTART",
        "CORE",
        "DOKUWIKI_AUTH",
        "LIVESTATUS_TCP",
        "LIVESTATUS_TCP_ONLY_FROM",
        "LIVESTATUS_TCP_PORT",
        "MKEVENTD",
        "MKEVENTD_SNMPTRAP",
        "MKEVENTD_SYSLOG",
        "MKEVENTD_SYSLOG_TCP",
        "MULTISITE_AUTHORISATION",
        "MULTISITE_COOKIE_AUTH",
        "NAGIOS_THEME",
        "NSCA",
        "NSCA_TCP_PORT",
        "PNP4NAGIOS",
    ]

    if site.version.edition() == "enterprise":
        hooks += [
            "LIVEPROXYD",
        ]

    installed_hooks = os.listdir(os.path.join(site.root, "lib/omd/hooks"))

    assert sorted(hooks) == sorted(installed_hooks)
