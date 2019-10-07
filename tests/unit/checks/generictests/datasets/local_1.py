# yapf: disable


checkname = 'local'


info = [
    ['node_1', '0', 'Service_FOO', 'V=1', 'This', 'Check', 'is', 'OK'],
    ['node_1', '1', 'Bar_Service', '-', 'This', 'is', 'WARNING', 'and', 'has', 'no',
     'performance', 'data'],
    ['node_1', '2', 'NotGood', 'V=120;50;100;0;1000', 'A', 'critical', 'check'],
    ['node_1', 'P', 'Some_other_Service', 'value1=10;30;50|value2=20;10:20;0:50;0;100',
     'Result', 'is', 'computed', 'from', 'two', 'values'],
    ['node_1', 'P', 'This_is_OK', 'foo=18;20;50'],
    ['node_1', 'P', 'Some_yet_other_Service', 'temp=40;30;50|humidity=28;50:100;0:50;0;100'],
    ['node_2', 'P', 'Has-no-var', '-', 'This', 'has', 'no', 'variable'],
    ['node_2', 'P', 'No-Text', 'hirn=-8;-20'],
    ['rogue', 'P', 'D\'oh!', 'this is an invalid metric|isotopes=0', 'I', 'messed', 'up!'],
    ['node_1', '0', 'This_is_yay', 'foo=18;20;50;;', 'Na', 'Na', 'Na'],
]


discovery = {
    '': [
        ('Bar_Service', {}),
        ('Has-no-var', {}),
        ('No-Text', {}),
        ('NotGood', {}),
        ('Service_FOO', {}),
        ('Some_other_Service', {}),
        ('Some_yet_other_Service', {}),
        ('This_is_OK', {}),
        ('This_is_yay', {}),
        ('D\'oh!', {})
    ],
}


checks = {
    '': [
        ('Bar_Service', {}, [
            (1, 'On node node_1: This is WARNING and has no performance data', []),
        ]),
        ('Has-no-var', {}, [
            (0, 'On node node_2: This has no variable', []),
        ]),
        ('No-Text', {}, [
            (1, 'On node node_2: hirn: -8.00 (warn/crit at -20.00/inf)', [
                ('hirn', -8, -20, None, None, None),
            ]),
        ]),
        ('NotGood', {}, [
            (2, 'On node node_1: A critical check', [
                ('V', 120, 50, 100, 0, 1000),
            ]),
        ]),
        ('Service_FOO', {}, [
            (0, 'On node node_1: This Check is OK', [
                ('V', 1, None, None, None, None),
            ]),
        ]),
        ('Some_other_Service', {}, [
            (1, 'On node node_1: Result is computed from two values, value1: 10.00, value2: 20.00 (warn/crit at 20.00/50.00)', [
                ('value1', 10, 30, 50, None, None),
                ('value2', 20, 20, 50, 0, 100),
            ]),
        ]),
        ('Some_yet_other_Service', {}, [
            (1, 'On node node_1: temp: 40.00 (warn/crit at 30.00/50.00), humidity: 28.00 (warn/crit below 50.00/0.00)', [
                ('temp', 40, 30, 50, None, None),
                ('humidity', 28, 100, 50, 0, 100),
            ]),
        ]),
        ('This_is_OK', {}, [
            (0, 'On node node_1: foo: 18.00', [
                ('foo', 18, 20, 50, None, None),
            ]),
        ]),
        ('D\'oh!', {}, [
            (3, "On node rogue: Invalid performance data: 'this is an invalid metric'. Output is: I messed up!", [
                ('isotopes', 0, None, None, None, None),
            ]),
        ]),
        ('This_is_yay', {}, [
            (0, 'On node node_1: Na Na Na', [
                ('foo', 18, 20, 50, None, None),
            ]),
        ]),
    ],
}
