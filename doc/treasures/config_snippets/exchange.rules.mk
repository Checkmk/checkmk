# Written by WATO
# encoding: utf-8


inventory_services_rules = [
  ( {'services': ['MSExchangeIS', 'MSExchangeMTA', 'MSExchangeSA', 'MSExchangeMGMT', 'MSSEARCH', 'RESvc', 'SMTPSVC']}, ['/' + FOLDER_PATH + '/+'], ALL_HOSTS ),
] + inventory_services_rules


host_groups = [
  ( 'exchange', ['/' + FOLDER_PATH + '/+'], ALL_HOSTS ),
] + host_groups


static_checks.setdefault('services', [])

static_checks['services'] = [
  ( ('services', 'MSExchangeADTopology', {'states': [('running', 'auto', 0)], 'else': 2}), ['/' + FOLDER_PATH + '/+'], ALL_HOSTS, {'comment': u'Exchange Active Directory Topology'} ),
  ( ('services', 'MSExchangeAB', {'states': [('running', 'auto', 0)], 'else': 2}), ['/' + FOLDER_PATH + '/+'], ALL_HOSTS, {'comment': u'Exchange Active Addressbook'} ),
  ( ('services', 'MSExchangeAntispamUpdate', {'states': [('running', 'auto', 0)], 'else': 2}), ['/' + FOLDER_PATH + '/+'], ALL_HOSTS, {'comment': u'Microsoft Exchange Anti-spam Update'} ),
  ( ('services', 'MSExchangeEdgeSync', {'states': [('running', 'auto', 0)], 'else': 2}), ['/' + FOLDER_PATH + '/+'], ALL_HOSTS, {'comment': u'Exchange EdgeSync'} ),
  ( ('services', 'MSExchangeFDS', {'states': [('running', 'auto', 0)], 'else': 2}), ['/' + FOLDER_PATH + '/+'], ALL_HOSTS, {'comment': u'Exchange File Distribution'} ),
  ( ('services', 'MSExchangeFBA', {'states': [('running', 'auto', 0)], 'else': 2}), ['/' + FOLDER_PATH + '/+'], ALL_HOSTS, {'comment': u'Exchange Forms-Based Authentication service'} ),
  ( ('services', 'MSExchangeIS', {'states': [('running', 'auto', 0)], 'else': 2}), ['/' + FOLDER_PATH + '/+'], ALL_HOSTS, {'comment': u'Exchange Information Store'} ),
  ( ('services', 'MSExchangeMailSubmission', {'states': [('running', 'auto', 0)], 'else': 2}), ['/' + FOLDER_PATH + '/+'], ALL_HOSTS, {'comment': u'Exchange Mail Submission'} ),
  ( ('services', 'MSExchangeMailboxAssistants', {'states': [('running', 'auto', 0)], 'else': 2}), ['/' + FOLDER_PATH + '/+'], ALL_HOSTS, {'comment': u'Exchange Mailbox Assistants'} ),
  ( ('services', 'MSExchangeMailboxReplication', {'states': [('running', 'auto', 0)], 'else': 2}), ['/' + FOLDER_PATH + '/+'], ALL_HOSTS, {'comment': u'Exchange Mailbox Replication'} ),
  ( ('services', 'MSExchangeProtectedServiceHost', {'states': [('running', 'auto', 0)], 'else': 2}), ['/' + FOLDER_PATH + '/+'], ALL_HOSTS, {'comment': u'Exchange Protected Service Host'} ),
  ( ('services', 'MSExchangeRepl', {'states': [('running', 'auto', 0)], 'else': 2}), ['/' + FOLDER_PATH + '/+'], ALL_HOSTS, {'comment': u'Exchange Replication'} ),
  ( ('services', 'MSExchangeRPC', {'states': [('running', 'auto', 0)], 'else': 2}), ['/' + FOLDER_PATH + '/+'], ALL_HOSTS, {'comment': u'Exchange RPC Client Access'} ),
  ( ('services', 'MSExchangeSearch', {'states': [('running', 'auto', 0)], 'else': 2}), ['/' + FOLDER_PATH + '/+'], ALL_HOSTS, {'comment': u'Exchange Search Indexer'} ),
  ( ('services', 'MSExchangeServiceHost', {'states': [('running', 'auto', 0)], 'else': 2}), ['/' + FOLDER_PATH + '/+'], ALL_HOSTS, {'comment': u'Exchange Service Host'} ),
  ( ('services', 'MSExchangeSA', {'states': [('running', 'auto', 0)], 'else': 2}), ['/' + FOLDER_PATH + '/+'], ALL_HOSTS, {'comment': u'Exchange System Attendant'} ),
  ( ('services', 'MSExchangeThrottling', {'states': [('running', 'auto', 0)], 'else': 2}), ['/' + FOLDER_PATH + '/+'], ALL_HOSTS, {'comment': u'Exchange Throttling'} ),
  ( ('services', 'MSExchangeTransport', {'states': [('running', 'auto', 0)], 'else': 2}), ['/' + FOLDER_PATH + '/+'], ALL_HOSTS, {'comment': u'Exchange Transport'} ),
  ( ('services', 'MSExchangeTransportLogSearch', {'states': [('running', 'auto', 0)], 'else': 2}), ['/' + FOLDER_PATH + '/+'], ALL_HOSTS, {'comment': u'Exchange Transport Log Search'} ),
  ( ('services', 'NetTcpActivator', {'states': [('running', 'auto', 0)], 'else': 2}), ['/' + FOLDER_PATH + '/+'], ALL_HOSTS, {'comment': u'Net.Tcp Listener Adapter'} ),
  ( ('services', 'NetTcpPortSharing', {'states': [('running', 'auto', 0)], 'else': 2}), ['/' + FOLDER_PATH + '/+'], ALL_HOSTS, {'comment': u'Net.Tcp Port Sharing Service'} ),
  ( ('services', 'NetPipeActivator', {'states': [('running', 'auto', 0)], 'else': 2}), ['/' + FOLDER_PATH + '/+'], ALL_HOSTS, {'comment': u'Net.Pipe Listener Adapter'} ),
  ( ('services', 'msftesql-Exchange', {'states': [(None, 'demand', 0)], 'else': 2}), ['/' + FOLDER_PATH + '/+'], ALL_HOSTS, {'comment': u'Microsoft Search  (Exchange)'} ),
] + static_checks['services']


static_checks.setdefault('wmic_process', [])

static_checks['wmic_process'] = [
  ( ('wmic_process', 'Exchange Active Directory Topology', ('MSExchangeADTopologyService.exe', 0, 0, 50, 90, 80.0, 90.0)), ['/' + FOLDER_PATH + '/+'], ALL_HOSTS ),
  ( ('wmic_process', 'Exchange Address Book', ('Microsoft.Exchange.AddressBook.Service.exe', 0, 0, 50, 90, 80.0, 90.0)), ['/' + FOLDER_PATH + '/+'], ALL_HOSTS ),
  ( ('wmic_process', 'Exchange Anti-spam Update', ('Microsoft.Exchange.AntispamUpdateSvc.exe', 0, 0, 50, 90, 80.0, 90.0)), ['/' + FOLDER_PATH + '/+'], ALL_HOSTS ),
  ( ('wmic_process', 'Exchange EdgeSync', ('Microsoft.Exchange.EdgeSyncSvc.exe', 0, 0, 50, 90, 80.0, 90.0)), ['/' + FOLDER_PATH + '/+'], ALL_HOSTS ),
  ( ('wmic_process', 'Exchange File Distribution', ('MsExchangeFDS.exe', 0, 0, 50, 90, 80.0, 90.0)), ['/' + FOLDER_PATH + '/+'], ALL_HOSTS ),
  ( ('wmic_process', 'Exchange Mailbox Assistants', ('MSExchangeMailboxAssistants.exe', 0, 0, 50, 90, 80.0, 90.0)), ['/' + FOLDER_PATH + '/+'], ALL_HOSTS ),
  ( ('wmic_process', 'Exchange Mailbox Replication', ('MSExchangeMailboxReplication.exe', 0, 0, 50, 90, 80.0, 90.0)), ['/' + FOLDER_PATH + '/+'], ALL_HOSTS ),
  ( ('wmic_process', 'Exchange Mail Submission', ('MSExchangeMailSubmission.exe', 0, 0, 50, 90, 80.0, 90.0)), ['/' + FOLDER_PATH + '/+'], ALL_HOSTS ),
  ( ('wmic_process', 'Exchange Protected Service Host', ('Microsoft.Exchange.ProtectedServiceHost.exe', 0, 0, 50, 90, 80.0, 90.0)), ['/' + FOLDER_PATH + '/+'], ALL_HOSTS ),
  ( ('wmic_process', 'Exchange Replication', ('msexchangerepl.exe', 0, 0, 50, 90, 80.0, 90.0)), ['/' + FOLDER_PATH + '/+'], ALL_HOSTS ),
  ( ('wmic_process', 'Exchange RPC Client Access', ('Microsoft.Exchange.RpcClientAccess.Service.exe', 0, 0, 50, 90, 80.0, 90.0)), ['/' + FOLDER_PATH + '/+'], ALL_HOSTS ),
  ( ('wmic_process', 'Exchange Search', ('Microsoft.Exchange.Search.ExSearch.exe', 0, 0, 50, 90, 80.0, 90.0)), ['/' + FOLDER_PATH + '/+'], ALL_HOSTS ),
  ( ('wmic_process', 'Exchange Service Host', ('Microsoft.Exchange.ServiceHost.exe', 0, 0, 50, 90, 80.0, 90.0)), ['/' + FOLDER_PATH + '/+'], ALL_HOSTS ),
  ( ('wmic_process', 'Exchange Throttling', ('MSExchangeThrottling.exe', 0, 0, 50, 90, 80.0, 90.0)), ['/' + FOLDER_PATH + '/+'], ALL_HOSTS ),
  ( ('wmic_process', 'Exchange Transport', ('MSExchangeTransport.exe', 0, 0, 50, 90, 80.0, 90.0)), ['/' + FOLDER_PATH + '/+'], ALL_HOSTS ),
  ( ('wmic_process', 'Exchange Transport Log Search', ('MSExchangeTransportLogSearch.exe', 0, 0, 50, 90, 80.0, 90.0)), ['/' + FOLDER_PATH + '/+'], ALL_HOSTS ),
] + static_checks['wmic_process']

