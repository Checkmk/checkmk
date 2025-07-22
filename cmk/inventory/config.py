#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Sequence
from typing import NotRequired, TypedDict

import cmk.utils.paths
from cmk.ccc.hostaddress import HostName
from cmk.utils.regex import regex


class InvHousekeepingParamsOfHosts(TypedDict):
    regexes_or_names: Sequence[str]
    file_age: NotRequired[int]
    number_of_history_entries: NotRequired[int]


class InvHousekeepingParamsFallback(TypedDict):
    file_age: NotRequired[int]
    number_of_history_entries: int


class InvHousekeepingParams(TypedDict):
    of_hosts: Sequence[InvHousekeepingParamsOfHosts]
    fallback: InvHousekeepingParamsFallback


CONFIG_DIR_INV_HOUSEKEEPING_PARAMS = cmk.utils.paths.default_config_dir / "inventory.d/wato/"


def matches(*, regex_or_name: str, host_name: HostName) -> bool:
    if regex_or_name.startswith("~"):
        if regex(regex_or_name[1:]).match(host_name):
            return True
    elif host_name == regex_or_name:
        return True
    return False


def _filter_regexes_or_names(
    *, regexes_or_names: Sequence[str], host_names: Sequence[HostName]
) -> Iterator[str]:
    for regex_or_name in regexes_or_names:
        for host_name in host_names:
            if matches(regex_or_name=regex_or_name, host_name=host_name):
                yield regex_or_name


def _create_parameters_of_hosts(
    *,
    regexes_or_names: Sequence[str],
    file_age: int | None,
    number_of_history_entries: int | None,
) -> InvHousekeepingParamsOfHosts:
    new = InvHousekeepingParamsOfHosts(regexes_or_names=regexes_or_names)
    if file_age is not None:
        new["file_age"] = file_age
    if number_of_history_entries is not None:
        new["number_of_history_entries"] = number_of_history_entries
    return new


def filter_inventory_housekeeping_parameters(
    *,
    parameters: InvHousekeepingParams,
    host_names: Sequence[HostName],
) -> InvHousekeepingParams:
    return InvHousekeepingParams(
        of_hosts=[
            _create_parameters_of_hosts(
                regexes_or_names=regexes_or_names,
                file_age=p.get("file_age"),
                number_of_history_entries=p.get("number_of_history_entries"),
            )
            for p in parameters["of_hosts"]
            if (
                regexes_or_names := list(
                    _filter_regexes_or_names(
                        regexes_or_names=p["regexes_or_names"],
                        host_names=host_names,
                    )
                )
            )
        ],
        fallback=parameters["fallback"],
    )
