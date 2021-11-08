#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Callable, Dict, List, NamedTuple, Optional

from cmk.utils.regex import regex
from cmk.utils.type_defs import ServiceName

_ServiceFilter = Callable[[ServiceName], bool]

_MATCH_EVERYTHING = regex("(.*)")

_MATCH_NOTHING = regex("((?!x)x)")


class _ServiceFilterLists(NamedTuple):
    new_whitelist: Optional[List[str]]
    new_blacklist: Optional[List[str]]
    vanished_whitelist: Optional[List[str]]
    vanished_blacklist: Optional[List[str]]


class ServiceFilters(NamedTuple):
    new: _ServiceFilter
    vanished: _ServiceFilter

    @classmethod
    def accept_all(cls) -> "ServiceFilters":
        return cls(_accept_all_services, _accept_all_services)

    @classmethod
    def from_settings(cls, rediscovery_parameters: Dict[str, Any]) -> "ServiceFilters":
        service_filter_lists = _get_service_filter_lists(rediscovery_parameters)

        new_services_filter = _get_service_filter_func(
            service_filter_lists.new_whitelist,
            service_filter_lists.new_blacklist,
        )

        vanished_services_filter = _get_service_filter_func(
            service_filter_lists.vanished_whitelist,
            service_filter_lists.vanished_blacklist,
        )

        return cls(new_services_filter, vanished_services_filter)


def _get_service_filter_lists(rediscovery_parameters: Dict[str, Any]) -> _ServiceFilterLists:

    if "service_filters" not in rediscovery_parameters:
        # Be compatible to pre 1.7.0 versions; There were only two general pattern lists
        # which were used for new AND vanished services:
        # {
        #     "service_whitelist": [PATTERN],
        #     "service_blacklist": [PATTERN],
        # }
        service_whitelist = rediscovery_parameters.get("service_whitelist")
        service_blacklist = rediscovery_parameters.get("service_blacklist")
        return _ServiceFilterLists(
            service_whitelist,
            service_blacklist,
            service_whitelist,
            service_blacklist,
        )

    # New since 1.7.0: A white- and blacklist can be configured for both new and vanished
    # services as "combined" pattern lists.
    # Or two separate pattern lists for each new and vanished services are configurable:
    # {
    #     "service_filters": (
    #         "combined",
    #         {
    #             "service_whitelist": [PATTERN],
    #             "service_blacklist": [PATTERN],
    #         },
    #     )
    # } resp.
    # {
    #     "service_filters": (
    #         "dedicated",
    #         {
    #             "service_whitelist": [PATTERN],
    #             "service_blacklist": [PATTERN],
    #             "vanished_service_whitelist": [PATTERN],
    #             "vanished_service_blacklist": [PATTERN],
    #         },
    #     )
    # }
    service_filter_ty, service_filter_lists = rediscovery_parameters["service_filters"]

    if service_filter_ty == "combined":
        new_service_whitelist = service_filter_lists.get("service_whitelist")
        new_service_blacklist = service_filter_lists.get("service_blacklist")
        return _ServiceFilterLists(
            new_service_whitelist,
            new_service_blacklist,
            new_service_whitelist,
            new_service_blacklist,
        )

    if service_filter_ty == "dedicated":
        return _ServiceFilterLists(
            service_filter_lists.get("service_whitelist"),
            service_filter_lists.get("service_blacklist"),
            service_filter_lists.get("vanished_service_whitelist"),
            service_filter_lists.get("vanished_service_blacklist"),
        )

    raise NotImplementedError()


def _get_service_filter_func(
    service_whitelist: Optional[List[str]],
    service_blacklist: Optional[List[str]],
) -> _ServiceFilter:
    if not service_whitelist and not service_blacklist:
        return _accept_all_services

    whitelist = (
        regex("|".join(f"({p})" for p in service_whitelist))  #
        if service_whitelist
        else _MATCH_EVERYTHING
    )

    blacklist = (
        regex("|".join(f"({p})" for p in service_blacklist))  #
        if service_blacklist
        else _MATCH_NOTHING
    )

    def _filter_service_by_patterns(service_name: ServiceName) -> bool:
        return whitelist.match(service_name) is not None and blacklist.match(service_name) is None

    return _filter_service_by_patterns


def _accept_all_services(_service_name: ServiceName) -> bool:
    return True
