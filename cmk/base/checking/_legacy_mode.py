#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Performing the actual checks."""

from typing import (
    Any,
    AnyStr,
    cast,
    Iterable,
    List,
    Optional,
    Tuple,
    Union,
)

import cmk.utils.debug
from cmk.utils.exceptions import MKGeneralException, MKTimeout
from cmk.utils.type_defs import (
    HostAddress,
    HostName,
    MetricTuple,
    SectionName,
    ServiceCheckResult,
    ServiceDetails,
    ServiceState,
    SourceType,
    state_markers,
)

import cmk.base.check_table as check_table
import cmk.base.config as config
import cmk.base.core
import cmk.base.crash_reporting
import cmk.base.decorator
import cmk.base.ip_lookup as ip_lookup
import cmk.base.item_state as item_state
import cmk.base.utils

from cmk.base.check_api_utils import MGMT_ONLY as LEGACY_MGMT_ONLY
from cmk.base.check_utils import LegacyCheckParameters, Service
from cmk.base.sources.host_sections import HostKey, MultiHostSections

from .utils import (
    AggregatedResult,
    CHECK_NOT_IMPLEMENTED,
    ITEM_NOT_FOUND,
    RECEIVED_NO_DATA,
)

ServiceCheckResultWithOptionalDetails = Tuple[ServiceState, ServiceDetails, List[MetricTuple]]


def get_aggregated_result(
    multi_host_sections: MultiHostSections,
    hostname: HostName,
    ipaddress: Optional[HostAddress],
    service: Service,
    *,
    used_params: LegacyCheckParameters,
) -> AggregatedResult:
    legacy_check_plugin_name = config.legacy_check_plugin_names.get(service.check_plugin_name)
    if legacy_check_plugin_name is None:
        return AggregatedResult(
            submit=True,
            data_received=True,
            result=CHECK_NOT_IMPLEMENTED,
            cache_info=None,
        )

    check_function = config.check_info[legacy_check_plugin_name].get("check_function")
    if check_function is None:
        return AggregatedResult(
            submit=True,
            data_received=True,
            result=CHECK_NOT_IMPLEMENTED,
            cache_info=None,
        )

    section_name = legacy_check_plugin_name.split('.')[0]

    section_content = None
    mgmt_board_info = config.get_management_board_precedence(section_name, config.check_info)
    source_type = SourceType.MANAGEMENT if mgmt_board_info == LEGACY_MGMT_ONLY else SourceType.HOST
    try:
        section_content = multi_host_sections.get_section_content(
            HostKey(hostname, ipaddress, source_type),
            mgmt_board_info,
            section_name,
            for_discovery=False,
            cluster_node_keys=config.get_config_cache().get_clustered_service_node_keys(
                hostname,
                source_type,
                service.description,
                ip_lookup.lookup_ip_address,
            ),
            check_legacy_info=config.check_info,
        )

        if section_content is None:  # No data for this check type
            return AggregatedResult(
                submit=False,
                data_received=False,
                result=RECEIVED_NO_DATA,
                cache_info=None,
            )

        # Call the actual check function
        item_state.reset_wrapped_counters()

        raw_result = check_function(service.item, used_params, section_content)
        result = _sanitize_check_result(raw_result)
        item_state.raise_counter_wrap()

    except item_state.MKCounterWrapped as exc:
        # handle check implementations that do not yet support the
        # handling of wrapped counters via exception on their own.
        # Do not submit any check result in that case:
        return AggregatedResult(
            submit=False,
            data_received=True,
            result=(0, f"Cannot compute check result: {exc}\n", []),
            cache_info=None,
        )

    except MKTimeout:
        raise

    except Exception:
        if cmk.utils.debug.enabled():
            raise
        result = 3, cmk.base.crash_reporting.create_check_crash_dump(
            host_name=hostname,
            service_name=service.description,
            plugin_name=service.check_plugin_name,
            plugin_kwargs={
                "item": service.item,
                "params": used_params,
                "section_content": section_content
            },
            is_manual=service.id() in check_table.get_check_table(hostname, skip_autochecks=True),
        ), []

    return AggregatedResult(
        submit=True,
        data_received=True,
        result=result,
        cache_info=multi_host_sections.legacy_determine_cache_info(SectionName(section_name)),
    )


def _sanitize_check_result(
        result: Union[None, ServiceCheckResult, Tuple, Iterable]) -> ServiceCheckResult:
    if isinstance(result, tuple):
        return cast(ServiceCheckResult, _sanitize_tuple_check_result(result))

    if result is None:
        return ITEM_NOT_FOUND

    return _sanitize_yield_check_result(result)


# The check function may return an iterator (using yield) since 1.2.5i5.
# This function handles this case and converts them to tuple results
def _sanitize_yield_check_result(result: Iterable[Any]) -> ServiceCheckResult:
    subresults = list(result)

    # Empty list? Check returned nothing
    if not subresults:
        return ITEM_NOT_FOUND

    # Several sub results issued with multiple yields. Make that worst sub check
    # decide the total state, join the texts and performance data. Subresults with
    # an infotext of None are used for adding performance data.
    perfdata: List[MetricTuple] = []
    infotexts: List[ServiceDetails] = []
    status: ServiceState = 0

    for subresult in subresults:
        st, text, perf = _sanitize_tuple_check_result(subresult, allow_missing_infotext=True)
        status = cmk.base.utils.worst_service_state(st, status)

        if text:
            infotexts.append(text + state_markers[st])

        if perf is not None:
            perfdata += perf

    return status, ", ".join(infotexts), perfdata


# TODO: Cleanup return value: Factor "infotext: Optional[str]" case out and then make Tuple values
# more specific
def _sanitize_tuple_check_result(
        result: Tuple,
        allow_missing_infotext: bool = False) -> ServiceCheckResultWithOptionalDetails:
    if len(result) >= 3:
        state, infotext, perfdata = result[:3]
        _validate_perf_data_values(perfdata)
    else:
        state, infotext = result
        perfdata = []

    infotext = _sanitize_check_result_infotext(infotext, allow_missing_infotext)

    # NOTE: the typing is just wishful thinking. However, this part of the
    # code is only used for the legacy cluster case, so we do not introduce
    # new validation here.
    return state, infotext, perfdata


def _validate_perf_data_values(perfdata: Any) -> None:
    if not isinstance(perfdata, list):
        return
    for v in [value for entry in perfdata for value in entry[1:]]:
        if " " in str(v):
            # See Nagios performance data spec for detailed information
            raise MKGeneralException("Performance data values must not contain spaces")


def _sanitize_check_result_infotext(infotext: Optional[AnyStr],
                                    allow_missing_infotext: bool) -> Optional[ServiceDetails]:
    if infotext is None and not allow_missing_infotext:
        raise MKGeneralException("Invalid infotext from check: \"None\"")

    if isinstance(infotext, bytes):
        return infotext.decode('utf-8')

    return infotext
