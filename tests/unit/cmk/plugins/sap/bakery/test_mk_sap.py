#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.bakery.v2_unstable import OS, Plugin, PluginConfig, Secret
from cmk.plugins.sap.bakery.mk_sap import bakery_plugin_mk_sap

CONFIG = {
    "deployment": ("sync", None),
    "instances": [
        {
            "ashost": "localhost",
            "lang": "EN",
            "trace": "3",
            "passwd": Secret("thiswontworkanyway", "", ""),
            "sysnr": "00",
            "client": "100",
            "user": "cmk-user",
        },
        {
            "ashost": "localhost",
            "lang": "EN",
            "trace": "3",
            "passwd": Secret("pass", "", ""),
            "sysnr": "00",
            "client": "100",
            "user": "cmk-user",
        },
    ],
    "paths": [
        "SAP BI Monitors/BI Monitor",
        "SAP BI Monitors/BI Monitor/*/Oracle/Performance",
        "SAP CCMS Monitor Templates/Operating System/OperatingSystem/CPU/*",
        "SAP CCMS Monitor Templates/Operating System/OperatingSystem/CPU/CPU_Utilization",
    ],
}

CONFIG_LINES = [
    "# Instances to monitor",
    "cfg = [{'ashost': 'localhost',",
    "  'client': '100',",
    "  'lang': 'EN',",
    "  'loglevel': 'warn',",
    "  'passwd': 'thiswontworkanyway',",
    "  'sysnr': '00',",
    "  'trace': '3',",
    "  'user': 'cmk-user'},",
    " {'ashost': 'localhost',",
    "  'client': '100',",
    "  'lang': 'EN',",
    "  'loglevel': 'warn',",
    "  'passwd': 'pass',",
    "  'sysnr': '00',",
    "  'trace': '3',",
    "  'user': 'cmk-user'}]",
    "",
    "",
    "# CCMS paths to monitor",
    "monitor_paths += ['SAP BI Monitors/BI Monitor',",
    " 'SAP BI Monitors/BI Monitor/*/Oracle/Performance',",
    " 'SAP CCMS Monitor Templates/Operating System/OperatingSystem/CPU/*',",
    " 'SAP CCMS Monitor Templates/Operating System/OperatingSystem/CPU/CPU_Utilization']",
]


def test_no_deploy() -> None:
    conf = bakery_plugin_mk_sap.parameter_parser({"deployment": ("do_not_deploy", None)})
    assert not list(bakery_plugin_mk_sap.files_function(conf))


def test_deploy() -> None:
    conf = bakery_plugin_mk_sap.parameter_parser(CONFIG)
    result = list(bakery_plugin_mk_sap.files_function(conf))
    assert result == [
        Plugin(base_os=OS.LINUX, source=Path("mk_sap.py"), interval=None),
        PluginConfig(
            base_os=OS.LINUX,
            lines=CONFIG_LINES,
            target=Path("sap.cfg"),
            include_header=True,
        ),
    ]
