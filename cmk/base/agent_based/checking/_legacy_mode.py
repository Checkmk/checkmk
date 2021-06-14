#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Legacy version of running checks on clusters"""

import sys
from typing import (
    Any,
    AnyStr,
    cast,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    Union,
)

import cmk.utils.caching
import cmk.utils.debug
from cmk.utils.check_utils import section_name_of, worst_service_state
from cmk.utils.exceptions import MKGeneralException, MKTimeout, MKParseFunctionError
from cmk.utils.type_defs import (
    HostAddress,
    HostKey,
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
import cmk.base.item_state as item_state
import cmk.base.plugin_contexts as plugin_contexts

from cmk.base.api.agent_based import register as agent_based_register
from cmk.base.api.agent_based.value_store import ValueStoreManager
from cmk.base.agent_based.data_provider import ParsedSectionsBroker, ParsedSectionContent
from cmk.base.check_utils import (
    LegacyCheckParameters,
    Service,
    MGMT_ONLY as LEGACY_MGMT_ONLY,
    HOST_PRECEDENCE as LEGACY_HOST_PRECEDENCE,
)

from cmk.core_helpers.cache import ABCRawDataSection

from .utils import (
    AggregatedResult,
    CHECK_NOT_IMPLEMENTED,
    ITEM_NOT_FOUND,
    RECEIVED_NO_DATA,
)

ServiceCheckResultWithOptionalDetails = Tuple[ServiceState, ServiceDetails, List[MetricTuple]]


def get_aggregated_result(
    parsed_sections_broker: ParsedSectionsBroker,
    hostname: HostName,
    ipaddress: Optional[HostAddress],
    service: Service,
    *,
    used_params: LegacyCheckParameters,
    value_store_manager: ValueStoreManager,
) -> AggregatedResult:
    with plugin_contexts.current_service(service):
        # In the legacy mode from hell (tm) the item state features *probably*
        # need to be called from the parse functions. We consolidate the
        # preperation of the item state at this point, which is the largest
        # possible scope without leaving the 'legacy' world.
        with value_store_manager.namespace(service.id()):
            return _get_aggregated_result(
                parsed_sections_broker=parsed_sections_broker,
                hostname=hostname,
                ipaddress=ipaddress,
                service=service,
                used_params=used_params,
            )


def _get_aggregated_result(
    *,
    parsed_sections_broker: ParsedSectionsBroker,
    hostname: HostName,
    ipaddress: Optional[HostAddress],
    service: Service,
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
    main_check_info = config.check_info.get(section_name, {})

    section_content = None
    multi_host_sections = _MultiHostSections(parsed_sections_broker)
    mgmt_board_info = main_check_info.get("management_board") or LEGACY_HOST_PRECEDENCE
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
        status = worst_service_state(st, status, default=0)

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


class _MultiHostSections:
    """Container object for wrapping the host sections of a host being processed
    or multiple hosts when a cluster is processed. Also holds the functionality for
    merging these information together for a check"""
    def __init__(self, parsed_sections_broker: ParsedSectionsBroker) -> None:
        super().__init__()
        self._parsed_sections_broker = parsed_sections_broker
        self._section_content_cache = cmk.utils.caching.DictCache()

    def get_section_content(
        self,
        host_key: HostKey,
        management_board_info: str,
        check_plugin_name: str,
        for_discovery: bool,
        *,
        cluster_node_keys: Optional[List[HostKey]] = None,
        check_legacy_info: Dict[str, Dict[str, Any]],
    ) -> Union[None, ParsedSectionContent, List[ParsedSectionContent]]:
        """Prepares the section_content construct for a Check_MK check on ANY host

        The section_content construct is then handed over to the check, inventory or
        discovery functions for doing their work.

        If the host is a cluster, the sections from all its nodes is merged together
        here. Optionally the node info is added to the nodes section content.

        It handles the whole data and cares about these aspects:

        a) Extract the section_content for the given check_plugin_name
        b) Adds node_info to the section_content (if check asks for this)
        c) Applies the parse function (if check has some)

        It can return an section_content construct or None when there is no section content
        for this check available.
        """

        section_name = section_name_of(check_plugin_name)
        cache_key = (host_key, management_board_info, section_name, for_discovery,
                     bool(cluster_node_keys))

        try:
            return self._section_content_cache[cache_key]
        except KeyError:
            pass

        section_content = self._get_section_content(
            host_key._replace(source_type=SourceType.MANAGEMENT if management_board_info ==
                              LEGACY_MGMT_ONLY else SourceType.HOST),
            check_plugin_name,
            SectionName(section_name),
            for_discovery,
            cluster_node_keys=cluster_node_keys,
            check_legacy_info=check_legacy_info,
        )

        # If we found nothing, see if we must check the management board:
        if (section_content is None and host_key.source_type is SourceType.HOST and
                management_board_info == LEGACY_HOST_PRECEDENCE):
            section_content = self._get_section_content(
                host_key._replace(source_type=SourceType.MANAGEMENT),
                check_plugin_name,
                SectionName(section_name),
                for_discovery,
                cluster_node_keys=cluster_node_keys,
                check_legacy_info=check_legacy_info,
            )

        self._section_content_cache[cache_key] = section_content
        return section_content

    def _get_section_content(
        self,
        host_key: HostKey,
        check_plugin_name: str,
        section_name: SectionName,
        for_discovery: bool,
        *,
        cluster_node_keys: Optional[List[HostKey]] = None,
        check_legacy_info: Dict[str, Dict[str, Any]]
    ) -> Union[None, ParsedSectionContent, List[ParsedSectionContent]]:
        # Now get the section_content from the required hosts and merge them together to
        # a single section_content. For each host optionally add the node info.
        section_content: Optional[ABCRawDataSection] = None
        for node_key in cluster_node_keys or [host_key]:

            try:
                _resolver, parser = self._parsed_sections_broker[node_key]
                host_section_content = parser.raw_data.sections[section_name]
            except KeyError:
                continue

            if section_content is None:
                section_content = host_section_content[:]
            else:
                section_content += host_section_content

        if section_content is None:
            return None

        assert isinstance(section_content, list)

        return self._update_with_parse_function(
            section_content,
            section_name,
            check_legacy_info,
        )

    @staticmethod
    def _update_with_parse_function(
        section_content: ABCRawDataSection,
        section_name: SectionName,
        check_legacy_info: Dict[str, Dict[str, Any]],
    ) -> ParsedSectionContent:
        """Transform the section_content using the defined parse functions.

        Some checks define a parse function that is used to transform the section_content
        somehow. It is applied by this function.

        Please note that this is not a check/subcheck individual setting. This option is related
        to the agent section.

        All exceptions raised by the parse function will be catched and re-raised as
        MKParseFunctionError() exceptions."""
        # We can use the migrated section: we refuse to migrate sections with
        # "'node_info'=True", so the auto-migrated ones will keep working.
        # This function will never be called on checks programmed against the new
        # API (or migrated manually)
        if not agent_based_register.is_registered_section_plugin(section_name):
            # use legacy parse function for unmigrated sections
            parse_function = check_legacy_info.get(str(section_name), {}).get("parse_function")
        else:
            section_plugin = agent_based_register.get_section_plugin(section_name)
            parse_function = cast(Callable[[ABCRawDataSection], ParsedSectionContent],
                                  section_plugin.parse_function)

        if parse_function is None:
            return section_content

        try:
            return parse_function(section_content)
        except item_state.MKCounterWrapped:
            raise
        except Exception:
            if cmk.utils.debug.enabled():
                raise
            raise MKParseFunctionError(*sys.exc_info())

    def legacy_determine_cache_info(self, section_name: SectionName) -> Optional[Tuple[int, int]]:
        """Aggregate information about the age of the data in the agent sections

        This is in checkers.g_agent_cache_info. For clusters we use the oldest
        of the timestamps, of course.
        """
        cache_infos = [
            parser.raw_data.cache_info[section_name]
            for _resolver, parser in self._parsed_sections_broker.values()
            if section_name in parser.raw_data.cache_info
        ]

        return (min(at for at, _ in cache_infos),
                max(interval for _, interval in cache_infos)) if cache_infos else None
