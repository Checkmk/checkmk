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
import collections
from pathlib2 import Path

import cmk.utils.paths
from cmk.utils.exceptions import MKTimeout

import cmk_base.config as config
import cmk_base.core_config as core_config
from cmk_base.exceptions import MKAgentError

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

    def _execute(self):
        command_line, command_stdin = self._get_command_line_and_stdin()
        return self._get_agent_info_program(command_line, command_stdin)

    def _get_agent_info_program(self, commandline, command_stdin):
        exepath = commandline.split()[0]  # for error message, hide options!

        self._logger.debug("Calling external program %r" % (commandline))
        p = None
        try:
            if config.monitoring_core == "cmc":
                p = subprocess.Popen(  # nosec
                    commandline,
                    shell=True,
                    stdin=subprocess.PIPE if command_stdin else open(os.devnull),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    preexec_fn=os.setsid,
                    close_fds=True)
            else:
                # We can not create a separate process group when running Nagios
                # Upon reaching the service_check_timeout Nagios only kills the process
                # group of the active check.
                p = subprocess.Popen(  # nosec
                    commandline,
                    shell=True,
                    stdin=subprocess.PIPE if command_stdin else open(os.devnull),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    close_fds=True)
            stdout, stderr = p.communicate(input=command_stdin)
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

    def _get_command_line_and_stdin(self):
        """Returns the final command line to be executed"""
        raise NotImplementedError()

    def describe(self):
        """Return a short textual description of the agent"""
        command_line, command_stdin = self._get_command_line_and_stdin()
        response = ["Program: %s" % command_line]
        if command_stdin:
            response.extend(["  Program stdin:", command_stdin])
        return "\n".join(response)


class DSProgramDataSource(ProgramDataSource):
    def __init__(self, hostname, ipaddress, command_template):
        super(DSProgramDataSource, self).__init__(hostname, ipaddress)
        self._command_template = command_template

    def id(self):
        return "agent"

    def name(self):
        """Return a unique (per host) textual identification of the data source"""
        command_line, _command_stdin = self._get_command_line_and_stdin()
        program = command_line.split(" ")[0]
        return os.path.basename(program)

    def _get_command_line_and_stdin(self):
        cmd = self._command_template

        cmd = self._translate_legacy_macros(cmd)
        cmd = self._translate_host_macros(cmd)

        return cmd, None

    def _translate_legacy_macros(self, cmd):
        # Make "legacy" translation. The users should use the $...$ macros in future
        return cmd.replace("<IP>", self._ipaddress or "").replace("<HOST>", self._hostname)

    def _translate_host_macros(self, cmd):
        attrs = core_config.get_host_attributes(self._hostname, self._config_cache)
        if self._host_config.is_cluster:
            parents_list = core_config.get_cluster_nodes_for_config(self._config_cache,
                                                                    self._host_config)
            attrs.setdefault("alias", "cluster of %s" % ", ".join(parents_list))
            attrs.update(
                core_config.get_cluster_attributes(self._config_cache, self._host_config,
                                                   parents_list))

        macros = core_config.get_host_macros_from_attributes(self._hostname, attrs)
        return core_config.replace_macros(cmd, macros)


SpecialAgentConfiguration = collections.namedtuple("SpecialAgentConfiguration", ["args", "stdin"])


class SpecialAgentDataSource(ProgramDataSource):
    def __init__(self, hostname, ipaddress, special_agent_id, params):
        self._special_agent_id = special_agent_id
        super(SpecialAgentDataSource, self).__init__(hostname, ipaddress)
        self._params = params

    def id(self):
        return "special_%s" % self._special_agent_id

    @property
    def special_agent_plugin_file_name(self):
        return "agent_%s" % self._special_agent_id

    # TODO: Can't we make this more specific in case of special agents?
    def _gather_check_plugin_names(self):
        return config.discoverable_tcp_checks()

    def _get_command_line_and_stdin(self):
        """Create command line using the special_agent_info"""
        info_func = config.special_agent_info[self._special_agent_id]
        agent_configuration = info_func(self._params, self._hostname, self._ipaddress)
        if isinstance(agent_configuration, SpecialAgentConfiguration):
            cmd_arguments = agent_configuration.args
            command_stdin = agent_configuration.stdin
        else:
            cmd_arguments = agent_configuration
            command_stdin = None

        final_arguments = config.prepare_check_command(cmd_arguments,
                                                       self._hostname,
                                                       description=None)

        agent_name = "agent_" + self._special_agent_id
        special_agent_path = Path(cmk.utils.paths.agents_dir, "special", agent_name)
        local_special_agent_path = cmk.utils.paths.local_agents_dir.joinpath("special", agent_name)

        path = local_special_agent_path if local_special_agent_path.exists() else special_agent_path
        return "%s %s" % (path, final_arguments), command_stdin
