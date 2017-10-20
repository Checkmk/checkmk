from itertools import chain, repeat
import os
import pytest
import re
from remote import (actual_output, config, remotetest, remotedir, wait_agent,
                    write_config)


@pytest.fixture
def testfile():
    return os.path.basename(__file__)


@pytest.fixture
def testconfig(request, config):
    section = 'services'
    config.set("global", "sections", section)
    config.set("global", "crash_debug", "yes")
    return config


@pytest.fixture
def expected_output():
    return chain(
        [re.escape(r'<<<services>>>')],
        repeat(r'[\w\.-]+ (unknown|continuing|pausing|paused|running|starting'
               r'|stopping|stopped)/(invalid1|invalid2|invalid3|invalid4|auto'
               r'|boot|demand|disabled|system|other) .+'))


def test_section_services(testconfig, expected_output, actual_output,
                          testfile):
    remotetest(testconfig, expected_output, actual_output, testfile)
