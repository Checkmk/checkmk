from itertools import chain, repeat
import os
import pytest
import re
from remote import actual_output, config, remotetest, wait_agent, write_config


@pytest.fixture
def testfile():
    return os.path.basename(__file__)


@pytest.fixture(
    params=['webservices', 'wmi_webservices'],
    ids=['sections=webservices', 'sections=wmi_webservices'])
def testconfig(request, config):
    config.set("global", "sections", request.param)
    config.set("global", "crash_debug", "yes")
    return config


@pytest.fixture
def expected_output():
    return chain(
        [
            re.escape(r'<<<wmi_webservices:sep(44)>>>'),
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
             r'UnlockRequestsPersec')
        ],
        repeat(
            r'\d+,\d+,\d+,\d+,,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,'
            r'\d+,,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,'
            r'\d+,\d+,\d+,\d+,\d+,\d+,\d+,[^,]+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,'
            r'\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,'
            r'\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,'
            r'\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+'))


def test_section_wmi_webservices(request, testconfig, expected_output,
                                 actual_output, testfile):
    # request.node.name gives test name
    remotetest(testconfig, expected_output, actual_output, testfile,
               request.node.name)
