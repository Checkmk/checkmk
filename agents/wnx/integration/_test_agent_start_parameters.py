#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset: 4 -*-
try:
    # Use iter version of filter
    from future_builtins import filter
except ImportError:
    # Python 3 compatibility tweak
    pass
import os
import platform
import pytest
import re
import shutil
import subprocess
from local import (actual_output, src_agent_exe, assert_subprocess, make_ini_config, port,
                   src_exec_dir, local_test, run_subprocess, write_config)
import sys


class Globals(object):
    param = None
    builddir = 'build64'
    capfile = 'plugins.cap'
    remote_capfile = os.path.join(src_exec_dir, capfile)
    plugintype = 'plugins'
    pluginnames = ['netstat_an.bat', 'wmic_if.bat']
    binaryplugin = 'MontyPython.exe'
    sections = ['check_mk', 'fileinfo', 'logfiles', 'logwatch', plugintype]
    testfiles = ('basedir', 'monty', [('python', 'flying'), ('circus', "It's")])
    testlogs = tuple([os.path.join(src_exec_dir, l) for l in ['test1.log', 'test2.log']])
    uninstall_batch = os.path.join(src_exec_dir, 'uninstall_plugins.bat')


@pytest.fixture
def testfile():
    return os.path.basename(__file__)


@pytest.fixture
def testconfig(make_ini_config):
    make_ini_config.set('global', 'crash_debug', 'yes')
    if Globals.param[0] == 'showconfig':
        make_ini_config.set('global', 'sections', ' '.join(Globals.sections))
        for section in filter(lambda s: s != 'check_mk', Globals.sections):
            make_ini_config.add_section(section)
        make_ini_config.set('fileinfo', 'path', os.path.join(src_exec_dir, '*.log'))
        make_ini_config.set('logfiles', 'textfile', 'from_start %s|nocontext %s' % Globals.testlogs)
        make_ini_config.set('logfiles', 'crit', 'e*o?')
        make_ini_config.set('logwatch', 'vista_api', 'yes')
        make_ini_config.set('logwatch', 'logfile Application', 'warn')
        for pluginname in Globals.pluginnames:
            make_ini_config.set(Globals.plugintype, 'execution %s' % pluginname, 'async')
            make_ini_config.set(Globals.plugintype, 'timeout %s' % pluginname, '10')
            make_ini_config.set(Globals.plugintype, 'cache_age %s' % pluginname, '300')
            make_ini_config.set(Globals.plugintype, 'retry_count %s' % pluginname, '3')
    return make_ini_config


@pytest.fixture
def actual_output(request, write_config):
    if platform.system() == 'Windows':
        # Run agent and yield its output.
        try:
            save_cwd = os.getcwd()
            os.chdir(src_exec_dir)
            cmd = []
            exit_code, stdout, stderr = run_subprocess([src_agent_exe] + Globals.param)
            if stdout:
                sys.stdout.write(stdout)
            if stderr:
                sys.stderr.write(stderr)
            expected_code = 1 if Globals.param[0] == '/?' else 0
            assert expected_code == exit_code
            # Usage is written to stderr, actual cmd output to stdout.
            handle = stderr if Globals.param[0] == '/?' else stdout
            yield handle.splitlines()
        finally:
            os.chdir(save_cwd)
    else:
        # Not on Windows, test run remotely, nothing to be done.
        yield


def output_config(make_ini_config):
    output = []
    for section, options in make_ini_config._sections.iteritems():
        output.append(r'\[%s\]' % section)
        for key, values in options.iteritems():
            for value in values:
                output.append('%s = %s' % (key, value))
    return output


def output_usage():
    return [
        r'Usage: ',
        (r'check_mk_agent version         -- show version '
         r'\d+\.\d+\.\d+([bi]\d+)?(p\d+)? and exit'),
        (r'check_mk_agent install         -- install as Windows NT service '
         r'Check_Mk_Agent'), r'check_mk_agent remove          -- remove Windows NT service',
        (r'check_mk_agent adhoc           -- open TCP port %d and answer '
         r'request until killed' % port),
        (r'check_mk_agent test            -- test output of plugin, do not '
         r'open TCP port'),
        (r'check_mk_agent file FILENAME   -- write output of plugin into '
         r'file, do not open TCP port'),
        (r'check_mk_agent debug           -- similar to test, but with lots '
         r'of debug output'),
        (r'check_mk_agent showconfig      -- shows the effective '
         r'configuration used \(currently incomplete\)')
    ]


@pytest.fixture
def expected_output(request, testconfig):
    return {
        'version': [r'Check_MK_Agent version \d+\.\d+\.\d+([bi]\d+)?(p\d+)?'],
        'install': [r'Check_MK_Agent Installed Successfully'],
        'remove': [r'Check_MK_Agent Removed Successfully'],
        'showconfig': output_config(testconfig),
        'unpack': [],
        '/?': output_usage()
    }[Globals.param[0]]


def copy_capfile():
    cmd = ['scp', sshopts, Globals.capfile, '%s@%s:"%s"' % (remoteuser, remote_ip, src_exec_dir)]
    assert_subprocess(cmd)


# Pack a directory and return the byte stream of the CAP.
# Excerpt from enterprise/cmk_base/cee/cap.py
def pack(install_basedir):
    cap = ""
    old_cwd = os.path.abspath('.')
    os.chdir(install_basedir)
    for relative_dir, _unused_dirs, files in os.walk('.'):
        for filename in sorted(files):
            path = (relative_dir + '/' + filename)[2:]
            cap += _cap_entry(path)
    os.chdir(old_cwd)
    return cap


def _cap_entry(relpath):
    entry = chr(len(relpath)) + relpath
    content = file(relpath).read()
    entry += _cap_filesize(len(content)) + content
    return entry


def _cap_filesize(l):
    return chr(l & 0xff) + \
           chr(l >> 8 & 0xff) + \
           chr(l >> 16 & 0xff) + \
           chr(l >> 24 & 0xff)


def pack_plugins(script):
    basedir, directory, plugins = Globals.testfiles
    plugindir = os.path.join(basedir, directory)
    # Clear possible leftovers from previous interrupted / failed tests:
    if os.path.exists(plugindir):
        shutil.rmtree(plugindir)
    os.makedirs(plugindir)
    if script:
        for pluginname, content in plugins:
            with open(os.path.join(plugindir, pluginname), 'w') as outfile:
                outfile.write(content)
    else:
        source = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              Globals.builddir, Globals.binaryplugin)
        shutil.copy(source, plugindir)

    with open(Globals.capfile, 'wb') as capfile:
        capfile.write(pack(basedir))
    shutil.rmtree(basedir)


def run_uninstall_plugins():
    if os.path.isfile(Globals.uninstall_batch):
        cmd = [Globals.uninstall_batch]
        exit_code, stdout, stderr = run_subprocess(cmd)
        if stdout:
            sys.stdout.write(stdout)
        if stderr:
            sys.stderr.write(stderr)


@pytest.fixture(
    # Note: param 'adhoc' is tested in all section tests
    #       params 'test' and 'debug' are tested in section check_mk tests
    params=[['version'], ['install'], ['remove'], ['showconfig'],
            ['unpack', Globals.remote_capfile, 'script'],
            ['unpack', Globals.remote_capfile, 'binary'], ['/?']],
    ids=['version', 'install', 'remove', 'showconfig', 'unpack_script', 'unpack_binary', 'usage'],
    autouse=True)
def pre_test(request):
    if request.param[0] == 'showconfig':
        pytest.skip("Agent option '%s' is broken, skipping test..." % request.param[0])
    Globals.param = request.param
    if platform.system() == 'Windows':
        if Globals.param[0] == 'install':
            for subcmd in ['stop', 'delete']:
                cmd = ['sc', subcmd, 'Check_MK_Agent']
                run_subprocess(cmd)  # ignore possible failure
        elif Globals.param[0] == 'remove':
            assert_subprocess(['sc', 'create', 'Check_MK_Agent', 'binPath=%s' % src_exec_dir])
        elif Globals.param[0] == 'unpack':
            run_uninstall_plugins()
    elif Globals.param[0] == 'unpack':
        pack_plugins(Globals.param[2] == 'script')
        copy_capfile()
    yield


def verify_plugin_contents():
    for root, dirs, files in os.walk(Globals.testfiles[1]):
        assert len(dirs) == 0
        for f in files:
            plugin_contents = [v[1] for v in Globals.testfiles[2] if v[0] == f]
            assert len(plugin_contents) == 1
            with open(os.path.join(root, f)) as fhandle:
                actual_data = fhandle.read()
                expected_data = plugin_contents[0]
                assert expected_data == actual_data, ('expected contents of file %s: %s, '
                                                      'actual contents: %s' %
                                                      (f, expected_data, actual_data))


def verify_plugin_output():
    cmd = [os.path.join(Globals.testfiles[1], Globals.binaryplugin)]
    exit_code, stdout, stderr = run_subprocess(cmd)
    assert exit_code == 0, "'%s' failed" % Globals.binaryplugin
    assert "<<<monty_python>>>\r\nMonty Python's Flying Circus\r\n" == stdout
    assert len(stderr) == 0, "Expected empty stderr, got '%s'" % stderr


def verify_uninstall_batch(script):
    drive_letter = r'[A-Z]:'

    if script:
        test_plugins = [t[0] for t in sorted(Globals.testfiles[2])]
    else:
        test_plugins = [Globals.binaryplugin]
    expected_uninstall = [
        ('REM \\* If you want to uninstall the plugins which were '
         'installed during the'),
        ("REM \\* last 'check_mk_agent.exe unpack' command, just "
         'execute this script'), ''
    ] + [
        'del "%s%s"' %
        (drive_letter, re.escape(os.path.join(src_exec_dir, Globals.testfiles[1], t)))
        for t in test_plugins
    ] + [
        'del "%s%s"' %
        (drive_letter, re.escape(os.path.join(src_exec_dir, 'uninstall_plugins.bat')))
    ]
    with open(os.path.join(src_exec_dir, 'uninstall_plugins.bat')) as fhandle:
        actual_uninstall = fhandle.read().splitlines()
        local_test(expected_uninstall, actual_uninstall, None)


@pytest.fixture(autouse=True)
def post_test():
    yield
    if platform.system() == 'Windows':
        try:
            if Globals.param[0] == 'install':
                cmd = ['sc', 'query', 'Check_MK_Agent']
                exit_code, stdout, stderr = run_subprocess(cmd)
                assert exit_code == 0, "'%s' failed" % ' '.join(cmd)
                assert 'SERVICE_NAME: Check_MK_Agent' in stdout, ('Agent was not installed')
            elif Globals.param[0] == 'remove':
                cmd = ['sc', 'query', 'Check_MK_Agent']
                exit_code, stdout, stderr = run_subprocess(cmd)
                assert exit_code == 1060, 'Check_MK_Agent should not be running'
        finally:
            # Make sure the service is stopped and deleted after tests:
            for subcmd in ['stop', 'delete']:
                cmd = ['sc', subcmd, 'Check_MK_Agent']
                run_subprocess(cmd)  # ignore possible failure
        if Globals.param[0] == 'unpack':
            try:
                save_cwd = os.getcwd()
                os.chdir(src_exec_dir)
                if Globals.param[2] == 'script':
                    verify_plugin_contents()
                else:
                    verify_plugin_output()
                verify_uninstall_batch(Globals.param[2] == 'script')
            finally:
                # run_uninstall_plugins()
                os.unlink(Globals.remote_capfile)
                shutil.rmtree(Globals.testfiles[1])
                os.chdir(save_cwd)
    else:
        if Globals.param[0] == 'unpack':
            os.unlink(Globals.capfile)


def test_agent_start_parameters(request, testconfig, expected_output, actual_output, testfile):
    # request.node.name gives test name
    local_test(expected_output, actual_output, testfile, request.node.name)
