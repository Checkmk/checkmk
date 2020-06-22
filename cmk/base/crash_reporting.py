#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Check_MK base specific code of the crash reporting"""

import os
import sys
import traceback
from typing import Any, Dict, Optional
from pathlib import Path

import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.encoding
import cmk.utils.crash_reporting as crash_reporting
from cmk.utils.type_defs import (
    HostName,
    CheckPluginName,
    ServiceName,
)

import cmk.base.check_utils
import cmk.base.config as config
from cmk.base.check_utils import RawAgentData

CrashReportStore = crash_reporting.CrashReportStore


@crash_reporting.crash_report_registry.register
class CMKBaseCrashReport(crash_reporting.ABCCrashReport):
    @classmethod
    def type(cls):
        # type: () -> str
        return "base"

    @classmethod
    def from_exception(cls, details=None, type_specific_attributes=None):
        # type: (Dict, Dict) -> crash_reporting.ABCCrashReport
        return super(CMKBaseCrashReport, cls).from_exception(details={
            "argv": sys.argv,
            "env": dict(os.environ),
        })


def create_check_crash_dump(
    hostname: HostName,
    check_plugin_name: CheckPluginName,
    check_plugin_kwargs: Dict[str, Any],
    is_manual_check: bool,
    description: ServiceName,
) -> str:
    """Create a crash dump from an exception occured during check execution

    The crash dump is put into a tarball, base64 encoded and appended to the long output
    of the check. The GUI (cmk.gui.crash_reporting) is able to parse it and send it to
    the Checkmk team.
    """
    text = u"check failed - please submit a crash report!"
    try:
        crash = CheckCrashReport.from_exception_and_context(
            hostname=hostname,
            check_plugin_name=check_plugin_name,
            check_plugin_kwargs=check_plugin_kwargs,
            is_manual_check=is_manual_check,
            description=description,
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
class CheckCrashReport(crash_reporting.ABCCrashReport):
    @classmethod
    def type(cls):
        # type: () -> str
        return "check"

    @classmethod
    def from_exception_and_context(
        cls,
        hostname: HostName,
        check_plugin_name: CheckPluginName,
        check_plugin_kwargs: Dict[str, Any],
        is_manual_check: bool,
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
                "uses_snmp": cmk.base.check_utils.is_snmp_check(check_plugin_name),
                "inline_snmp": host_config.snmp_config(hostname).is_inline_snmp_host,
                "manual_check": is_manual_check,
                **check_plugin_kwargs,
            },
            type_specific_attributes={
                "snmp_info": snmp_info,
                "agent_output": agent_output,
            },
        )

    def __init__(self, crash_info, snmp_info=None, agent_output=None):
        # type: (Dict, Optional[bytes], Optional[bytes]) -> None
        super(CheckCrashReport, self).__init__(crash_info)
        self.snmp_info = snmp_info
        self.agent_output = agent_output

    def _serialize_attributes(self):
        # type: () -> Dict
        """Serialize object type specific attributes for transport"""
        attributes = super(CheckCrashReport, self)._serialize_attributes()

        for key, val in [
            ("snmp_info", self.snmp_info),
            ("agent_output", self.agent_output),
        ]:
            if val is not None:
                attributes[key] = val

        return attributes


def _read_snmp_info(hostname):
    # type: (str) -> Optional[bytes]
    cache_path = Path(cmk.utils.paths.data_source_cache_dir, "snmp", hostname)
    try:
        with cache_path.open(mode="rb") as f:
            return f.read()
    except IOError:
        pass
    return None


def _read_agent_output(hostname):
    # type: (str) -> Optional[RawAgentData]
    try:
        import cmk.base.cee.real_time_checks as real_time_checks  # pylint: disable=import-outside-toplevel
    except ImportError:
        real_time_checks = None  # type: ignore[assignment]

    if real_time_checks and real_time_checks.is_real_time_check_helper():
        return real_time_checks.get_rtc_package()

    cache_path = Path(cmk.utils.paths.tcp_cache_dir, hostname)
    try:
        with cache_path.open(mode="rb") as f:
            return f.read()
    except IOError:
        pass
    return None
