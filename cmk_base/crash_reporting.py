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
from typing import (Text, Tuple)  # pylint: disable=unused-import

import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.crash_reporting as crash_reporting

import cmk_base.utils
import cmk_base.check_utils
import cmk_base.config as config

CrashReportStore = crash_reporting.CrashReportStore


@crash_reporting.crash_report_registry.register
class CMKBaseCrashReport(crash_reporting.ABCCrashReport):
    @classmethod
    def type(cls):
        return "base"

    @classmethod
    def from_exception(cls, details=None, type_specific_attributes=None):
        return super(CMKBaseCrashReport, cls).from_exception(details={
            "argv": sys.argv,
            "env": dict(os.environ),
        })


def create_check_crash_dump(hostname, check_plugin_name, item, is_manual_check, params, description,
                            info):
    """Create a crash dump from an exception occured during check execution

    The crash dump is put into a tarball, base64 encoded and appended to the long output
    of the check. The GUI (cmk.gui.crash_reporting) is able to parse it and send it to
    the Checkmk team.
    """
    text = "check failed - please submit a crash report!"
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
        text += "\n" + "Crash dump:\n" + crash.get_packed() + "\n"
        return text
    except Exception:
        if cmk.utils.debug.enabled():
            raise
        return "check failed - failed to create a crash report: %s" % traceback.format_exc()


@crash_reporting.crash_report_registry.register
class CheckCrashReport(crash_reporting.ABCCrashReport):
    @classmethod
    def type(cls):
        return "check"

    @classmethod
    def from_exception_and_context(cls, hostname, check_plugin_name, item, is_manual_check, params,
                                   description, info, text):
        config_cache = config.get_config_cache()
        host_config = config_cache.get_host_config(hostname)

        snmp_info, agent_output = None, None
        if cmk_base.check_utils.is_snmp_check(check_plugin_name):
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
                "uses_snmp": cmk_base.check_utils.is_snmp_check(check_plugin_name),
                "inline_snmp": host_config.snmp_config(hostname).is_inline_snmp_host,
                "manual_check": is_manual_check,
            },
            type_specific_attributes={
                "snmp_info": snmp_info,
                "agent_output": agent_output,
            },
        )

    def __init__(self, crash_info, snmp_info, agent_output):
        super(CheckCrashReport, self).__init__(crash_info)
        self.snmp_info = snmp_info
        self.agent_output = agent_output

    def ident(self):
        # type: () -> Tuple[Text, Text]
        """The identitfy of the crash report
        This makes Check_MK keep one report for each host/service"""
        return (self.crash_info["details"]["host"], self.crash_info["details"]["description"])

    def _serialize_attributes(self):
        # type: () -> dict
        """Serialize object type specific attributes for transport"""
        attributes = super(CheckCrashReport, self)._serialize_attributes()
        attributes.update({
            "snmp_info": self.snmp_info,
            "agent_output": self.agent_output,
        })
        return attributes


def _read_snmp_info(hostname):
    cachefile_path = "%s/snmp/%s" % (cmk.utils.paths.data_source_cache_dir, hostname)
    if not os.path.exists(cachefile_path):
        return

    with open(cachefile_path) as f:
        return f.read()


def _read_agent_output(hostname):
    try:
        import cmk_base.cee.real_time_checks as real_time_checks
    except ImportError:
        real_time_checks = None

    if real_time_checks and real_time_checks.is_real_time_check_helper():
        return real_time_checks.get_rtc_package()

    cachefile = "%s/%s" % (cmk.utils.paths.tcp_cache_dir, hostname)
    if not os.path.exists(cachefile):
        return

    with open(cachefile) as f:
        return f.read()
