#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any, Literal, NamedTuple, TypedDict

from cmk.agent_based.v2 import Result, State, StringTable


class OraErrors:
    """
    >>> for line in ([""], ["", "FAILURE","ORA-", "foo"], ["", "FAILURE","ORA-"], ["", "FAILURE"],
    ... ["", "select"], ["", "ORA-bar"], ["ORA-bar", "some", "data"], ["Error", "Message:", "Hello"]):
    ...     [OraErrors(line).ignore,OraErrors(line).has_error,
    ...     OraErrors(line).error_text,OraErrors(line).error_severity]
    [False, False, '', <State.OK: 0>]
    [False, True, 'ORA- foo', <State.UNKNOWN: 3>]
    [False, True, 'ORA-', <State.UNKNOWN: 3>]
    [True, False, '', <State.OK: 0>]
    [True, False, '', <State.OK: 0>]
    [False, True, 'Found error in agent output "ORA-bar"', <State.UNKNOWN: 3>]
    [False, True, 'Found error in agent output "ORA-bar some data"', <State.UNKNOWN: 3>]
    [False, True, 'Found error in agent output "Message: Hello"', <State.UNKNOWN: 3>]
    """

    def __init__(self, line: list[str]) -> None:
        # Default values
        self.ignore = False
        self.has_error = False
        self.error_text = ""
        self.error_severity = State.OK

        # Update according to line content
        self.handle_errors(line)

    # This function must be executed for each agent line which has been
    # found for the current item. It must deal with the ORA-* error
    # messages. It has to skip over the lines which show the SQL statement
    # and the SQL error message which comes before the ORA-* message.
    def handle_errors(self, line: Sequence[str]) -> None:
        if len(line) == 1:
            return

        if line[0].startswith("ORA-"):
            self.has_error = True
            self.error_text = _error_summary_text(" ".join(line))
            self.error_severity = State.UNKNOWN
            return

        # Handle error output from new agent
        if line[1] == "FAILURE":
            if len(line) >= 3 and line[2].startswith("ORA-"):
                self.has_error = True
                self.error_text = "%s" % " ".join(line[2:])
                self.error_severity = State.UNKNOWN
                return
            self.ignore = True
            return  # ignore other FAILURE lines

        # Handle error output from old (pre 1.2.0p2) agent
        if line[1] in ["select", "*", "ERROR"]:
            self.ignore = True
            return
        if line[1].startswith("ORA-"):
            self.has_error = True
            self.error_text = _error_summary_text(" ".join(line[1:]))
            self.error_severity = State.UNKNOWN
            return

        # Handle error output from 1.6 solaris agent, see SUP-9521
        if line[0] == "Error":
            self.has_error = True
            self.error_text = _error_summary_text(" ".join(line[1:]))
            self.error_severity = State.UNKNOWN
            return


def _error_summary_text(agent_output_string: str) -> str:
    return f'Found error in agent output "{agent_output_string}"'


class DataFiles(TypedDict):
    autoextensible: bool
    file_online_status: str
    name: str
    status: str
    ts_status: str
    ts_type: str
    block_size: int | None
    size: int | None
    max_size: int | None
    used_size: int | None
    free_space: int | None
    increment_size: int | None


class TableSpaces(TypedDict):
    amount_missing_filenames: int
    autoextensible: bool
    datafiles: list[DataFiles]
    db_version: int
    status: str
    type: str


ErrorSids = dict[str, OraErrors]


class SectionTableSpaces(TypedDict):
    error_sids: ErrorSids
    tablespaces: dict[tuple[str, str], TableSpaces]


InstancePerformance = Mapping[str, Mapping[str, Any]]
SectionPerformance = Mapping[str, InstancePerformance]


class Datafile(NamedTuple):
    name: str


class UnavailableDatafiles(NamedTuple):
    offline: Sequence[Datafile]
    recover: Sequence[Datafile]


def check_unavailable_datafiles(
    datafiles: list[DataFiles],
) -> UnavailableDatafiles:
    offline = []
    recover = []
    for datafile in datafiles:
        online_status = datafile["file_online_status"]
        if online_status == "OFFLINE":
            offline.append(Datafile(datafile["name"]))
        if online_status == "RECOVER":
            recover.append(Datafile(datafile["name"]))

    return UnavailableDatafiles(
        offline=offline,
        recover=recover,
    )


class OnlineStatsResult(NamedTuple):
    current_size: int
    used_size: int
    max_size: int
    free_space: int
    num_increments: int
    increment_size: int
    uses_default_increment: int
    num_extensible: int
    num_files: int
    num_avail: int


def datafiles_online_stats(
    datafiles: list[DataFiles],
    db_version: int,
) -> OnlineStatsResult | None:
    """
    calculate summary statistics over multiple datafiles. Only certain
    datafiles will be included. If there are none, None will be returned.
    """
    num_files = 0
    num_avail = 0
    num_extensible = 0
    current_size = 0
    max_size = 0
    used_size = 0
    num_increments = 0
    increment_size = 0
    uses_default_increment = False
    free_space = 0

    for datafile in datafiles:
        num_files += 1
        if (
            datafile["status"] not in ["AVAILABLE", "ONLINE", "READONLY"]
            or datafile["size"] is None
            or datafile["free_space"] is None
            or datafile["max_size"] is None
        ):
            continue

        df_size = datafile["size"]
        df_free_space = datafile["free_space"]
        df_max_size = datafile["max_size"]

        num_avail += 1
        current_size += df_size
        used_size += df_size - df_free_space

        # Autoextensible? Honor max size. Everything is computed in
        # *Bytes* here!
        if datafile["autoextensible"] and datafile["increment_size"] is not None:
            num_extensible += 1
            incsize = datafile["increment_size"]

            if df_size > df_max_size:
                max_size += df_size
                # current file size > df_max_size => no more extents available
                free_extension = 0
            else:
                max_size += df_max_size
                free_extension = df_max_size - df_size  # free extension space

            if incsize == datafile["block_size"]:
                uses_default_increment = True

            num_increments += free_extension // incsize
            increment_size += free_extension

            if db_version >= 11:
                # Newer versions of Oracle uses every time the remaining space of the
                # datafile. There is no need for calculation of remaing space with
                # next extend anymore!
                free_space += free_extension + df_free_space
            else:
                # The free space in this table is the current free space plus
                # the additional space that can be gathered by using all available
                # remaining increments
                free_space += increment_size + df_free_space

        # not autoextensible: take current size as maximum
        else:
            max_size += df_size
            free_space += df_free_space

    if num_avail == 0:
        return None

    return OnlineStatsResult(
        current_size,
        used_size,
        max_size,
        free_space,
        num_increments,
        increment_size,
        uses_default_increment,
        num_extensible,
        num_files,
        num_avail,
    )


# This function must be executed for each agent line which has been
# found for the current item. It must deal with the ORA-* error
# messages. It has to skip over the lines which show the SQL statement
# and the SQL error message which comes before the ORA-* message.
#
# The check must completely skip the lines before the ORA-* messages
# and return UNKNOWN on the first found ORA-* message.
# line[0] is the item (db instance)
#
# This function returns a tuple when an ORA-* message has been found.
# It returns False if this line should be skipped by the check.
def oracle_handle_ora_errors(line: Sequence[str]) -> Result | Literal[False] | None:
    if len(line) == 1:
        return None

    legacy_error = _oracle_handle_legacy_ora_errors(line)
    if legacy_error:
        return legacy_error

    # Handle error output from new agent
    if line[1] == "FAILURE":
        if len(line) >= 3 and line[2].startswith("ORA-"):
            return Result(state=State.UNKNOWN, summary="%s" % " ".join(line[2:]))
        return False  # ignore other FAILURE lines

    # Handle error output from old (pre 1.2.0p2) agent
    if line[1] in ["select", "*", "ERROR"]:
        return False
    if line[1].startswith("ORA-"):
        return Result(
            state=State.UNKNOWN, summary='Found error in agent output "%s"' % " ".join(line[1:])
        )
    return None


def _oracle_handle_legacy_ora_errors(line: Sequence[str]) -> Result | Literal[False] | None:
    # Skip over line before ORA- errors (e.g. sent by AIX agent from 2014)
    if line == ["ERROR:"]:
        return False

    if line[0].startswith("ORA-"):
        return Result(
            state=State.UNKNOWN, summary='Found error in agent output "%s"' % " ".join(line)
        )

    # Handle error output from 1.6 solaris agent, see SUP-9521
    if line[0] == "Error":
        return Result(
            state=State.UNKNOWN, summary='Found error in agent output "%s"' % " ".join(line[1:])
        )
    return None


# Fully prevent creation of services when an error is found.
def oracle_handle_ora_errors_discovery(info: StringTable) -> None:
    for line in info:
        err = oracle_handle_ora_errors(line)
        if err is False:
            continue
        if isinstance(err, tuple):
            raise RuntimeError(err[1])  # soooo ... we create a crash report?
