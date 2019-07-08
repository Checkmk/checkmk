#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset: 4 -*-
from itertools import chain, repeat
import os
import pytest
import re
from local import actual_output, make_yaml_config, local_test, wait_agent, write_config
import it_utils


class Globals(object):
    alone = True


@pytest.fixture
def testfile():
    return os.path.basename(__file__)


@pytest.fixture(params=[('wmi_webservices', True), ('wmi_webservices', False)],
                ids=['sections=wmi_webservices', 'sections=wmi_webservices_systemtime'])
def testconfig(request, make_yaml_config):
    Globals.alone = request.param[1]
    if Globals.alone:
        make_yaml_config['global']['sections'] = request.param[0]
    else:
        make_yaml_config['global']['sections'] = [request.param[0], '%s systemtime']
    return make_yaml_config


@pytest.fixture
def expected_output():
    re_str = (
        r'^\d+,\d+,\d+,\d+,,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,'
        r'\d+,,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,'
        r'\d+,\d+,\d+,\d+,\d+,\d+,\d+,[^,]+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,'
        r'\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,'
        r'\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,'
        r'\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\b(?:OK|Timeout)\b').replace(
            ',', '\\|')
    if not Globals.alone:
        re_str += r'|' + re.escape(r'<<<systemtime>>>') + r'|\d+'
    re_str += r'$'
    return chain([
        re.escape(r'<<<wmi_webservices:sep(124)>>>'),
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
         r'UnlockRequestsPersec,WMIStatus').replace(',', '\\|')
    ], repeat(re_str))


def test_section_wmi_webservices(request, testconfig, expected_output, actual_output, testfile):
    # special case wmi may timeout
    required_lines = 3
    name = 'webservices'

    if not it_utils.check_actual_input(name, required_lines, Globals.alone, actual_output):
        return

    local_test(expected_output, actual_output, testfile, request.node.name)
