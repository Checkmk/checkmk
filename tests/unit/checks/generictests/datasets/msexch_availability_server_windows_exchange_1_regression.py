# yapf: disable
checkname = 'msexch_availability'

info = [[
    u'AvailabilityRequestssec', u'AverageNumberofMailboxesProcessedperRequest',
    u'AverageNumberofMailboxesProcessedperRequest_Base',
    u'AverageTimetoMapExternalCallertoInternalIdentity',
    u'AverageTimetoMapExternalCallertoInternalIdentity_Base',
    u'AverageTimetoProcessaCrossForestFreeBusyRequest',
    u'AverageTimetoProcessaCrossForestFreeBusyRequest_Base',
    u'AverageTimetoProcessaCrossSiteFreeBusyRequest',
    u'AverageTimetoProcessaCrossSiteFreeBusyRequest_Base',
    u'AverageTimetoProcessaFederatedFreeBusyRequest',
    u'AverageTimetoProcessaFederatedFreeBusyRequest_Base',
    u'AverageTimetoProcessaFederatedFreeBusyRequestwithOAuth',
    u'AverageTimetoProcessaFederatedFreeBusyRequestwithOAuth_Base',
    u'AverageTimetoProcessaFreeBusyRequest', u'AverageTimetoProcessaFreeBusyRequest_Base',
    u'AverageTimetoProcessaMeetingSuggestionsRequest',
    u'AverageTimetoProcessaMeetingSuggestionsRequest_Base',
    u'AverageTimetoProcessanIntraSiteFreeBusyRequest',
    u'AverageTimetoProcessanIntraSiteFreeBusyRequest_Base', u'Caption',
    u'ClientReportedFailuresAutodiscoverFailures', u'ClientReportedFailuresConnectionFailures',
    u'ClientReportedFailuresPartialorOtherFailures', u'ClientReportedFailuresTimeoutFailures',
    u'ClientReportedFailuresTotal', u'CrossForestCalendarFailuressec',
    u'CrossForestCalendarQueriessec', u'CrossSiteCalendarFailuressec',
    u'CrossSiteCalendarQueriessec', u'CurrentRequests', u'Description',
    u'FederatedFreeBusyCalendarQueriesincludingOAuthsec', u'FederatedFreeBusyFailuressec',
    u'FederatedFreeBusyFailureswithOAuthsec', u'ForeignConnectorQueriessec',
    u'ForeignConnectorRequestFailureRate', u'Frequency_Object', u'Frequency_PerfTime',
    u'Frequency_Sys100NS', u'IntraSiteCalendarFailuressec', u'IntraSiteCalendarQueriessec',
    u'IntraSiteProxyFreeBusyCalendarQueriessec', u'IntraSiteProxyFreeBusyFailuressec', u'Name',
    u'PublicFolderQueriessec', u'PublicFolderRequestFailuressec',
    u'SuccessfulClientReportedRequestsLessthan10seconds',
    u'SuccessfulClientReportedRequestsLessthan20seconds',
    u'SuccessfulClientReportedRequestsLessthan5seconds',
    u'SuccessfulClientReportedRequestsOver20seconds', u'SuccessfulClientReportedRequestsTotal',
    u'SuggestionsRequestssec', u'Timestamp_Object', u'Timestamp_PerfTime', u'Timestamp_Sys100NS'
],
        [
            u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
            u'0', u'0', u'0', u'0', u'0', u'', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
            u'0', u'', u'0', u'0', u'0', u'0', u'0', u'0', u'1953125', u'10000000', u'0', u'0',
            u'0', u'0', u'', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'6743176212200',
            u'130951777565030000'
        ]]

discovery = {'': [(None, None)]}

checks = {
    '': [(None, {}, [(0, '0.00 requests/sec', [('requests_per_sec', 0.0, None, None, None,
                                                None)])])]
}
