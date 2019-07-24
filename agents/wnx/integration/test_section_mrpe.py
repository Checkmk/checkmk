#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset: 4 -*-
import os
import platform
import pytest
import re
import shutil
from local import (actual_output, assert_subprocess, make_yaml_config, src_exec_dir, local_test,
                   wait_agent, write_config, user_dir)


class Globals(object):
    section = 'mrpe'
    alone = True
    pluginname = 'check_crit.bat'
    param = 'foobar'
    checkname = 'Dummy'
    mrpedir = 'mrpe'
    includedir = 'test include'  # space in directory name!
    cfgfile = 'test.cfg'
    newline = -1


@pytest.fixture
def testfile():
    return os.path.basename(__file__)


@pytest.fixture(params=['alone', 'with_systemtime'])
def testconfig(request, make_yaml_config):
    Globals.alone = request.param == 'alone'
    if Globals.alone:
        make_yaml_config['global']['sections'] = Globals.section
    else:
        make_yaml_config['global']['sections'] = [Globals.section, "systemtime"]

    if Globals.newline < 0:
        make_yaml_config['mrpe'] = {
            'enabled': 'yes',
            'timeout': 60,
            'config': [
                "check = %s '%s'" %
                (Globals.checkname, os.path.join(Globals.mrpedir, Globals.pluginname))
            ]
        }
    else:
        make_yaml_config['mrpe'] = {
            'enabled': 'yes',
            'timeout': 60,
            'config': ["include = '%s'" % os.path.join(Globals.includedir, Globals.cfgfile)]
        }
    return make_yaml_config


@pytest.fixture
def expected_output():
    drive = r'[A-Z]:%s' % re.escape(os.sep)
    expected = [
        re.escape(r'<<<%s>>>' % Globals.section),
        r'\(%s\) %s 2 CRIT - This check is always critical' %
        (Globals.pluginname, Globals.checkname)
    ]
    if not Globals.alone:
        expected += [re.escape(r'<<<systemtime>>>'), r'\d+']
    return expected


@pytest.fixture(params=[-1, 0, 1, 2],
                ids=[
                    'direct', 'include_without_newline', 'include_with_newline',
                    'include_with_newline_forward_slash'
                ],
                autouse=True)
def manage_plugin(request):
    Globals.newline = request.param
    plugin_dir = (Globals.mrpedir if Globals.newline < 0 else Globals.includedir)
    source_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "test_files\\integration")
    target_dir = os.path.join(user_dir, plugin_dir)
    if not os.path.exists(target_dir):
        os.mkdir(target_dir)

    shutil.copy(os.path.join(source_dir, Globals.pluginname), target_dir)

    # create config file
    if Globals.newline >= 0:
        with open(os.path.join(target_dir, Globals.cfgfile), 'wb') as cfg:
            path = os.path.join(target_dir, Globals.pluginname)
            if Globals.newline == 2:
                path = path.replace('\\', '/')
            cfg_line = "check = %s '%s'%s" % (Globals.checkname, path,
                                              '\n' if Globals.newline > 0 else '')
            cfg.write(str.encode(cfg_line))
    yield
    if platform.system() == 'Windows':
        os.unlink(os.path.join(target_dir, Globals.pluginname))
        if Globals.newline >= 0:
            os.unlink(os.path.join(target_dir, Globals.cfgfile))


def test_section_mrpe(request, testconfig, expected_output, actual_output, testfile):
    # request.node.name gives test name
    local_test(expected_output, actual_output, testfile, request.node.name)
