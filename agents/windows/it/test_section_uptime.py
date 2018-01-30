import os
import pytest
from remote import actual_output, config, remotetest, wait_agent, write_config


@pytest.fixture
def testfile():
    return os.path.basename(__file__)


@pytest.fixture
def testconfig(config):
    section = 'uptime'
    config.set("global", "sections", section)
    config.set("global", "crash_debug", "yes")
    return config


@pytest.fixture
def expected_output():
    return [r'<<<uptime>>>', r'\d+']


def test_section_uptime(testconfig, expected_output, actual_output, testfile):
    remotetest(expected_output, actual_output, testfile)
