#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Sequence
from typing import Literal, TypedDict

from cmk.ccc.hostaddress import HostName
from cmk.utils.regex import regex


class InvCleanupParamsCombined(TypedDict):
    strategy: Literal["and", "or"]
    file_age: int
    number_of_history_entries: int


type InvCleanupParamsChoice = (
    tuple[Literal["file_age"], int]
    | tuple[Literal["number_of_history_entries"], int]
    | tuple[Literal["combined"], InvCleanupParamsCombined]
)


class InvCleanupParamsOfHosts(TypedDict):
    regex_or_explicit: Sequence[str]
    parameters: InvCleanupParamsChoice


class InvCleanupParamsDefaultCombined(TypedDict):
    strategy: Literal["and"]
    file_age: int
    number_of_history_entries: int


class InvCleanupParams(TypedDict):
    for_hosts: Sequence[InvCleanupParamsOfHosts]
    default: InvCleanupParamsDefaultCombined | None
    abandoned_file_age: int


def matches(*, regex_or_name: str, host_name: HostName) -> bool:
    if regex_or_name.startswith("~"):
        if regex(regex_or_name[1:]).match(host_name):
            return True
    elif host_name == regex_or_name:
        return True
    return False


def _filter_regex_or_explicit(
    *, regex_or_explicit: Sequence[str], host_names: Sequence[HostName]
) -> Iterator[str]:
    for regex_or_name in regex_or_explicit:
        for host_name in host_names:
            if matches(regex_or_name=regex_or_name, host_name=host_name):
                yield regex_or_name


def filter_inventory_cleanup_parameters(
    *,
    cleanup_parameters: InvCleanupParams,
    host_names: Sequence[HostName],
) -> InvCleanupParams:
    return InvCleanupParams(
        for_hosts=[
            InvCleanupParamsOfHosts(
                regex_or_explicit=regex_or_explicit,
                parameters=p["parameters"],
            )
            for p in cleanup_parameters["for_hosts"]
            if (
                regex_or_explicit := list(
                    _filter_regex_or_explicit(
                        regex_or_explicit=p["regex_or_explicit"],
                        host_names=host_names,
                    )
                )
            )
        ],
        default=cleanup_parameters["default"],
        abandoned_file_age=cleanup_parameters["abandoned_file_age"],
    )
