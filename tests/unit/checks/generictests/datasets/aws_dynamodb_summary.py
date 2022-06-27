#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore


checkname = 'aws_dynamodb_summary'

info = [['[{"AttributeDefinitions":', '[{"AttributeName":', '"key",', '"AttributeType":', '"S"},',
         '{"AttributeName":', '"key-2",', '"AttributeType":', '"S"}],', '"TableName":',
         '"joerg-herbel-global-table",', '"KeySchema":', '[{"AttributeName":', '"key",',
         '"KeyType":', '"HASH"}],', '"TableStatus":', '"ACTIVE",', '"CreationDateTime":',
         '"2020-04-16', '10:58:13.516000+02:00",', '"ProvisionedThroughput":',
         '{"LastIncreaseDateTime":', '"2020-04-16', '11:03:21.421000+02:00",',
         '"LastDecreaseDateTime":', '"2020-04-16', '11:13:09.059000+02:00",',
         '"NumberOfDecreasesToday":', '0,', '"ReadCapacityUnits":', '1,', '"WriteCapacityUnits":',
         '1},', '"TableSizeBytes":', '123,', '"ItemCount":', '2,', '"TableId":',
         '"7e1de3fa-be2f-4f40-b8bc-931eb28dad59",', '"GlobalSecondaryIndexes":', '[{"IndexName":',
         '"key-2-index",', '"KeySchema":', '[{"AttributeName":', '"key-2",', '"KeyType":',
         '"HASH"}],', '"Projection":', '{"ProjectionType":', '"ALL"},', '"IndexStatus":',
         '"ACTIVE",', '"ProvisionedThroughput":', '{"NumberOfDecreasesToday":', '0,',
         '"ReadCapacityUnits":', '1,', '"WriteCapacityUnits":', '1},', '"IndexSizeBytes":', '18,',
         '"ItemCount":', '1}],', '"StreamSpecification":', '{"StreamEnabled":', 'true,',
         '"StreamViewType":', '"NEW_AND_OLD_IMAGES"},', '"LatestStreamLabel":',
         '"2020-04-16T08:58:40.417",', '"GlobalTableVersion":', '"2019.11.21",', '"Replicas":',
         '[{"RegionName":', '"us-east-1",', '"ReplicaStatus":', '"ACTIVE",',
         '"ProvisionedThroughputOverride":', '{"ReadCapacityUnits":', '2},',
         '"GlobalSecondaryIndexes":', '[{"IndexName":', '"key-2-index",',
         '"ProvisionedThroughputOverride":', '{"ReadCapacityUnits":', '2}}]}],', '"Region":',
         '"eu-central-1"},', '{"AttributeDefinitions":', '[{"AttributeName":', '"key-1",',
         '"AttributeType":', '"S"},', '{"AttributeName":', '"key-2",', '"AttributeType":', '"S"}],',
         '"TableName":', '"joerg-herbel-on-demand",', '"KeySchema":', '[{"AttributeName":',
         '"key-1",', '"KeyType":', '"HASH"}],', '"TableStatus":', '"ACTIVE",',
         '"CreationDateTime":', '"2020-04-17', '08:48:36.779000+02:00",',
         '"ProvisionedThroughput":', '{"NumberOfDecreasesToday":', '0,', '"ReadCapacityUnits":',
         '0,', '"WriteCapacityUnits":', '0},', '"TableSizeBytes":', '10,', '"ItemCount":', '1,',
         '"TableId":', '"69f76fb0-2483-4346-b5b9-72eb7a9be83a",', '"BillingModeSummary":',
         '{"BillingMode":', '"PAY_PER_REQUEST",', '"LastUpdateToPayPerRequestDateTime":',
         '"2020-04-17', '08:48:36.779000+02:00"},', '"GlobalSecondaryIndexes":', '[{"IndexName":',
         '"key-2-index",', '"KeySchema":', '[{"AttributeName":', '"key-2",', '"KeyType":',
         '"HASH"}],', '"Projection":', '{"ProjectionType":', '"ALL"},', '"IndexStatus":',
         '"ACTIVE",', '"ProvisionedThroughput":', '{"NumberOfDecreasesToday":', '0,',
         '"ReadCapacityUnits":', '0,', '"WriteCapacityUnits":', '0},', '"IndexSizeBytes":', '0,',
         '"ItemCount":', '0}],', '"Region":', '"eu-central-1"},', '{"AttributeDefinitions":',
         '[{"AttributeName":', '"primary-key",', '"AttributeType":', '"S"},', '{"AttributeName":',
         '"primary-sorter",', '"AttributeType":', '"N"},', '{"AttributeName":',
         '"secondary-sorter",', '"AttributeType":', '"S"}],', '"TableName":',
         '"joerg-herbel-table",', '"KeySchema":', '[{"AttributeName":', '"primary-key",',
         '"KeyType":', '"HASH"},', '{"AttributeName":', '"primary-sorter",', '"KeyType":',
         '"RANGE"}],', '"TableStatus":', '"ACTIVE",', '"CreationDateTime":', '"2020-04-16',
         '16:42:59.334000+02:00",', '"ProvisionedThroughput":', '{"NumberOfDecreasesToday":', '0,',
         '"ReadCapacityUnits":', '1,', '"WriteCapacityUnits":', '1},', '"TableSizeBytes":', '481,',
         '"ItemCount":', '6,', '"TableId":', '"597f3bae-e5c0-4589-9551-69be19c9e5a9",',
         '"LocalSecondaryIndexes":', '[{"IndexName":', '"primary-key-secondary-sorter-index",',
         '"KeySchema":', '[{"AttributeName":', '"primary-key",', '"KeyType":', '"HASH"},',
         '{"AttributeName":', '"secondary-sorter",', '"KeyType":', '"RANGE"}],', '"Projection":',
         '{"ProjectionType":', '"ALL"},', '"IndexSizeBytes":', '481,', '"ItemCount":', '6}],',
         '"StreamSpecification":', '{"StreamEnabled":', 'true,', '"StreamViewType":',
         '"NEW_AND_OLD_IMAGES"},', '"LatestStreamLabel":', '"2020-04-17T06:32:34.559",',
         '"Region":', '"eu-central-1"}]'],
        ['[{"AttributeDefinitions":', '[{"AttributeName":', '"key",', '"AttributeType":', '"S"},',
         '{"AttributeName":', '"key-2",', '"AttributeType":', '"S"}],', '"TableName":',
         '"joerg-herbel-global-table",', '"KeySchema":', '[{"AttributeName":', '"key",',
         '"KeyType":', '"HASH"}],', '"TableStatus":', '"ACTIVE",', '"CreationDateTime":',
         '"2020-04-16', '11:04:05.267000+02:00",', '"ProvisionedThroughput":',
         '{"LastIncreaseDateTime":', '"2020-04-16', '16:47:45.834000+02:00",',
         '"LastDecreaseDateTime":', '"2020-04-16', '16:48:15.185000+02:00",',
         '"NumberOfDecreasesToday":', '0,', '"ReadCapacityUnits":', '2,', '"WriteCapacityUnits":',
         '1},', '"TableSizeBytes":', '123,', '"ItemCount":', '2,', '"TableId":',
         '"a952205f-65fa-4398-bafa-0610c41c6ebf",', '"GlobalSecondaryIndexes":', '[{"IndexName":',
         '"key-2-index",', '"KeySchema":', '[{"AttributeName":', '"key-2",', '"KeyType":',
         '"HASH"}],', '"Projection":', '{"ProjectionType":', '"ALL"},', '"IndexStatus":',
         '"ACTIVE",', '"ProvisionedThroughput":', '{"LastIncreaseDateTime":', '"2020-04-16',
         '16:47:49.020000+02:00",', '"LastDecreaseDateTime":', '"2020-04-16',
         '16:48:18.070000+02:00",', '"NumberOfDecreasesToday":', '0,', '"ReadCapacityUnits":', '2,',
         '"WriteCapacityUnits":', '1},', '"IndexSizeBytes":', '18,', '"ItemCount":', '1}],',
         '"StreamSpecification":', '{"StreamEnabled":', 'true,', '"StreamViewType":',
         '"NEW_AND_OLD_IMAGES"},', '"LatestStreamLabel":', '"2020-04-16T09:07:08.854",',
         '"GlobalTableVersion":', '"2019.11.21",', '"Replicas":', '[{"RegionName":',
         '"eu-central-1",', '"ReplicaStatus":', '"ACTIVE",', '"ProvisionedThroughputOverride":',
         '{"ReadCapacityUnits":', '1},', '"GlobalSecondaryIndexes":', '[{"IndexName":',
         '"key-2-index",', '"ProvisionedThroughputOverride":', '{"ReadCapacityUnits":', '1}}]}],',
         '"Region":', '"us-east-1"}]']]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, {},
            [
                (0, 'Total number of tables: 4'),
                (0, 'EU (Frankfurt): 3'),
                (0, 'US East (N. Virginia): 1'),
                (0, '\nEU (Frankfurt):\njoerg-herbel-global-table -- Items: 2, Size: 123 B, '
                    'Status: ACTIVE\njoerg-herbel-on-demand -- Items: 1, Size: 10 B, Status: '
                    'ACTIVE\njoerg-herbel-table -- Items: 6, Size: 481 B, Status: ACTIVE\nUS '
                    'East (N. Virginia):\njoerg-herbel-global-table -- Items: 2, Size: 123 B, '
                    'Status: ACTIVE')
            ]
        )
    ]
}
