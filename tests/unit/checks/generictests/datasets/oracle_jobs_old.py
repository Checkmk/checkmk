# -*- encoding: utf-8
# yapf: disable
checkname = 'oracle_jobs'

info = [
    [
        'DB1', 'SYS', 'BSLN_MAINTAIN_STATS_JOB', 'SCHEDULED', '1', '421',
        'TRUE', '09.12.19 00:00:00,000000 +02:00', 'BSLN_MAINTAIN_STATS_SCHED',
        'SUCCEEDED'
    ]
]

discovery = {'': [('DB1.SYS.BSLN_MAINTAIN_STATS_JOB', {})]}

checks = {
    '': [
        (
            'DB1.SYS.BSLN_MAINTAIN_STATS_JOB', {
                'disabled': True,
                'missingjob': 3,
                'missinglog': 1
            }, [
                (
                    0,
                    'Job-State: SCHEDULED, Enabled: Yes, Last Duration: 1.00 s, Next Run: 09.12.19 00:00:00,000000 +02:00, Last Run Status: SUCCEEDED (ignored disabled Job)',
                    [('duration', 1, None, None, None, None)]
                )
            ]
        )
    ]
}
