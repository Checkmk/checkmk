# -*- encoding: utf-8
# yapf: disable
from cmk.base.discovered_labels import HostLabel

checkname = 'docker_node_info'


info = [['']]


discovery = {'': [(None, {}), HostLabel(u'cmk/docker_object', u'node')],
            'containers': [(None, {})]}


checks = {'': [(None, {}, [])],
          'containers': [(None,
                          {},
                          [(3, 'Containers: count not present in agent output', []),
                           (3, 'Running: count not present in agent output', []),
                           (3, 'Paused: count not present in agent output', []),
                           (3, 'Stopped: count not present in agent output', [])])]}
