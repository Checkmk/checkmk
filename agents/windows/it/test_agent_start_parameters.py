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
from remote import (actual_output, agent_exe, assert_subprocess, config, port,
                    remotetest, remotedir, run_subprocess, write_config)
import sys


class Globals(object):
    param = None
    capfile = 'plugins.cap'
    plugintype = 'plugins'
    pluginnames = ['netstat_an.bat', 'wmic_if.bat']
    sections = ['check_mk', 'fileinfo', 'logfiles', 'logwatch', plugintype]
    testfiles = ('basedir', 'monty', [('python', 'flying'), ('circus',
                                                             "It's")])
    testlogs = tuple(
        [os.path.join(remotedir, l) for l in ['test1.log', 'test2.log']])


@pytest.fixture
def testfile():
    return os.path.basename(__file__)


@pytest.fixture
def testconfig(config):
    config.set("global", "crash_debug", "yes")
    if Globals.param[0] == 'showconfig':
        config.set("global", "sections", ' '.join(Globals.sections))
        for section in filter(lambda s: s != 'check_mk', Globals.sections):
            config.add_section(section)
        config.set('fileinfo', 'path', os.path.join(remotedir, '*.log'))
        config.set('logfiles', "textfile",
                   "from_start %s|nocontext %s" % Globals.testlogs)
        config.set('logfiles', 'crit', 'e*o?')
        config.set('logwatch', 'vista_api', 'yes')
        config.set('logwatch', 'logfile Application', 'warn')
        for pluginname in Globals.pluginnames:
            config.set(Globals.plugintype, 'execution %s' % pluginname,
                       'async')
            config.set(Globals.plugintype, 'timeout %s' % pluginname, '10')
            config.set(Globals.plugintype, 'cache_age %s' % pluginname, '300')
            config.set(Globals.plugintype, 'retry_count %s' % pluginname, '3')
    return config


@pytest.fixture
def actual_output(request, write_config):
    if platform.system() == 'Windows':
        # Run agent and yield its output.
        try:
            save_cwd = os.getcwd()
            os.chdir(remotedir)
            cmd = []
            exit_code, stdout, stderr = run_subprocess(
                [agent_exe] + Globals.param)
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


def output_config(config):
    output = []
    for section, options in config._sections.iteritems():
        output.append(r'\[%s\]' % section)
        for key, values in options.iteritems():
            for value in values:
                output.append('%s = %s' % (key, value))
    return output


def output_usage():
    return [
        r'Usage: ', (r'check_mk_agent version         -- show version '
                     r'\d+\.\d+\.\d+([bi]\d+)?(p\d+)? and exit'),
        (r'check_mk_agent install         -- install as Windows NT service '
         r'Check_Mk_Agent'),
        r'check_mk_agent remove          -- remove Windows NT service',
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


# Pack a directory and return the byte stream of the CAP.
# Excerpt from enterprise/cmk_base/cee/cap.py
def pack(install_basedir):
    cap = ""
    old_cwd = os.path.abspath('.')
    os.chdir(install_basedir)
    for relative_dir, _unused_dirs, files in os.walk("."):
        for filename in files:
            path = (relative_dir + "/" + filename)[2:]
            cap += _cap_entry(path)
    os.chdir(old_cwd)
    return cap


def _cap_entry(relpath):
    entry = chr(len(relpath)) + relpath
    content = file(relpath).read()
    entry += _cap_filesize(len(content)) + content
    return entry


def _cap_filesize(l):
    return chr(l     & 0xff) + \
           chr(l>>8  & 0xff) + \
           chr(l>>16 & 0xff) + \
           chr(l>>24 & 0xff)


@pytest.fixture(
    # Note: param 'adhoc' is tested in all section tests
    #       params 'test' and 'debug' are tested in section check_mk tests
    params=[['version'], ['install'], ['remove'], ['showconfig'],
            ['unpack', Globals.capfile], ['/?']],
    ids=['version', 'install', 'remove', 'showconfig', 'unpack', 'usage'],
    autouse=True)
def pre_test(request):
    if request.param[0] == 'showconfig':
        pytest.skip(
            "Agent option '%s' is broken, skipping test..." % request.param[0])
    Globals.param = request.param
    if platform.system() == 'Windows':
        if Globals.param[0] == 'install':
            for subcmd in ['stop', 'delete']:
                cmd = ['sc', subcmd, 'Check_MK_Agent']
                run_subprocess(cmd)  # ignore possible failure
        elif Globals.param[0] == 'remove':
            assert_subprocess(
                ['sc', 'create', 'Check_MK_Agent',
                 'binPath=%s' % remotedir])
        elif Globals.param[0] == 'unpack':
            save_cwd = os.getcwd()
            try:
                os.chdir(remotedir)
                basedir, directory, plugins = Globals.testfiles
                os.mkdir(basedir)
                os.mkdir(os.path.join(basedir, directory))
                for pluginname, content in plugins:
                    with open(
                            os.path.join(basedir, directory, pluginname),
                            'w') as outfile:
                        outfile.write(content)
                with open(Globals.capfile, 'wb') as capfile:
                    capfile.write(pack(basedir))
                shutil.rmtree(basedir)
            finally:
                os.chdir(save_cwd)
    yield


@pytest.fixture(autouse=True)
def post_test():
    yield
    if platform.system() == 'Windows':
        try:
            if Globals.param[0] == 'install':
                cmd = ['sc', 'query', 'Check_MK_Agent']
                exit_code, stdout, stderr = run_subprocess(cmd)
                assert exit_code == 0, "'%s' failed" % ' '.join(cmd)
                assert 'SERVICE_NAME: Check_MK_Agent' in stdout, (
                    'Agent was not installed')
            elif Globals.param[0] == 'remove':
                cmd = ['sc', 'query', 'Check_MK_Agent']
                exit_code, stdout, stderr = run_subprocess(cmd)
                assert exit_code == 1060, "Check_MK_Agent should not be running"
        finally:
            # Make sure the service is stopped and deleted after tests:
            for subcmd in ['stop', 'delete']:
                cmd = ['sc', subcmd, 'Check_MK_Agent']
                run_subprocess(cmd)  # ignore possible failure
        if Globals.param[0] == 'unpack':
            try:
                save_cwd = os.getcwd()
                os.chdir(remotedir)
                for root, dirs, files in os.walk(Globals.testfiles[1]):
                    assert len(dirs) == 0
                    for f in files:
                        plugin_contents = [
                            v[1] for v in Globals.testfiles[2] if v[0] == f
                        ]
                        assert len(plugin_contents) == 1
                        with open(os.path.join(root, f)) as fhandle:
                            actual_data = fhandle.read()
                            expected_data = plugin_contents[0]
                            assert expected_data == actual_data, (
                                'expected contents of file %s: %s, '
                                'actual contents: %s' % (f, expected_data,
                                                         actual_data))
                drive_letter = r'[A-Z]:'

                def paircmp(t1, t2):
                    if t1[0] < t2[0]:
                        return -1
                    elif t2[0] < t1[0]:
                        return 1
                    return 0

                expected_uninstall = [
                    ("REM \\* If you want to uninstall the plugins which were "
                     "installed during the"),
                    ("REM \\* last 'check_mk_agent.exe unpack' command, just "
                     "execute this script"), ""
                ] + [
                    'del "%s%s"' %
                    (drive_letter,
                     re.escape(
                         os.path.join(remotedir, Globals.testfiles[1], t[0])))
                    for t in sorted(Globals.testfiles[2], paircmp)
                ] + [
                    'del "%s%s"' %
                    (drive_letter,
                     re.escape(
                         os.path.join(remotedir, 'uninstall_plugins.bat')))
                ]
                with open(os.path.join(remotedir,
                                       'uninstall_plugins.bat')) as fhandle:
                    actual_uninstall = fhandle.read().splitlines()
                    remotetest(expected_uninstall, actual_uninstall, None)
            finally:
                os.unlink(Globals.capfile)
                shutil.rmtree(Globals.testfiles[1])
                os.chdir(save_cwd)


def test_agent_start_parameters(request, testconfig, expected_output,
                                actual_output, testfile):
    # request.node.name gives test name
    remotetest(expected_output, actual_output, testfile, request.node.name)
