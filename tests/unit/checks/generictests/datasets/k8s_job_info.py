# -*- encoding: utf-8
# yapf: disable


from cmk.base.discovered_labels import HostLabel


checkname = 'k8s_job_info'


parsed = {u'active': 1, u'failed': 1, u'succeeded': 1}


discovery = {
    '': [(None, {}), HostLabel(u'cmk/kubernetes_object', u'job')]
}


checks = {'': [(None, {}, [(2, 'Running: 1/3, Failed: 1, Succeeded: 1', [])])]}
