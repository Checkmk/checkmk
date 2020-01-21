#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
"""Check_MK base specific code of the crash reporting"""

import os
import sys
import traceback
from typing import (Dict, Optional, Text, Tuple)  # pylint: disable=unused-import
from pathlib2 import Path

import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.encoding
import cmk.utils.crash_reporting as crash_reporting
from cmk.utils.type_defs import (  # pylint: disable=unused-import
    HostName, CheckPluginName, Item, ServiceName,
)

import cmk.base.utils
import cmk.base.check_utils
import cmk.base.config as config
from cmk.base.data_sources.host_sections import FinalSectionContent  # pylint: disable=unused-import
from cmk.base.check_utils import CheckParameters, RawAgentData  # pylint: disable=unused-import

CrashReportStore = crash_reporting.CrashReportStore


@crash_reporting.crash_report_registry.register
class CMKBaseCrashReport(crash_reporting.ABCCrashReport):
    @classmethod
    def type(cls):
        # type: () -> Text
        return "base"

    @classmethod
    def from_exception(cls, details=None, type_specific_attributes=None):
        # type: (Dict, Dict) -> crash_reporting.ABCCrashReport
        return super(CMKBaseCrashReport, cls).from_exception(details={
            "argv": sys.argv,
            "env": dict(os.environ),
        })


def create_check_crash_dump(hostname, check_plugin_name, item, is_manual_check, params, description,
                            info):
    # type: (HostName, CheckPluginName, Item, bool, CheckParameters, ServiceName, FinalSectionContent) -> Text
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
            item=item,
            is_manual_check=is_manual_check,
            params=params,
            description=description,
            info=info,
            text=text,
        )
        CrashReportStore().save(crash)
        text += "(Crash-ID: %s)" % crash.ident_to_text()
        return text
    except Exception:
        if cmk.utils.debug.enabled():
            raise
        return "check failed - failed to create a crash report: %s" % traceback.format_exc()


@crash_reporting.crash_report_registry.register
class CheckCrashReport(crash_reporting.ABCCrashReport):
    @classmethod
    def type(cls):
        # type: () -> Text
        return "check"

    @classmethod
    def from_exception_and_context(cls, hostname, check_plugin_name, item, is_manual_check, params,
                                   description, info, text):
        # type: (HostName, CheckPluginName, Item, bool, CheckParameters, ServiceName, FinalSectionContent, Text) -> crash_reporting.ABCCrashReport
        config_cache = config.get_config_cache()
        host_config = config_cache.get_host_config(hostname)

        snmp_info, agent_output = None, None
        if cmk.base.check_utils.is_snmp_check(check_plugin_name):
            snmp_info = _read_snmp_info(hostname)
        else:
            agent_output = _read_agent_output(hostname)

        return cls.from_exception(
            details={
                "check_output": text,
                "host": hostname,
                "is_cluster": host_config.is_cluster,
                "description": description,
                "check_type": check_plugin_name,
                "item": item,
                "params": params,
                "uses_snmp": cmk.base.check_utils.is_snmp_check(check_plugin_name),
                "inline_snmp": host_config.snmp_config(hostname).is_inline_snmp_host,
                "manual_check": is_manual_check,
            },
            type_specific_attributes={
                "snmp_info": snmp_info,
                "agent_output": agent_output,
            },
        )

    def __init__(self, crash_info, snmp_info, agent_output):
        # type: (Dict, Optional[Text], Optional[Text]) -> None
        super(CheckCrashReport, self).__init__(crash_info)
        self.snmp_info = snmp_info
        self.agent_output = agent_output

    def _serialize_attributes(self):
        # type: () -> Dict
        """Serialize object type specific attributes for transport"""
        attributes = super(CheckCrashReport, self)._serialize_attributes()
        attributes.update({
            "snmp_info": self.snmp_info,
            "agent_output": self.agent_output,
        })
        return attributes


def _read_snmp_info(hostname):
    # type: (str) -> Optional[Text]
    cache_path = Path(cmk.utils.paths.data_source_cache_dir, "snmp", hostname)
    try:
        with cache_path.open(encoding="utf-8") as f:
            return f.read()
    except IOError:
        pass
    return None


def _read_agent_output(hostname):
    # type: (str) -> Optional[Text]
    try:
        import cmk.base.cee.real_time_checks as real_time_checks
    except ImportError:
        real_time_checks = None  # type: ignore

    if real_time_checks and real_time_checks.is_real_time_check_helper():
        rtc_package = real_time_checks.get_rtc_package()
        if rtc_package is not None:
            return cmk.utils.encoding.convert_to_unicode(rtc_package)
        return None

    cache_path = Path(cmk.utils.paths.tcp_cache_dir, hostname)
    try:
        # Use similar decoding logic as cmk.base/data_sources/abstract.py does. In case this is not
        # working as intended, we may have to keep working with bytes here.
        with cache_path.open() as f:
            output = u""
            for l in f:
                output += cmk.utils.encoding.convert_to_unicode(l)
            return output
    except IOError:
        pass
    return None
