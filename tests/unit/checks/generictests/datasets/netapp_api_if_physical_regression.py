# -*- encoding: utf-8
# yapf: disable


checkname = 'netapp_api_if'


info = [[u'interface e0a',
         u'mediatype auto-1000t-fd-up',
         u'flowcontrol full',
         u'mtusize 9000',
         u'ipspace-name default-ipspace',
         u'mac-address 01:b0:89:22:df:01'],
        [u'interface e0b',
         u'mediatype auto-1000t-fd-up',
         u'flowcontrol full',
         u'mtusize 9000',
         u'ipspace-name default-ipspace',
         u'mac-address 01:b0:89:22:df:01'],
        [u'interface e0c',
         u'ipspace-name default-ipspace',
         u'flowcontrol full',
         u'mediatype auto-1000t-fd-up',
         u'mac-address 01:b0:89:22:df:02'],
        [u'interface e0d',
         u'ipspace-name default-ipspace',
         u'flowcontrol full',
         u'mediatype auto-1000t-fd-up',
         u'mac-address 01:b0:89:22:df:02'],
        [u'interface ifgrp_sto',
         u'v4-primary-address.ip-address-info.address 11.12.121.33',
         u'v4-primary-address.ip-address-info.addr-family af-inet',
         u'mtusize 9000',
         u'v4-primary-address.ip-address-info.netmask-or-prefix 255.255.255.220',
         u'v4-primary-address.ip-address-info.broadcast 12.13.142.33',
         u'ipspace-name default-ipspace',
         u'mac-address 01:b0:89:22:df:01',
         u'v4-primary-address.ip-address-info.creator vfiler:vfiler0',
         u'send_mcasts 1360660',
         u'recv_errors 0',
         u'instance_name ifgrp_sto',
         u'send_errors 0',
         u'send_data 323931282332034',
         u'recv_mcasts 1234567',
         u'v4-primary-address.ip-address-info.address 11.12.121.21',
         u'v4-primary-address.ip-address-info.addr-family af-inet',
         u'v4-primary-address.ip-address-info.netmask-or-prefix 255.255.253.0',
         u'v4-primary-address.ip-address-info.broadcast 14.11.123.255',
         u'ipspace-name default-ipspace',
         u'mac-address 01:b0:89:22:df:02',
         u'v4-primary-address.ip-address-info.creator vfiler:vfiler0',
         u'send_mcasts 166092',
         u'recv_errors 0',
         u'instance_name ifgrp_srv-600',
         u'send_errors 0',
         u'send_data 12367443455534',
         u'recv_mcasts 2308439',
         u'recv_data 412332323639']]


discovery = {'': [('5', "{'state': ['1'], 'speed': 1000000000}")]}


checks = {'': [('5',
                {'errors': (0.01, 0.1), 'speed': 1000000000, 'state': ['1']},
                [(0, u'[ifgrp_sto] (up) MAC: 01:B0:89:22:DF:02, 1 Gbit/s', []),
                 (0, u'Physical interfaces: e0d(up)', []),
                 (0, u'e0c(up)', [])])]}