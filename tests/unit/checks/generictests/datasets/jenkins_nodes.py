# -*- encoding: utf-8
# yapf: disable
checkname = 'jenkins_nodes'

info = [
    [
        u'[{"displayName": "master", "description": "the master Jenkins node", "temporarilyOffline": false, "monitorData": {"hudson.node_monitors.SwapSpaceMonitor": {"totalPhysicalMemory": 67429359616, "availableSwapSpace": 59097583616, "_class": "hudson.node_monitors.SwapSpaceMonitor$MemoryUsage2", "availablePhysicalMemory": 4450242560, "totalSwapSpace": 64000876544}, "hudson.node_monitors.ClockMonitor": {"diff": 0, "_class": "hudson.util.ClockDifference"}, "hudson.node_monitors.DiskSpaceMonitor": {"size": 290845855744, "timestamp": 1573468791686, "_class": "hudson.node_monitors.DiskSpaceMonitorDescriptor$DiskSpace", "path": "/var/lib/jenkins"}, "hudson.node_monitors.TemporarySpaceMonitor": {"size": 32569888768, "timestamp": 1573468792277, "_class": "hudson.node_monitors.DiskSpaceMonitorDescriptor$DiskSpace", "path": "/tmp"}, "hudson.node_monitors.ResponseTimeMonitor": {"timestamp": 1573468791687, "average": 0, "_class": "hudson.node_monitors.ResponseTimeMonitor$Data"}, "hudson.node_monitors.ArchitectureMonitor": "MYARCH1"}, "assignedLabels": [{"busyExecutors": 3, "idleExecutors": 17, "nodes": [{"_class": "hudson.model.Hudson", "mode": "EXCLUSIVE"}]}, {"busyExecutors": 3, "idleExecutors": 17}], "numExecutors": 20, "idle": false, "offlineCause": null, "offline": false, "_class": "hudson.model.Hudson$MasterComputer", "jnlpAgent": false}, {"displayName": "Windows", "description": "Name: MYNAME, IP-Address: 1.1.1.1", "temporarilyOffline": false, "monitorData": {"hudson.node_monitors.SwapSpaceMonitor": {"totalPhysicalMemory": 17179332608, "availableSwapSpace": 8569982976, "_class": "hudson.node_monitors.SwapSpaceMonitor$MemoryUsage2", "availablePhysicalMemory": 5656227840, "totalSwapSpace": 22548041728}, "hudson.node_monitors.ClockMonitor": {"diff": 8, "_class": "hudson.util.ClockDifference"}, "hudson.node_monitors.DiskSpaceMonitor": {"size": 15085674496, "timestamp": 1573468791711, "_class": "hudson.node_monitors.DiskSpaceMonitorDescriptor$DiskSpace", "path": "C:\\\\"}, "hudson.node_monitors.TemporarySpaceMonitor": {"size": 15085674496, "timestamp": 1573468792334, "_class": "hudson.node_monitors.DiskSpaceMonitorDescriptor$DiskSpace", "path": "C:\\\\Windows\\\\Temp"}, "hudson.node_monitors.ResponseTimeMonitor": {"timestamp": 1573468791722, "average": 35, "_class": "hudson.node_monitors.ResponseTimeMonitor$Data"}, "hudson.node_monitors.ArchitectureMonitor": "MYARCH"}, "assignedLabels": [{"busyExecutors": 0, "idleExecutors": 1, "nodes": [{"_class": "hudson.slaves.DumbSlave", "mode": "EXCLUSIVE"}]}, {"busyExecutors": 0, "idleExecutors": 1}], "numExecutors": 1, "idle": true, "offlineCause": null, "offline": false, "_class": "hudson.slaves.SlaveComputer", "jnlpAgent": true}]'
    ]
]

discovery = {'': [(u'Windows', {}), (u'master', {})]}

checks = {
    '': [
        (
            u'Windows', {
                'jenkins_offline': 2
            }, [
                (0, u'Description: Name: Myname, Ip-Address: 1.1.1.1', []),
                (0, 'Is JNLP agent: yes', []), (0, 'Is idle: yes', []),
                (
                    0, 'Total number of executors: 1', [
                        ('jenkins_num_executors', 1, None, None, None, None)
                    ]
                ),
                (
                    0, 'Number of busy executors: 0', [
                        ('jenkins_busy_executors', 0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Number of idle executors: 1', [
                        ('jenkins_idle_executors', 1, None, None, None, None)
                    ]
                ), (0, u'Mode: Exclusive ', []), (0, 'Offline: no', []),
                (
                    0, u'Average response time: 35.0 ms', [
                        ('avg_response_time', 0.035, None, None, None, None)
                    ]
                ),
                (
                    0, u'Clock difference: 8.00 ms', [
                        ('jenkins_clock', 0.008, None, None, None, None)
                    ]
                ),
                (
                    0, 'Free temp space: 14.05 GB', [
                        ('jenkins_temp', 15085674496, None, None, None, None)
                    ]
                )
            ]
        ),
        (
            u'master', {
                'jenkins_offline': 2
            }, [
                (0, u'Description: The Master Jenkins Node', []),
                (0, 'Is JNLP agent: no', []), (0, 'Is idle: no', []),
                (
                    0, 'Total number of executors: 20', [
                        ('jenkins_num_executors', 20, None, None, None, None)
                    ]
                ),
                (
                    0, 'Number of busy executors: 3', [
                        ('jenkins_busy_executors', 3, None, None, None, None)
                    ]
                ),
                (
                    0, 'Number of idle executors: 17', [
                        ('jenkins_idle_executors', 17, None, None, None, None)
                    ]
                ), (0, u'Mode: Exclusive ', []), (0, 'Offline: no', []),
                (
                    0, u'Average response time: 0.00 s', [
                        ('avg_response_time', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, u'Clock difference: 0.00 s', [
                        ('jenkins_clock', 0.0, None, None, None, None)
                    ]
                ),
                (
                    0, 'Free temp space: 30.33 GB', [
                        ('jenkins_temp', 32569888768, None, None, None, None)
                    ]
                )
            ]
        )
    ]
}
