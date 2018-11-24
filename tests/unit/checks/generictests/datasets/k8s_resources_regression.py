checkname = 'k8s_resources'

info = [[
    u'{"capacity": {"pods": 110, "cpu": 1.0, "memory": 609845248.0}, "requests": {"cpu": 0.2, "memory": 0.0}, "limits": {"cpu": 0.5, "memory": Infinity}, "allocations": {}}'
]]

discovery = {
    'cpu': [(None, {})],
    'memory': [(None, {})],
    'pods': [(None, {})],
}

checks = {
    'cpu': [(None, 'default', [
        (0, 'Request: 0.200', []),
        (0, 'Limit: 0.500', []),
        (0, 'Capacity: 1.000', []),
    ])],
    'memory': [(None, 'default', [
        (0, 'Request: 0.00 B', []),
        (0, 'Limit: n.a.', []),
        (0, 'Capacity: 581.59 MB', []),
    ])],
    'pods': [(None, 'default', [
        (0, 'Pods: 0', []),
        (0, 'Capacity: 110', []),
    ])],
}
