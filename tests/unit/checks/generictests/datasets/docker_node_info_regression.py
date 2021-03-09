# yapf: disable
checkname = 'docker_node_info'

info = [
    [
        '{"ID":"VAW5:RDCA:ATG7:24TV:Q7IJ:L33R:U5MX:XKXN:Z77K:AR22:QUE6:3JGL","Containers":0,"ContainersRunning":0,"ContainersPaused":0,"ContainersStopped":0,"Images":0,"Driver":"overlay2","DriverStatus":[["Backing',
        'Filesystem","extfs"],["Supports', 'd_type","true"],["Native', 'Overlay',
        'Diff","true"]],"SystemStatus":null,"Plugins":{"Volume":["local"],"Network":["bridge","host","macvlan","null","overlay"],"Authorization":null,"Log":["awslogs","fluentd","gcplogs","gelf","journald","json-file","logentries","splunk","syslog"]},"MemoryLimit":true,"SwapLimit":false,"KernelMemory":true,"CpuCfsPeriod":true,"CpuCfsQuota":true,"CPUShares":true,"CPUSet":true,"IPv4Forwarding":true,"BridgeNfIptables":true,"BridgeNfIp6tables":true,"Debug":false,"NFd":22,"OomKillDisable":true,"NGoroutines":43,"SystemTime":"2018-10-04T08:47:40.954398342+02:00","LoggingDriver":"json-file","CgroupDriver":"cgroupfs","NEventsListener":0,"KernelVersion":"4.15.0-36-generic","OperatingSystem":"Ubuntu',
        '18.04.1',
        'LTS","OSType":"linux","Architecture":"x86_64","IndexServerAddress":"https://index.docker.io/v1/","RegistryConfig":{"AllowNondistributableArtifactsCIDRs":[],"AllowNondistributableArtifactsHostnames":[],"InsecureRegistryCIDRs":["127.0.0.0/8"],"IndexConfigs":{"docker.io":{"Name":"docker.io","Mirrors":[],"Secure":true,"Official":true}},"Mirrors":[]},"NCPU":8,"MemTotal":16690192384,"GenericResources":null,"DockerRootDir":"/var/lib/docker","HttpProxy":"","HttpsProxy":"","NoProxy":"","Name":"klappson","Labels":[],"ExperimentalBuild":false,"ServerVersion":"18.06.1-ce","ClusterStore":"","ClusterAdvertise":"","Runtimes":{"runc":{"path":"docker-runc"}},"DefaultRuntime":"runc","Swarm":{"NodeID":"","NodeAddr":"","LocalNodeState":"inactive","ControlAvailable":false,"Error":"","RemoteManagers":null},"LiveRestoreEnabled":false,"Isolation":"","InitBinary":"docker-init","ContainerdCommit":{"ID":"468a545b9edcd5932818eb9de8e72413e616e86e","Expected":"468a545b9edcd5932818eb9de8e72413e616e86e"},"RuncCommit":{"ID":"69663f0bd4b60df09991c08812a60108003fa340","Expected":"69663f0bd4b60df09991c08812a60108003fa340"},"InitCommit":{"ID":"fec3683","Expected":"fec3683"},"SecurityOptions":["name=apparmor","name=seccomp,profile=default"]}'
    ],
]

discovery = {'': [(None, {})], 'containers': [(None, {})]}

checks = {
    '': [(None, {}, [(0, u'Daemon running on host klappson', [])])],
    'containers': [(None, {}, [(0, 'Containers: 0', [('containers', 0, None, None, None, None)]),
                               (0, 'Running: 0', [('running', 0, None, None, None, None)]),
                               (0, 'Paused: 0', [('paused', 0, None, None, None, None)]),
                               (0, 'Stopped: 0', [('stopped', 0, None, None, None, None)])])]
}
