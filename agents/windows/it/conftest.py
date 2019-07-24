#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset: 4 -*-
import glob
import os
import subprocess
import sys
import pytest
from remote import (assert_subprocess, remote_ip, remotedir, remoteuser, run_subprocess, sshopts)

localdir = os.path.dirname(os.path.abspath(__file__))


def lock_cmd(subcmd):
    return [
        'ssh', sshopts,
        '%s@%s' % (remoteuser, remote_ip),
        ('cd %s' % remotedir + ' && python ./lock.py %s' % subcmd)
    ]


def lock_operation(command):
    # Copy essential sources always to remote host. This is necessary as
    # another test executor might have removed the files meanwhile.
    files = [os.path.join(localdir, f) for f in ['lock.py', 'remote.py']]
    cmds = [[
        'scp',
        sshopts,
    ] + files + ['%s@%s:%s' % (remoteuser, remote_ip, remotedir)],
            lock_cmd(command)]
    for cmd in cmds:
        assert_subprocess(cmd)


def acquire_lock():
    lock_operation('acquire')


def release_lock():
    lock_operation('release')


def scp_agent_exe():
    agents_windows_dir = os.path.dirname(localdir)
    agent_exe = os.path.join(agents_windows_dir, 'check_mk_agent-64.exe')
    cmd = ['scp', agent_exe, '%s@%s:%s' % (remoteuser, remote_ip, remotedir)]
    assert_subprocess(cmd)


def scp_tests():
    test_files = [
        os.path.abspath(t) for t in glob.glob(os.path.join(localdir, 'test_*')) +
        [os.path.join(localdir, 'remote.py')]
    ]
    cmd = ['scp'] + test_files + ['%s@%s:%s' % (remoteuser, remote_ip, remotedir)]
    assert_subprocess(cmd)


def rm_rf_testfiles():
    cmd = [
        'ssh',
        '%s@%s' % (remoteuser, remote_ip),
        ('cd %s' % remotedir + ' && del /S /F /Q * '
         '&& for /d %G in ("*") do rmdir "%~G" /Q')
    ]
    exit_code, stdout, stderr = run_subprocess(cmd)
    if stdout:
        sys.stdout.write(stdout)
    if stderr:
        sys.stderr.write(stderr)
    if exit_code != 0:
        pytest.skip(stderr)


def verify_remote_ip_reachable():
    if subprocess.call(["ping", "-c", "1", remote_ip]) != 0:
        raise Exception("Test VM %s is not reachable via ping" % remote_ip)


@pytest.fixture(scope='session', autouse=True)
def session_scope():
    verify_remote_ip_reachable()
    try:
        acquire_lock()
        scp_agent_exe()
        scp_tests()
        yield
    finally:
        release_lock()
        rm_rf_testfiles()
