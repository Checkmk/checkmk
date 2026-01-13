#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Sequence
from typing import Literal, NamedTuple

from typing_extensions import TypedDict

from cmk.utils.regex import combine_patterns, regex
from cmk.utils.servicename import ServiceName

from ._utils import DiscoveryVsSettings

ServiceFilter = Callable[[ServiceName], bool]

_MATCH_EVERYTHING = regex("(.*)")

_MATCH_NOTHING = regex("((?!x)x)")


class ServiceFiltersDedicated(TypedDict, total=False):
    service_whitelist: Sequence[str]  # combined + dedicated
    service_blacklist: Sequence[str]  # combined + dedicated
    vanished_service_whitelist: Sequence[str]  # dedicated only
    vanished_service_blacklist: Sequence[str]  # dedicated only
    changed_service_labels_whitelist: Sequence[str]
    changed_service_labels_blacklist: Sequence[str]
    changed_service_params_whitelist: Sequence[str]
    changed_service_params_blacklist: Sequence[str]


class RediscoveryParameters(TypedDict, total=False):
    activation: bool  # not sure about the type
    excluded_time: Sequence[tuple[tuple[int, int], tuple[int, int]]]
    keep_clustered_vanished_services: bool
    group_time: int
    mode: DiscoveryVsSettings
    service_whitelist: Sequence[str]
    service_blacklist: Sequence[str]
    service_filters: tuple[Literal["combined", "dedicated"], ServiceFiltersDedicated]


class _ServiceFilterLists(NamedTuple):
    new_whitelist: Sequence[str] | None
    new_blacklist: Sequence[str] | None
    vanished_whitelist: Sequence[str] | None
    vanished_blacklist: Sequence[str] | None
    changed_labels_whitelist: Sequence[str] | None
    changed_labels_blacklist: Sequence[str] | None
    changed_params_whitelist: Sequence[str] | None
    changed_params_blacklist: Sequence[str] | None


class ServiceFilters(NamedTuple):
    new: ServiceFilter
    vanished: ServiceFilter
    changed_labels: ServiceFilter
    changed_params: ServiceFilter

    @classmethod
    def accept_all(cls) -> "ServiceFilters":
        return cls(
            _accept_all_services,
            _accept_all_services,
            _accept_all_services,
            _accept_all_services,
        )

    @classmethod
    def from_settings(cls, rediscovery_parameters: RediscoveryParameters) -> "ServiceFilters":
        service_filter_lists = _get_service_filter_lists(rediscovery_parameters)

        new_services_filter = _get_service_filter_func(
            service_filter_lists.new_whitelist,
            service_filter_lists.new_blacklist,
        )

        vanished_services_filter = _get_service_filter_func(
            service_filter_lists.vanished_whitelist,
            service_filter_lists.vanished_blacklist,
        )

        changed_service_labels_filter = _get_service_filter_func(
            service_filter_lists.changed_labels_whitelist,
            service_filter_lists.changed_labels_blacklist,
        )

        changed_services_params_filter = _get_service_filter_func(
            service_filter_lists.changed_params_whitelist,
            service_filter_lists.changed_params_blacklist,
        )

        return cls(
            new_services_filter,
            vanished_services_filter,
            changed_service_labels_filter,
            changed_services_params_filter,
        )


def _get_service_filter_lists(
    rediscovery_parameters: RediscoveryParameters,
) -> _ServiceFilterLists:
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
            service_filter_lists.get("changed_service_labels_whitelist"),
            service_filter_lists.get("changed_service_labels_blacklist"),
            service_filter_lists.get("changed_service_params_whitelist"),
            service_filter_lists.get("changed_service_params_blacklist"),
        )

    raise NotImplementedError()


def _get_service_filter_func(
    service_whitelist: Sequence[str] | None,
    service_blacklist: Sequence[str] | None,
) -> ServiceFilter:
    if not service_whitelist and not service_blacklist:
        return _accept_all_services

    whitelist = (
        regex(combine_patterns(service_whitelist)) if service_whitelist else _MATCH_EVERYTHING
    )

    blacklist = regex(combine_patterns(service_blacklist)) if service_blacklist else _MATCH_NOTHING

    def _filter_service_by_patterns(service_name: ServiceName) -> bool:
        return whitelist.match(service_name) is not None and blacklist.match(service_name) is None

    return _filter_service_by_patterns


def _accept_all_services(_service_name: ServiceName) -> bool:
    return True
