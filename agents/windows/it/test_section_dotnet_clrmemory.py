from itertools import chain, repeat
import os
import pytest
import re
from remote import actual_output, config, remotetest, wait_agent, write_config


@pytest.fixture
def testfile():
    return os.path.basename(__file__)


@pytest.fixture
def testconfig(config):
    section = 'dotnet_clrmemory'
    config.set("global", "sections", section)
    config.set("global", "crash_debug", "yes")
    return config


@pytest.fixture
def expected_output():
    return chain([
        re.escape(r'<<<dotnet_clrmemory:sep(44)>>>'),
        (r'AllocatedBytesPersec,Caption,Description,FinalizationSurvivors,'
         r'Frequency_Object,Frequency_PerfTime,Frequency_Sys100NS,Gen0heapsize,'
         r'Gen0PromotedBytesPerSec,Gen1heapsize,Gen1PromotedBytesPerSec,'
         r'Gen2heapsize,LargeObjectHeapsize,Name,NumberBytesinallHeaps,'
         r'NumberGCHandles,NumberGen0Collections,NumberGen1Collections,'
         r'NumberGen2Collections,NumberInducedGC,NumberofPinnedObjects,'
         r'NumberofSinkBlocksinuse,NumberTotalcommittedBytes,'
         r'NumberTotalreservedBytes,PercentTimeinGC,PercentTimeinGC_Base,'
         r'ProcessID,PromotedFinalizationMemoryfromGen0,PromotedMemoryfromGen0,'
         r'PromotedMemoryfromGen1,Timestamp_Object,Timestamp_PerfTime,'
         r'Timestamp_Sys100NS')
    ],
                 repeat(r'\d+,,,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,'
                        r'[\w\#\.]+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,'
                        r'\d+,\-?\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+'))


def test_section_dotnet_clrmemory(testconfig, expected_output, actual_output,
                                  testfile):
    remotetest(testconfig, expected_output, actual_output, testfile)
