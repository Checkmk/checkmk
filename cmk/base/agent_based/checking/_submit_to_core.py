#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import errno
import os
import time
from functools import partial
from random import Random
from typing import Callable, IO, Literal, Optional, Tuple, Union

import cmk.utils.paths
import cmk.utils.tty as tty
from cmk.utils.check_utils import ServiceCheckResult
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.log import console
from cmk.utils.timeout import Timeout
from cmk.utils.type_defs import HostName, KeepaliveAPI, ServiceDetails, ServiceName, ServiceState

Submitter = Callable[
    [
        HostName,
        ServiceName,
        ServiceState,
        ServiceDetails,
        Optional[Tuple[int, int]],
    ],
    None,
]


def _sanitize_perftext(
    result: ServiceCheckResult, perfdata_format: Literal["pnp", "standard"]
) -> str:
    if not result.metrics:
        return ""

    perftexts = [_serialize_metric(*mt) for mt in result.metrics]

    if perfdata_format == "pnp" and (check_command := _extract_check_command(result.output)):
        perftexts.append("[%s]" % check_command)

    return " ".join(perftexts)


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


def check_result(
    *,
    host_name: HostName,
    service_name: ServiceName,
    result: ServiceCheckResult,
    cache_info: Optional[Tuple[int, int]],
    show_perfdata: bool,
    perfdata_format: Literal["pnp", "standard"],
    submitter: Submitter,
) -> None:
    output = "%s|%s" % (
        # The vertical bar indicates end of service output and start of metrics.
        # Replace the ones in the output by a Uniocode "Light vertical bar"
        result.output.replace("|", "\u2758"),
        _sanitize_perftext(result, perfdata_format),
    )

    _output_check_result(service_name, result.state, output, show_perfdata=show_perfdata)

    submitter(
        host_name,
        service_name,
        result.state,
        output,
        cache_info,
    )


def get_submitter(
    check_submission: str,
    monitoring_core: str,
    dry_run: bool,
    keepalive: KeepaliveAPI,
) -> Submitter:
    if dry_run:
        return _submit_noop

    if keepalive.enabled():
        return partial(_submit_via_keepalive, keepalive)

    if check_submission == "pipe" or monitoring_core == "cmc":
        return _submit_via_command_pipe

    if check_submission == "file":
        return _submit_via_check_result_file

    raise MKGeneralException(f"Invalid setting {check_submission=} (expected 'pipe' or 'file')")


def _submit_noop(
    host: HostName,
    service: ServiceName,
    state: ServiceState,
    output: ServiceDetails,
    cache_info: Optional[tuple[int, int]],
) -> None:
    pass


def _submit_via_keepalive(
    keepalive: KeepaliveAPI,
    host: HostName,
    service: ServiceName,
    state: ServiceState,
    output: ServiceDetails,
    cache_info: Optional[tuple[int, int]],
) -> None:
    """Regular case for the CMC - check helpers are running in keepalive mode"""
    return keepalive.add_check_result(host, service, state, output, cache_info)


# Filedescriptor to open nagios command pipe.
_nagios_command_pipe: Union[Literal[False], IO[bytes], None] = None


def _open_command_pipe() -> None:
    global _nagios_command_pipe
    if _nagios_command_pipe is not None:
        return

    if not os.path.exists(cmk.utils.paths.nagios_command_pipe_path):
        _nagios_command_pipe = False  # False means: tried but failed to open
        raise MKGeneralException(
            "Missing core command pipe '%s'" % cmk.utils.paths.nagios_command_pipe_path
        )

    try:
        with Timeout(3, message="Timeout after 3 seconds"):
            _nagios_command_pipe = open(  # pylint:disable=consider-using-with
                cmk.utils.paths.nagios_command_pipe_path, "wb"
            )
    except Exception as exc:
        _nagios_command_pipe = False
        raise MKGeneralException(f"Error opening command pipe: {exc!r}") from exc


def _submit_via_command_pipe(
    host: HostName,
    service: ServiceName,
    state: ServiceState,
    output: ServiceDetails,
    cache_info: Optional[tuple[int, int]],
) -> None:
    """In case of CMC this is used when running "cmk" manually"""
    output = output.replace("\n", "\\n")
    _open_command_pipe()
    if not _nagios_command_pipe:
        return

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


# global variables used to cache temporary values that do not need
# to be reset after a configuration change.
_checkresult_file_fd = None
_checkresult_file_path = None


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


# TODO: existence of this means the submit-functions ought to be ctxt-mngr.
def finalize() -> None:
    global _checkresult_file_fd
    if _checkresult_file_fd is None or _checkresult_file_path is None:
        return

    os.close(_checkresult_file_fd)
    _checkresult_file_fd = None

    with open(_checkresult_file_path + ".ok", "w"):
        pass


def _submit_via_check_result_file(
    host: HostName,
    service: ServiceName,
    state: ServiceState,
    output: ServiceDetails,
    cache_info: Optional[tuple[int, int]],
) -> None:
    output = output.replace("\n", "\\n")
    _open_checkresult_file()
    if not _checkresult_file_fd:
        return

    now = time.time()
    os.write(
        _checkresult_file_fd,
        (
            f"host_name={host}\n"
            f"service_description={service}\n"
            "check_type=1\n"
            "check_options=0\n"
            "reschedule_check\n"
            "latency=0.0\n"
            f"start_time={now:.1f}\n"
            f"finish_time={now:.1f}\n"
            f"return_code={state}\n"
            f"output={output}\n"
            "\n"
        ).encode(),
    )


def _output_check_result(
    servicedesc: ServiceName,
    state: ServiceState,
    infotext: ServiceDetails,
    *,
    show_perfdata: bool,
) -> None:
    console.verbose(
        "%-20s %s%s%s%s%s\n",
        servicedesc,
        tty.bold,
        tty.states[state],
        infotext.split("|", 1)[0].split("\n", 1)[0],
        tty.normal,
        f" ({infotext.split('|', 1)[1]})" if show_perfdata else "",
    )
