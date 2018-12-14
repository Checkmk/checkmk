checkname = 'msexch_activesync'

info = [[
    u'AvailabilityRequestsPersec', u'AvailabilityRequestsTotal', u'AverageHangTime',
    u'AverageLDAPLatency', u'AverageRequestTime', u'AverageRPCLatency',
    u'BadItemReportsGeneratedTotal', u'Caption', u'ConflictingConcurrentSyncPersec',
    u'ConflictingConcurrentSyncTotal', u'CreateCollectionCommandsPersec', u'CreateCollectionTotal',
    u'CurrentRequests', u'DeleteCollectionCommandsPersec', u'DeleteCollectionTotal', u'Description',
    u'DocumentLibraryFetchCommandsPersec', u'DocumentLibraryFetchTotal',
    u'DocumentLibrarySearchesPersec', u'DocumentLibrarySearchTotal', u'EmptyFolderContentsPersec',
    u'EmptyFolderContentsTotal', u'FailedItemConversionTotal', u'FolderCreateCommandsPersec',
    u'FolderCreateTotal', u'FolderDeleteCommandsPersec', u'FolderDeleteTotal',
    u'FolderSyncCommandsPersec', u'FolderSyncTotal', u'FolderUpdateCommandsPersec',
    u'FolderUpdateTotal', u'Frequency_Object', u'Frequency_PerfTime', u'Frequency_Sys100NS',
    u'GALSearchesPersec', u'GALSearchTotal', u'GetAttachmentCommandsPersec', u'GetAttachmentTotal',
    u'GetHierarchyCommandsPersec', u'GetHierarchyTotal', u'GetItemEstimateCommandsPersec',
    u'GetItemEstimateTotal', u'HeartbeatInterval', u'IncomingProxyRequestsTotal',
    u'IRMprotectedMessageDownloadsPersec', u'IRMprotectedMessageDownloadsTotal',
    u'ItemOperationsCommandsPersec', u'ItemOperationsTotal',
    u'MailboxAttachmentFetchCommandsPersec', u'MailboxAttachmentFetchTotal',
    u'MailboxItemFetchCommandsPersec', u'MailboxItemFetchTotal', u'MailboxOfflineErrorsPerminute',
    u'MailboxSearchesPersec', u'MailboxSearchTotal', u'MeetingResponseCommandsPersec',
    u'MeetingResponseTotal', u'MoveCollectionCommandsPersec', u'MoveCollectionTotal',
    u'MoveItemsCommandsPersec', u'MoveItemsTotal', u'Name', u'NumberofADPolicyQueriesonReconnect',
    u'Numberofautoblockeddevices', u'NumberofNotificationManagerObjectsinMemory',
    u'OptionsCommandsPersec', u'OptionsTotal', u'OutgoingProxyRequestsTotal',
    u'PermanentActiveDirectoryErrorsPerminute', u'PermanentStorageErrorsPerminute', u'PID',
    u'PingCommandsDroppedPersec', u'PingCommandsPending', u'PingCommandsPersec',
    u'PingDroppedTotal', u'PingTotal', u'ProvisionCommandsPersec', u'ProvisionTotal',
    u'ProxyLogonCommandsSentTotal', u'ProxyLogonReceivedTotal', u'RecoverySyncCommandsPersec',
    u'RecoverySyncTotal', u'RequestsPersec', u'RequestsTotal', u'SearchCommandsPersec',
    u'SearchTotal', u'SendIRMprotectedMessagesPersec', u'SendIRMprotectedMessagesTotal',
    u'SendMailCommandsPersec', u'SendMailTotal', u'SettingsCommandsPersec', u'SettingsTotal',
    u'SmartForwardCommandsPersec', u'SmartForwardTotal', u'SmartReplyCommandsPersec',
    u'SmartReplyTotal', u'SyncCommandsDroppedPersec', u'SyncCommandsPending', u'SyncCommandsPersec',
    u'SyncDroppedTotal', u'SyncStateKBytesLeftCompressed', u'SyncStateKBytesTotal', u'SyncTotal',
    u'Timestamp_Object', u'Timestamp_PerfTime', u'Timestamp_Sys100NS',
    u'TransientActiveDirectoryErrorsPerminute', u'TransientErrorsPerminute',
    u'TransientMailboxConnectionFailuresPerminute', u'TransientStorageErrorsPerminute',
    u'WrongCASProxyRequestsTotal'
],
        [
            u'0', u'0', u'0', u'0', u'53', u'0', u'0', u'', u'0', u'0', u'0', u'0', u'0', u'0',
            u'0', u'', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
            u'0', u'0', u'0', u'1953125', u'10000000', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
            u'0', u'0', u'15426', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
            u'0', u'0', u'0', u'0', u'0', u'0', u'', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
            u'13604', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'15426',
            u'15426', u'0', u'0', u'0', u'0', u'0', u'0', u'15426', u'15426', u'0', u'0', u'0',
            u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'6743176182062',
            u'130951777564870000', u'0', u'0', u'0', u'0', u'0'
        ]]

discovery = {'': [(None, None)]}

checks = {
    '': [(
        None,
        {},
        [(0, '0.00 requests/sec', [('requests_per_sec', 0.0, None, None, None, None)])],
    )]
}
