#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict, List, Mapping, Optional, Tuple, TypedDict

from ..agent_based_api.v1 import State


class DatafilesException(RuntimeError):
    pass


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

    def __init__(self, line: List[str]):
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
    def handle_errors(self, line):
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


DataFiles = TypedDict(
    "DataFiles",
    {
        "autoextensible": bool,
        "file_online_status": str,
        "name": str,
        "status": str,
        "ts_status": str,
        "ts_type": str,
        "block_size": Optional[int],
        "size": Optional[int],
        "max_size": Optional[int],
        "used_size": Optional[int],
        "free_space": Optional[int],
        "increment_size": Optional[int],
    },
)

TableSpaces = TypedDict(
    "TableSpaces",
    {
        "amount_missing_filenames": int,
        "autoextensible": bool,
        "datafiles": List[DataFiles],
        "db_version": int,
        "status": str,
        "type": str,
    },
)

ErrorSids = Dict[str, OraErrors]
SectionTableSpaces = TypedDict(
    "SectionTableSpaces",
    {
        "error_sids": ErrorSids,
        "tablespaces": Dict[Tuple[str, str], TableSpaces],
    },
)


def analyze_datafiles(
    datafiles: List[DataFiles],
    db_version: int,
    sid: str,
    params: Optional[Mapping[str, Any]] = None,
    raise_on_offline_files: bool = False,
) -> Tuple[int, int, int, int, int, int, bool, int, int, int, Dict[str, Dict[str, Any]]]:
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
    file_online_states: Dict[str, Dict[str, Any]] = {}

    for datafile in datafiles:

        df_file_online_status = datafile["file_online_status"]
        if df_file_online_status in ["OFFLINE", "RECOVER"] and params:

            file_online_states_params = dict(params.get("map_file_online_states", []))
            if (
                datafile["block_size"] is not None
                and file_online_states_params
                and df_file_online_status in file_online_states_params
            ):

                file_online_states.setdefault(
                    df_file_online_status,
                    {
                        "state": file_online_states_params[df_file_online_status],
                        "sids": [],
                    },
                )
                file_online_states[df_file_online_status]["sids"].append(sid)

            else:
                if raise_on_offline_files:
                    raise DatafilesException("One or more datafiles OFFLINE or RECOVER")

        num_files += 1
        if (
            datafile["status"] in ["AVAILABLE", "ONLINE", "READONLY"]
            and datafile["size"] is not None
            and datafile["free_space"] is not None
            and datafile["max_size"] is not None
        ):
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
    return (
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
        file_online_states,
    )
