#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.fritz import parse_fritz

_STRING_TABLE = [
    ["VersionOS", "137.06.83"],
    ["VersionDevice", "AVM", "FRITZ!Box", "7412", "(UI)"],
    ["NewVoipDNSServer1", "217.237.148.102"],
    ["NewDNSServer2", "217.237.151.115"],
    ["NewDNSServer1", "217.237.148.102"],
    ["NewVoipDNSServer2", "217.237.151.115"],
    ["NewIdleDisconnectTime", "0"],
    ["NewLayer1DownstreamMaxBitRate", "25088000"],
    ["NewWANAccessType", "DSL"],
    ["NewByteSendRate", "197"],
    ["NewPacketReceiveRate", "0"],
    ["NewConnectionStatus", "Connected"],
    ["NewRoutedBridgedModeBoth", "1"],
    ["NewUptime", "1"],
    ["NewTotalBytesReceived", "178074787"],
    ["NewPacketSendRate", "0"],
    ["NewPhysicalLinkStatus", "Up"],
    ["NewLinkStatus", "Up"],
    ["NewLayer1UpstreamMaxBitRate", "5056000"],
    ["NewTotalBytesSent", "40948982"],
    ["NewLastConnectionError", "ERROR_NONE"],
    ["NewAutoDisconnectTime", "0"],
    ["NewExternalIPAddress", "217.235.84.223"],
    ["NewLinkType", "PPPoE"],
    ["NewByteReceiveRate", "0"],
    ["NewUpnpControlEnabled", "1"],
]

_SECTION = {
    "NewAutoDisconnectTime": "0",
    "NewByteReceiveRate": "0",
    "NewByteSendRate": "197",
    "NewConnectionStatus": "Connected",
    "NewDNSServer1": "217.237.148.102",
    "NewDNSServer2": "217.237.151.115",
    "NewExternalIPAddress": "217.235.84.223",
    "NewIdleDisconnectTime": "0",
    "NewLastConnectionError": "ERROR_NONE",
    "NewLayer1DownstreamMaxBitRate": "25088000",
    "NewLayer1UpstreamMaxBitRate": "5056000",
    "NewLinkStatus": "Up",
    "NewLinkType": "PPPoE",
    "NewPacketReceiveRate": "0",
    "NewPacketSendRate": "0",
    "NewPhysicalLinkStatus": "Up",
    "NewRoutedBridgedModeBoth": "1",
    "NewTotalBytesReceived": "178074787",
    "NewTotalBytesSent": "40948982",
    "NewUpnpControlEnabled": "1",
    "NewUptime": "1",
    "NewVoipDNSServer1": "217.237.148.102",
    "NewVoipDNSServer2": "217.237.151.115",
    "NewWANAccessType": "DSL",
    "VersionDevice": "AVM FRITZ!Box 7412 (UI)",
    "VersionOS": "137.06.83",
}


def test_parse_fritz() -> None:
    assert parse_fritz(_STRING_TABLE) == _SECTION
