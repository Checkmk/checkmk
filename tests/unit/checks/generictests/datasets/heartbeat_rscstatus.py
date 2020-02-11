# -*- encoding: utf-8
# yapf: disable
checkname = 'heartbeat_rscstatus'

info = [[u'all']]

discovery = {'': [(None, {'discovered_state': u'all'})]}

checks = {
    '': [
        (None, {'discovered_state': u'all'}, [
            (0, u'Current state: all', []),
        ]),
        (None, {'discovered_state': u'local'}, [
            (2, u'Current state: all (Expected: local)', []),
        ]),
        (None, u'"all"', [
            (0, u'Current state: all', []),
        ]),
        (None, u'"local"', [
            (2, u'Current state: all (Expected: local)', []),
        ]),
    ],
}
