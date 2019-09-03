# -*- encoding: utf-8
# yapf: disable


checkname = 'docker_container_cpu'


info = [['@docker_version_info',
         '{"PluginVersion": "0.1", "DockerPyVersion": "4.0.2", "ApiVersion": "1.40"}'],
        ['{"cpu_usage": {"usage_in_usermode": 460000000, "total_usage": 496463002, "percpu_usage": [249092600, 1110856, 5308606, 1416868, 2668609, 4305930, 227572804, 4986729], "usage_in_kernelmode": 10000000}, "system_cpu_usage": 20722470000000, "online_cpus": 8, "throttling_data": {"throttled_time": 0, "periods": 0, "throttled_periods": 0}}']]


discovery = {'': [(None, {})]}


checks = {
    '': [
        (None, {}, [
            (0, 'Total CPU: 0.02%', [
                ('util', 0.019166170905302312, None, None, 0, 100),
            ]),
        ]),
    ],
}


mock_item_state = {'': (0, 0)}
