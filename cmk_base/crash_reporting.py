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
import base64
import tarfile
import cStringIO as StringIO

import cmk.debug
import cmk.paths
import cmk_base.checks as checks
import cmk_base.config as config
import cmk.crash_reporting as crash_reporting

import cmk_base.utils

# Create a crash dump with a backtrace and the agent output.
# This is put into a directory per service. The content is then
# put into a tarball, base64 encoded and put into the long output
# of the check :-)
def create_crash_dump(hostname, check_type, item, is_manual_check, params, description, info):
    text = "check failed - please submit a crash report!"
    try:
        crash_dir = cmk.paths.var_dir + "/crashed_checks/" + hostname + "/" + description.replace("/", "\\")
        _prepare_crash_dump_directory(crash_dir)

        _create_crash_dump_info_file(crash_dir, hostname, check_type, item, is_manual_check, params, description, info, text)
        if checks.is_snmp_check(check_type):
            _write_crash_dump_snmp_info(crash_dir, hostname, check_type)
        else:
            _write_crash_dump_agent_output(crash_dir, hostname)

        text += "\n" + "Crash dump:\n" + _pack_crash_dump(crash_dir) + "\n"
    except:
        if cmk.debug.enabled():
            raise

    return text


def _prepare_crash_dump_directory(crash_dir):
    if not os.path.exists(crash_dir):
        os.makedirs(crash_dir)
    # Remove all files of former crash reports
    for f in os.listdir(crash_dir):
        try:
            os.unlink(crash_dir + "/" + f)
        except OSError:
            pass


def _create_crash_dump_info_file(crash_dir, hostname, check_type, item, is_manual_check, params, description, info, text):
    crash_info = crash_reporting.create_crash_info("check", details={
        "check_output"  : text,
        "host"          : hostname,
        "is_cluster"    : config.is_cluster(hostname),
        "description"   : description,
        "check_type"    : check_type,
        "item"          : item,
        "params"        : params,
        "uses_snmp"     : checks.is_snmp_check(check_type),
        "inline_snmp"   : config.is_inline_snmp_host(hostname),
        "manual_check"  : is_manual_check,
    })
    file(crash_dir+"/crash.info", "w").write(crash_reporting.crash_info_to_string(crash_info)+"\n")


def _write_crash_dump_snmp_info(crash_dir, hostname, check_type):
    cachefile = cmk.paths.tcp_cache_dir + "/" + hostname + "." + check_type.split(".")[0]
    if os.path.exists(cachefile):
        file(crash_dir + "/snmp_info", "w").write(file(cachefile).read())


def _write_crash_dump_agent_output(crash_dir, hostname):
    try:
        import cmk_base.cee.real_time_checks as real_time_checks
    except ImportError:
        real_time_checks = None

    if real_time_checks and real_time_checks.is_real_time_check_helper():
        file(crash_dir + "/agent_output", "w").write(real_time_checks.get_rtc_package())
    else:
        cachefile = cmk.paths.tcp_cache_dir + "/" + hostname
        if os.path.exists(cachefile):
            file(crash_dir + "/agent_output", "w").write(file(cachefile).read())


def _pack_crash_dump(crash_dir):
    buf = StringIO.StringIO()
    with tarfile.open(mode="w:gz", fileobj=buf) as tar:
        for filename in os.listdir(crash_dir):
            tar.add(os.path.join(crash_dir, filename), filename)

    return base64.b64encode(buf.getvalue())
