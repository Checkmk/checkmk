# -*- encoding: utf-8
# pylint: disable=redefined-outer-name
import imp
import os

import pytest

from testlib import cmk_path  # pylint: disable=import-error

DEFAULT_AGRS = {
    "debug": False,
    "direct": False,
    "agent": False,
    "timeout": 60,
    "port": 443,
    "hostname": None,
    "skip_placeholder_vm": False,
    "pysphere": False,
    "tracefile": None,
    "host_pwr_display": None,
    "vm_pwr_display": None,
    "snapshot_display": None,
    "vm_piggyname": "alias",
    "spaces": "underscore",
    "no_cert_check": False,
    "modules": ['hostsystem', 'virtualmachine', 'datastore', 'counters', 'licenses'],
    "host_address": 'test_host',
    "user": None,
    "secret": None,
}


@pytest.fixture(scope="module")
def agent_vsphere(request):
    """
    Fixture to inject special agent as module

    imp.load_source() has the side effect of creating a .*c file, so remove it
    before and after importing it (just to be safe).
    """
    src_path = os.path.abspath(os.path.join(cmk_path(), 'agents', 'special', 'agent_vsphere'))

    for action in ('setup', 'teardown'):
        try:
            os.remove(src_path + "c")
        except OSError:
            pass

        if action == 'setup':
            yield imp.load_source("agent_vsphere", src_path)


@pytest.mark.parametrize("argv, expected_non_default_args", [
    ([], {}),
    (['--debug'], {
        "debug": True
    }),
    (['--direct'], {
        "direct": True
    }),
    (['-D'], {
        "direct": True
    }),
    (['--agent'], {
        "agent": True
    }),
    (['-a'], {
        "agent": True
    }),
    (['--timeout', '23'], {
        "timeout": 23
    }),
    (['-t', '23'], {
        "timeout": 23
    }),
    (['--port', '80'], {
        "port": '80'
    }),
    (['-p', '80'], {
        "port": '80'
    }),
    (['--hostname', 'myHost'], {
        "hostname": 'myHost'
    }),
    (['-H', 'myHost'], {
        "hostname": 'myHost'
    }),
    (['-P'], {
        "skip_placeholder_vm": True
    }),
    (['--pysphere'], {
        "pysphere": True
    }),
    (['--tracefile', 'pathToTracefile'], {
        "tracefile": "pathToTracefile"
    }),
    (['--host_pwr_display', 'whoopdeedoo'], {
        "host_pwr_display": "whoopdeedoo"
    }),
    (['--vm_pwr_display', 'whoopdeedoo'], {
        "vm_pwr_display": "whoopdeedoo"
    }),
    (['--snapshot_display', 'whoopdeedoo'], {
        "snapshot_display": "whoopdeedoo"
    }),
    (['--vm_piggyname', 'MissPiggy'], {
        "vm_piggyname": "MissPiggy"
    }),
    (['--spaces', 'underscore'], {
        "spaces": "underscore"
    }),
    (['-S', 'cut'], {
        "spaces": "cut"
    }),
    (['--no-cert-check'], {
        "no_cert_check": True
    }),
    (['--modules', 'are,not,vectorspaces'], {
        "modules": ["are", "not", "vectorspaces"]
    }),
    (['-i', 'are,not,vectorspaces'], {
        "modules": ["are", "not", "vectorspaces"]
    }),
    (['--user', 'hi-its-me'], {
        "user": "hi-its-me"
    }),
    (['-u', 'hi-its-me'], {
        "user": "hi-its-me"
    }),
    (['--secret', 'I like listening to Folk music'], {
        "secret": "I like listening to Folk music"
    }),
    (['-s', 'I like listening to Folk music'], {
        "secret": "I like listening to Folk music"
    }),
])
def test_parse_arguments(agent_vsphere, argv, expected_non_default_args):
    args = agent_vsphere.parse_arguments(["./agent_vsphere"] + argv + ["test_host"])
    for attr in DEFAULT_AGRS:
        expected = expected_non_default_args.get(attr, DEFAULT_AGRS[attr])
        actual = getattr(args, attr)
        assert actual == expected


@pytest.mark.parametrize("invalid_argv", [
    [],
    ['--skip_placeholder_vm'],
    ['--tracefile', 'wrongly_interpreted_as_host_address'],
    ['--spaces', 'safe'],
])
def test_parse_arguments_invalid(agent_vsphere, invalid_argv):
    with pytest.raises(SystemExit):
        agent_vsphere.parse_arguments(["./agent_vsphere"] + invalid_argv)
