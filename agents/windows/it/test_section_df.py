import os
import pytest
import re
from remote import (actual_output, config, remotetest, remotedir, wait_agent,
                    write_config)


@pytest.fixture
def testfile():
    return os.path.basename(__file__)


@pytest.fixture
def testconfig(config):
    section = 'df'
    config.set("global", "sections", section)
    config.set("global", "crash_debug", "yes")
    return config


@pytest.fixture
def expected_output():
    drive = r'[A-Z]:%s' % re.escape(os.sep)
    return [
        re.escape(r'<<<df:sep(9)>>>'),
        r'%s\s+\w+\s+\d+\s+\d+\s+\d+\s+\d{1,3}%s\s+%s' %
        (drive, re.escape('%'), drive)
    ]


def test_section_df(testconfig, expected_output, actual_output, testfile):
    remotetest(expected_output, actual_output, testfile)
