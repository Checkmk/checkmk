import os
import platform
import pytest
import re
from remote import (actual_output, config, remotedir, remotetest, wait_agent,
                    write_config)
import shutil

section = 'fileinfo'
tempdir1 = os.path.join(remotedir, 'testdir1')
tempdir2 = os.path.join(tempdir1, 'testdir2')
tempfile1 = os.path.join(tempdir1, "testfile1")
tempfile2 = os.path.join(tempdir1, "testfile2")
tempfile3 = os.path.join(tempdir2, "testfile3")
missingfile = os.path.join(tempdir1, 'foobar')


@pytest.fixture
def testfile(request):
    return os.path.basename(__file__)


@pytest.fixture
def testconfig(config):
    if platform.system() == 'Windows':
        config.set("global", "sections", section)
        config.set("global", "crash_debug", "yes")
        config.add_section(section)
        config.set(section, "path", tempfile1)
        config.set(section, "path",
                   os.path.join(tempdir1,
                                '?' + os.path.basename(tempfile2)[1:]))
        config.set(section, "path", os.path.join(tempdir1, '*', '*'))
        config.set(section, "path", missingfile)

        return config


@pytest.fixture
def expected_output():
    if platform.system() == 'Windows':
        return [
            re.escape(r'<<<%s:sep(124)>>>' % section), r'\d+',
            re.escape(r'%s|' % tempfile1) + r'\d+\|\d+',
            re.escape(r'%s|' % tempfile2) + r'\d+\|\d+',
            re.escape(r'%s|' % tempfile3) + r'\d+\|\d+',
            re.escape(r'%s|missing|' % missingfile) + r'\d+'
        ]


@pytest.fixture
def use_testfiles():
    if platform.system() == 'Windows':
        tempdir1 = os.path.join(remotedir, 'testdir1')
        tempdir2 = os.path.join(tempdir1, 'testdir2')
        tempfile1 = os.path.join(tempdir1, "testfile1")
        tempfile2 = os.path.join(tempdir1, "testfile2")
        tempfile3 = os.path.join(tempdir2, "testfile3")

        for d in [tempdir1, tempdir2]:
            os.mkdir(d)
        for f in [tempfile1, tempfile2, tempfile3]:
            with open(f, 'w') as handle:
                handle.write(f)

    yield

    if platform.system() == 'Windows':
        for d in [tempdir2, tempdir1]:
            shutil.rmtree(d)


@pytest.mark.usefixtures("use_testfiles")
def test_section_fileinfo(testconfig, expected_output, actual_output,
                          testfile):
    remotetest(testconfig, expected_output, actual_output, testfile)
