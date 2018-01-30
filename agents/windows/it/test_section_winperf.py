from itertools import repeat
import os
import pytest
from remote import actual_output, config, remotetest, wait_agent, write_config


@pytest.fixture
def testfile():
    return os.path.basename(__file__)


@pytest.fixture(params=['System', '2'], ids=['counter:System', 'counter:2'])
def testconfig(request, config):
    section = 'winperf'
    config.set("global", "sections", section)
    config.set("global", "crash_debug", "yes")
    config.add_section(section)
    config.set(section, 'counters', '%s:test' % request.param)
    return config


@pytest.fixture
def expected_output():
    return repeat(r'\<\<\<winperf_(if|phydisk|processor|test)\>\>\>'
                  r'|\d+\.\d{2} \d+ \d+'
                  r'|\d+ instances\:( [^ ]+)+'
                  r'|\-?\d+( \d+)+ [\w\(\)]+')


def test_section_winperf(testconfig, expected_output, actual_output, testfile):
    remotetest(expected_output, actual_output, testfile)
