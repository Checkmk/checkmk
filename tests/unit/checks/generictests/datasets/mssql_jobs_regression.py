#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'mssql_jobs'

info = [
    ['MSSQLSERVER',],
    [
        '{CB09DA64-FBBD-46A0-9CD4-02D609249DE4}',
        'täglich 00:03', '1', '20200929', '300', '1',
        'The job succeeded.  The Job was invoked by Schedule 55 (täglich 00:03).  The last step to run was step 2 (Tagesstatistik Listentool).',
        '20200928', '300', '35', '1', '2020-09-28 15:37:36'
    ],
    [
        '{DD63E68D-61FF-42CB-9986-0B00276611EE}', '4x Täglich Infomanagement',
        '1', '20200929', '63333', '1',
        'The job succeeded.  The Job was invoked by Schedule 126 (4x Täglich ab 06:30 Uhr).  The last step to run was step 1 (auto_importAll).',
        '20200928', '123333', '745', '1', '2020-09-28 15:37:36'
    ],
    [
        '{E185714E-1231-4A02-88E5-21D521DE6A61}', 'Wartung Stündlich', '1',
        '20200928', '161500', '0',
        'The job failed.  JobManager tried to run a non-existent step (3) for job Wartung Stündlich.',
        '20200928', '151500', '9', '1', '2020-09-28 15:37:36'
    ],
    [
        '{76F94409-DDB4-4F9B-9AE2-3AF23AF46C48}', '1x Täglich', '1',
        '20200929', '32000', '1',
        'The job succeeded.  The Job was invoked by Schedule 43 (Mo-Sa 03:20).  The last step to run was step 18 (Abgleich MAV).',
        '20200928', '32000', '10806', '1', '2020-09-28 15:37:36'
    ],
    [
        '{4B9D1121-FDEF-4CA5-A202-4ED8B0421230}', 'aller 2h', '1', '20200928',
        '170500', '1',
        'The job succeeded.  The Job was invoked by Schedule 48 (Mo-Sa 07:00 aller 2h).  The last step to run was step 2 (Magicinfo_Device_IP).',
        '20200928', '150501', '1245', '1', '2020-09-28 15:37:36'
    ],
    [
        '{11E5BEA3-6925-45F7-B67B-5B954F11153A}', 'Wartung Täglich', '1',
        '20200929', '14500', '0',
        'The job failed.  JobManager tried to run a non-existent step (3) for job Wartung Täglich.',
        '20200928', '14500', '341', '1', '2020-09-28 15:37:36'
    ],
    [
        '{783F8CB4-A09A-409A-BFBF-6822589DFA50}', '1x Täglich 6:00 Uhr', '1',
        '20200929', '60101', '1',
        'The job succeeded.  The Job was invoked by Schedule 84 (Mo-So 6:00 Uhr).  The last step to run was step 2 (C2C_Export_OptIn).',
        '20200928', '60101', '43', '1', '2020-09-28 15:37:36'
    ],
    [
        '{A58A7683-E8CF-446B-AED7-6A60D8E29FE0}', '1x Täglich Infomanagement',
        '1', '20200929', '21700', '1',
        'The job succeeded.  The Job was invoked by Schedule 61 (Mo-So 02:17).  The last step to run was step 1 (Quali AUTO MAIN).',
        '20200928', '21700', '3628', '1', '2020-09-28 15:37:36'
    ],
    [
        '{32267254-2240-474F-92D1-806FDBBC036E}', 'Sonntag', '1', '20201004',
        '73400', '1',
        'The job succeeded.  The Job was invoked by Schedule 60 (Sonntag).  The last step to run was step 1 (LdapImportActiveDirectory).',
        '20200927', '73400', '134', '1', '2020-09-28 15:37:36'
    ],
    [
        '{03013FF0-175C-4492-9C03-89AD3A05926C}',
        'SSIS Server Maintenance Job', '1', '20200929', '0', '1',
        'The job succeeded.  The Job was invoked by Schedule 10 (SSISDB Scheduler).  The last step to run was step 2 (SSIS Server Max Version Per Project Maintenance).',
        '20200928', '0', '2', '0', '2020-09-28 15:37:36'
    ],
    [
        '{000B84B2-F29F-422A-8C89-BFE84696918F}', 'aller 1h', '1', '20200928',
        '153500', '1',
        'The job succeeded.  The Job was invoked by Schedule 47 (Mo-Sa 05:30 aller 1h).  The last step to run was step 4 (Outbound IBI/PIC).',
        '20200928', '153500', '45', '1', '2020-09-28 15:37:36'
    ],
    [
        '{FD3904A7-A6A3-48A2-B5C7-C6AFAE646966}', '1 x täglich 01:00 Uhr', '1',
        '20200929', '10000', '1',
        'The job succeeded.  The Job was invoked by Schedule 261 (täglich 01:00 Uhr).  The last step to run was step 2 (C2C Import AIC).',
        '20200928', '10000', '43', '1', '2020-09-28 15:37:36'
    ],
    [
        '{99B511D3-A808-4B50-8C57-C962B4E5DA55}', '1x täglich ttCall', '0',
        '20200929', '53000', '1',
        'The job succeeded.  The Job was invoked by Schedule 173 (ttCall).  The last step to run was step 1 (Projekt Vorausverfügung-Veraltete Daten disablen).',
        '20200928', '53000', '1', '1', '2020-09-28 15:37:36'
    ],
    [
        '{C31ED308-A554-40A0-B10A-CB06988FEDA5}', 'aller 15 min', '1',
        '20200928', '153005', '1',
        'The job succeeded.  The Job was invoked by Schedule 77 (CMS Import).  The last step to run was step 1 (CMS Intervall Import).',
        '20200928', '153005', '34', '1', '2020-09-28 15:37:36'
    ],
    [
        '{54DBA242-E5AA-4A45-8ABB-D166C1493170}', 'aller 5 min', '1',
        '20200928', '152934', '1',
        'The job succeeded.  The Job was invoked by Schedule 255 (aller 5 min in GZ).  The last step to run was step 1 (CMS hagent).',
        '20200928', '153434', '6', '1', '2020-09-28 15:37:36'
    ],
    [
        '{BFFB963B-332C-4EE1-AF06-EC8D8C2796DD}', 'SSRS BO-Tool Report DL',
        '1', '20200928', '175600', '1',
        'The job succeeded.  The Job was invoked by Schedule 81 (Mo-So 15 Uhr).  The last step to run was step 1 (SSRS BO-Tool Report DL).',
        '20200928', '145600', '0', '1', '2020-09-28 15:37:36'
    ],
    [
        '{BFFB963B-332C-4EE1-AF06-EC8D8C2796DD}', 'SSRS BO-Tool Report DL',
        '1', '20200928', '195600', '1',
        'The job succeeded.  The Job was invoked by Schedule 81 (Mo-So 15 Uhr).  The last step to run was step 1 (SSRS BO-Tool Report DL).',
        '20200928', '145600', '0', '1', '2020-09-28 15:37:36'
    ],
    [
        '{BFFB963B-332C-4EE1-AF06-EC8D8C2796DD}', 'SSRS BO-Tool Report DL',
        '1', '20200928', '215600', '1',
        'The job succeeded.  The Job was invoked by Schedule 81 (Mo-So 15 Uhr).  The last step to run was step 1 (SSRS BO-Tool Report DL).',
        '20200928', '145600', '0', '1', '2020-09-28 15:37:36'
    ],
    [
        '{BFFB963B-332C-4EE1-AF06-EC8D8C2796DD}', 'SSRS BO-Tool Report DL',
        '1', '20200929', '115600', '1',
        'The job succeeded.  The Job was invoked by Schedule 81 (Mo-So 15 Uhr).  The last step to run was step 1 (SSRS BO-Tool Report DL).',
        '20200928', '145600', '0', '1', '2020-09-28 15:37:36'
    ],
    [
        '{BFFB963B-332C-4EE1-AF06-EC8D8C2796DD}', 'SSRS BO-Tool Report DL',
        '1', '20200929', '145600', '1',
        'The job succeeded.  The Job was invoked by Schedule 81 (Mo-So 15 Uhr).  The last step to run was step 1 (SSRS BO-Tool Report DL).',
        '20200928', '145600', '0', '1', '2020-09-28 15:37:36'
    ],
    [
        '{3E0CEFB9-DCCD-43E7-BF86-F1406AB5E318}', 'SSRS AIC Report DL', '1',
        '20200928', '160000', '1',
        'The job succeeded.  The Job was invoked by Schedule 16 (Mo-So 07-23 Uhr).  The last step to run was step 1 (SSRS AIC Report DL).',
        '20200928', '150000', '0', '1', '2020-09-28 15:37:36'
    ],
    [
        '{35572CF3-551F-4216-84E7-FCEC2A2FE508}', '14 Uhr', '1', '20200929',
        '140500', '1',
        'The job succeeded.  The Job was invoked by Schedule 46 (Mo-So 14:00).  The last step to run was step 2 (Aktivitaeten).',
        '20200928', '140500', '758', '1', '2020-09-28 15:37:36'
    ]
]

discovery = {
    '': [
        ('täglich 00:03', {}),
        ('1 x täglich 01:00 Uhr', {}),
        ('14 Uhr', {}),
        ('1x Täglich 6:00 Uhr', {}),
        ('1x Täglich Infomanagement', {}),
        ('1x Täglich', {}),
        ('1x täglich ttCall', {}),
        ('4x Täglich Infomanagement', {}),
        ('SSIS Server Maintenance Job', {}),
        ('SSRS AIC Report DL', {}),
        ('SSRS BO-Tool Report DL', {}),
        ('Sonntag', {}),
        ('Wartung Stündlich', {}),
        ('Wartung Täglich', {}),
        ('aller 15 min', {}),
        ('aller 1h', {}),
        ('aller 2h', {}),
        ('aller 5 min', {}),
    ]
}

checks = {
    '': [
        (
            'täglich 00:03', {
                'consider_job_status': 'ignore',
                'status_disabled_jobs': 0,
                'status_missing_jobs': 2,
                'run_duration': (1800, 2400)
            }, [
                (
                    0, 'Last duration: 35.0 s',
                    [('database_job_duration', 35.0, 1800.0, 2400.0, None, None)]
                ), (0, 'MSSQL status: Succeed', []),
                (0, 'Last run: 2020-09-28 00:03:00', []),
                (0, 'Next run: 2020-09-29 00:03:00', []),
                (
                    0,
                    '\nOutcome message: The job succeeded.  The Job was invoked by Schedule 55 (täglich 00:03).  The last step to run was step 2 (Tagesstatistik Listentool).',
                    []
                )
            ]
        ),
        (
            '1 x täglich 01:00 Uhr', {
                'consider_job_status': 'ignore',
                'status_disabled_jobs': 0,
                'status_missing_jobs': 2,
                'run_duration': (1800, 2400)
            }, [
                (
                    0, 'Last duration: 43.0 s',
                    [('database_job_duration', 43.0, 1800.0, 2400.0, None, None)]
                ), (0, 'MSSQL status: Succeed', []),
                (0, 'Last run: 2020-09-28 01:00:00', []),
                (0, 'Next run: 2020-09-29 01:00:00', []),
                (
                    0,
                    '\nOutcome message: The job succeeded.  The Job was invoked by Schedule 261 (täglich 01:00 Uhr).  The last step to run was step 2 (C2C Import AIC).',
                    []
                )
            ]
        ),
        (
            '14 Uhr', {
                'consider_job_status': 'ignore',
                'status_disabled_jobs': 0,
                'status_missing_jobs': 2,
                'run_duration': (1800, 2400)
            }, [
                (
                    0, 'Last duration: 7 m',
                    [('database_job_duration', 478.0, 1800.0, 2400.0, None, None)]
                ), (0, 'MSSQL status: Succeed', []),
                (0, 'Last run: 2020-09-28 14:05:00', []),
                (0, 'Next run: 2020-09-29 14:05:00', []),
                (
                    0,
                    '\nOutcome message: The job succeeded.  The Job was invoked by Schedule 46 (Mo-So 14:00).  The last step to run was step 2 (Aktivitaeten).',
                    []
                )
            ]
        ),
        (
            '1x Täglich 6:00 Uhr', {
                'consider_job_status': 'ignore',
                'status_disabled_jobs': 0,
                'status_missing_jobs': 2,
                'run_duration': (1800, 2400)
            }, [
                (
                    0, 'Last duration: 43.0 s',
                    [('database_job_duration', 43.0, 1800.0, 2400.0, None, None)]
                ), (0, 'MSSQL status: Succeed', []),
                (0, 'Last run: 2020-09-28 06:01:01', []),
                (0, 'Next run: 2020-09-29 06:01:01', []),
                (
                    0,
                    '\nOutcome message: The job succeeded.  The Job was invoked by Schedule 84 (Mo-So 6:00 Uhr).  The last step to run was step 2 (C2C_Export_OptIn).',
                    []
                )
            ]
        ),
        (
            '1x Täglich Infomanagement', {
                'consider_job_status': 'ignore',
                'status_disabled_jobs': 0,
                'status_missing_jobs': 2,
                'run_duration': (1800, 2400)
            }, [
                (
                    1, 'Last duration: 36 m (warn/crit at 30 m/40 m)', [
                        (
                            'database_job_duration', 2188.0, 1800.0, 2400.0, None,
                            None
                        )
                    ]
                ), (0, 'MSSQL status: Succeed', []),
                (0, 'Last run: 2020-09-28 02:17:00', []),
                (0, 'Next run: 2020-09-29 02:17:00', []),
                (
                    0,
                    '\nOutcome message: The job succeeded.  The Job was invoked by Schedule 61 (Mo-So 02:17).  The last step to run was step 1 (Quali AUTO MAIN).',
                    []
                )
            ]
        ),
        (
            '1x Täglich', {
                'consider_job_status': 'ignore',
                'status_disabled_jobs': 0,
                'status_missing_jobs': 2,
                'run_duration': (1800, 2400)
            }, [
                (
                    2, 'Last duration: 68 m (warn/crit at 30 m/40 m)', [
                        (
                            'database_job_duration', 4086.0, 1800.0, 2400.0, None,
                            None
                        )
                    ]
                ), (0, 'MSSQL status: Succeed', []),
                (0, 'Last run: 2020-09-28 03:20:00', []),
                (0, 'Next run: 2020-09-29 03:20:00', []),
                (
                    0,
                    '\nOutcome message: The job succeeded.  The Job was invoked by Schedule 43 (Mo-Sa 03:20).  The last step to run was step 18 (Abgleich MAV).',
                    []
                )
            ]
        ),
        (
            '1x täglich ttCall', {
                'consider_job_status': 'ignore',
                'status_disabled_jobs': 2,
                'status_missing_jobs': 2,
                'run_duration': (1800, 2400)
            }, [
                (
                    0, 'Last duration: 1.00 s', [
                        ('database_job_duration', 1.0, 1800.0, 2400.0, None, None)
                    ]
                ), (0, 'MSSQL status: Succeed', []),
                (0, 'Last run: 2020-09-28 05:30:00', []),
                (2, 'Job is disabled', []),
                (
                    0,
                    '\nOutcome message: The job succeeded.  The Job was invoked by Schedule 173 (ttCall).  The last step to run was step 1 (Projekt Vorausverfügung-Veraltete Daten disablen).',
                    []
                )
            ]
        ),
        (
            '4x Täglich Infomanagement', {
                'consider_job_status': 'ignore',
                'status_disabled_jobs': 0,
                'status_missing_jobs': 2,
                'run_duration': (1800, 2400)
            }, [
                (
                    0, 'Last duration: 7 m',
                    [('database_job_duration', 465.0, 1800.0, 2400.0, None, None)]
                ), (0, 'MSSQL status: Succeed', []),
                (0, 'Last run: 2020-09-28 12:33:33', []),
                (0, 'Next run: 2020-09-29 06:33:33', []),
                (
                    0,
                    '\nOutcome message: The job succeeded.  The Job was invoked by Schedule 126 (4x Täglich ab 06:30 Uhr).  The last step to run was step 1 (auto_importAll).',
                    []
                )
            ]
        ),
        (
            'SSIS Server Maintenance Job', {
                'consider_job_status': 'ignore',
                'status_disabled_jobs': 1,
                'status_missing_jobs': 2,
                'run_duration': (1800, 2400)
            }, [
                (
                    0, 'Last duration: 2.00 s', [
                        ('database_job_duration', 2.0, 1800.0, 2400.0, None, None)
                    ]
                ), (0, 'MSSQL status: Succeed', []),
                (0, 'Last run: 2020-09-28 00:00:00', []),
                (1, 'Schedule is disabled', []),
                (
                    0,
                    '\nOutcome message: The job succeeded.  The Job was invoked by Schedule 10 (SSISDB Scheduler).  The last step to run was step 2 (SSIS Server Max Version Per Project Maintenance).',
                    []
                )
            ]
        ),
        (
            'SSRS AIC Report DL', {
                'consider_job_status': 'ignore',
                'status_disabled_jobs': 0,
                'status_missing_jobs': 2,
                'run_duration': (1800, 2400)
            }, [
                (
                    0, 'Last duration: 0.00 s', [
                        ('database_job_duration', 0.0, 1800.0, 2400.0, None, None)
                    ]
                ), (0, 'MSSQL status: Succeed', []),
                (0, 'Last run: 2020-09-28 15:00:00', []),
                (0, 'Next run: 2020-09-28 16:00:00', []),
                (
                    0,
                    '\nOutcome message: The job succeeded.  The Job was invoked by Schedule 16 (Mo-So 07-23 Uhr).  The last step to run was step 1 (SSRS AIC Report DL).',
                    []
                )
            ]
        ),
        (
            'SSRS BO-Tool Report DL', {
                'consider_job_status': 'ignore',
                'status_disabled_jobs': 0,
                'status_missing_jobs': 2,
                'run_duration': (1800, 2400)
            }, [
                (
                    0, 'Last duration: 0.00 s', [
                        ('database_job_duration', 0.0, 1800.0, 2400.0, None, None)
                    ]
                ), (0, 'MSSQL status: Succeed', []),
                (0, 'Last run: 2020-09-28 14:56:00', []),
                (0, 'Next run: 2020-09-28 17:56:00', []),
                (
                    0,
                    '\nOutcome message: The job succeeded.  The Job was invoked by Schedule 81 (Mo-So 15 Uhr).  The last step to run was step 1 (SSRS BO-Tool Report DL).',
                    []
                )
            ]
        ),
        (
            'Sonntag', {
                'consider_job_status': 'ignore',
                'status_disabled_jobs': 0,
                'status_missing_jobs': 2,
                'run_duration': (1800, 2400)
            }, [
                (
                    0, 'Last duration: 94 s',
                    [('database_job_duration', 94.0, 1800.0, 2400.0, None, None)]
                ), (0, 'MSSQL status: Succeed', []),
                (0, 'Last run: 2020-09-27 07:34:00', []),
                (0, 'Next run: 2020-10-04 07:34:00', []),
                (
                    0,
                    '\nOutcome message: The job succeeded.  The Job was invoked by Schedule 60 (Sonntag).  The last step to run was step 1 (LdapImportActiveDirectory).',
                    []
                )
            ]
        ),
        (
            'Wartung Stündlich', {
                'consider_job_status': 'consider',
                'status_disabled_jobs': 0,
                'status_missing_jobs': 2,
                'run_duration': (1800, 2400)
            }, [
                (
                    0, 'Last duration: 9.00 s', [
                        ('database_job_duration', 9.0, 1800.0, 2400.0, None, None)
                    ]
                ), (2, 'MSSQL status: Fail', []),
                (0, 'Last run: 2020-09-28 15:15:00', []),
                (0, 'Next run: 2020-09-28 16:15:00', []),
                (
                    0,
                    '\nOutcome message: The job failed.  JobManager tried to run a non-existent step (3) for job Wartung Stündlich.',
                    []
                )
            ]
        ),
        (
            'Wartung Täglich', {
                'consider_job_status': 'ignore',
                'status_disabled_jobs': 0,
                'status_missing_jobs': 2,
                'run_duration': (1800, 2400)
            }, [
                (
                    0, 'Last duration: 221 s',
                    [('database_job_duration', 221.0, 1800.0, 2400.0, None, None)]
                ), (0, 'MSSQL status: Fail', []),
                (0, 'Last run: 2020-09-28 01:45:00', []),
                (0, 'Next run: 2020-09-29 01:45:00', []),
                (
                    0,
                    '\nOutcome message: The job failed.  JobManager tried to run a non-existent step (3) for job Wartung Täglich.',
                    []
                )
            ]
        ),
        (
            'aller 15 min', {
                'consider_job_status': 'ignore',
                'status_disabled_jobs': 0,
                'status_missing_jobs': 2,
                'run_duration': (1800, 2400)
            }, [
                (
                    0, 'Last duration: 34.0 s',
                    [('database_job_duration', 34.0, 1800.0, 2400.0, None, None)]
                ), (0, 'MSSQL status: Succeed', []),
                (0, 'Last run: 2020-09-28 15:30:05', []),
                (0, 'Next run: 2020-09-28 15:30:05', []),
                (
                    0,
                    '\nOutcome message: The job succeeded.  The Job was invoked by Schedule 77 (CMS Import).  The last step to run was step 1 (CMS Intervall Import).',
                    []
                )
            ]
        ),
        (
            'aller 1h', {
                'consider_job_status': 'ignore',
                'status_disabled_jobs': 0,
                'status_missing_jobs': 2,
                'run_duration': (1800, 2400)
            }, [
                (
                    0, 'Last duration: 45.0 s',
                    [('database_job_duration', 45.0, 1800.0, 2400.0, None, None)]
                ), (0, 'MSSQL status: Succeed', []),
                (0, 'Last run: 2020-09-28 15:35:00', []),
                (0, 'Next run: 2020-09-28 15:35:00', []),
                (
                    0,
                    '\nOutcome message: The job succeeded.  The Job was invoked by Schedule 47 (Mo-Sa 05:30 aller 1h).  The last step to run was step 4 (Outbound IBI/PIC).',
                    []
                )
            ]
        ),
        (
            'aller 2h', {
                'consider_job_status': 'ignore',
                'status_disabled_jobs': 0,
                'status_missing_jobs': 2,
                'run_duration': (1800, 2400)
            }, [
                (
                    0, 'Last duration: 12 m',
                    [('database_job_duration', 765.0, 1800.0, 2400.0, None, None)]
                ), (0, 'MSSQL status: Succeed', []),
                (0, 'Last run: 2020-09-28 15:05:01', []),
                (0, 'Next run: 2020-09-28 17:05:00', []),
                (
                    0,
                    '\nOutcome message: The job succeeded.  The Job was invoked by Schedule 48 (Mo-Sa 07:00 aller 2h).  The last step to run was step 2 (Magicinfo_Device_IP).',
                    []
                )
            ]
        ),
        (
            'aller 5 min', {
                'consider_job_status': 'ignore',
                'status_disabled_jobs': 0,
                'status_missing_jobs': 2,
                'run_duration': (1800, 2400)
            }, [
                (
                    0, 'Last duration: 6.00 s', [
                        ('database_job_duration', 6.0, 1800.0, 2400.0, None, None)
                    ]
                ), (0, 'MSSQL status: Succeed', []),
                (0, 'Last run: 2020-09-28 15:34:34', []),
                (0, 'Next run: 2020-09-28 15:29:34', []),
                (
                    0,
                    '\nOutcome message: The job succeeded.  The Job was invoked by Schedule 255 (aller 5 min in GZ).  The last step to run was step 1 (CMS hagent).',
                    []
                )
            ]
        )
    ]
}
