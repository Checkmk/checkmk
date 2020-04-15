#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import collections
import os
import signal
import sys
from logging import Logger  # pylint: disable=unused-import
from types import TracebackType  # pylint: disable=unused-import
from typing import Dict, Optional, Set, Text, Type, Union  # pylint: disable=unused-import

import six

if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error
else:
    from pathlib2 import Path  # pylint: disable=import-error

import cmk.utils.paths
from cmk.utils.exceptions import MKTimeout
import cmk.utils.cmk_subprocess as subprocess
from cmk.utils.encoding import ensure_bytestr

import cmk.base.config as config
import cmk.base.core_config as core_config
from cmk.base.exceptions import MKAgentError
from cmk.base.check_utils import CheckPluginName  # pylint: disable=unused-import
from cmk.utils.type_defs import (  # pylint: disable=unused-import
    HostName, HostAddress)

from .abstract import CheckMKAgentDataSource, RawAgentData  # pylint: disable=unused-import

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


class ProgramDataFetcher(object):  # pylint: disable=useless-object-inheritance
    def __init__(self, cmdline, stdin, logger):
        super(ProgramDataFetcher, self).__init__()
        self._cmdline = cmdline  # type: Union[bytes, Text]
        self._stdin = stdin  # type: Optional[str]
        self._logger = logger  # type: Logger
        self._process = None  # type: Optional[subprocess.Popen]

    def __enter__(self):
        # type: () -> ProgramDataFetcher
        if config.monitoring_core == "cmc":
            # Warning:
            # The preexec_fn parameter is not safe to use in the presence of threads in your
            # application. The child process could deadlock before exec is called. If you
            # must use it, keep it trivial! Minimize the number of libraries you call into.
            #
            # Note:
            # If you need to modify the environment for the child use the env parameter
            # rather than doing it in a preexec_fn. The start_new_session parameter can take
            # the place of a previously common use of preexec_fn to call os.setsid() in the
            # child.
            self._process = subprocess.Popen(
                self._cmdline,
                shell=True,
                stdin=subprocess.PIPE if self._stdin else open(os.devnull),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
                close_fds=True,
            )
        else:
            # We can not create a separate process group when running Nagios
            # Upon reaching the service_check_timeout Nagios only kills the process
            # group of the active check.
            self._process = subprocess.Popen(
                self._cmdline,
                shell=True,
                stdin=subprocess.PIPE if self._stdin else open(os.devnull),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                close_fds=True,
            )
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # type: (Optional[Type[BaseException]], Optional[BaseException], Optional[TracebackType]) -> None
        if self._process is None:
            return
        if exc_type is MKTimeout:
            # On timeout exception try to stop the process to prevent child process "leakage"
            os.killpg(os.getpgid(self._process.pid), signal.SIGTERM)
            self._process.wait()
        # The stdout and stderr pipe are not closed correctly on a MKTimeout
        # Normally these pipes getting closed after p.communicate finishes
        # Closing them a second time in a OK scenario won't hurt neither..
        if self._process.stdout is None or self._process.stderr is None:
            raise Exception("stdout needs to be set")
        self._process.stdout.close()
        self._process.stderr.close()
        self._process = None

    def data(self):
        # type: () -> RawAgentData
        if self._process is None:
            raise MKAgentError("No process")
        stdout, stderr = self._process.communicate(
            input=ensure_bytestr(self._stdin) if self._stdin else None)
        if self._process.returncode == 127:
            exepath = self._cmdline.split()[0]  # for error message, hide options!
            raise MKAgentError("Program '%s' not found (exit code 127)" % six.ensure_str(exepath))
        if self._process.returncode:
            raise MKAgentError("Agent exited with code %d: %s" %
                               (self._process.returncode, six.ensure_str(stderr)))
        return stdout


class ProgramDataSource(CheckMKAgentDataSource):
    """Abstract base class for all data source classes that execute external programs"""
    @property
    @abc.abstractmethod
    def source_cmdline(self):
        # type: () -> str
        """Return the command line to the source."""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def source_stdin(self):
        # type: () -> Optional[str]
        """Return the standard in of the source, or None."""
        raise NotImplementedError()

    def _cpu_tracking_id(self):
        # type: () -> str
        return "ds"

    def _execute(self):
        # type: () -> RawAgentData
        self._logger.debug("Calling external program %r" % (self.source_cmdline))
        with ProgramDataFetcher(self.source_cmdline, self.source_stdin, self._logger) as fetcher:
            return fetcher.data()
        raise MKAgentError("Failed to read data")

    def describe(self):
        # type: () -> str
        """Return a short textual description of the agent"""
        response = ["Program: %s" % self.source_cmdline]
        if self.source_stdin:
            response.extend(["  Program stdin:", self.source_stdin])
        return "\n".join(response)


class DSProgramDataSource(ProgramDataSource):
    def __init__(self, hostname, ipaddress, command_template):
        # type: (HostName, Optional[HostAddress], str) -> None
        super(DSProgramDataSource, self).__init__(hostname, ipaddress)
        self._command_template = command_template

    def id(self):
        # type: () -> str
        return "agent"

    def name(self):
        # type: () -> str
        """Return a unique (per host) textual identification of the data source"""
        program = self.source_cmdline.split(" ")[0]
        return os.path.basename(program)

    @property
    def source_cmdline(self):
        # type: () -> str
        cmd = self._command_template
        cmd = self._translate_legacy_macros(cmd)
        cmd = self._translate_host_macros(cmd)
        return cmd

    @property
    def source_stdin(self):
        return None

    def _translate_legacy_macros(self, cmd):
        # type: (str) -> str
        # Make "legacy" translation. The users should use the $...$ macros in future
        return cmd.replace("<IP>", self._ipaddress or "").replace("<HOST>", self._hostname)

    def _translate_host_macros(self, cmd):
        # type: (str) -> str
        attrs = core_config.get_host_attributes(self._hostname, self._config_cache)
        if self._host_config.is_cluster:
            parents_list = core_config.get_cluster_nodes_for_config(self._config_cache,
                                                                    self._host_config)
            attrs.setdefault("alias", "cluster of %s" % ", ".join(parents_list))
            attrs.update(
                core_config.get_cluster_attributes(self._config_cache, self._host_config,
                                                   parents_list))

        macros = core_config.get_host_macros_from_attributes(self._hostname, attrs)
        return six.ensure_str(core_config.replace_macros(cmd, macros))


SpecialAgentConfiguration = collections.namedtuple("SpecialAgentConfiguration", ["args", "stdin"])


class SpecialAgentDataSource(ProgramDataSource):
    def __init__(self, hostname, ipaddress, special_agent_id, params):
        # type: (HostName, Optional[HostAddress], str, Dict) -> None
        self._special_agent_id = special_agent_id
        super(SpecialAgentDataSource, self).__init__(hostname, ipaddress)
        self._params = params

    def id(self):
        # type: () -> str
        return "special_%s" % self._special_agent_id

    @property
    def special_agent_plugin_file_name(self):
        # type: () -> str
        return "agent_%s" % self._special_agent_id

    # TODO: Can't we make this more specific in case of special agents?
    def _gather_check_plugin_names(self):
        # type: () -> Set[CheckPluginName]
        return config.discoverable_tcp_checks()

    @property
    def _source_path(self):
        # type: () -> Path
        local_path = cmk.utils.paths.local_agents_dir / "special" / self.special_agent_plugin_file_name
        if local_path.exists():
            return local_path
        return Path(cmk.utils.paths.agents_dir) / "special" / self.special_agent_plugin_file_name

    @property
    def _source_args(self):
        # type: () -> str
        info_func = config.special_agent_info[self._special_agent_id]
        agent_configuration = info_func(self._params, self._hostname, self._ipaddress)
        if isinstance(agent_configuration, SpecialAgentConfiguration):
            cmd_arguments = agent_configuration.args
        else:
            cmd_arguments = agent_configuration

        return config.prepare_check_command(cmd_arguments, self._hostname, description=None)

    @property
    def source_cmdline(self):
        # type: () -> str
        """Create command line using the special_agent_info"""
        return "%s %s" % (self._source_path, self._source_args)

    @property
    def source_stdin(self):
        # type: () -> Optional[str]
        """Create command line using the special_agent_info"""
        info_func = config.special_agent_info[self._special_agent_id]
        agent_configuration = info_func(self._params, self._hostname, self._ipaddress)
        if isinstance(agent_configuration, SpecialAgentConfiguration):
            return agent_configuration.stdin
        return None
