checkname = 'dotnet_clrmemory'

info = [[
    u'AllocatedBytesPersec', u'Caption', u'Description', u'FinalizationSurvivors',
    u'Frequency_Object', u'Frequency_PerfTime', u'Frequency_Sys100NS', u'Gen0heapsize',
    u'Gen0PromotedBytesPerSec', u'Gen1heapsize', u'Gen1PromotedBytesPerSec', u'Gen2heapsize',
    u'LargeObjectHeapsize', u'Name', u'NumberBytesinallHeaps', u'NumberGCHandles',
    u'NumberGen0Collections', u'NumberGen1Collections', u'NumberGen2Collections',
    u'NumberInducedGC', u'NumberofPinnedObjects', u'NumberofSinkBlocksinuse',
    u'NumberTotalcommittedBytes', u'NumberTotalreservedBytes', u'PercentTimeinGC',
    u'PercentTimeinGC_Base', u'ProcessID', u'PromotedFinalizationMemoryfromGen0',
    u'PromotedMemoryfromGen0', u'PromotedMemoryfromGen1', u'Timestamp_Object',
    u'Timestamp_PerfTime', u'Timestamp_Sys100NS'
],
        [
            u'46584024', u'', u'', u'201', u'0', u'3914064', u'10000000', u'6291456', u'1110904',
            u'1100372', u'850168', u'3279916', u'73912', u'_Global_', u'4454200', u'1470', u'4',
            u'3', u'1', u'0', u'39', u'135', u'10493952', u'33546240', u'3003926', u'-1', u'0',
            u'15076', u'1110904', u'850168', u'0', u'9918361461', u'131261124692120000'
        ],
        [
            u'0', u'', u'', u'0', u'0', u'3914064', u'10000000', u'0', u'0', u'0', u'0', u'0', u'0',
            u'isa', u'0', u'41', u'0', u'0', u'0', u'0', u'0', u'8', u'0', u'0', u'0', u'0', u'0',
            u'0', u'0', u'0', u'0', u'9918361461', u'131261124692120000'
        ],
        [
            u'0', u'', u'', u'0', u'0', u'3914064', u'10000000', u'0', u'0', u'0', u'0', u'0', u'0',
            u'SCNotification', u'0', u'390', u'0', u'0', u'0', u'0', u'0', u'65', u'0', u'0', u'0',
            u'0', u'0', u'0', u'0', u'0', u'0', u'9918361461', u'131261124692120000'
        ],
        [
            u'23292012', u'', u'', u'201', u'0', u'3914064', u'10000000', u'6291456', u'1110904',
            u'1100372', u'850168', u'3279916', u'73912', u'IAStorDataMgrSvc', u'4454200', u'678',
            u'4', u'3', u'1', u'0', u'39', u'30', u'10493952', u'33546240', u'162041', u'46336747',
            u'5804', u'15076', u'1110904', u'850168', u'0', u'9918361461', u'131261124692120000'
        ],
        [
            u'0', u'', u'', u'0', u'0', u'3914064', u'10000000', u'0', u'0', u'0', u'0', u'0', u'0',
            u'CcmExec', u'0', u'21', u'0', u'0', u'0', u'0', u'0', u'2', u'0', u'0', u'0', u'0',
            u'0', u'0', u'0', u'0', u'0', u'9918361461', u'131261124692120000'
        ],
        [
            u'0', u'', u'', u'0', u'0', u'3914064', u'10000000', u'0', u'0', u'0', u'0', u'0', u'0',
            u'IAStorIcon', u'0', u'340', u'0', u'0', u'0', u'0', u'0', u'30', u'0', u'0', u'0',
            u'0', u'0', u'0', u'0', u'0', u'0', u'9918361461', u'131261124692120000'
        ]]

discovery = {'': [(u'_Global_', 'dotnet_clrmemory_defaultlevels')]}

checks = {
    '': [(u'_Global_', {
        "upper": (10.0, 15.0)
    }, [(0, '0.07% time in GC', [('percent', 0.06994060242314372, 10.0, 15.0, 0, 100)])])]
}
