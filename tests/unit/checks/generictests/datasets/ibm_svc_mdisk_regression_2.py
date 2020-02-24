# -*- encoding: utf-8
# yapf: disable


checkname = 'ibm_svc_mdisk'


# This device does not support the lsmdisk command so
# no services should be discovered.
info = [[u'id',
         u'status',
         u'mode',
         u'capacity',
         u'encrypt',
         u'enclosure_id',
         u'over_provisioned',
         u'supports_unmap',
         u'warning'],
        [u'0', u'online', u'array', u'20.8TB', u'no', u'1', u'no', u'yes', u'80']]


discovery = {'': []}
