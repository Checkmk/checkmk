#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

# NOTE: This file has been created by an LLM (from something that was worse).
# It mostly serves as test to ensure we don't accidentally break anything.
# If you encounter something weird in here, do not hesitate to replace this
# test by something more appropriate.

from collections.abc import Mapping
from typing import Any

import pytest

from cmk.agent_based.v2 import GetRateError
from cmk.base.legacy_checks.msexch_activesync import (
    check_msexch_activesync,
    discover_msexch_activesync,
)
from cmk.plugins.windows.agent_based.libwmi import parse_wmi_table


@pytest.fixture
def parsed() -> Mapping[str, Any]:
    """Create parsed Microsoft Exchange ActiveSync data using actual parse function."""
    string_table = [
        [
            "AvailabilityRequestsPersec",
            "AvailabilityRequestsTotal",
            "AverageHangTime",
            "AverageLDAPLatency",
            "AverageRequestTime",
            "AverageRPCLatency",
            "BadItemReportsGeneratedTotal",
            "Caption",
            "ConflictingConcurrentSyncPersec",
            "ConflictingConcurrentSyncTotal",
            "CreateCollectionCommandsPersec",
            "CreateCollectionTotal",
            "CurrentRequests",
            "DeleteCollectionCommandsPersec",
            "DeleteCollectionTotal",
            "Description",
            "DocumentLibraryFetchCommandsPersec",
            "DocumentLibraryFetchTotal",
            "DocumentLibrarySearchesPersec",
            "DocumentLibrarySearchTotal",
            "EmptyFolderContentsPersec",
            "EmptyFolderContentsTotal",
            "FailedItemConversionTotal",
            "FolderCreateCommandsPersec",
            "FolderCreateTotal",
            "FolderDeleteCommandsPersec",
            "FolderDeleteTotal",
            "FolderSyncCommandsPersec",
            "FolderSyncTotal",
            "FolderUpdateCommandsPersec",
            "FolderUpdateTotal",
            "Frequency_Object",
            "Frequency_PerfTime",
            "Frequency_Sys100NS",
            "GALSearchesPersec",
            "GALSearchTotal",
            "GetAttachmentCommandsPersec",
            "GetAttachmentTotal",
            "GetHierarchyCommandsPersec",
            "GetHierarchyTotal",
            "GetItemEstimateCommandsPersec",
            "GetItemEstimateTotal",
            "HeartbeatInterval",
            "IncomingProxyRequestsTotal",
            "IRMprotectedMessageDownloadsPersec",
            "IRMprotectedMessageDownloadsTotal",
            "ItemOperationsCommandsPersec",
            "ItemOperationsTotal",
            "MailboxAttachmentFetchCommandsPersec",
            "MailboxAttachmentFetchTotal",
            "MailboxItemFetchCommandsPersec",
            "MailboxItemFetchTotal",
            "MailboxOfflineErrorsPerminute",
            "MailboxSearchesPersec",
            "MailboxSearchTotal",
            "MeetingResponseCommandsPersec",
            "MeetingResponseTotal",
            "MoveCollectionCommandsPersec",
            "MoveCollectionTotal",
            "MoveItemsCommandsPersec",
            "MoveItemsTotal",
            "Name",
            "NumberofADPolicyQueriesonReconnect",
            "Numberofautoblockeddevices",
            "NumberofNotificationManagerObjectsinMemory",
            "OptionsCommandsPersec",
            "OptionsTotal",
            "OutgoingProxyRequestsTotal",
            "PermanentActiveDirectoryErrorsPerminute",
            "PermanentStorageErrorsPerminute",
            "PID",
            "PingCommandsDroppedPersec",
            "PingCommandsPending",
            "PingCommandsPersec",
            "PingDroppedTotal",
            "PingTotal",
            "ProvisionCommandsPersec",
            "ProvisionTotal",
            "ProxyLogonCommandsSentTotal",
            "ProxyLogonReceivedTotal",
            "RecoverySyncCommandsPersec",
            "RecoverySyncTotal",
            "RequestsPersec",
            "RequestsTotal",
            "SearchCommandsPersec",
            "SearchTotal",
            "SendIRMprotectedMessagesPersec",
            "SendIRMprotectedMessagesTotal",
            "SendMailCommandsPersec",
            "SendMailTotal",
            "SettingsCommandsPersec",
            "SettingsTotal",
            "SmartForwardCommandsPersec",
            "SmartForwardTotal",
            "SmartReplyCommandsPersec",
            "SmartReplyTotal",
            "SyncCommandsDroppedPersec",
            "SyncCommandsPending",
            "SyncCommandsPersec",
            "SyncDroppedTotal",
            "SyncStateKBytesLeftCompressed",
            "SyncStateKBytesTotal",
            "SyncTotal",
            "Timestamp_Object",
            "Timestamp_PerfTime",
            "Timestamp_Sys100NS",
            "TransientActiveDirectoryErrorsPerminute",
            "TransientErrorsPerminute",
            "TransientMailboxConnectionFailuresPerminute",
            "TransientStorageErrorsPerminute",
            "WrongCASProxyRequestsTotal",
        ],
        [
            "0",  # AvailabilityRequestsPersec
            "0",  # AvailabilityRequestsTotal
            "0",  # AverageHangTime
            "0",  # AverageLDAPLatency
            "53",  # AverageRequestTime
            "0",  # AverageRPCLatency
            "0",  # BadItemReportsGeneratedTotal
            "",  # Caption
            "0",  # ConflictingConcurrentSyncPersec
            "0",  # ConflictingConcurrentSyncTotal
            "0",  # CreateCollectionCommandsPersec
            "0",  # CreateCollectionTotal
            "0",  # CurrentRequests
            "0",  # DeleteCollectionCommandsPersec
            "0",  # DeleteCollectionTotal
            "",  # Description
            "0",  # DocumentLibraryFetchCommandsPersec
            "0",  # DocumentLibraryFetchTotal
            "0",  # DocumentLibrarySearchesPersec
            "0",  # DocumentLibrarySearchTotal
            "0",  # EmptyFolderContentsPersec
            "0",  # EmptyFolderContentsTotal
            "0",  # FailedItemConversionTotal
            "0",  # FolderCreateCommandsPersec
            "0",  # FolderCreateTotal
            "0",  # FolderDeleteCommandsPersec
            "0",  # FolderDeleteTotal
            "0",  # FolderSyncCommandsPersec
            "0",  # FolderSyncTotal
            "0",  # FolderUpdateCommandsPersec
            "0",  # FolderUpdateTotal
            "0",  # Frequency_Object
            "13604",  # Frequency_PerfTime
            "0",  # Frequency_Sys100NS
            "0",  # GALSearchesPersec
            "0",  # GALSearchTotal
            "0",  # GetAttachmentCommandsPersec
            "0",  # GetAttachmentTotal
            "0",  # GetHierarchyCommandsPersec
            "0",  # GetHierarchyTotal
            "0",  # GetItemEstimateCommandsPersec
            "0",  # GetItemEstimateTotal
            "0",  # HeartbeatInterval
            "0",  # IncomingProxyRequestsTotal
            "0",  # IRMprotectedMessageDownloadsPersec
            "0",  # IRMprotectedMessageDownloadsTotal
            "0",  # ItemOperationsCommandsPersec
            "0",  # ItemOperationsTotal
            "0",  # MailboxAttachmentFetchCommandsPersec
            "0",  # MailboxAttachmentFetchTotal
            "0",  # MailboxItemFetchCommandsPersec
            "0",  # MailboxItemFetchTotal
            "0",  # MailboxOfflineErrorsPerminute
            "0",  # MailboxSearchesPersec
            "0",  # MailboxSearchTotal
            "0",  # MeetingResponseCommandsPersec
            "0",  # MeetingResponseTotal
            "0",  # MoveCollectionCommandsPersec
            "0",  # MoveCollectionTotal
            "0",  # MoveItemsCommandsPersec
            "0",  # MoveItemsTotal
            "",  # Name - Empty name for _Total instance
            "0",  # NumberofADPolicyQueriesonReconnect
            "0",  # Numberofautoblockeddevices
            "0",  # NumberofNotificationManagerObjectsinMemory
            "0",  # OptionsCommandsPersec
            "0",  # OptionsTotal
            "0",  # OutgoingProxyRequestsTotal
            "0",  # PermanentActiveDirectoryErrorsPerminute
            "0",  # PermanentStorageErrorsPerminute
            "0",  # PID
            "0",  # PingCommandsDroppedPersec
            "0",  # PingCommandsPending
            "0",  # PingCommandsPersec
            "0",  # PingDroppedTotal
            "0",  # PingTotal
            "0",  # ProvisionCommandsPersec
            "0",  # ProvisionTotal
            "0",  # ProxyLogonCommandsSentTotal
            "0",  # ProxyLogonReceivedTotal
            "0",  # RecoverySyncCommandsPersec
            "0",  # RecoverySyncTotal
            "15426",  # RequestsPersec - This is the key metric
            "15426",  # RequestsTotal
            "0",  # SearchCommandsPersec
            "0",  # SearchTotal
            "0",  # SendIRMprotectedMessagesPersec
            "0",  # SendIRMprotectedMessagesTotal
            "0",  # SendMailCommandsPersec
            "0",  # SendMailTotal
            "0",  # SettingsCommandsPersec
            "0",  # SettingsTotal
            "0",  # SmartForwardCommandsPersec
            "0",  # SmartForwardTotal
            "0",  # SmartReplyCommandsPersec
            "0",  # SmartReplyTotal
            "0",  # SyncCommandsDroppedPersec
            "0",  # SyncCommandsPending
            "0",  # SyncCommandsPersec
            "0",  # SyncDroppedTotal
            "0",  # SyncStateKBytesLeftCompressed
            "0",  # SyncStateKBytesTotal
            "15426",  # SyncTotal
            "15426",  # SyncTotal (duplicate)
            "0",  # Timestamp_Object
            "0",  # Timestamp_PerfTime
            "0",  # Timestamp_Sys100NS
            "6743176182062",  # Timestamp_Object
            "130951777564870000",  # Timestamp_PerfTime
            "0",  # TransientActiveDirectoryErrorsPerminute
            "0",  # TransientErrorsPerminute
            "0",  # TransientMailboxConnectionFailuresPerminute
            "0",  # TransientStorageErrorsPerminute
            "0",  # WrongCASProxyRequestsTotal
        ],
    ]

    return parse_wmi_table(string_table)


def test_msexch_activesync_discovery(parsed: Mapping[str, Any]) -> None:
    """Test Microsoft Exchange ActiveSync discovery function."""
    result = list(discover_msexch_activesync(parsed))

    # Should discover exactly one service (empty string as item name)
    assert len(result) == 1
    assert result[0] == (None, {})


@pytest.mark.usefixtures("initialised_item_state")
def test_msexch_activesync_check(parsed: Mapping[str, Any]) -> None:
    """Test Microsoft Exchange ActiveSync check function."""
    # Based on the original dataset, this should produce a rate of 0.00 requests/sec
    # The rate calculation gets GetRateError on first run due to initialization
    # Should get GetRateError on first check (normal behavior)
    with pytest.raises(GetRateError):
        list(check_msexch_activesync(None, {}, parsed))


def test_msexch_activesync_parse_function() -> None:
    """Test Microsoft Exchange ActiveSync parse function with minimal dataset."""
    string_table = [
        [
            "RequestsPersec",
            "RequestsTotal",
            "Frequency_PerfTime",
            "Name",
        ],
        [
            "15426",
            "15426",
            "13604",
            "",
        ],
    ]

    result = parse_wmi_table(string_table)

    # Should parse exactly one WMI instance
    assert "" in result
    wmi_data = result[""]

    # Check that it's a WMI table object (not the internal structure)
    assert hasattr(wmi_data, "__class__")
    assert "WMITable" in wmi_data.__class__.__name__


def test_msexch_activesync_discovery_empty_section() -> None:
    """Test Microsoft Exchange ActiveSync discovery function with empty section."""
    result = list(discover_msexch_activesync({}))

    # Should not discover any service for empty section
    assert len(result) == 0


def test_msexch_activesync_check_no_data() -> None:
    """Test Microsoft Exchange ActiveSync check function with no data."""
    # Check function expects key "" to exist, so it will raise KeyError on missing data
    import pytest

    with pytest.raises(KeyError):
        list(check_msexch_activesync(None, {}, {}))
