# -*- encoding: utf-8
# yapf: disable
from cmk.base.discovered_labels import HostLabel

checkname = 'k8s_ingress_infos'

parsed = {
    u'cafe-ingress': {
        u'load_balancers': [{
            u'ip': u'10.0.2.15',
            u'hostname': u''
        }],
        u'backends': [
            [u'cafe.example.com/tea', u'tea-svc', 80],
            [u'cafe.example.com/coffee', u'coffee-svc', 80]
        ],
        u'hosts': {
            u'cafe-secret': [u'cafe.example.com']
        }
    }
}

discovery = {
    '': [
        HostLabel(u'cmk/kubernetes_object', u'ingress', plugin_name=None),
        (u'cafe.example.com/coffee', None), (u'cafe.example.com/tea', None)
    ]
}

checks = {
    '': [
        (
            u'cafe.example.com/coffee', {}, [
                (0, u'Ports: 80, 443', []), (0, u'Service: coffee-svc:80', [])
            ]
        ),
        (
            u'cafe.example.com/tea', {}, [
                (0, u'Ports: 80, 443', []), (0, u'Service: tea-svc:80', [])
            ]
        )
    ]
}
