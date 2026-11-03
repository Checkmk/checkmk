#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
from ast import literal_eval
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import override

from cmk.automations.internal import AutomationID, AutomationResult
from cmk.automations.results import (
    DiagCmkAgentInput,
    DiagSnmpInput,
    DiagSpecialAgentHostConfig,
    DiagSpecialAgentInput,
    DiagSpecialAgentResult,
    Gateway,
    GatewayResult,
    NotifyResult,
    PingHostCmd,
    PingHostInput,
    ScanParentsResult,
    ServiceDiscoveryPreviewResult,
    ServiceDiscoveryResult,
    SpecialAgentResult,
)
from cmk.ccc import version as cmk_version
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.checkengine.discovery import CheckPreviewEntry
from cmk.checkengine.discovery import DiscoveryReport as SingleHostDiscoveryResult
from cmk.checkengine.plugins import SectionName
from cmk.password_store.v1 import Secret
from cmk.ruleset_matcher.labels import HostLabel
from cmk.utils.ip_lookup import IPStackConfig


@dataclass
class AutomationResultTest(AutomationResult):
    a: int
    b: str
    c: bool
    d: Sequence[None]
    e: Mapping[str, str]

    @staticmethod
    @override
    def automation_call() -> AutomationID:
        return AutomationID("test")


def test_serialization() -> None:
    automation_res_test = AutomationResultTest(
        a=1,
        b="string",
        c=True,
        d=(
            None,
            None,
        ),
        e={
            "a": "test",
            "123": "456",
        },
    )
    assert automation_res_test == AutomationResultTest.deserialize(
        automation_res_test.serialize(cmk_version.__version__)
    )


class TestDiscoveryResult:
    HOSTS = {
        HostName("host_1"): SingleHostDiscoveryResult(),
        HostName("host_2"): SingleHostDiscoveryResult(),
    }

    def test_serialization(self) -> None:
        assert ServiceDiscoveryResult.deserialize(
            ServiceDiscoveryResult(self.HOSTS).serialize(cmk_version.__version__)
        ) == ServiceDiscoveryResult(self.HOSTS)


class TestTryDiscoveryResult:
    RESULT = ServiceDiscoveryPreviewResult(
        output="output",
        check_table=[
            CheckPreviewEntry(
                check_source="my_check_source",
                check_plugin_name="my_check_plugin_name",
                ruleset_name=None,
                discovery_ruleset_name=None,
                item=None,
                old_discovered_parameters={},
                new_discovered_parameters={},
                effective_parameters={},
                description="description",
                state=0,
                output="output",
                metrics=[],
                old_labels={},
                new_labels={},
                found_on_nodes=[],
            )
        ],
        nodes_check_table={},
        host_labels={},
        new_labels={},
        vanished_labels={},
        changed_labels={},
        source_results=[(0, "Success")],
        labels_by_host={HostName("my_host"): [HostLabel("cmk/foo", "bar", SectionName("baz"))]},
        config_warnings=["Don't leave your luggage unattended."],
    )

    def test_serialization(self) -> None:
        assert (
            ServiceDiscoveryPreviewResult.deserialize(
                self.RESULT.serialize(cmk_version.__version__)
            )
            == self.RESULT
        )

    def test_serialization_for_2_4_keys_source_results(self) -> None:
        assert literal_eval(self.RESULT.serialize("2.4.0p1"))["source_results"] == {
            0: (0, "Success")
        }


class TestScanParentsResult:
    SERIALIZED_RESULT = "([((None, '108.170.228.254', None), 'gateway', 0, '')],)"

    DESERIALIZED_RESULT = ScanParentsResult(
        results=[
            GatewayResult(
                gateway=Gateway(None, HostAddress("108.170.228.254"), None),
                state="gateway",
                ping_fails=0,
                message="",
            )
        ]
    )

    def test_serialization_roundtrip(self) -> None:
        assert (
            ScanParentsResult.deserialize(
                self.DESERIALIZED_RESULT.serialize(cmk_version.__version__)
            )
            == self.DESERIALIZED_RESULT
        )

    def test_deserialization(self) -> None:
        assert ScanParentsResult.deserialize(self.SERIALIZED_RESULT) == self.DESERIALIZED_RESULT


class TestDiagSpecialAgentInput:
    DIAG_SPECIAL_AGENT_INPUT = DiagSpecialAgentInput(
        host_config=DiagSpecialAgentHostConfig(
            host_name=HostName("test-host"),
            host_alias="test-host",
            relay_id=None,
            ip_address=None,
            ip_stack_config=IPStackConfig.NO_IP,
            host_attrs={},
            macros={},
            host_primary_family=socket.AddressFamily.AF_INET,
            host_additional_addresses_ipv4=[],
            host_additional_addresses_ipv6=[],
        ),
        agent_name="aws",
        params={
            "access_key_id": "my_access_key",
            "secret_access_key": (
                "cmk_postprocessed",
                "explicit_password",
                ("uuid8d60b66c-c3e1-45cb-a771-b8b291a07cea", "wow_this_access_key_is_secret"),
            ),
            "access": {},
            "global_services": {
                "ce": ("none", None),
                "route53": ("none", None),
                "cloudfront": ("none", None),
            },
            "regions_to_monitor": ["eu_central_1"],
            "services": {
                "ec2": ("all", {"limits": "limits"}),
                "ebs": ("all", {"limits": "limits"}),
                "s3": ("all", {"limits": "limits"}),
                "glacier": ("all", {"limits": "limits"}),
                "elb": ("all", {"limits": "limits"}),
                "elbv2": ("all", {"limits": "limits"}),
                "rds": ("all", {"limits": "limits"}),
                "cloudwatch_alarms": ("all", {"limits": "limits"}),
                "dynamodb": ("all", {"limits": "limits"}),
                "wafv2": ("all", {"limits": "limits"}),
                "aws_lambda": ("all", {"limits": "limits"}),
                "sns": ("all", {"limits": "limits"}),
                "ecs": ("all", {"limits": "limits"}),
                "elasticache": ("all", {"limits": "limits"}),
            },
            "piggyback_naming_convention": "ip_region_instance",
        },
        passwords={
            "uuid8d60b66c-c3e1-45cb-a771-b8b291a07cea": Secret("wow_this_access_key_is_secret"),
        },
    )

    def test_serialization_roundtrip(self) -> None:
        assert (
            DiagSpecialAgentInput.deserialize(
                self.DIAG_SPECIAL_AGENT_INPUT.serialize(
                    cmk_version.Version.from_str(cmk_version.__version__)
                )
            )
            == self.DIAG_SPECIAL_AGENT_INPUT
        )


class TestDiagSpecialAgentResult:
    DIAG_SPECIAL_AGENT_RESULT = DiagSpecialAgentResult(
        results=[
            SpecialAgentResult(return_code=0, response="<<<aws_ec2>>>\n"),
            SpecialAgentResult(return_code=2, response="Unauthorized"),
        ]
    )

    def test_serialization_roundtrip(self) -> None:
        assert (
            DiagSpecialAgentResult.deserialize(
                self.DIAG_SPECIAL_AGENT_RESULT.serialize(cmk_version.__version__)
            )
            == self.DIAG_SPECIAL_AGENT_RESULT
        )

    def test_deserialize_empty_string_gives_no_results(self) -> None:
        assert DiagSpecialAgentResult.deserialize("") == DiagSpecialAgentResult(results=[])


class TestDiagCmkAgentInput:
    DIAG_CMK_AGENT_INPUT = DiagCmkAgentInput(
        host_name=HostName("agent-host"),
        ip_address=HostAddress("10.1.2.3"),
        address_family="ip-v4-only",
        agent_port=6557,
        timeout=9,
    )

    def test_serialization_roundtrip(self) -> None:
        assert (
            DiagCmkAgentInput.deserialize(
                self.DIAG_CMK_AGENT_INPUT.serialize(
                    cmk_version.Version.from_str(cmk_version.__version__)
                )
            )
            == self.DIAG_CMK_AGENT_INPUT
        )


class TestDiagSnmpInput:
    DIAG_SNMP_INPUT = DiagSnmpInput(
        host_name=HostName("snmp-host"),
        ip_address=HostAddress("2001:db8::1"),
        address_family="ip-v6-only",
        snmp_version="snmp-v2",
        snmp_community="community",
        snmpv3_use="authPriv",
        snmpv3_auth_proto="SHA-256",
        snmpv3_security_name="security-name",
        snmpv3_security_password="security-password",
        snmpv3_privacy_proto="AES",
        snmpv3_privacy_password="privacy-password",
        port=1161,
        timeout=7,
        retries=3,
    )

    def test_serialization_roundtrip(self) -> None:
        assert (
            DiagSnmpInput.deserialize(
                self.DIAG_SNMP_INPUT.serialize(
                    cmk_version.Version.from_str(cmk_version.__version__)
                )
            )
            == self.DIAG_SNMP_INPUT
        )


class TestPingHostInput:
    PING_HOST_INPUT = PingHostInput(
        ip_or_dns_name="ping-host.example.com",
        base_cmd=PingHostCmd.PING6,
    )

    def test_serialization_roundtrip(self) -> None:
        assert (
            PingHostInput.deserialize(
                self.PING_HOST_INPUT.serialize(
                    cmk_version.Version.from_str(cmk_version.__version__)
                )
            )
            == self.PING_HOST_INPUT
        )


def test_notify_result_serialization() -> None:
    original = NotifyResult(exit_code=0, output="All good!")
    deserialized = NotifyResult.deserialize(original.serialize(cmk_version.__version__))
    assert original == deserialized
