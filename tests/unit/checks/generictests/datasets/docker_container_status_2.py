# -*- encoding: utf-8
# yapf: disable
from cmk.base.discovered_labels import HostLabel

checkname = 'docker_container_status'

info = [[
    u'@docker_version_info',
    u'{"PluginVersion": "0.1", "DockerPyVersion": "4.0.2", "ApiVersion": "1.39"}'
],
        [
            u'{"Status": "exited", "Pid": 0, "OOMKilled": false, "Dead": false, "RestartPolicy": {"MaximumRetryCount": 0, "Name": "always"}, "Paused": false, "Running": false, "FinishedAt": "2019-07-11T15:18:44.293247926Z", "Restarting": false, "Error": "", "StartedAt": "2019-07-11T13:45:30.378476501Z", "ExitCode": 0, "NodeName": "Quarktasche"}'
        ]]

discovery = {
    '': [HostLabel(u'cmk/docker_object', u'container'), (None, {})],
    'uptime': [(None, {})],
    'health': []
}

checks = {
    '': [(None, {}, [(2, u'Container exited on node Quarktasche', [])])],
    'uptime':
    [(None, {}, [(0, u'[exited]', [('uptime', 0.0, None, None, None, None)])])]
}

extra_sections = {'': [[]], 'uptime': [[]], 'health': [[]]}
