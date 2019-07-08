#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset: 4 -*-
import os
import platform
import pytest
import re
from remote import (actual_output, config, remotedir, remotetest, wait_agent, write_config)
import shutil


class TestPaths(object):
    drive = os.getcwd()[:2]

    def tempdir1(self):
        return os.path.join(self.drive, remotedir, 'Testdir1')

    def tempdir2(self):
        return os.path.join(self.tempdir1(), 'Testdir2')

    def tempfile1(self):
        return os.path.join(self.tempdir1(), 'TestFile1')

    def tempfile2(self):
        return os.path.join(self.tempdir1(), 'TestFile2')

    def tempfile3(self):
        return os.path.join(self.tempdir2(), 'TestFile3')

    def missingfile(self):
        return os.path.join(self.tempdir1(), 'foobar')

    def drive_upper(self):
        self.drive = self.drive.upper()

    def drive_lower(self):
        self.drive = self.drive.lower()


class Globals(object):
    section = 'fileinfo'
    alone = True
    paths = TestPaths()


@pytest.fixture
def testfile(request):
    return os.path.basename(__file__)


@pytest.fixture(params=['uppercase_drive', 'lowercase_drive'])
def testconfig_drive(request, config):
    if request.param == 'uppercase_drive':
        Globals.paths.drive_upper()
    else:
        Globals.paths.drive_lower()
    return config


@pytest.fixture(params=[(Globals.paths.tempdir1, '**', True), (Globals.paths.tempdir2, 'Te*', True),
                        (Globals.paths.tempdir2, 'Te*', False)],
                ids=['recursive_glob', 'simple_glob_alone', 'simple_glob_with_systemtime'])
def testconfig(request, testconfig_drive):
    if platform.system() == 'Windows':
        Globals.alone = request.param[2]
        if Globals.alone:
            testconfig_drive.set('global', 'sections', Globals.section)
        else:
            testconfig_drive.set('global', 'sections', '%s systemtime' % Globals.section)
        testconfig_drive.set('global', 'crash_debug', 'yes')
        testconfig_drive.add_section(Globals.section)
        if request.param[0] != Globals.paths.tempdir1:
            testconfig_drive.set(Globals.section, 'path', Globals.paths.tempfile1())
            testconfig_drive.set(
                Globals.section, 'path',
                os.path.join(Globals.paths.tempdir1(),
                             '?' + os.path.basename(Globals.paths.tempfile2())[1:]))
        testconfig_drive.set(Globals.section, 'path',
                             os.path.join(request.param[0](), request.param[1]))
        testconfig_drive.set(Globals.section, 'path', Globals.paths.missingfile())

        return testconfig_drive


@pytest.fixture
def expected_output():
    if platform.system() == 'Windows':
        expected = [
            re.escape(r'<<<%s:sep(124)>>>' % Globals.section), r'\d+',
            re.escape(r'%s|' % Globals.paths.tempfile1()) + r'\d+\|\d+',
            re.escape(r'%s|' % Globals.paths.tempfile2()) + r'\d+\|\d+',
            re.escape(r'%s|' % Globals.paths.tempfile3()) + r'\d+\|\d+',
            re.escape(r'%s|missing|' % Globals.paths.missingfile()) + r'\d+'
        ]
        if not Globals.alone:
            expected += [re.escape(r'<<<systemtime>>>'), r'\d+']
        return expected


@pytest.fixture
def use_testfiles():
    if platform.system() == 'Windows':
        for d in [Globals.paths.tempdir1(), Globals.paths.tempdir2()]:
            os.mkdir(d)
        for f in [Globals.paths.tempfile1(), Globals.paths.tempfile2(), Globals.paths.tempfile3()]:
            with open(f, 'w') as handle:
                handle.write(f)

    yield

    if platform.system() == 'Windows':
        for d in [Globals.paths.tempdir2(), Globals.paths.tempdir1()]:
            shutil.rmtree(d)


@pytest.mark.usefixtures('use_testfiles')
def test_section_fileinfo(request, testconfig, expected_output, actual_output, testfile):
    # request.node.name gives test name
    remotetest(expected_output, actual_output, testfile, request.node.name)
