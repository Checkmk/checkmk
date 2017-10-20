import os
import pytest
from remote import actual_output, config, remotetest, wait_agent, write_config


@pytest.fixture
def testfile():
    return os.path.basename(__file__)


@pytest.fixture
def testconfig(config):
    section = 'mem'
    config.set("global", "sections", section)
    config.set("global", "crash_debug", "yes")
    return config


@pytest.fixture
def expected_output():
    return [
        r'<<<mem>>>',
        r'MemTotal:\s+\d+\skB',
        r'MemFree:\s+\d+\skB',
        r'SwapTotal:\s+\d+\skB',
        r'SwapFree:\s+\d+\skB',
        r'PageTotal:\s+\d+\skB',
        r'PageFree:\s+\d+\skB',
        r'VirtualTotal:\s+\d+\skB',
        r'VirtualFree:\s+\d+\skB'
    ]


def test_section_mem(testconfig, expected_output, actual_output, testfile):
    remotetest(testconfig, expected_output, actual_output, testfile)
