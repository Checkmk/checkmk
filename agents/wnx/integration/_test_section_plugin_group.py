#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset: 4 -*-
from itertools import chain, repeat
import os
import platform
import pytest
import re
import sys
import time
from local import (actual_output, assert_subprocess, make_yaml_config, src_exec_dir, local_test,
                   wait_agent, write_config)


class Globals(object):
    executionmode = None
    pluginname = None
    plugintype = None
    suffixes = None
    builddir = 'build64'
    binaryplugin = 'MontyPython.exe'


@pytest.fixture
def testfile():
    return os.path.basename(__file__)


@pytest.fixture(params=['default', 'bat ps1'], ids=['default_suffixes', 'bat_ps1'])
def testconfig_suffixes(request, make_yaml_config):
    Globals.suffixes = request.param
    if request.param != 'default':
        make_yaml_config.set('global', 'execute', request.param)
    return make_yaml_config


@pytest.fixture(params=['alone', 'with_systemtime'])
def testconfig_sections(request, testconfig_suffixes):
    Globals.alone = request.param == 'alone'
    if Globals.alone:
        make_yaml_config['global']['sections'] = Globals.section
    else:
        make_yaml_config['global']['sections'] = [Globals.section, "systemtime"]
    return make_yaml_config


@pytest.fixture(params=['sync', 'async', 'async+cached'])
def testconfig(request, testconfig_sections):
    Globals.executionmode = request.param
    testconfig_sections.set('global', 'crash_debug', 'yes')
    if request.param != 'sync':
        testconfig_sections.add_section(Globals.plugintype)
        testconfig_sections.set(Globals.plugintype, 'execution %s' % Globals.pluginname, 'async')
        testconfig_sections.set(Globals.plugintype, 'timeout %s' % Globals.pluginname, '10')
        if request.param == 'async+cached':
            testconfig_sections.set(Globals.plugintype, 'cache_age %s' % Globals.pluginname, '300')
        testconfig_sections.set(Globals.plugintype, 'retry_count %s' % Globals.pluginname, '3')
    return testconfig_sections


@pytest.fixture()
def expected_output():
    main_label = [
        re.escape(r'<<<%s>>>' % (Globals.plugintype if Globals.plugintype == 'local' else ''))
    ]
    if Globals.suffixes == 'default':
        plugin_fixed = [
            re.escape(r'<<<') + r'monty_python' + re.escape(r'>>>'), r"Monty Python's Flying Circus"
        ]
    else:
        plugin_fixed = []
    if Globals.pluginname == 'netstat_an.bat':
        plugin_fixed += [
            re.escape(r'<<<') + r'win_netstat%s' %
            (r':cached\(\d+,\d+\)' if Globals.executionmode == 'async+cached' else r'') +
            re.escape(r'>>>'), r'^$'
        ]
        repeating_pattern = (r'^$'
                             r'|Aktive Verbindungen'
                             r'|Active Connections'
                             r'|\s+Proto\s+Lokale Adresse\s+Remoteadresse\s+Status'
                             r'|\s+Proto\s+Local Address\s+Foreign Adress\s+State'
                             r'|\s+TCP\s+(\d+\.\d+\.\d+\.\d+|'
                             r'\[::\d*\]|\[[0-9a-f]{,4}(:[0-9a-f]{,4})+(%\d+)?\]):\d+'
                             r'\s+(\d+\.\d+\.\d+\.\d+|\[::\d*\]|'
                             r'\[[0-9a-f]{,4}(:[0-9a-f]{,4})+(%\d+)?\]):\d+'
                             r'\s+(ABH.REN|HERGESTELLT|WARTEND|SCHLIESSEN_WARTEN|SYN_GESENDET'
                             r'|LISTENING|ESTABLISHED|TIME_WAIT|CLOSE_WAIT)'
                             r'|\s+UDP\s+\d+\.\d+\.\d+\.\d+:\d+\s+\*:\*'
                             r'|\-?\d+( \d+)+ [\w\(\)]+')
        if Globals.plugintype == 'plugins':
            repeating_pattern += r'|%s' % re.escape(r'<<<>>>')
        if not Globals.alone:
            repeating_pattern += r'|' + re.escape(r'<<<systemtime>>>') + r'|\d+'
        plugin_variadic = repeat(repeating_pattern)
    elif Globals.pluginname == 'wmic_if.bat':
        plugin_fixed += [
            re.escape(r'<<<') + r'winperf_if:sep\(44\)%s' %
            (r':cached\(\d+,\d+\)' if Globals.executionmode == 'async+cached' else r'') +
            re.escape(r'>>>'), r'^$', r'^$',
            r'Node,MACAddress,Name,NetConnectionID,NetConnectionStatus,Speed'
        ]
        re_variadic = (r'[^,]+,([0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5})?,[^,]+,[^,]*,\d*,\d*' r'|^$')
        if Globals.plugintype == 'plugins':
            re_variadic += r'|%s' % re.escape(r'<<<>>>')
        if not Globals.alone:
            re_variadic += r'|' + re.escape(r'<<<systemtime>>>') + r'|\d+'
        plugin_variadic = repeat(re_variadic)
    elif Globals.pluginname == 'windows_if.ps1':
        plugin_fixed += [
            re.escape(r'<<<') + r'winperf_if:sep\(9\)%s' %
            (r':cached\(\d+,\d+\)' if Globals.executionmode == 'async+cached' else r'') +
            re.escape(r'>>>'),
            (r'Node\s+MACAddress\s+Name\s+NetConnectionID\s+NetConnectionStatus'
             r'\s+Speed\s+GUID'),
            (r'[^\t]+\s+([0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5})?\s+[^\t]+\s+[^\t]*'
             r'\s+\d*\s+\d*\s+\{[0-9A-F]+(\-[0-9A-F]+)+\}')
        ]
        plugin_variadic = [
            r'%s' % ('' if Globals.alone else r'|' + re.escape(r'<<<systemtime>>>') + r'|\d+')
        ]

    return chain(main_label, plugin_fixed, plugin_variadic)


@pytest.fixture(params=['plugins', 'local'])
def plugindir(request):
    Globals.plugintype = request.param
    sourcedir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'plugins')
    targetdir = os.path.join(src_exec_dir, request.param)
    return sourcedir, targetdir


@pytest.fixture(params=['netstat_an.bat', 'wmic_if.bat', 'windows_if.ps1'], autouse=True)
def manage_plugins(request, plugindir):
    Globals.pluginname = request.param
    targetdir = plugindir[1].replace('/', '\\')
    if platform.system() != 'Windows':
        fullbuilddir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                    Globals.builddir)
        cmds = [[
            'ssh', sshopts,
            '%s@%s' % (remoteuser, remote_ip),
            'if not exist %s md %s' % (targetdir, targetdir)
        ],
                [
                    'scp', sshopts,
                    os.path.join(plugindir[0], request.param),
                    '%s@%s:%s' % (remoteuser, remote_ip, plugindir[1])
                ],
                [
                    'scp', sshopts,
                    os.path.join(fullbuilddir, Globals.binaryplugin),
                    '%s@%s:%s' % (remoteuser, remote_ip, plugindir[1])
                ]]
        for cmd in cmds:
            assert_subprocess(cmd)
    yield
    if platform.system() == 'Windows':
        for plugin in [request.param, Globals.binaryplugin]:
            for i in range(0, 5):
                try:
                    os.unlink(os.path.join(targetdir, plugin))
                    break
                except WindowsError as e:
                    # For some reason, the exe plugin remains locked for a short
                    # while every now and then. Just sleep 1 s and retry.
                    sys.stderr.write('%s\n' % str(e))
                    time.sleep(1)


def test_section_plugin_group(request, testconfig, expected_output, actual_output, testfile):
    # request.node.name gives test name
    local_test(expected_output, actual_output, testfile, request.node.name)
