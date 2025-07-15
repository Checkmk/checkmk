#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Check_MK base specific code of the crash reporting"""

import traceback
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal, TypedDict

import cmk.ccc.debug
import cmk.ccc.version as cmk_version
from cmk.ccc import crash_reporting
from cmk.ccc.crash_reporting import CrashInfo
from cmk.ccc.hostaddress import HostName

import cmk.utils.encoding
import cmk.utils.paths
from cmk.utils.agentdatatype import AgentRawData
from cmk.utils.sectionname import SectionName
from cmk.utils.servicename import ServiceName

from cmk.snmplib import SNMPBackendEnum

from cmk.checkengine.plugins import CheckPluginName

from cmk.piggyback.backend import get_messages_for

CrashReportStore = crash_reporting.CrashReportStore


def create_section_crash_dump(
    *,
    operation: str,
    section_name: SectionName,
    section_content: Sequence[object],
    host_name: HostName,
    rtc_package: AgentRawData | None,
) -> str:
    """Create a crash dump from an exception raised in a parse or host label function"""

    text = f"{operation.title()} of section {section_name} failed"
    try:
        crash = SectionCrashReport(
            cmk.utils.paths.crash_dir,
            SectionCrashReport.make_crash_info(
                cmk_version.get_general_version_infos(cmk.utils.paths.omd_root),
                details={
                    "section_name": str(section_name),
                    "section_content": section_content,
                    "host_name": host_name,
                },
            ),
            snmp_info=_read_snmp_info(host_name),
            agent_output=_read_agent_output(host_name) if rtc_package is None else rtc_package,
        )
        CrashReportStore().save(crash)
        return f"{text} - please submit a crash report! (Crash-ID: {crash.ident_to_text()})"
    except Exception:
        if cmk.ccc.debug.enabled():
            raise
        return f"{text} - failed to create a crash report: {traceback.format_exc()}"


def create_check_crash_dump(
    host_name: HostName,
    service_name: ServiceName,
    *,
    plugin_name: str | CheckPluginName,
    plugin_kwargs: dict[str, Any],
    is_cluster: bool,
    is_enforced: bool,
    snmp_backend: SNMPBackendEnum,
    rtc_package: AgentRawData | None,
) -> str:
    """Create a crash dump from an exception occurred during check execution

    The crash dump is put into a tarball, base64 encoded and appended to the long output
    of the check. The GUI (cmk.gui.crash_reporting) is able to parse it and send it to
    the Checkmk team.
    """
    text = "check failed - please submit a crash report!"
    try:
        crash = CheckCrashReport(
            cmk.utils.paths.crash_dir,
            CheckCrashReport.make_crash_info(
                cmk_version.get_general_version_infos(cmk.utils.paths.omd_root),
                CheckDetails(
                    check_output=text,
                    host=host_name,
                    is_cluster=is_cluster,
                    description=service_name,
                    check_type=str(plugin_name),
                    inline_snmp=snmp_backend is SNMPBackendEnum.INLINE,
                    enforced_service=is_enforced,
                    # TODO: Change CheckDetails to use extra_items=True in Python 3.13 (PEP 728)
                    **plugin_kwargs,  # type: ignore[typeddict-item]
                ),
            ),
            snmp_info=_read_snmp_info(host_name),
            agent_output=_read_agent_output(host_name) if rtc_package is None else rtc_package,
        )
        CrashReportStore().save(crash)
        text += " (Crash-ID: %s)" % crash.ident_to_text()
        return text
    except Exception:
        if cmk.ccc.debug.enabled():
            raise
        return "check failed - failed to create a crash report: %s" % traceback.format_exc()


class CrashReportWithAgentOutput[T](crash_reporting.ABCCrashReport[T]):
    def __init__(
        self,
        crashdir: Path,
        crash_info: CrashInfo,
        snmp_info: bytes | None = None,
        agent_output: bytes | None = None,
    ) -> None:
        super().__init__(crashdir, crash_info)
        self.snmp_info = snmp_info
        self.agent_output = agent_output

    def _serialize_attributes(self) -> dict:
        """Serialize object type specific attributes for transport"""
        attributes = super()._serialize_attributes()

        for key, val in [
            ("snmp_info", self.snmp_info),
            ("agent_output", self.agent_output),
        ]:
            if val is not None:
                attributes[key] = val

        return attributes


class SectionDetails(TypedDict):
    host_name: str
    section_name: str
    section_content: Sequence[object]


@crash_reporting.crash_report_registry.register
class SectionCrashReport(CrashReportWithAgentOutput[SectionDetails]):
    @staticmethod
    def type() -> Literal["section"]:
        return "section"


class CheckDetails(TypedDict):
    check_output: str
    item: str
    host: str
    check_type: str
    params: dict[str, Any]
    is_cluster: bool
    manual_check: bool
    enforced_service: bool
    uses_snmp: bool
    inline_snmp: bool
    description: str


@crash_reporting.crash_report_registry.register
class CheckCrashReport(CrashReportWithAgentOutput[CheckDetails]):
    @staticmethod
    def type() -> Literal["check"]:
        return "check"


def _read_snmp_info(hostname: str) -> bytes | None:
    try:
        with (cmk.utils.paths.snmpwalks_dir / hostname).open(mode="rb") as f:
            return f.read()
    except OSError:
        return None


def _read_agent_output(hostname: HostName) -> AgentRawData | None:
    agent_outputs = []

    cache_path = cmk.utils.paths.tcp_cache_dir / hostname
    try:
        agent_outputs.append(cache_path.read_bytes())
    except OSError:
        pass

    # Note: this is not quite what the fetcher does :(
    agent_outputs.extend(r.raw_data for r in get_messages_for(hostname, cmk.utils.paths.omd_root))

    if agent_outputs:
        return AgentRawData(b"\n".join(agent_outputs))
    return None
