#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'skype'

info = [
    [u'sampletime', u'42', u'1'], [u'[LS:WEB - Address Book Web Query]'],
    [
        u'instance', u'WEB - Search requests', u'WEB - Search requests/sec',
        u'WEB - Successful search requests', u'WEB - Successful search requests/sec',
        u'WEB - Failed search requests', u'WEB - Failed search requests/sec',
        u'WEB - Average processing time for a search request in milliseconds', u' ',
        u'WEB - Database queries/sec',
        u'WEB - Average processing time per address book database query in milliseconds', u' ',
        u'WEB - Change Search requests', u'WEB - Change Search requests/sec',
        u'WEB - Failed change search requests', u'WEB - Failed change search requests/sec',
        u'WEB - Average processing time per change search in milliseconds', u' ',
        u'WEB - Change Search of DTMF requests', u'WEB - Change Search of DTMF requests/sec',
        u'WEB - Organizational search requests', u'WEB - Organizational search requests/sec',
        u'WEB - Failed organizational search requests',
        u'WEB - Failed organizational search requests/sec',
        u'WEB - Average processing time for organizational search request in milliseconds', u' ',
        u'WEB - Basic and Org Search Request Exception Count',
        u'WEB - Basic and Org Search Request Exception/sec', u'WEB - Basic Search requests',
        u'WEB - Basic Search requests/sec', u'WEB - Failed basic search requests',
        u'WEB - Failed Basic search requests/sec',
        u'WEB - Average processing time for basic search request in milliseconds', u' ',
        u'WEB - Prefix dial string search requests',
        u'WEB - Prefix dial string search requests/sec',
        u'WEB - One character prefix search requests',
        u'WEB - One character prefix search requests/sec',
        u'WEB - Average processing time for one character search requests in milliseconds', u' ',
        u'WEB - Two character prefix search requests',
        u'WEB - Two character prefix search requests/sec',
        u'WEB - Average processing time for two character search requests in milliseconds', u' ',
        u'WEB - Three or more character prefix search requests',
        u'WEB - Three or more character prefix search requests/sec',
        u'WEB - Average processing time for three or more character search requests in milliseconds',
        u' ', u'WEB - Photo requests', u'WEB - Photo requests/sec', u'WEB - Photo failed requests',
        u'WEB - Photo failed requests/sec', u'WEB - Photo requests throttled',
        u'WEB - Photo hash cache entry update count',
        u'WEB - Average processing time for photo cached locally in milliseconds', u' ',
        u'WEB - Average processing time for photo not cached in milliseconds', u' ',
        u'WEB - % Photo Local Cache Hit', u' ', u'WEB - Skype Public Directory Search Requests',
        u'WEB - Skype Public Directory Search Requests/sec',
        u'WEB - Failed Skype Public Directory Search Requests',
        u'WEB - Failed Skype Public Directory Search Requests/sec',
        u'WEB - Skype Public Search Average Processing Time', u' ',
        u'WEB - Skype Public Directory Search Feedback Requests',
        u'WEB - Skype Public Directory Search Feedback Requests/sec',
        u'WEB - Failed Skype Public Directory Search Feedback Requests',
        u'WEB - Failed Skype Public Directory Search Feedback Requests/sec',
        u'WEB - Skype Public Search Feedback Average Processing Time', u' ',
        u'WEB - Failed Skype Search Requests With 4xx Response Codes',
        u'WEB - Failed Skype Search Requests Per Second With 4xx Response Codes',
        u'WEB - Total Skype Search Requests Throttled',
        u'WEB - Skype Search Requests Throttled Per Second',
        u'WEB - Failed Skype Search Requests With 5xx Response Codes',
        u'WEB - Failed Skype Search Requests Per Second With 5xx Response Codes',
        u'WEB - Failed Skype Search Feedback Requests With 4xx Response Codes',
        u'WEB - Failed Skype Search Feedback Requests Per Second With 4xx Response Codes',
        u'WEB - Total Skype Search Feedback Requests Throttled',
        u'WEB - Skype Search Feedback Requests Throttled Per Second',
        u'WEB - Failed Skype Search Feedback Requests With 5xx Response Codes',
        u'WEB - Failed Skype Search Feedback Requests Per Second With 5xx Response Codes',
        u'WEB - Total Skype Search Requests Next Hop Connection Failures',
        u'WEB - Skype Search Requests Next Hop Connection Failures Per Second',
        u'WEB - Skype Search Or Feedback Requests In Processing',
        u'WEB - Total Skype Search Or Feedback Requests Throttled By Local Server'
    ],
    [
        u'""', u'17740', u'17740', u'17740', u'17740', u'0', u'0', u'34282', u'17740', u'17740',
        u'33925', u'17740', u'8332', u'8332', u'0', u'0', u'9852', u'8332', u'0', u'0', u'7', u'7',
        u'0', u'0', u'15', u'7', u'0', u'0', u'95', u'95', u'0', u'0', u'264', u'95', u'0', u'0',
        u'13', u'13', u'109', u'13', u'11', u'11', u'16', u'11', u'71', u'71', u'139', u'71',
        u'1593', u'1593', u'0', u'0', u'0', u'208', u'222', u'1385', u'7702', u'208', u'1385',
        u'1593', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ], [u'[LS:WEB - Location Information Service]'],
    [
        u'instance', u'WEB - Succeeded Get Locations Requests',
        u'WEB - Succeeded Get Locations Requests/Second',
        u'WEB - Average processing time for a successful Get Locations request in milliseconds',
        u' ', u'WEB - Failed Get Locations Requests', u'WEB - Failed Get Locations Requests/Second',
        u'WEB - Location matches by WAP', u'WEB - Location matches by WAP/Second',
        u'WEB - Location matches by Subnet', u'WEB - Location matches by Subnet/Second',
        u'WEB - Location matches by Switch', u'WEB - Location matches by Switch/Second',
        u'WEB - Location matches by Port', u'WEB - LocationMatchesByPort/Second',
        u'WEB - Location matches by MAC', u'WEB - Location matches by MAC/Second',
        u'WEB - Succeeded Get Locations In City Requests',
        u'WEB - Succeeded Get Locations In City Requests/Second',
        u'WEB - Average processing time for a successful Get Locations In City request in milliseconds',
        u' ', u'WEB - Failed Get Locations In City Requests',
        u'WEB - Failed Get Locations In City Requests/Second'
    ],
    [
        u'""', u'0', u'0', u'0', u'0', u'264', u'264', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ], [u'[LS:WEB - Distribution List Expansion]'],
    [
        u'instance', u'WEB - Valid User Requests', u'WEB - Valid User Requests/sec',
        u'WEB - Request Processing Time', u' ', u'WEB - Pending Active Directory Requests',
        u'WEB - Average Active Directory Fetch time in milliseconds', u' ',
        u'WEB - Pending Requests that fetch member properties',
        u'WEB - Average member properties fetch time in milliseconds', u' ',
        u'WEB - Timed out Active Directory Requests',
        u'WEB - Timed out Active Directory Requests/sec',
        u'WEB - Timed out Requests that fetch member properties',
        u'WEB - Timed out Requests that fetch member properties/sec', u'WEB - Soap Exceptions',
        u'WEB - Soap exceptions/sec', u'WEB - Database Errors', u'WEB - Database Errors/sec',
        u'WEB - MSODS User Requests', u'WEB - MSODS User Requests/sec',
        u'WEB - MSODS Responses that succeeded', u'WEB - MSODS Responses that failed',
        u'WEB - Average MSODS query time in milliseconds', u' ',
        u'WEB - Failed MSODS authorizations attempts', u'WEB - Empty MSODS results received',
        u'WEB - Number of empty results from AD per second', u'WEB - Request Succeeded Count',
        u'WEB - Request Success Rate (%)', u' ', u'WEB - Request Failed Count',
        u'WEB - Request Failed Rate (%)', u' ', u'WEB - Request Exception Count',
        u'WEB - Request Exception Rate (%)', u''
    ],
    [
        u'""', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ], [u'[LS:WEB - UCWA]'],
    [
        u'instance', u'UCWA - Average Lifetime for Session (ms)', u' ',
        u'UCWA - Average Application Startup Time (ms)', u' ', u'UCWA - Active Application Count',
        u'UCWA - Active User Instance Count', u'UCWA - Active User Instances without application',
        u'UCWA - Active Session Count',
        u'UCWA - Active Session Count With Active Presence Subscriptions',
        u'UCWA - HTTP 4xx Responses/Second', u'UCWA - HTTP 5xx Responses/Second',
        u'UCWA - Requests Received/Second', u'UCWA - Requests Succeeded/Second',
        u'UCWA - Application Creation Requests Received/Second',
        u'UCWA - Succeeded Create Application Requests/Second',
        u'UCWA - Total Requests Received on the Command Channel',
        u'UCWA - Total HTTP 4xx Responses', u'UCWA - Total HTTP 5xx Responses',
        u'UCWA - Total Requests Succeeded', u'UCWA - Total Application Creation Requests Received',
        u'UCWA - Total Sessions Initiated',
        u'UCWA - Total Sessions Terminated Because of Idle Timeout',
        u'UCWA - Active Messaging Modality Count', u'UCWA - Active Audio Modality Count',
        u'UCWA - Active Video Modality Count', u'UCWA - Active Panoramic Video Modality Count',
        u'UCWA - Active Application Sharing Modality Count',
        u'UCWA - Active Data Collaboration Modality Count',
        u'UCWA - Exchange HD Photo Get Latency (ms)', u' ',
        u'UCWA - Number of HD Photo Get Failures', u'UCWA - Exchange Contact Search Latency (ms)',
        u' ', u'UCWA - Currently Active Presence Subscription Count',
        u'UCWA - Over The Maximum Subscriptions Per Application',
        u'UCWA - Over The Maximum Subscriptions Per Batch',
        u'UCWA - Retrieving Inband Data Failures', u'UCWA - Presence Subscription Failures',
        u'UCWA - Registering Endpoint Failures', u'UCWA - Total Throttled Applications',
        u'UCWA - IM MCU Join Failures', u'UCWA - AV MCU Join Failures',
        u'UCWA - AS MCU Join Failures', u'UCWA - Data MCU Join Failures',
        u'UCWA - Active Directory Photo Get Latency (ms)', u' ',
        u'UCWA - Number of Active Directory Photo Get Failures',
        u'UCWA - Number of Deserialization Failures', u'UCWA - Exchange Photo Get Requests/Second',
        u'UCWA - Exchange Photo Get Success/Second', u'UCWA - Exchange Photo Get Latency (ms)',
        u' ', u'UCWA - Number of Photo Get Failures', u'UCWA - AD Photo Get Requests/Second',
        u'UCWA - AD Photo Get Success/Second', u'UCWA - Number of Serialization Failures',
        u'UCWA - Number of Presence Publications', u'UCWA - Presence Publications/Second',
        u'UCWA - Number of Presence Deletions', u'UCWA - Presence Deletions/Second',
        u'UCWA - Number of Presence Polling', u'UCWA - Presence Polling/Second',
        u'UCWA - Number of External Presence Subscriptions',
        u'UCWA - Current Number of External Presence Subscriptions',
        u'UCWA - External Presence Subscriptions/Second',
        u'UCWA - Address Book Search Requests/Second',
        u'UCWA - Number of Address Book Search Request Failures',
        u'UCWA - Exchange Search Requests/Second',
        u'UCWA - Number of Exchange Search Request Failures',
        u'UCWA - Number of UCS Subcription failures', u'UCWA - Current Number of AV Calls',
        u'UCWA - Outbound AV Calls/Second', u'UCWA - Number of Outbound AV Call Failures',
        u'UCWA - Inbound AV Calls/Second', u'UCWA - Number of Inbound AV Call Failures',
        u'UCWA - Number of Inbound AV Calls Declined', u'UCWA - Push Notifications/Second',
        u'UCWA - Number of Push Notification Failures',
        u'UCWA - Number of PNCH returned Push Notification Failures',
        u'UCWA - Number of Push Notifications Throttled', u'UCWA - DL Expansion Latency (ms)', u' ',
        u'UCWA - Number of DL Expansion Failures', u'UCWA - DL Expansion Requests/Second',
        u'UCWA - Inbound IM Calls/Second', u'UCWA - Number of Inbound IM Call Failures',
        u'UCWA - Number of Inbound IM Calls Declined', u'UCWA - Outbound IM Calls/Second',
        u'UCWA - Number of Outbound IM Call Failures', u'UCWA - IM Messages Sent/Second',
        u'UCWA - IM Messages Received/Second', u'UCWA - Number of Outgoing IM Message Failures',
        u'UCWA - Number of Incoming IM Message Failures',
        u'UCWA - UCWA Application Instance Lifetime Bucket 0',
        u'UCWA - UCWA Application Instance Lifetime Bucket 1',
        u'UCWA - UCWA Application Instance Lifetime Bucket 2',
        u'UCWA - Total Missed Conversations Pulled from Exchange',
        u'UCWA - Total Archived Conversations Pulled from Exchange',
        u'UCWA - Total Conversations History Requests to Exchange Failed',
        u'UCWA - Total Conversations History Requests to Exchange Succeeded',
        u'UCWA - Exchange Conversation History Request Latency (ms)', u' ',
        u'UCWA - Number of Conversation History Message Format Transcription Failed',
        u'UCWA - Conversation History Message Converted to Plain Text',
        u'UCWA - Total Conversation History Messages Converted to HTML',
        u'UCWA - Total Number of Start Modality Requested',
        u'UCWA - Total Number of Continue Modality Requested',
        u'UCWA - Conversation History Fallbacks To Mail Addresses',
        u'UCWA - Total number of get conversation log requests',
        u'UCWA - Total number of get conversation log batched requests',
        u'UCWA - Total number of get conversation log effective batched requests',
        u'UCWA - Total number of auto accepted incoming messaging invite requests',
        u'UCWA - Total number of auto accepted incoming conference invite requests',
        u'UCWA - Number of Address Book Search Request Succeeded',
        u'UCWA - Number of Exchange Search Request Succeeded'
    ],
    [
        u'_Total', u'295600679', u'463', u'7844247', u'640', u'0', u'0', u'0', u'0', u'0', u'5147',
        u'1', u'22864', u'17716', u'30', u'640', u'22864', u'5147', u'1', u'17716', u'30', u'463',
        u'18', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'4316', u'610', u'0', u'0', u'2185',
        u'867', u'264506', u'2185', u'1318', u'610', u'610', u'0', u'1125', u'1125', u'230', u'230',
        u'248', u'248', u'135', u'0', u'135', u'66', u'0', u'0', u'0', u'0', u'0', u'21', u'1',
        u'1', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'52', u'0', u'0', u'27',
        u'3', u'36', u'10', u'0', u'0', u'0', u'0', u'0', u'255', u'5613', u'10', u'413', u'111947',
        u'352', u'0', u'513', u'0', u'12', u'6', u'33', u'441', u'146', u'44', u'52', u'1', u'66',
        u'0'
    ],
    [
        u'Undefined', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'3140', u'1', u'6489',
        u'3348', u'0', u'0', u'6489', u'3140', u'1', u'3348', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'4316', u'610', u'0', u'0', u'2185', u'867', u'264506', u'2185',
        u'1318', u'610', u'610', u'0', u'1125', u'1125', u'230', u'230', u'248', u'248', u'0', u'0',
        u'0', u'66', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'513', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'66', u'0'
    ],
    [
        u'iPhoneLync', u'177298156', u'282', u'7286806', u'436', u'0', u'0', u'0', u'0', u'0',
        u'1777', u'0', u'13550', u'11773', u'8', u'436', u'13550', u'1777', u'0', u'11773', u'8',
        u'282', u'9', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'96', u'0', u'96',
        u'0', u'0', u'0', u'0', u'0', u'0', u'8', u'1', u'1', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'19', u'0', u'0', u'17', u'3', u'20', u'0', u'0', u'0', u'0', u'0',
        u'0', u'123', u'4173', u'1', u'296', u'83674', u'278', u'0', u'0', u'0', u'12', u'5', u'29',
        u'311', u'121', u'35', u'19', u'0', u'0', u'0'
    ],
    [
        u'AndroidLync', u'76688062', u'119', u'4741', u'138', u'0', u'0', u'0', u'0', u'0', u'91',
        u'0', u'1405', u'1314', u'3', u'138', u'1405', u'91', u'0', u'1314', u'3', u'119', u'4',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'32', u'0', u'32', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'16', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'128',
        u'1236', u'9', u'103', u'25301', u'63', u'0', u'0', u'0', u'0', u'0', u'0', u'97', u'19',
        u'6', u'16', u'1', u'0', u'0'
    ],
    [
        u'LWA', u'13635907', u'16', u'241', u'16', u'0', u'0', u'0', u'0', u'0', u'62', u'0',
        u'523', u'461', u'16', u'16', u'523', u'62', u'0', u'461', u'16', u'16', u'4', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'11', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'9', u'0', u'16', u'10', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0'
    ],
    [
        u'iPadLync', u'27978554', u'46', u'552459', u'50', u'0', u'0', u'0', u'0', u'0', u'77',
        u'0', u'897', u'820', u'3', u'50', u'897', u'77', u'0', u'820', u'3', u'46', u'1', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'7', u'0', u'7', u'0', u'0', u'0',
        u'0', u'0', u'0', u'2', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'17', u'0', u'0', u'1', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'4', u'204',
        u'0', u'14', u'2972', u'11', u'0', u'0', u'0', u'0', u'1', u'4', u'33', u'6', u'3', u'17',
        u'0', u'0', u'0'
    ], [u'[LS:WEB - Mobile Communication Service]'],
    [
        u'instance', u'WEB - Total Session Initiated Count',
        u'WEB - Currently Active Session Count',
        u'WEB - Currently Active Session Count With Active Presence Subscriptions',
        u'WEB - Succeeded Initiate Session Requests/Second',
        u'WEB - Total number of sessions terminated by user',
        u'WEB - Total Sessions Terminated Because of User Idle Timeout',
        u'WEB - Average life time for a session in milliseconds', u' ',
        u'WEB - Total Requests received on the Command Channel', u'WEB - Requests received/Second',
        u'WEB - Total Requests Rejected', u'WEB - Requests Rejected/Second',
        u'WEB - Total Requests Succeeded', u'WEB - Requests Succeeded/Second',
        u'WEB - Total Requests Failed', u'WEB - Requests Failed/Second',
        u'WEB - Currently Active Poll Count', u'WEB - Currently Active Network Timeout Poll Count',
        u'WEB - Total Succesful Outbound Voice Calls', u'WEB - Total Succesful Inbound Voice Calls',
        u'WEB - Total Failed Outbound Voice Calls', u'WEB - Total Failed Inbound Voice Calls',
        u'WEB - Total Declined Inbound Voice Calls',
        u'WEB - Current Push Notification Subscriptions', u'WEB - Total Push Notification Requests',
        u'WEB - Push Notification Requests/Second',
        u'WEB - Total Push Notification Requests Succeeded',
        u'WEB - Push Notification Requests Succeeded/Second',
        u'WEB - Total Push Notification Requests Throttled',
        u'WEB - Push Notification Requests Throttled/Second',
        u'WEB - Total Push Notification Requests Failed',
        u'WEB - Push Notification Requests Failed/Second'
    ],
    [
        u'""', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0'
    ], [u'[LS:WEB - Throttling and Authentication]'],
    [
        u'instance', u'WEB - Unauthenticated Requests In Processing',
        u'WEB - User Authenticated Requests In Processing',
        u'WEB - Conference Authenticated Requests In Processing',
        u'WEB - Total Requests In Processing', u'WEB - Entity Body Reads Outstanding',
        u'WEB - Requests Exceeded Per-App Limit', u'WEB - Requests Exceeded Per-User Limit',
        u'WEB - Requests Exceeded Per-Conference Limit',
        u'WEB - Requests Exceeded Entity Body Read Time', u'WEB - Windows Authentication Requests',
        u'WEB - Windows Authentication Requests/sec',
        u'WEB - Failed Windows Authentication Requests',
        u'WEB - Failed Windows Authentication Requests/sec',
        u'WEB - Certificate Authentication Requests',
        u'WEB - Certificate Authentication Requests/sec',
        u'WEB - Failed Certificate Authentication Requests',
        u'WEB - Failed Certificate Authentication Requests/sec',
        u'WEB - Phone and PIN Authentication Requests',
        u'WEB - Phone and PIN Authentication Requests/sec',
        u'WEB - Failed Phone and PIN Authentication Requests',
        u'WEB - Failed Phone and PIN Authentication Requests/sec',
        u'WEB - Conference ID/PIN Authentication Requests',
        u'WEB - Conference ID/PIN Authentication Requests/sec',
        u'WEB - Failed Conference ID/PIN Authentication Requests',
        u'WEB - Failed Conference ID/PIN Authentication Requests/sec',
        u'WEB - Machine Certificate Authentication Requests',
        u'WEB - Machine Certificate Authentication Requests/sec',
        u'WEB - Failed Machine Certificate Authentication Requests',
        u'WEB - Failed Machine Certificate Authentication Requests/sec',
        u'WEB - WS Federated Authentication Requests',
        u'WEB - WS Federated Authentication Requests/sec',
        u'WEB - Failed WS Federated Authentication Requests',
        u'WEB - Failed WS Federated Authentication Requests/sec',
        u'WEB - Web Ticket Authentication Requests',
        u'WEB - Web Ticket Authentication Requests/sec',
        u'WEB - Failed Web Ticket Authentication Requests',
        u'WEB - Failed Web Ticket Authentication Requests/sec',
        u'WEB - Conference Ticket Authentication Requests',
        u'WEB - Conference Ticket Authentication Requests/sec',
        u'WEB - Failed Conference Ticket Authentication Requests',
        u'WEB - Failed Conference Ticket Authentication Requests/sec',
        u'WEB - Expired Web Tickets Rejected', u'WEB - Expired Web Tickets Rejected/sec',
        u'WEB - Other Server Proof Tickets Rejected',
        u'WEB - Other Server Proof Tickets Rejected/sec',
        u'WEB - Time Skewed Proof Tickets Rejected',
        u'WEB - Time Skewed Proof Tickets Rejected/sec',
        u'WEB - Missing Credential Requests Challenged',
        u'WEB - Missing Credential Requests Challenged/sec', u'WEB - Total Requests',
        u'WEB - Total Requests/sec', u'WEB - WS-Federation Passive Authentication Requests',
        u'WEB - WS-Federation Passive Authentication Requests/sec',
        u'WEB - Failed WS-Federation Passive Authentication Requests',
        u'WEB - Failed WS-Federation Passive Authentication Requests/sec',
        u'WEB - OAuth Token Authentication Requests',
        u'WEB - OAuth Token Authentication Requests/sec',
        u'WEB - Failed OAuth Token Authentication Requests',
        u'WEB - Failed OAuth Token Authentication Requests/sec',
        u'WEB - Internal Mutual TLS Authentication Requests',
        u'WEB - Internal Mutual TLS Authentication Requests/sec',
        u'WEB - Failed Internal Mutual TLS Authentication Requests',
        u'WEB - Failed Internal Mutual TLS Authentication Requests/sec',
        u'WEB - Session Web Ticket Authentication Requests',
        u'WEB - Session Web Ticket Authentication Requests/sec',
        u'WEB - Failed Session Web Ticket Authentication Requests',
        u'WEB - Failed Session Web Ticket Authentication Requests/sec',
        u'WEB - HTTP Proxy Requests', u'WEB - HTTP Proxy Requests/sec',
        u'WEB - Failed HTTP Proxy Requests', u'WEB - Failed HTTP Proxy Requests/sec',
        u'WEB - Number of proxy requests awaiting completion.',
        u'WEB - Deep lookup user Latency (ms)', u' ', u'WEB - Failed Deep Lookup Requests',
        u'WEB - HTTP Proxy Server Request Latency (ms)', u''
    ],
    [
        u'_Total', u'0', u'1', u'0', u'1', u'0', u'0', u'0', u'0', u'0', u'8', u'8', u'0', u'0',
        u'245', u'245', u'0', u'0', u'0', u'0', u'0', u'0', u'2', u'2', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'9242', u'9242', u'43', u'43', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'16167', u'16167', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'6106', u'6106', u'0', u'0', u'7', u'7', u'0', u'0', u'22', u'22',
        u'0', u'0', u'0', u'0', u'11868', u'0', u'0', u'0'
    ],
    [
        u'LM_W3SVC_34578_ROOT_Ucwa', u'0', u'1', u'0', u'1', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'5693', u'5693', u'43', u'43', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'11511', u'11511', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'5802', u'5802', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'11452', u'0', u'0', u'0'
    ],
    [
        u'LM_W3SVC_34577_ROOT_Reach', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'1', u'1', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ],
    [
        u'LM_W3SVC_34578_ROOT_Reach', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'1', u'1', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ],
    [
        u'LM_W3SVC_34577_ROOT_LocationInformation', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'264', u'264', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'378', u'378',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ],
    [
        u'LM_W3SVC_34577_ROOT_RgsClients', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'187', u'187', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'306', u'306', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ],
    [
        u'LM_W3SVC_34577_ROOT_Autodiscover', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'12', u'12', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'62', u'62', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'13', u'13', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'25', u'0', u'0', u'0'
    ],
    [
        u'LM_W3SVC_34577_ROOT_meet', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'4', u'4', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ],
    [
        u'LM_W3SVC_34577_ROOT_DataCollabWeb_wopi', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'7', u'7', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'7', u'7', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ],
    [
        u'LM_W3SVC_34577_ROOT_RequestHandler', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'1', u'1', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ],
    [
        u'LM_W3SVC_34578_ROOT_Autodiscover', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'47', u'47', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'226', u'226', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'63', u'63', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'110', u'0', u'0', u'0'
    ],
    [
        u'LM_W3SVC_34578_ROOT_RgsClients', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'7', u'7', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'11', u'11', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'5', u'5', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'10', u'0', u'0', u'0'
    ],
    [
        u'LM_W3SVC_34578_ROOT_meet', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'27', u'27', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'6', u'6', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ],
    [
        u'LM_W3SVC_34578_ROOT_lwa', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'55', u'55', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'16', u'16', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ],
    [
        u'LM_W3SVC_34578_ROOT_GroupExpansion', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'208', u'208', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'210', u'210', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'110', u'110', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'220', u'0', u'0', u'0'
    ],
    [
        u'LM_W3SVC_34578_ROOT_WebTicket', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'5', u'5', u'0', u'0', u'101', u'101', u'0', u'0', u'0', u'0', u'0', u'0', u'2', u'2',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'210', u'210', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'102', u'102', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'51', u'0', u'0', u'0'
    ],
    [
        u'LM_W3SVC_34577_ROOT_WebTicket', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'3', u'3', u'0', u'0', u'144', u'144', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'276', u'276', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'11', u'11', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ],
    [
        u'LM_W3SVC_34577_ROOT_CertProv', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'3', u'3', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'6', u'6', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ],
    [
        u'LM_W3SVC_34577_ROOT_GroupExpansion', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'2683', u'2683', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'2707', u'2707', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ],
    [
        u'LM_W3SVC_34577_ROOT_Abs_Handler', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'138', u'138', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'168', u'168', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ], [u'[LS:SIP - Protocol]'],
    [
        u'instance', u'SIP - Incoming Messages', u'SIP - Incoming Messages /Sec',
        u'SIP - Incoming Dialog Creating Requests', u'SIP - Incoming Dialog Creating Requests /Sec',
        u'SIP - Incoming Requests Dropped', u'SIP - Incoming Requests Dropped /Sec',
        u'SIP - Incoming Responses Dropped', u'SIP - Incoming Responses Dropped /Sec',
        u'SIP - REGISTER Requests that Failed or Timed Out',
        u'SIP - REGISTER Requests that Failed or Timed Out /Sec', u'SIP - Messages In Server',
        u'SIP - Compressed Server Connections', u'SIP - Compressed Client Connections',
        u'SIP - Incoming Requests In Server', u'SIP - Incoming Responses In Server',
        u'SIP - Local Requests In Server', u'SIP - Local Responses In Server',
        u'SIP - Outgoing Messages', u'SIP - Outgoing Messages /Sec',
        u'SIP - Average Incoming Message Processing Time', u' ',
        u'SIP - Average Local Message Processing Time', u' ', u'SIP - Events In Processing',
        u'SIP - Events Processed /Sec', u'SIP - Events Queued In State Machine',
        u'SIP - Average Event Processing Time', u' ',
        u'SIP - Average Number Of Active Worker Threads', u'SIP - UAS Transactions Outstanding',
        u'SIP - UAS Transactions Timed Out', u'SIP - UAS Transactions Timed Out /Sec',
        u'SIP - UAC Transactions Outstanding', u'SIP - UAC Transactions Timed Out',
        u'SIP - UAC Transactions Timed Out /Sec', u'SIP - Proxy Transactions Outstanding',
        u'SIP - Proxy Transactions Timed Out', u'SIP - Proxy Transactions Timed Out /Sec'
    ],
    [
        u'""', u'2512273', u'2512311', u'1475877', u'1475902', u'813', u'813', u'502', u'502',
        u'2203', u'2203', u'0', u'17', u'53', u'0', u'0', u'0', u'0', u'2842314', u'2842320',
        u'229005714', u'2534318', u'223039244', u'1331487', u'0', u'7849715', u'0', u'1315518577',
        u'7845726', u'1603540', u'0', u'230', u'230', u'0', u'101', u'101', u'0', u'1028', u'1028'
    ], [u'[LS:SIP - Responses]'],
    [
        u'instance', u'SIP - Incoming 1xx (non-100) Responses',
        u'SIP - Incoming 1xx (non-100) Responses /Sec', u'SIP - Incoming 2xx Responses',
        u'SIP - Incoming 2xx Responses /Sec', u'SIP - Incoming 3xx Responses',
        u'SIP - Incoming 3xx Responses /Sec', u'SIP - Incoming 400 Responses',
        u'SIP - Incoming 400 Responses /Sec', u'SIP - Incoming 401 Responses',
        u'SIP - Incoming 401 Responses /Sec', u'SIP - Incoming 403 Responses',
        u'SIP - Incoming 403 Responses /Sec', u'SIP - Incoming 404 Responses',
        u'SIP - Incoming 404 Responses /Sec', u'SIP - Incoming 407 Responses',
        u'SIP - Incoming 407 Responses /Sec', u'SIP - Incoming 408 Responses',
        u'SIP - Incoming 408 Responses /Sec', u'SIP - Incoming 482 Responses',
        u'SIP - Incoming 482 Responses /Sec', u'SIP - Incoming 483 Responses',
        u'SIP - Incoming 483 Responses /Sec', u'SIP - Incoming Other 4xx Responses',
        u'SIP - Incoming Other 4xx Responses /Sec', u'SIP - Incoming 503 Responses',
        u'SIP - Incoming 503 Responses /Sec', u'SIP - Incoming 504 Responses',
        u'SIP - Incoming 504 Responses /Sec', u'SIP - Incoming Other 5xx Responses',
        u'SIP - Incoming Other 5xx Responses /Sec', u'SIP - Incoming 6xx Responses',
        u'SIP - Incoming 6xx Responses /Sec', u'SIP - Local 1xx Responses',
        u'SIP - Local 1xx Responses /Sec', u'SIP - Local 2xx Responses',
        u'SIP - Local 2xx Responses /Sec', u'SIP - Local 3xx Responses',
        u'SIP - Local 3xx Responses /Sec', u'SIP - Local 400 Responses',
        u'SIP - Local 400 Responses /Sec', u'SIP - Local 400 Responses Ratio',
        u'SIP - Local 403 Responses', u'SIP - Local 403 Responses /Sec',
        u'SIP - Local 403 Responses Ratio', u'SIP - Local 404 Responses',
        u'SIP - Local 404 Responses /Sec', u'SIP - Local 404 Responses Ratio',
        u'SIP - Local 408 Responses', u'SIP - Local 408 Responses /Sec',
        u'SIP - Local 408 Responses Ratio', u'SIP - Local 482 Responses',
        u'SIP - Local 482 Responses /Sec', u'SIP - Local 482 Responses Ratio',
        u'SIP - Local 483 Responses', u'SIP - Local 483 Responses /Sec',
        u'SIP - Local 483 Responses Ratio', u'SIP - Local Other 4xx Responses',
        u'SIP - Local 4xx Responses /Sec', u'SIP - Local Other 4xx Responses Ratio',
        u'SIP - Local 500 Responses', u'SIP - Local 500 Responses /Sec',
        u'SIP - Local 500 Responses Ratio', u'SIP - Local 503 Responses',
        u'SIP - Local 503 Responses /Sec', u'SIP - Local 503 Responses Ratio',
        u'SIP - Local 504 Responses', u'SIP - Local 504 Responses /Sec',
        u'SIP - Local 504 Responses Ratio', u'SIP - Local Other 5xx Responses',
        u'SIP - Local 5xx Responses /Sec', u'SIP - Local Other 5xx Responses Ratio',
        u'SIP - Local 6xx Responses', u'SIP - Local 6xx Responses /Sec',
        u'SIP - Local 6xx Responses Ratio'
    ],
    [
        u'""', u'3209', u'3209', u'696923', u'696923', u'94', u'94', u'4575', u'4575', u'0', u'0',
        u'31142', u'31142', u'276268', u'276268', u'0', u'0', u'21', u'21', u'0', u'0', u'0', u'0',
        u'6263', u'6263', u'0', u'0', u'7533', u'7533', u'21', u'21', u'17', u'17', u'16203',
        u'16203', u'430709', u'430715', u'0', u'0', u'140', u'140', u'0', u'217', u'217', u'0',
        u'2141', u'2141', u'0', u'2', u'2', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'46375',
        u'46375', u'0', u'0', u'0', u'0', u'6', u'6', u'0', u'437', u'437', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0'
    ], [u'[LS:SIP - Peers]'],
    [
        u'instance', u'SIP - Connections Active', u'SIP - Inactive Connections Dropped',
        u'SIP - Revoked Connections Dropped',
        u'SIP - Above Limit Connections Dropped (Access Edge Server only)',
        u'SIP - Outgoing Connects Failed', u'SIP - Outgoing TLS Negotiations Failed',
        u'SIP - Sends Outstanding', u'SIP - Sends Timed-Out', u'SIP - Sends Timed-Out /Sec',
        u'SIP - Average Outgoing Queue Delay', u' ',
        u'SIP - Average Number Of Messages In Processing', u'SIP - Flow-controlled Connections',
        u'SIP - Flow-controlled Connections Dropped', u'SIP - Average Flow-Control Delay', u' ',
        u'SIP - Incoming Requests', u'SIP - Incoming Requests /Sec', u'SIP - Incoming Responses',
        u'SIP - Incoming Responses /Sec', u'SIP - Outgoing Requests',
        u'SIP - Outgoing Requests /Sec', u'SIP - Outgoing Responses',
        u'SIP - Outgoing Responses /Sec',
        u'SIP - Requests Rejected Due To User Limits Exceeded (Access Edge Server only)',
        u'SIP - Messages To Federated Partners Throttled Due to Frequent Connectivity Failures',
        u'SIP - Messages To Federated Partners Throttled Due to Frequent Connectivity Failures /Sec'
    ],
    [
        u'_Total', u'95', u'29186', u'0', u'0', u'237', u'0', u'0', u'0', u'0', u'4103288425',
        u'10344', u'102449654', u'0', u'0', u'0', u'0', u'1475950', u'1475151', u'1036352',
        u'1036352', u'1356931', u'1356935', u'1484234', u'1484249', u'0', u'0', u'0'
    ],
    [
        u'Clients', u'29', u'61', u'0', u'0', u'237', u'0', u'0', u'0', u'0', u'3719588120',
        u'3419', u'66025479', u'0', u'0', u'0', u'0', u'747275', u'747273', u'445107', u'445107',
        u'744094', u'744098', u'724529', u'724529', u'0', u'0', u'0'
    ],
    [
        u'pbwvw-skype03', u'18', u'2432', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'83298406',
        u'1937', u'25567524', u'0', u'0', u'0', u'0', u'333085', u'332315', u'110994', u'110994',
        u'114096', u'114096', u'333930', u'333943', u'0', u'0', u'0'
    ],
    [
        u'edge', u'14', u'1514', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'175675572', u'2983',
        u'4440807', u'0', u'0', u'0', u'0', u'65210', u'65210', u'379519', u'379519', u'379900',
        u'379900', u'65862', u'65862', u'0', u'0', u'0'
    ],
    [
        u'pbwvw-skype01', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ],
    [
        u'pbwvw-skype02', u'0', u'1', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'3', u'2381',
        u'0', u'0', u'0', u'0', u'69', u'69', u'0', u'0', u'0', u'0', u'71', u'71', u'0', u'0', u'0'
    ],
    [
        u'pbwvw-stapp01', u'6', u'2106', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'28281202',
        u'461', u'2759567', u'0', u'0', u'0', u'0', u'21885', u'21859', u'1124', u'1124', u'3804',
        u'3804', u'22077', u'22078', u'0', u'0', u'0'
    ],
    [
        u'0.0.0.0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ],
    [
        u'pbwvw-skype04', u'9', u'1023', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'45999760',
        u'905', u'353869', u'0', u'0', u'0', u'0', u'253916', u'253915', u'97641', u'97641',
        u'97624', u'97624', u'253840', u'253841', u'0', u'0', u'0'
    ],
    [
        u'outlook', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'50025',
        u'0', u'0', u'0', u'0', u'818', u'818', u'0', u'0', u'0', u'0', u'818', u'818', u'0', u'0',
        u'0'
    ],
    [
        u'pbwvw-stapp02', u'4', u'12', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'43492372',
        u'570', u'2455625', u'0', u'0', u'0', u'0', u'24186', u'24186', u'1500', u'1500', u'16970',
        u'16970', u'24186', u'24186', u'0', u'0', u'0'
    ],
    [
        u'pbwvw-exchg02', u'2', u'3662', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'3327524',
        u'32', u'374704', u'0', u'0', u'0', u'0', u'5048', u'5048', u'262', u'262', u'244', u'244',
        u'10079', u'10079', u'0', u'0', u'0'
    ],
    [
        u'pbwvw-exchg01', u'2', u'3643', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'371775', u'4',
        u'101531', u'0', u'0', u'0', u'0', u'4924', u'4924', u'24', u'24', u'24', u'24', u'9832',
        u'9832', u'0', u'0', u'0'
    ],
    [
        u'pbwaw-exchg02', u'3', u'3550', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'703999', u'6',
        u'56435', u'0', u'0', u'0', u'0', u'4876', u'4876', u'28', u'28', u'28', u'28', u'9740',
        u'9740', u'0', u'0', u'0'
    ],
    [
        u'pbwbw-exchg01', u'3', u'3742', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'986128', u'10',
        u'36080', u'0', u'0', u'0', u'0', u'4888', u'4888', u'79', u'79', u'74', u'74', u'9754',
        u'9754', u'0', u'0', u'0'
    ],
    [
        u'pbwbw-exchg02', u'2', u'3618', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'1030952', u'8',
        u'154928', u'0', u'0', u'0', u'0', u'4895', u'4895', u'48', u'48', u'47', u'47', u'9778',
        u'9778', u'0', u'0', u'0'
    ],
    [
        u'pbwaw-exchg01', u'3', u'3822', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'532615', u'6',
        u'70699', u'0', u'0', u'0', u'0', u'4875', u'4875', u'26', u'26', u'26', u'26', u'9738',
        u'9738', u'0', u'0', u'0'
    ], [u'[LS:SIP - Load Management]'],
    [
        u'instance', u'SIP - Average Holding Time For Incoming Messages', u' ',
        u'SIP - Incoming Messages Held', u'SIP - Incoming Messages Held Above Low Watermark',
        u'SIP - Incoming Messages Held Above High Watermark',
        u'SIP - Incoming Messages Held Above Overload Watermark',
        u'SIP - Incoming Messages Timed out', u'SIP - Low Watermark', u'SIP - High Watermark',
        u'SIP - Address space usage', u'SIP - Page file usage'
    ],
    [u'""', u'1510747184', u'2960375', u'0', u'0', u'0', u'0', u'0', u'250', u'500', u'0', u'41'],
    [u'[LS:DATAMCU - MCU Health And Performance]'],
    [
        u'instance', u'DATAMCU - HTTP Stack load', u'DATAMCU - HTTP Stack state',
        u'DATAMCU - Thread Pool Load', u'DATAMCU - Thread Pool Health State',
        u'DATAMCU - Thread Pool Unhandled Exceptions', u'DATAMCU - MCU Health State',
        u'DATAMCU - MCU Draining State', u'DATAMCU - MCU Health State Changed Count',
        u'DATAMCU - MCU Health DNS resolution failure Count',
        u'DATAMCU - MCU Health DNS resolution succeeded Count'
    ], [u'""', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'2587'],
    [u'[LS:AVMCU - MCU Health And Performance]'],
    [
        u'instance', u'AVMCU - HTTP Stack load', u'AVMCU - HTTP Stack state',
        u'AVMCU - Thread Pool Load', u'AVMCU - Thread Pool Health State',
        u'AVMCU - Thread Pool Unhandled Exceptions', u'AVMCU - MCU Health State',
        u'AVMCU - MCU Draining State', u'AVMCU - MCU Health State Changed Count',
        u'AVMCU - MCU Health DNS resolution failure Count',
        u'AVMCU - MCU Health DNS resolution succeeded Count'
    ], [u'""', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'2587'],
    [u'[LS:AsMcu - MCU Health And Performance]'],
    [
        u'instance', u'ASMCU - HTTP Stack load', u'ASMCU - HTTP Stack state',
        u'ASMCU - Thread Pool Load', u'ASMCU - Thread Pool Health State',
        u'ASMCU - Thread Pool Unhandled Exceptions', u'ASMCU - MCU Health State',
        u'ASMCU - MCU Draining State', u'ASMCU - MCU Health State Changed Count',
        u'ASMCU - MCU Health DNS resolution failure Count',
        u'ASMCU - MCU Health DNS resolution succeeded Count'
    ], [u'""', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'2587'],
    [u'[LS:ImMcu - MCU Health And Performance]'],
    [
        u'instance', u'IMMCU - HTTP Stack load', u'IMMCU - HTTP Stack state',
        u'IMMCU - Thread Pool Load', u'IMMCU - Thread Pool Health State',
        u'IMMCU - Thread Pool Unhandled Exceptions', u'IMMCU - MCU Health State',
        u'IMMCU - MCU Draining State', u'IMMCU - MCU Health State Changed Count',
        u'IMMCU - MCU Health DNS resolution failure Count',
        u'IMMCU - MCU Health DNS resolution succeeded Count'
    ], [u'""', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'2587'],
    [u'[LS:USrv - DBStore]'],
    [
        u'instance', u'USrv - Queue Depth', u' ', u'USrv - Queue Latency (msec)', u' ',
        u'USrv - Sproc Latency (msec)', u' ', u'USrv - % Database Time', u' ',
        u'USrv - Threads Waiting for New Database Requests',
        u'USrv - Threads Executing Database Operations',
        u'USrv - Threads Calling Back with Database Results', u'USrv - Blocked Client Threads',
        u' ', u'USrv - Total Deadlocks', u'USrv - Total Dropped Requests',
        u'USrv - Total Deadlock Failures', u'USrv - Total Transaction Count Mismatch Failures',
        u'USrv - Total ODBC Timeout Failures', u'USrv - Total severe SQL errors',
        u'USrv - Total fatal SQL errors', u'USrv - Throttled requests/sec',
        u'USrv - Total throttled requests', u'USrv - Database connection status',
        u'USrv - Sproc Calls/sec', u'USrv - Total sproc calls', u'USrv - Database failover count'
    ],
    [
        u'""', u'524', u'1132983', u'238138', u'1135722', u'4967352', u'1135722', u'3081699',
        u'31859', u'10', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'1', u'1103251', u'1103251', u'0'
    ], [u'[LS:MediationServer - Health Indices]'], [u'instance', u'- Load Call Failure Index'],
    [u'""', u'0'], [u'[LS:MediationServer - Global Counters]'],
    [
        u'instance', u'- Current audio channels with PSM quality reporting',
        u'- Total failed calls caused by unexpected interaction from the Proxy',
        u'- Current number of ports opened on the gateway side',
        u'- Total number of timer timeouts that are exceeding the predefined threshold'
    ], [u'""', u'1', u'5', u'1', u'0'], [u'[LS:MediationServer - Global Per Gateway Counters]'],
    [u'instance', u'- Total failed calls caused by unexpected interaction from a gateway'],
    [u'_Total', u'0'], [u'pbwva-vgate01.intern.rossmann.de', u'0'],
    [u'pbwva-vgate01.intern.rossmann.de;trunk=pbwva-vgate01.intern.rossmann.de', u'0'],
    [u'[LS:MediationServer - Media Relay]'],
    [u'instance', u'- Candidates Missing', u'- Media Connectivity Check Failure'],
    [u'""', u'0', u'0'], [u'[LS:A/V Auth - Requests]'],
    [
        u'instance', u'- Credentials Issued', u'- Credentials Issued/sec',
        u'- Bad Requests Received', u'- Bad Requests Received/sec', u'- Current requests serviced'
    ], [u'""', u'0', u'0', u'0', u'0', u'0'], [u'[ASP.NET Apps v4.0.30319]'],
    [
        u'instance', u'Anonymous Requests', u'Anonymous Requests/Sec', u'Cache Total Entries',
        u'Cache Total Turnover Rate', u'Cache Total Hits', u'Cache Total Misses',
        u'Cache Total Hit Ratio', u'Cache Total Hit Ratio Base', u'Cache API Entries',
        u'Cache API Turnover Rate', u'Cache API Hits', u'Cache API Misses', u'Cache API Hit Ratio',
        u'Cache API Hit Ratio Base', u'Output Cache Entries', u'Output Cache Turnover Rate',
        u'Output Cache Hits', u'Output Cache Misses', u'Output Cache Hit Ratio',
        u'Output Cache Hit Ratio Base', u'Compilations Total', u'Debugging Requests',
        u'Errors During Preprocessing', u'Errors During Compilation', u'Errors During Execution',
        u'Errors Unhandled During Execution', u'Errors Unhandled During Execution/Sec',
        u'Errors Total', u'Errors Total/Sec', u'Pipeline Instance Count', u'Request Bytes In Total',
        u'Request Bytes Out Total', u'Requests Executing', u'Requests Failed',
        u'Requests Not Found', u'Requests Not Authorized', u'Requests In Application Queue',
        u'Requests Timed Out', u'Requests Succeeded', u'Requests Total', u'Requests/Sec',
        u'Sessions Active', u'Sessions Abandoned', u'Sessions Timed Out', u'Sessions Total',
        u'Transactions Aborted', u'Transactions Committed', u'Transactions Pending',
        u'Transactions Total', u'Transactions/Sec', u'Session State Server connections total',
        u'Session SQL Server connections total', u'Events Raised', u'Events Raised/Sec',
        u'Application Lifetime Events', u'Application Lifetime Events/Sec', u'Error Events Raised',
        u'Error Events Raised/Sec', u'Request Error Events Raised',
        u'Request Error Events Raised/Sec', u'Infrastructure Error Events Raised',
        u'Infrastructure Error Events Raised/Sec', u'Request Events Raised',
        u'Request Events Raised/Sec', u'Audit Success Events Raised',
        u'Audit Failure Events Raised', u'Membership Authentication Success',
        u'Membership Authentication Failure', u'Forms Authentication Success',
        u'Forms Authentication Failure', u'Viewstate MAC Validation Failure',
        u'Request Execution Time', u'Requests Disconnected', u'Requests Rejected',
        u'Request Wait Time', u'Cache % Machine Memory Limit Used',
        u'Cache % Machine Memory Limit Used Base', u'Cache % Process Memory Limit Used',
        u'Cache % Process Memory Limit Used Base', u'Cache Total Trims', u'Cache API Trims',
        u'Output Cache Trims', u'% Managed Processor Time (estimated)',
        u'% Managed Processor Time Base (estimated)', u'Managed Memory Used (estimated)',
        u'Request Bytes In Total (WebSockets)', u'Request Bytes Out Total (WebSockets)',
        u'Requests Executing (WebSockets)', u'Requests Failed (WebSockets)',
        u'Requests Succeeded (WebSockets)', u'Requests Total (WebSockets)'
    ],
    [
        u'__Total__', u'4020', u'4020', u'223', u'177475', u'246152', u'89212', u'246152',
        u'335364', u'8', u'12', u'637', u'19', u'637', u'656', u'0', u'0', u'0', u'0', u'0', u'0',
        u'104', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'49', u'22591387', u'59046000',
        u'1', u'17774', u'2629', u'12645', u'0', u'0', u'11384', u'29159', u'29159', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'16591', u'16591', u'232', u'232',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'16359', u'0', u'0', u'0', u'0', u'0',
        u'0', u'586100', u'0', u'0', u'0', u'875', u'2475', u'22933', u'503303275', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ],
    [
        u'_LM_W3SVC_34577_ROOT_LocationInformation', u'378', u'378', u'8', u'1008', u'778', u'519',
        u'778', u'1297', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'1', u'1062329', u'2619756', u'0',
        u'0', u'0', u'0', u'0', u'0', u'378', u'378', u'378', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'542', u'542', u'1', u'1', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'541', u'0', u'0', u'0', u'0', u'0', u'0', u'8', u'0', u'0', u'0', u'35',
        u'99', u'0', u'20132131', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0'
    ],
    [
        u'_LM_W3SVC_34578_ROOT_Autodiscover', u'59', u'59', u'10', u'788', u'921', u'409', u'921',
        u'1330', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'1', u'0', u'299231', u'0', u'57', u'0', u'57',
        u'0', u'0', u'169', u'226', u'226', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'229', u'229', u'1', u'1', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'228', u'0', u'0', u'0', u'0', u'0', u'0', u'3', u'0', u'0', u'0', u'35', u'99', u'1033',
        u'20132131', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ],
    [
        u'_LM_W3SVC_34578_ROOT_lwa', u'4', u'4', u'7', u'379', u'350', u'207', u'350', u'557', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'1', u'0', u'5712217', u'0', u'2', u'2', u'0', u'0', u'0',
        u'53', u'55', u'55', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'5',
        u'5', u'1', u'1', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'4', u'0', u'0', u'0',
        u'0', u'0', u'0', u'1', u'0', u'0', u'0', u'35', u'99', u'919', u'20132131', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ],
    [
        u'_LM_W3SVC_34577_ROOT_Reach', u'0', u'0', u'8', u'60', u'147', u'56', u'147', u'203', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'1', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'1', u'0', u'0', u'0', u'1', u'0', u'1', u'0', u'0', u'0',
        u'1', u'1', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'3', u'3',
        u'3', u'3', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'174', u'0', u'0', u'0', u'35', u'99', u'983', u'20132131', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ],
    [
        u'_LM_W3SVC_34577_ROOT_cscp', u'0', u'0', u'14', u'198', u'1510', u'129', u'1510', u'1639',
        u'8', u'12', u'637', u'19', u'637', u'656', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'1', u'41663', u'99355', u'0', u'10', u'1', u'9',
        u'0', u'0', u'284', u'294', u'294', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'1', u'1', u'1', u'1', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'35', u'99', u'0', u'20132131',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ],
    [
        u'_LM_W3SVC_34577_ROOT_Autodiscover', u'24', u'24', u'10', u'336', u'353', u'183', u'353',
        u'536', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'2', u'0', u'95742', u'0', u'13', u'0', u'13',
        u'0', u'0', u'49', u'62', u'62', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'74', u'74', u'1', u'1', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'73', u'0',
        u'0', u'0', u'0', u'0', u'0', u'2', u'0', u'0', u'0', u'35', u'99', u'0', u'20132131', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ],
    [
        u'_LM_W3SVC_34577_ROOT_RequestHandler', u'1', u'1', u'4', u'28', u'69', u'26', u'69', u'95',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'1', u'549', u'115', u'0', u'0', u'0', u'0', u'0',
        u'0', u'1', u'1', u'1', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'3', u'3', u'1', u'1', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'2', u'0', u'0',
        u'0', u'0', u'0', u'0', u'161', u'0', u'0', u'0', u'35', u'99', u'0', u'20132131', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ],
    [
        u'_LM_W3SVC_34578_ROOT_Abs', u'0', u'0', u'4', u'22', u'12538', u'23', u'12538', u'12561',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'2', u'0', u'0', u'0', u'12462', u'0', u'12462', u'0',
        u'0', u'0', u'12462', u'12462', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'1', u'1', u'1', u'1', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'35', u'99', u'0', u'20132131', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ],
    [
        u'_LM_W3SVC_34578_ROOT_GroupExpansion', u'100', u'100', u'5', u'181', u'473', u'104',
        u'473', u'577', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'1', u'980445', u'671267', u'0',
        u'0', u'0', u'0', u'0', u'0', u'210', u'210', u'210', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'233', u'233', u'1', u'1', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'232', u'0', u'0', u'0', u'0', u'0', u'0', u'8', u'0', u'0', u'0', u'35',
        u'99', u'0', u'20132131', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0'
    ],
    [
        u'_LM_W3SVC_34577_ROOT_Abs', u'0', u'0', u'40', u'602', u'488', u'331', u'488', u'819',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'2', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'138', u'138', u'138', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'1', u'1', u'1', u'1', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'35', u'99', u'1052', u'20132131', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ],
    [
        u'_LM_W3SVC_34577_ROOT', u'0', u'0', u'3', u'211', u'200', u'117', u'200', u'317', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'1', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'32',
        u'32', u'32', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'1', u'1',
        u'1', u'1', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'35', u'99', u'0', u'20132131', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ],
    [
        u'_LM_W3SVC_34578_ROOT_Ucwa', u'0', u'0', u'4', u'170444', u'220886', u'85285', u'220886',
        u'306171', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'2', u'4992207', u'27042896', u'1',
        u'5185', u'2626', u'59', u'0', u'0', u'6325', u'11511', u'11511', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'11452', u'11452', u'1', u'1', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'11451', u'0', u'0', u'0', u'0', u'0', u'0', u'585289', u'0',
        u'0', u'0', u'35', u'99', u'10035', u'20132131', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0'
    ],
    [
        u'_LM_W3SVC_34578_ROOT_Reach', u'0', u'0', u'8', u'60', u'147', u'56', u'147', u'203', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'1', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'1', u'0', u'0', u'0', u'1', u'0', u'1', u'0', u'0', u'0',
        u'1', u'1', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'3', u'3',
        u'3', u'3', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'163', u'0', u'0', u'0', u'35', u'99', u'981', u'20132131', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ],
    [
        u'_LM_W3SVC_34577_ROOT_WebTicket', u'270', u'270', u'5', u'717', u'590', u'372', u'590',
        u'962', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'1', u'801128', u'3286709', u'0', u'3', u'0',
        u'3', u'0', u'0', u'273', u'276', u'276', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'381', u'381', u'1', u'1', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'380', u'0', u'0', u'0', u'0', u'0', u'0', u'25', u'0', u'0', u'0', u'35', u'99',
        u'0', u'20132131', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ],
    [
        u'_LM_W3SVC_34577_ROOT_GroupExpansion', u'2707', u'2707', u'6', u'122', u'3381', u'75',
        u'3381', u'3456', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'9', u'13354163', u'14215371', u'0',
        u'0', u'0', u'0', u'0', u'0', u'2707', u'2707', u'2707', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'2723', u'2723', u'1', u'1', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'2722', u'0', u'0', u'0', u'0', u'0', u'0', u'5', u'0', u'0', u'0',
        u'35', u'99', u'3706', u'20132131', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0'
    ],
    [
        u'_LM_W3SVC_34577_ROOT_Ucwa', u'0', u'0', u'4', u'24', u'49', u'24', u'49', u'73', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'35', u'99', u'447', u'20132131', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ],
    [
        u'_LM_W3SVC_34577_ROOT_DataCollabWeb_wopi', u'0', u'0', u'5', u'37', u'92', u'31', u'92',
        u'123', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'1', u'0', u'484259', u'0', u'0', u'0', u'0',
        u'0', u'0', u'7', u'7', u'7', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'8', u'8', u'1', u'1', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'7', u'0',
        u'0', u'0', u'0', u'0', u'0', u'2', u'0', u'0', u'0', u'35', u'99', u'0', u'20132131', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ],
    [
        u'_LM_W3SVC_34578_ROOT', u'0', u'0', u'3', u'31', u'125', u'27', u'125', u'152', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'1', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'61', u'61',
        u'61', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'1', u'1', u'1',
        u'1', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'35', u'99', u'1038', u'20132131', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ],
    [
        u'_LM_W3SVC_34578_ROOT_meet', u'5', u'5', u'7', u'285', u'586', u'162', u'586', u'748',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'51', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'1', u'0', u'172965', u'0', u'0', u'0', u'0', u'0',
        u'0', u'27', u'27', u'27', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'108', u'108', u'103', u'103', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'5', u'0',
        u'0', u'0', u'0', u'0', u'0', u'2', u'0', u'0', u'0', u'35', u'99', u'1853', u'20132131',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ],
    [
        u'_LM_W3SVC_34577_ROOT_RgsClients', u'306', u'306', u'10', u'770', u'662', u'402', u'662',
        u'1064', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'1', u'752085', u'2607922', u'0', u'0', u'0',
        u'0', u'0', u'0', u'306', u'306', u'306', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'429', u'429', u'1', u'1', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'428', u'0', u'0', u'0', u'0', u'0', u'0', u'20', u'0', u'0', u'0', u'35', u'99',
        u'0', u'20132131', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ],
    [
        u'_LM_W3SVC_34577_ROOT_meet', u'4', u'4', u'6', u'170', u'470', u'103', u'470', u'573',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'51', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'1', u'0', u'3846', u'0', u'0', u'0', u'0', u'0', u'0',
        u'4', u'4', u'4', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'107',
        u'107', u'103', u'103', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'4', u'0', u'0',
        u'0', u'0', u'0', u'0', u'65', u'0', u'0', u'0', u'35', u'99', u'0', u'20132131', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ],
    [
        u'_LM_W3SVC_34577_ROOT_Abs_Handler', u'0', u'0', u'35', u'311', u'597', u'183', u'597',
        u'780', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'14', u'0', u'0', u'0', u'30', u'0', u'30', u'0',
        u'0', u'138', u'168', u'168', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'1', u'1', u'1', u'1', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'30', u'0', u'0', u'0', u'35', u'99', u'0', u'20132131',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ],
    [
        u'_LM_W3SVC_34578_ROOT_RgsClients', u'6', u'6', u'7', u'79', u'137', u'55', u'137', u'192',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'1', u'27726', u'87838', u'0', u'0', u'0', u'0', u'0',
        u'0', u'11', u'11', u'11', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'17', u'17', u'1', u'1', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'16', u'0', u'0',
        u'0', u'0', u'0', u'0', u'25', u'0', u'0', u'0', u'35', u'99', u'886', u'20132131', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ],
    [
        u'_LM_W3SVC_34577_ROOT_CertProv', u'6', u'6', u'5', u'49', u'89', u'38', u'89', u'127',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'1', u'21702', u'118505', u'0', u'0', u'0', u'0', u'0',
        u'0', u'6', u'6', u'6', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'10', u'10', u'1', u'1', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'9', u'0', u'0',
        u'0', u'0', u'0', u'0', u'106', u'0', u'0', u'0', u'35', u'99', u'0', u'20132131', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ],
    [
        u'_LM_W3SVC_34578_ROOT_WebTicket', u'150', u'150', u'5', u'563', u'514', u'295', u'514',
        u'809', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'1', u'557390', u'1528006', u'0', u'10', u'0',
        u'10', u'0', u'0', u'205', u'215', u'215', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'258', u'258', u'1', u'1', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'0', u'257', u'0', u'0', u'0', u'0', u'0', u'0', u'11', u'0', u'0', u'0', u'35', u'99',
        u'0', u'20132131', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0'
    ]
]

discovery = {
    '': [(None, None)],
    'conferencing': [],
    'data_proxy': [],
    'edge': [],
    'edge_auth': [(None, None)],
    'mcu': [(None, None)],
    'mediation_server': [(None, None)],
    'mobile': [(None, None)],
    'sip_stack': [(None, None)],
    'xmpp_proxy': []
}

checks = {
    '': [(None, {
        'failed_locations_requests': {
            'upper': (1.0, 2.0)
        },
        'failed_file_requests': {
            'upper': (1.0, 2.0)
        },
        'join_failures': {
            'upper': (1, 2)
        },
        'asp_requests_rejected': {
            'upper': (1, 2)
        },
        'failed_validate_cert': {
            'upper': (1, 2)
        },
        'failed_search_requests': {
            'upper': (1.0, 2.0)
        },
        '5xx_responses': {
            'upper': (1.0, 2.0)
        },
        'timedout_ad_requests': {
            'upper': (0.01, 0.02)
        }
    }, [(0, 'Failed search requests/sec: 0.00', [('failed_search_requests', 0.0, 1.0, 2.0, None,
                                                 None)]),
        (0, 'Failed location requests/sec: 0.00', [('failed_location_requests', 0.0, 1.0, 2.0, None,
                                                   None)]),
        (0, 'Timeout AD requests/sec: 0.00', [('failed_ad_requests', 0.0, 0.01, 0.02, None, None)]),
        (0, 'HTTP 5xx/sec: 0.00', [('http_5xx', 0.0, 1.0, 2.0, None, None)]),
        (0, 'Requests rejected: 0', [('asp_requests_rejected', 0.0, 1, 2, None, None)])])],
    'edge_auth': [(None, {
        'bad_requests': {
            'upper': (20, 40)
        }
    }, [(0, 'Bad requests/sec: 0.00', [('avauth_failed_requests', 0.0, 20, 40, None, None)])])],
    'mcu': [(None, {}, [(0, 'DATAMCU: Normal', []), (0, 'AVMCU: Normal', []),
                        (0, 'ASMCU: Normal', []), (0, 'IMMCU: Normal', [])])],
    'mediation_server': [(None, {
        'failed_calls_because_of_proxy': {
            'upper': (10, 20)
        },
        'load_call_failure_index': {
            'upper': (10, 20)
        },
        'media_connectivity_failure': {
            'upper': (1, 2)
        },
        'failed_calls_because_of_gateway': {
            'upper': (10, 20)
        }
    }, [(0, 'Load call failure index: 0', [('mediation_load_call_failure_index', 0.0, 10, 20, None,
                                           None)]),
        (0, 'Failed calls because of proxy: 5', [('mediation_failed_calls_because_of_proxy', 5.0, 10,
                                                 20, None, None)]),
        (0, 'Failed calls because of gateway: 0', [('mediation_failed_calls_because_of_gateway', 0.0,
                                                   10, 20, None, None)]),
        (0, 'Media connectivity check failure: 0', [('mediation_media_connectivity_failure', 0.0, 1,
                                                    2, None, None)])])],
    'mobile': [(None, {
        'requests_processing': {
            'upper': (10000, 20000)
        }
    }, [(0, 'Android: 0 active', [('ucwa_active_sessions_android', 0.0, None, None, None, None)]),
        (0, 'iPad: 0 active', [('ucwa_active_sessions_ipad', 0.0, None, None, None, None)]),
        (0, 'iPhone: 0 active', [('ucwa_active_sessions_iphone', 0.0, None, None, None, None)]),
        (0, 'Requested: 1', [('web_requests_processing', 1.0, 10000, 20000, None, None)])])],
    'sip_stack': [(None, {
        'authentication_errors': {
            'upper': (1, 2)
        },
        'timedout_incoming_messages': {
            'upper': (2, 4)
        },
        'local_503_responses': {
            'upper': (0.01, 0.02)
        },
        'outgoing_queue_delay': {
            'upper': (2.0, 4.0)
        },
        'incoming_requests_dropped': {
            'upper': (1.0, 2.0)
        },
        'queue_latency': {
            'upper': (0.0001, 0.2)
        },
        'message_processing_time': {
            'upper': (1.0, 2.0)
        },
        'sproc_latency': {
            'upper': (0.1, 0.2)
        },
        'throttled_requests': {
            'upper': (0.2, 0.4)
        },
        'holding_time_incoming': {
            'upper': (6.0, 12.0)
        },
        'incoming_responses_dropped': {
            'upper': (1.0, 2.0)
        },
        'flow_controlled_connections': {
            'upper': (1, 2)
        },
        'timedout_sends': {
            'upper': (0.01, 0.02)
        }
    }, [(0, 'Avg incoming message processing time: 0.00', [('sip_message_processing_time', 0.0, 1.0,
                                                           2.0, None, None)]),
        (0, 'Incoming responses dropped/sec: 0.00', [('sip_incoming_responses_dropped', 0.0, 1.0,
                                                     2.0, None, None)]),
        (0, 'Incoming requests dropped/sec: 0.00', [('sip_incoming_requests_dropped', 0.0, 1.0, 2.0,
                                                    None, None)]),
        (1, u'Queue latency: 210 microseconds (warn/crit at 100 microseconds/200 milliseconds)',
         [('usrv_queue_latency', 0.00020967983362125592, 0.0001, 0.2, None, None)]),
        (0, u'Sproc latency: 1 microsecond', [('usrv_sproc_latency', 1.1562460162588214e-06, 0.1, 0.2, None,
                                       None)]),
        (0, 'Throttled requests/sec: 0.00', [('usrv_throttled_requests', 0.0, 0.2, 0.4, None,
                                             None)]),
        (0, 'Local 503 responses/sec: 0.00', [('sip_503_responses', 0.0, 0.01, 0.02, None, None)]),
        (0, 'Incoming messages timed out: 0', [('sip_incoming_messages_timed_out', 0.0, 2, 4, None,
                                               None)]),
        (0, 'Avg holding time for incoming messages: 0.00',
         [('sip_avg_holding_time_incoming_messages', 0.0, 6.0, 12.0, None, None)]),
        (0, 'Flow-controlled connections: 0', [('sip_flow_controlled_connections', 0.0, 1, 2, None,
                                               None)]),
        (0, 'Avg outgoing queue delay: 0.00', [('sip_avg_outgoing_queue_delay', 0.0, 2.0, 4.0, None,
                                               None)]),
        (0, 'Sends timed out/sec: 0.00', [('sip_sends_timed_out', 0.0, 0.01, 0.02, None, None)])])]
}
