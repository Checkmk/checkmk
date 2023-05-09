#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'msexch_isclienttype'

info = [
    [
        u'AdministrativeRPCrequestsPersec', u'AdminRPCRequests', u'Caption', u'Description',
        u'DirectoryAccessLDAPSearchesPersec', u'Frequency_Object', u'Frequency_PerfTime',
        u'Frequency_Sys100NS', u'JetLogRecordBytesPersec', u'JetLogRecordsPersec',
        u'JetPagesModifiedPersec', u'JetPagesPrereadPersec', u'JetPagesReadPersec',
        u'JetPagesReferencedPersec', u'JetPagesRemodifiedPersec', u'LazyindexescreatedPersec',
        u'LazyindexesdeletedPersec', u'LazyindexfullrefreshPersec',
        u'LazyindexincrementalrefreshPersec', u'MessagescreatedPersec', u'MessagesdeletedPersec',
        u'MessagesopenedPersec', u'MessagesupdatedPersec', u'Name', u'PropertypromotionsPersec',
        u'RPCAverageLatency', u'RPCAverageLatency_Base', u'RPCBytesReceivedPersec',
        u'RPCBytesSentPersec', u'RPCOperationsPersec', u'RPCPacketsPersec', u'RPCRequests',
        u'Timestamp_Object', u'Timestamp_PerfTime', u'Timestamp_Sys100NS'
    ],
    [
        u'0', u'0', u'', u'', u'0', u'0', u'1953125', u'10000000', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'hrc', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'6743176285319', u'130951777565340000'
    ],
    [
        u'0', u'0', u'', u'', u'0', u'0', u'1953125', u'10000000', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'officegraph', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'6743176285319', u'130951777565340000'
    ],
    [
        u'0', u'0', u'', u'', u'0', u'0', u'1953125', u'10000000', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'publicfolderhierarchyreplication', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'6743176285319', u'130951777565340000'
    ],
    [
        u'0', u'0', u'', u'', u'0', u'0', u'1953125', u'10000000', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'unifiedauditing', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'6743176285319', u'130951777565340000'
    ],
    [
        u'0', u'0', u'', u'', u'0', u'0', u'1953125', u'10000000', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'snackyservice', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'6743176285319', u'130951777565340000'
    ],
    [
        u'0', u'0', u'', u'', u'0', u'0', u'1953125', u'10000000', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'addriver', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'6743176285319', u'130951777565340000'
    ],
    [
        u'0', u'0', u'', u'', u'0', u'0', u'1953125', u'10000000', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'liveidbasicauth', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'6743176285319', u'130951777565340000'
    ],
    [
        u'0', u'0', u'', u'', u'0', u'0', u'1953125', u'10000000', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'pop', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'6743176285319', u'130951777565340000'
    ],
    [
        u'0', u'0', u'', u'', u'0', u'0', u'1953125', u'10000000', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'notificationbroker', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'6743176285319', u'130951777565340000'
    ],
    [
        u'958', u'0', u'', u'', u'0', u'0', u'1953125', u'10000000', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'unifiedpolicy', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'6743176285319', u'130951777565340000'
    ],
    [
        u'0', u'0', u'', u'', u'0', u'0', u'1953125', u'10000000', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'outlookservice', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'6743176285319', u'130951777565340000'
    ],
    [
        u'0', u'0', u'', u'', u'0', u'0', u'1953125', u'10000000', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'mailboxloadbalance', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'6743176285319', u'130951777565340000'
    ],
    [
        u'0', u'0', u'', u'', u'0', u'0', u'1953125', u'10000000', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'anchorservice', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'6743176285319', u'130951777565340000'
    ],
    [
        u'0', u'0', u'', u'', u'0', u'0', u'1953125', u'10000000', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'contentindexingmovedestination', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'6743176285319', u'130951777565340000'
    ],
    [
        u'0', u'0', u'', u'', u'0', u'0', u'1953125', u'10000000', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'ediscoverysearch', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'6743176285319', u'130951777565340000'
    ],
    [
        u'0', u'0', u'', u'', u'0', u'0', u'1953125', u'10000000', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'publicfoldersystem', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'6743176285319', u'130951777565340000'
    ],
    [
        u'11495', u'0', u'', u'', u'22627', u'0', u'1953125', u'10000000', u'540', u'6', u'1', u'0',
        u'0', u'23098', u'3', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'simplemigration',
        u'0', u'69283', u'126447', u'0', u'43957144', u'287377', u'126447', u'11495', u'0',
        u'6743176285319', u'130951777565340000'
    ],
    [
        u'0', u'0', u'', u'', u'0', u'0', u'1953125', u'10000000', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'loadgen', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'6743176285319', u'130951777565340000'
    ],
    [
        u'59353', u'0', u'', u'', u'4311', u'0', u'1953125', u'10000000', u'1740', u'18', u'0',
        u'8', u'10', u'3388915', u'12', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'storeactivemonitoring', u'0', u'176465', u'574334', u'0', u'331274072', u'1033798',
        u'574334', u'57433', u'0', u'6743176285319', u'130951777565340000'
    ],
    [
        u'0', u'0', u'', u'', u'0', u'0', u'1953125', u'10000000', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'teammailbox', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'6743176285319', u'130951777565340000'
    ],
    [
        u'0', u'0', u'', u'', u'0', u'0', u'1953125', u'10000000', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'sms', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'6743176285319', u'130951777565340000'
    ],
    [
        u'0', u'0', u'', u'', u'0', u'0', u'1953125', u'10000000', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'inference', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'6743176285319', u'130951777565340000'
    ],
    [
        u'183763', u'0', u'', u'', u'88', u'0', u'1953125', u'10000000', u'50065286', u'2423113',
        u'5244', u'434', u'135', u'3750983', u'1679627', u'0', u'24', u'0', u'80', u'0', u'0', u'0',
        u'0', u'maintenance', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
        u'6743176285319', u'130951777565340000'
    ],
    [
        u'86269', u'0', u'', u'', u'2', u'0', u'1953125', u'10000000', u'66', u'3', u'1', u'0',
        u'4', u'311', u'1', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'ha', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'6743176285319', u'130951777565340000'
    ],
    [
        u'0', u'0', u'', u'', u'0', u'0', u'1953125', u'10000000', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'transportsync', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'6743176285319', u'130951777565340000'
    ],
    [
        u'55887', u'0', u'', u'', u'108', u'0', u'1953125', u'10000000', u'580', u'6', u'0', u'0',
        u'0', u'108', u'4', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'migration', u'0',
        u'8668', u'49818', u'0', u'3645017', u'141151', u'49818', u'8303', u'0', u'6743176285319',
        u'130951777565340000'
    ],
    [
        u'0', u'0', u'', u'', u'10413', u'0', u'1953125', u'10000000', u'23651', u'210', u'0', u'4',
        u'1', u'22859226', u'140', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'momt', u'0',
        u'524761', u'1148614', u'0', u'1301595880', u'2067486', u'1148614', u'114863', u'0',
        u'6743176285319', u'130951777565340000'
    ],
    [
        u'41455', u'0', u'', u'', u'1589', u'0', u'1953125', u'10000000', u'20909367', u'639566',
        u'1293', u'380', u'92', u'3712279', u'427309', u'0', u'0', u'0', u'752', u'0', u'2', u'100',
        u'96', u'timebasedassistants', u'0', u'53399', u'29902', u'1040', u'27396903', u'72740',
        u'29902', u'1060', u'0', u'6743176285319', u'130951777565340000'
    ],
    [
        u'0', u'0', u'', u'', u'0', u'0', u'1953125', u'10000000', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'approvalapi', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'6743176285319', u'130951777565340000'
    ],
    [
        u'0', u'0', u'', u'', u'0', u'0', u'1953125', u'10000000', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'webservices', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'6743176285319', u'130951777565340000'
    ],
    [
        u'0', u'0', u'', u'', u'0', u'0', u'1953125', u'10000000', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'unifiedmessaging', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'6743176285319', u'130951777565340000'
    ],
    [
        u'11502', u'0', u'', u'', u'7091', u'0', u'1953125', u'10000000', u'125279633', u'1345068',
        u'10501', u'0', u'18', u'1925947', u'1016274', u'0', u'0', u'0', u'0', u'23004', u'0',
        u'11502', u'23004', u'monitoring', u'0', u'304479', u'897860', u'0', u'160522104',
        u'1012880', u'897860', u'165768', u'0', u'6743176285319', u'130951777565340000'
    ],
    [
        u'22857', u'0', u'', u'', u'28', u'0', u'1953125', u'10000000', u'5249', u'131', u'12',
        u'0', u'3', u'427880', u'77', u'1', u'0', u'1', u'4', u'0', u'0', u'4', u'0', u'management',
        u'0', u'623', u'280', u'0', u'208125', u'669', u'280', u'15', u'0', u'6743176285319',
        u'130951777565340000'
    ],
    [
        u'0', u'0', u'', u'', u'0', u'0', u'1953125', u'10000000', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'elc', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'6743176285319', u'130951777565340000'
    ],
    [
        u'0', u'0', u'', u'', u'0', u'0', u'1953125', u'10000000', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'availabilityservice', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'6743176285319', u'130951777565340000'
    ],
    [
        u'3419753', u'0', u'', u'', u'1898', u'0', u'1953125', u'10000000', u'293', u'7', u'0',
        u'0', u'2', u'948423', u'4', u'0', u'0', u'0', u'0', u'0', u'0', u'35747', u'0',
        u'contentindexing', u'0', u'103789', u'72246', u'0', u'202073477', u'123630', u'72246',
        u'1093', u'0', u'6743176285319', u'130951777565340000'
    ],
    [
        u'0', u'0', u'', u'', u'0', u'0', u'1953125', u'10000000', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'rpchttp', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'6743176285319', u'130951777565340000'
    ],
    [
        u'0', u'0', u'', u'', u'0', u'0', u'1953125', u'10000000', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'imap', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'6743176285319', u'130951777565340000'
    ],
    [
        u'0', u'0', u'', u'', u'0', u'0', u'1953125', u'10000000', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'owa', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'6743176285319', u'130951777565340000'
    ],
    [
        u'8903712', u'0', u'', u'', u'2421', u'0', u'1953125', u'10000000', u'146072449',
        u'4829076', u'537', u'0', u'8', u'12336816', u'3218853', u'0', u'0', u'0', u'0', u'0', u'0',
        u'202', u'0', u'eventbasedassistants', u'0', u'4017', u'2568', u'0', u'2752073', u'6242',
        u'2568', u'108', u'0', u'6743176285319', u'130951777565340000'
    ],
    [
        u'0', u'0', u'', u'', u'10096', u'0', u'1953125', u'10000000', u'71226', u'808', u'80',
        u'0', u'2', u'1604', u'544', u'0', u'0', u'0', u'0', u'0', u'0', u'19165', u'40',
        u'airsync', u'0', u'113736', u'76832', u'0', u'49952360', u'172924', u'76832', u'1', u'0',
        u'6743176285319', u'130951777565340000'
    ],
    [
        u'0', u'0', u'', u'', u'618', u'0', u'1953125', u'10000000', u'272223148', u'2854731',
        u'31380', u'0', u'37', u'4065273', u'2163330', u'2', u'0', u'2', u'2', u'57482', u'23004',
        u'34506', u'0', u'transport', u'0', u'543742', u'529138', u'0', u'424193667', u'1219430',
        u'529138', u'40243', u'0', u'6743176285319', u'130951777565340000'
    ],
    [
        u'0', u'0', u'', u'', u'0', u'0', u'1953125', u'10000000', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'user', u'0', u'926',
        u'400382', u'0', u'0', u'0', u'400382', u'400382', u'0', u'6743176285319',
        u'130951777565340000'
    ],
    [
        u'406299', u'0', u'', u'', u'98', u'0', u'1953125', u'10000000', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'administrator', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'6743176285319', u'130951777565340000'
    ],
    [
        u'0', u'0', u'', u'', u'0', u'0', u'1953125', u'10000000', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'system', u'0', u'0', u'3',
        u'0', u'0', u'0', u'3', u'345025', u'0', u'6743176285319', u'130951777565340000'
    ],
    [
        u'13203303', u'0', u'', u'', u'61388', u'0', u'1953125', u'10000000', u'614653228',
        u'12092743', u'49049', u'826', u'312', u'53440863', u'8506178', u'3', u'24', u'3', u'838',
        u'80486', u'23006', u'101226', u'23140', u'_total', u'0', u'1903888', u'3908424', u'1040',
        u'400087174', u'6138327', u'3908424', u'1145789', u'0', u'6743176285319',
        u'130951777565340000'
    ]
]

discovery = {
    '': [(u'_total', None), (u'addriver', None), (u'administrator', None), (u'airsync', None),
         (u'anchorservice', None), (u'approvalapi', None), (u'availabilityservice', None),
         (u'contentindexing', None), (u'contentindexingmovedestination', None),
         (u'ediscoverysearch', None), (u'elc', None), (u'eventbasedassistants', None), (u'ha',
                                                                                        None),
         (u'hrc', None), (u'imap', None), (u'inference', None), (u'liveidbasicauth', None),
         (u'loadgen', None), (u'mailboxloadbalance', None), (u'maintenance', None),
         (u'management', None), (u'migration', None), (u'momt', None), (u'monitoring', None),
         (u'notificationbroker', None), (u'officegraph', None), (u'outlookservice', None),
         (u'owa', None), (u'pop', None), (u'publicfolderhierarchyreplication', None),
         (u'publicfoldersystem', None), (u'rpchttp', None), (u'simplemigration', None),
         (u'sms', None), (u'snackyservice', None), (u'storeactivemonitoring', None),
         (u'system', None), (u'teammailbox', None), (u'timebasedassistants', None),
         (u'transport', None), (u'transportsync', None), (u'unifiedauditing', None),
         (u'unifiedmessaging', None), (u'unifiedpolicy', None), (u'user', None),
         (u'webservices', None)]
}

checks = {
    '': [(u'_total', {
        'store_latency': {
            'upper': (40.0, 50.0)
        },
        'clienttype_requests': {
            'upper': (60, 70)
        },
        'clienttype_latency': {
            'upper': (40.0, 50.0)
        }
    }, [(0, 'Average latency: 0.49 ms', [('average_latency', 0.48712422193702626, 40.0, 50.0, None,
                                        None)]),
        (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'addriver', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.00 ms', [('average_latency', 0.0, 40.0, 50.0, None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'administrator', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.00 ms', [('average_latency', 0.0, 40.0, 50.0, None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'airsync', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.00 ms', [('average_latency', 2.6480752376567898e-05, 40.0, 50.0,
                                             None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'anchorservice', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.00 ms', [('average_latency', 0.0, 40.0, 50.0, None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'approvalapi', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.00 ms', [('average_latency', 0.0, 40.0, 50.0, None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'availabilityservice', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.00 ms', [('average_latency', 0.0, 40.0, 50.0, None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'contentindexing', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.00 ms', [('average_latency', 2.4164853195197893e-05, 40.0, 50.0,
                                             None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'contentindexingmovedestination', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.00 ms', [('average_latency', 0.0, 40.0, 50.0, None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'ediscoverysearch', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.00 ms', [('average_latency', 0.0, 40.0, 50.0, None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'elc', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
             }, [(0, 'Average latency: 0.00 ms', [('average_latency', 0.0, 40.0, 50.0, None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'eventbasedassistants', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.00 ms', [('average_latency', 9.352801363450964e-07, 40.0, 50.0,
                                             None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'ha', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.00 ms', [('average_latency', 0.0, 40.0, 50.0, None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'hrc', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.00 ms', [('average_latency', 0.0, 40.0, 50.0, None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'imap', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.00 ms', [('average_latency', 0.0, 40.0, 50.0, None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'inference', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.00 ms', [('average_latency', 0.0, 40.0, 50.0, None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'liveidbasicauth', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.00 ms', [('average_latency', 0.0, 40.0, 50.0, None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'loadgen', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.00 ms', [('average_latency', 0.0, 40.0, 50.0, None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'mailboxloadbalance', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.00 ms', [('average_latency', 0.0, 40.0, 50.0, None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'maintenance', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.00 ms', [('average_latency', 0.0, 40.0, 50.0, None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'management', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.00 ms', [('average_latency', 1.4505348153995004e-07, 40.0, 50.0,
                                             None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'migration', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.17 ms', [('average_latency', 0.17399333574210124, 40.0, 50.0,
                                             None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'momt', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.46 ms', [('average_latency', 0.45686453412547645, 40.0, 50.0,
                                             None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'monitoring', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.34 ms', [('average_latency', 0.33911634330519236, 40.0, 50.0,
                                             None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'notificationbroker', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.00 ms', [('average_latency', 0.0, 40.0, 50.0, None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'officegraph', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.00 ms', [('average_latency', 0.0, 40.0, 50.0, None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'outlookservice', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.00 ms', [('average_latency', 0.0, 40.0, 50.0, None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'owa', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.00 ms', [('average_latency', 0.0, 40.0, 50.0, None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'pop', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.00 ms', [('average_latency', 0.0, 40.0, 50.0, None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'publicfolderhierarchyreplication', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.00 ms', [('average_latency', 0.0, 40.0, 50.0, None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'publicfoldersystem', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.00 ms', [('average_latency', 0.0, 40.0, 50.0, None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'rpchttp', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.00 ms', [('average_latency', 0.0, 40.0, 50.0, None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'simplemigration', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.55 ms', [('average_latency', 0.5479212634542535, 40.0, 50.0,
                                             None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'sms', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.00 ms', [('average_latency', 0.0, 40.0, 50.0, None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'snackyservice', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.00 ms', [('average_latency', 0.0, 40.0, 50.0, None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'storeactivemonitoring', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.31 ms', [('average_latency', 0.3072515295977602, 40.0, 50.0,
                                             None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'system', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.00 ms', [('average_latency', 0.0, 40.0, 50.0, None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'teammailbox', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.00 ms', [('average_latency', 0.0, 40.0, 50.0, None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'timebasedassistants', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.00 ms', [('average_latency', 1.243283698179493e-05, 40.0, 50.0,
                                             None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'transport', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.00 ms', [('average_latency', 0.0001265842047257069, 40.0, 50.0,
                                             None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'transportsync', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.00 ms', [('average_latency', 0.0, 40.0, 50.0, None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'unifiedauditing', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.00 ms', [('average_latency', 0.0, 40.0, 50.0, None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'unifiedmessaging', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.00 ms', [('average_latency', 0.0, 40.0, 50.0, None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'unifiedpolicy', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.00 ms', [('average_latency', 0.0, 40.0, 50.0, None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'user', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.00 ms', [('average_latency', 0.0023127912843234713, 40.0, 50.0,
                                             None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])]),
         (u'webservices', {
             'store_latency': {
                 'upper': (40.0, 50.0)
             },
             'clienttype_requests': {
                 'upper': (60, 70)
             },
             'clienttype_latency': {
                 'upper': (40.0, 50.0)
             }
         }, [(0, 'Average latency: 0.00 ms', [('average_latency', 0.0, 40.0, 50.0, None, None)]),
             (0, 'RPC Requests/sec: 0.00', [('requests_per_sec', 0.0, 60, 70, None, None)])])]
}
