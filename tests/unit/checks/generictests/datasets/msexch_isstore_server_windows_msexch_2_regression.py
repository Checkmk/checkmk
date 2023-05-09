#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'msexch_isstore'

info = [[
    u'Activemailboxes', u'AverageKeywordStatsSearchExecutionTime',
    u'AverageKeywordStatsSearchExecutionTime_Base', u'AverageMultiMailboxSearchFailed',
    u'AverageMultiMailboxSearchFailed_Base', u'AverageMultiMailboxSearchQueryLength',
    u'AverageMultiMailboxSearchQueryLength_Base',
    u'AverageMultiMailboxSearchtimespentinFullTextIndex',
    u'AverageMultiMailboxSearchtimespentinFullTextIndex_Base',
    u'AverageMultiMailboxSearchtimespentinStorecalls',
    u'AverageMultiMailboxSearchtimespentinStorecalls_Base',
    u'AveragenumberofKeywordsinMultiMailboxSearch',
    u'AveragenumberofKeywordsinMultiMailboxSearch_Base', u'AverageSearchExecutionTime',
    u'AverageSearchExecutionTime_Base', u'Averagesearchresultsperquery',
    u'Averagesearchresultsperquery_Base', u'CachedeletesintheAddressInfocachePersec',
    u'CachedeletesintheDatabaseInfocachePersec',
    u'CachedeletesintheDistributionListMembershipcachePersec',
    u'CachedeletesintheForeignAddressInfocachePersec',
    u'CachedeletesintheForeignMailboxInfocachePersec',
    u'CachedeletesintheIncompleteAddressInfocachePersec',
    u'CachedeletesintheLogicalIndexcachePersec', u'CachedeletesintheMailboxInfocachePersec',
    u'CachedeletesintheOrganizationContainercachePersec', u'CachehitsintheAddressInfocachePersec',
    u'CachehitsintheDatabaseInfocachePersec',
    u'CachehitsintheDistributionListMembershipcachePersec',
    u'CachehitsintheForeignAddressInfocachePersec', u'CachehitsintheForeignMailboxInfocachePersec',
    u'CachehitsintheIncompleteAddressInfocachePersec', u'CachehitsintheLogicalIndexcachePersec',
    u'CachehitsintheMailboxInfocachePersec', u'CachehitsintheOrganizationContainercachePersec',
    u'CacheinsertsintheAddressInfocachePersec', u'CacheinsertsintheDatabaseInfocachePersec',
    u'CacheinsertsintheDistributionListMembershipcachePersec',
    u'CacheinsertsintheForeignAddressInfocachePersec',
    u'CacheinsertsintheForeignMailboxInfocachePersec',
    u'CacheinsertsintheIncompleteAddressInfocachePersec',
    u'CacheinsertsintheLogicalIndexcachePersec', u'CacheinsertsintheMailboxInfocachePersec',
    u'CacheinsertsintheOrganizationContainercachePersec',
    u'CachelookupsintheAddressInfocachePersec', u'CachelookupsintheDatabaseInfocachePersec',
    u'CachelookupsintheDistributionListMembershipcachePersec',
    u'CachelookupsintheForeignAddressInfocachePersec',
    u'CachelookupsintheForeignMailboxInfocachePersec',
    u'CachelookupsintheIncompleteAddressInfocachePersec',
    u'CachelookupsintheLogicalIndexcachePersec', u'CachelookupsintheMailboxInfocachePersec',
    u'CachelookupsintheOrganizationContainercachePersec', u'CachemissesintheAddressInfocachePersec',
    u'CachemissesintheDatabaseInfocachePersec',
    u'CachemissesintheDistributionListMembershipcachePersec',
    u'CachemissesintheForeignAddressInfocachePersec',
    u'CachemissesintheForeignMailboxInfocachePersec',
    u'CachemissesintheIncompleteAddressInfocachePersec', u'CachemissesintheLogicalIndexcachePersec',
    u'CachemissesintheMailboxInfocachePersec', u'CachemissesintheOrganizationContainercachePersec',
    u'Caption', u'DatabaseLevelMaintenancesPersec', u'DatabaseState', u'Description',
    u'FolderscreatedPersec', u'FoldersdeletedPersec', u'FoldersopenedPersec', u'Frequency_Object',
    u'Frequency_PerfTime', u'Frequency_Sys100NS', u'IntegrityCheckDropBusyJobs',
    u'IntegrityCheckFailedJobs', u'IntegrityCheckPendingJobs', u'IntegrityCheckTotalJobs',
    u'LastMaintenanceItemRequestedAge', u'Lazyindexchunkedpopulations', u'LazyindexescreatedPersec',
    u'LazyindexesdeletedPersec', u'LazyindexfullrefreshPersec',
    u'LazyindexincrementalrefreshPersec', u'LazyindexinvalidationduetolocaleversionchangePersec',
    u'LazyindexinvalidationPersec', u'Lazyindexnonchunkedpopulations',
    u'Lazyindexpopulationsfromindex', u'Lazyindexpopulationswithouttransactionpulsing',
    u'Lazyindextotalpopulations', u'LostDiagnosticEntries', u'MailboxesWithMaintenanceItems',
    u'MailboxLevelMaintenanceItems', u'MailboxLevelMaintenancesPersec',
    u'MAPIMessagesCreatedPersec', u'MAPIMessagesModifiedPersec', u'MAPIMessagesOpenedPersec',
    u'MessagescreatedPersec', u'MessagesdeletedPersec', u'MessagesDeliveredPersec',
    u'MessagesopenedPersec', u'MessagesSubmittedPersec', u'MessagesupdatedPersec',
    u'MultiMailboxKeywordStatsSearchPersec', u'MultiMailboxPreviewSearchPersec',
    u'MultiMailboxSearchFullTextIndexQueryPersec', u'Name',
    u'NonrecursivefolderhierarchyreloadsPersec', u'Numberofactivebackgroundtasks',
    u'NumberofactiveWLMLogicalIndexmaintenancetablemaintenances',
    u'NumberofmailboxesmarkedforWLMLogicalIndexmaintenancetablemaintenance',
    u'NumberofprocessingLogicalIndexmaintenancetasks',
    u'NumberofscheduledLogicalIndexmaintenancetasks', u'PercentRPCRequests',
    u'PercentRPCRequests_Base', u'ProcessID', u'PropertypromotionmessagesPersec',
    u'PropertypromotionsPersec', u'PropertyPromotionTasks', u'QuarantinedComponentCount',
    u'QuarantinedMailboxCount', u'QuarantinedSchemaUpgraderCount',
    u'QuarantinedUserAccessibleMailboxCount', u'RecursivefolderhierarchyreloadsPersec',
    u'RPCAverageLatency', u'RPCAverageLatency_Base', u'RPCOperationsPersec', u'RPCPacketsPersec',
    u'RPCPoolContextHandles', u'RPCPoolParkedAsyncNotificationCalls', u'RPCPoolPools',
    u'RPCRequests', u'ScheduledISIntegDetectedCount', u'ScheduledISIntegFixedCount',
    u'ScheduledISIntegPersec', u'SearchPersec', u'SearchresultsPersec', u'SizeofAddressInfocache',
    u'SizeofDatabaseInfocache', u'SizeofDistributionListMembershipcache',
    u'SizeofForeignAddressInfocache', u'SizeofForeignMailboxInfocache',
    u'SizeofIncompleteAddressInfocache', u'SizeofLogicalIndexcache', u'SizeofMailboxInfocache',
    u'SizeofOrganizationContainercache', u'SizeoftheexpirationqueuefortheAddressInfocache',
    u'SizeoftheexpirationqueuefortheDatabaseInfocache',
    u'SizeoftheexpirationqueuefortheDistributionListMembershipcache',
    u'SizeoftheexpirationqueuefortheForeignAddressInfocache',
    u'SizeoftheexpirationqueuefortheForeignMailboxInfocache',
    u'SizeoftheexpirationqueuefortheIncompleteAddressInfocache',
    u'SizeoftheexpirationqueuefortheLogicalIndexcache',
    u'SizeoftheexpirationqueuefortheMailboxInfocache',
    u'SizeoftheexpirationqueuefortheOrganizationContainercache', u'SubobjectscleanedPersec',
    u'SubobjectscreatedPersec', u'SubobjectsdeletedPersec', u'Subobjectsintombstone',
    u'SubobjectsopenedPersec', u'SuccessfulsearchPersec', u'Timestamp_Object',
    u'Timestamp_PerfTime', u'Timestamp_Sys100NS', u'TopMessagescleanedPersec',
    u'Topmessagesintombstone', u'TotalfailedmultimailboxkeywordstatisticsSearches',
    u'TotalfailedmultimailboxPreviewSearches', u'TotalMultiMailboxkeywordstatisticssearches',
    u'Totalmultimailboxkeywordstatisticssearchestimedout', u'TotalMultiMailboxpreviewsearches',
    u'Totalmultimailboxpreviewsearchestimedout',
    u'TotalMultiMailboxsearchesfailedduetoFullTextfailure',
    u'TotalmultimailboxsearchesFullTextIndexQueryExecution',
    u'Totalnumberofsuccessfulsearchqueries', u'Totalobjectssizeintombstonebytes', u'Totalsearches',
    u'Totalsearchesinprogress', u'Totalsearchqueriescompletedin005sec',
    u'Totalsearchqueriescompletedin052sec', u'Totalsearchqueriescompletedin1060sec',
    u'Totalsearchqueriescompletedin210sec', u'Totalsearchqueriescompletedin60sec'
],
        [
            u'9', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
            u'0', u'2219184', u'3736', u'8803', u'756', u'0', u'0', u'0', u'0', u'8777', u'10033',
            u'0', u'8331793', u'16999241', u'0', u'0', u'0', u'0', u'223497', u'4021508', u'0',
            u'8811', u'756', u'0', u'0', u'0', u'0', u'9663', u'10041', u'0', u'8344336',
            u'17000070', u'0', u'12543', u'10788', u'0', u'242823', u'4032296', u'0', u'12543',
            u'829', u'0', u'12543', u'10788', u'0', u'19326', u'10788', u'0', u'', u'516', u'1',
            u'', u'3736', u'3736', u'945803', u'0', u'2536125', u'10000000', u'0', u'0', u'0', u'0',
            u'3', u'0', u'7472', u'7473', u'3736', u'612', u'0', u'3736', u'0', u'0', u'0', u'3736',
            u'0', u'0', u'0', u'3774', u'15329', u'15355', u'232526', u'28415', u'2268', u'9350',
            u'234848', u'13', u'468', u'0', u'0', u'0', u'mailbox database 0356176343', u'0', u'0',
            u'0', u'0', u'0', u'0', u'0', u'50', u'8084', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
            u'631', u'560849', u'3606679', u'5831463', u'3606679', u'146', u'9', u'67', u'0', u'0',
            u'0', u'0', u'3736', u'2219184', u'8', u'1', u'0', u'0', u'0', u'0', u'0', u'8', u'0',
            u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'5264', u'5257', u'10514', u'0',
            u'5296', u'3736', u'0', u'2844496046608', u'131405402071970000', u'2275', u'0', u'0',
            u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'3736', u'0', u'3736', u'0', u'3736', u'0',
            u'0', u'0', u'0'
        ],
        [
            u'9', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
            u'0', u'2219184', u'3736', u'8803', u'756', u'0', u'0', u'0', u'0', u'8777', u'10033',
            u'0', u'8331793', u'16999243', u'0', u'0', u'0', u'0', u'223497', u'4021508', u'0',
            u'8811', u'757', u'0', u'0', u'0', u'0', u'9663', u'10041', u'0', u'8344336',
            u'17000073', u'0', u'12543', u'10788', u'0', u'242823', u'4032296', u'0', u'12543',
            u'830', u'0', u'12543', u'10788', u'0', u'19326', u'10788', u'0', u'', u'516', u'1',
            u'', u'3736', u'3736', u'945803', u'0', u'2536125', u'10000000', u'0', u'0', u'0', u'0',
            u'3', u'0', u'7472', u'7473', u'3736', u'612', u'0', u'3736', u'0', u'0', u'0', u'3736',
            u'0', u'0', u'0', u'3774', u'15329', u'15355', u'232526', u'28415', u'2268', u'9350',
            u'234848', u'13', u'468', u'0', u'0', u'0', u'_total', u'0', u'0', u'0', u'0', u'0',
            u'0', u'0', u'50', u'8084', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'631', u'560849',
            u'3606679', u'5831463', u'3606679', u'178', u'10', u'68', u'0', u'0', u'0', u'0',
            u'3736', u'2219184', u'8', u'2', u'0', u'0', u'0', u'0', u'0', u'8', u'0', u'0', u'0',
            u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'5264', u'5257', u'10514', u'0', u'5296',
            u'3736', u'0', u'2844496046608', u'131405402071970000', u'2275', u'0', u'0', u'0', u'0',
            u'0', u'0', u'0', u'0', u'0', u'3736', u'0', u'3736', u'0', u'3736', u'0', u'0', u'0',
            u'0'
        ]]

discovery = {'': [(u'_total', None), (u'mailbox database 0356176343', None)]}

checks = {
    '': [
        (
            u'_total',
            {
                'store_latency': {
                    'upper': (40.0, 50.0)
                },
                'clienttype_requests': {
                    'upper': (60, 70)
                },
                'clienttype_latency': {
                    'upper': (40.0, 50.0)
                }
            },
            [(
                0,
                'Average latency: 0.16 ms',
                [('average_latency', 0.15550288783670518, 40.0, 50.0, None, None)],
            )],
        ),
        (
            u'mailbox database 0356176343',
            {
                'store_latency': {
                    'upper': (40.0, 50.0)
                },
                'clienttype_requests': {
                    'upper': (60, 70)
                },
                'clienttype_latency': {
                    'upper': (40.0, 50.0)
                }
            },
            [(
                0,
                'Average latency: 0.16 ms',
                [('average_latency', 0.15550288783670518, 40.0, 50.0, None, None)],
            )],
        ),
    ],
}
