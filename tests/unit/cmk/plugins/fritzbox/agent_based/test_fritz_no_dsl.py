#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.plugins.fritzbox.agent_based import fritz

_STRING_TABLE = [
    ["VersionOS", "154.07.29"],
    ["VersionDevice", "AVM", "FRITZ!Box", "7590"],
    ["NewConnectionStatus", "Connected"],
    ["NewLastConnectionError", "ERROR_NONE"],
    ["NewUptime", "3345534"],
    ["NewExternalIPAddress", "XXX.XXX.XXX.XXX"],
    ["NewByteSendRate", "2659"],
    ["NewByteReceiveRate", "134912"],
    ["NewPacketSendRate", "0"],
    ["NewPacketReceiveRate", "0"],
    ["NewTotalBytesSent", "865038171"],
    ["NewTotalBytesReceived", "2076709574"],
    ["NewAutoDisconnectTime", "300"],
    ["NewIdleDisconnectTime", "0"],
    ["NewDNSServer1", "217.237.149.205"],
    ["NewDNSServer2", "217.237.151.51"],
    ["NewVoipDNSServer1", "217.237.149.205"],
    ["NewVoipDNSServer2", "217.237.151.51"],
    ["NewUpnpControlEnabled", "0"],
    ["NewRoutedBridgedModeBoth", "1"],
    ["NewX_AVM_DE_TotalBytesSent64", "91059351387"],
    ["NewX_AVM_DE_TotalBytesReceived64", "1535380034246"],
    ["NewX_AVM_DE_WANAccessType", "ATA"],
    ["NewWANAccessType", "Ethernet"],
    ["NewLayer1UpstreamMaxBitRate", "100000000"],
    ["NewLayer1DownstreamMaxBitRate", "500000000"],
    ["NewPhysicalLinkStatus", "Up"],
]


def test_new_physical_link_status_respected() -> None:
    interfaces = fritz._section_to_interface(fritz.parse_fritz(_STRING_TABLE))
    assert interfaces[0].attributes.oper_status == "1"
