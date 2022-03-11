#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult, StringTable
from cmk.base.plugins.agent_based.cmk_site_statistics import (
    check_cmk_site_statistics,
    CMKSiteStatisticsSection,
    discover_cmk_site_statistics,
    HostStatistics,
    parse_cmk_site_statistics,
    ServiceStatistics,
)
from cmk.base.plugins.agent_based.utils.livestatus_status import LivestatusSection

_SECTION_CMK_SITE_STATISTICS = {
    'heute': (
        HostStatistics(up=1, down=0, unreachable=0, in_downtime=0),
        ServiceStatistics(ok=32, in_downtime=0, on_down_hosts=0, warning=2, unknown=0, critical=1),
    ),
    'gestern': (
        HostStatistics(up=1, down=2, unreachable=3, in_downtime=4),
        ServiceStatistics(ok=5, in_downtime=6, on_down_hosts=7, warning=8, unknown=9, critical=10),
    ),
}

_SECTION_LIVESTATUS_STATUS = {
    'heute': {
        'accept_passive_host_checks': '1',
        'accept_passive_service_checks': '1',
        'average_latency_cmk': '0',
        'average_latency_fetcher': '5.46863e-05',
        'average_latency_generic': '0',
        'average_latency_real_time': '0',
        'average_runnable_jobs_checker': '0',
        'average_runnable_jobs_fetcher': '8.14872e-130',
        'cached_log_messages': '191',
        'check_external_commands': '1',
        'check_host_freshness': '1',
        'check_service_freshness': '1',
        'connections': '1128',
        'connections_rate': '0.0542024',
        'core_pid': '213179',
        'enable_event_handlers': '1',
        'enable_flap_detection': '1',
        'enable_notifications': '1',
        'execute_host_checks': '1',
        'execute_service_checks': '1',
        'external_command_buffer_max': '1',
        'external_command_buffer_slots': '0',
        'external_command_buffer_usage': '0',
        'external_commands': '2',
        'external_commands_rate': '3.38121e-107',
        'forks': '0',
        'forks_rate': '0',
        'has_event_handlers': '0',
        'helper_usage_checker': '7.74162e-07',
        'helper_usage_cmk': '0',
        'helper_usage_fetcher': '0.0057499',
        'helper_usage_generic': '0',
        'helper_usage_real_time': '0',
        'host_checks': '13507',
        'host_checks_rate': '1.83284',
        'interval_length': '60',
        'is_trial_expired': '0',
        'last_command_check': '0',
        'last_log_rotation': '1614934294',
        'license_usage_history': "LQ't#$x~}Qi Q`]`Q[ Q9:DE@CJQi ,LQG6CD:@?Qi Qa_a`]_b]_d]466Q[ Q65:E:@?Qi Q466Q[ QA=2E7@C>Qi Q&3F?EF a_]_c]a {%$Q[ Q:D04>2Qi 72=D6[ QD2>A=60E:>6Qi `e`chbcb_a[ QE:>6K@?6Qi Qrt%Q[ Q?F>09@DEDQi `[ Q?F>09@DED06I4=F565Qi _[ Q?F>0D6CG:46DQi bc[ Q?F>0D6CG:46D06I4=F565Qi _[ Q6IE6?D:@?DQi LQ?E@AQi 72=D6NN.N",
        'livechecks': '0',
        'livechecks_rate': '0',
        'livestatus_active_connections': '1',
        'livestatus_overflows': '0',
        'livestatus_overflows_rate': '0',
        'livestatus_queued_connections': '0',
        'livestatus_threads': '20',
        'livestatus_usage': '6.52923e-52',
        'livestatus_version': '2021.03.05',
        'log_messages': '243',
        'log_messages_rate': '0.000779744',
        'mk_inventory_last': '1614937256',
        'nagios_pid': '213179',
        'neb_callbacks': '0',
        'neb_callbacks_rate': '0',
        'num_hosts': '4',
        'num_queued_alerts': '0',
        'num_queued_notifications': '0',
        'num_services': '135',
        'obsess_over_hosts': '0',
        'obsess_over_services': '0',
        'process_performance_data': '1',
        'program_start': '1614938209',
        'program_version': 'Check_MK 2021.03.05',
        'requests': '5189',
        'requests_rate': '0.0542024',
        'service_checks': '8718',
        'service_checks_rate': '1.86315',
        'state_file_created': '1614934294',
    },
    'gestern': {
        'accept_passive_host_checks': '1',
        'accept_passive_service_checks': '1',
        'average_latency_cmk': '0',
        'average_latency_fetcher': '1.6504e-05',
        'average_latency_generic': '0',
        'average_latency_real_time': '0',
        'average_runnable_jobs_checker': '0',
        'average_runnable_jobs_fetcher': '0',
        'cached_log_messages': '30',
        'check_external_commands': '1',
        'check_host_freshness': '1',
        'check_service_freshness': '1',
        'connections': '712',
        'connections_rate': '0.0660719',
        'core_pid': '196517',
        'enable_event_handlers': '1',
        'enable_flap_detection': '1',
        'enable_notifications': '1',
        'execute_host_checks': '1',
        'execute_service_checks': '1',
        'external_command_buffer_max': '0',
        'external_command_buffer_slots': '0',
        'external_command_buffer_usage': '0',
        'external_commands': '0',
        'external_commands_rate': '0',
        'forks': '0',
        'forks_rate': '0',
        'has_event_handlers': '0',
        'helper_usage_checker': '2.15661e-05',
        'helper_usage_cmk': '0',
        'helper_usage_fetcher': '0.000610388',
        'helper_usage_generic': '0',
        'helper_usage_real_time': '0',
        'host_checks': '2893',
        'host_checks_rate': '0.552585',
        'interval_length': '60',
        'is_trial_expired': '0',
        'last_command_check': '0',
        'last_log_rotation': '1614934313',
        'license_usage_history': "LQ't#$x~}Qi Q`]`Q[ Q9:DE@CJQi ,LQG6CD:@?Qi Qa_a`]_b]_d]466Q[ Q65:E:@?Qi Q466Q[ QA=2E7@C>Qi Q&3F?EF a_]_c]a {%$Q[ Q:D04>2Qi 72=D6[ QD2>A=60E:>6Qi `e`chbcba_[ QE:>6K@?6Qi Qrt%Q[ Q?F>09@DEDQi `[ Q?F>09@DED06I4=F565Qi _[ Q?F>0D6CG:46DQi b_[ Q?F>0D6CG:46D06I4=F565Qi _[ Q6IE6?D:@?DQi LQ?E@AQi 72=D6NN.N",
        'livechecks': '0',
        'livechecks_rate': '0',
        'livestatus_active_connections': '6',
        'livestatus_overflows': '0',
        'livestatus_overflows_rate': '0',
        'livestatus_queued_connections': '0',
        'livestatus_threads': '20',
        'livestatus_usage': '0.25',
        'livestatus_version': '2021.03.05',
        'log_messages': '111',
        'log_messages_rate': '8.02473e-118',
        'mk_inventory_last': '1614936875',
        'nagios_pid': '196517',
        'neb_callbacks': '0',
        'neb_callbacks_rate': '0',
        'num_hosts': '4',
        'num_queued_alerts': '0',
        'num_queued_notifications': '0',
        'num_services': '103',
        'obsess_over_hosts': '0',
        'obsess_over_services': '0',
        'process_performance_data': '1',
        'program_start': '1614937748',
        'program_version': 'Check_MK 2021.03.05',
        'requests': '3703',
        'requests_rate': '0.266072',
        'service_checks': '7410',
        'service_checks_rate': '0.839335',
        'state_file_created': '1614934313',
    },
}


@pytest.mark.parametrize(
    "string_table, parsed_section",
    [
        pytest.param(
            [
                ['[heute]'],
                ['1', '0', '0', '0'],
                ['32', '0', '0', '2', '0', '1'],
                ['[gestern]'],
                ['1', '2', '3', '4'],
                ['5', '6', '7', '8', '9', '10'],
            ],
            _SECTION_CMK_SITE_STATISTICS,
            id="standard case",
        ),
        pytest.param(
            [
                ['[site1]'],
                ['1', '0', '0', '0'],
                ['32', '0', '0', '2', '0', '1'],
                ['[site2]'],
                ['1', '2', '3', '4'],
                ['[site3]'],
                ['1', '0', '0', '0'],
                ['32', '0', '0', '2', '0', '1'],
                ['[site4]'],
                ['32', '0', '0', '2', '0', '1'],
                ['[site5]'],
                ['[site6]'],
                ['1', '0', '0', '0'],
                ['32', '0', '0', '2', '0', '1'],
            ],
            {
                site: (
                    HostStatistics(
                        up=1,
                        down=0,
                        unreachable=0,
                        in_downtime=0,
                    ),
                    ServiceStatistics(
                        ok=32,
                        in_downtime=0,
                        on_down_hosts=0,
                        warning=2,
                        unknown=0,
                        critical=1,
                    ),
                ) for site in (
                    "site1",
                    "site3",
                    "site6",
                )
            },
            id="timeouts in checkmk agent",
        ),
    ],
)
def test_parse_cmk_site_statistics(
    string_table: StringTable,
    parsed_section: CMKSiteStatisticsSection,
) -> None:
    assert parse_cmk_site_statistics(string_table) == parsed_section


def test_discover_cmk_site_statistics() -> None:
    assert list(
        discover_cmk_site_statistics(
            _SECTION_CMK_SITE_STATISTICS,
            _SECTION_LIVESTATUS_STATUS,
        )) == [
            Service(item='heute'),
            Service(item='gestern'),
        ]


@pytest.mark.parametrize(
    "item, section_cmk_site_statistics, section_livestatus_status, expected_result",
    [
        pytest.param(
            'gestern',
            _SECTION_CMK_SITE_STATISTICS,
            _SECTION_LIVESTATUS_STATUS,
            [
                Result(
                    state=State.OK,
                    summary='Total hosts: 10',
                ),
                Result(
                    state=State.OK,
                    summary='Problem hosts: 9',
                    details='Hosts in state UP: 1\n'
                    'Hosts in state DOWN: 2\n'
                    'Unreachable hosts: 3\n'
                    'Hosts in downtime: 4',
                ),
                Result(
                    state=State.OK,
                    summary='Total services: 45',
                ),
                Result(
                    state=State.OK,
                    summary='Problem services: 40',
                    details='Services in state OK: 5\n'
                    'Services in downtime: 6\n'
                    'Services of down hosts: 7\n'
                    'Services in state WARNING: 8\n'
                    'Services in state UNKNOWN: 9\n'
                    'Services in state CRITICAL: 10',
                ),
                Metric('cmk_hosts_up', 1.0),
                Metric('cmk_hosts_down', 2.0),
                Metric('cmk_hosts_unreachable', 3.0),
                Metric('cmk_hosts_in_downtime', 4.0),
                Metric('cmk_services_ok', 5.0),
                Metric('cmk_services_in_downtime', 6.0),
                Metric('cmk_services_on_down_hosts', 7.0),
                Metric('cmk_services_warning', 8.0),
                Metric('cmk_services_unknown', 9.0),
                Metric('cmk_services_critical', 10.0),
                Result(state=State.OK, notice='Core PID: 196517'),
            ],
            id="both sections present",
        ),
        pytest.param(
            "gestern",
            _SECTION_CMK_SITE_STATISTICS,
            {"gestern": None},
            [
                Result(
                    state=State.OK,
                    summary='Total hosts: 10',
                ),
                Result(
                    state=State.OK,
                    summary='Problem hosts: 9',
                    details='Hosts in state UP: 1\n'
                    'Hosts in state DOWN: 2\n'
                    'Unreachable hosts: 3\n'
                    'Hosts in downtime: 4',
                ),
                Result(
                    state=State.OK,
                    summary='Total services: 45',
                ),
                Result(
                    state=State.OK,
                    summary='Problem services: 40',
                    details='Services in state OK: 5\n'
                    'Services in downtime: 6\n'
                    'Services of down hosts: 7\n'
                    'Services in state WARNING: 8\n'
                    'Services in state UNKNOWN: 9\n'
                    'Services in state CRITICAL: 10',
                ),
                Metric('cmk_hosts_up', 1.0),
                Metric('cmk_hosts_down', 2.0),
                Metric('cmk_hosts_unreachable', 3.0),
                Metric('cmk_hosts_in_downtime', 4.0),
                Metric('cmk_services_ok', 5.0),
                Metric('cmk_services_in_downtime', 6.0),
                Metric('cmk_services_on_down_hosts', 7.0),
                Metric('cmk_services_warning', 8.0),
                Metric('cmk_services_unknown', 9.0),
                Metric('cmk_services_critical', 10.0),
            ],
            id="livestatus section missing",
        )
    ],
)
def test_check_cmk_site_statistics(
    item: str,
    section_cmk_site_statistics: CMKSiteStatisticsSection,
    section_livestatus_status: LivestatusSection,
    expected_result: CheckResult,
) -> None:
    assert list(
        check_cmk_site_statistics(
            item,
            section_cmk_site_statistics,
            section_livestatus_status,
        )) == expected_result
