#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Metric, Result, State, StringTable
from cmk.plugins.redfish.agent_based.redfish_drives import check_redfish_drives
from cmk.plugins.redfish.lib import parse_redfish_multiple


@pytest.mark.parametrize(
    ["item", "string_table", "expected"],
    [
        pytest.param(
            "0-1.2TB 12G SAS HDD",
            [
                [
                    '{"@Redfish.WriteableProperties": ["LocationIndicatorActive", "HotspareType"], "@odata.etag": "3928DC48", "@odata.id": "/redfish/v1/Systems/1/Storage/DE07A000/Drives/0", "@odata.type": "#Drive.v1_18_0.Drive", "BlockSizeBytes": 512, "CapableSpeedGbs": 12.0, "CapacityBytes": 1200243695616, "DriveFormFactor": "Drive2_5", "EncryptionAbility": "None", "FailurePredicted": false, "FirmwareVersion": "HPD5", "HotspareType": "None", "HotspareType@Redfish.AllowableValues": ["None"], "Id": "0", "Identifiers": [{"DurableName": "5000039B28119BF1", "DurableNameFormat": "NAA"}], "Links": {"Storage": {"@odata.id": "/redfish/v1/Systems/1/Storage/DE07A000"}, "Volumes": [{"@odata.id": "/redfish/v1/Systems/1/Storage/DE07A000/Volumes/1"}], "Volumes@odata.count": 1}, "LocationIndicatorActive": false, "Manufacturer": "HPE", "MediaType": "HDD", "Metrics": {"@odata.id": "/redfish/v1/Systems/1/Storage/DE07A000/Drives/0/Metrics"}, "Model": "EG001200JWJNK", "Multipath": false, "Name": "1.2TB 12G SAS HDD", "NegotiatedSpeedGbs": 12.0, "Operations": [], "PhysicalLocation": {"PartLocation": {"LocationOrdinalValue": 4, "LocationType": "Bay", "ServiceLabel": "Slot=0:Port=1I:Box=3:Bay=4"}}, "Protocol": "SAS", "Revision": "HPD5", "RotationSpeedRPM": 10000.0, "SerialNumber": "9170A0QXFF4F", "SlotCapableProtocols": ["SAS", "SATA"], "Status": {"Conditions": [], "Health": "OK", "State": "Enabled"}, "StatusIndicator": "OK", "WriteCacheEnabled": false}',
                ]
            ],
            [
                Result(state=State.OK, summary="Size: 1118GB, Speed 12.0 Gbs"),
                Result(state=State.OK, notice="Component State: Normal, This resource is enabled."),
            ],
            id="Enabled",
        ),
        pytest.param(
            "1-12G SAS HDD",
            [
                [
                    '{"@Redfish.WriteableProperties": ["LocationIndicatorActive", "HotspareType"], "@odata.etag": "F7DA9496", "@odata.id": "/redfish/v1/Systems/1/Storage/DE07A000/Drives/1", "@odata.type": "#Drive.v1_18_0.Drive", "BlockSizeBytes": null, "CapableSpeedGbs": 12.0, "CapacityBytes": null, "DriveFormFactor": "Drive2_5", "EncryptionAbility": "None", "FailurePredicted": null, "FirmwareVersion": "HPD5", "HotspareType": null, "HotspareType@Redfish.AllowableValues": ["None"], "Id": "1", "Identifiers": null, "Links": {"Storage": {"@odata.id": "/redfish/v1/Systems/1/Storage/DE07A000"}, "Volumes": [{"@odata.id": "/redfish/v1/Systems/1/Storage/DE07A000/Volumes/1"}], "Volumes@odata.count": 1}, "LocationIndicatorActive": false, "Manufacturer": "HPE", "MediaType": "HDD", "Metrics": {"@odata.id": "/redfish/v1/Systems/1/Storage/DE07A000/Drives/1/Metrics"}, "Model": "EG001200JWJNK", "Multipath": null, "Name": "12G SAS HDD", "NegotiatedSpeedGbs": 12.0, "Operations": [], "PhysicalLocation": {"PartLocation": {"LocationOrdinalValue": 3, "LocationType": "Bay", "ServiceLabel": "Slot=0:Port=1I:Box=3:Bay=3"}}, "Protocol": "SAS", "Revision": "HPD5", "RotationSpeedRPM": 10000.0, "SerialNumber": "9170A0MJFF4F", "SlotCapableProtocols": ["SAS", "SATA"], "Status": {"Conditions": [{"MessageArgs": ["Slot=0:Port=1I:Box=3:Bay=3"], "MessageId": "StorageDevice.1.1.DriveFailure", "Severity": "Critical"}], "Health": "Critical", "State": "UnavailableOffline"}, "StatusIndicator": "Fail", "WriteCacheEnabled": null}',
                ]
            ],
            [
                Result(state=State.OK, summary="Size: 0GB, Speed 12.0 Gbs"),
                Result(
                    state=State.CRIT,
                    notice="Component State: A critical condition requires immediate attention., This function or resource is present but cannot be used",
                ),
            ],
            id="UnavailableOffline",
        ),
    ],
)
def test_check_redfish_drives(
    item: str, string_table: StringTable, expected: list[Result | Metric]
) -> None:
    parsed = parse_redfish_multiple(string_table)
    assert expected == list(check_redfish_drives(item, parsed))
