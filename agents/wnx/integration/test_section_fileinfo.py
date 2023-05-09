#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import platform
import pytest  # type: ignore
import re
from local import actual_output, make_yaml_config, local_test, wait_agent, write_config, user_dir
import shutil


class TestPaths(object):
    def __init__(self):
        self.drive, _ = os.path.splitdrive(user_dir)

    def tempdir1(self):
        _, path = os.path.splitdrive(user_dir)
        return os.path.join(self.drive, path, "Testdir1")

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
def testconfig_drive(request, make_yaml_config):
    if request.param == 'uppercase_drive':
        Globals.paths.drive_upper()
    else:
        Globals.paths.drive_lower()
    return make_yaml_config


@pytest.fixture(params=[(Globals.paths.tempdir1, '**', True), (Globals.paths.tempdir2, 'Te*', True),
                        (Globals.paths.tempdir2, 'Te*', False)],
                ids=['recursive_glob', 'simple_glob_alone', 'simple_glob_with_systemtime'])
def testconfig(request, testconfig_drive):
    if platform.system() == 'Windows':
        Globals.alone = request.param[2]
        Globals.alone = request.param == 'alone'
        if Globals.alone:
            testconfig_drive['global']['sections'] = Globals.section
        else:
            testconfig_drive['global']['sections'] = [Globals.section, "systemtime"]

        path_array = []
        if request.param[0] != Globals.paths.tempdir1:
            path_array.append(Globals.paths.tempfile1())
            path_array.append(
                os.path.join(Globals.paths.tempdir1(),
                             '?' + os.path.basename(Globals.paths.tempfile2())[1:]))

        path_array.append(os.path.join(request.param[0](), request.param[1]))
        path_array.append(Globals.paths.missingfile())
        testconfig_drive[Globals.section] = {'path': path_array}

        return testconfig_drive


@pytest.fixture
def expected_output():
    if platform.system() == 'Windows':
        # this variable is for a future release
        expected_modern = [
            re.escape(r'<<<%s:sep(124)>>>' % Globals.section), r'\d+',
            re.escape(r'[[[header]]]'),
            re.escape(r'name|status|size|time'),
            re.escape(r'[[[content]]]'),
            re.escape(r'%s|' % Globals.paths.tempfile1()) + r'ok\|' + r'\d+\|\d+',
            re.escape(r'%s|' % Globals.paths.tempfile2()) + r'ok\|' + r'\d+\|\d+',
            re.escape(r'%s|' % Globals.paths.tempfile3()) + r'ok\|' + r'\d+\|\d+',
            re.escape(r'%s|' % Globals.paths.missingfile()) + r'missing'
        ]
        expected_legacy = [
            re.escape(r'<<<%s:sep(124)>>>' % Globals.section), r'\d+',
            re.escape(r'%s|' % Globals.paths.tempfile1()) + r'\d+\|\d+',
            re.escape(r'%s|' % Globals.paths.tempfile2()) + r'\d+\|\d+',
            re.escape(r'%s|' % Globals.paths.tempfile3()) + r'\d+\|\d+',
            re.escape(r'%s|missing|' % Globals.paths.missingfile()) + r'\d+'
        ]
        if not Globals.alone:
            expected_legacy += [re.escape(r'<<<systemtime>>>'), r'\d+']
        return expected_legacy


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
    local_test(expected_output, actual_output, testfile, request.node.name)
