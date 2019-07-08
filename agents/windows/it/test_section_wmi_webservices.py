#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset: 4 -*-
from itertools import chain, repeat
import os
import pytest
import re
from remote import actual_output, config, remotetest, wait_agent, write_config


class Globals(object):
    alone = True


@pytest.fixture
def testfile():
    return os.path.basename(__file__)


@pytest.fixture(params=[('webservices', True), ('wmi_webservices', True), ('webservices', False),
                        ('wmi_webservices', False)],
                ids=[
                    'sections=webservices', 'sections=wmi_webservices',
                    'sections=webservices_systemtime', 'sections=wmi_webservices_systemtime'
                ])
def testconfig(request, config):
    Globals.alone = request.param[1]
    if Globals.alone:
        config.set('global', 'sections', request.param[0])
    else:
        config.set('global', 'sections', '%s systemtime' % request.param[0])
    config.set('global', 'crash_debug', 'yes')
    return config


@pytest.fixture
def expected_output():
    re_str = (
        r'^\d+,\d+,\d+,\d+,,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,'
        r'\d+,,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,'
        r'\d+,\d+,\d+,\d+,\d+,\d+,\d+,[^,]+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,'
        r'\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,'
        r'\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,'
        r'\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\b(?:OK|Timeout)\b').replace(
            ',', '\t')
    if not Globals.alone:
        re_str += r'|' + re.escape(r'<<<systemtime>>>') + r'|\d+'
    re_str += r'$'
    return chain([
        re.escape(r'<<<wmi_webservices:sep(9)>>>'),
        (r'AnonymousUsersPersec,BytesReceivedPersec,BytesSentPersec,'
         r'BytesTotalPersec,Caption,CGIRequestsPersec,'
         r'ConnectionAttemptsPersec,CopyRequestsPersec,'
         r'CurrentAnonymousUsers,CurrentBlockedAsyncIORequests,'
         r'Currentblockedbandwidthbytes,'
         r'CurrentCALcountforauthenticatedusers,'
         r'CurrentCALcountforSSLconnections,CurrentCGIRequests,'
         r'CurrentConnections,CurrentISAPIExtensionRequests,'
         r'CurrentNonAnonymousUsers,DeleteRequestsPersec,Description,'
         r'FilesPersec,FilesReceivedPersec,FilesSentPersec,'
         r'Frequency_Object,Frequency_PerfTime,Frequency_Sys100NS,'
         r'GetRequestsPersec,HeadRequestsPersec,'
         r'ISAPIExtensionRequestsPersec,LockedErrorsPersec,'
         r'LockRequestsPersec,LogonAttemptsPersec,MaximumAnonymousUsers,'
         r'MaximumCALcountforauthenticatedusers,'
         r'MaximumCALcountforSSLconnections,MaximumCGIRequests,'
         r'MaximumConnections,MaximumISAPIExtensionRequests,'
         r'MaximumNonAnonymousUsers,MeasuredAsyncIOBandwidthUsage,'
         r'MkcolRequestsPersec,MoveRequestsPersec,Name,'
         r'NonAnonymousUsersPersec,NotFoundErrorsPersec,'
         r'OptionsRequestsPersec,OtherRequestMethodsPersec,'
         r'PostRequestsPersec,PropfindRequestsPersec,'
         r'ProppatchRequestsPersec,PutRequestsPersec,SearchRequestsPersec,'
         r'ServiceUptime,Timestamp_Object,Timestamp_PerfTime,'
         r'Timestamp_Sys100NS,TotalAllowedAsyncIORequests,'
         r'TotalAnonymousUsers,TotalBlockedAsyncIORequests,'
         r'Totalblockedbandwidthbytes,TotalBytesReceived,TotalBytesSent,'
         r'TotalBytesTransferred,TotalCGIRequests,'
         r'TotalConnectionAttemptsallinstances,TotalCopyRequests,'
         r'TotalcountoffailedCALrequestsforauthenticatedusers,'
         r'TotalcountoffailedCALrequestsforSSLconnections,'
         r'TotalDeleteRequests,TotalFilesReceived,TotalFilesSent,'
         r'TotalFilesTransferred,TotalGetRequests,TotalHeadRequests,'
         r'TotalISAPIExtensionRequests,TotalLockedErrors,TotalLockRequests,'
         r'TotalLogonAttempts,TotalMethodRequests,'
         r'TotalMethodRequestsPersec,TotalMkcolRequests,'
         r'TotalMoveRequests,TotalNonAnonymousUsers,TotalNotFoundErrors,'
         r'TotalOptionsRequests,TotalOtherRequestMethods,TotalPostRequests,'
         r'TotalPropfindRequests,TotalProppatchRequests,TotalPutRequests,'
         r'TotalRejectedAsyncIORequests,TotalSearchRequests,'
         r'TotalTraceRequests,TotalUnlockRequests,TraceRequestsPersec,'
         r'UnlockRequestsPersec,WMIStatus').replace(',', '\t')
    ], repeat(re_str))


def test_section_wmi_webservices(request, testconfig, expected_output, actual_output, testfile):

    # special case wmi may timeout
    ac = actual_output
    required_lines = 3
    if not Globals.alone:
        required_lines += 2
    name = 'webservices'

    if ac is None:
        pytest.skip('"%s" Data is absent' % name)
        return

    if len(ac) < required_lines:
        pytest.skip('"%s" Data is TOO short:\n %s' % (name, '\n'.join(ac)))
        return

    remotetest(expected_output, ac, testfile, request.node.name)
