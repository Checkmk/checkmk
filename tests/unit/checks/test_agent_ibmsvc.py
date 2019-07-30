import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize('params,expected_args', [
    ({
        'infos': [
            'lshost', 'lslicense', 'lsmdisk', 'lsmdiskgrp', 'lsnode', 'lsnodestats', 'lssystem',
            'lssystemstats', 'lsportfc', 'lsenclosure', 'lsenclosurestats', 'lsarray', 'disks'
        ],
        'user': 'user',
        'accept-any-hostkey': True
    }, [
        "-u", "user", "--accept-any-hostkey", "-i",
        "lshost,lslicense,lsmdisk,lsmdiskgrp,lsnode,lsnodestats,lssystem,lssystemstats,lsportfc,lsenclosure,lsenclosurestats,lsarray,disks",
        "address"
    ]),
    ({
        'infos': [
            'lshost', 'lslicense', 'lsmdisk', 'lsmdiskgrp', 'lsnode', 'lsnodestats', 'lssystem',
            'lssystemstats', 'lsportfc', 'lsenclosure', 'lsenclosurestats', 'lsarray', 'disks'
        ],
        'user': 'user',
        'accept-any-hostkey': False
    }, ["-u", "user", "address"]),
])
def test_ibmsvc_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    agent = check_manager.get_special_agent('agent_ibmsvc')
    arguments = agent.argument_func(params, "host", "address")
    assert arguments == expected_args
