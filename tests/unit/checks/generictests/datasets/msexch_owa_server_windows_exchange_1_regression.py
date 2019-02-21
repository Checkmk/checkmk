# yapf: disable
checkname = 'msexch_owa'

info = [[
    u'ActiveConversions', u'ActiveMailboxSubscriptions', u'AggregatedConfigurationReads',
    u'AggregatedConfigurationRebuilds', u'AggregatedConfigurationRequests', u'ASQueries',
    u'ASQueriesFailurePercent', u'AttachmentsUploadedSinceOWAStart', u'AverageCheckSpellingTime',
    u'AverageConversionQueuingTime', u'AverageConversionTime', u'AverageResponseTime',
    u'AverageSearchTime', u'CalendarViewRefreshed', u'CalendarViewsLoaded', u'Caption',
    u'CASCrossSiteRedirectionEarliertoLaterVersion',
    u'CASCrossSiteRedirectionLatertoEarlierVersion',
    u'CASIntraSiteRedirectionEarliertoLaterVersion',
    u'CASIntraSiteRedirectionLatertoEarlierVersion', u'ConnectionFailedTransientExceptionPercent',
    u'ConversionRequestsKBPersec', u'ConversionResponsesKBPersec', u'Conversions',
    u'ConversionsEndedbyTimeout', u'ConversionsEndedwithErrors', u'CurrentProxyUsers',
    u'CurrentUniqueUsers', u'CurrentUniqueUsersLight', u'CurrentUniqueUsersPremium',
    u'CurrentUsers', u'CurrentUsersLight', u'CurrentUsersPremium', u'Description',
    u'FailedRequestsPersec', u'FailurerateofrequestsfromOWAtoEWS', u'Frequency_Object',
    u'Frequency_PerfTime', u'Frequency_Sys100NS', u'IMAverageSignInTime',
    u'IMMessageDeliveryFailuresPersec', u'IMMessagesReceivedPersec', u'IMMessagesSentPersec',
    u'IMPresenceQueriesPersec', u'IMSentMessageDeliveryFailurePercent', u'IMSignInFailurePercent',
    u'IMSignInFailures', u'IMSignInFailuresPersec', u'IMTotalMessageDeliveryFailures',
    u'IMTotalMessagesReceived', u'IMTotalMessagesSent', u'IMTotalPresenceQueries', u'IMTotalUsers',
    u'IMUsersCurrentlySignedIn', u'InvalidCanaryRequests', u'IRMprotectedMessagesSent',
    u'ItemsCreatedSinceOWAStart', u'ItemsDeletedSinceOWAStart', u'ItemsUpdatedSinceOWAStart',
    u'LogonsPersec', u'LogonsPersecLight', u'LogonsPersecPremium', u'MailboxNotificationsPersec',
    u'MailboxOfflineExceptionFailurePercent', u'MailViewRefreshes', u'MailViewsLoaded',
    u'MessagesSent', u'Name', u'NamesChecked', u'PasswordChanges', u'PeakUserCount',
    u'PeakUserCountLight', u'PeakUserCountPremium', u'PID', u'ProxyRequestBytes',
    u'ProxyResponseBytes', u'ProxyResponseTimeAverage', u'ProxyUserRequests',
    u'ProxyUserRequestsPersec', u'QueuedConversionRequests', u'RejectedConversions', u'Requests',
    u'RequestsFailed', u'RequestsPersec', u'RequestTimeOuts', u'Searches', u'SearchesTimedOut',
    u'SenderPhotosLDAPcallsPersec', u'SenderPhotosTotalentriesinRecipientsNegativeCache',
    u'SenderPhotosTotalLDAPcalls', u'SenderPhotosTotalLDAPcallsreturnednonemptyimagedata',
    u'SenderPhotosTotalnumberofavoidedLDAPcallsduetocache', u'SessionDataCachebuildscompleted',
    u'SessionDataCachebuildstarts', u'SessionDataCachetimeout', u'SessionDataCacheused',
    u'SessionDataCachewaitedforpreloadtocomplete', u'SessionsEndedbyLogoff',
    u'SessionsEndedbyTimeout', u'SpellingChecks', u'StoragePermanentExceptionFailurePercent',
    u'StorageTransientExceptionFailurePercent', u'StoreLogonFailurePercent',
    u'SuccessfulConversionRequestsKBPersec', u'Timestamp_Object', u'Timestamp_PerfTime',
    u'Timestamp_Sys100NS', u'TotalMailboxNotifications', u'TotalUniqueUsers',
    u'TotalUniqueUsersLight', u'TotalUniqueUsersPremium',
    u'TotalUsercontextReInitializationrequests', u'TotalUsers', u'TotalUsersLight',
    u'TotalUsersPremium', u'UNCRequests', u'UNCResponseBytes', u'UNCResponseBytesPersec',
    u'WSSRequests', u'WSSResponseBytes', u'WSSResponseBytesPersec'
],
        [
            u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
            u'0', u'', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
            u'0', u'0', u'0', u'0', u'', u'0', u'0', u'0', u'1953125', u'10000000', u'0', u'0',
            u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
            u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'', u'0', u'0',
            u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
            u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
            u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'6743176249526', u'130951777565180000', u'0',
            u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0'
        ]]

discovery = {'': [(None, None)]}

checks = {
    '': [(None, {}, [(0, '0.00 requests/sec', [('requests_per_sec', 0.0, None, None, None, None)]),
                     (0, '0 unique users', [('current_users', 0.0, None, None, None, None)])])]
}
