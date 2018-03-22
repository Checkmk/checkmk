#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset: 4 -*-
from itertools import chain, repeat
import os
import platform
import pytest
import re
import sys
import time
from remote import (actual_output, assert_subprocess, config, remote_ip,
                    remotedir, remotetest, remoteuser, sshopts, wait_agent,
                    write_config)


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


@pytest.fixture(
    params=["default", "bat ps1"], ids=["default_suffixes", "bat_ps1"])
def testconfig_suffixes(request, config):
    Globals.suffixes = request.param
    if request.param != "default":
        config.set("global", "execute", request.param)
    return config


@pytest.fixture(params=['sync', 'async', 'async+cached'])
def testconfig(request, testconfig_suffixes):
    Globals.executionmode = request.param
    testconfig_suffixes.set("global", "sections", Globals.plugintype)
    testconfig_suffixes.set("global", "crash_debug", "yes")
    if request.param != 'sync':
        testconfig_suffixes.add_section(Globals.plugintype)
        testconfig_suffixes.set(Globals.plugintype,
                                'execution %s' % Globals.pluginname, 'async')
        testconfig_suffixes.set(Globals.plugintype,
                                'timeout %s' % Globals.pluginname, '10')
        if request.param == 'async+cached':
            testconfig_suffixes.set(Globals.plugintype,
                                    'cache_age %s' % Globals.pluginname, '300')
        testconfig_suffixes.set(Globals.plugintype,
                                'retry_count %s' % Globals.pluginname, '3')
    return testconfig_suffixes


@pytest.fixture()
def expected_output():
    main_label = [
        re.escape(r'<<<%s>>>' % (Globals.plugintype
                                 if Globals.plugintype == 'local' else ''))
    ]
    if Globals.suffixes == 'default':
        plugin_fixed = [
            re.escape(r'<<<') + r'monty_python' + re.escape(r'>>>'),
            r"Monty Python's Flying Circus"
        ]
    else:
        plugin_fixed = []
    if Globals.pluginname == 'netstat_an.bat':
        plugin_fixed += [
            re.escape(r'<<<') + r'win_netstat%s' %
            (r':cached\(\d+,\d+\)'
             if Globals.executionmode == 'async+cached' else r'') +
            re.escape(r'>>>'), r'^$'
        ]
        netstat_pattern = (
            r'^$'
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
            r'|\-?\d+( \d+)+ [\w\(\)]+')
        if Globals.plugintype == 'plugins':
            netstat_pattern += r'|%s' % re.escape(r'<<<>>>')
        plugin_variadic = repeat(netstat_pattern)
    elif Globals.pluginname == 'wmic_if.bat':
        plugin_fixed += [
            re.escape(r'<<<') + r'winperf_if:sep\(44\)%s' %
            (r':cached\(\d+,\d+\)'
             if Globals.executionmode == 'async+cached' else r'') +
            re.escape(r'>>>'), r'^$', r'^$',
            r'Node,MACAddress,Name,NetConnectionID,NetConnectionStatus,Speed'
        ]
        plugin_variadic = repeat(
            r'[^,]+,([0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5})?,[^,]+,[^,]*,\d*,\d*'
            r'|^$'
            r'%s' % (r'|%s' % re.escape(r'<<<>>>')
                     if Globals.plugintype == 'plugins' else ''))
    elif Globals.pluginname == 'windows_if.ps1':
        plugin_fixed += [
            re.escape(r'<<<') + r'winperf_if:sep\(9\)%s' %
            (r':cached\(\d+,\d+\)'
             if Globals.executionmode == 'async+cached' else r'') +
            re.escape(r'>>>'),
            (r'Node\s+MACAddress\s+Name\s+NetConnectionID\s+NetConnectionStatus'
             r'\s+Speed\s+GUID'),
            (r'[^\t]+\s+([0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5})?\s+[^\t]+\s+[^\t]*'
             r'\s+\d*\s+\d*\s+\{[0-9A-F]+(\-[0-9A-F]+)+\}')
        ]
        plugin_variadic = []

    return chain(main_label, plugin_fixed, plugin_variadic)


@pytest.fixture(params=['plugins', 'local'])
def plugindir(request):
    Globals.plugintype = request.param
    sourcedir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'plugins')
    targetdir = os.path.join(remotedir, request.param)
    return sourcedir, targetdir


@pytest.fixture(
    params=['netstat_an.bat', 'wmic_if.bat', 'windows_if.ps1'], autouse=True)
def manage_plugins(request, plugindir):
    Globals.pluginname = request.param
    targetdir = plugindir[1].replace('/', '\\')
    if platform.system() != 'Windows':
        fullbuilddir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            Globals.builddir)
        cmds = [[
            'ssh', sshopts,
            '%s@%s' % (remoteuser, remote_ip),
            'if not exist %s md %s' % (targetdir, targetdir)
        ], [
            'scp', sshopts,
            os.path.join(plugindir[0], request.param),
            '%s@%s:%s' % (remoteuser, remote_ip, plugindir[1])
        ], [
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
                    sys.stderr.write("%s\n" % str(e))
                    time.sleep(1)


def test_section_plugin_group(request, testconfig, expected_output,
                              actual_output, testfile):
    # request.node.name gives test name
    remotetest(expected_output, actual_output, testfile, request.node.name)
