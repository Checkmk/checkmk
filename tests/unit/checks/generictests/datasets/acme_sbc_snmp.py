# yapf: disable
checkname = 'acme_sbc_snmp'

info = [
    ['20', '2'],
]

discovery = {
    '': [(None, {}),],
}

checks = {
    '': [(None, {
        'levels_lower': (99, 75)
    }, [
        (0, 'Health state: active', []),
        (2, 'Score: 20% (warn/crit at or below 99%/75%)', []),
    ]),],
}
