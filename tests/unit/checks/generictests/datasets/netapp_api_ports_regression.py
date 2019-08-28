# -*- encoding: utf-8
# yapf: disable


checkname = 'netapp_api_ports'


info = [[u'port cl01-02.e0c-614',
         u'is-administrative-auto-negotiate true',
         u'operational-speed 10000',
         u'is-administrative-up true',
         u'vlan-port e0c',
         u'operational-flowcontrol none',
         u'vlan-id 614',
         u'port e0c-614',
         u'role data',
         u'ignore-health-status false',
         u'mac-address 00:a0:98:f2:39:8d',
         u'is-operational-auto-negotiate true',
         u'node cl01-02',
         u'ipspace Default',
         u'vlan-node cl01-02',
         u'mtu-admin 9000',
         u'operational-duplex full',
         u'administrative-speed auto',
         u'broadcast-domain vlan-614-p',
         u'administrative-duplex auto',
         u'health-status healthy',
         u'mtu 9000',
         u'link-status up',
         u'administrative-flowcontrol none',
         u'port-type vlan'],
        [u'port cl01-02.e0d',
         u'administrative-speed auto',
         u'node cl01-02',
         u'operational-speed 10000',
         u'port-type physical',
         u'remote-device-id LAB01_SAP_HANA5(FDO231719MB)',
         u'administrative-duplex auto',
         u'health-status healthy',
         u'is-administrative-auto-negotiate true',
         u'operational-flowcontrol none',
         u'ipspace Default',
         u'port e0d',
         u'is-administrative-up true',
         u'link-status up',
         u'role data',
         u'ignore-health-status false',
         u'mtu-admin 9000',
         u'administrative-flowcontrol none',
         u'mtu 9000',
         u'mac-address 00:a0:98:f2:39:8e',
         u'operational-duplex full',
         u'is-operational-auto-negotiate true']]


discovery = {'': [(u'Physical port cl01-02.e0d', {})]}


checks = {'': [(u'Physical port cl01-02.e0d',
                {},
                [(0, u'Health status: healthy, Operational speed: 10000', [])])]}


mock_host_conf_merged = {'': {'ignored_ports': ['vlan']}}