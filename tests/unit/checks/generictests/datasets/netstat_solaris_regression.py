# -*- encoding: utf-8
# yapf: disable


checkname = 'netstat'


info = [['tcp', '0', '0', '127.0.0.1.5999', '*.*', 'LISTENING'],
        ['tcp', '0', '0', '127.0.0.1.25', '*.*', 'LISTENING'],
        ['tcp', '0', '0', '127.0.0.1.587', '*.*', 'LISTENING'],
        ['udp', '*.*', '0.0.0.0:*'],
        ['udp', '*.68', '0.0.0.0:*'],
        ['udp', '*.631', '0.0.0.0:*']]


discovery = {'': []}

checks = {'': [("connections", {}, [(0, "Matching entries found: 6", [(    "connections", 6)]) ])]}
