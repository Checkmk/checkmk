# yapf: disable
checkname = 'docker_node_info'

info = [
    [u'|Containers', u' 42'],
    [u'|Images', u' 23'],
    [u'|Storage Driver', u' devicemapper'],
    [u'| Pool Name', u' docker-9', u'232-23232323-pool'],
    [u'| Pool Blocksize', u' 23.23 kB'],
    [u'| Backing Filesystem', u' extfs'],
    [u'| Data file', u' /dev/loop23'],
    [u'| Metadata file', u' /dev/loop24'],
    [u'| Data Space Used', u' 42.42 GB'],
    [u'| Data Space Total', u' 142.42 GB'],
    [u'| Data Space Available', u' 42.42 GB'],
    [u'| Metadata Space Used', u' 42.42 MB'],
    [u'| Metadata Space Total', u' 23.23 GB'],
    [u'| Metadata Space Available', u' 3.141 GB'],
    [u'| Udev Sync Supported', u' true'],
    [u'| Deferred Removal Enabled', u' false'],
    [u'| Data loop file', u' /data/docker/devicemapper/devicemapper/data'],
    [u'| Metadata loop file', u' /data/docker/devicemapper/devicemapper/metadata'],
    [u'| Library Version', u' 1.02.117-Koechelverzeichnis/ (2024-12-12)'],
    [u'|Execution Driver', u' killmenow-0.23'],
    [u'|Logging Driver', u' json-file'],
    [u'|Kernel Version', u' 3.14.15-926.5.3.el5.x86_64'],
    [u'|Operating System', u' <unknown>'],
    [u'|CPUs', u' 1024'],
    [u'|Total Memory', u' -23 GiB'],
    [u'|Name', u' voms01'],
    [
        u'|ID', u' XXXX', u'XXXX', u'XXXX', u'XXXX', u'XXXX', u'XXXX', u'BLOB', u'BOBO', u'0COV',
        u'FEFE', u'WHOO', u'0TEH'
    ],
]

discovery = {'': [(None, {})], 'containers': [(None, {})]}

checks = {
    '': [(None, {}, [(0, u'Daemon running on host voms01', [])])],
    'containers': [(None, {}, [(0, 'Containers: 42', [('containers', 42, None, None, None, None)]),
                               (3, 'Running: count not present in agent output', []),
                               (3, 'Paused: count not present in agent output', []),
                               (3, 'Stopped: count not present in agent output', [])])]
}
