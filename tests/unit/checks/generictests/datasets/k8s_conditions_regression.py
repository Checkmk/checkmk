# yapf: disable
checkname = 'k8s_conditions'

info = [[
    u'{"DiskPressure": "False", "OutOfDisk": "False", "MemoryPressure": "False", "Ready": "False", "NetworkUnavailable": "False", "KernelDeadlock": "True"}'
]]

discovery = {
    '': [(u'DiskPressure', {}), (u'KernelDeadlock', {}), (u'MemoryPressure', {}),
         (u'NetworkUnavailable', {}), (u'OutOfDisk', {}), (u'Ready', {})]
}

checks = {
    '': [(u'DiskPressure', {}, [(0, u'False', [])]), (u'KernelDeadlock', {}, [(2, u'True', [])]),
         (u'MemoryPressure', {}, [(0, u'False', [])]),
         (u'NetworkUnavailable', {}, [(0, u'False', [])]), (u'OutOfDisk', {}, [(0, u'False', [])]),
         (u'Ready', {}, [(2, u'False', [])])]
}
