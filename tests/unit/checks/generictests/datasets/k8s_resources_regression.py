checkname = 'k8s_resources'

info = [[
    u'{"allocatable": {"pods": 110, "cpu": 0.9400000000000001, "memory": 609845248.0}, "capacity": {"pods": 110, "cpu": 1.0, "memory": 609845248.0}, "requests": {"cpu": 0.2, "memory": 0.0}, "limits": {"cpu": 0.5, "memory": Infinity}, "allocations": {}}'
]]

discovery = {
    'cpu': [(None, {})],
    'memory': [(None, {})],
    'pods': [(None, {})],
}

checks = {
    'cpu': [(None, 'default', [
        (0, 'Request: 0.200', [('k8s_cpu_request', 0.2)]),
        (0, 'Limit: 0.500', [('k8s_cpu_limit', 0.5)]),
        (0, 'Allocatable: 0.940', [('k8s_cpu_allocatable', 0.9400000000000001)]),
        (0, 'Capacity: 1.000', [('k8s_cpu_capacity', 1.0)]),
    ])],
    'memory': [(None, 'default', [
        (0, 'Request: 0.00 B', [('k8s_memory_request', 0.0)]),
        (0, 'Limit: n.a.', []),
        (0, 'Allocatable: 581.59 MB', [('k8s_memory_allocatable', 609845248.0)]),
        (0, 'Capacity: 581.59 MB', [('k8s_memory_capacity', 609845248.0)]),
    ])],
    'pods': [(None, 'default', [
        (0, 'Pods: 0', [('k8s_pods', 0)]),
        (0, 'Allocatable: 110', [('k8s_pods_allocatable', 110)]),
        (0, 'Capacity: 110', [('k8s_pods_capacity', 110)]),
    ])],
}
