import pytest  # type:ignore
import collections
from cmk_base.check_api import MKGeneralException

pytestmark = pytest.mark.checks

UnitEntry = collections.namedtuple("UnitEntry",
                                   ['name', 'type', 'load', 'active', 'sub', 'description'])


@pytest.mark.parametrize('services, blacklist, expected', [
    ([
        UnitEntry(
            name=u'gpu-manager',
            type='service',
            load=u'loaded',
            active=u'inactive',
            sub=u'dead',
            description=u'Detect the available GPUs and deal with any system changes'),
        UnitEntry(
            name=u'rsyslog',
            type='service',
            load=u'loaded',
            active=u'active',
            sub=u'running',
            description=u'System Logging Service'),
        UnitEntry(
            name=u'alsa-state',
            type='service',
            load=u'loaded',
            active=u'inactive',
            sub=u'dead',
            description=u'Manage Sound Card State (restore and store)')
    ], [], ([
        UnitEntry(
            name=u'gpu-manager',
            type='service',
            load=u'loaded',
            active=u'inactive',
            sub=u'dead',
            description=u'Detect the available GPUs and deal with any system changes'),
        UnitEntry(
            name=u'rsyslog',
            type='service',
            load=u'loaded',
            active=u'active',
            sub=u'running',
            description=u'System Logging Service'),
        UnitEntry(
            name=u'alsa-state',
            type='service',
            load=u'loaded',
            active=u'inactive',
            sub=u'dead',
            description=u'Manage Sound Card State (restore and store)')
    ], [])),
    ([
        UnitEntry(
            name=u'gpu-manager',
            type='service',
            load=u'loaded',
            active=u'inactive',
            sub=u'dead',
            description=u'Detect the available GPUs and deal with any system changes'),
        UnitEntry(
            name=u'rsyslog',
            type='service',
            load=u'loaded',
            active=u'active',
            sub=u'running',
            description=u'System Logging Service'),
        UnitEntry(
            name=u'alsa-state',
            type='service',
            load=u'loaded',
            active=u'inactive',
            sub=u'dead',
            description=u'Manage Sound Card State (restore and store)')
    ], [u'gpu'], ([
        UnitEntry(
            name=u'rsyslog',
            type='service',
            load=u'loaded',
            active=u'active',
            sub=u'running',
            description=u'System Logging Service'),
        UnitEntry(
            name=u'alsa-state',
            type='service',
            load=u'loaded',
            active=u'inactive',
            sub=u'dead',
            description=u'Manage Sound Card State (restore and store)')
    ], [
        UnitEntry(
            name=u'gpu-manager',
            type='service',
            load=u'loaded',
            active=u'inactive',
            sub=u'dead',
            description=u'Detect the available GPUs and deal with any system changes')
    ])),
])
def test_services_split(check_manager, services, blacklist, expected):
    check = check_manager.get_check('systemd_units')
    services_split = check.context['services_split']
    actual = services_split(services, blacklist)
    assert actual == expected
