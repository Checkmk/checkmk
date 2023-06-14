#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated
checkname = "storeonce4x_alerts"
info = [
    [
        '{"count": 100, "total": 232, "unFilteredTotal": 0, "start": 0, "prevPageUri": "/rest/alerts?start=0&count=100&category=alerts", "nextPageUri": "/rest/alerts?start=100&count=100&category=alerts", "category": "resources", "members": [{"name": "level.notset", "category": "alerts", "uri": "/rest/alerts/95e070c8-c6be-42bd-b76a-d8463d936889", "created": "2019-04-30T22:47:51.123+0000", "modified": "2019-05-23T13:56:39.099+0000", "description": "Remote Support level is not configured.", "status": "Critical", "state": "Cleared", "type": "IndexResource", "dataSenderId": "localhost", "attributes": {"description": "Remote Support level is not configured."}, "attributesList": ["Remote Support level is not configured."], "associatedResource": {"associationType": "DOWN", "resourceCategory": "SERVICE", "resourceName": "Remote Support Service", "resourceLocation": "so39170v01"}, "uuid": "95e070c8-c6be-42bd-b76a-d8463d936889", "level": "ALERT", "severity": "Critical", "urgency": "High", "descriptionInfo": {"catalogName": "rsvsservice-event", "messageKey": "level.notset", "arguments": ["Remote Support"], "messageForCurrentLocale": "Remote Support level is not configured."}, "correctiveAction": "Configure the appropriate level information.", "correctiveActionInfo": {"catalogName": "rsvsservice-event", "messageKey": "level.notset.resolution", "messageForCurrentLocale": "Configure the appropriate level information."}, "eventCode": "E030F000002", "serviceEventSource": false, "alertState": "Cleared", "alertTypeID": "rsvs.level", "changeLog": [], "clearedByUser": "System", "clearedTime": "2019-05-23T13:56:39.099+0000", "lifeCycle": false, "resourceID": "rsvs.level", "eTag": "Thu May 16 09:09:56 UTC 2019"}]}'
    ]
]

discovery = {"": [(None, {})]}

checks = {
    "": [
        (
            None,
            {},
            [
                (0, "No uncleared alerts found", []),
            ],
        )
    ]
}
