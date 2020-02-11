# yapf: disable
from cmk.base.discovered_labels import HostLabel

checkname = 'docker_node_info'


info = [
    ['@docker_version_info', '{"PluginVersion": "0.1", "DockerPyVersion": "3.7.0", "ApiVersion": "1.39"}'],
    ['{"Name": "klappson"}'],
    ['@docker_version_info', '{"PluginVersion": "0.1", "DockerPyVersion": "3.7.0", "ApiVersion": "1.39"}'],
    ['{"Unknown": "Plugin exception in section_node_disk_usage: Kokosnuss geklaut"}'],
]


discovery = {
    '': [(None, {}),
         HostLabel(u'cmk/docker_object', u'node')
        ],
    'containers': [(None, {})],
}


checks = {
    '': [
        (None, {}, [
            (0, u'Daemon running on host klappson', []),
            (3, u'Plugin exception in section_node_disk_usage: Kokosnuss geklaut', []),
        ]),
    ],
}
