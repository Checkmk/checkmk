#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset: 4 -*-
from itertools import chain, repeat
import os
import pytest
import re
from remote import actual_output, config, remotetest, wait_agent, write_config


class Globals(object):
    section = 'dotnet_clrmemory'
    alone = True


@pytest.fixture
def testfile():
    return os.path.basename(__file__)


@pytest.fixture(params=['alone', 'with_systemtime'])
def testconfig(request, config):
    Globals.alone = request.param == 'alone'
    if Globals.alone:
        config.set('global', 'sections', Globals.section)
    else:
        config.set('global', 'sections', '%s systemtime' % Globals.section)
    config.set('global', 'crash_debug', 'yes')
    return config


@pytest.fixture
def expected_output():
    base = [
        re.escape(r'<<<%s:sep(9)>>>' % Globals.section),
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
         r'Timestamp_Sys100NS').replace(',', '\t')
    ]
    re_str = (r'\d+,,,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,'
              r'[\w\#\.]+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,'
              r'\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+').replace(',', '\t')
    if not Globals.alone:
        re_str += r'|' + re.escape(r'<<<systemtime>>>') + r'|\d+'
    return chain(base, repeat(re_str))


def test_section_dotnet_clrmemory(request, testconfig, expected_output, actual_output, testfile):

    # special case wmi may timeout.
    ac = actual_output
    required_lines = 5
    if not Globals.alone:
        required_lines += 2
    name = 'dotnet'

    if ac is None:
        pytest.skip('"%s" Data is absent' % name)
        return

    if len(ac) < required_lines:
        pytest.skip('"%s" Data is TOO short:\n %s' % (name, '\n'.join(ac)))
        return

    remotetest(expected_output, ac, testfile, request.node.name)
