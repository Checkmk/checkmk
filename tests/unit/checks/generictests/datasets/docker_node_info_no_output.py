# -*- encoding: utf-8
# yapf: disable


checkname = 'docker_node_info'


info = [['']]


discovery = {'': [(None, {})], 'containers': [(None, {})]}


checks = {'': [(None, {}, [])],
          'containers': [(None,
                          {},
                          [(3, 'containers: count not present in agent output', []),
                           (3, 'running: count not present in agent output', []),
                           (3, 'paused: count not present in agent output', []),
                           (3, 'stopped: count not present in agent output', [])])]}