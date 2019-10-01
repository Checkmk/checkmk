# -*- encoding: utf-8
# yapf: disable

checkname = 'apt'

info = [
    [u'Inst base-files [9.9+deb9u9] (9.9+deb9u11 Debian:9.11/oldstable [amd64])'],
    [u'Inst ntpdate [1:4.2.6.p5+dfsg-3ubuntu2.14.04.2] (1:4.2.6.p5+dfsg-3ubuntu2.14.04.3 '
     u'Ubuntu:14.04/trusty-security [amd64])'],
    [u'Inst libsdl-image1.2 [1.2.12-5+deb9u1] (1.2.12-5+deb9u2 Debian:9.11/oldstable [amd64])'],
    [u'Inst usbutils [1:007-4+b1] (1:007-4+deb9u1 Debian:9.11/oldstable [amd64])'],
]

discovery = {'': [(None, {})]}

checks = {
    '': [(None, {'normal': 1, 'removals': 1, 'security': 2},
          [(1, '3 normal updates', [('normal_updates', 3, None, None, None, None)]),
           (2, '1 security updates (ntpdate)',
            [('security_updates', 1, None, None, None, None)])])]
}
