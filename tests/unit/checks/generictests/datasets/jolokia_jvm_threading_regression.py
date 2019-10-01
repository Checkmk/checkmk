# yapf: disable


checkname = 'jolokia_jvm_threading'


info = [[u'JIRA',
         u'*:name=*,type=ThreadPool/maxThreads,currentThreadCount,currentThreadsBusy/',
         u'{"Catalina:name=\\"http-nio-8080\\",type=ThreadPool": {"maxThreads": 150,'
         ' "currentThreadCount": 25, "currentThreadsBusy": 12}}'],
        [u'JIRA',
         u'java.lang:type=Threading',
         u'{"PeakThreadCount": 142, "ThreadCpuTimeEnabled": true, "ObjectName": {"objectName": "java.lang:type=Threading"}, "CurrentThreadUserTime": 148790000000, "AllThreadIds": [3510, 3474, 3233, 2323, 2322, 2321, 234, 218, 217, 215, 214, 213, 212, 206, 205, 204, 203, 202, 201, 200, 199, 198, 197, 196, 195, 194, 193, 192, 191, 188, 187, 186, 185, 183, 182, 181, 180, 179, 178, 175, 174, 173, 172, 171, 169, 164, 159, 156, 155, 144, 139, 138, 137, 136, 135, 134, 133, 128, 119, 118, 117, 116, 115, 114, 113, 112, 111, 110, 109, 108, 107, 106, 105, 104, 103, 102, 96, 95, 94, 93, 92, 91, 90, 89, 88, 87, 86, 85, 84, 83, 82, 81, 80, 79, 78, 77, 76, 75, 74, 73, 72, 71, 70, 69, 68, 67, 66, 65, 64, 63, 62, 32, 31, 30, 29, 27, 26, 25, 23, 21, 20, 19, 18, 17, 16, 11, 10, 4, 3, 2, 1], "ThreadCpuTimeSupported": true, "ThreadContentionMonitoringEnabled": false, "ThreadCount": 131, "SynchronizerUsageSupported": true, "DaemonThreadCount": 115, "CurrentThreadCpuTimeSupported": true, "ThreadAllocatedMemorySupported": true, "ThreadAllocatedMemoryEnabled": true, "CurrentThreadCpuTime": 152910232714, "TotalStartedThreadCount": 3506, "ThreadContentionMonitoringSupported": true, "ObjectMonitorUsageSupported": true}']]


discovery = {
    '': [
        (u'JIRA', {}),
    ],
    'pool': [
        (u'JIRA ThreadPool http-nio-8080', {}),
    ],
}


checks = {
    '': [
        (u'JIRA', {'daemonthreadcount_levels': (90, 100)}, [
            (0, 'Count: 131', [('ThreadCount', 131, None, None, None, None)]),
            (0, 'Rate: 0.00', [('ThreadRate', 0.0, None, None, None, None)]),
            (2, 'Daemon threads: 115 (warn/crit at 90/100)', [('DaemonThreadCount', 115, 90, 100, None, None)]),
            (0, 'Peak count: 142', [('PeakThreadCount', 142, None, None, None, None)]),
            (0, 'Total started: 3506', [('TotalStartedThreadCount', 3506, None, None, None, None)]),
        ]),
    ],
    'pool': [
        (u'JIRA ThreadPool http-nio-8080', {'currentThreadsBusy': (5, 90)}, [
            (0, 'Maximum threads: 150', []),
            (1, 'Busy: 12 (warn/crit at 8/135)', [
                ('currentThreadsBusy', 12, 7.5, 135.0, None, 150)]),
            (0, 'Total: 25', [('currentThreadCount', 25, None, None, None, 150)]),
        ]),
    ],
}
