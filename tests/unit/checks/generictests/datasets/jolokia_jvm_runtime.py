# -*- encoding: utf-8
# yapf: disable
checkname = 'jolokia_jvm_runtime'

freeze_time = '2019-10-11 08:32:51'

info = [
    [
        u'MyJIRA', u'java.lang:type=Runtime/Uptime,Name',
        u'{"Uptime": 34502762, "Name": "1020@jira"}'
    ]
]

discovery = {'': [(u'MyJIRA', {})]}

checks = {
    '': [
        (
            u'MyJIRA', {}, [
                (
                    0, 'Up since Fri Sep  7 02:26:49 2018 (399d 08:06:02)', [
                        ('uptime', 34502762, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
