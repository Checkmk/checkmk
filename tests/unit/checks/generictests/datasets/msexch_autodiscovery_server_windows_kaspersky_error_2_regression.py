

checkname = 'msexch_autodiscovery'


info = [[u'Caption',
         u'Description',
         u'ErrorResponses',
         u'ErrorResponsesPersec',
         u'Frequency_Object',
         u'Frequency_PerfTime',
         u'Frequency_Sys100NS',
         u'Name',
         u'ProcessID',
         u'RequestsPersec',
         u'Timestamp_Object',
         u'Timestamp_PerfTime',
         u'Timestamp_Sys100NS',
         u'TotalRequests'],
        [u'',
         u'',
         u'0',
         u'0',
         u'0',
         u'2343747',
         u'10000000',
         u'',
         u'29992',
         u'19086',
         u'0',
         u'1025586529184',
         u'131287884132350000',
         u'19086']]


discovery = {'': [(None, None)]}


checks = {'': [(None,
                {},
                [(0,
                  '0.00 requests/sec',
                  [('requests_per_sec', 0.0, None, None, None, None)])])]}
