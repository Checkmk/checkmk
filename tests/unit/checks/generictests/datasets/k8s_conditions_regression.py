

checkname = 'k8s_conditions'


info = [[u'{"DiskPressure": "False", "OutOfDisk": "False", "MemoryPressure": "False", "Ready": "False", "NetworkUnavailable": "False", "KernelDeadlock": "True"}']]


discovery = {'': [(u'DiskPressure', {}),
                  (u'KernelDeadlock', {}),
                  (u'MemoryPressure', {}),
                  (u'NetworkUnavailable', {}),
                  (u'OutOfDisk', {}),
                  (u'Ready', {})]}


checks = {'': [(u'DiskPressure', 'default', [(0, u'False', [])]),
               (u'KernelDeadlock', 'default', [(2, u'True', [])]),
               (u'MemoryPressure', 'default', [(0, u'False', [])]),
               (u'NetworkUnavailable', 'default', [(0, u'False', [])]),
               (u'OutOfDisk', 'default', [(0, u'False', [])]),
               (u'Ready', 'default', [(2, u'False', [])])]}
