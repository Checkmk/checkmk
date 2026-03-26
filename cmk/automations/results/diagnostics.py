#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Host connectivity and diagnostics results.

Groups all "probe/diagnose a host" automations.
"""

from __future__ import annotations

import json
import socket
from ast import literal_eval
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Literal, Self

from cmk.automations.results._base import (
    ABCAutomationResult,
    result_type_registry,
    SerializedResult,
)
from cmk.ccc import version as cmk_version
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.password_store.v1_unstable import Secret
from cmk.utils.http_proxy_config import HTTPProxySpec
from cmk.utils.ip_lookup import IPStackConfig
from cmk.utils.oauth2_connection import OAuth2Connection

from ..types import AutomationID


@dataclass(frozen=True)
class Gateway:
    existing_gw_host_name: HostName | None
    ip: HostAddress
    dns_name: HostName | None


@dataclass(frozen=True)
class GatewayResult:
    gateway: Gateway | None
    state: str
    ping_fails: int
    message: str


@dataclass
class ScanParentsResult(ABCAutomationResult):
    results: Sequence[GatewayResult]

    @staticmethod
    def automation_call() -> AutomationID:
        return AutomationID("scan-parents")

    @classmethod
    def deserialize(cls, serialized_result: SerializedResult) -> ScanParentsResult:
        (serialized_results,) = literal_eval(serialized_result)
        results = [
            GatewayResult(
                gateway=Gateway(*gw) if gw else None,
                state=state,
                ping_fails=ping_fails,
                message=message,
            )
            for gw, state, ping_fails, message in serialized_results
        ]
        return cls(results=results)


result_type_registry.register(ScanParentsResult)


@dataclass
class DiagSpecialAgentHostConfig:
    host_name: HostName
    host_alias: str
    relay_id: str | None
    ip_address: HostAddress | None
    ip_stack_config: IPStackConfig
    host_attrs: Mapping[str, str]
    macros: Mapping[str, object]
    host_primary_family: Literal[
        socket.AddressFamily.AF_INET,
        socket.AddressFamily.AF_INET6,
    ]
    host_additional_addresses_ipv4: list[HostAddress]
    host_additional_addresses_ipv6: list[HostAddress]

    @classmethod
    def deserialize(cls, serialized_input: str) -> Self:
        raw = json.loads(serialized_input)
        return cls(
            host_name=HostName(raw["host_name"]),
            host_alias=raw["host_alias"],
            relay_id=raw.get("relay_id"),  # missing in 2.4 and earlier
            ip_address=HostAddress(raw["ip_address"]) if raw["ip_address"] else None,
            ip_stack_config=IPStackConfig(raw["ip_stack_config"]),
            host_attrs=raw["host_attrs"],
            macros=raw["macros"],
            host_primary_family=cls.deserialize_host_primary_family(raw["host_primary_family"]),
            host_additional_addresses_ipv4=[
                HostAddress(ip) for ip in raw["host_additional_addresses_ipv4"]
            ],
            host_additional_addresses_ipv6=[
                HostAddress(ip) for ip in raw["host_additional_addresses_ipv6"]
            ],
        )

    @staticmethod
    def deserialize_host_primary_family(
        raw: int,
    ) -> Literal[
        socket.AddressFamily.AF_INET,
        socket.AddressFamily.AF_INET6,
    ]:
        address_family = socket.AddressFamily(raw)
        if address_family is socket.AddressFamily.AF_INET:
            return socket.AddressFamily.AF_INET
        if address_family is socket.AddressFamily.AF_INET6:
            return socket.AddressFamily.AF_INET6
        raise ValueError(f"Invalid address family: {address_family}")

    def serialize(self, _for_cmk_version: cmk_version.Version) -> str:
        return json.dumps(
            {
                "host_name": str(self.host_name),
                "host_alias": self.host_alias,
                "relay_id": self.relay_id,
                "ip_address": str(self.ip_address) if self.ip_address else None,
                "ip_stack_config": self.ip_stack_config.value,
                "host_attrs": self.host_attrs,
                "macros": self.macros,
                "host_primary_family": self.host_primary_family.value,
                "host_additional_addresses_ipv4": [
                    str(ip) for ip in self.host_additional_addresses_ipv4
                ],
                "host_additional_addresses_ipv6": [
                    str(ip) for ip in self.host_additional_addresses_ipv6
                ],
            }
        )


@dataclass
class DiagSpecialAgentInput:
    host_config: DiagSpecialAgentHostConfig
    agent_name: str
    params: Mapping[str, object]
    passwords: Mapping[str, Secret[str]]
    http_proxies: Mapping[str, HTTPProxySpec] = field(default_factory=dict)
    oauth2_connections: Mapping[str, OAuth2Connection] = field(default_factory=dict)
    is_cmc: bool = True

    @classmethod
    def deserialize(cls, serialized_input: str) -> DiagSpecialAgentInput:
        raw = json.loads(serialized_input)
        deserialized = {
            "host_config": DiagSpecialAgentHostConfig.deserialize(raw["host_config"]),
            "agent_name": raw["agent_name"],
            # TODO: at the moment there is no validation for params input possible
            #  this could change when being able to use the formspec vue visitor for
            #  (de)serialization in the future.
            "params": literal_eval(raw["params"]),
            "passwords": {k: Secret(v) for k, v in raw["passwords"].items()},
        }
        if "http_proxies" in raw:
            deserialized["http_proxies"] = raw["http_proxies"]
        if "oauth2_connections" in raw:
            deserialized["oauth2_connections"] = raw["oauth2_connections"]
        if "is_cmc" in raw:
            deserialized["is_cmc"] = raw["is_cmc"]
        return cls(**deserialized)

    def serialize(self, _for_cmk_version: cmk_version.Version) -> str:
        return json.dumps(
            {
                "host_config": self.host_config.serialize(_for_cmk_version),
                "agent_name": self.agent_name,
                "params": repr(self.params),
                "passwords": {k: v.reveal() for k, v in self.passwords.items()},
                "http_proxies": self.http_proxies,
                "oauth2_connections": self.oauth2_connections,
                "is_cmc": self.is_cmc,
            }
        )


@dataclass
class SpecialAgentResult:
    return_code: int
    response: str


@dataclass
class DiagSpecialAgentResult(ABCAutomationResult):
    results: Sequence[SpecialAgentResult]

    @staticmethod
    def automation_call() -> AutomationID:
        return AutomationID("diag-special-agent")

    def serialize(self, for_cmk_version: cmk_version.Version) -> SerializedResult:
        return SerializedResult(
            json.dumps(
                {
                    "results": [asdict(r) for r in self.results],
                }
            )
        )

    @classmethod
    def deserialize(cls, serialized_result: SerializedResult) -> DiagSpecialAgentResult:
        if not serialized_result:
            return cls(results=[])
        raw = json.loads(serialized_result)
        return cls(
            results=[SpecialAgentResult(**r) for r in raw["results"]],
        )


result_type_registry.register(DiagSpecialAgentResult)


@dataclass
class DiagCmkAgentInput:
    host_name: HostName
    ip_address: HostAddress
    address_family: Literal["no-ip", "ip-v4-only", "ip-v6-only", "ip-v4v6"]
    agent_port: int
    timeout: int

    @classmethod
    def deserialize(cls, serialized_input: str) -> DiagCmkAgentInput:
        raw = json.loads(serialized_input)
        deserialized = {
            "host_name": HostName(raw["host_name"]),
            "ip_address": HostAddress(raw["ip_address"]),
            "address_family": raw["address_family"],
            "agent_port": raw["agent_port"],
            "timeout": raw["timeout"],
        }
        return cls(**deserialized)

    def serialize(self, _for_cmk_version: cmk_version.Version) -> str:
        return json.dumps(
            {
                "host_name": self.host_name,
                "ip_address": self.ip_address,
                "address_family": self.address_family,
                "agent_port": self.agent_port,
                "timeout": self.timeout,
            }
        )


@dataclass
class DiagCmkAgentResult(ABCAutomationResult):
    return_code: int
    response: str

    @staticmethod
    def automation_call() -> AutomationID:
        return AutomationID("diag-cmk-agent")


result_type_registry.register(DiagCmkAgentResult)

SnmpV3SecurityLevel = Literal["authPriv", "authNoPriv", "noAuthNoPriv"]
SnmpV3AuthProtocol = Literal["md5", "sha", "SHA-224", "SHA-256", "SHA-384", "SHA-512"]


@dataclass
class DiagSnmpInput:
    host_name: HostName
    ip_address: HostAddress
    address_family: Literal["no-ip", "ip-v4-only", "ip-v6-only", "ip-v4v6"]
    snmp_version: Literal["snmp-v1", "snmp-v2"]
    snmp_community: str | None
    snmpv3_use: SnmpV3SecurityLevel | None
    snmpv3_auth_proto: SnmpV3AuthProtocol | None
    snmpv3_security_name: str | None
    snmpv3_security_password: str | None
    snmpv3_privacy_proto: str | None
    snmpv3_privacy_password: str | None
    port: int
    timeout: int
    retries: int

    @classmethod
    def deserialize(cls, serialized_input: str) -> DiagSnmpInput:
        raw = json.loads(serialized_input)
        return cls(
            host_name=HostName(raw["host_name"]),
            ip_address=HostAddress(raw["ip_address"]),
            address_family=raw["address_family"],
            snmp_version=raw["snmp_version"],
            snmp_community=raw.get("snmp_community"),
            snmpv3_use=raw.get("snmpv3_use"),
            snmpv3_auth_proto=raw.get("snmpv3_auth_proto"),
            snmpv3_security_name=raw.get("snmpv3_security_name"),
            snmpv3_security_password=raw.get("snmpv3_security_password"),
            snmpv3_privacy_proto=raw.get("snmpv3_privacy_proto"),
            snmpv3_privacy_password=raw.get("snmpv3_privacy_password"),
            port=raw.get("port", 161),
            timeout=raw.get("timeout", 5),
            retries=raw.get("retries", 1),
        )

    def serialize(self, _for_cmk_version: cmk_version.Version) -> str:
        return json.dumps(
            {
                "host_name": self.host_name,
                "ip_address": self.ip_address,
                "address_family": self.address_family,
                "snmp_version": self.snmp_version,
                "snmp_community": self.snmp_community,
                "snmpv3_use": self.snmpv3_use,
                "snmpv3_auth_proto": self.snmpv3_auth_proto,
                "snmpv3_security_name": self.snmpv3_security_name,
                "snmpv3_security_password": self.snmpv3_security_password,
                "snmpv3_privacy_proto": self.snmpv3_privacy_proto,
                "snmpv3_privacy_password": self.snmpv3_privacy_password,
                "port": self.port,
                "timeout": self.timeout,
                "retries": self.retries,
            }
        )


@dataclass
class DiagSnmpResult(ABCAutomationResult):
    return_code: int
    response: str

    @staticmethod
    def automation_call() -> AutomationID:
        return AutomationID("diag-snmp")


result_type_registry.register(DiagSnmpResult)


@dataclass
class DiagHostResult(ABCAutomationResult):
    return_code: int
    response: str

    @staticmethod
    def automation_call() -> AutomationID:
        return AutomationID("diag-host")


result_type_registry.register(DiagHostResult)


@dataclass
class PingHostResult(ABCAutomationResult):
    return_code: int
    response: str

    @staticmethod
    def automation_call() -> AutomationID:
        return AutomationID("ping-host")


result_type_registry.register(PingHostResult)


class PingHostCmd(StrEnum):
    PING = "ping"
    PING6 = "ping6"


@dataclass
class PingHostInput:
    ip_or_dns_name: str
    base_cmd: PingHostCmd = PingHostCmd.PING

    @classmethod
    def deserialize(cls, serialized_input: str) -> PingHostInput:
        raw = json.loads(serialized_input)
        deserialized = {
            "ip_or_dns_name": raw["ip_or_dns_name"],
            "base_cmd": PingHostCmd(raw.get("base_cmd", PingHostCmd.PING)),
        }
        return cls(**deserialized)

    def serialize(self, _for_cmk_version: cmk_version.Version) -> str:
        return json.dumps(
            {
                "ip_or_dns_name": self.ip_or_dns_name,
                "base_cmd": self.base_cmd.value,
            }
        )


@dataclass
class CreateDiagnosticsDumpResult(ABCAutomationResult):
    output: str
    tarfile_path: str
    tarfile_created: bool

    @staticmethod
    def automation_call() -> AutomationID:
        return AutomationID("create-diagnostics-dump")


result_type_registry.register(CreateDiagnosticsDumpResult)
