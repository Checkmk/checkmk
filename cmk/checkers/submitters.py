#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import abc
import os
import time
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from random import Random
from typing import Final, IO, Literal, NamedTuple

import cmk.utils.paths
import cmk.utils.tty as tty
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.log import console
from cmk.utils.timeout import Timeout
from cmk.utils.type_defs import HostName, ServiceDetails, ServiceName, ServiceState

from cmk.checkers.checkresults import ServiceCheckResult

_CacheInfo = tuple[int, int]


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
    warn: float | None,
    crit: float | None,
    min_: float | None,
    max_: float | None,
) -> str:
    """
    >>> _serialize_metric("hot_chocolate", 2.3, None, 42.0, 0.0, None)
    'hot_chocolate=2.3;;42;0;'

    """
    return (
        f"{name}={_serialize_value(value)};{_serialize_value(warn)};{_serialize_value(crit)};"
        f"{_serialize_value(min_)};{_serialize_value(max_)}"
    )


def _serialize_value(x: float | None) -> str:
    return "" if x is None else ("%.6f" % x).rstrip("0").rstrip(".")


def _extract_check_command(infotext: str) -> str | None:
    """
    Check may append the name of the check command to the
    details of service output.
    It might be needed by the graphing tool in order to choose the correct
    template or apply the correct metric name translations.
    Currently this is used only by mrpe.
    """
    marker = "Check command used in metric system: "
    return infotext.split(marker, 1)[1].split("\n")[0] if marker in infotext else None


def get_submitter(
    check_submission: Literal["pipe", "file"],
    monitoring_core: Literal["nagios", "cmc"],
    host_name: HostName,
    *,
    dry_run: bool,
    perfdata_format: Literal["pnp", "standard"],
    show_perfdata: bool,
) -> Submitter:
    """Enterprise should use `cmk.base.cee.keepalive.submitters`."""
    if dry_run:
        return NoOpSubmitter(
            host_name,
            dry_run=dry_run,
            perfdata_format=perfdata_format,
            show_perfdata=show_perfdata,
        )

    if check_submission == "pipe" or monitoring_core == "cmc":
        return PipeSubmitter(
            host_name,
            dry_run=dry_run,
            perfdata_format=perfdata_format,
            show_perfdata=show_perfdata,
        )

    if check_submission == "file":
        return FileSubmitter(
            host_name,
            dry_run=dry_run,
            perfdata_format=perfdata_format,
            show_perfdata=show_perfdata,
        )

    raise MKGeneralException(f"Invalid setting {check_submission=} (expected 'pipe' or 'file')")


class Submittee(NamedTuple):
    name: ServiceName
    result: ServiceCheckResult
    cache_info: _CacheInfo | None
    pending: bool


class FormattedSubmittee(NamedTuple):
    name: ServiceName
    state: ServiceState
    details: ServiceDetails
    cache_info: _CacheInfo | None


class Submitter(abc.ABC):
    def __init__(
        self,
        host_name: HostName,
        *,
        dry_run: bool,
        perfdata_format: Literal["pnp", "standard"],
        show_perfdata: bool,
    ):
        self.host_name: Final = host_name
        self.dry_run: Final = dry_run
        self.perfdata_format: Final = perfdata_format
        self.show_perfdata: Final = show_perfdata

    def submit(self, submittees: Iterable[Submittee]) -> None:
        formatted_submittees = [
            (
                FormattedSubmittee(
                    name=s.name,
                    state=s.result.state,
                    details="%s|%s"
                    % (
                        # The vertical bar indicates end of service output and start of metrics.
                        # Replace the ones in the output by a Uniocode "Light vertical bar"
                        s.result.output.replace("|", "\u2758"),
                        _sanitize_perftext(s.result, self.perfdata_format),
                    ),
                    cache_info=s.cache_info,
                ),
                s.pending,
            )
            for s in submittees
        ]

        for submittee, pending in formatted_submittees:
            _output_check_result(submittee, show_perfdata=self.show_perfdata, pending=pending)

        self._submit((submittee for submittee, pending in formatted_submittees if not pending))

    @abc.abstractmethod
    def _submit(self, formatted_submittees: Iterable[FormattedSubmittee]) -> None:
        ...


class NoOpSubmitter(Submitter):
    def _submit(self, formatted_submittees: Iterable[FormattedSubmittee]) -> None:
        pass


class PipeSubmitter(Submitter):

    # Filedescriptor to open nagios command pipe.
    _nagios_command_pipe: Literal[False] | IO[bytes] | None = None

    @classmethod
    def _open_command_pipe(cls) -> Literal[False] | IO[bytes]:
        if cls._nagios_command_pipe is not None:
            return cls._nagios_command_pipe

        if not os.path.exists(cmk.utils.paths.nagios_command_pipe_path):
            cls._nagios_command_pipe = False  # False means: tried but failed to open
            raise MKGeneralException(
                "Missing core command pipe '%s'" % cmk.utils.paths.nagios_command_pipe_path
            )

        try:
            with Timeout(3, message="Timeout after 3 seconds"):
                cls._nagios_command_pipe = open(  # pylint:disable=consider-using-with
                    cmk.utils.paths.nagios_command_pipe_path, "wb"
                )
        except Exception as exc:
            cls._nagios_command_pipe = False
            raise MKGeneralException(f"Error opening command pipe: {exc!r}") from exc

        return cls._nagios_command_pipe

    def _submit(self, formatted_submittees: Iterable[FormattedSubmittee]) -> None:
        if not (pipe := PipeSubmitter._open_command_pipe()):
            return

        for service, state, output, _cache_info in formatted_submittees:

            msg = "[%d] PROCESS_SERVICE_CHECK_RESULT;%s;%s;%d;%s\n" % (
                time.time(),
                self.host_name,
                service,
                state,
                output.replace("\n", "\\n"),
            )
            pipe.write(msg.encode())
            # Important: Nagios needs the complete command in one single write() block!
            # Python buffers and sends chunks of 4096 bytes, if we do not flush.
            pipe.flush()


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

    def __iter__(self) -> _RandomNameSequence:
        return self

    def __next__(self) -> str:
        c = self.characters
        choose = self.rng.choice
        letters = [choose(c) for dummy in range(6)]
        return "".join(letters)


class FileSubmitter(Submitter):

    _names = _RandomNameSequence()

    def _submit(self, formatted_submittees: Iterable[FormattedSubmittee]) -> None:

        now = time.time()

        with self._open_checkresult_file() as fd:
            for service, state, output, _cache_info in formatted_submittees:
                output = output.replace("\n", "\\n")
                os.write(
                    fd,
                    (
                        f"host_name={self.host_name}\n"
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

    @classmethod
    @contextmanager
    def _open_checkresult_file(cls) -> Iterator[int]:
        """Create some temporary file for storing the checkresults.
        Nagios expects a seven character long file starting with "c". Since Python3 we can not
        use tempfile.mkstemp anymore since it produces file names with 9 characters length.

        Logic is similar to tempfile.mkstemp, but simplified. No prefix/suffix/thread-safety
        """
        base_dir = cmk.utils.paths.check_result_path

        flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW

        for name, _seq in zip(cls._names, range(os.TMP_MAX)):
            filepath = os.path.join(base_dir, "c" + name)
            try:
                checkresult_file_fd = os.open(filepath, flags, 0o600)
            except FileExistsError:
                continue  # try again
            except Exception as e:
                raise MKGeneralException(f"Cannot create check result file in {base_dir}: {e!r}")

            yield checkresult_file_fd

            os.close(checkresult_file_fd)
            with open(filepath + ".ok", "w"):
                pass

            return

        raise MKGeneralException(
            f"Cannot create check result file in {base_dir}: No usable temporary file name found"
        )


def _output_check_result(
    submittee: FormattedSubmittee,
    *,
    show_perfdata: bool,
    pending: bool,
) -> None:
    weight, state_txt = ("", "PEND ") if pending else (tty.bold, tty.states[submittee.state])
    console.verbose(
        "%-20s %s%s%s%s%s\n",
        submittee.name,
        weight,
        state_txt,
        submittee.details.split("|", 1)[0].split("\n", 1)[0],
        tty.normal,
        f" ({submittee.details.split('|', 1)[1]})" if show_perfdata else "",
    )
