checkname = 'dotnet_clrmemory'

info = [
    [
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
        u'766573506832', u'', u'', u'761', u'0', u'2240904', u'10000000', u'12582912', u'2708256',
        u'3461688', u'124320', u'60014800', u'3584288', u'_Global_', u'67060776', u'20831',
        u'60934', u'7064', u'1038', u'388', u'0', u'392', u'79908864', u'805289984', u'377048032',
        u'-1', u'0', u'406627', u'2708256', u'124320', u'0', u'4227247572262', u'131350801098190000'
    ],
    [
        u'0', u'', u'', u'0', u'0', u'2240904', u'10000000', u'0', u'0', u'0', u'0', u'0', u'0',
        u'w3wp', u'0', u'4197', u'0', u'0', u'0', u'0', u'0', u'250', u'0', u'0', u'0', u'0', u'0',
        u'0', u'0', u'0', u'0', u'4227247572262', u'131350801098190000'
    ],
    [
        u'985532528', u'', u'', u'469', u'0', u'2240904', u'10000000', u'6291456', u'1880936',
        u'1911608', u'124320', u'28709512', u'604456', u'ServerManager', u'31225576', u'14591',
        u'400', u'393', u'390', u'388', u'0', u'82', u'36921344', u'402644992', u'71295', u'270884',
        u'6240', u'14022', u'1880936', u'124320', u'0', u'4227247572262', u'131350801098190000'
    ],
    [
        u'382301220888', u'', u'', u'292', u'0', u'2240904', u'10000000', u'6291456', u'827320',
        u'1550080', u'0', u'31305288', u'2979832', u'Quartal.TaskServer', u'35835200', u'2043',
        u'60534', u'6671', u'648', u'0', u'0', u'60', u'42987520', u'402644992', u'8485',
        u'49571805', u'5920', u'392605', u'827320', u'0', u'0', u'4227247572262',
        u'131350801098190000'
    ]
]

discovery = {'': [(u'_Global_', 'dotnet_clrmemory_defaultlevels')]}

checks = {
    '': [(u'_Global_', {
        "upper": (10.0, 15.0)
    }, [(0, '8.78% time in GC', [('percent', 8.778833599942464, 10.0, 15.0, 0, 100)])])]
}
