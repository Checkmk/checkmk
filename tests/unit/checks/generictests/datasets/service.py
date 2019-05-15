# -*- encoding: utf-8
# yapf: disable


checkname = u'services'


info = [[None, u'AeLookupSvc', u'stopped/demand', u'Application', u'Experience'],
        [None,
         u'RemoteAccess',
         u'stopped/disabled',
         u'Routing',
         u'and',
         u'Remote',
         u'Access'],
        [None, u'RemoteRegistry', u'stopped/auto', u'Remote', u'Registry'],
        [None,
         u'RpcLocator',
         u'stopped/demand',
         u'Remote',
         u'Procedure',
         u'Call',
         u'(RPC)',
         u'Locator'],
        [None, u'SNMPTRAP', u'stopped/demand', u'SNMP', u'Trap'],
        [None, u'Sophos_Agent', u'running/auto', u'Sophos', u'Agent'],
        [None,
         u'sophossps',
         u'running/auto',
         u'Sophos',
         u'System',
         u'Protection',
         u'Service'],
        [None, u'sppsvc', u'stopped/auto', u'Software', u'Protection'],
        [None, u'SSDPSRV', u'stopped/disabled', u'SSDP', u'Discovery'],
        [None,
         u'SstpSvc',
         u'stopped/demand',
         u'Secure',
         u'Socket',
         u'Tunneling',
         u'Protocol',
         u'Service'],
        [None, u'svsvc', u'stopped/demand', u'Spot', u'Verifier'],
        [None,
         u'swprv',
         u'stopped/demand',
         u'Microsoft',
         u'Software',
         u'Shadow',
         u'Copy',
         u'Provider'],
        [None, u'SysMain', u'stopped/demand', u'Superfetch'],
        [None,
         u'UI0Detect',
         u'stopped/demand',
         u'Interactive',
         u'Services',
         u'Detection'],
        [None, u'upnphost', u'stopped/disabled', u'UPnP', u'Device', u'Host'],
        [None, u'VaultSvc', u'stopped/demand', u'Credential', u'Manager'],
        [None, u'vds', u'stopped/demand', u'Virtual', u'Disk'],
        [None, u'swi_filter', u'running/auto', u'Sophos', u'Web', u'Filter']]


discovery = {'': [], 'summary': [(None, 'services_summary_default_levels')]}


checks = {'summary': [(None,
                       {'ignored': ('nsi'), 'state_if_stopped': 0},
                       [(0,
                         u'18 services, 5 services in autostart - of which 1 services are stopped (RemoteRegistry), 1 services stopped but ignored',
                         [])])]}
