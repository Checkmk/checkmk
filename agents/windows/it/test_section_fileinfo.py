#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset: 4 -*-
import os
import platform
import pytest
import re
from remote import (actual_output, config, remotedir, remotetest, wait_agent,
                    write_config)
import shutil


class Globals:
    section = 'fileinfo'
    tempdir1 = os.path.join(remotedir, 'Testdir1')
    tempdir2 = os.path.join(tempdir1, 'Testdir2')
    tempfile1 = os.path.join(tempdir1, 'TestFile1')
    tempfile2 = os.path.join(tempdir1, 'TestFile2')
    tempfile3 = os.path.join(tempdir2, 'TestFile3')
    missingfile = os.path.join(tempdir1, 'foobar')


@pytest.fixture
def testfile(request):
    return os.path.basename(__file__)


@pytest.fixture(
    params=[
        os.path.join(Globals.tempdir1, '**'),
        os.path.join(Globals.tempdir2, 'Te*')
    ],
    ids=['recursive_glob', 'simple_glob'])
def testconfig(request, config):
    if platform.system() == 'Windows':
        config.set('global', 'sections', Globals.section)
        config.set('global', 'crash_debug', 'yes')
        config.add_section(Globals.section)
        if request.param != os.path.join(Globals.tempdir1, '**'):
            config.set(Globals.section, 'path', Globals.tempfile1)
            config.set(
                Globals.section, 'path',
                os.path.join(Globals.tempdir1,
                             '?' + os.path.basename(Globals.tempfile2)[1:]))
        config.set(Globals.section, 'path', request.param)
        config.set(Globals.section, 'path', Globals.missingfile)

        return config


@pytest.fixture
def expected_output():
    if platform.system() == 'Windows':
        return [
            re.escape(r'<<<%s:sep(124)>>>' % Globals.section), r'\d+',
            re.escape(r'%s|' % Globals.tempfile1) + r'\d+\|\d+',
            re.escape(r'%s|' % Globals.tempfile2) + r'\d+\|\d+',
            re.escape(r'%s|' % Globals.tempfile3) + r'\d+\|\d+',
            re.escape(r'%s|missing|' % Globals.missingfile) + r'\d+'
        ]


@pytest.fixture
def use_testfiles():
    if platform.system() == 'Windows':
        for d in [Globals.tempdir1, Globals.tempdir2]:
            os.mkdir(d)
        for f in [Globals.tempfile1, Globals.tempfile2, Globals.tempfile3]:
            with open(f, 'w') as handle:
                handle.write(f)

    yield

    if platform.system() == 'Windows':
        for d in [Globals.tempdir2, Globals.tempdir1]:
            shutil.rmtree(d)


@pytest.mark.usefixtures('use_testfiles')
def test_section_fileinfo(request, testconfig, expected_output, actual_output,
                          testfile):
    # request.node.name gives test name
    remotetest(expected_output, actual_output, testfile, request.node.name)
