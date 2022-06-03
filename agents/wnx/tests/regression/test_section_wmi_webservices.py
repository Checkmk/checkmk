#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import re
from itertools import chain, repeat

import pytest

from . import it_utils
from .local import local_test


class Globals:
    alone = True


@pytest.fixture(name="testfile")
def testfile_engine():
    return os.path.basename(__file__)


@pytest.fixture(
    name="testconfig",
    params=[("wmi_webservices", True), ("wmi_webservices", False)],
    ids=["sections=wmi_webservices", "sections=wmi_webservices_systemtime"],
)
def testconfig_engine(request, make_yaml_config):
    Globals.alone = request.param[1]
    if Globals.alone:
        make_yaml_config["global"]["sections"] = request.param[0]
    else:
        make_yaml_config["global"]["sections"] = [request.param[0], "%s systemtime"]
    return make_yaml_config


@pytest.fixture(name="expected_output")
def expected_output_engine():
    re_str = (
        r"^\d+,\d+,\d+,\d+,,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,"
        r"\d+,,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,"
        r"\d+,\d+,\d+,\d+,\d+,\d+,\d+,[^,]+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,"
        r"\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,"
        r"\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,"
        r"\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\d+,\b(?:OK|Timeout)\b"
    ).replace(",", "\\|")
    if not Globals.alone:
        re_str += r"|" + re.escape(r"<<<systemtime>>>") + r"|\d+"
    re_str += r"$"
    return chain(
        [
            re.escape(r"<<<wmi_webservices:sep(124)>>>"),
            (
                r"AnonymousUsersPersec,BytesReceivedPersec,BytesSentPersec,"
                r"BytesTotalPersec,Caption,CGIRequestsPersec,"
                r"ConnectionAttemptsPersec,CopyRequestsPersec,"
                r"CurrentAnonymousUsers,CurrentBlockedAsyncIORequests,"
                r"Currentblockedbandwidthbytes,"
                r"CurrentCALcountforauthenticatedusers,"
                r"CurrentCALcountforSSLconnections,CurrentCGIRequests,"
                r"CurrentConnections,CurrentISAPIExtensionRequests,"
                r"CurrentNonAnonymousUsers,DeleteRequestsPersec,Description,"
                r"FilesPersec,FilesReceivedPersec,FilesSentPersec,"
                r"Frequency_Object,Frequency_PerfTime,Frequency_Sys100NS,"
                r"GetRequestsPersec,HeadRequestsPersec,"
                r"ISAPIExtensionRequestsPersec,LockedErrorsPersec,"
                r"LockRequestsPersec,LogonAttemptsPersec,MaximumAnonymousUsers,"
                r"MaximumCALcountforauthenticatedusers,"
                r"MaximumCALcountforSSLconnections,MaximumCGIRequests,"
                r"MaximumConnections,MaximumISAPIExtensionRequests,"
                r"MaximumNonAnonymousUsers,MeasuredAsyncIOBandwidthUsage,"
                r"MkcolRequestsPersec,MoveRequestsPersec,Name,"
                r"NonAnonymousUsersPersec,NotFoundErrorsPersec,"
                r"OptionsRequestsPersec,OtherRequestMethodsPersec,"
                r"PostRequestsPersec,PropfindRequestsPersec,"
                r"ProppatchRequestsPersec,PutRequestsPersec,SearchRequestsPersec,"
                r"ServiceUptime,Timestamp_Object,Timestamp_PerfTime,"
                r"Timestamp_Sys100NS,TotalAllowedAsyncIORequests,"
                r"TotalAnonymousUsers,TotalBlockedAsyncIORequests,"
                r"Totalblockedbandwidthbytes,TotalBytesReceived,TotalBytesSent,"
                r"TotalBytesTransferred,TotalCGIRequests,"
                r"TotalConnectionAttemptsallinstances,TotalCopyRequests,"
                r"TotalcountoffailedCALrequestsforauthenticatedusers,"
                r"TotalcountoffailedCALrequestsforSSLconnections,"
                r"TotalDeleteRequests,TotalFilesReceived,TotalFilesSent,"
                r"TotalFilesTransferred,TotalGetRequests,TotalHeadRequests,"
                r"TotalISAPIExtensionRequests,TotalLockedErrors,TotalLockRequests,"
                r"TotalLogonAttempts,TotalMethodRequests,"
                r"TotalMethodRequestsPersec,TotalMkcolRequests,"
                r"TotalMoveRequests,TotalNonAnonymousUsers,TotalNotFoundErrors,"
                r"TotalOptionsRequests,TotalOtherRequestMethods,TotalPostRequests,"
                r"TotalPropfindRequests,TotalProppatchRequests,TotalPutRequests,"
                r"TotalRejectedAsyncIORequests,TotalSearchRequests,"
                r"TotalTraceRequests,TotalUnlockRequests,TraceRequestsPersec,"
                r"UnlockRequestsPersec,WMIStatus"
            ).replace(",", "\\|"),
        ],
        repeat(re_str),
    )


def test_section_wmi_webservices(request, testconfig, expected_output, actual_output, testfile):
    # special case wmi may timeout
    required_lines = 3
    name = "webservices"

    if not it_utils.check_actual_input(name, required_lines, Globals.alone, actual_output):
        return

    local_test(expected_output, actual_output, testfile, request.node.name)
