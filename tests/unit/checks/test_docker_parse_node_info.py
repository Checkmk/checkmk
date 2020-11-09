#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import pytest  # type: ignore[import]

from cmk.base.plugins.agent_based.utils import legacy_docker

from cmk.base.check_legacy_includes.legacy_docker import *
pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    'indata,outdata_subset',
    [
        (
            [
                ['|Containers', ' 22'],
                ['| Running', ' 0'],
                ['| Paused', ' 0'],
                ['| Stopped', ' 22'],
                ['|Images', ' 7'],
                ['|Server Version', ' 1.13.1'],
                ['|Storage Driver', ' devicemapper'],
                ['| Pool Name', ' docker-253', '6-16345697760-pool'],
                ['| Pool Blocksize', ' 65.54 kB'],
                ['| Base Device Size', ' 10.74 GB'],
                ['| Backing Filesystem', ' xfs'],
                ['| Data file', ' /dev/loop0'],
                ['| Metadata file', ' /dev/loop1'],
                ['| Data Space Used', ' 5.311 GB'],
                ['| Data Space Total', ' 107.4 GB'],
                ['| Data Space Available', ' 5.394 GB'],
                ['| Metadata Space Used', ' 7.807 MB'],
                ['| Metadata Space Total', ' 2.147 GB'],
                ['| Metadata Space Available', ' 2.14 GB'],
                ['| Thin Pool Minimum Free Space', ' 10.74 GB'],
                ['| Udev Sync Supported', ' true'],
                ['| Deferred Removal Enabled', ' true'],
                ['| Deferred Deletion Enabled', ' true'],
                ['| Deferred Deleted Device Count', ' 0'],
                ['| Data loop file', ' /var/lib/docker/devicemapper/devicemapper/data'],
                ['| WARNING', ' Do something esle!'],
                ['| Metadata loop file', ' /var/lib/docker/devicemapper/devicemapper/metadata'],
                ['| Library Version', ' 1.666.666-RHEL6 (2540-04-01)'],
                ['|Logging Driver', ' journald'],
                ['|Cgroup Driver', ' systemd'],
                ['|Plugins', ' '],
                ['| Volume', ' local'],
                ['| Network', ' bridge host macvlan null overlay'],
                ['| Authorization', ' rhel-push-plugin'],
                ['|Swarm', ' inactive'],
                ['|Runtimes', ' docker-runc runc'],
                ['|Default Runtime', ' docker-runc'],
                ['|Init Binary', ' /usr/libexec/docker/docker-init-current'],
                ['|containerd version', '  (expected', ' aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'],
                [
                    '|runc version', ' 6666666666666666666666666666666666666666 (expected',
                    ' 9999999999999999999999999999999999999999)'
                ],
                [
                    '|init version', ' 1234567890123456789012345678901234567890 (expected',
                    ' 1111111111111111111111111111111111111111)'
                ],
                ['|Security Options', ''],
                ['| seccomp'],
                ['|  WARNING', ' You\'re not using the default seccomp profile'],
                ['|  Profile', ' /etc/docker/seccomp.json'],
                ['|Kernel Version', ' 3.10.0-862.el7.x86_64'],
                ['|Operating System', ' Red Hat Enterprise Linux Server 7.5 (Maipo)'],
                ['|OSType', ' linux'],
                ['|Architecture', ' x86_64'],
                ['|Number of Docker Hooks', ' 3'],
                ['|CPUs', ' 4'],
                ['|Total Memory', ' 15.41 GiB'],
                ['|Name', ' Tiberius'],
                [
                    '|ID', ' 4WPT', '7J3Q', '5FAL', 'L53Q', 'JL4F', 'RFPA', 'NUQV', 'RKDI', 'ETKD',
                    'UXPH', 'OXRT', 'ZCGA'
                ],
                ['|Docker Root Dir', ' /var/lib/docker'],
                ['|Debug Mode (client)', ' false'],
                ['|Debug Mode (server)', ' false'],
                ['|Http Proxy', ' http', '//whoops.meta.de', '8080/'],
                ['|Https Proxy', ' http', '//wheeeeeeee.downhill.com', '8080/'],
                ['|No Proxy', ' localhost, 127.0.0.1'],
                ['|Registry', ' https', '//registry.access.redhat.com/v1/'],
                ['|Experimental', ' false'],
                ['|Insecure Registries', ''],
                ['| fofofofofofo.ddddp.de', '5000'],
                ['| fofofofofofo', '5000,'],
                ['| 127.0.0.0/8'],
                ['|Live Restore Enabled', ' false'],
                [
                    '|Registries',
                    ' registry.access.redhat.com (secure), registry.access.redhat.com (secure),'
                ],
            ],
            {
                # needed for inventory:
                "ServerVersion": "1.13.1",  # -> version
                "IndexServerAddress": "https://registry.access.redhat.com/v1/",  # -> registry
                "Swarm": {
                    "LocalNodeState": "inactive",
                },
                "Containers": 22,
                "ContainersRunning": 0,
                "ContainersStopped": 22,
                "ContainersPaused": 0,
                "Images": 7,
                "Labels": [],
                # needed for check:
                "Name": "Tiberius",
            }),
        (
            [
                ['|Containers', ' 14'],
                ['| Running', ' 3'],
                ['| Paused', ' 1'],
                ['| Stopped', ' 10'],
                ['|Images', ' 52'],
                ['|Server Version', ' 1.13.0'],
                ['|Storage Driver', ' overlay2'],
                ['| Backing Filesystem', ' extfs'],
                ['| Supports d_type', ' true'],
                ['| Native Overlay Diff', ' false'],
                ['|Logging Driver', ' json-file'],
                ['|Cgroup Driver', ' cgroupfs'],
                ['|Plugins', ''],
                ['| Volume', ' local'],
                ['| Network', ' bridge host macvlan null overlay'],
                ['|Swarm', ' active'],
                ['| NodeID', ' rdjq45w1op418waxlairloqbm'],
                ['| Is Manager', ' true'],
                ['| ClusterID', ' te8kdyw33n36fqiz74bfjeixd'],
                ['| Managers', ' 1'],
                ['| Nodes', ' 2'],
                ['| Orchestration', ''],
                ['|  Task History Retention Limit', ' 5'],
                ['| Raft', ''],
                ['|  Snapshot Interval', ' 10000'],
                ['|  Number of Old Snapshots to Retain', ' 0'],
                ['|  Heartbeat Tick', ' 1'],
                ['|  Election Tick', ' 3'],
                ['| Dispatcher', ''],
                ['|  Heartbeat Period', ' 5 seconds'],
                ['| CA Configuration', ''],
                ['|  Expiry Duration', ' 3 months'],
                ['| Root Rotation In Progress', ' false'],
                ['| Node Address', ' 172.16.66.128 172.16.66.129'],
                ['| Manager Addresses', ''],
                ['|  172.16.66.128', '2477'],
                ['|Runtimes', ' runc'],
                ['|Default Runtime', ' runc'],
                ['|Init Binary', ' docker-init'],
                ['|containerd version', ' 8517738ba4b82aff5662c97ca4627e7e4d03b531'],
                ['|runc version', ' ac031b5bf1cc92239461125f4c1ffb760522bbf2'],
                ['|init version', ' N/A (expected', ' v0.13.0)'],
                ['|Security Options', ''],
                ['| apparmor'],
                ['| seccomp'],
                ['|  Profile', ' default'],
                ['|Kernel Version', ' 4.4.0-31-generic'],
                ['|Operating System', ' Ubuntu 16.04.1 LTS'],
                ['|OSType', ' linux'],
                ['|Architecture', ' x86_64'],
                ['|CPUs', ' 2'],
                ['|Total Memory', ' 1.937 GiB'],
                ['|Name', ' ubuntu'],
                [
                    '|ID', ' H52R', '7ZR6', 'EIIA', '76JG', 'ORIY', 'BVKF', 'GSFU', 'HNPG', 'B5MK',
                    'APSC', 'SZ3Q', 'N326'
                ],
                ['|Docker Root Dir', ' /var/lib/docker'],
                ['|Debug Mode (client)', ' true'],
                ['|Debug Mode (server)', ' true'],
                ['| File Descriptors', ' 30'],
                ['| Goroutines', ' 123'],
                ['| System Time', ' 2016-11-12T17', '24', '37.955404361-08', '00'],
                ['| EventsListeners', ' 0'],
                ['|Http Proxy', ' http', '//test', 'test@proxy.example.com', '8080'],
                ['|Https Proxy', ' https', '//test', 'test@proxy.example.com', '8080'],
                ['|No Proxy', ' localhost,127.0.0.1,docker-registry.somecorporation.com'],
                ['|Registry', ' https', '//index.docker.io/v1/'],
                ['|WARNING', ' No swap limit support'],
                ['|Labels', ''],
                ['| staging=true'],
                ['| storage=ssd'],
                ['|Experimental', ' false'],
                ['|Insecure Registries', ''],
                ['| 127.0.0.0/8'],
                ['|Registry Mirrors', ''],
                ['|  http', '//192.168.1.2/'],
                ['|  http', '//registry-mirror.example.com', '5000/'],
                ['|Live Restore Enabled', ' false'],
            ],
            {
                # needed for inventory:
                "ServerVersion": "1.13.0",  # -> version
                "IndexServerAddress": "https://index.docker.io/v1/",  # -> registry
                "Swarm": {
                    "LocalNodeState": "active",
                    "RemoteManagers": "1",
                    "NodeID": "rdjq45w1op418waxlairloqbm",
                },
                "Containers": 14,
                "ContainersRunning": 3,
                "ContainersStopped": 10,
                "ContainersPaused": 1,
                "Images": 52,
                "Labels": ["staging=true", "storage=ssd"],
                # needed for check:
                "Name": "ubuntu",
            }),
        (
            [
                ['|Containers', ' 2'],
                ['| Running', ' 1'],
                ['| Paused', ' 0'],
                ['| Stopped', ' 1'],
                ['|Images', ' 107'],
                ['|Server Version', ' 18.06.1-ce'],
                ['|Storage Driver', ' overlay2'],
                ['| Backing Filesystem', ' extfs'],
                ['| Supports d_type', ' true'],
                ['| Native Overlay Diff', ' true'],
                ['|Logging Driver', ' json-file'],
                ['|Cgroup Driver', ' cgroupfs'],
                ['|Plugins', ''],
                ['| Volume', ' local'],
                ['| Network', ' bridge host macvlan null overlay'],
                [
                    '| Log',
                    ' awslogs fluentd gcplogs gelf journald json-file logentries splunk syslog'
                ],
                ['|Swarm', ' inactive'],
                ['|Runtimes', ' runc'],
                ['|Default Runtime', ' runc'],
                ['|Init Binary', ' docker-init'],
                ['|containerd version', ' 468a545b9edcd5932818eb9de8e72413e616e86e'],
                ['|runc version', ' 69663f0bd4b60df09991c08812a60108003fa340'],
                ['|init version', ' fec3683'],
                ['|Security Options', ''],
                ['| apparmor'],
                ['| seccomp'],
                ['|  Profile', ' default'],
                ['|Kernel Version', ' 4.13.0-41-generic'],
                ['|Operating System', ' Ubuntu 17.10'],
                ['|OSType', ' linux'],
                ['|Architecture', ' x86_64'],
                ['|CPUs', ' 8'],
                ['|Total Memory', ' 15.54GiB'],
                ['|Name', ' Klappspaten'],
                [
                    '|ID', ' UY52', 'B5IQ', 'QBD5', 'M36B', 'EKTQ', 'ZR6X', 'NJLK', 'QDLG', 'ZFOE',
                    'KPXB', 'YXJK', '4OAV'
                ],
                ['|Docker Root Dir', ' /var/lib/docker'],
                ['|Debug Mode (client)', ' false'],
                ['|Debug Mode (server)', ' false'],
                ['|Registry', ' https', '//index.docker.io/v1/'],
                ['|Labels', ''],
                ['|Experimental', ' false'],
                ['|Insecure Registries', ''],
                ['| 127.0.0.0/8'],
                ['|Live Restore Enabled', ' false'],
            ],
            {
                # needed for inventory:
                "ServerVersion": "18.06.1-ce",  # -> version
                "IndexServerAddress": "https://index.docker.io/v1/",  # -> registry
                "Swarm": {
                    "LocalNodeState": "inactive",
                },
                "Containers": 2,
                "ContainersRunning": 1,
                "ContainersStopped": 1,
                "ContainersPaused": 0,
                "Images": 107,
                "Labels": [],
                # needed for check:
                "Name": "Klappspaten",
            }),
        (
            [
                [u'|Client', u''],
                [u'| Debug Mode', u' false'],
                [u'|'],
                [u'|Server', u''],
                [u'| Containers', u' 5'],
                [u'| Running', u' 1'],
                [u'| Paused', u' 0'],
                [u'| Stopped', u' 4'],
                [u'| Images', u' 4'],
                [u'| Server Version', u' 19.03.1'],
                [u'| Storage Driver', u' overlay2'],
                [u'| Backing Filesystem', u' extfs'],
                [u'| Supports d_type', u' true'],
                [u'| Native Overlay Diff', u' true'],
                [u'| Logging Driver', u' json-file'],
                [u'| Cgroup Driver', u' cgroupfs'],
                [u'| Plugins', u''],
                [u'| Volume', u' local'],
                [u'| Network', u' bridge host ipvlan macvlan null overlay'],
                [
                    u'| Log',
                    u' awslogs fluentd gcplogs gelf journald json-file local logentries splunk syslog'
                ],
                [u'| Swarm', u' inactive'],
                [u'| Runtimes', u' runc'],
                [u'| Default Runtime', u' runc'],
                [u'| Init Binary', u' docker-init'],
                [u'| containerd version', u' 894b81a4b802e4eb2a91d1ce216b8817763c29fb'],
                [u'| runc version', u' 425e105d5a03fabd737a126ad93d62a9eeede87f'],
                [u'| init version', u' fec3683'],
                [u'| Security Options', u''],
                [u'| apparmor'],
                [u'| seccomp'],
                [u'| Profile', u' default'],
                [u'| Kernel Version', u' 4.15.0-58-generic'],
                [u'| Operating System', u' Ubuntu 18.04.3 LTS'],
                [u'| OSType', u' linux'],
                [u'| Architecture', u' x86_64'],
                [u'| CPUs', u' 8'],
                [u'| Total Memory', u' 15.54GiB'],
                [u'| Name', u' klappson'],
                [
                    u'| ID', u' VAW5', u'RDCA', u'ATG7', u'24TV', u'Q7IJ', u'L33R', u'U5MX',
                    u'XKXN', u'Z77K', u'AR22', u'QUE6', u'3JGL'
                ],
                [u'| Docker Root Dir', u' /var/lib/docker'],
                [u'| Debug Mode', u' false'],
                [u'| Registry', u' https', u'//index.docker.io/v1/'],
                [u'| Labels', u''],
                [u'| Experimental', u' false'],
                [u'| Insecure Registries', u''],
                [u'| 127.0.0.0/8'],
                [u'| Live Restore Enabled', u' false'],
                [u'|'],
            ],
            {
                # needed for inventory:
                "ServerVersion": "19.03.1",  # -> version
                "IndexServerAddress": "https://index.docker.io/v1/",  # -> registry
                "Swarm": {
                    "LocalNodeState": "inactive",
                },
                "Containers": 5,
                "ContainersRunning": 1,
                "ContainersStopped": 4,
                "ContainersPaused": 0,
                "Images": 4,
                "Labels": [],
                # needed for check:
                "Name": "klappson",
            }),
        (
            [
                [
                    '{"ID":"UY52:B5IQ:QBD5:M36B:EKTQ:ZR6X:NJLK:QDLG:ZFOE:KPXB:YXJK:4OAV",'
                    '"Containers":2,"ContainersRunning":1,"ContainersPaused":0,'
                    '"ContainersStopped":1,"Images":107,"Driver":"overlay2",'
                    '"DriverStatus":[["Backing', 'Filesystem","extfs"],["Supports',
                    'd_type","true"],["Native', 'Overlay', 'Diff","true"]],"SystemStatus":null,'
                    '"Plugins":{"Volume":["local"],"Network":["bridge","host","macvlan",'
                    '"null","overlay"],"Authorization":null,"Log":["awslogs","fluentd","gcplogs",'
                    '"gelf","journald","json-file","logentries","splunk","syslog"]},'
                    '"MemoryLimit":true,"SwapLimit":false,"KernelMemory":true,"CpuCfsPeriod":true,'
                    '"CpuCfsQuota":true,"CPUShares":true,"CPUSet":true,"IPv4Forwarding":true,'
                    '"BridgeNfIptables":true,"BridgeNfIp6tables":true,"Debug":false,"NFd":29,'
                    '"OomKillDisable":true,"NGoroutines":50,"SystemTime":'
                    '"2018-10-09T13:08:31.024759984+02:00","LoggingDriver":"json-file",'
                    '"CgroupDriver":"cgroupfs","NEventsListener":0,"KernelVersion":'
                    '"4.13.0-41-generic","OperatingSystem":"Ubuntu', '17.10","OSType":"linux",'
                    '"Architecture":"x86_64","IndexServerAddress":"https://index.docker.io/v1/",'
                    '"RegistryConfig":{"AllowNondistributableArtifactsCIDRs":[],'
                    '"AllowNondistributableArtifactsHostnames":[],"InsecureRegistryCIDRs":'
                    '["127.0.0.0/8"],"IndexConfigs":{"docker.io":{"Name":"docker.io","Mirrors":[],'
                    '"Secure":true,"Official":true}},"Mirrors":[]},"NCPU":8,"MemTotal":16690483200,'
                    '"GenericResources":null,"DockerRootDir":"/var/lib/docker","HttpProxy":"",'
                    '"HttpsProxy":"","NoProxy":"","Name":"Klappspaten","Labels":[],'
                    '"ExperimentalBuild":false,"ServerVersion":"18.06.1-ce","ClusterStore":""'
                    ',"ClusterAdvertise":"","Runtimes":{"runc":{"path":"docker-runc"}},'
                    '"DefaultRuntime":"runc","Swarm":{"NodeID":"","NodeAddr":"",'
                    '"LocalNodeState":"inactive","ControlAvailable":false,"Error":"",'
                    '"RemoteManagers":null},"LiveRestoreEnabled":false,"Isolation":"",'
                    '"InitBinary":"docker-init","ContainerdCommit":{"ID":"468a545b9edcd5932818e'
                    'b9de8e72413e616e86e","Expected":"468a545b9edcd5932818eb9de8e72413e616e86e"},'
                    '"RuncCommit":{"ID":"69663f0bd4b60df09991c08812a60108003fa340",'
                    '"Expected":"69663f0bd4b60df09991c08812a60108003fa340"},"InitCommit":'
                    '{"ID":"fec3683","Expected":"fec3683"},'
                    '"SecurityOptions":["name=apparmor","name=seccomp,profile=default"]}'
                ],
            ],
            {
                # needed for inventory:
                "ServerVersion": "18.06.1-ce",  # -> version
                "IndexServerAddress": "https://index.docker.io/v1/",  # -> registry
                "Swarm": {
                    u"LocalNodeState": u"inactive",
                },
                "Containers": 2,
                "ContainersRunning": 1,
                "ContainersStopped": 1,
                "ContainersPaused": 0,
                "Images": 107,
                "Labels": [],
                # needed for check:
                "Name": "Klappspaten",
            }),
        ([[
            u'Got', u'permission', u'denied', u'while', u'trying', u'to', u'connect', u'to', u'the',
            u'Docker', u'daemon', u'socket', u'at', u'unix:///var/run/docker.sock:', u'Get',
            u'http://%2Fvar%2Frun%2Fdocker.sock/v1.26/info:', u'dial', u'unix',
            u'/var/run/docker.sock:', u'connect:', u'permission', u'denied'
        ]], {}),
        ([], {}),
    ])
def test_parse_legacy_docker_node_info(indata, outdata_subset):
    def assert_contains(dic, key, value):
        assert key in dic, "missing key: %r" % key
        if isinstance(value, dict):
            for r_key, r_value in value.items():
                assert_contains(dic[key], r_key, r_value)
        else:
            assert dic[key] == value, "expected: %r, got %r" % (
                value,
                parsed[key]  # type: ignore[name-defined,misc]
            )

    parsed = legacy_docker.parse_node_info(indata)
    for k, v in outdata_subset.items():
        assert_contains(parsed, k, v)
