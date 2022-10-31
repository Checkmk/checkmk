#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Check_MK base specific code of the crash reporting"""

import os
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, Literal, Mapping, Optional, Union

import cmk.utils.crash_reporting as crash_reporting
import cmk.utils.debug
import cmk.utils.encoding
import cmk.utils.paths
from cmk.utils.type_defs import (
    AgentRawData,
    CheckPluginName,
    CheckPluginNameStr,
    HostName,
    SectionName,
    ServiceName,
)

from cmk.snmplib.type_defs import SNMPBackendEnum

from cmk.base.config import HostConfig

CrashReportStore = crash_reporting.CrashReportStore


@crash_reporting.crash_report_registry.register
class CMKBaseCrashReport(crash_reporting.ABCCrashReport):
    @classmethod
    def type(cls) -> str:
        return "base"

    @classmethod
    def from_exception(
        cls,
        details: Mapping[str, Any] | None = None,
        type_specific_attributes: Mapping[str, Any] | None = None,
    ) -> crash_reporting.ABCCrashReport:
        return super().from_exception(
            details={
                "argv": sys.argv,
                "env": dict(os.environ),
            }
        )


def create_section_crash_dump(
    *,
    operation: str,
    section_name: SectionName,
    section_content: object,
    host_name: HostName,
    rtc_package: Optional[AgentRawData],
) -> str:
    """Create a crash dump from an exception raised in a parse or host label function"""

    text = f"{operation.title()} of section {section_name} failed"
    try:
        crash = SectionCrashReport.from_exception(
            details={
                "section_name": str(section_name),
                "section_content": section_content,
                "host_name": host_name,
            },
            type_specific_attributes={
                "snmp_info": _read_snmp_info(host_name),
                "agent_output": (
                    _read_agent_output(host_name) if rtc_package is None else rtc_package
                ),
            },
        )
        CrashReportStore().save(crash)
        return f"{text} - please submit a crash report! (Crash-ID: {crash.ident_to_text()})"
    except Exception:
        if cmk.utils.debug.enabled():
            raise
        return f"{text} - failed to create a crash report: {traceback.format_exc()}"


def create_check_crash_dump(
    *,
    host_config: HostConfig,
    service_name: ServiceName,
    plugin_name: Union[CheckPluginNameStr, CheckPluginName],
    plugin_kwargs: Mapping[str, Any],
    is_enforced: bool,
    rtc_package: Optional[AgentRawData],
) -> str:
    """Create a crash dump from an exception occured during check execution

    The crash dump is put into a tarball, base64 encoded and appended to the long output
    of the check. The GUI (cmk.gui.crash_reporting) is able to parse it and send it to
    the Checkmk team.
    """
    text = "check failed - please submit a crash report!"
    try:
        crash = CheckCrashReport.from_exception(
            details={
                "check_output": text,
                "host": host_config.hostname,
                "is_cluster": host_config.is_cluster,
                "description": service_name,
                "check_type": str(plugin_name),
                "inline_snmp": (
                    host_config.snmp_config(host_config.hostname).snmp_backend
                    == SNMPBackendEnum.INLINE
                ),
                "enforced_service": is_enforced,
                **plugin_kwargs,
            },
            type_specific_attributes={
                "snmp_info": _read_snmp_info(host_config.hostname),
                "agent_output": _read_agent_output(host_config.hostname)
                if rtc_package is None
                else rtc_package,
            },
        )
        CrashReportStore().save(crash)
        text += " (Crash-ID: %s)" % crash.ident_to_text()
        return text
    except Exception:
        if cmk.utils.debug.enabled():
            raise
        return "check failed - failed to create a crash report: %s" % traceback.format_exc()


class CrashReportWithAgentOutput(crash_reporting.ABCCrashReport):
    def __init__(
        self,
        crash_info: Dict,
        snmp_info: Optional[bytes] = None,
        agent_output: Optional[bytes] = None,
    ) -> None:
        super().__init__(crash_info)
        self.snmp_info = snmp_info
        self.agent_output = agent_output

    def _serialize_attributes(self) -> Dict:
        """Serialize object type specific attributes for transport"""
        attributes = super()._serialize_attributes()

        for key, val in [
            ("snmp_info", self.snmp_info),
            ("agent_output", self.agent_output),
        ]:
            if val is not None:
                attributes[key] = val

        return attributes


@crash_reporting.crash_report_registry.register
class SectionCrashReport(CrashReportWithAgentOutput):
    @staticmethod
    def type() -> Literal["section"]:
        return "section"


@crash_reporting.crash_report_registry.register
class CheckCrashReport(CrashReportWithAgentOutput):
    @staticmethod
    def type() -> Literal["check"]:
        return "check"


def _read_snmp_info(hostname: str) -> Optional[bytes]:
    cache_path = Path(cmk.utils.paths.data_source_cache_dir, "snmp", hostname)
    try:
        with cache_path.open(mode="rb") as f:
            return f.read()
    except IOError:
        pass
    return None


def _read_agent_output(hostname: str) -> Optional[AgentRawData]:
    cache_path = Path(cmk.utils.paths.tcp_cache_dir, hostname)
    try:
        with cache_path.open(mode="rb") as f:
            return AgentRawData(f.read())
    except IOError:
        pass
    return None
