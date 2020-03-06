# -*- encoding: utf-8 -*-

# yapf: disable
# type: ignore

checkname = 'proxmox_version'

info = [
    [
        u'{"keyboard": "de", "release": "6.1", "repoid": "9bf06119", "version": "6.1-5"}'
    ]
]

discovery = {
    '': [
        (
            None, {
                u"discovered_release": u"6.1"
            }
        )
    ]
}

checks = {
    '': [(None, {
        u"discovered_release": u"6.1"
    }, [(0, "Version running: 6.1, Version during discovery: 6.1", [])])]
}
