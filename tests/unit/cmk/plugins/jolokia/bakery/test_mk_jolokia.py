#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.bakery.v2_unstable import OS, Plugin, PluginConfig, Secret
from cmk.plugins.jolokia.bakery.mk_jolokia import bakery_plugin_jolokia

jolokia_lines = [
    "# Default values",
    "protocol = 'https'",
    "verify = '/etc/ssl/certs/company-ca.pem'",
    "server = '127.0.0.1'",
    "port = 8080",
    "timeout = 1.0",
    "user = 'moni'",
    "password = 'toring'",
    "mode = 'basic'",
    "suburi = 'jolokia'",
    "instance = 'Cööle Instanß'",
    "custom_vars = [('some_mbean', 'some_path', 'some_title', [], False, 'number'),",
    " ('another_mbean', 'another_path', 'another_path', [], False, 'string')]",
    "",
    "# Instances",
    "instances = [{'protocol': 'http', 'server': 'use fqdn'},",
    " {'protocol': 'https', 'server': '10.0.0.1', 'verify': False},",
    " {'server': 'use fqdn', 'verify': True}]",
]

jolokia_conf = {
    "deployment": "sync",
    "protocol": "https",
    "verify": ("ca_file", "/etc/ssl/certs/company-ca.pem"),
    "server": ("ip_or_fqdn", "127.0.0.1"),
    "port": 8080,
    "timeout": 1.0,
    "login": {
        "user": "moni",
        "password": Secret("toring", "", ""),
        "mode": "basic",
    },
    "suburi": "jolokia",
    "instance": "Cööle Instanß",
    "custom_vars": [
        {
            "mbean": "some_mbean",
            "path": "some_path",
            "value_type": "number",
            "title": "some_title",
        },
        {"mbean": "another_mbean", "path": "another_path", "value_type": "string"},
    ],
    "instances": [
        {"protocol": "http", "server": ("use_local_fqdn", None)},
        {"protocol": "https", "server": ("ip_or_fqdn", "10.0.0.1"), "verify": ("disabled", None)},
        {"verify": ("trust_store", None)},
    ],
}


def test_bakery_plugin() -> None:
    assert list(
        bakery_plugin_jolokia.files_function(bakery_plugin_jolokia.parameter_parser(jolokia_conf))
    ) == [
        Plugin(base_os=OS.LINUX, source=Path("mk_jolokia.py")),
        PluginConfig(
            base_os=OS.LINUX,
            lines=jolokia_lines,
            target=Path("jolokia.cfg"),
            include_header=True,
        ),
        Plugin(base_os=OS.WINDOWS, source=Path("mk_jolokia.py")),
        PluginConfig(
            base_os=OS.WINDOWS,
            lines=jolokia_lines,
            target=Path("jolokia.cfg"),
            include_header=True,
        ),
    ]
