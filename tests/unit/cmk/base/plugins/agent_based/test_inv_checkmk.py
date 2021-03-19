#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Dict

import pytest  # type: ignore[import]

from cmk.base.plugins.agent_based import inv_checkmk
from cmk.base.api.agent_based.inventory_classes import TableRow, Attributes

SECTION_LIVESTATUS_STATUS = {
    'heute': {
        'accept_passive_host_checks': '1',
        'accept_passive_service_checks': '1',
        'average_latency_cmk': '0.456069',
        'average_latency_fetcher': '0.456069',
        'average_latency_generic': '0.83618',
        'average_latency_real_time': '0',
        'cached_log_messages': '86',
        'check_external_commands': '1',
        'check_host_freshness': '1',
        'check_service_freshness': '1',
        'connections': '48',
        'connections_rate': '0.0813164',
        'core_pid': '3845866',
        'enable_event_handlers': '1',
        'enable_flap_detection': '1',
        'enable_notifications': '1',
        'execute_host_checks': '1',
        'execute_service_checks': '1',
        'external_command_buffer_max': '1',
        'external_command_buffer_slots': '0',
        'external_command_buffer_usage': '0',
        'external_commands': '2',
        'external_commands_rate': '2.27554e-11',
        'forks': '0',
        'forks_rate': '0',
        'has_event_handlers': '0',
        'helper_usage_cmk': '0.00172541',
        'helper_usage_checker': '0.00172541',
        'helper_usage_fetcher': '0.00172541',
        'helper_usage_generic': '6.34573e-14',
        'helper_usage_real_time': '0',
        'host_checks': '820',
        'host_checks_rate': '1.52884',
        'interval_length': '60',
        'last_command_check': '0',
        'last_log_rotation': '1597912517',
        'livechecks': '7',
        'livechecks_rate': '0.0038456',
        'livestatus_active_connections': '1',
        'livestatus_overflows': '0',
        'livestatus_overflows_rate': '0',
        'livestatus_queued_connections': '0',
        'livestatus_threads': '20',
        'livestatus_usage': '0.0',
        'livestatus_version': '2020.08.20',
        'log_messages': '58',
        'log_messages_rate': '0.00679318',
        'mk_inventory_last': '1597927626',
        'nagios_pid': '3845866',
        'neb_callbacks': '0',
        'neb_callbacks_rate': '0',
        'num_hosts': '1',
        'num_queued_alerts': '0',
        'num_queued_notifications': '0',
        'num_services': '48',
        'obsess_over_hosts': '0',
        'obsess_over_services': '0',
        'process_performance_data': '1',
        'program_start': '1597927584',
        'program_version': 'Check_MK 2020.08.20',
        'requests': '155',
        'requests_rate': '0.20962',
        'service_checks': '277',
        'service_checks_rate': '0.312616'
    },
    'stable': {
        'accept_passive_host_checks': '1',
        'accept_passive_service_checks': '1',
        'average_latency_cmk': '2.93392e-05',
        'average_latency_fetcher': '2.93392e-05',
        'average_latency_generic': '6.15271e-06',
        'average_latency_real_time': '0',
        'cached_log_messages': '848',
        'check_external_commands': '1',
        'check_host_freshness': '1',
        'check_service_freshness': '1',
        'connections': '3819',
        'connections_rate': '0.0530824',
        'core_pid': '1667677',
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
        'helper_usage_cmk': '0.00377173',
        'helper_usage_fetcher': '0.00377173',
        'helper_usage_checker': '0.00377173',
        'helper_usage_generic': '3.45846e-323',
        'helper_usage_real_time': '0',
        'host_checks': '182590',
        'host_checks_rate': '2.80027',
        'interval_length': '60',
        'last_command_check': '0',
        'last_log_rotation': '1597761337',
        'livechecks': '2903',
        'livechecks_rate': '0.0771468',
        'livestatus_active_connections': '1',
        'livestatus_overflows': '0',
        'livestatus_overflows_rate': '0',
        'livestatus_queued_connections': '0',
        'livestatus_threads': '20',
        'livestatus_usage': '0.0',
        'livestatus_version': '1.6.0-2020.08.18',
        'log_messages': '706',
        'log_messages_rate': '0.075',
        'mk_inventory_last': '1597847744',
        'nagios_pid': '1667677',
        'neb_callbacks': '0',
        'neb_callbacks_rate': '0',
        'num_hosts': '2',
        'num_queued_alerts': '0',
        'num_queued_notifications': '0',
        'num_services': '103',
        'obsess_over_hosts': '0',
        'obsess_over_services': '0',
        'process_performance_data': '1',
        'program_start': '1597840735',
        'program_version': 'Check_MK 1.6.0-2020.08.18',
        'requests': '8762',
        'requests_rate': '0.0530824',
        'service_checks': '83939',
        'service_checks_rate': '2.28431'
    }
}
SECTION_OMD_STATUS: Dict[str, Dict[str, Any]] = {
    'cisco': {
        'stopped': [
            'mkeventd', 'liveproxyd', 'mknotifyd', 'rrdcached', 'cmc', 'apache', 'dcd', 'crontab'
        ],
        'existing': [
            'mkeventd', 'liveproxyd', 'mknotifyd', 'rrdcached', 'cmc', 'apache', 'dcd', 'crontab'
        ],
        'overall': 'stopped'
    },
    'heute': {
        'stopped': [],
        'existing': [
            'mkeventd', 'liveproxyd', 'mknotifyd', 'rrdcached', 'cmc', 'apache', 'dcd', 'crontab'
        ],
        'overall': 'running'
    },
    'stable': {
        'stopped': [],
        'existing': [
            'mkeventd', 'liveproxyd', 'mknotifyd', 'rrdcached', 'cmc', 'apache', 'dcd', 'crontab'
        ],
        'overall': 'running'
    }
}
SECTION_OMD_INFO = {
    'versions': {
        '1.6.0-2020.08.18.cee': {
            'version': '1.6.0-2020.08.18.cee',
            'number': '1.6.0-2020.08.18',
            'edition': 'cee',
            'demo': '0'
        },
        '1.6.0p12.cee': {
            'version': '1.6.0p12.cee',
            'number': '1.6.0p12',
            'edition': 'cee',
            'demo': '0'
        },
        '1.6.0p13.cee': {
            'version': '1.6.0p13.cee',
            'number': '1.6.0p13',
            'edition': 'cee',
            'demo': '0'
        },
        '2020.08.13.cee': {
            'version': '2020.08.13.cee',
            'number': '2020.08.13',
            'edition': 'cee',
            'demo': '0'
        },
        '2020.08.20.cee': {
            'version': '2020.08.20.cee',
            'number': '2020.08.20',
            'edition': 'cee',
            'demo': '0'
        }
    },
    'sites': {
        'cisco': {
            'site': 'cisco',
            'used_version': '1.6.0p13.cee',
            'autostart': '0'
        },
        'heute': {
            'site': 'heute',
            'used_version': '2020.08.20.cee',
            'autostart': '0'
        },
        'stable': {
            'site': 'stable',
            'used_version': '1.6.0-2020.08.18.cee',
            'autostart': '0'
        }
    }
}

MERGED_SECTION_ENTERPRISE = {
    'check_mk': {
        'num_sites': 3,
        'num_versions': 5
    },
    'sites': {
        'cisco': {
            'inventory_columns': {
                'autostart': False,
                'used_version': '1.6.0p13.cee'
            },
            'status_columns': {
                'apache': 'stopped',
                'cmc': 'stopped',
                'crontab': 'stopped',
                'dcd': 'stopped',
                'liveproxyd': 'stopped',
                'mkeventd': 'stopped',
                'mknotifyd': 'stopped',
                'rrdcached': 'stopped',
                'stunnel': 'not existent',
                'xinetd': 'not existent'
            }
        },
        'heute': {
            'inventory_columns': {
                'autostart': False,
                'used_version': '2020.08.20.cee'
            },
            'status_columns': {
                'apache': 'running',
                'check_helper_usage': 6.34573e-12,
                'check_mk_helper_usage': 0.172541,
                'fetcher_helper_usage': 0.172541,
                'checker_helper_usage': 0.172541,
                'cmc': 'running',
                'crontab': 'running',
                'dcd': 'running',
                'liveproxyd': 'running',
                'livestatus_usage': 0.0,
                'mkeventd': 'running',
                'mknotifyd': 'running',
                'num_hosts': '1',
                'num_services': '48',
                'rrdcached': 'running',
                'stunnel': 'not existent',
                'xinetd': 'not existent'
            }
        },
        'stable': {
            'inventory_columns': {
                'autostart': False,
                'used_version': '1.6.0-2020.08.18.cee'
            },
            'status_columns': {
                'apache': 'running',
                'check_helper_usage': 3.46e-321,
                'check_mk_helper_usage': 0.377173,
                'fetcher_helper_usage': 0.377173,
                'checker_helper_usage': 0.377173,
                'cmc': 'running',
                'crontab': 'running',
                'dcd': 'running',
                'liveproxyd': 'running',
                'livestatus_usage': 0.0,
                'mkeventd': 'running',
                'mknotifyd': 'running',
                'num_hosts': '2',
                'num_services': '103',
                'rrdcached': 'running',
                'stunnel': 'not existent',
                'xinetd': 'not existent'
            }
        }
    },
    'versions': {
        '1.6.0-2020.08.18.cee': {
            'demo': False,
            'edition': 'cee',
            'num_sites': 1,
            'number': '1.6.0-2020.08.18'
        },
        '1.6.0p12.cee': {
            'demo': False,
            'edition': 'cee',
            'num_sites': 0,
            'number': '1.6.0p12'
        },
        '1.6.0p13.cee': {
            'demo': False,
            'edition': 'cee',
            'num_sites': 1,
            'number': '1.6.0p13'
        },
        '2020.08.13.cee': {
            'demo': False,
            'edition': 'cee',
            'num_sites': 0,
            'number': '2020.08.13'
        },
        '2020.08.20.cee': {
            'demo': False,
            'edition': 'cee',
            'num_sites': 1,
            'number': '2020.08.20'
        }
    },
}

MERGED_SECTION_RAWEDITION = {
    'check_mk': {
        'num_sites': 3,
        'num_versions': 5
    },
    'sites': {
        'cisco': {
            'inventory_columns': {
                'autostart': False,
                'used_version': '1.6.0p13.cee'
            },
            'status_columns': {
                'apache': 'stopped',
                'crontab': 'stopped',
                'mkeventd': 'stopped',
                'nagios': 'not existent',
                'npcd': 'not existent',
                'rrdcached': 'stopped',
                'stunnel': 'not existent',
                'xinetd': 'not existent'
            }
        },
        'heute': {
            'inventory_columns': {
                'autostart': False,
                'used_version': '2020.08.20.cee'
            },
            'status_columns': {
                'apache': 'running',
                'check_helper_usage': 6.34573e-12,
                'check_mk_helper_usage': 0.172541,
                'fetcher_helper_usage': 0.172541,
                'checker_helper_usage': 0.172541,
                'crontab': 'running',
                'livestatus_usage': 0.0,
                'mkeventd': 'running',
                'nagios': 'not existent',
                'npcd': 'not existent',
                'num_hosts': '1',
                'num_services': '48',
                'rrdcached': 'running',
                'stunnel': 'not existent',
                'xinetd': 'not existent'
            }
        },
        'stable': {
            'inventory_columns': {
                'autostart': False,
                'used_version': '1.6.0-2020.08.18.cee'
            },
            'status_columns': {
                'apache': 'running',
                'check_helper_usage': 3.46e-321,
                'check_mk_helper_usage': 0.377173,
                'fetcher_helper_usage': 0.377173,
                'checker_helper_usage': 0.377173,
                'crontab': 'running',
                'livestatus_usage': 0.0,
                'mkeventd': 'running',
                'nagios': 'not existent',
                'npcd': 'not existent',
                'num_hosts': '2',
                'num_services': '103',
                'rrdcached': 'running',
                'stunnel': 'not existent',
                'xinetd': 'not existent'
            }
        }
    },
    'versions': {
        '1.6.0-2020.08.18.cee': {
            'demo': False,
            'edition': 'cee',
            'num_sites': 2,
            'number': '1.6.0-2020.08.18'
        },
        '1.6.0p12.cee': {
            'demo': False,
            'edition': 'cee',
            'num_sites': 0,
            'number': '1.6.0p12'
        },
        '1.6.0p13.cee': {
            'demo': False,
            'edition': 'cee',
            'num_sites': 2,
            'number': '1.6.0p13'
        },
        '2020.08.13.cee': {
            'demo': False,
            'edition': 'cee',
            'num_sites': 0,
            'number': '2020.08.13'
        },
        '2020.08.20.cee': {
            'demo': False,
            'edition': 'cee',
            'num_sites': 2,
            'number': '2020.08.20'
        }
    },
}


@pytest.mark.parametrize("is_raw_edition, merged_sections", [
    (False, MERGED_SECTION_ENTERPRISE),
    (True, MERGED_SECTION_RAWEDITION),
])
def test_merge_sections(monkeypatch, is_raw_edition, merged_sections):
    monkeypatch.setattr(inv_checkmk.cmk_version, "is_raw_edition", lambda: is_raw_edition)
    assert merged_sections == inv_checkmk.merge_sections(SECTION_LIVESTATUS_STATUS,
                                                         SECTION_OMD_STATUS, SECTION_OMD_INFO)


def test_inventory_checkmk():

    yielded_inventory = list(inv_checkmk.generate_inventory(MERGED_SECTION_ENTERPRISE))
    assert yielded_inventory == [
        TableRow(path=['software', 'applications', 'check_mk', 'sites'],
                 key_columns={'site': 'cisco'},
                 inventory_columns={
                     'autostart': False,
                     'used_version': '1.6.0p13.cee'
                 },
                 status_columns={
                     'apache': 'stopped',
                     'cmc': 'stopped',
                     'crontab': 'stopped',
                     'dcd': 'stopped',
                     'liveproxyd': 'stopped',
                     'mkeventd': 'stopped',
                     'mknotifyd': 'stopped',
                     'rrdcached': 'stopped',
                     'stunnel': 'not existent',
                     'xinetd': 'not existent'
                 }),
        TableRow(path=['software', 'applications', 'check_mk', 'sites'],
                 key_columns={'site': 'heute'},
                 inventory_columns={
                     'autostart': False,
                     'used_version': '2020.08.20.cee'
                 },
                 status_columns={
                     'apache': 'running',
                     'check_helper_usage': 6.34573e-12,
                     'check_mk_helper_usage': 0.172541,
                     'fetcher_helper_usage': 0.172541,
                     'checker_helper_usage': 0.172541,
                     'cmc': 'running',
                     'crontab': 'running',
                     'dcd': 'running',
                     'liveproxyd': 'running',
                     'livestatus_usage': 0.0,
                     'mkeventd': 'running',
                     'mknotifyd': 'running',
                     'num_hosts': '1',
                     'num_services': '48',
                     'rrdcached': 'running',
                     'stunnel': 'not existent',
                     'xinetd': 'not existent'
                 }),
        TableRow(path=['software', 'applications', 'check_mk', 'sites'],
                 key_columns={'site': 'stable'},
                 inventory_columns={
                     'autostart': False,
                     'used_version': '1.6.0-2020.08.18.cee'
                 },
                 status_columns={
                     'apache': 'running',
                     'check_helper_usage': 3.46e-321,
                     'check_mk_helper_usage': 0.377173,
                     'fetcher_helper_usage': 0.377173,
                     'checker_helper_usage': 0.377173,
                     'cmc': 'running',
                     'crontab': 'running',
                     'dcd': 'running',
                     'liveproxyd': 'running',
                     'livestatus_usage': 0.0,
                     'mkeventd': 'running',
                     'mknotifyd': 'running',
                     'num_hosts': '2',
                     'num_services': '103',
                     'rrdcached': 'running',
                     'stunnel': 'not existent',
                     'xinetd': 'not existent'
                 }),
        TableRow(path=['software', 'applications', 'check_mk', 'versions'],
                 key_columns={'version': '1.6.0-2020.08.18.cee'},
                 inventory_columns={
                     'demo': False,
                     'edition': 'cee',
                     'num_sites': 1,
                     'number': '1.6.0-2020.08.18'
                 },
                 status_columns={}),
        TableRow(path=['software', 'applications', 'check_mk', 'versions'],
                 key_columns={'version': '1.6.0p12.cee'},
                 inventory_columns={
                     'demo': False,
                     'edition': 'cee',
                     'num_sites': 0,
                     'number': '1.6.0p12'
                 },
                 status_columns={}),
        TableRow(path=['software', 'applications', 'check_mk', 'versions'],
                 key_columns={'version': '1.6.0p13.cee'},
                 inventory_columns={
                     'demo': False,
                     'edition': 'cee',
                     'num_sites': 1,
                     'number': '1.6.0p13'
                 },
                 status_columns={}),
        TableRow(path=['software', 'applications', 'check_mk', 'versions'],
                 key_columns={'version': '2020.08.13.cee'},
                 inventory_columns={
                     'demo': False,
                     'edition': 'cee',
                     'num_sites': 0,
                     'number': '2020.08.13'
                 },
                 status_columns={}),
        TableRow(path=['software', 'applications', 'check_mk', 'versions'],
                 key_columns={'version': '2020.08.20.cee'},
                 inventory_columns={
                     'demo': False,
                     'edition': 'cee',
                     'num_sites': 1,
                     'number': '2020.08.20'
                 },
                 status_columns={}),
        Attributes(path=['software', 'applications', 'check_mk'],
                   inventory_attributes={
                       'num_versions': 5,
                       'num_sites': 3
                   },
                   status_attributes={}),
    ]
