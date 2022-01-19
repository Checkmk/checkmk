#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import errno
import os
import signal
import time
from random import Random
from types import FrameType
from typing import IO, Optional, Sequence, Tuple, Union

import cmk.utils.paths
import cmk.utils.tty as tty
import cmk.utils.version as cmk_version
from cmk.utils.check_utils import ServiceCheckResult
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.log import console
from cmk.utils.type_defs import HostName, ServiceDetails, ServiceName, ServiceState

# TODO: make this two arguments!
import cmk.base.config as config

if not cmk_version.is_raw_edition():
    import cmk.base.cee.keepalive as keepalive  # type: ignore[import] # pylint: disable=no-name-in-module
else:
    keepalive = None  # type: ignore[assignment]

# global variables used to cache temporary values that do not need
# to be reset after a configuration change.
# Filedescriptor to open nagios command pipe.
_nagios_command_pipe: Union[bool, IO[bytes], None] = None
_checkresult_file_fd = None
_checkresult_file_path = None


def check_result(
    *,
    host_name: HostName,
    service_name: ServiceName,
    result: ServiceCheckResult,
    cache_info: Optional[Tuple[int, int]],
    dry_run: bool,
    show_perfdata: bool,
) -> None:
    perftexts = [_serialize_metric(*mt) for mt in result.metrics]
    if perftexts:
        check_command = _extract_check_command(result.output)
        if check_command and config.perfdata_format == "pnp":
            perftexts.append("[%s]" % check_command)
        perftext = "|" + (" ".join(perftexts))
    else:
        perftext = ""

    if not dry_run:
        # make sure that plugin output does not contain a vertical bar. If that is the
        # case then replace it with a Uniocode "Light vertical bar"
        _do_submit_to_core(
            host_name,
            service_name,
            result.state,
            result.output.replace("|", "\u2758") + perftext,
            cache_info,
        )

    _output_check_result(
        service_name, result.state, result.output, perftexts, show_perfdata=show_perfdata
    )


def finalize() -> None:
    global _checkresult_file_fd
    if _checkresult_file_fd is not None and _checkresult_file_path is not None:
        os.close(_checkresult_file_fd)
        _checkresult_file_fd = None

        with open(_checkresult_file_path + ".ok", "w"):
            pass


def _serialize_metric(
    name: str,
    value: float,
    warn: Optional[float],
    crit: Optional[float],
    min_: Optional[float],
    max_: Optional[float],
) -> str:
    """
    >>> _serialize_metric("hot_chocolate", 2.3, None, 42.0, 0.0, None)
    'hot_chocolate=2.3;;42;0;'

    """
    return (
        f"{name}={_serialize_value(value)};{_serialize_value(warn)};{_serialize_value(crit)};"
        f"{_serialize_value(min_)};{_serialize_value(max_)}"
    )


def _serialize_value(x: Optional[float]) -> str:
    return "" if x is None else ("%.6f" % x).rstrip("0").rstrip(".")


def _extract_check_command(infotext: str) -> Optional[str]:
    """
    Check may append the name of the check command to the
    details of service output.
    It might be needed by the graphing tool in order to choose the correct
    template or apply the correct metric name translations.
    Currently this is used only by mrpe.
    """
    marker = "Check command used in metric system: "
    return infotext.split(marker, 1)[1].split("\n")[0] if marker in infotext else None


def _do_submit_to_core(
    host: HostName,
    service: ServiceName,
    state: ServiceState,
    output: ServiceDetails,
    cache_info: Optional[Tuple[int, int]],
) -> None:
    if keepalive and keepalive.enabled():
        cached_at, cache_interval = cache_info or (None, None)
        # Regular case for the CMC - check helpers are running in keepalive mode
        keepalive.add_check_result(host, service, state, output, cached_at, cache_interval)

    elif config.check_submission == "pipe" or config.monitoring_core == "cmc":
        # In case of CMC this is used when running "cmk" manually
        _submit_via_command_pipe(host, service, state, output)

    elif config.check_submission == "file":
        _submit_via_check_result_file(host, service, state, output)

    else:
        raise MKGeneralException(
            "Invalid setting %r for check_submission. "
            "Must be 'pipe' or 'file'" % config.check_submission
        )


def _output_check_result(
    servicedesc: ServiceName,
    state: ServiceState,
    infotext: ServiceDetails,
    perftexts: Sequence[str],
    *,
    show_perfdata: bool,
) -> None:
    if show_perfdata:
        infotext_fmt = "%-56s"
        p = " (%s)" % (" ".join(perftexts))
    else:
        p = ""
        infotext_fmt = "%s"

    console.verbose(
        "%-20s %s%s" + infotext_fmt + "%s%s\n",
        servicedesc,
        tty.bold,
        tty.states[state],
        infotext.split("\n", 1)[0],
        tty.normal,
        p,
    )


def _submit_via_command_pipe(
    host: HostName, service: ServiceName, state: ServiceState, output: ServiceDetails
) -> None:
    output = output.replace("\n", "\\n")
    _open_command_pipe()
    if _nagios_command_pipe is not None and not isinstance(_nagios_command_pipe, bool):
        # [<timestamp>] PROCESS_SERVICE_CHECK_RESULT;<host_name>;<svc_description>;<return_code>;<plugin_output>
        msg = "[%d] PROCESS_SERVICE_CHECK_RESULT;%s;%s;%d;%s\n" % (
            time.time(),
            host,
            service,
            state,
            output,
        )
        _nagios_command_pipe.write(msg.encode())
        # Important: Nagios needs the complete command in one single write() block!
        # Python buffers and sends chunks of 4096 bytes, if we do not flush.
        _nagios_command_pipe.flush()


def _submit_via_check_result_file(
    host: HostName, service: ServiceName, state: ServiceState, output: ServiceDetails
) -> None:
    output = output.replace("\n", "\\n")
    _open_checkresult_file()
    if _checkresult_file_fd:
        now = time.time()
        os.write(
            _checkresult_file_fd,
            (
                """host_name=%s
service_description=%s
check_type=1
check_options=0
reschedule_check
latency=0.0
start_time=%.1f
finish_time=%.1f
return_code=%d
output=%s

"""
                % (host, service, now, now, state, output)
            ).encode(),
        )


def _open_command_pipe() -> None:
    global _nagios_command_pipe
    if _nagios_command_pipe is None:
        if not os.path.exists(cmk.utils.paths.nagios_command_pipe_path):
            _nagios_command_pipe = False  # False means: tried but failed to open
            raise MKGeneralException(
                "Missing core command pipe '%s'" % cmk.utils.paths.nagios_command_pipe_path
            )
        try:
            signal.signal(signal.SIGALRM, _core_pipe_open_timeout)
            signal.alarm(3)  # three seconds to open pipe
            _nagios_command_pipe = open(  # pylint:disable=consider-using-with
                cmk.utils.paths.nagios_command_pipe_path, "wb"
            )
            signal.alarm(0)  # cancel alarm
        except Exception as e:
            _nagios_command_pipe = False
            raise MKGeneralException("Error writing to command pipe: %s" % e)


def _open_checkresult_file() -> None:
    global _checkresult_file_fd
    global _checkresult_file_path
    if _checkresult_file_fd is None:
        try:
            _checkresult_file_fd, _checkresult_file_path = _create_nagios_check_result_file()
        except Exception as e:
            raise MKGeneralException(
                "Cannot create check result file in %s: %s" % (cmk.utils.paths.check_result_path, e)
            )


def _core_pipe_open_timeout(signum: int, stackframe: Optional[FrameType]) -> None:
    raise IOError("Timeout while opening pipe")


def _create_nagios_check_result_file() -> Tuple[int, str]:
    """Create some temporary file for storing the checkresults.
    Nagios expects a seven character long file starting with "c". Since Python3 we can not
    use tempfile.mkstemp anymore since it produces file names with 9 characters length.

    Logic is similar to tempfile.mkstemp, but simplified. No prefix/suffix/thread-safety
    """

    base_dir = cmk.utils.paths.check_result_path

    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW

    names = _get_candidate_names()
    for _seq in range(os.TMP_MAX):
        name = next(names)
        filepath = os.path.join(base_dir, "c" + name)
        try:
            fd = os.open(filepath, flags, 0o600)
        except FileExistsError:
            continue  # try again
        return (fd, os.path.abspath(filepath))

    raise FileExistsError(errno.EEXIST, "No usable temporary file name found")


_name_sequence: "Optional[_RandomNameSequence]" = None


def _get_candidate_names() -> "_RandomNameSequence":
    global _name_sequence
    if _name_sequence is None:
        _name_sequence = _RandomNameSequence()
    return _name_sequence


class _RandomNameSequence:
    """An instance of _RandomNameSequence generates an endless
    sequence of unpredictable strings which can safely be incorporated
    into file names.  Each string is eight characters long.  Multiple
    threads can safely use the same instance at the same time.

    _RandomNameSequence is an iterator."""

    characters = "abcdefghijklmnopqrstuvwxyz0123456789_"

    @property
    def rng(self) -> Random:
        cur_pid = os.getpid()
        if cur_pid != getattr(self, "_rng_pid", None):
            self._rng = Random()
            self._rng_pid = cur_pid
        return self._rng

    def __iter__(self) -> "_RandomNameSequence":
        return self

    def __next__(self) -> str:
        c = self.characters
        choose = self.rng.choice
        letters = [choose(c) for dummy in range(6)]
        return "".join(letters)
