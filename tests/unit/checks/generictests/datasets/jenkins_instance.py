# -*- encoding: utf-8
# yapf: disable
checkname = 'jenkins_instance'

info = [
    [
        u'{"quietingDown": false, "nodeDescription": "the master Jenkins node", "numExecutors": 10, "mode": "NORMAL", "_class": "hudson.model.Hudson", "useSecurity": true}'
    ]
]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, {}, [
                (0, u'Description: The Master Jenkins Node', []),
                (0, 'Quieting Down: no', []), (0, 'Security used: yes', [])
            ]
        )
    ]
}
