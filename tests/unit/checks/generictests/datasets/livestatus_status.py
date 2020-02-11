# -*- encoding: utf-8
# yapf: disable
checkname = 'livestatus_status'

freeze_time = '2019-12-24T19:00:00'

info = [
    [u'[heute]'],
    [
        u'accept_passive_host_checks', u'accept_passive_service_checks',
        u'average_latency_cmk', u'average_latency_generic',
        u'average_latency_real_time', u'cached_log_messages',
        u'check_external_commands', u'check_host_freshness',
        u'check_service_freshness', u'connections', u'connections_rate',
        u'core_pid', u'enable_event_handlers', u'enable_flap_detection',
        u'enable_notifications', u'execute_host_checks',
        u'execute_service_checks', u'external_command_buffer_max',
        u'external_command_buffer_slots', u'external_command_buffer_usage',
        u'external_commands', u'external_commands_rate', u'forks',
        u'forks_rate', u'has_event_handlers', u'helper_usage_cmk',
        u'helper_usage_generic', u'helper_usage_real_time', u'host_checks',
        u'host_checks_rate', u'interval_length', u'last_command_check',
        u'last_log_rotation', u'livechecks', u'livechecks_rate',
        u'livestatus_active_connections', u'livestatus_overflows',
        u'livestatus_overflows_rate', u'livestatus_queued_connections',
        u'livestatus_threads', u'livestatus_usage', u'livestatus_version',
        u'log_messages', u'log_messages_rate', u'mk_inventory_last',
        u'nagios_pid', u'neb_callbacks', u'neb_callbacks_rate', u'num_hosts',
        u'num_queued_alerts', u'num_queued_notifications', u'num_services',
        u'obsess_over_hosts', u'obsess_over_services',
        u'process_performance_data', u'program_start', u'program_version',
        u'requests', u'requests_rate', u'service_checks',
        u'service_checks_rate'
    ],
    [
        u'1', u'1', u'7.95', u'0', u'0', u'419', u'1', u'1', u'1', u'133',
        u'0.0713417', u'13720', u'1', u'1', u'1', u'1', u'1', u'1', u'0', u'0',
        u'4', u'3.21734e-39', u'0', u'0', u'0', u'0.00883692', u'0', u'0',
        u'4238', u'1.60605', u'60', u'0', u'1565177516', u'29', u'0.0512264',
        u'1', u'0', u'0', u'0', u'20', u'7.32431e-48', u'2019.08.07', u'93',
        u'0.000153006', u'1565177522', u'13720', u'0', u'0', u'1', u'0', u'0',
        u'44', u'0', u'0', u'1', u'1565245696', u'Check_MK 2019.08.07', u'335',
        u'0.0713417', u'1217', u'2.16815'
    ]
]

discovery = {'': [(u'heute', {})]}

checks = {
    '': [
        (
            u'heute', {
                'livestatus_overflows_rate': (0.01, 0.02),
                'helper_usage_generic': (60.0, 90.0),
                'accept_passive_service_checks': 2,
                'livestatus_usage': (80.0, 90.0),
                'process_performance_data': 1,
                'check_external_commands': 2,
                'execute_host_checks': 2,
                'check_service_freshness': 1,
                'site_stopped': 2,
                'helper_usage_cmk': (0.1, 90.0),
                'accept_passive_host_checks': 2,
                'enable_flap_detection': 1,
                'check_host_freshness': 0,
                'site_cert_days': (30, 7),
                'average_latency_cmk': (3, 6),
                'enable_event_handlers': 1,
                'average_latency_generic': (30, 60),
                'enable_notifications': 2,
                'execute_service_checks': 2
            }, [
                (
                    0, 'HostChecks: 0.0/s', [
                        ('host_checks', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'ServiceChecks: 0.0/s', [
                        ('service_checks', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'ProcessCreations: 0.0/s', [
                        ('forks', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'LivestatusConnects: 0.0/s', [
                        ('connections', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'LivestatusRequests: 0.0/s', [
                        ('requests', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'LogMessages: 0.0/s', [
                        ('log_messages', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Average check latency: 0.000s',
                    [('average_latency_generic', 0.0, 30.0, 60.0, None, None)]
                ),
                (
                    2,
                    'Average Check_MK latency: 7.950s (warn/crit at 3.000s/6.000s)',
                    [('average_latency_cmk', 7.95, 3.0, 6.0, None, None)]
                ),
                (
                    0, 'Check helper usage: 0%', [
                        ('helper_usage_generic', 0.0, 60.0, 90.0, None, None)
                    ]
                ),
                (
                    1,
                    'Check_MK helper usage: 0.88% (warn/crit at 0.1%/90.0%)', [
                        ('helper_usage_cmk', 0.883692, 0.1, 90.0, None, None)
                    ]
                ),
                (
                    0, 'Livestatus usage: 0%', [
                        (
                            'livestatus_usage', 7.32431e-46, 80.0, 90.0, None,
                            None
                        )
                    ]
                ),
                (
                    0, 'Livestatus overflow rate: 0.0/s', [
                        (
                            'livestatus_overflows_rate', 0.0, 0.01, 0.02, None,
                            None
                        )
                    ]
                ),
                (
                    0, '1 Hosts', [
                        ('monitored_hosts', 1, None, None, None, None)
                    ]
                ),
                (
                    0, '44 Services', [
                        ('monitored_services', 44, None, None, None, None)
                    ]
                ), (0, u'Core version: Check_MK 2019.08.07', []),
                (0, u'Livestatus version: 2019.08.07', [])
            ]
        ),
        (
            u'heute', {
                'site_stopped': 2,
                'process_performance_data': 1,
                'average_latency_cmk': (30, 60),
                'check_service_freshness': 1,
                'helper_usage_cmk': (60.0, 90.0),
                'enable_flap_detection': 1,
                'check_host_freshness': 0,
                'site_cert_days': (30, 7),
                'accept_passive_service_checks': 2,
                'average_latency_generic': (30, 60),
                'helper_usage_generic': (60.0, 90.0),
                'livestatus_usage': (80.0, 90.0),
                'check_external_commands': 2,
                'execute_host_checks': 2,
                'accept_passive_host_checks': 2,
                'livestatus_overflows_rate': (0.01, 0.02),
                'enable_event_handlers': 1,
                'enable_notifications': 2,
                'execute_service_checks': 2
            }, [
                (
                    0, 'HostChecks: 0.0/s', [
                        ('host_checks', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'ServiceChecks: 0.0/s', [
                        ('service_checks', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'ProcessCreations: 0.0/s', [
                        ('forks', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'LivestatusConnects: 0.0/s', [
                        ('connections', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'LivestatusRequests: 0.0/s', [
                        ('requests', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'LogMessages: 0.0/s', [
                        ('log_messages', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Average check latency: 0.000s',
                    [('average_latency_generic', 0.0, 30.0, 60.0, None, None)]
                ),
                (
                    0, 'Average Check_MK latency: 7.950s', [
                        ('average_latency_cmk', 7.95, 30.0, 60.0, None, None)
                    ]
                ),
                (
                    0, 'Check helper usage: 0%', [
                        ('helper_usage_generic', 0.0, 60.0, 90.0, None, None)
                    ]
                ),
                (
                    0, 'Check_MK helper usage: 0.88%', [
                        ('helper_usage_cmk', 0.883692, 60.0, 90.0, None, None)
                    ]
                ),
                (
                    0, 'Livestatus usage: 0%', [
                        (
                            'livestatus_usage', 7.32431e-46, 80.0, 90.0, None,
                            None
                        )
                    ]
                ),
                (
                    0, 'Livestatus overflow rate: 0.0/s', [
                        (
                            'livestatus_overflows_rate', 0.0, 0.01, 0.02, None,
                            None
                        )
                    ]
                ),
                (
                    0, '1 Hosts', [
                        ('monitored_hosts', 1, None, None, None, None)
                    ]
                ),
                (
                    0, '44 Services', [
                        ('monitored_services', 44, None, None, None, None)
                    ]
                ), (0, u'Core version: Check_MK 2019.08.07', []),
                (0, u'Livestatus version: 2019.08.07', [])
            ]
        )
    ]
}

extra_sections = {
    '': [
        [
            [u'[azure_test]'],
            [u'/omd/sites/azure_test/etc/ssl/ca.pem', u'33068342059'],
            [
                u'/omd/sites/azure_test/etc/ssl/sites/azure_test.pem',
                u'33068342059'
            ], [u'[beta]'],
            [u'/omd/sites/beta/etc/ssl/ca.pem', u'33066708720'],
            [u'/omd/sites/beta/etc/ssl/sites/beta.pem', u'33066708720'],
            [u'[heute]'], [u'/omd/sites/heute/etc/ssl/ca.pem', u''],
            [u'/omd/sites/heute/etc/ssl/sites/heute.pem',
             u''], [u'[stable14]'], [u'[stable15]']
        ]
    ]
}
