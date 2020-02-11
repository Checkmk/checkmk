# yapf: disable
from cmk.base.discovered_labels import HostLabel

checkname = 'docker_node_info'

info = [['|Containers', ' 0'], ['| Running', ' 0'], ['| Paused', ' 0'], ['| Stopped', ' 0'],
        ['|Images', ' 0'], ['|Server Version', ' 18.06.1-ce'], ['|Storage Driver', ' overlay2'],
        ['| Backing Filesystem', ' extfs'], ['| Supports d_type', ' true'],
        ['| Native Overlay Diff', ' true'], ['|Logging Driver', ' json-file'],
        ['|Cgroup Driver', ' cgroupfs'], ['|Plugins', ''], ['| Volume', ' local'],
        ['| Network', ' bridge host macvlan null overlay'],
        ['| Log', ' awslogs fluentd gcplogs gelf journald json-file logentries splunk syslog'],
        ['|Swarm', ' inactive'], ['|Runtimes', ' runc'], ['|Default Runtime', ' runc'],
        ['|Init Binary', ' docker-init'],
        ['|containerd version', ' 468a545b9edcd5932818eb9de8e72413e616e86e'],
        ['|runc version', ' 69663f0bd4b60df09991c08812a60108003fa340'],
        ['|init version', ' fec3683'], ['|Security Options', ''], ['| apparmor', ''],
        ['| seccomp', ''], ['|  Profile', ' default'], ['|Kernel Version', ' 4.15.0-36-generic'],
        ['|Operating System', ' Ubuntu 18.04.1 LTS'], ['|OSType', ' linux'],
        ['|Architecture', ' x86_64'], ['|CPUs', ' 8'], ['|Total Memory', ' 15.54GiB'],
        ['|Name', ' klappson'],
        [
            '|ID', ' VAW5', 'RDCA', 'ATG7', '24TV', 'Q7IJ', 'L33R', 'U5MX', 'XKXN', 'Z77K', 'AR22',
            'QUE6', '3JGL'
        ], ['|Docker Root Dir', ' /var/lib/docker'], ['|Debug Mode (client)', ' false'],
        ['|Debug Mode (server)', ' false'], ['|Registry', ' https', '//index.docker.io/v1/'],
        ['|Labels', ''], ['|Experimental', ' false'], ['|Insecure Registries', ''],
        ['| 127.0.0.0/8', ''], ['|Live Restore Enabled', ' false']]

discovery = {'': [(None, {}),
                  HostLabel(u'cmk/docker_object', u'node')
                 ],
            'containers': [(None, {})]}

checks = {
    '': [(None, {}, [(0, u'Daemon running on host klappson', [])])],
    'containers': [(None, {}, [(0, 'Containers: 0', [('containers', 0, None, None, None, None)]),
                               (0, 'Running: 0', [('running', 0, None, None, None, None)]),
                               (0, 'Paused: 0', [('paused', 0, None, None, None, None)]),
                               (0, 'Stopped: 0', [('stopped', 0, None, None, None, None)])])]
}
