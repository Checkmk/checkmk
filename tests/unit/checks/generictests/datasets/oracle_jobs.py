# -*- encoding: utf-8
# yapf: disable
checkname = 'oracle_jobs'

info = [
    [
        'DB19', 'CDB$ROOT', 'ORACLE_OCM', 'MGMT_STATS_CONFIG_JOB', 'SCHEDULED',
        '0', '2', 'TRUE', '01-JAN-20 01.01.01.312723 AM +00:00', '-',
        'SUCCEEDED'
    ]
]

discovery = {'': [('DB19.CDB$ROOT.ORACLE_OCM.MGMT_STATS_CONFIG_JOB', {})]}

checks = {
    '': [
        (
            'DB19.CDB$ROOT.ORACLE_OCM.MGMT_STATS_CONFIG_JOB', {
                'disabled': True,
                'missingjob': 3,
                'missinglog': 1
            }, [
                (
                    0,
                    'Job-State: SCHEDULED, Enabled: Yes, Last Duration: 0.00 s, Next Run: 01-JAN-20 01.01.01.312723 AM +00:00, Last Run Status: SUCCEEDED (ignored disabled Job)',
                    [('duration', 0, None, None, None, None)]
                )
            ]
        )
    ]
}
