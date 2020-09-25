#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
from testlib import on_time
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    Service,
    State as state,
    Result,
    Metric,
)

from cmk.utils.type_defs import CheckPluginName
from cmk.base.api.agent_based import value_store
from cmk.base.api.agent_based.type_defs import Parameters
import cmk.base.plugins.agent_based.livestatus_status as livestatus_status

NOW_SIMULATED = 581785200, "UTC"
STRING_TABLE_STATUS = [
    ['[heute]'],
    [
        'accept_passive_host_checks', 'accept_passive_service_checks', 'average_latency_cmk',
        'average_latency_generic', 'average_latency_real_time', 'cached_log_messages',
        'check_external_commands', 'check_host_freshness', 'check_service_freshness', 'connections',
        'connections_rate', 'core_pid', 'enable_event_handlers', 'enable_flap_detection',
        'enable_notifications', 'execute_host_checks', 'execute_service_checks',
        'external_command_buffer_max', 'external_command_buffer_slots',
        'external_command_buffer_usage', 'external_commands', 'external_commands_rate', 'forks',
        'forks_rate', 'has_event_handlers', 'helper_usage_cmk', 'helper_usage_fetcher',
        'helper_usage_checker', 'helper_usage_generic', 'helper_usage_real_time', 'host_checks',
        'host_checks_rate', 'interval_length', 'last_command_check', 'last_log_rotation',
        'livecheck_overflows', 'livecheck_overflows_rate', 'livechecks', 'livechecks_rate',
        'livestatus_active_connections', 'livestatus_overflows', 'livestatus_overflows_rate',
        'livestatus_queued_connections', 'livestatus_threads', 'livestatus_usage',
        'livestatus_version', 'log_messages', 'log_messages_rate', 'mk_inventory_last',
        'nagios_pid', 'neb_callbacks', 'neb_callbacks_rate', 'num_hosts', 'num_queued_alerts',
        'num_queued_notifications', 'num_services', 'obsess_over_hosts', 'obsess_over_services',
        'process_performance_data', 'program_start', 'program_version', 'requests', 'requests_rate',
        'service_checks', 'service_checks_rate'
    ],
    [
        '1', '1', '2.01088e-05', '2.23711e-06', '0', '446', '1', '1', '1', '3645', '0.0319528',
        '6334', '1', '1', '1', '1', '1', '1', '0', '0', '49', '9.88131e-324', '0', '0', '0',
        '0.000438272', '0.000438272', '0.000438272', '0.0142967', '0', '44310', '11.1626', '60',
        '0', '1559292801', '0', '0', '3793', '0.0695533', '1', '0', '0', '0', '20', '3.45846e-323',
        '2019.05.31', '932', '1.84655e-07', '1559732314', '6334', '0', '0', '2', '0', '0', '513',
        '0', '0', '1', '1559719506', 'Check_MK 2019.05.31', '4709', '0.0319528', '156263', '5.85075'
    ], ['[oldstable]'],
    [
        'accept_passive_host_checks', 'accept_passive_service_checks', 'average_latency_cmk',
        'average_latency_generic', 'average_latency_real_time', 'cached_log_messages',
        'check_external_commands', 'check_host_freshness', 'check_service_freshness', 'connections',
        'connections_rate', 'core_pid', 'enable_event_handlers', 'enable_flap_detection',
        'enable_notifications', 'execute_host_checks', 'execute_service_checks',
        'external_command_buffer_max', 'external_command_buffer_slots',
        'external_command_buffer_usage', 'external_commands', 'external_commands_rate', 'forks',
        'forks_rate', 'has_event_handlers', 'helper_usage_cmk', 'helper_usage_generic',
        'helper_usage_real_time', 'host_checks', 'host_checks_rate', 'interval_length',
        'last_command_check', 'last_log_rotation', 'livecheck_overflows',
        'livecheck_overflows_rate', 'livechecks', 'livechecks_rate',
        'livestatus_active_connections', 'livestatus_overflows', 'livestatus_overflows_rate',
        'livestatus_queued_connections', 'livestatus_threads', 'livestatus_usage',
        'livestatus_version', 'log_messages', 'log_messages_rate', 'mk_inventory_last',
        'nagios_pid', 'neb_callbacks', 'neb_callbacks_rate', 'num_hosts', 'num_services',
        'obsess_over_hosts', 'obsess_over_services', 'process_performance_data', 'program_start',
        'program_version', 'requests', 'requests_rate', 'service_checks', 'service_checks_rate'
    ],
    [
        '1', '1', '0', '0', '0', '0', '1', '1', '1', '3390', '0.0319528', '3294', '1', '1', '1',
        '1', '1', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '0', '60', '0',
        '1559562137', '0', '0', '0', '0', '1', '0', '0', '0', '20', '0', '1.4.0p38', '4',
        '9.88131e-324', '0', '3294', '0', '0', '0', '0', '0', '0', '1', '1559629930',
        'Check_MK 1.4.0p38', '3390', '0.0319528', '0', '0'
    ], ['[stable]'],
    [
        'accept_passive_host_checks', 'accept_passive_service_checks', 'average_latency_cmk',
        'average_latency_generic', 'average_latency_real_time', 'cached_log_messages',
        'check_external_commands', 'check_host_freshness', 'check_service_freshness', 'connections',
        'connections_rate', 'core_pid', 'enable_event_handlers', 'enable_flap_detection',
        'enable_notifications', 'execute_host_checks', 'execute_service_checks',
        'external_command_buffer_max', 'external_command_buffer_slots',
        'external_command_buffer_usage', 'external_commands', 'external_commands_rate', 'forks',
        'forks_rate', 'has_event_handlers', 'helper_usage_cmk', 'helper_usage_fetcher',
        'helper_usage_checker', 'helper_usage_generic', 'helper_usage_real_time', 'host_checks',
        'host_checks_rate', 'interval_length', 'last_command_check', 'last_log_rotation',
        'livecheck_overflows', 'livecheck_overflows_rate', 'livechecks', 'livechecks_rate',
        'livestatus_active_connections', 'livestatus_overflows', 'livestatus_overflows_rate',
        'livestatus_queued_connections', 'livestatus_threads', 'livestatus_usage',
        'livestatus_version', 'log_messages', 'log_messages_rate', 'mk_inventory_last',
        'nagios_pid', 'neb_callbacks', 'neb_callbacks_rate', 'num_hosts', 'num_queued_alerts',
        'num_queued_notifications', 'num_services', 'obsess_over_hosts', 'obsess_over_services',
        'process_performance_data', 'program_start', 'program_version', 'requests', 'requests_rate',
        'service_checks', 'service_checks_rate'
    ],
    [
        '1', '1', '1.16922e-05', '0', '0', '152', '1', '1', '1', '109', '0.0952764', '27961', '1',
        '1', '1', '1', '1', '1', '0', '0', '2', '9.88576e-38', '0', '0', '0', '2.51355e-07',
        '2.51355e-07', '2.51355e-07', '0', '0', '5792', '10.9501', '60', '0', '1558943084', '0',
        '0', '52', '0.0319455', '1', '0', '0', '0', '20', '7.76247e-05', '1.5.0-2019.05.27', '68',
        '1.34222e-06', '1559648243', '27961', '0', '0', '2', '0', '0', '45', '0', '0', '1',
        '1559730846', 'Check_MK 1.5.0-2019.05.27', '385', '0.437433', '1058', '1.11243'
    ]
]
PARSED_STATUS = {
    'heute': {
        'accept_passive_host_checks': '1',
        'accept_passive_service_checks': '1',
        'average_latency_cmk': '2.01088e-05',
        'average_latency_generic': '2.23711e-06',
        'average_latency_real_time': '0',
        'cached_log_messages': '446',
        'check_external_commands': '1',
        'check_host_freshness': '1',
        'check_service_freshness': '1',
        'connections': '3645',
        'connections_rate': '0.0319528',
        'core_pid': '6334',
        'enable_event_handlers': '1',
        'enable_flap_detection': '1',
        'enable_notifications': '1',
        'execute_host_checks': '1',
        'execute_service_checks': '1',
        'external_command_buffer_max': '1',
        'external_command_buffer_slots': '0',
        'external_command_buffer_usage': '0',
        'external_commands': '49',
        'external_commands_rate': '9.88131e-324',
        'forks': '0',
        'forks_rate': '0',
        'has_event_handlers': '0',
        'helper_usage_cmk': '0.000438272',
        'helper_usage_fetcher': '0.000438272',
        'helper_usage_checker': '0.000438272',
        'helper_usage_generic': '0.0142967',
        'helper_usage_real_time': '0',
        'host_checks': '44310',
        'host_checks_rate': '11.1626',
        'interval_length': '60',
        'last_command_check': '0',
        'last_log_rotation': '1559292801',
        'livecheck_overflows': '0',
        'livecheck_overflows_rate': '0',
        'livechecks': '3793',
        'livechecks_rate': '0.0695533',
        'livestatus_active_connections': '1',
        'livestatus_overflows': '0',
        'livestatus_overflows_rate': '0',
        'livestatus_queued_connections': '0',
        'livestatus_threads': '20',
        'livestatus_usage': '3.45846e-323',
        'livestatus_version': '2019.05.31',
        'log_messages': '932',
        'log_messages_rate': '1.84655e-07',
        'mk_inventory_last': '1559732314',
        'nagios_pid': '6334',
        'neb_callbacks': '0',
        'neb_callbacks_rate': '0',
        'num_hosts': '2',
        'num_queued_alerts': '0',
        'num_queued_notifications': '0',
        'num_services': '513',
        'obsess_over_hosts': '0',
        'obsess_over_services': '0',
        'process_performance_data': '1',
        'program_start': '1559719506',
        'program_version': 'Check_MK 2019.05.31',
        'requests': '4709',
        'requests_rate': '0.0319528',
        'service_checks': '156263',
        'service_checks_rate': '5.85075'
    },
    'oldstable': {
        'accept_passive_host_checks': '1',
        'accept_passive_service_checks': '1',
        'average_latency_cmk': '0',
        'average_latency_generic': '0',
        'average_latency_real_time': '0',
        'cached_log_messages': '0',
        'check_external_commands': '1',
        'check_host_freshness': '1',
        'check_service_freshness': '1',
        'connections': '3390',
        'connections_rate': '0.0319528',
        'core_pid': '3294',
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
        'helper_usage_cmk': '0',
        # Simulate the host without those counters:
        #'helper_usage_fetcher': '0',
        #'helper_usage_checker': '0',
        'helper_usage_generic': '0',
        'helper_usage_real_time': '0',
        'host_checks': '0',
        'host_checks_rate': '0',
        'interval_length': '60',
        'last_command_check': '0',
        'last_log_rotation': '1559562137',
        'livecheck_overflows': '0',
        'livecheck_overflows_rate': '0',
        'livechecks': '0',
        'livechecks_rate': '0',
        'livestatus_active_connections': '1',
        'livestatus_overflows': '0',
        'livestatus_overflows_rate': '0',
        'livestatus_queued_connections': '0',
        'livestatus_threads': '20',
        'livestatus_usage': '0',
        'livestatus_version': '1.4.0p38',
        'log_messages': '4',
        'log_messages_rate': '9.88131e-324',
        'mk_inventory_last': '0',
        'nagios_pid': '3294',
        'neb_callbacks': '0',
        'neb_callbacks_rate': '0',
        'num_hosts': '0',
        'num_services': '0',
        'obsess_over_hosts': '0',
        'obsess_over_services': '0',
        'process_performance_data': '1',
        'program_start': '1559629930',
        'program_version': 'Check_MK 1.4.0p38',
        'requests': '3390',
        'requests_rate': '0.0319528',
        'service_checks': '0',
        'service_checks_rate': '0'
    },
    'stable': {
        'accept_passive_host_checks': '1',
        'accept_passive_service_checks': '1',
        'average_latency_cmk': '1.16922e-05',
        'average_latency_generic': '0',
        'average_latency_real_time': '0',
        'cached_log_messages': '152',
        'check_external_commands': '1',
        'check_host_freshness': '1',
        'check_service_freshness': '1',
        'connections': '109',
        'connections_rate': '0.0952764',
        'core_pid': '27961',
        'enable_event_handlers': '1',
        'enable_flap_detection': '1',
        'enable_notifications': '1',
        'execute_host_checks': '1',
        'execute_service_checks': '1',
        'external_command_buffer_max': '1',
        'external_command_buffer_slots': '0',
        'external_command_buffer_usage': '0',
        'external_commands': '2',
        'external_commands_rate': '9.88576e-38',
        'forks': '0',
        'forks_rate': '0',
        'has_event_handlers': '0',
        'helper_usage_cmk': '2.51355e-07',
        'helper_usage_fetcher': '2.51355e-07',
        'helper_usage_checker': '2.51355e-07',
        'helper_usage_generic': '0',
        'helper_usage_real_time': '0',
        'host_checks': '5792',
        'host_checks_rate': '10.9501',
        'interval_length': '60',
        'last_command_check': '0',
        'last_log_rotation': '1558943084',
        'livecheck_overflows': '0',
        'livecheck_overflows_rate': '0',
        'livechecks': '52',
        'livechecks_rate': '0.0319455',
        'livestatus_active_connections': '1',
        'livestatus_overflows': '0',
        'livestatus_overflows_rate': '0',
        'livestatus_queued_connections': '0',
        'livestatus_threads': '20',
        'livestatus_usage': '7.76247e-05',
        'livestatus_version': '1.5.0-2019.05.27',
        'log_messages': '68',
        'log_messages_rate': '1.34222e-06',
        'mk_inventory_last': '1559648243',
        'nagios_pid': '27961',
        'neb_callbacks': '0',
        'neb_callbacks_rate': '0',
        'num_hosts': '2',
        'num_queued_alerts': '0',
        'num_queued_notifications': '0',
        'num_services': '45',
        'obsess_over_hosts': '0',
        'obsess_over_services': '0',
        'process_performance_data': '1',
        'program_start': '1559730846',
        'program_version': 'Check_MK 1.5.0-2019.05.27',
        'requests': '385',
        'requests_rate': '0.437433',
        'service_checks': '1058',
        'service_checks_rate': '1.11243'
    }
}
STRING_TABLE_SSL = [['[cmk]'], ['[heute]'], ['/omd/sites/heute/etc/ssl/ca.pem', '33063756788'],
                    ['/omd/sites/heute/etc/ssl/sites/heute.pem', '33063756788'], ['[oldstable]'],
                    ['[stable]']]
PARSED_SSL = {
    'cmk': {},
    'heute': {
        '/omd/sites/heute/etc/ssl/ca.pem': '33063756788',
        '/omd/sites/heute/etc/ssl/sites/heute.pem': '33063756788'
    },
    'oldstable': {},
    'stable': {}
}


def test_parse():
    assert livestatus_status.parse_livestatus_status(STRING_TABLE_STATUS) == PARSED_STATUS
    assert livestatus_status.parse_livestatus_ssl_certs(STRING_TABLE_SSL) == PARSED_SSL


def test_discovery():
    discovered_services = list(
        livestatus_status.discovery_livestatus_status(PARSED_STATUS, PARSED_SSL))
    assert discovered_services == [
        Service(item='heute', parameters={}, labels=[]),
        Service(item='oldstable', parameters={}, labels=[]),
        Service(item='stable', parameters={}, labels=[]),
    ]


@pytest.fixture(name="fetcher_checker_counters")
def fixture_fetcher_checker_counters_list():
    return [
        Result(state=state.OK,
               summary='Fetcher helper usage: 0%',
               details='Fetcher helper usage: 0%'),
        Metric('helper_usage_fetcher', 0.0, levels=(40.0, 80.0), boundaries=(None, None)),
        Result(state=state.OK,
               summary='Checker helper usage: 0%',
               details='Checker helper usage: 0%'),
        Metric('helper_usage_checker', 0.0, levels=(40.0, 80.0), boundaries=(None, None)),
    ]


def patch_get_value(monkeypatch, item):
    value_store_patched = {}
    for key in [
            "host_checks",
            "service_checks",
            "forks",
            "connections",
            "requests",
            "log_messages",
    ]:
        value_store_patched["livestatus_status.%s.%s" % (item, key)] = [1, 2]

    monkeypatch.setattr(livestatus_status, 'get_value_store', lambda: value_store_patched)


@pytest.mark.usefixtures("fetcher_checker_counters")
def test_check_new_counters_in_oldstable(monkeypatch, fetcher_checker_counters):
    patch_get_value(monkeypatch, "oldstable")

    with on_time(*NOW_SIMULATED):
        with value_store.context(CheckPluginName("livestatus_status"), None):

            yielded_results = list(
                livestatus_status.check_livestatus_status(
                    "oldstable",
                    Parameters(livestatus_status.livestatus_status_default_levels),
                    PARSED_STATUS,
                    PARSED_SSL,
                ))
            assert all(x in yielded_results for x in fetcher_checker_counters)


@pytest.mark.parametrize("item, params", [
    ("heute", livestatus_status.livestatus_status_default_levels),
])
def test_check(monkeypatch, item, params):
    patch_get_value(monkeypatch, item)

    with on_time(*NOW_SIMULATED):
        with value_store.context(CheckPluginName("livestatus_status"), None):

            yielded_results = list(
                livestatus_status.check_livestatus_status(item, params, PARSED_STATUS, PARSED_SSL))

            assert yielded_results == [
                Result(state=state.OK, summary='HostChecks: 0.0/s', details='HostChecks: 0.0/s'),
                Metric('host_checks',
                       7.615869237677187e-05,
                       levels=(None, None),
                       boundaries=(None, None)),
                Result(state=state.OK,
                       summary='ServiceChecks: 0.0/s',
                       details='ServiceChecks: 0.0/s'),
                Metric('service_checks',
                       0.0002685888198403617,
                       levels=(None, None),
                       boundaries=(None, None)),
                Result(state=state.OK,
                       summary='ProcessCreations: -0.0/s',
                       details='ProcessCreations: -0.0/s'),
                Metric('forks',
                       -3.4376948802370615e-09,
                       levels=(None, None),
                       boundaries=(None, None)),
                Result(state=state.OK,
                       summary='LivestatusConnects: 0.0/s',
                       details='LivestatusConnects: 0.0/s'),
                Metric('connections',
                       6.261761224351807e-06,
                       levels=(None, None),
                       boundaries=(None, None)),
                Result(state=state.OK,
                       summary='LivestatusRequests: 0.0/s',
                       details='LivestatusRequests: 0.0/s'),
                Metric('requests',
                       8.090614900637924e-06,
                       levels=(None, None),
                       boundaries=(None, None)),
                Result(state=state.OK, summary='LogMessages: 0.0/s', details='LogMessages: 0.0/s'),
                Metric('log_messages',
                       1.5985281193102335e-06,
                       levels=(None, None),
                       boundaries=(None, None)),
                Result(state=state.OK,
                       summary='Average check latency: 0.000s',
                       details='Average check latency: 0.000s'),
                Metric('average_latency_generic',
                       2.23711e-06,
                       levels=(30.0, 60.0),
                       boundaries=(None, None)),
                Result(state=state.OK,
                       summary='Average Checkmk latency: 0.000s',
                       details='Average Checkmk latency: 0.000s'),
                Metric('average_latency_cmk',
                       2.01088e-05,
                       levels=(30.0, 60.0),
                       boundaries=(None, None)),
                Result(state=state.OK,
                       summary='Check helper usage: 1.43%',
                       details='Check helper usage: 1.43%'),
                Metric('helper_usage_generic',
                       1.42967,
                       levels=(60.0, 90.0),
                       boundaries=(None, None)),
                Result(state=state.OK,
                       summary='Checkmk helper usage: 0.04%',
                       details='Checkmk helper usage: 0.04%'),
                Metric('helper_usage_cmk',
                       0.043827200000000004,
                       levels=(60.0, 90.0),
                       boundaries=(None, None)),
                Result(state=state.OK,
                       summary='Fetcher helper usage: 0.04%',
                       details='Fetcher helper usage: 0.04%'),
                Metric('helper_usage_fetcher',
                       0.043827200000000004,
                       levels=(40.0, 80.0),
                       boundaries=(None, None)),
                Result(state=state.OK,
                       summary='Checker helper usage: 0.04%',
                       details='Checker helper usage: 0.04%'),
                Metric('helper_usage_checker',
                       0.043827200000000004,
                       levels=(40.0, 80.0),
                       boundaries=(None, None)),
                Result(state=state.OK,
                       summary='Livestatus usage: 0.00%',
                       details='Livestatus usage: 0.00%'),
                Metric('livestatus_usage', 3.46e-321, levels=(80.0, 90.0), boundaries=(None, None)),
                Result(state=state.OK,
                       summary='Livestatus overflow rate: 0.0/s',
                       details='Livestatus overflow rate: 0.0/s'),
                Metric('livestatus_overflows_rate',
                       0.0,
                       levels=(0.01, 0.02),
                       boundaries=(None, None)),
                Result(state=state.OK,
                       summary='Monitored Hosts: 2.00',
                       details='Monitored Hosts: 2.00'),
                Metric('monitored_hosts', 2.0, levels=(None, None), boundaries=(None, None)),
                Result(state=state.OK, summary='Services: 513.00', details='Services: 513.00'),
                Metric('monitored_services', 513.0, levels=(None, None), boundaries=(None, None)),
                Result(state=state.OK,
                       summary='Core version: Checkmk 2019.05.31',
                       details='Core version: Checkmk 2019.05.31'),
                Result(state=state.OK,
                       summary='Livestatus version: 2019.05.31',
                       details='Livestatus version: 2019.05.31'),
                Result(state=state.OK,
                       summary='Site certificate validity (until 3017-10-01 08:53:08): 375948.75',
                       details='Site certificate validity (until 3017-10-01 08:53:08): 375948.75'),
                Metric('site_cert_days',
                       375948.7452314815,
                       levels=(None, None),
                       boundaries=(None, None)),
            ]
