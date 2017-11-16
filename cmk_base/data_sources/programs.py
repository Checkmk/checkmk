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

import os
import signal
import subprocess

import cmk.paths

import cmk_base.console as console
import cmk_base.config as config
import cmk_base.core_config as core_config
import cmk_base.checks as checks
from cmk_base.exceptions import MKAgentError, MKTimeout

from .abstract import CheckMKAgentDataSource

#.
#   .--Datasoure Programs--------------------------------------------------.
#   |      ____        _                     ____                          |
#   |     |  _ \  __ _| |_ __ _ ___ _ __ ___|  _ \ _ __ ___   __ _         |
#   |     | | | |/ _` | __/ _` / __| '__/ __| |_) | '__/ _ \ / _` |        |
#   |     | |_| | (_| | || (_| \__ \ | | (__|  __/| | | (_) | (_| |_       |
#   |     |____/ \__,_|\__\__,_|___/_|  \___|_|   |_|  \___/ \__, (_)      |
#   |                                                        |___/         |
#   +----------------------------------------------------------------------+
#   | Fetching agent data from program calls instead of an agent           |
#   '----------------------------------------------------------------------'

class ProgramDataSource(CheckMKAgentDataSource):
    """Abstract base class for all data source classes that execute external programs"""
    def _cpu_tracking_id(self):
        return "ds"


    def _execute(self, hostname, ipaddress):
        command_line = self._get_command_line(hostname, ipaddress)
        return self._get_agent_info_program(command_line)


    def _get_agent_info_program(self, commandline):
        exepath = commandline.split()[0] # for error message, hide options!

        console.vverbose("Calling external program %s\n" % commandline)
        p = None
        try:
            if config.monitoring_core == "cmc":
                p = subprocess.Popen(commandline, shell=True, stdin=open(os.devnull), # nosec
                                     stdout=subprocess.PIPE, stderr = subprocess.PIPE,
                                     preexec_fn=os.setsid, close_fds=True)
            else:
                # We can not create a separate process group when running Nagios
                # Upon reaching the service_check_timeout Nagios only kills the process
                # group of the active check.
                p = subprocess.Popen(commandline, shell=True, stdin=open(os.devnull), # nosec
                                     stdout=subprocess.PIPE, stderr = subprocess.PIPE,
                                     close_fds=True)
            stdout, stderr = p.communicate()
            exitstatus = p.returncode
        except MKTimeout:
            # On timeout exception try to stop the process to prevent child process "leakage"
            if p:
                os.killpg(os.getpgid(p.pid), signal.SIGTERM)
                p.wait()
            raise
        finally:
            # The stdout and stderr pipe are not closed correctly on a MKTimeout
            # Normally these pipes getting closed after p.communicate finishes
            # Closing them a second time in a OK scenario won't hurt neither..
            if p:
                p.stdout.close()
                p.stderr.close()

        if exitstatus:
            if exitstatus == 127:
                raise MKAgentError("Program '%s' not found (exit code 127)" % exepath)
            else:
                raise MKAgentError("Agent exited with code %d: %s" % (exitstatus, stderr))

        return stdout


    def _get_command_line(self, hostname, ipaddress):
        """Returns the final command line to be executed"""
        raise NotImplementedError()


    def describe(self, hostname, ipaddress):
        """Return a short textual description of the agent"""
        return "Program: %s" % self._get_command_line(hostname, ipaddress)




class DSProgramDataSource(ProgramDataSource):
    def __init__(self, command_template):
        super(DSProgramDataSource, self).__init__()
        self._command_template = command_template


    def id(self):
        return "agent"


    def name(self, hostname, ipaddress):
        """Return a unique (per host) textual identification of the data source"""
        program = self._get_command_line(hostname, ipaddress).split(" ")[0]
        return os.path.basename(program)


    def _get_command_line(self, hostname, ipaddress):
        cmd = self._command_template

        cmd = self._translate_legacy_macros(cmd, hostname, ipaddress)
        cmd = self._translate_host_macros(cmd, hostname)

        return cmd


    def _translate_legacy_macros(self, cmd, hostname, ipaddress):
        # Make "legacy" translation. The users should use the $...$ macros in future
        return cmd.replace("<IP>", ipaddress or "").replace("<HOST>", hostname)


    def _translate_host_macros(self, cmd, hostname):
        tags = config.tags_of_host(hostname)
        attrs = core_config.get_host_attributes(hostname, tags)
        if config.is_cluster(hostname):
            parents_list = core_config.get_cluster_nodes_for_config(hostname)
            attrs.setdefault("alias", "cluster of %s" % ", ".join(parents_list))
            attrs.update(core_config.get_cluster_attributes(hostname, parents_list))

        macros = core_config.get_host_macros_from_attributes(hostname, attrs)
        return core_config.replace_macros(cmd, macros)



class SpecialAgentDataSource(ProgramDataSource):
    def __init__(self, special_agent_id, params):
        super(SpecialAgentDataSource, self).__init__()
        self._special_agent_id = special_agent_id
        self._params = params


    def id(self):
        return "special_%s" % self._special_agent_id


    # TODO: Can't we make this more specific in case of special agents?
    def _gather_check_types(self, hostname, ipaddress):
        return checks.discoverable_tcp_checks()


    def _get_command_line(self, hostname, ipaddress):
        """Create command line using the special_agent_info"""
        info_func = checks.special_agent_info[self._special_agent_id]
        cmd_arguments = info_func(self._params, hostname, ipaddress)

        special_agents_dir       = cmk.paths.agents_dir + "/special"
        local_special_agents_dir = cmk.paths.local_agents_dir + "/special"

        if os.path.exists(local_special_agents_dir + "/agent_" + self._special_agent_id):
            path = local_special_agents_dir + "/agent_" + self._special_agent_id
        else:
            path = special_agents_dir + "/agent_" + self._special_agent_id

        return path + " " + cmd_arguments
