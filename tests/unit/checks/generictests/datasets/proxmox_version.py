# -*- encoding: utf-8
# yapf: disable
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
    '': [
        (
            None, {
                u"discovered_release": u"6.1"
            }, [(0, "Version running: u'6.1', Version during discovery: u'6.1'", [])]
        )
    ]
}
