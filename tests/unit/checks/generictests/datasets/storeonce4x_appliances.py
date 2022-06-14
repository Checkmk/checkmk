#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'storeonce4x_appliances'

info = [
    [
        '{"members": [{"uuid": "bcc0842d7420290ccc3d061ec23ce", "address": "127.0.0.1", "hostname": "myhostname", "productName": "HPE StoreOnce 5250", "serialNumber": "123456789", "localhost": true, "applianceState": 0, "stateUpdatedDate": "2020-05-11T10:45:51.807Z", "federationApiVersion": 1, "applianceStateString": "Reachable", "sinceStateUpdatedSeconds": 1493050}]}'
    ],
    [
        '{"uuid": "bcc0842d7420290ccc3d061ec23ce", "hostname": "myhostname", "platformType": "HPE StoreOnce 5250", "softwareVersion": "4.1.3-1921.10", "softwareUpdateRecommended": false, "recommendedSoftwareVersion": "", "localDiskBytes": 100792069099520, "localUserBytes": 1014343032520056, "localFreeBytes": 258734285025280, "localCapacityBytes": 359526354124800, "cloudDiskBytes": 0, "cloudUserBytes": 0, "cloudFreeBytes": 0, "cloudCapacityBytes": 0, "catalystDataJobSessions": 10, "nasNumDedupeSessions": 0, "vtlNumActiveSessions": 0, "catalystInboundCopyJobSessions": 0, "catalystOutboundCopyJobSessions": 0, "repNumSourceJobs": 0, "repNumTargetJobs": 0, "maxStreamsLimit": 512, "metricsCpuTotal": 8.49826, "metricsMemoryTotalPhysical": 506482655232, "metricsMemoryUsedPercent": 6.7811, "metricsDataDiskUtilisationPercent": 97.3215, "applianceStatus": "WARNING", "applianceStatusString": "Warning", "dataServicesStatus": "OK", "dataServicesStatusString": "OK", "licenseStatus": "OK", "licenseStatusString": "OK", "userStorageStatus": "OK", "userStorageStatusString": "OK", "hardwareStatus": "WARNING", "hardwareStatusString": "Warning", "remoteSupportStatus": "OK", "remoteSupportStatusString": "OK", "catStoresSummary": {"statusSummary": {"numOk": 4, "numWarning": 0, "numCritical": 0, "numUnknown": 0, "total": 4}}, "cloudBankStoresSummary": {"statusSummary": {"numOk": 0, "numWarning": 0, "numCritical": 0, "numUnknown": 0, "total": 0}}, "nasSharesSummary": {"statusSummary": {"numOk": 0, "numWarning": 0, "numCritical": 0, "numUnknown": 0, "total": 0}}, "vtlLibrariesSummary": {"statusSummary": {"numOk": 0, "numWarning": 0, "numCritical": 0, "numUnknown": 0, "total": 0}}, "nasRepMappingSummary": {"statusSummary": {"numOk": 0, "numWarning": 0, "numCritical": 0, "numUnknown": 0, "total": 0}}, "vtlRepMappingSummary": {"statusSummary": {"numOk": 0, "numWarning": 0, "numCritical": 0, "numUnknown": 0, "total": 0}}, "systemLocation": "ZH1", "contactName": "Roger Huegi", "contactNumber": "+41 34 426 13 13", "contactEmail": "tm-system@wagner.ch", "diskBytes": 100792069099520, "userBytes": 1014343032520056, "totalActiveSessions": 10, "capacitySavedBytes": 913550963420536, "capacitySavedPercent": 90.06332, "dedupeRatio": 10.06372}'
    ]
]

discovery = {
    '': [('myhostname', {})],
    'storage': [('myhostname', {})],
    'license': [('myhostname', {})],
    'summaries': [('myhostname', {})]
}

checks = {
    '': [
        (
            'myhostname', {}, [
                (
                    0,
                    'State: Reachable, Serial Number: 123456789, Software version: 4.1.3-1921.10, Product Name: HPE StoreOnce 5250',
                    []
                )
            ]
        )
    ],
    'storage': [
        (
            'myhostname', {}, [
                (
                    0, '28.03% used (91.7 of 327 TiB)', [
                        (
                            'fs_used', 96122807.59765625, 274296840.0,
                            308583945.0, 0, 342871050.0
                        ), ('fs_size', 342871050.0, None, None, None, None),
                        (
                            'fs_used_percent', 28.034681725872233, None, None,
                            None, None
                        )
                    ]
                ), (0, 'Total local: 327 TiB', []),
                (0, 'Free local: 235 TiB', []),
                (
                    0, 'Dedup ratio: 10.06', [
                        ('dedup_rate', 10.06372, None, None, None, None)
                    ]
                )
            ]
        )
    ],
    'license': [('myhostname', {}, [(0, 'Status: OK', [])])],
    'summaries': [('myhostname', {}, [(0, 'Cat stores Ok (4 of 4)', [])])]
}
