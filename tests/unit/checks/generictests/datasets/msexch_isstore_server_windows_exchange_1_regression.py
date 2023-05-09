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
    u'MailboxKeyDecryptAverageLatency', u'MailboxKeyDecryptAverageLatency_Base',
    u'MailboxKeyDecryptsPersec', u'MailboxKeyEncryptsPersec', u'MailboxLevelMaintenanceItems',
    u'MailboxLevelMaintenancesPersec', u'MAPIMessagesCreatedPersec', u'MAPIMessagesModifiedPersec',
    u'MAPIMessagesOpenedPersec', u'MessagescreatedPersec', u'MessagesdeletedPersec',
    u'MessagesDeliveredPersec', u'MessagesopenedPersec', u'MessagesSubmittedPersec',
    u'MessagesupdatedPersec', u'MultiMailboxKeywordStatsSearchPersec',
    u'MultiMailboxPreviewSearchPersec', u'MultiMailboxSearchFullTextIndexQueryPersec', u'Name',
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
    u'ScheduledISIntegPersec', u'ScopeKeyReadAverageLatency', u'ScopeKeyReadAverageLatency_Base',
    u'ScopeKeyReadsPersec', u'SearchPersec', u'SearchresultsPersec', u'SizeofAddressInfocache',
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
    u'SubobjectsopenedPersec', u'SuccessfulsearchPersec', u'TimedEventsProcessed',
    u'TimedEventsProcessedPersec', u'TimedEventsProcessingFailures', u'Timestamp_Object',
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
            u'4', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
            u'0', u'0', u'0', u'11705', u'2038', u'0', u'0', u'0', u'0', u'52', u'7962', u'0',
            u'12671984', u'18440396', u'0', u'0', u'0', u'0', u'639930', u'6127781', u'0', u'11708',
            u'2038', u'0', u'0', u'0', u'0', u'623', u'7964', u'0', u'12684158', u'18442669', u'0',
            u'12174', u'8514', u'0', u'641176', u'6136295', u'0', u'12174', u'2273', u'0', u'12174',
            u'8514', u'0', u'1246', u'8514', u'0', u'', u'11724', u'1', u'', u'0', u'0', u'1220570',
            u'0', u'1953125', u'10000000', u'0', u'0', u'0', u'0', u'0', u'0', u'3', u'24', u'3',
            u'838', u'0', u'0', u'0', u'2', u'0', u'3', u'0', u'1', u'0', u'0', u'0', u'0', u'1',
            u'11680', u'40243', u'51785', u'66714', u'80486', u'23006', u'28741', u'101226',
            u'11502', u'23140', u'0', u'0', u'0', u'db3', u'0', u'0', u'0', u'1', u'0', u'0', u'0',
            u'50', u'5716', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'284', u'1977204',
            u'4308720', u'6138327', u'4308720', u'23304', u'8', u'11650', u'0', u'0', u'0', u'0',
            u'0', u'0', u'0', u'0', u'0', u'3', u'1', u'0', u'0', u'0', u'0', u'8', u'2', u'0',
            u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
            u'0', u'0', u'0', u'0', u'0', u'6743176366056', u'130951777565810000', u'23004', u'2',
            u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
            u'0', u'0', u'0'
        ],
        [
            u'4', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
            u'0', u'0', u'0', u'11705', u'2038', u'0', u'0', u'0', u'0', u'52', u'7962', u'0',
            u'12671984', u'18440397', u'0', u'0', u'0', u'0', u'639930', u'6127781', u'0', u'11708',
            u'2039', u'0', u'0', u'0', u'0', u'623', u'7964', u'0', u'12684158', u'18442671', u'0',
            u'12174', u'8514', u'0', u'641176', u'6136295', u'0', u'12174', u'2274', u'0', u'12174',
            u'8514', u'0', u'1246', u'8514', u'0', u'', u'11724', u'1', u'', u'0', u'0', u'1220570',
            u'0', u'1953125', u'10000000', u'0', u'0', u'0', u'0', u'0', u'0', u'3', u'24', u'3',
            u'838', u'0', u'0', u'0', u'2', u'0', u'3', u'0', u'1', u'0', u'0', u'0', u'0', u'1',
            u'11680', u'40243', u'51785', u'66714', u'80486', u'23006', u'28741', u'101226',
            u'11502', u'23140', u'0', u'0', u'0', u'_total', u'0', u'0', u'0', u'1', u'0', u'0',
            u'0', u'50', u'5716', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'284', u'1977204',
            u'4308720', u'6138327', u'4308720', u'23336', u'9', u'11651', u'0', u'0', u'0', u'0',
            u'0', u'0', u'0', u'0', u'0', u'3', u'2', u'0', u'0', u'0', u'0', u'8', u'2', u'0',
            u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
            u'0', u'0', u'0', u'0', u'0', u'6743176366056', u'130951777565810000', u'23004', u'2',
            u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0', u'0',
            u'0', u'0', u'0'
        ]]

discovery = {'': [(u'_total', None), (u'db3', None)]}

checks = {
    '': [
        (u'_total', {
            'store_latency': {
                'upper': (40.0, 50.0)
            },
            'clienttype_requests': {
                'upper': (60, 70)
            },
            'clienttype_latency': {
                'upper': (40.0, 50.0)
            }
        }, [(0, 'Average latency: 0.46 ms', [('average_latency', 0.45888430902913163, 40.0, 50.0,
                                            None, None)])]),
        (u'db3', {
            'store_latency': {
                'upper': (40.0, 50.0)
            },
            'clienttype_requests': {
                'upper': (60, 70)
            },
            'clienttype_latency': {
                'upper': (40.0, 50.0)
            }
        }, [(0, 'Average latency: 0.46 ms', [('average_latency', 0.45888430902913163, 40.0, 50.0,
                                            None, None)])]),
    ]
}
