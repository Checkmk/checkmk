#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Check_MK base specific code of the crash reporting"""

import os
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Union

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

import cmk.base.config as config

CrashReportStore = crash_reporting.CrashReportStore


@crash_reporting.crash_report_registry.register
class CMKBaseCrashReport(crash_reporting.ABCCrashReport):
    @classmethod
    def type(cls) -> str:
        return "base"

    @classmethod
    def from_exception(
        cls, details: Optional[Dict] = None, type_specific_attributes: Optional[Dict] = None
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
) -> str:
    """Create a crash dump from an exception raised in a parse or host label function"""

    text = f"{operation.title()} of section {section_name} failed"
    try:
        crash = SectionCrashReport.from_exception_and_context(
            section_name=section_name,
            section_content=section_content,
            host_name=host_name,
        )
        CrashReportStore().save(crash)
        return f"{text} - please submit a crash report! (Crash-ID: {crash.ident_to_text()})"
    except Exception:
        if cmk.utils.debug.enabled():
            raise
        return f"{text} - failed to create a crash report: {traceback.format_exc()}"


def create_check_crash_dump(
    *,
    host_name: HostName,
    service_name: ServiceName,
    plugin_name: Union[CheckPluginNameStr, CheckPluginName],
    plugin_kwargs: Mapping[str, Any],
    is_enforced: bool,
) -> str:
    """Create a crash dump from an exception occured during check execution

    The crash dump is put into a tarball, base64 encoded and appended to the long output
    of the check. The GUI (cmk.gui.crash_reporting) is able to parse it and send it to
    the Checkmk team.
    """
    text = "check failed - please submit a crash report!"
    try:
        crash = CheckCrashReport.from_exception_and_context(
            hostname=host_name,
            check_plugin_name=str(plugin_name),
            check_plugin_kwargs=plugin_kwargs,
            is_enforced_service=is_enforced,
            description=service_name,
            text=text,
        )
        CrashReportStore().save(crash)
        text += " (Crash-ID: %s)" % crash.ident_to_text()
        return text
    except Exception:
        if cmk.utils.debug.enabled():
            raise
        return "check failed - failed to create a crash report: %s" % traceback.format_exc()


@crash_reporting.crash_report_registry.register
class SectionCrashReport(crash_reporting.ABCCrashReport):
    @classmethod
    def type(cls) -> str:
        return "section"

    @classmethod
    def from_exception_and_context(
        cls,
        *,
        section_name: SectionName,
        section_content: object,
        host_name: HostName,
    ) -> crash_reporting.ABCCrashReport:
        return cls.from_exception(
            details={
                "section_name": str(section_name),
                "section_content": section_content,
                "host_name": host_name,
            },
        )


@crash_reporting.crash_report_registry.register
class CheckCrashReport(crash_reporting.ABCCrashReport):
    @classmethod
    def type(cls) -> str:
        return "check"

    @classmethod
    def from_exception_and_context(
        cls,
        hostname: HostName,
        check_plugin_name: str,
        check_plugin_kwargs: Mapping[str, Any],
        is_enforced_service: bool,
        description: ServiceName,
        text: str,
    ) -> crash_reporting.ABCCrashReport:
        config_cache = config.get_config_cache()
        host_config = config_cache.get_host_config(hostname)

        snmp_info = _read_snmp_info(hostname)
        agent_output = _read_agent_output(hostname)

        return cls.from_exception(
            details={
                "check_output": text,
                "host": hostname,
                "is_cluster": host_config.is_cluster,
                "description": description,
                "check_type": check_plugin_name,
                "inline_snmp": host_config.snmp_config(hostname).snmp_backend
                == SNMPBackendEnum.INLINE,
                "enforced_service": is_enforced_service,
                **check_plugin_kwargs,
            },
            type_specific_attributes={
                "snmp_info": snmp_info,
                "agent_output": agent_output,
            },
        )

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


def _read_snmp_info(hostname: str) -> Optional[bytes]:
    cache_path = Path(cmk.utils.paths.data_source_cache_dir, "snmp", hostname)
    try:
        with cache_path.open(mode="rb") as f:
            return f.read()
    except IOError:
        pass
    return None


def _read_agent_output(hostname: str) -> Optional[AgentRawData]:
    try:
        from cmk.base.cee.keepalive import rtc  # pylint: disable=import-outside-toplevel
    except ImportError:
        rtc = None  # type: ignore[assignment]

    if rtc and rtc.is_real_time_check_helper():
        return rtc.get_rtc_package()

    cache_path = Path(cmk.utils.paths.tcp_cache_dir, hostname)
    try:
        with cache_path.open(mode="rb") as f:
            return AgentRawData(f.read())
    except IOError:
        pass
    return None
