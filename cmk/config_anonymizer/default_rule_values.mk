# Written by Checkmk store


active_checks.setdefault('by_ssh', [])

active_checks['by_ssh'] = [
{'id': '0827c95b-1fe3-4934-8b8a-6bc730e2fc65', 'value': {'options': ('example', {})}, 'condition': {}, 'options': {'disabled': False}},
] + active_checks['by_ssh']


active_checks.setdefault('cert', [])

active_checks['cert'] = [
{'id': '7c1e566f-81d6-4bf1-8752-15fa4110a5f3', 'value': {'connections': [{'service_name': {'prefix': 'auto', 'name': 'example'}, 'address': '127.0.0.1'}], 'standard_settings': {'port': 443}}, 'condition': {}, 'options': {'disabled': False}},
] + active_checks['cert']


active_checks.setdefault('cmk_inv', [])

active_checks['cmk_inv'] = [
{'id': '7ba2ac2a-5a49-47ce-bc3c-1630fb191c7f', 'value': {'status_data_inventory': True}, 'condition': {'host_label_groups': [('and', [('and', 'cmk/docker_object:node')])]}, 'options': {'description': 'Factory default. Required for the shipped dashboards.'}},
] + active_checks['cmk_inv']


active_checks.setdefault('disk_smb', [])

active_checks['disk_smb'] = [
{'id': '50de4259-dbfd-4232-a037-9c057bab3e3b', 'value': {'share': 'example', 'host': ('define_host', 'example'), 'levels': ('fixed', (85.0, 95.0))}, 'condition': {}, 'options': {'disabled': False}},
] + active_checks['disk_smb']


active_checks.setdefault('dns', [])

active_checks['dns'] = [
{'id': '82a3ea2b-9eed-4386-854f-023c3fed6c7d', 'value': {'hostname': 'example', 'server': None}, 'condition': {}, 'options': {'disabled': False}},
] + active_checks['dns']


active_checks.setdefault('elasticsearch_query', [])

active_checks['elasticsearch_query'] = [
{'id': 'b53b67d4-6c0d-4a02-8c6c-acf559b449f7', 'value': {'svc_item': 'example', 'verify_tls_cert': True, 'pattern': '', 'timerange': 60.0}, 'condition': {}, 'options': {'disabled': False}},
] + active_checks['elasticsearch_query']


active_checks.setdefault('form_submit', [])

active_checks['form_submit'] = [
{'id': 'a1d8baa2-aa89-4297-a76d-405911a7dbd6', 'value': {'name': 'example', 'url_details': {}}, 'condition': {}, 'options': {'disabled': False}},
] + active_checks['form_submit']


active_checks.setdefault('ftp', [])

active_checks['ftp'] = [
{'id': '15fe2e4e-574c-4e75-bd62-91cbb9f78ffe', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + active_checks['ftp']


active_checks.setdefault('http', [])

active_checks['http'] = [
{'id': '3d6b43c1-3dd7-4bb1-b797-cd6d1e5df38c', 'value': {'name': 'Demo HTTP Check', 'host': {'address': ('direct', '$HOSTNAME$')}, 'mode': ('url', {})}, 'condition': {}, 'options': {'disabled': False, 'description': 'Demo HTTP check rule'}},
] + active_checks['http']


active_checks.setdefault('httpv2', [])

active_checks['httpv2'] = [
{'id': '5ad540d5-bcfb-4557-b5b6-493261ff9bdd', 'value': {'endpoints': [{'service_name': {'prefix': 'auto', 'name': 'example'}, 'url': 'https://example.domain'}], 'standard_settings': {}}, 'condition': {}, 'options': {'disabled': False}},
] + active_checks['httpv2']


active_checks.setdefault('icmp', [])

active_checks['icmp'] = [
{'id': '4f2081a1-2dae-4c4a-ba51-17e7acf0e435', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + active_checks['icmp']


active_checks.setdefault('ldap', [])

active_checks['ldap'] = [
{'id': '64c68079-bea6-45bc-8fdf-a7d7984790e9', 'value': {'name': 'Demo LDAP', 'base_dn': 'dc=example,dc=com', 'hostname': 'ldap.example.com'}, 'condition': {}, 'options': {'disabled': False, 'description': 'Demo ldap rule'}},
] + active_checks['ldap']


active_checks.setdefault('mail', [])

active_checks['mail'] = [
{'id': '3aefefda-88ef-4f08-8513-3f27eb36d72d', 'value': {'service_description': 'Email', 'fetch': ('POP3', {'connection': {}, 'auth': ('basic', {'username': 'example', 'password': ('cmk_postprocessed', 'explicit_password', ('uuid69ad1446-d722-49a2-bdfa-44ecd2626f13', 'example'))})})}, 'condition': {}, 'options': {'disabled': False}},
] + active_checks['mail']


active_checks.setdefault('mail_loop', [])

active_checks['mail_loop'] = [
{'id': '95cde924-10c6-4524-a14b-3d639e5b49bb', 'value': {'item': 'example', 'send': ('EWS', {'connection': {}, 'auth': ('basic', {'username': 'example', 'password': ('cmk_postprocessed', 'explicit_password', ('uuidcc0a46e9-b94e-4286-aeb0-07e624ca0b71', 'example'))})}), 'fetch': ('IMAP', {'connection': {}, 'auth': ('basic', {'username': 'example', 'password': ('cmk_postprocessed', 'explicit_password', ('uuid15c71c45-5e2b-4da3-8637-08ca42a59d67', 'example'))})}), 'delete_messages': False}, 'condition': {}, 'options': {'disabled': False}},
] + active_checks['mail_loop']


active_checks.setdefault('mailboxes', [])

active_checks['mailboxes'] = [
{'id': 'a613ce51-4297-47b2-86b2-6317e5747727', 'value': {'service_description': 'Mailboxes', 'fetch': ('EWS', {'connection': {}, 'auth': ('basic', {'username': 'example', 'password': ('cmk_postprocessed', 'explicit_password', ('uuid28d702b7-7cd3-4859-9157-791c7c3a7afc', 'example'))})})}, 'condition': {}, 'options': {'disabled': False}},
] + active_checks['mailboxes']


active_checks.setdefault('notify_count', [])

active_checks['notify_count'] = [
{'id': '6bb66fb3-84d0-40a4-b492-8016948f8ac5', 'value': {'description': 'example', 'interval': 60}, 'condition': {}, 'options': {'disabled': False}},
] + active_checks['notify_count']


active_checks.setdefault('sftp', [])

active_checks['sftp'] = [
{'id': '5e7a9497-bff3-4a68-8334-b8fd6a7d9227', 'value': {'host': 'example.host', 'user': 'example.user', 'secret': ('cmk_postprocessed', 'explicit_password', ('uuidd990aaf5-1618-4008-af35-7240822ba9ac', 'example'))}, 'condition': {}, 'options': {'disabled': False}},
] + active_checks['sftp']


active_checks.setdefault('smtp', [])

active_checks['smtp'] = [
{'id': 'b9d9da91-e931-455e-b421-8ce4ebf4518a', 'value': {'name': 'example'}, 'condition': {}, 'options': {'disabled': False}},
] + active_checks['smtp']


active_checks.setdefault('sql', [])

active_checks['sql'] = [
{'id': '7142e053-7fe8-4e8f-8b5b-33561c91c83b', 'value': {'description': 'example', 'dbms': 'postgres', 'name': 'example', 'user': 'example', 'password': ('cmk_postprocessed', 'explicit_password', ('uuid6f65e4ec-cd2f-42c1-83b8-0615447b69d9', 'example')), 'sql': 'GET'}, 'condition': {}, 'options': {'disabled': False}},
] + active_checks['sql']


active_checks.setdefault('ssh', [])

active_checks['ssh'] = [
{'id': '581e15a1-4ace-4246-9fcd-55e6a3ed03a1', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + active_checks['ssh']


active_checks.setdefault('tcp', [])

active_checks['tcp'] = [
{'id': '072d8ac0-d09f-413c-8d27-c8f2353dd755', 'value': {'port': 7777}, 'condition': {}, 'options': {'disabled': False}},
] + active_checks['tcp']


active_checks.setdefault('traceroute', [])

active_checks['traceroute'] = [
{'id': '131acd4a-4e28-4c7e-99a9-a2bf45e48fec', 'value': {'dns': False, 'address_family': None, 'routers': [], 'method': None}, 'condition': {}, 'options': {'disabled': False}},
] + active_checks['traceroute']


active_checks.setdefault('uniserv', [])

active_checks['uniserv'] = [
{'id': '87064e76-274d-43eb-956d-aedabd67b5ef', 'value': {'port': 0, 'service': 'example', 'check_version': False, 'check_address': ('no', None)}, 'condition': {}, 'options': {'disabled': False}},
] + active_checks['uniserv']


agent_config.setdefault('ad_replication', [])

agent_config['ad_replication'] = [
{'id': '00c04793-c13b-49c3-8e8c-03851719f226', 'value': True, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['ad_replication']


agent_config.setdefault('agent_controller', [])

agent_config['agent_controller'] = [
{'id': 'b2036835-cd06-4fee-88c9-0ebad8ad2561', 'value': {'agent_ctl_enabled': (True, {})}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['agent_controller']


agent_config.setdefault('agent_paths', [])

agent_config['agent_paths'] = [
{'id': '6e2d2426-785e-4b93-b424-1fb90e153725', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['agent_paths']


agent_config.setdefault('agent_user', [])

agent_config['agent_user'] = [
{'id': '56f8f8cd-c87a-46da-8198-500fec7ff796', 'value': 'root', 'condition': {}, 'options': {'disabled': False}},
] + agent_config['agent_user']


agent_config.setdefault('apache_status', [])

agent_config['apache_status'] = [
{'id': '72101ecf-b5ed-4e55-a2a3-d56bbbf1caf2', 'value': ('autodetect', [443]), 'condition': {}, 'options': {'disabled': False}},
] + agent_config['apache_status']


agent_config.setdefault('arcserve_backup', [])

agent_config['arcserve_backup'] = [
{'id': 'd17f50b6-034b-495c-aca4-12c4289c5024', 'value': {'sqlserver': 'SATURN\\ARCSERVE_DB'}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['arcserve_backup']


agent_config.setdefault('bakery_packages', [])

agent_config['bakery_packages'] = [
{'id': 'b82b47c6-2c8e-45b8-a23c-4b9a82ded1dc', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['bakery_packages']


agent_config.setdefault('ceph', [])

agent_config['ceph'] = [
{'id': 'fd710e9a-1568-408a-9716-9c12d2be521a', 'value': {'deploy': True, 'interval': ('uncached', None)}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['ceph']


agent_config.setdefault('citrix_licenses', [])

agent_config['citrix_licenses'] = [
{'id': 'c6bad90e-3403-4aec-8d35-c1d5e80a2368', 'value': {'deployment': ('sync', None)}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['citrix_licenses']


agent_config.setdefault('citrix_xenapp', [])

agent_config['citrix_xenapp'] = [
{'id': '607b1762-8b2c-42fd-852e-ea508313e586', 'value': {'deployment': ('sync', None)}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['citrix_xenapp']


agent_config.setdefault('cmk_update_agent', [])

agent_config['cmk_update_agent'] = [
{'id': '897abbab-e700-4c75-ada9-bdf2d9c604cc', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['cmk_update_agent']


agent_config.setdefault('custom_files', [])

agent_config['custom_files'] = [
{'id': 'c28c304d-2d30-41d3-8a49-3e00d515c184', 'value': [], 'condition': {}, 'options': {'disabled': False}},
] + agent_config['custom_files']


agent_config.setdefault('customize_agent_package', [])

agent_config['customize_agent_package'] = [
{'id': '5c5221e2-ec58-4375-9051-cfc6cedac642', 'value': {'directory': {'installation_directory': '/opt/checkmk/agent'}, 'agent_controller_arch': 'x86'}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['customize_agent_package']


agent_config.setdefault('db2_mem', [])

agent_config['db2_mem'] = [
{'id': 'b869604b-47eb-46c3-b9d0-0ce0e139ba3b', 'value': True, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['db2_mem']


agent_config.setdefault('dnsclient', [])

agent_config['dnsclient'] = [
{'id': '26f32894-ae37-4844-af61-0fa83f2b6a23', 'value': ['checkmk.com'], 'condition': {}, 'options': {'disabled': False}},
] + agent_config['dnsclient']


agent_config.setdefault('exclude_sections_aix', [])

agent_config['exclude_sections_aix'] = [
{'id': '434adbe8-7dc7-4695-87b6-b4981e90c341', 'value': {'sections_aix': []}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['exclude_sections_aix']


agent_config.setdefault('fileinfo', [])

agent_config['fileinfo'] = [
{'id': 'c232971e-7646-4fe1-8f83-8163b4e8f19e', 'value': [], 'condition': {}, 'options': {'disabled': False}},
] + agent_config['fileinfo']


agent_config.setdefault('firewall', [])

agent_config['firewall'] = [
{'id': '4fc0a9b7-26da-4cd5-9d95-79565ceb986d', 'value': {'mode': 'configure', 'port': 'auto'}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['firewall']


agent_config.setdefault('hyperv_collection', [])

agent_config['hyperv_collection'] = [
{'id': '4eb1a14b-543a-4f35-8a41-739663f0cb9f', 'value': {'deploy': ('deploy', ['hyperv_host'])}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['hyperv_collection']


agent_config.setdefault('hyperv_vms', [])

agent_config['hyperv_vms'] = [
{'id': '6dd9ec57-0fd8-430b-9187-93bfc4f5b244', 'value': True, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['hyperv_vms']


agent_config.setdefault('ibm_mq', [])

agent_config['ibm_mq'] = [
{'id': '98706833-7a35-4e58-9a5f-e887d678daf3', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['ibm_mq']


agent_config.setdefault('iis_app_pool_state', [])

agent_config['iis_app_pool_state'] = [
{'id': 'dd94d482-9be7-496f-bba9-41179317aaf2', 'value': True, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['iis_app_pool_state']


agent_config.setdefault('install_python', [])

agent_config['install_python'] = [
{'id': 'fcee40cd-6fc2-4869-8bc7-45a5d690af56', 'value': {'installation': 'auto', 'usage': 'auto'}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['install_python']


agent_config.setdefault('isc_dhcpd', [])

agent_config['isc_dhcpd'] = [
{'id': 'c2e412ce-cf2b-4521-a373-1a9d8db0397a', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['isc_dhcpd']


agent_config.setdefault('jar_signature', [])

agent_config['jar_signature'] = [
{'id': 'eb410e96-7084-431b-8762-a8ec06ef4533', 'value': ('/home/oracle/bin/jdk_latest_version', ['/home/oracle/fmw/11gR2/as_1/forms/java/*.jar']), 'condition': {}, 'options': {'disabled': False}},
] + agent_config['jar_signature']


agent_config.setdefault('kaspersky_av', [])

agent_config['kaspersky_av'] = [
{'id': '68afd885-e28c-4ec3-be61-1ffffe1b4bd4', 'value': True, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['kaspersky_av']


agent_config.setdefault('linux_robotmk', [])

agent_config['linux_robotmk'] = [
{'id': '71cf4c43-7f11-4ad0-9180-37efe0dea282', 'value': {'deployment': ('no_deploy', None)}, 'condition': {}, 'options': {'disabled': False, 'description': 'Example rule'}},
] + agent_config['linux_robotmk']


agent_config.setdefault('lnx_quota', [])

agent_config['lnx_quota'] = [
{'id': 'afd1cb9c-6469-42c9-87ad-6aa55b7f0aaa', 'value': True, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['lnx_quota']


agent_config.setdefault('logging', [])

agent_config['logging'] = [
{'id': '548975bf-1197-4852-9b5b-1d3b9efef827', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['logging']


agent_config.setdefault('lvm', [])

agent_config['lvm'] = [
{'id': '79514202-0c0e-4803-a3a5-aff2935757e4', 'value': True, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['lvm']


agent_config.setdefault('mailman_lists', [])

agent_config['mailman_lists'] = [
{'id': '1221273c-9fe0-435c-91c9-3982e57ed2d2', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['mailman_lists']


agent_config.setdefault('mcafee_av_client', [])

agent_config['mcafee_av_client'] = [
{'id': '22288bd7-caa2-4cb0-8cdc-5461afd314c2', 'value': True, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['mcafee_av_client']


agent_config.setdefault('mk_apt', [])

agent_config['mk_apt'] = [
{'id': 'b14949b1-d845-49d7-9e87-7d75d1596855', 'value': {'interval': 86400, 'method': 'upgrade', 'update': True}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['mk_apt']


agent_config.setdefault('mk_cups_queues', [])

agent_config['mk_cups_queues'] = [
{'id': '35f39f22-1219-4082-8231-c9027227cd1f', 'value': {'interval': 60}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['mk_cups_queues']


agent_config.setdefault('mk_db2', [])

agent_config['mk_db2'] = [
{'id': '8496c591-0262-4a9d-a207-cd69cc650c07', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['mk_db2']


agent_config.setdefault('mk_docker', [])

agent_config['mk_docker'] = [
{'id': '593ba77e-3a81-4a15-994f-05426e3a4e45', 'value': {'node': [], 'containers': [], 'container_id': 'short'}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['mk_docker']


agent_config.setdefault('mk_filehandler', [])

agent_config['mk_filehandler'] = [
{'id': '73b54d9d-dabc-4152-9238-8ed3160557b2', 'value': True, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['mk_filehandler']


agent_config.setdefault('mk_filestats', [])

agent_config['mk_filestats'] = [
{'id': '89dd4e77-8a03-48f9-8fca-6ce5124858ee', 'value': {'sections': [{'name': 'example_section', 'input_patterns': '/tmp/*.log'}]}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['mk_filestats']


agent_config.setdefault('mk_inotify', [])

agent_config['mk_inotify'] = [
{'id': '17ffd5a3-449a-4e92-839c-12e1016be6a5', 'value': None, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['mk_inotify']


agent_config.setdefault('mk_inventory', [])

agent_config['mk_inventory'] = [
{'id': '2859b446-eb7a-46b1-b5ef-738b0b86c75f', 'value': {'interval': 14400, 'reg_paths': ['Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall', 'Software\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall']}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['mk_inventory']


agent_config.setdefault('mk_iptables', [])

agent_config['mk_iptables'] = [
{'id': '5fd5ecfd-0f12-49b8-82d1-0876bae2397b', 'value': True, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['mk_iptables']


agent_config.setdefault('mk_jolokia', [])

agent_config['mk_jolokia'] = [
{'id': 'f75499fe-2ef3-4d30-a6ec-db4cca00ca71', 'value': {'deployment': 'sync'}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['mk_jolokia']


agent_config.setdefault('mk_logins', [])

agent_config['mk_logins'] = [
{'id': '7c248677-fb41-45a8-b1ad-c15fc98121c1', 'value': True, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['mk_logins']


agent_config.setdefault('mk_logwatch', [])

agent_config['mk_logwatch'] = [
{'id': '208e14ae-82de-4bc7-baab-8680dc1682e2', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['mk_logwatch']


agent_config.setdefault('mk_mongodb', [])

agent_config['mk_mongodb'] = [
{'id': '84a130f8-807a-4cb4-bbf4-bbcf04cb7239', 'value': True, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['mk_mongodb']


agent_config.setdefault('mk_ms_sql', [])

agent_config['mk_ms_sql'] = [
{'id': 'd84533fd-d7ac-4dba-8ff6-74aa2508f584', 'value': {'main': {'auth': 'local'}}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['mk_ms_sql']


agent_config.setdefault('mk_msoffice', [])

agent_config['mk_msoffice'] = [
{'id': '9f2c53de-b9fd-4bc4-aeea-7f39a8cea4de', 'value': {'client_id': '00000000-0000-0000-0000-000000000001', 'tenant_id': '00000000-0000-0000-0000-000000000001', 'client_secret': ('password', 'example_secret_value_for_demo')}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['mk_msoffice']


agent_config.setdefault('mk_mysql', [])

agent_config['mk_mysql'] = [
{'id': 'e82fd570-f001-4f9a-87c0-1cfea1ac6e02', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['mk_mysql']


agent_config.setdefault('mk_nfsiostat', [])

agent_config['mk_nfsiostat'] = [
{'id': 'c4cc2c94-68f5-42cd-b71a-f56163f75892', 'value': True, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['mk_nfsiostat']


agent_config.setdefault('mk_oracle', [])

agent_config['mk_oracle'] = [
{'id': 'c36f0943-2cce-42b8-82f7-71163288c1b1', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['mk_oracle']


agent_config.setdefault('mk_oracle_unified', [])

agent_config['mk_oracle_unified'] = [
{'id': '74dbeb3f-011d-435f-9275-0fcf5781232a', 'value': {'deploy': ('deploy', None), 'main': {'auth': {'auth_type': ('wallet', None)}, 'connection': {}}, 'instances': []}, 'condition': {}, 'options': {'disabled': False, 'description': 'Example rule'}},
] + agent_config['mk_oracle_unified']


agent_config.setdefault('mk_podman', [])

agent_config['mk_podman'] = [
{'id': 'b0e3ed85-f8aa-4029-accf-76db0a7b0f69', 'value': {'deploy': False, 'connection_method': ('api', ('auto', None)), 'piggyback_name_method': 'nodename_name'}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['mk_podman']


agent_config.setdefault('mk_postgres', [])

agent_config['mk_postgres'] = [
{'id': '54c37e01-f03f-4a05-b401-8b1a3b6dbee3', 'value': {'deployment': ('sync', None)}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['mk_postgres']


agent_config.setdefault('mk_redis', [])

agent_config['mk_redis'] = [
{'id': '0f339552-8dd4-429d-b981-2a01c1ec1c03', 'value': 'autodetect', 'condition': {}, 'options': {'disabled': False}},
] + agent_config['mk_redis']


agent_config.setdefault('mk_sap', [])

agent_config['mk_sap'] = [
{'id': '4b414be3-a897-416c-b58c-0e02ae1cbf6f', 'value': {'instances': [{'ashost': 'localhost', 'sysnr': '00', 'client': '100', 'user': 'cmk-user', 'passwd': ('password', 'thiswontworkanyway'), 'trace': '3', 'lang': 'EN'}], 'paths': ['SAP BI Monitors/BI Monitor', 'SAP BI Monitors/BI Monitor/*/Oracle/Performance', 'SAP CCMS Monitor Templates/Operating System/OperatingSystem/CPU/*', 'SAP CCMS Monitor Templates/Operating System/OperatingSystem/CPU/CPU_Utilization']}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['mk_sap']


agent_config.setdefault('mk_sap_hana', [])

agent_config['mk_sap_hana'] = [
{'id': '6c5f5be1-afa0-4543-8c74-734da02b32e6', 'value': {'credentials': ('SYSTEM', ('password', 'example_password'))}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['mk_sap_hana']


agent_config.setdefault('mk_saprouter', [])

agent_config['mk_saprouter'] = [
{'id': '7370c586-f64e-4660-a3f5-7b21b3c2aea0', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['mk_saprouter']


agent_config.setdefault('mk_scaleio', [])

agent_config['mk_scaleio'] = [
{'id': '215f961b-3160-4a84-8a81-7d7c5f566e78', 'value': {'user': '', 'password': ('password', ''), 'interval': 60}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['mk_scaleio']


agent_config.setdefault('mk_site_object_counts', [])

agent_config['mk_site_object_counts'] = [
{'id': '0190f9b7-d98b-4ce9-9ae9-e1ef18d8f64d', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['mk_site_object_counts']


agent_config.setdefault('mk_sshd_config', [])

agent_config['mk_sshd_config'] = [
{'id': 'f9b4c7a4-10d2-4568-a45d-b3f4ba1250c7', 'value': True, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['mk_sshd_config']


agent_config.setdefault('mk_suseconnect', [])

agent_config['mk_suseconnect'] = [
{'id': '63fcb662-0b30-4a64-a18a-fcda86d0cc19', 'value': True, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['mk_suseconnect']


agent_config.setdefault('mk_tsm', [])

agent_config['mk_tsm'] = [
{'id': 'c26a732e-f0c7-4189-8525-8fee136349d3', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['mk_tsm']


agent_config.setdefault('mk_zypper', [])

agent_config['mk_zypper'] = [
{'id': 'd6a60045-7344-405e-ae65-71fe31ce80b8', 'value': 14400, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['mk_zypper']


agent_config.setdefault('mrpe', [])

agent_config['mrpe'] = [
{'id': '0b9dc919-f1a8-4340-95a1-244dafb6f36a', 'value': [], 'condition': {}, 'options': {'disabled': False}},
] + agent_config['mrpe']


agent_config.setdefault('msexch_dag', [])

agent_config['msexch_dag'] = [
{'id': '6313b715-d7fd-480a-a41f-602b191dad83', 'value': True, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['msexch_dag']


agent_config.setdefault('msexch_database', [])

agent_config['msexch_database'] = [
{'id': 'c3fd015b-d9e9-4342-b0e9-4704961b2fd9', 'value': True, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['msexch_database']


agent_config.setdefault('mtr', [])

agent_config['mtr'] = [
{'id': '0ebc319a-677b-4cf5-a5ac-c2393a36bca5', 'value': {'deployment': ('do_not_deploy', None), 'mtr_config': []}, 'condition': {}, 'options': {'disabled': False, 'description': 'Example rule'}},
] + agent_config['mtr']


agent_config.setdefault('netstat', [])

agent_config['netstat'] = [
{'id': '25622e1c-8ed2-4dbd-b20d-50104306b7fb', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['netstat']


agent_config.setdefault('nfsexports', [])

agent_config['nfsexports'] = [
{'id': 'd0c3908c-c79c-4ffa-9619-5d15260e3755', 'value': True, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['nfsexports']


agent_config.setdefault('nginx_status', [])

agent_config['nginx_status'] = [
{'id': '743b8168-3e32-42f8-a82c-60b5e09d34e9', 'value': ('autodetect', [443]), 'condition': {}, 'options': {'disabled': False}},
] + agent_config['nginx_status']


agent_config.setdefault('nvidia_smi', [])

agent_config['nvidia_smi'] = [
{'id': '57ce7640-2426-49a3-a686-6da659c1e6e0', 'value': {'nvidia_smi_path': 'C:\\Program Files\\NVIDIA Corporation\\NVSMI\\nvidia-smi.exe'}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['nvidia_smi']


agent_config.setdefault('only_from', [])

agent_config['only_from'] = [
{'id': '38c51063-4b75-4e5f-a127-dd8ed3a7bc9e', 'value': [], 'condition': {}, 'options': {'disabled': False}},
] + agent_config['only_from']


agent_config.setdefault('package_name', [])

agent_config['package_name'] = [
{'id': '1f77993a-9629-43f6-b892-1e3ab5249876', 'value': 'check-mk-agent', 'condition': {}, 'options': {'disabled': False}},
] + agent_config['package_name']


agent_config.setdefault('plesk', [])

agent_config['plesk'] = [
{'id': '0c6957c6-7cef-4188-95c7-1990f29848df', 'value': {'deployment': ('sync', None)}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['plesk']


agent_config.setdefault('python_plugins', [])

agent_config['python_plugins'] = [
{'id': 'daadce35-e1a4-486e-ae3d-83793cf7266b', 'value': {'version': 'auto'}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['python_plugins']


agent_config.setdefault('rds_licenses', [])

agent_config['rds_licenses'] = [
{'id': '315a2ec9-309f-4823-adad-26ab0917a0c4', 'value': {'deployment': ('sync', None)}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['rds_licenses']


agent_config.setdefault('real_time_checks', [])

agent_config['real_time_checks'] = [
{'id': '600f5cb4-6751-4e22-b3f4-e695f34f28e7', 'value': {'encryption': ('enabled', ('password', 'yMeCbPqxfJmlygfXZxUpSvC')), 'sections': [], 'real_time_plugins': [], 'port': ('auto', None), 'timeout': 90}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['real_time_checks']


agent_config.setdefault('remove_legacy', [])

agent_config['remove_legacy'] = [
{'id': '74dfe805-162a-4a60-aecd-b8de7a437651', 'value': False, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['remove_legacy']


agent_config.setdefault('rpm_tags', [])

agent_config['rpm_tags'] = [
{'id': '88c43ea7-cd8a-402c-a309-348fc5daf427', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['rpm_tags']


agent_config.setdefault('runas', [])

agent_config['runas'] = [
{'id': '2c15fe3f-4e5c-46ad-ad8d-9f9a44075b0a', 'value': [], 'condition': {}, 'options': {'disabled': False}},
] + agent_config['runas']


agent_config.setdefault('smart', [])

agent_config['smart'] = [
{'id': '204a08f0-6bc8-4bfb-a07f-8583f1cd05dc', 'value': 'smart_posix', 'condition': {}, 'options': {'disabled': False}},
] + agent_config['smart']


agent_config.setdefault('storcli', [])

agent_config['storcli'] = [
{'id': 'e7b0da8e-78a7-4bf9-bf1c-b2f1a08c06c3', 'value': None, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['storcli']


agent_config.setdefault('super_server', [])

agent_config['super_server'] = [
{'id': '230cdf0b-6f57-4535-80b7-728d87b4a54a', 'value': 'auto', 'condition': {}, 'options': {'disabled': False}},
] + agent_config['super_server']


agent_config.setdefault('super_server_solaris', [])

agent_config['super_server_solaris'] = [
{'id': 'c8f57430-0124-4dc4-8c1c-3529e459920c', 'value': 'inetd', 'condition': {}, 'options': {'disabled': False}},
] + agent_config['super_server_solaris']


agent_config.setdefault('symantec_av', [])

agent_config['symantec_av'] = [
{'id': 'a1915524-f230-41c2-9069-f438f52eacb4', 'value': True, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['symantec_av']


agent_config.setdefault('unitrends', [])

agent_config['unitrends'] = [
{'id': 'a68cb32e-5612-44d5-8719-416643bf97aa', 'value': True, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['unitrends']


agent_config.setdefault('unix_plugins_cache_age', [])

agent_config['unix_plugins_cache_age'] = [
{'id': '6eb83522-cf8e-4a8c-b45f-2c220b7637ff', 'value': {'override': False, 'pattern': '*', 'interval': 0}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['unix_plugins_cache_age']


agent_config.setdefault('veeam_backup_status', [])

agent_config['veeam_backup_status'] = [
{'id': '7b8cca9e-36ed-45fe-8356-cb1708b2951a', 'value': True, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['veeam_backup_status']


agent_config.setdefault('vxvm', [])

agent_config['vxvm'] = [
{'id': '269e98a3-d0aa-4679-88a7-60f8a98f5af3', 'value': True, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['vxvm']


agent_config.setdefault('win_agent_disabled_sections', [])

agent_config['win_agent_disabled_sections'] = [
{'id': '91ca1245-3a49-4d38-955b-79d0ddc1fa7b', 'value': [], 'condition': {}, 'options': {'disabled': False}},
] + agent_config['win_agent_disabled_sections']


agent_config.setdefault('win_agent_sections', [])

agent_config['win_agent_sections'] = [
{'id': 'df88124d-af99-4768-a582-d540757ec8c3', 'value': ['check_mk', 'uptime', 'systemtime', 'w32time_status', 'w32time_peers', 'df', 'mem', 'ps', 'services', 'winperf', 'logwatch', 'logfiles', 'fileinfo', 'plugins', 'local', 'mrpe', 'spool', 'wmi_cpuload', 'msexch', 'wmi_webservices', 'dotnet_clrmemory', 'openhardwaremonitor', 'skype'], 'condition': {}, 'options': {'disabled': False}},
] + agent_config['win_agent_sections']


agent_config.setdefault('win_clean_uninstall', [])

agent_config['win_clean_uninstall'] = [
{'id': 'ad7a9542-d876-4af3-8103-255346e6a7c3', 'value': 'none', 'condition': {}, 'options': {'disabled': False}},
] + agent_config['win_clean_uninstall']


agent_config.setdefault('win_controller', [])

agent_config['win_controller'] = [
{'id': 'ed6f5d72-7d8f-4785-893f-d8512fc53d8e', 'value': {'check_controller_access': True, 'force_legacy': False}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['win_controller']


agent_config.setdefault('win_dhcp_pools', [])

agent_config['win_dhcp_pools'] = [
{'id': '61d13fc2-eb38-4475-b802-c98a6e2c4cb8', 'value': True, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['win_dhcp_pools']


agent_config.setdefault('win_dmidecode', [])

agent_config['win_dmidecode'] = [
{'id': 'c8bc686b-cea6-4736-b058-cfe4a255e88b', 'value': True, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['win_dmidecode']


agent_config.setdefault('win_eventlog', [])

agent_config['win_eventlog'] = [
{'id': '8e05d650-58d1-4d96-a112-a74d69b5c58d', 'value': {'logfiles': [], 'sendall': False, 'skip_duplicated': False}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['win_eventlog']


agent_config.setdefault('win_exe_suffixes', [])

agent_config['win_exe_suffixes'] = [
{'id': '9515215d-efd4-41ce-b38d-6742d14824a8', 'value': None, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['win_exe_suffixes']


agent_config.setdefault('win_license', [])

agent_config['win_license'] = [
{'id': '498be1c5-f630-4ee0-ab54-43b525a081d1', 'value': True, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['win_license']


agent_config.setdefault('win_megaraid', [])

agent_config['win_megaraid'] = [
{'id': '361d6700-f55a-43cc-a219-3b5fcaf3343f', 'value': {'megacli': 'C:\\Program Files\\LSI Corporation\\MegaCLI\\MegaCli.exe', 'tempdir': 'C:\\Temp'}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['win_megaraid']


agent_config.setdefault('win_printers', [])

agent_config['win_printers'] = [
{'id': '312a444f-2f98-45c3-9abd-6b4ff3c25bc5', 'value': True, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['win_printers']


agent_config.setdefault('win_ps', [])

agent_config['win_ps'] = [
{'id': 'ee35076e-61ba-4126-8f66-988b3492cbdd', 'value': {'use_wmi': True, 'full_path': False}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['win_ps']


agent_config.setdefault('win_robotmk', [])

agent_config['win_robotmk'] = [
{'id': '8971ff84-afa8-4df7-bbd5-efececce3ded', 'value': {'deployment': ('no_deploy', None)}, 'condition': {}, 'options': {'disabled': False, 'description': 'Example rule'}},
] + agent_config['win_robotmk']


agent_config.setdefault('win_script_cache_age', [])

agent_config['win_script_cache_age'] = [
{'id': '8fc023c2-85c4-4a61-8f8a-e754b6250e93', 'value': {'type': 'plugin', 'pattern': '*', 'cache_age': 0}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['win_script_cache_age']


agent_config.setdefault('win_script_execution', [])

agent_config['win_script_execution'] = [
{'id': '033543ef-5153-4ed1-b22b-fc60c1036fe1', 'value': {'type': 'plugin', 'pattern': '*', 'execution': 'sync'}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['win_script_execution']


agent_config.setdefault('win_script_retry_count', [])

agent_config['win_script_retry_count'] = [
{'id': '6b1be405-d89b-4a7b-8aa6-d71238df8c59', 'value': {'type': 'plugin', 'pattern': '*', 'retry_count': 0}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['win_script_retry_count']


agent_config.setdefault('win_script_runas', [])

agent_config['win_script_runas'] = [
{'id': '381dc3f2-26b0-4c3b-902e-e856cff2465e', 'value': {'type': 'plugin', 'pattern': '*', 'group': 'Users'}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['win_script_runas']


agent_config.setdefault('win_script_timeout', [])

agent_config['win_script_timeout'] = [
{'id': '4afced2b-8a3d-4ed5-885b-7ba1e588283d', 'value': {'type': 'plugin', 'pattern': '*', 'timeout': 60}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['win_script_timeout']


agent_config.setdefault('win_service', [])

agent_config['win_service'] = [
{'id': '62b326d8-4997-4d1d-a457-bca03b0be1fa', 'value': {'restart_on_crash': 'yes', 'error_mode': 'log', 'start_mode': 'auto'}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['win_service']


agent_config.setdefault('win_set_wmi_timeout', [])

agent_config['win_set_wmi_timeout'] = [
{'id': '954d1fc9-d818-4cf0-8950-5ff9c60b204d', 'value': 3, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['win_set_wmi_timeout']


agent_config.setdefault('windows_broadcom_bonding', [])

agent_config['windows_broadcom_bonding'] = [
{'id': 'dff0e2a0-d887-4cce-8aaf-762ddb77d31c', 'value': True, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['windows_broadcom_bonding']


agent_config.setdefault('windows_multipath', [])

agent_config['windows_multipath'] = [
{'id': '7780a797-ff4b-4283-9f65-549ed90c51e3', 'value': True, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['windows_multipath']


agent_config.setdefault('windows_tasks', [])

agent_config['windows_tasks'] = [
{'id': 'b6ac39e3-4dd4-419c-9338-4f656d613953', 'value': True, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['windows_tasks']


agent_config.setdefault('windows_updates', [])

agent_config['windows_updates'] = [
{'id': '8d884509-c3c9-4af4-8b1d-7ff9e7f722ef', 'value': True, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['windows_updates']


agent_config.setdefault('winperf', [])

agent_config['winperf'] = [
{'id': '72aac8ba-3f4d-48d9-a5c0-0ce1c5857c60', 'value': [], 'condition': {}, 'options': {'disabled': False}},
] + agent_config['winperf']


agent_config.setdefault('winperf_if', [])

agent_config['winperf_if'] = [
{'id': '3e5a3f79-a8a5-47fe-b050-7d9b602462f7', 'value': 'ps1', 'condition': {}, 'options': {'disabled': False}},
] + agent_config['winperf_if']


agent_config.setdefault('zorp', [])

agent_config['zorp'] = [
{'id': 'ce6b1204-52ab-4814-af0a-865792b40f19', 'value': {'deployment': ('sync', None)}, 'condition': {}, 'options': {'disabled': False}},
] + agent_config['zorp']


globals().setdefault('agent_encryption', [])

agent_encryption = [
{'id': 'aed26744-00ac-40d0-a890-99615f77009e', 'value': None, 'condition': {}, 'options': {'disabled': False}},
] + agent_encryption


globals().setdefault('agent_exclude_sections', [])

agent_exclude_sections = [
{'id': 'f49dc496-6172-4718-bf79-bd38bbfc04b3', 'value': {'sections': []}, 'condition': {}, 'options': {'disabled': False}},
] + agent_exclude_sections


globals().setdefault('agent_ports', [])

agent_ports = [
{'id': 'eb77c2e5-b767-474e-832b-08717e3eecb7', 'value': 6556, 'condition': {}, 'options': {'disabled': False, 'description': 'Example rule'}},
] + agent_ports


globals().setdefault('brocade_fcport_inventory', [])

brocade_fcport_inventory = [
{'id': 'ac707fe6-b15a-4758-ab71-63f4d118c6c1', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + brocade_fcport_inventory


globals().setdefault('bulkwalk_hosts', [])

bulkwalk_hosts = [
{'id': 'b92a5406-1d57-4f1d-953d-225b111239e5', 'value': True, 'condition': {'host_tags': {'snmp': 'snmp', 'snmp_ds': {'$ne': 'snmp-v1'}}}, 'options': {'description': 'Hosts with the tag "snmp-v1" must not use bulkwalk'}},
] + bulkwalk_hosts


globals().setdefault('check_mk_exit_status', [])

check_mk_exit_status = [
{'id': '5f526c6b-dda2-4e6f-8a70-de8cdd2619c8', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + check_mk_exit_status


globals().setdefault('check_periods', [])

check_periods = [
{'id': '12d1b1e8-ceb8-43e8-acad-743d20d5e81f', 'value': '24X7', 'condition': {}, 'options': {'disabled': False}},
] + check_periods


checkgroup_parameters.setdefault('acme_certificates', [])

checkgroup_parameters['acme_certificates'] = [
{'id': '9b111b70-cb4e-424e-a6b1-ca8b6631a374', 'value': {'expire_lower': ('fixed', (604800.0, 2592000.0))}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['acme_certificates']


checkgroup_parameters.setdefault('acme_sbc_snmp', [])

checkgroup_parameters['acme_sbc_snmp'] = [
{'id': 'e6633739-9256-49cf-b2c8-73dbba90ed59', 'value': {'lower_levels': ('fixed', (99, 75))}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['acme_sbc_snmp']


checkgroup_parameters.setdefault('ad_replication', [])

checkgroup_parameters['ad_replication'] = [
{'id': 'fbf0a3d4-382b-4b25-911d-18e4d60b361a', 'value': {'failure_levels': (0, 0)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['ad_replication']


checkgroup_parameters.setdefault('adva_ifs', [])

checkgroup_parameters['adva_ifs'] = [
{'id': 'dd518faf-6a8a-487d-8f04-cd901cec0934', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['adva_ifs']


checkgroup_parameters.setdefault('agent_update', [])

checkgroup_parameters['agent_update'] = [
{'id': '7581769e-9984-4726-8399-b1b3c61799ae', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['agent_update']


checkgroup_parameters.setdefault('airflow', [])

checkgroup_parameters['airflow'] = [
{'id': '99c4c8b9-8cca-4e76-9f2e-0f18bd2b80b9', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['airflow']


checkgroup_parameters.setdefault('airflow_deviation', [])

checkgroup_parameters['airflow_deviation'] = [
{'id': 'd8816e84-2e9c-4224-84d0-0b501aae7150', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['airflow_deviation']


checkgroup_parameters.setdefault('alertmanager_rule_state', [])

checkgroup_parameters['alertmanager_rule_state'] = [
{'id': '9b475f80-7c02-44c2-b9f7-c9e7f35b83ca', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['alertmanager_rule_state']


checkgroup_parameters.setdefault('alertmanager_rule_state_summary', [])

checkgroup_parameters['alertmanager_rule_state_summary'] = [
{'id': 'c45094df-2911-44e8-a84e-568941ec568a', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['alertmanager_rule_state_summary']


checkgroup_parameters.setdefault('antivir_update_age', [])

checkgroup_parameters['antivir_update_age'] = [
{'id': '96170133-0a2e-40e1-bd3e-7cbbba0c2844', 'value': {'levels': None}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['antivir_update_age']


checkgroup_parameters.setdefault('apache_status', [])

checkgroup_parameters['apache_status'] = [
{'id': '0fe9e677-618b-4417-8b36-9171eac60fee', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['apache_status']


checkgroup_parameters.setdefault('apc_ats_output', [])

checkgroup_parameters['apc_ats_output'] = [
{'id': '6dd2fb17-43b7-4962-9985-140c63fd1353', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['apc_ats_output']


checkgroup_parameters.setdefault('apc_symmetra', [])

checkgroup_parameters['apc_symmetra'] = [
{'id': 'b107b605-cefe-48ff-826a-c3907b3a0904', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['apc_symmetra']


checkgroup_parameters.setdefault('apc_system_events', [])

checkgroup_parameters['apc_system_events'] = [
{'id': '60b2afa6-9932-49dd-a745-cf562230c637', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['apc_system_events']


checkgroup_parameters.setdefault('apt', [])

checkgroup_parameters['apt'] = [
{'id': '46aeb028-929c-4bea-b44e-3f66b3b41397', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['apt']


checkgroup_parameters.setdefault('asm_diskgroup', [])

checkgroup_parameters['asm_diskgroup'] = [
{'id': '0b076c34-ac4e-4716-afa0-8c8a9e1c7919', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['asm_diskgroup']


checkgroup_parameters.setdefault('audiocodes_calls', [])

checkgroup_parameters['audiocodes_calls'] = [
{'id': '0c6facca-1c2f-48f3-818f-0be2a1667870', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['audiocodes_calls']


checkgroup_parameters.setdefault('audiocodes_system_events', [])

checkgroup_parameters['audiocodes_system_events'] = [
{'id': '3e692247-2591-4079-ac05-012fa4d0a245', 'value': {'severity_state_mapping': {'cleared': 0, 'indeterminate': 3, 'warning': 1, 'minor': 1, 'major': 2, 'critical': 2}}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['audiocodes_system_events']


checkgroup_parameters.setdefault('aws_cloudwatch_alarms_limits', [])

checkgroup_parameters['aws_cloudwatch_alarms_limits'] = [
{'id': '2cb9145b-2705-4523-9a3d-b143da6d4d6e', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['aws_cloudwatch_alarms_limits']


checkgroup_parameters.setdefault('aws_costs_and_usage', [])

checkgroup_parameters['aws_costs_and_usage'] = [
{'id': 'f7e76abe-682c-4e4f-bfcb-e88601f889cd', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['aws_costs_and_usage']


checkgroup_parameters.setdefault('aws_dynamodb_capacity', [])

checkgroup_parameters['aws_dynamodb_capacity'] = [
{'id': '58038971-0a1a-42da-9f96-6df52638b54d', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['aws_dynamodb_capacity']


checkgroup_parameters.setdefault('aws_dynamodb_latency', [])

checkgroup_parameters['aws_dynamodb_latency'] = [
{'id': '30e3093d-8fca-4a7c-a7eb-52a60f56bc66', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['aws_dynamodb_latency']


checkgroup_parameters.setdefault('aws_dynamodb_limits', [])

checkgroup_parameters['aws_dynamodb_limits'] = [
{'id': '103fa79b-1fbb-4e42-b4fb-7fd9257de6e3', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['aws_dynamodb_limits']


checkgroup_parameters.setdefault('aws_ebs_burst_balance', [])

checkgroup_parameters['aws_ebs_burst_balance'] = [
{'id': '4c68497c-12f8-4c91-8b34-c8eb8c3b783e', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['aws_ebs_burst_balance']


checkgroup_parameters.setdefault('aws_ebs_limits', [])

checkgroup_parameters['aws_ebs_limits'] = [
{'id': '08d977ee-90ce-4607-9fa9-4a64c96d5acc', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['aws_ebs_limits']


checkgroup_parameters.setdefault('aws_ec2_cpu_credits', [])

checkgroup_parameters['aws_ec2_cpu_credits'] = [
{'id': 'f161cce0-984f-40ed-b761-c0b2a6731576', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['aws_ec2_cpu_credits']


checkgroup_parameters.setdefault('aws_ec2_limits', [])

checkgroup_parameters['aws_ec2_limits'] = [
{'id': '18edc437-d5d0-43c4-8036-fa8b84a3c5a2', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['aws_ec2_limits']


checkgroup_parameters.setdefault('aws_elb_backend_connection_errors', [])

checkgroup_parameters['aws_elb_backend_connection_errors'] = [
{'id': '7b5c9a51-126c-43b0-915b-e12a35c6ec56', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['aws_elb_backend_connection_errors']


checkgroup_parameters.setdefault('aws_elb_healthy_hosts', [])

checkgroup_parameters['aws_elb_healthy_hosts'] = [
{'id': 'b5370bc1-4d17-412d-bd85-672283c0236a', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['aws_elb_healthy_hosts']


checkgroup_parameters.setdefault('aws_elb_http', [])

checkgroup_parameters['aws_elb_http'] = [
{'id': '22f9e3fe-89d2-4bc8-8fed-873af34dbb8b', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['aws_elb_http']


checkgroup_parameters.setdefault('aws_elb_latency', [])

checkgroup_parameters['aws_elb_latency'] = [
{'id': '226d03f4-39f9-4355-a2ee-1c73de74b9e2', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['aws_elb_latency']


checkgroup_parameters.setdefault('aws_elb_limits', [])

checkgroup_parameters['aws_elb_limits'] = [
{'id': '9b0f9ad9-1b93-4d1f-b9e3-962820d3ed48', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['aws_elb_limits']


checkgroup_parameters.setdefault('aws_elb_statistics', [])

checkgroup_parameters['aws_elb_statistics'] = [
{'id': 'e9d7f099-d268-42de-9f05-5ead14b2429e', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['aws_elb_statistics']


checkgroup_parameters.setdefault('aws_elbv2_lcu', [])

checkgroup_parameters['aws_elbv2_lcu'] = [
{'id': '2ca35c2a-be3f-4dce-9020-60bf873ac7a2', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['aws_elbv2_lcu']


checkgroup_parameters.setdefault('aws_elbv2_limits', [])

checkgroup_parameters['aws_elbv2_limits'] = [
{'id': 'e4c78847-e80b-42f2-8a2f-a69ada4811b2', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['aws_elbv2_limits']


checkgroup_parameters.setdefault('aws_elbv2_target_errors', [])

checkgroup_parameters['aws_elbv2_target_errors'] = [
{'id': 'c93f8eb9-a30d-4814-ad67-921253218d2b', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['aws_elbv2_target_errors']


checkgroup_parameters.setdefault('aws_glacier_limits', [])

checkgroup_parameters['aws_glacier_limits'] = [
{'id': '8efda28d-532c-425e-b73e-8e91c0010cef', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['aws_glacier_limits']


checkgroup_parameters.setdefault('aws_glacier_vault_archives', [])

checkgroup_parameters['aws_glacier_vault_archives'] = [
{'id': '8c5be107-ec02-4d4b-80ab-d557b6237e62', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['aws_glacier_vault_archives']


checkgroup_parameters.setdefault('aws_glacier_vaults', [])

checkgroup_parameters['aws_glacier_vaults'] = [
{'id': '029c70fe-1e4d-4c58-a095-c674dece2819', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['aws_glacier_vaults']


checkgroup_parameters.setdefault('aws_rds_connections', [])

checkgroup_parameters['aws_rds_connections'] = [
{'id': '6652fa8f-de8a-4755-9847-607077343b6c', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['aws_rds_connections']


checkgroup_parameters.setdefault('aws_rds_cpu_credits', [])

checkgroup_parameters['aws_rds_cpu_credits'] = [
{'id': '8ce3f727-0e99-4112-86e0-a2eff4f7aa28', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['aws_rds_cpu_credits']


checkgroup_parameters.setdefault('aws_rds_disk_usage', [])

checkgroup_parameters['aws_rds_disk_usage'] = [
{'id': '55a852e9-3063-44db-9c2d-0019d2fe323d', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['aws_rds_disk_usage']


checkgroup_parameters.setdefault('aws_rds_limits', [])

checkgroup_parameters['aws_rds_limits'] = [
{'id': 'e0dd50c2-d857-4319-8b2c-0dc96425efb8', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['aws_rds_limits']


checkgroup_parameters.setdefault('aws_rds_replica_lag', [])

checkgroup_parameters['aws_rds_replica_lag'] = [
{'id': '7c547bf2-a7fe-413b-b547-7b2e3455d333', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['aws_rds_replica_lag']


checkgroup_parameters.setdefault('aws_reservation_utilization', [])

checkgroup_parameters['aws_reservation_utilization'] = [
{'id': '73f5602a-4609-410e-9111-da519e684e32', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['aws_reservation_utilization']


checkgroup_parameters.setdefault('aws_s3_buckets', [])

checkgroup_parameters['aws_s3_buckets'] = [
{'id': 'ce98872f-f537-47c5-ad96-c2454f567486', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['aws_s3_buckets']


checkgroup_parameters.setdefault('aws_s3_buckets_objects', [])

checkgroup_parameters['aws_s3_buckets_objects'] = [
{'id': 'd0ee8a1b-8b4e-45b2-b9d9-6035cb4ea7e6', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['aws_s3_buckets_objects']


checkgroup_parameters.setdefault('aws_s3_http_errors', [])

checkgroup_parameters['aws_s3_http_errors'] = [
{'id': '6da3597d-ad2b-47e8-b906-b3eb1d32cdc5', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['aws_s3_http_errors']


checkgroup_parameters.setdefault('aws_s3_latency', [])

checkgroup_parameters['aws_s3_latency'] = [
{'id': '12cbfbcf-8350-438e-876f-5f16607d4bea', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['aws_s3_latency']


checkgroup_parameters.setdefault('aws_s3_limits', [])

checkgroup_parameters['aws_s3_limits'] = [
{'id': '590f86bd-b279-4ac3-9daf-5dc61826e7c9', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['aws_s3_limits']


checkgroup_parameters.setdefault('aws_s3_requests', [])

checkgroup_parameters['aws_s3_requests'] = [
{'id': '22373bf6-4635-43d8-a69a-4e06058a50b4', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['aws_s3_requests']


checkgroup_parameters.setdefault('aws_wafv2_limits', [])

checkgroup_parameters['aws_wafv2_limits'] = [
{'id': '573a8f68-0a02-4384-96d4-79e164ff2bbc', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['aws_wafv2_limits']


checkgroup_parameters.setdefault('aws_wafv2_web_acl', [])

checkgroup_parameters['aws_wafv2_web_acl'] = [
{'id': '4a75445c-c669-4ef3-8f4c-e955188d8c96', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['aws_wafv2_web_acl']


checkgroup_parameters.setdefault('azure_ad', [])

checkgroup_parameters['azure_ad'] = [
{'id': '9195090b-5c23-4922-b59d-1ef1ce4be0f1', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_ad']


checkgroup_parameters.setdefault('azure_agent_info', [])

checkgroup_parameters['azure_agent_info'] = [
{'id': 'b802793f-e19d-464a-a40b-b818805a9ad3', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_agent_info']


checkgroup_parameters.setdefault('azure_databases_cpu', [])

checkgroup_parameters['azure_databases_cpu'] = [
{'id': '6856fbcf-e780-494b-89c3-5d6d28990082', 'value': {'cpu_percent': ('fixed', (85.0, 95.0))}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_databases_cpu']


checkgroup_parameters.setdefault('azure_databases_deadlock', [])

checkgroup_parameters['azure_databases_deadlock'] = [
{'id': 'a5cadd2a-0f7d-4023-9bba-efeb8f0b0310', 'value': {'deadlocks': ('fixed', (10.0, 100.0))}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_databases_deadlock']


checkgroup_parameters.setdefault('azure_databases_dtu', [])

checkgroup_parameters['azure_databases_dtu'] = [
{'id': '4cb8eebd-80be-4214-a7e2-d45e436c6aa1', 'value': {'dtu_percent': ('fixed', (40.0, 50.0))}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_databases_dtu']


checkgroup_parameters.setdefault('azure_databases_storage', [])

checkgroup_parameters['azure_databases_storage'] = [
{'id': '354cd811-ccdc-40ed-9b8e-81be53fe7d25', 'value': {'storage_percent': ('fixed', (85.0, 95.0))}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_databases_storage']


checkgroup_parameters.setdefault('azure_db_storage', [])

checkgroup_parameters['azure_db_storage'] = [
{'id': '5cb37d4a-1fc5-4f22-b777-f27edddfa8c9', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_db_storage']


checkgroup_parameters.setdefault('azure_load_balancer_health', [])

checkgroup_parameters['azure_load_balancer_health'] = [
{'id': '2c6496ff-d2c7-4265-a811-d2b32a17b274', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_load_balancer_health']


checkgroup_parameters.setdefault('azure_storageaccounts', [])

checkgroup_parameters['azure_storageaccounts'] = [
{'id': 'ee844290-0237-4d99-8a61-bf1b054d4848', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_storageaccounts']


checkgroup_parameters.setdefault('azure_storageaccounts_flow', [])

checkgroup_parameters['azure_storageaccounts_flow'] = [
{'id': '1f87df34-f070-4afa-b9cd-79300805efcf', 'value': {'transactions_levels': ('no_levels', None), 'ingress_levels': ('no_levels', None), 'egress_levels': ('no_levels', None)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_storageaccounts_flow']


checkgroup_parameters.setdefault('azure_storageaccounts_performance', [])

checkgroup_parameters['azure_storageaccounts_performance'] = [
{'id': '6dd74da3-a30b-48ea-8b86-45bce7a501b2', 'value': {'server_latency_levels': ('no_levels', None), 'e2e_latency_levels': ('no_levels', None), 'availability_levels': ('no_levels', None)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_storageaccounts_performance']


checkgroup_parameters.setdefault('azure_storageaccounts_usage', [])

checkgroup_parameters['azure_storageaccounts_usage'] = [
{'id': 'ea80f931-a6d7-4b10-a04c-e4a25fdc3db7', 'value': {'used_capacity_levels': ('no_levels', None)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_storageaccounts_usage']


checkgroup_parameters.setdefault('azure_traffic_manager_probe_state', [])

checkgroup_parameters['azure_traffic_manager_probe_state'] = [
{'id': 'cd9f9187-d03b-4792-8b4c-43224ec3c128', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_traffic_manager_probe_state']


checkgroup_parameters.setdefault('azure_traffic_manager_qps', [])

checkgroup_parameters['azure_traffic_manager_qps'] = [
{'id': 'eac36b53-53ed-40e6-8b48-0980fc7ac794', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_traffic_manager_qps']


checkgroup_parameters.setdefault('azure_usagedetails', [])

checkgroup_parameters['azure_usagedetails'] = [
{'id': '72d9b29b-bbd5-4b2d-bda4-1e18a4136636', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_usagedetails']


checkgroup_parameters.setdefault('azure_v2_ad', [])

checkgroup_parameters['azure_v2_ad'] = [
{'id': 'ae8e4dfa-8e56-4589-9415-b8f7c34bb995', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_v2_ad']


checkgroup_parameters.setdefault('azure_v2_agent_info', [])

checkgroup_parameters['azure_v2_agent_info'] = [
{'id': '0ea428c9-695c-4651-834e-8cbc3faefe26', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_v2_agent_info']


checkgroup_parameters.setdefault('azure_v2_app_registration', [])

checkgroup_parameters['azure_v2_app_registration'] = [
{'id': '518f2154-2dad-4706-aac5-73174b300535', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_v2_app_registration']


checkgroup_parameters.setdefault('azure_v2_database_connections', [])

checkgroup_parameters['azure_v2_database_connections'] = [
{'id': 'd554c0d8-a1f5-4a49-99df-e163bf85a8e5', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_v2_database_connections']


checkgroup_parameters.setdefault('azure_v2_databases_connections', [])

checkgroup_parameters['azure_v2_databases_connections'] = [
{'id': '4f45d9fd-f74a-4e1f-9a16-2d95c0e827c1', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_v2_databases_connections']


checkgroup_parameters.setdefault('azure_v2_databases_cpu', [])

checkgroup_parameters['azure_v2_databases_cpu'] = [
{'id': '3629b2b9-a4ee-44a6-9835-4ef628d4ce84', 'value': {'cpu_percent': ('fixed', (85.0, 95.0))}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_v2_databases_cpu']


checkgroup_parameters.setdefault('azure_v2_databases_deadlock', [])

checkgroup_parameters['azure_v2_databases_deadlock'] = [
{'id': '07fa26dd-bcc6-4ba7-996e-2eef755efd5f', 'value': {'deadlocks': ('fixed', (0.0, 0.0))}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_v2_databases_deadlock']


checkgroup_parameters.setdefault('azure_v2_databases_dtu', [])

checkgroup_parameters['azure_v2_databases_dtu'] = [
{'id': 'f2752fcc-02de-4aba-bf95-c2cd6dcc756b', 'value': {'dtu_percent': ('fixed', (40.0, 50.0))}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_v2_databases_dtu']


checkgroup_parameters.setdefault('azure_v2_databases_storage', [])

checkgroup_parameters['azure_v2_databases_storage'] = [
{'id': '63bea5aa-be07-4810-8c8d-c26322f05800', 'value': {'storage_percent': ('fixed', (85.0, 95.0))}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_v2_databases_storage']


checkgroup_parameters.setdefault('azure_v2_db_network', [])

checkgroup_parameters['azure_v2_db_network'] = [
{'id': '010c9b58-a167-4c1c-8170-e7a4ba1438f4', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_v2_db_network']


checkgroup_parameters.setdefault('azure_v2_db_storage', [])

checkgroup_parameters['azure_v2_db_storage'] = [
{'id': '52866d22-7b22-42aa-a33a-58988d7f08d8', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_v2_db_storage']


checkgroup_parameters.setdefault('azure_v2_firewall_health', [])

checkgroup_parameters['azure_v2_firewall_health'] = [
{'id': '73e6e1ef-b6eb-4db0-8a11-a73976c376c8', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_v2_firewall_health']


checkgroup_parameters.setdefault('azure_v2_firewall_latency', [])

checkgroup_parameters['azure_v2_firewall_latency'] = [
{'id': 'a996440e-20a7-4607-b2ee-b945372995ad', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_v2_firewall_latency']


checkgroup_parameters.setdefault('azure_v2_firewall_snat', [])

checkgroup_parameters['azure_v2_firewall_snat'] = [
{'id': '5519a058-95a6-4aec-ab2a-cb2a0de17235', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_v2_firewall_snat']


checkgroup_parameters.setdefault('azure_v2_firewall_throughput', [])

checkgroup_parameters['azure_v2_firewall_throughput'] = [
{'id': 'f3a27fe3-750c-4f38-9a49-cfacb27dabc8', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_v2_firewall_throughput']


checkgroup_parameters.setdefault('azure_v2_load_balancer_byte_count', [])

checkgroup_parameters['azure_v2_load_balancer_byte_count'] = [
{'id': 'c28e13ff-fc9c-412f-88a0-87276fd3e8ab', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_v2_load_balancer_byte_count']


checkgroup_parameters.setdefault('azure_v2_load_balancer_health', [])

checkgroup_parameters['azure_v2_load_balancer_health'] = [
{'id': '87107032-9c35-4e5a-bc6b-62b0946b4526', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_v2_load_balancer_health']


checkgroup_parameters.setdefault('azure_v2_load_balancer_snat', [])

checkgroup_parameters['azure_v2_load_balancer_snat'] = [
{'id': '71404f5a-5403-41a1-863f-c56ca1247b1c', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_v2_load_balancer_snat']


checkgroup_parameters.setdefault('azure_v2_storageaccounts_flow', [])

checkgroup_parameters['azure_v2_storageaccounts_flow'] = [
{'id': '93fc1b73-6fe1-4a18-beb8-2cb950484ae5', 'value': {'transactions_levels': ('no_levels', None), 'ingress_levels': ('no_levels', None), 'egress_levels': ('no_levels', None)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_v2_storageaccounts_flow']


checkgroup_parameters.setdefault('azure_v2_storageaccounts_performance', [])

checkgroup_parameters['azure_v2_storageaccounts_performance'] = [
{'id': '3d171bd7-62c9-4234-a5ba-a88445b484cf', 'value': {'server_latency_levels': ('no_levels', None), 'e2e_latency_levels': ('no_levels', None), 'availability_levels': ('no_levels', None)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_v2_storageaccounts_performance']


checkgroup_parameters.setdefault('azure_v2_storageaccounts_usage', [])

checkgroup_parameters['azure_v2_storageaccounts_usage'] = [
{'id': '6485136a-9677-404d-b704-21e9168e1b13', 'value': {'used_capacity_levels': ('no_levels', None)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_v2_storageaccounts_usage']


checkgroup_parameters.setdefault('azure_v2_subscription_info', [])

checkgroup_parameters['azure_v2_subscription_info'] = [
{'id': 'f246d9aa-0135-4f40-92ca-c523c4b87487', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_v2_subscription_info']


checkgroup_parameters.setdefault('azure_v2_traffic_manager_probe_state', [])

checkgroup_parameters['azure_v2_traffic_manager_probe_state'] = [
{'id': 'e2edf1da-a9d4-4310-a002-1162b5e5c2fe', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_v2_traffic_manager_probe_state']


checkgroup_parameters.setdefault('azure_v2_traffic_manager_qps', [])

checkgroup_parameters['azure_v2_traffic_manager_qps'] = [
{'id': 'e12aba61-9d52-4c68-8f67-96f743e00e35', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_v2_traffic_manager_qps']


checkgroup_parameters.setdefault('azure_v2_usagedetails', [])

checkgroup_parameters['azure_v2_usagedetails'] = [
{'id': 'aa8e790a-fcd8-4ed2-b27f-7df11797a04e', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_v2_usagedetails']


checkgroup_parameters.setdefault('azure_v2_virtualnetworkgateways', [])

checkgroup_parameters['azure_v2_virtualnetworkgateways'] = [
{'id': 'e0d6f391-8cc8-490a-8f5d-17130a783665', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_v2_virtualnetworkgateways']


checkgroup_parameters.setdefault('azure_v2_vm_burst_cpu_credits', [])

checkgroup_parameters['azure_v2_vm_burst_cpu_credits'] = [
{'id': 'abfd7c50-f05f-49a5-b44c-23a2beba1543', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_v2_vm_burst_cpu_credits']


checkgroup_parameters.setdefault('azure_v2_vm_disk', [])

checkgroup_parameters['azure_v2_vm_disk'] = [
{'id': '2d8da5f0-542a-4acd-b11c-4fa3de0b0214', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_v2_vm_disk']


checkgroup_parameters.setdefault('azure_v2_vms', [])

checkgroup_parameters['azure_v2_vms'] = [
{'id': '78b5aa68-ef2a-4afe-8dee-04561fd2c681', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_v2_vms']


checkgroup_parameters.setdefault('azure_v2_webserver', [])

checkgroup_parameters['azure_v2_webserver'] = [
{'id': 'faa6db64-62fd-493f-82c8-d436e1bf3859', 'value': {'avg_response_time_levels': ('fixed', (1.0, 10.0)), 'error_rate_levels': ('fixed', (0.01, 0.04)), 'cpu_time_percent_levels': ('fixed', (85.0, 95.0))}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_v2_webserver']


checkgroup_parameters.setdefault('azure_virtualnetworkgateways', [])

checkgroup_parameters['azure_virtualnetworkgateways'] = [
{'id': '801d4f07-57de-40bd-8cef-da83ea6f7af9', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_virtualnetworkgateways']


checkgroup_parameters.setdefault('azure_vm_burst_cpu_credits', [])

checkgroup_parameters['azure_vm_burst_cpu_credits'] = [
{'id': 'bca44138-9d36-49eb-996b-ad71de779e4d', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_vm_burst_cpu_credits']


checkgroup_parameters.setdefault('azure_vm_disk', [])

checkgroup_parameters['azure_vm_disk'] = [
{'id': '0dc88a70-7bff-4b0a-9f9e-1494a0365c2c', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_vm_disk']


checkgroup_parameters.setdefault('azure_vms', [])

checkgroup_parameters['azure_vms'] = [
{'id': '47f29460-40a7-430c-82dd-756a3ce98b45', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_vms']


checkgroup_parameters.setdefault('azure_vms_summary', [])

checkgroup_parameters['azure_vms_summary'] = [
{'id': 'bb529f20-afcb-4db1-89fa-eb0ded7c145a', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['azure_vms_summary']


checkgroup_parameters.setdefault('backup_timemachine', [])

checkgroup_parameters['backup_timemachine'] = [
{'id': '47ec7203-00fb-48f8-9502-3d0225491f12', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['backup_timemachine']


checkgroup_parameters.setdefault('battery', [])

checkgroup_parameters['battery'] = [
{'id': '12b77f38-68a1-4953-9933-311b0ce551e1', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['battery']


checkgroup_parameters.setdefault('bazel_version', [])

checkgroup_parameters['bazel_version'] = [
{'id': '7d1ac788-8520-4e5f-bb0e-4087573483c5', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['bazel_version']


checkgroup_parameters.setdefault('bgp_peer', [])

checkgroup_parameters['bgp_peer'] = [
{'id': '3eaf569e-4908-4384-93ae-c6dfc5a25d86', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['bgp_peer']


checkgroup_parameters.setdefault('blank_tapes', [])

checkgroup_parameters['blank_tapes'] = [
{'id': '86ef5a67-9127-48bc-a589-48e105fc51b8', 'value': {'levels_lower': None}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['blank_tapes']


checkgroup_parameters.setdefault('bluecat_command_server', [])

checkgroup_parameters['bluecat_command_server'] = [
{'id': '02605f95-635e-4245-8633-4f94da355e3e', 'value': {'oper_states': {'warning': [2, 3, 4], 'critical': [5]}}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['bluecat_command_server']


checkgroup_parameters.setdefault('bluecat_dhcp', [])

checkgroup_parameters['bluecat_dhcp'] = [
{'id': '5376428e-bff4-4545-a288-df207ecc1e5c', 'value': {'oper_states': {'warning': [2, 3, 4], 'critical': [5]}}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['bluecat_dhcp']


checkgroup_parameters.setdefault('bluecat_dns', [])

checkgroup_parameters['bluecat_dns'] = [
{'id': '50bf59a8-2615-4dfb-ac40-097efb4160a6', 'value': {'oper_states': {'warning': [2, 3, 4], 'critical': [5]}}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['bluecat_dns']


checkgroup_parameters.setdefault('bluecat_ha', [])

checkgroup_parameters['bluecat_ha'] = [
{'id': '1949467a-0e8d-49f3-9a3a-f289313c760a', 'value': {'oper_states': {'warning': [5, 6, 7], 'critical': [4, 8]}}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['bluecat_ha']


checkgroup_parameters.setdefault('bluecat_ntp', [])

checkgroup_parameters['bluecat_ntp'] = [
{'id': 'a20573c0-a86f-4877-a0bc-4a36aacc3aa8', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['bluecat_ntp']


checkgroup_parameters.setdefault('bonding', [])

checkgroup_parameters['bonding'] = [
{'id': '44f97912-116a-4474-a04c-7abdd2ea1214', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['bonding']


checkgroup_parameters.setdefault('bossock_fibers', [])

checkgroup_parameters['bossock_fibers'] = [
{'id': '328c0c9a-fc08-4a31-88b3-007cb99d192b', 'value': {'levels': None}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['bossock_fibers']


checkgroup_parameters.setdefault('brightness', [])

checkgroup_parameters['brightness'] = [
{'id': 'a124221d-d916-4cbd-ac97-b640b65843a9', 'value': {'levels': (50.0, 100.0)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['brightness']


checkgroup_parameters.setdefault('brocade_fcport', [])

checkgroup_parameters['brocade_fcport'] = [
{'id': '0938a364-421b-4e25-b84b-98271547d5d6', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['brocade_fcport']


checkgroup_parameters.setdefault('brocade_optical', [])

checkgroup_parameters['brocade_optical'] = [
{'id': '5381225e-0b17-44c1-9f3b-fc1155263d38', 'value': {'temp': True, 'tx_light': False, 'rx_light': False, 'lanes': False}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['brocade_optical']


checkgroup_parameters.setdefault('brocade_sfp', [])

checkgroup_parameters['brocade_sfp'] = [
{'id': 'abe598c1-3f6b-43da-a877-f38b656f76ea', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['brocade_sfp']


checkgroup_parameters.setdefault('bvip_link', [])

checkgroup_parameters['bvip_link'] = [
{'id': 'fb032982-00fd-4ca8-816d-2e7b3fda8dd6', 'value': {'ok_states': [0, 4, 5], 'warn_states': [7], 'crit_states': [1, 2, 3]}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['bvip_link']


checkgroup_parameters.setdefault('byte_count', [])

checkgroup_parameters['byte_count'] = [
{'id': 'dd3e8302-3e93-4528-a36d-073477b95625', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['byte_count']


checkgroup_parameters.setdefault('carbon_monoxide', [])

checkgroup_parameters['carbon_monoxide'] = [
{'id': '7d35c85d-a560-4177-ba65-c0b25676de52', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['carbon_monoxide']


checkgroup_parameters.setdefault('check_redfish_ethernetinterfaces', [])

checkgroup_parameters['check_redfish_ethernetinterfaces'] = [
{'id': '1a5432e1-56e4-438c-bbf2-51d6a0f61bc7', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['check_redfish_ethernetinterfaces']


checkgroup_parameters.setdefault('checkpoint_connections', [])

checkgroup_parameters['checkpoint_connections'] = [
{'id': 'f9630bbf-586e-4290-808d-82c337387753', 'value': {'levels': (40000, 50000)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['checkpoint_connections']


checkgroup_parameters.setdefault('checkpoint_packets', [])

checkgroup_parameters['checkpoint_packets'] = [
{'id': '01017883-2983-4f98-ae97-c47c5814d74c', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['checkpoint_packets']


checkgroup_parameters.setdefault('checkpoint_powersupply', [])

checkgroup_parameters['checkpoint_powersupply'] = [
{'id': 'e0d1f75e-0760-417c-8689-e05b88e90837', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['checkpoint_powersupply']


checkgroup_parameters.setdefault('checkpoint_tunnels', [])

checkgroup_parameters['checkpoint_tunnels'] = [
{'id': 'a469bee0-aa2e-4739-b372-2f2c2753c6a2', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['checkpoint_tunnels']


checkgroup_parameters.setdefault('checkpoint_vsx_connections', [])

checkgroup_parameters['checkpoint_vsx_connections'] = [
{'id': 'fef98a51-1e36-41fc-8fea-5aca4a3a9eb3', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['checkpoint_vsx_connections']


checkgroup_parameters.setdefault('checkpoint_vsx_packets', [])

checkgroup_parameters['checkpoint_vsx_packets'] = [
{'id': '621462fc-5966-480c-8b82-e39ba5bd926a', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['checkpoint_vsx_packets']


checkgroup_parameters.setdefault('checkpoint_vsx_traffic', [])

checkgroup_parameters['checkpoint_vsx_traffic'] = [
{'id': 'e7ed53eb-8c5a-4dc7-81ce-d6b85d098df8', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['checkpoint_vsx_traffic']


checkgroup_parameters.setdefault('cisco_asa_failover', [])

checkgroup_parameters['cisco_asa_failover'] = [
{'id': 'f188129a-3a2c-4f93-9a05-5909045613f6', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['cisco_asa_failover']


checkgroup_parameters.setdefault('cisco_cpu_memory', [])

checkgroup_parameters['cisco_cpu_memory'] = [
{'id': 'c31f047a-7bfb-4996-b193-99845ceb374a', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['cisco_cpu_memory']


checkgroup_parameters.setdefault('cisco_dom', [])

checkgroup_parameters['cisco_dom'] = [
{'id': '636f6c13-712e-4e90-ad70-e8c9439195e0', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['cisco_dom']


checkgroup_parameters.setdefault('cisco_fw_connections', [])

checkgroup_parameters['cisco_fw_connections'] = [
{'id': '6310407e-1b64-4d9f-9f1f-a9d2c2d6044d', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['cisco_fw_connections']


checkgroup_parameters.setdefault('cisco_ip_sla', [])

checkgroup_parameters['cisco_ip_sla'] = [
{'id': '278c7b38-3292-458b-b6c7-fb1383fa3e4f', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['cisco_ip_sla']


checkgroup_parameters.setdefault('cisco_mem', [])

checkgroup_parameters['cisco_mem'] = [
{'id': '1c5952fd-3ed8-4cd1-b42f-af1f8127fa80', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['cisco_mem']


checkgroup_parameters.setdefault('cisco_meraki_org_api_response_codes', [])

checkgroup_parameters['cisco_meraki_org_api_response_codes'] = [
{'id': 'aa42f27f-7668-4110-9660-23ad15f1cc2b', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['cisco_meraki_org_api_response_codes']


checkgroup_parameters.setdefault('cisco_meraki_org_appliance_performance', [])

checkgroup_parameters['cisco_meraki_org_appliance_performance'] = [
{'id': '59911f67-1584-438e-9875-178f632ce380', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['cisco_meraki_org_appliance_performance']


checkgroup_parameters.setdefault('cisco_meraki_org_appliance_uplinks', [])

checkgroup_parameters['cisco_meraki_org_appliance_uplinks'] = [
{'id': '289c6fb1-4431-4241-bdaf-9d899eee729f', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['cisco_meraki_org_appliance_uplinks']


checkgroup_parameters.setdefault('cisco_meraki_org_appliance_vpns', [])

checkgroup_parameters['cisco_meraki_org_appliance_vpns'] = [
{'id': '7cd896a1-6ebe-4f79-abd8-40a71b00fcfc', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['cisco_meraki_org_appliance_vpns']


checkgroup_parameters.setdefault('cisco_meraki_org_device_status', [])

checkgroup_parameters['cisco_meraki_org_device_status'] = [
{'id': '78b5111c-43ae-473f-8315-e39fb416c121', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['cisco_meraki_org_device_status']


checkgroup_parameters.setdefault('cisco_meraki_org_device_status_ps', [])

checkgroup_parameters['cisco_meraki_org_device_status_ps'] = [
{'id': 'e17ffedc-b93f-4dc6-8d07-03b7c623cf5d', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['cisco_meraki_org_device_status_ps']


checkgroup_parameters.setdefault('cisco_meraki_org_licenses_overview', [])

checkgroup_parameters['cisco_meraki_org_licenses_overview'] = [
{'id': '01f483db-7510-48b7-ad72-b2e0b04fd366', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['cisco_meraki_org_licenses_overview']


checkgroup_parameters.setdefault('cisco_meraki_org_wireless_device_statuses_ssids', [])

checkgroup_parameters['cisco_meraki_org_wireless_device_statuses_ssids'] = [
{'id': '8f3c2d07-16fd-433f-98d2-da6b80a9cc8e', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['cisco_meraki_org_wireless_device_statuses_ssids']


checkgroup_parameters.setdefault('cisco_meraki_switch_ports_statuses', [])

checkgroup_parameters['cisco_meraki_switch_ports_statuses'] = [
{'id': '49dfd630-82c1-4fe3-9a5f-2b52914c8348', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['cisco_meraki_switch_ports_statuses']


checkgroup_parameters.setdefault('cisco_prime_wifi_access_points', [])

checkgroup_parameters['cisco_prime_wifi_access_points'] = [
{'id': '047426c9-9fb6-4f9d-a0c8-b4c761f322d2', 'value': {'levels': (20.0, 40.0)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['cisco_prime_wifi_access_points']


checkgroup_parameters.setdefault('cisco_prime_wifi_connections', [])

checkgroup_parameters['cisco_prime_wifi_connections'] = [
{'id': '8b38be21-f8e3-45b4-93c0-5840b27b5a60', 'value': {'levels_lower': None}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['cisco_prime_wifi_connections']


checkgroup_parameters.setdefault('cisco_prime_wlan_controller_access_points', [])

checkgroup_parameters['cisco_prime_wlan_controller_access_points'] = [
{'id': '964f4984-3028-402a-8260-f01e60a51e1b', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['cisco_prime_wlan_controller_access_points']


checkgroup_parameters.setdefault('cisco_prime_wlan_controller_clients', [])

checkgroup_parameters['cisco_prime_wlan_controller_clients'] = [
{'id': '6b0c936c-bce6-4f33-ac1a-10bb31cbfaf5', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['cisco_prime_wlan_controller_clients']


checkgroup_parameters.setdefault('cisco_prime_wlan_controller_last_backup', [])

checkgroup_parameters['cisco_prime_wlan_controller_last_backup'] = [
{'id': '23cb2de3-c94e-4bb3-aeb9-f137d697c2f5', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['cisco_prime_wlan_controller_last_backup']


checkgroup_parameters.setdefault('cisco_qos', [])

checkgroup_parameters['cisco_qos'] = [
{'id': '990f4148-d3a9-4665-9262-649fad859797', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['cisco_qos']


checkgroup_parameters.setdefault('cisco_sma_dns_requests', [])

checkgroup_parameters['cisco_sma_dns_requests'] = [
{'id': '5407588a-f064-4a1c-bd6a-03f2194e51fe', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['cisco_sma_dns_requests']


checkgroup_parameters.setdefault('cisco_sma_files_and_sockets', [])

checkgroup_parameters['cisco_sma_files_and_sockets'] = [
{'id': 'f43fa630-ae02-49fc-8a92-1b0b5482a3c9', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['cisco_sma_files_and_sockets']


checkgroup_parameters.setdefault('cisco_sma_mail_transfer_memory', [])

checkgroup_parameters['cisco_sma_mail_transfer_memory'] = [
{'id': '5beb9e0d-0a16-4752-a48a-7ed6a6776c8a', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['cisco_sma_mail_transfer_memory']


checkgroup_parameters.setdefault('cisco_sma_mail_transfer_threads', [])

checkgroup_parameters['cisco_sma_mail_transfer_threads'] = [
{'id': 'decab122-a6ee-4d75-a70b-eec51f66240e', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['cisco_sma_mail_transfer_threads']


checkgroup_parameters.setdefault('cisco_sma_message_queue', [])

checkgroup_parameters['cisco_sma_message_queue'] = [
{'id': 'b74cef29-8a95-4499-a627-a180389f5bf0', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['cisco_sma_message_queue']


checkgroup_parameters.setdefault('cisco_stack', [])

checkgroup_parameters['cisco_stack'] = [
{'id': '71a1cd44-c3ad-47d6-87cb-9ec9c769a9ad', 'value': {'waiting': 0, 'progressing': 0, 'added': 0, 'ready': 0, 'sdmMismatch': 1, 'verMismatch': 1, 'featureMismatch': 1, 'newMasterInit': 0, 'provisioned': 0, 'invalid': 2, 'removed': 2}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['cisco_stack']


checkgroup_parameters.setdefault('cisco_supervisor_mem', [])

checkgroup_parameters['cisco_supervisor_mem'] = [
{'id': '493bc878-77d8-4a4c-be12-901981aa742b', 'value': {'levels': None}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['cisco_supervisor_mem']


checkgroup_parameters.setdefault('cisco_vpn_sessions', [])

checkgroup_parameters['cisco_vpn_sessions'] = [
{'id': '11ba3150-8fb4-4126-83c5-a7c27e019ee3', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['cisco_vpn_sessions']


checkgroup_parameters.setdefault('cisco_wlc', [])

checkgroup_parameters['cisco_wlc'] = [
{'id': '6eb3068b-19a7-4497-9ae1-d106f7d33e43', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['cisco_wlc']


checkgroup_parameters.setdefault('citrix_desktops_registered', [])

checkgroup_parameters['citrix_desktops_registered'] = [
{'id': '073ef855-6522-4257-b0f7-d4f424d77b73', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['citrix_desktops_registered']


checkgroup_parameters.setdefault('citrix_licenses', [])

checkgroup_parameters['citrix_licenses'] = [
{'id': '5966f01f-7270-4142-9135-0d951b2c45a8', 'value': {'levels': ('crit_on_all', None)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['citrix_licenses']


checkgroup_parameters.setdefault('citrix_load', [])

checkgroup_parameters['citrix_load'] = [
{'id': '4cfbfb1e-2c5e-4b06-bb9c-72860adab644', 'value': {'levels': None}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['citrix_load']


checkgroup_parameters.setdefault('citrix_sessions', [])

checkgroup_parameters['citrix_sessions'] = [
{'id': 'f80c4428-90d0-49ba-a9b8-542bc92fb345', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['citrix_sessions']


checkgroup_parameters.setdefault('citrix_state', [])

checkgroup_parameters['citrix_state'] = [
{'id': 'e62a763d-204f-4137-aae6-1af0cc6c6950', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['citrix_state']


checkgroup_parameters.setdefault('clr_memory', [])

checkgroup_parameters['clr_memory'] = [
{'id': '3a7aa186-e9a7-459b-a2a2-2413e6d12ed8', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['clr_memory']


checkgroup_parameters.setdefault('cluster_status', [])

checkgroup_parameters['cluster_status'] = [
{'id': '77046d4e-e9a3-4288-a1f2-cbaf01966a87', 'value': {'type': 'active_standby'}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['cluster_status']


checkgroup_parameters.setdefault('corosync_latency', [])

checkgroup_parameters['corosync_latency'] = [
{'id': '4a44fecb-88df-4303-b3b3-92fcda018d28', 'value': {'latency_max': ('fixed', (0.005, 0.01)), 'latency_ave': ('fixed', (0.005, 0.01))}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['corosync_latency']


checkgroup_parameters.setdefault('couchbase_cache', [])

checkgroup_parameters['couchbase_cache'] = [
{'id': '8b3fcdfa-ff10-4760-997b-3caccce5ef58', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['couchbase_cache']


checkgroup_parameters.setdefault('couchbase_fragmentation', [])

checkgroup_parameters['couchbase_fragmentation'] = [
{'id': 'd85b3e04-1800-43b6-be76-67783de01c31', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['couchbase_fragmentation']


checkgroup_parameters.setdefault('couchbase_items', [])

checkgroup_parameters['couchbase_items'] = [
{'id': '15aef9bc-d44a-4a72-81c5-b106ab60b8d0', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['couchbase_items']


checkgroup_parameters.setdefault('couchbase_ops', [])

checkgroup_parameters['couchbase_ops'] = [
{'id': 'b7ffabd4-8ee9-42c3-ba18-97b934229f46', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['couchbase_ops']


checkgroup_parameters.setdefault('couchbase_ops_buckets', [])

checkgroup_parameters['couchbase_ops_buckets'] = [
{'id': '3697d2fd-9c3c-44ad-8e15-0e721508ed7e', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['couchbase_ops_buckets']


checkgroup_parameters.setdefault('couchbase_ops_nodes', [])

checkgroup_parameters['couchbase_ops_nodes'] = [
{'id': '191493ff-cda8-4e9d-a85c-d4a475d0b0c0', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['couchbase_ops_nodes']


checkgroup_parameters.setdefault('couchbase_size_couch', [])

checkgroup_parameters['couchbase_size_couch'] = [
{'id': '6f9de796-4269-427a-967a-bca2c8cd3592', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['couchbase_size_couch']


checkgroup_parameters.setdefault('couchbase_size_docs', [])

checkgroup_parameters['couchbase_size_docs'] = [
{'id': 'b0b72d00-68ad-475d-ace6-a14394ddab98', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['couchbase_size_docs']


checkgroup_parameters.setdefault('couchbase_size_spacial', [])

checkgroup_parameters['couchbase_size_spacial'] = [
{'id': 'e0b006c2-380a-4c9e-a422-ec93a98e73b5', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['couchbase_size_spacial']


checkgroup_parameters.setdefault('couchbase_status', [])

checkgroup_parameters['couchbase_status'] = [
{'id': '0cdc1455-0dd5-462a-92f5-66d56001eeef', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['couchbase_status']


checkgroup_parameters.setdefault('couchbase_vbuckets', [])

checkgroup_parameters['couchbase_vbuckets'] = [
{'id': 'c331f085-b90a-451d-829b-5abac089f4d4', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['couchbase_vbuckets']


checkgroup_parameters.setdefault('cpu_iowait', [])

checkgroup_parameters['cpu_iowait'] = [
{'id': '32c13093-d82d-4d1b-a658-b346b31a0cdd', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['cpu_iowait']


checkgroup_parameters.setdefault('cpu_load', [])

checkgroup_parameters['cpu_load'] = [
{'id': '6d8d8ac2-017e-4430-b21f-34a85b6f8bb1', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['cpu_load']


checkgroup_parameters.setdefault('cpu_utilization', [])

checkgroup_parameters['cpu_utilization'] = [
{'id': '0dfeaaf1-67ea-471a-8676-a35392b64c41', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['cpu_utilization']


checkgroup_parameters.setdefault('cpu_utilization_esx_vsphere_hostsystem', [])

checkgroup_parameters['cpu_utilization_esx_vsphere_hostsystem'] = [
{'id': '91b8e6fa-e615-414e-8cfe-bffe1bd1073b', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['cpu_utilization_esx_vsphere_hostsystem']


checkgroup_parameters.setdefault('cpu_utilization_multiitem', [])

checkgroup_parameters['cpu_utilization_multiitem'] = [
{'id': '15918ab0-7923-4b46-b472-604db7dd989e', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['cpu_utilization_multiitem']


checkgroup_parameters.setdefault('cpu_utilization_os', [])

checkgroup_parameters['cpu_utilization_os'] = [
{'id': '6aacbb2b-e7e0-4cf4-a47a-7fb2c1b68937', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['cpu_utilization_os']


checkgroup_parameters.setdefault('cpu_utilization_with_item', [])

checkgroup_parameters['cpu_utilization_with_item'] = [
{'id': '30a47146-1bcd-41de-a531-988177207a8e', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['cpu_utilization_with_item']


checkgroup_parameters.setdefault('credentials_expiration', [])

checkgroup_parameters['credentials_expiration'] = [
{'id': '7fa8f782-f6fe-4e70-bf00-aed8a185feff', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['credentials_expiration']


checkgroup_parameters.setdefault('cups_queues', [])

checkgroup_parameters['cups_queues'] = [
{'id': 'a88ceb75-7191-48d3-9851-d77ae40e8859', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['cups_queues']


checkgroup_parameters.setdefault('database_connections', [])

checkgroup_parameters['database_connections'] = [
{'id': '087b28f3-46d6-4c8f-90b5-75953d706230', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['database_connections']


checkgroup_parameters.setdefault('datadog_monitors_check', [])

checkgroup_parameters['datadog_monitors_check'] = [
{'id': '5de59c39-c66f-4712-be54-d87c02c4dead', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['datadog_monitors_check']


checkgroup_parameters.setdefault('db2_backup', [])

checkgroup_parameters['db2_backup'] = [
{'id': 'eb89cfd2-8158-453e-9d21-0b7f3ad86882', 'value': {'levels': None}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['db2_backup']


checkgroup_parameters.setdefault('db2_connections', [])

checkgroup_parameters['db2_connections'] = [
{'id': '620998a5-e88b-4c5e-88e9-9b96d8160f6e', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['db2_connections']


checkgroup_parameters.setdefault('db2_counters', [])

checkgroup_parameters['db2_counters'] = [
{'id': '882e5999-25ee-4119-854f-c4a6c1a1bf17', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['db2_counters']


checkgroup_parameters.setdefault('db2_logsize', [])

checkgroup_parameters['db2_logsize'] = [
{'id': 'd12130f8-a981-4f63-89b4-ed97b202ac59', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['db2_logsize']


checkgroup_parameters.setdefault('db2_mem', [])

checkgroup_parameters['db2_mem'] = [
{'id': '3bcea6a0-16be-4757-8049-c891ab5dfbab', 'value': {'levels_lower': None}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['db2_mem']


checkgroup_parameters.setdefault('db2_sortoverflow', [])

checkgroup_parameters['db2_sortoverflow'] = [
{'id': '21357f64-7b7d-4ae7-8125-ca22666726ee', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['db2_sortoverflow']


checkgroup_parameters.setdefault('db2_tablespaces', [])

checkgroup_parameters['db2_tablespaces'] = [
{'id': '11a0725f-f6be-4c4a-9af2-bfe23aa3b78d', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['db2_tablespaces']


checkgroup_parameters.setdefault('db_bloat', [])

checkgroup_parameters['db_bloat'] = [
{'id': '1af0e877-03f1-4c08-b289-fd65913703bc', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['db_bloat']


checkgroup_parameters.setdefault('db_connections', [])

checkgroup_parameters['db_connections'] = [
{'id': 'c5d521a5-95b7-4afa-bb01-defef085296a', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['db_connections']


checkgroup_parameters.setdefault('db_connections_mongodb', [])

checkgroup_parameters['db_connections_mongodb'] = [
{'id': 'bf1a979c-539e-4c6b-9610-9b26e7b6101f', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['db_connections_mongodb']


checkgroup_parameters.setdefault('db_usage', [])

checkgroup_parameters['db_usage'] = [
{'id': '1412fd47-e9c2-43ad-93be-0e4bb0aef47e', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['db_usage']


checkgroup_parameters.setdefault('ddn_s2a_port_errors', [])

checkgroup_parameters['ddn_s2a_port_errors'] = [
{'id': 'e86868f1-1334-4dd8-933f-6c22ca68db33', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['ddn_s2a_port_errors']


checkgroup_parameters.setdefault('ddn_s2a_wait', [])

checkgroup_parameters['ddn_s2a_wait'] = [
{'id': '8b235941-f5be-455c-ae1e-ea2c1726073b', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['ddn_s2a_wait']


checkgroup_parameters.setdefault('disk_failures', [])

checkgroup_parameters['disk_failures'] = [
{'id': 'd21e01a1-097e-4538-abdf-460519ebc5a8', 'value': {'levels': None}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['disk_failures']


checkgroup_parameters.setdefault('disk_io', [])

checkgroup_parameters['disk_io'] = [
{'id': '8e17bf32-1120-493e-8b45-8f793cb6ef67', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['disk_io']


checkgroup_parameters.setdefault('diskstat', [])

checkgroup_parameters['diskstat'] = [
{'id': '52642dbe-da44-4faf-85d6-095f68b1f08e', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['diskstat']


checkgroup_parameters.setdefault('docker_node_containers', [])

checkgroup_parameters['docker_node_containers'] = [
{'id': '1de30749-b5d1-46cc-a06e-a9e1953e03d5', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['docker_node_containers']


checkgroup_parameters.setdefault('docker_node_disk_usage', [])

checkgroup_parameters['docker_node_disk_usage'] = [
{'id': '2ccceffd-2477-468f-aced-58ad74db89b4', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['docker_node_disk_usage']


checkgroup_parameters.setdefault('docsis_channels_downstream', [])

checkgroup_parameters['docsis_channels_downstream'] = [
{'id': 'acf32aa9-24be-43e7-8c36-9b3b79178b1a', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['docsis_channels_downstream']


checkgroup_parameters.setdefault('docsis_channels_upstream', [])

checkgroup_parameters['docsis_channels_upstream'] = [
{'id': '6da08662-3e6c-4580-89b1-6f867fcf8e86', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['docsis_channels_upstream']


checkgroup_parameters.setdefault('docsis_cm_status', [])

checkgroup_parameters['docsis_cm_status'] = [
{'id': 'da937013-0b97-4353-907e-71abecebf084', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['docsis_cm_status']


checkgroup_parameters.setdefault('domino_mailqueues', [])

checkgroup_parameters['domino_mailqueues'] = [
{'id': 'ba2fe135-9cf1-4d95-92f8-e9ee0b89e9a3', 'value': {'queue_length': (300, 350)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['domino_mailqueues']


checkgroup_parameters.setdefault('domino_tasks', [])

checkgroup_parameters['domino_tasks'] = [
{'id': '798a5f42-f3dd-4379-afad-983417774d60', 'value': {'levels': (1, 1, 99999, 99999)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['domino_tasks']


checkgroup_parameters.setdefault('domino_transactions', [])

checkgroup_parameters['domino_transactions'] = [
{'id': 'd1d71afe-35dc-4b83-a7d8-a87b31978c42', 'value': {'levels': None}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['domino_transactions']


checkgroup_parameters.setdefault('domino_users', [])

checkgroup_parameters['domino_users'] = [
{'id': '6dfaf251-240b-4877-931a-a39a9dde36e0', 'value': {'levels': None}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['domino_users']


checkgroup_parameters.setdefault('drbd', [])

checkgroup_parameters['drbd'] = [
{'id': '5f6369d5-f66f-42ee-8ad5-c41c73cf2407', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['drbd']


checkgroup_parameters.setdefault('eaton_enviroment', [])

checkgroup_parameters['eaton_enviroment'] = [
{'id': '304076ff-d4dc-456f-8af1-d3afaddeb0e0', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['eaton_enviroment']


checkgroup_parameters.setdefault('efreq', [])

checkgroup_parameters['efreq'] = [
{'id': '918c0a5a-5a5d-4f73-8132-77387fc3f866', 'value': {'levels_lower': (40, 45)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['efreq']


checkgroup_parameters.setdefault('el_inphase', [])

checkgroup_parameters['el_inphase'] = [
{'id': '0065d07e-5b17-46ef-bb39-5011c555eedf', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['el_inphase']


checkgroup_parameters.setdefault('elasticsearch_cluster_health', [])

checkgroup_parameters['elasticsearch_cluster_health'] = [
{'id': '73e99744-2e3f-4c09-9d11-8be7872bb86b', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['elasticsearch_cluster_health']


checkgroup_parameters.setdefault('elasticsearch_cluster_shards', [])

checkgroup_parameters['elasticsearch_cluster_shards'] = [
{'id': '4cef5f65-b4eb-41e1-a5d5-f3ba23ea81f7', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['elasticsearch_cluster_shards']


checkgroup_parameters.setdefault('elasticsearch_cluster_tasks', [])

checkgroup_parameters['elasticsearch_cluster_tasks'] = [
{'id': 'df0135be-3bb5-486b-90b9-61be303b9e5f', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['elasticsearch_cluster_tasks']


checkgroup_parameters.setdefault('elasticsearch_indices', [])

checkgroup_parameters['elasticsearch_indices'] = [
{'id': '2fde0eeb-9a59-4286-afec-5e78807f3ee0', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['elasticsearch_indices']


checkgroup_parameters.setdefault('elasticsearch_nodes', [])

checkgroup_parameters['elasticsearch_nodes'] = [
{'id': '0421ff81-2e9c-4aee-ab5a-9c27d87d3ee4', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['elasticsearch_nodes']


checkgroup_parameters.setdefault('emc_datadomain_mtree', [])

checkgroup_parameters['emc_datadomain_mtree'] = [
{'id': '17d99d67-47bc-4240-98df-9cb1c0af324b', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['emc_datadomain_mtree']


checkgroup_parameters.setdefault('enterasys_powersupply', [])

checkgroup_parameters['enterasys_powersupply'] = [
{'id': '4dd427d1-5efb-4857-9407-e6c3aa5ad0f3', 'value': {'redundancy_ok_states': [1]}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['enterasys_powersupply']


checkgroup_parameters.setdefault('entersekt_certexpiry', [])

checkgroup_parameters['entersekt_certexpiry'] = [
{'id': '835ee5a5-9b97-4907-ad8c-4a0bba259452', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['entersekt_certexpiry']


checkgroup_parameters.setdefault('entersekt_ecerterrors', [])

checkgroup_parameters['entersekt_ecerterrors'] = [
{'id': '840de5c8-70a9-4bdd-863c-f3b959580238', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['entersekt_ecerterrors']


checkgroup_parameters.setdefault('entersekt_emrerrors', [])

checkgroup_parameters['entersekt_emrerrors'] = [
{'id': '2aabdb5f-83f9-44ae-a367-b777c0057438', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['entersekt_emrerrors']


checkgroup_parameters.setdefault('entersekt_soaperrors', [])

checkgroup_parameters['entersekt_soaperrors'] = [
{'id': '8bce3cc3-18e4-4b12-8da5-da97e0f53bcc', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['entersekt_soaperrors']


checkgroup_parameters.setdefault('epower', [])

checkgroup_parameters['epower'] = [
{'id': '941f8d6a-67fb-4210-a8f0-d1929666de26', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['epower']


checkgroup_parameters.setdefault('epower_single', [])

checkgroup_parameters['epower_single'] = [
{'id': '49490c8c-76f2-4df6-9943-9d4d18ed1c11', 'value': {'levels': None}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['epower_single']


checkgroup_parameters.setdefault('esx_host_memory', [])

checkgroup_parameters['esx_host_memory'] = [
{'id': 'ee107293-3de7-488d-a4d7-274ca9fba5fe', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['esx_host_memory']


checkgroup_parameters.setdefault('esx_hostystem_maintenance', [])

checkgroup_parameters['esx_hostystem_maintenance'] = [
{'id': 'e821936c-9802-44b2-820b-21bb06116a56', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['esx_hostystem_maintenance']


checkgroup_parameters.setdefault('esx_licenses', [])

checkgroup_parameters['esx_licenses'] = [
{'id': '9a6a08fa-f51c-4ca7-8f5b-4e9325a330a7', 'value': {'levels': ('crit_on_all', None)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['esx_licenses']


checkgroup_parameters.setdefault('esx_vsphere_counters_gpu_utilization', [])

checkgroup_parameters['esx_vsphere_counters_gpu_utilization'] = [
{'id': '307af6a4-05f2-4347-9297-a1775ad2ec2d', 'value': {'levels_upper': ('fixed', (80.0, 90.0))}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['esx_vsphere_counters_gpu_utilization']


checkgroup_parameters.setdefault('esx_vsphere_datastores', [])

checkgroup_parameters['esx_vsphere_datastores'] = [
{'id': '70052309-6467-44c5-bc10-313826a40734', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['esx_vsphere_datastores']


checkgroup_parameters.setdefault('esx_vsphere_objects', [])

checkgroup_parameters['esx_vsphere_objects'] = [
{'id': 'ab67611b-4d50-4f31-8aec-d8ac82bf21ad', 'value': {'states': {'standBy': 1, 'poweredOn': 0, 'poweredOff': 1, 'suspended': 1, 'unknown': 3}}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['esx_vsphere_objects']


checkgroup_parameters.setdefault('esx_vsphere_objects_count', [])

checkgroup_parameters['esx_vsphere_objects_count'] = [
{'id': '99269bde-5179-41a2-b97e-d6af52f8d7b1', 'value': {'distribution': []}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['esx_vsphere_objects_count']


checkgroup_parameters.setdefault('esx_vsphere_vm_memory', [])

checkgroup_parameters['esx_vsphere_vm_memory'] = [
{'id': 'eccb173b-bb72-43bf-934f-29d78cdda6a3', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['esx_vsphere_vm_memory']


checkgroup_parameters.setdefault('etherbox_smoke', [])

checkgroup_parameters['etherbox_smoke'] = [
{'id': '21011781-3044-4f0c-89fd-4ab41dbf00d4', 'value': {'smoke_handling': ('binary', (0, 0))}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['etherbox_smoke']


checkgroup_parameters.setdefault('etherbox_voltage', [])

checkgroup_parameters['etherbox_voltage'] = [
{'id': 'e02c98f0-f538-4f40-8155-463265ee4ed6', 'value': {'levels': ('fixed', (0.0, 0.0))}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['etherbox_voltage']


checkgroup_parameters.setdefault('evolt', [])

checkgroup_parameters['evolt'] = [
{'id': '17cb1b21-37bd-4c86-abaa-43d7268b616d', 'value': {'levels_lower': (210.0, 180.0)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['evolt']


checkgroup_parameters.setdefault('ewon', [])

checkgroup_parameters['ewon'] = [
{'id': '479a181c-26a5-4ea3-a44f-a0188c8ae0f1', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['ewon']


checkgroup_parameters.setdefault('f5_bigip_cluster_v11', [])

checkgroup_parameters['f5_bigip_cluster_v11'] = [
{'id': 'bf16f55f-e70a-426d-9122-28d2d573c042', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['f5_bigip_cluster_v11']


checkgroup_parameters.setdefault('f5_bigip_snat', [])

checkgroup_parameters['f5_bigip_snat'] = [
{'id': 'a4c13c6b-0e9e-456d-ab29-0cb34c4c2daf', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['f5_bigip_snat']


checkgroup_parameters.setdefault('f5_bigip_vserver', [])

checkgroup_parameters['f5_bigip_vserver'] = [
{'id': 'ba0a9063-e9cd-4ae3-a030-a355a7eee478', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['f5_bigip_vserver']


checkgroup_parameters.setdefault('f5_connections', [])

checkgroup_parameters['f5_connections'] = [
{'id': 'f76bda5c-7ffe-42f1-99b6-e637c4ab8987', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['f5_connections']


checkgroup_parameters.setdefault('f5_pools', [])

checkgroup_parameters['f5_pools'] = [
{'id': '9f7c3cd7-2fe3-46ff-af62-6a6e1ee53db9', 'value': {'levels_lower': ('fixed', (2, 1))}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['f5_pools']


checkgroup_parameters.setdefault('fan_failures', [])

checkgroup_parameters['fan_failures'] = [
{'id': '604d624d-97ff-4d9e-8ba1-628e3a2f16a3', 'value': {'levels': None}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['fan_failures']


checkgroup_parameters.setdefault('fc_port', [])

checkgroup_parameters['fc_port'] = [
{'id': 'd5972b81-df09-41aa-9e94-4595c597d445', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['fc_port']


checkgroup_parameters.setdefault('fcp', [])

checkgroup_parameters['fcp'] = [
{'id': 'dffe108b-2d53-4263-892d-228c486323c9', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['fcp']


checkgroup_parameters.setdefault('fcport_words', [])

checkgroup_parameters['fcport_words'] = [
{'id': '681db607-6e7f-45a4-965d-8e5646483178', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['fcport_words']


checkgroup_parameters.setdefault('filehandler', [])

checkgroup_parameters['filehandler'] = [
{'id': '999d7755-be06-446a-baf4-7b63d0eb4bbe', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['filehandler']


checkgroup_parameters.setdefault('fileinfo', [])

checkgroup_parameters['fileinfo'] = [
{'id': '393dac5f-3855-492f-89e1-e4e75c616797', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['fileinfo']


checkgroup_parameters.setdefault('fileinfo_groups_checking', [])

checkgroup_parameters['fileinfo_groups_checking'] = [
{'id': '8b10e874-51df-4968-b6fb-9da36ab52b91', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['fileinfo_groups_checking']


checkgroup_parameters.setdefault('filestats', [])

checkgroup_parameters['filestats'] = [
{'id': '12641010-e0bb-4b05-967a-128781030cc5', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['filestats']


checkgroup_parameters.setdefault('filestats_single', [])

checkgroup_parameters['filestats_single'] = [
{'id': '1bb4c120-8a02-437e-950c-f245c18b6c44', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['filestats_single']


checkgroup_parameters.setdefault('filesystem', [])

checkgroup_parameters['filesystem'] = [
{'id': '465ba363-1e96-48ac-bff2-5ea22826a9a0', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['filesystem']


checkgroup_parameters.setdefault('fireeye_active_vms', [])

checkgroup_parameters['fireeye_active_vms'] = [
{'id': '91f0c6d3-5a2e-4c16-a871-c59b8c46329d', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['fireeye_active_vms']


checkgroup_parameters.setdefault('fireeye_content', [])

checkgroup_parameters['fireeye_content'] = [
{'id': 'ebd8127e-452e-464b-8674-0420a7018840', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['fireeye_content']


checkgroup_parameters.setdefault('fireeye_lic', [])

checkgroup_parameters['fireeye_lic'] = [
{'id': '9410e471-8f3a-416b-926f-3978e0058056', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['fireeye_lic']


checkgroup_parameters.setdefault('fireeye_mail', [])

checkgroup_parameters['fireeye_mail'] = [
{'id': '6b5c219b-a8be-40b9-afa9-6432af8ee8e7', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['fireeye_mail']


checkgroup_parameters.setdefault('fireeye_mailq', [])

checkgroup_parameters['fireeye_mailq'] = [
{'id': '4db80148-3d5f-45df-b0a6-9ebc7f3e4a5a', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['fireeye_mailq']


checkgroup_parameters.setdefault('fireeye_quarantine', [])

checkgroup_parameters['fireeye_quarantine'] = [
{'id': '884bc4d9-c64a-4764-b205-00b812fe22ca', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['fireeye_quarantine']


checkgroup_parameters.setdefault('firewall_if', [])

checkgroup_parameters['firewall_if'] = [
{'id': '90162fdc-5f9e-4771-80f7-ecd6b6357097', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['firewall_if']


checkgroup_parameters.setdefault('fortiauthenticator_auth_fail', [])

checkgroup_parameters['fortiauthenticator_auth_fail'] = [
{'id': 'f40e5eb6-5727-475b-8150-c6a73e7963bc', 'value': {'auth_fails': (100, 200)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['fortiauthenticator_auth_fail']


checkgroup_parameters.setdefault('fortigate_antivirus', [])

checkgroup_parameters['fortigate_antivirus'] = [
{'id': 'b3213874-6b97-459c-8cd6-00c3ff5b0353', 'value': {'detections': (100.0, 300.0)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['fortigate_antivirus']


checkgroup_parameters.setdefault('fortigate_ips', [])

checkgroup_parameters['fortigate_ips'] = [
{'id': '28921966-a8f6-4d7e-b689-0097e8a60ddd', 'value': {'detections': (100.0, 300.0)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['fortigate_ips']


checkgroup_parameters.setdefault('fortigate_node_memory', [])

checkgroup_parameters['fortigate_node_memory'] = [
{'id': 'fc4810f5-377a-4884-8032-d58d8a9debc3', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['fortigate_node_memory']


checkgroup_parameters.setdefault('fortigate_node_sessions', [])

checkgroup_parameters['fortigate_node_sessions'] = [
{'id': 'c7c902e9-cd93-44ab-aa31-5b9ff0dec8d7', 'value': {'levels': None}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['fortigate_node_sessions']


checkgroup_parameters.setdefault('fortigate_sessions', [])

checkgroup_parameters['fortigate_sessions'] = [
{'id': 'bd35a7e8-5417-4045-92d6-fd4628349a5e', 'value': {'levels': None}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['fortigate_sessions']


checkgroup_parameters.setdefault('fortigate_sslvpn', [])

checkgroup_parameters['fortigate_sslvpn'] = [
{'id': 'ef045620-ccd1-48ae-93c5-78c68803e603', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['fortigate_sslvpn']


checkgroup_parameters.setdefault('fortimail_cpu_load', [])

checkgroup_parameters['fortimail_cpu_load'] = [
{'id': '5876ce69-9134-495a-89bc-0988468a7ebf', 'value': {'cpu_load': None}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['fortimail_cpu_load']


checkgroup_parameters.setdefault('fortimail_disk_usage', [])

checkgroup_parameters['fortimail_disk_usage'] = [
{'id': '8ce9dcf5-bccc-48ab-9905-8a10246f35c6', 'value': {'disk_usage': (80.0, 90.0)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['fortimail_disk_usage']


checkgroup_parameters.setdefault('fortimail_queue', [])

checkgroup_parameters['fortimail_queue'] = [
{'id': 'ed069ed3-b6bd-4a96-b6be-99dc33cc3e5a', 'value': {'queue_length': (100, 200)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['fortimail_queue']


checkgroup_parameters.setdefault('fortinet_signatures', [])

checkgroup_parameters['fortinet_signatures'] = [
{'id': '42d1bb6c-d830-4226-be16-59ae9bcb43a5', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['fortinet_signatures']


checkgroup_parameters.setdefault('fortisandbox_queues', [])

checkgroup_parameters['fortisandbox_queues'] = [
{'id': '660ac54b-702b-449a-bb3b-8d01991467b6', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['fortisandbox_queues']


checkgroup_parameters.setdefault('fpga_utilization', [])

checkgroup_parameters['fpga_utilization'] = [
{'id': '6c4b2dbf-35a2-411d-aae8-d4807e0d97d1', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['fpga_utilization']


checkgroup_parameters.setdefault('fs_mount_options', [])

checkgroup_parameters['fs_mount_options'] = [
{'id': '38b64904-9999-4327-af17-e4fc93ba4250', 'value': {'expected_mount_options': []}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['fs_mount_options']


checkgroup_parameters.setdefault('gcp_cost', [])

checkgroup_parameters['gcp_cost'] = [
{'id': '239e5f72-7e6c-45e3-8553-ebec643d453b', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['gcp_cost']


checkgroup_parameters.setdefault('gcp_filestore_disk', [])

checkgroup_parameters['gcp_filestore_disk'] = [
{'id': 'c590d838-3207-4d92-9759-eaeb00155cfb', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['gcp_filestore_disk']


checkgroup_parameters.setdefault('gcp_gce_cpu', [])

checkgroup_parameters['gcp_gce_cpu'] = [
{'id': '2158522a-2656-4064-8381-69aa9036ca1b', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['gcp_gce_cpu']


checkgroup_parameters.setdefault('gcp_gce_disk', [])

checkgroup_parameters['gcp_gce_disk'] = [
{'id': '963e9825-2edc-4a1d-a713-753411d90cbf', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['gcp_gce_disk']


checkgroup_parameters.setdefault('gcp_gce_storage', [])

checkgroup_parameters['gcp_gce_storage'] = [
{'id': 'f3fd4940-ee37-44e0-aac0-a7f1ad025c57', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['gcp_gce_storage']


checkgroup_parameters.setdefault('gcp_gcs_network', [])

checkgroup_parameters['gcp_gcs_network'] = [
{'id': '25819a1c-e1b1-4a84-83ae-903ed27d6409', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['gcp_gcs_network']


checkgroup_parameters.setdefault('gcp_gcs_objects', [])

checkgroup_parameters['gcp_gcs_objects'] = [
{'id': 'c6e925c6-d886-478b-9203-e82efbdda335', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['gcp_gcs_objects']


checkgroup_parameters.setdefault('gcp_gcs_requests', [])

checkgroup_parameters['gcp_gcs_requests'] = [
{'id': 'acd27b91-2071-4a40-a04d-e1c0a3a37c23', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['gcp_gcs_requests']


checkgroup_parameters.setdefault('gcp_http_lb_latencies', [])

checkgroup_parameters['gcp_http_lb_latencies'] = [
{'id': 'e611fa4d-0b8c-4486-9b1d-7d47c1554aa9', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['gcp_http_lb_latencies']


checkgroup_parameters.setdefault('gcp_http_lb_requests', [])

checkgroup_parameters['gcp_http_lb_requests'] = [
{'id': '371bfa29-700c-4dfe-9fd1-05028c3d15b4', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['gcp_http_lb_requests']


checkgroup_parameters.setdefault('gcp_replication_lag', [])

checkgroup_parameters['gcp_replication_lag'] = [
{'id': '2de2e664-f850-4d81-aa7d-3e6cae454e0c', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['gcp_replication_lag']


checkgroup_parameters.setdefault('gcp_sql_cpu', [])

checkgroup_parameters['gcp_sql_cpu'] = [
{'id': 'd3870394-ba16-458b-8733-1af69dfdd75c', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['gcp_sql_cpu']


checkgroup_parameters.setdefault('gcp_sql_disk', [])

checkgroup_parameters['gcp_sql_disk'] = [
{'id': '1cbe8fdf-95ca-474e-b2e2-60214658cf81', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['gcp_sql_disk']


checkgroup_parameters.setdefault('gcp_sql_memory', [])

checkgroup_parameters['gcp_sql_memory'] = [
{'id': '9c849979-1da7-4853-b74d-05bc6716adcd', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['gcp_sql_memory']


checkgroup_parameters.setdefault('gcp_sql_network', [])

checkgroup_parameters['gcp_sql_network'] = [
{'id': 'd5fe3577-7dfd-4579-a579-c33044bcdc1e', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['gcp_sql_network']


checkgroup_parameters.setdefault('gcp_sql_status', [])

checkgroup_parameters['gcp_sql_status'] = [
{'id': 'a5053859-8c8b-4bf1-b2c3-f6ed07d5affe', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['gcp_sql_status']


checkgroup_parameters.setdefault('general_flash_usage', [])

checkgroup_parameters['general_flash_usage'] = [
{'id': '71dd98e7-b0fb-4d13-b755-7dcc5358ca67', 'value': {'levels': (0.0, 0.0)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['general_flash_usage']


checkgroup_parameters.setdefault('generic_number', [])

checkgroup_parameters['generic_number'] = [
{'id': 'e0daea92-1621-433b-ab9f-90ee05599db7', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['generic_number']


checkgroup_parameters.setdefault('generic_percentage_value', [])

checkgroup_parameters['generic_percentage_value'] = [
{'id': 'e36d15a6-822c-4a08-b751-6b645844f733', 'value': {'upper_levels': ('fixed', (0.0, 0.0))}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['generic_percentage_value']


checkgroup_parameters.setdefault('generic_rate', [])

checkgroup_parameters['generic_rate'] = [
{'id': '7534bc91-7f8f-4d22-b9e7-0898ec28356a', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['generic_rate']


checkgroup_parameters.setdefault('generic_string', [])

checkgroup_parameters['generic_string'] = [
{'id': '255c090d-2bb4-40e0-8efc-84f7e987d19b', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['generic_string']


checkgroup_parameters.setdefault('gerrit_version', [])

checkgroup_parameters['gerrit_version'] = [
{'id': '550b9468-0d99-48d1-a616-b946ced7810d', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['gerrit_version']


checkgroup_parameters.setdefault('globalprotect_utilization', [])

checkgroup_parameters['globalprotect_utilization'] = [
{'id': '8bd5ba4c-d7f5-412c-8ce3-ab4a3959ad70', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['globalprotect_utilization']


checkgroup_parameters.setdefault('graylog_alerts', [])

checkgroup_parameters['graylog_alerts'] = [
{'id': '7fb19c52-66ab-4de1-b9ea-aebadd99cae6', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['graylog_alerts']


checkgroup_parameters.setdefault('graylog_cluster_stats', [])

checkgroup_parameters['graylog_cluster_stats'] = [
{'id': 'f05fc473-c70a-41e4-bb62-8f7ca0035977', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['graylog_cluster_stats']


checkgroup_parameters.setdefault('graylog_cluster_stats_elastic', [])

checkgroup_parameters['graylog_cluster_stats_elastic'] = [
{'id': '150170ad-f341-4f07-8325-6e9f30bf5b2f', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['graylog_cluster_stats_elastic']


checkgroup_parameters.setdefault('graylog_cluster_stats_mongodb', [])

checkgroup_parameters['graylog_cluster_stats_mongodb'] = [
{'id': '98710653-c393-4f74-a876-dcbb965072ee', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['graylog_cluster_stats_mongodb']


checkgroup_parameters.setdefault('graylog_cluster_traffic', [])

checkgroup_parameters['graylog_cluster_traffic'] = [
{'id': '247c0fc7-71b9-4a0e-b15d-158aa83f2b76', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['graylog_cluster_traffic']


checkgroup_parameters.setdefault('graylog_events', [])

checkgroup_parameters['graylog_events'] = [
{'id': '64870c28-06ad-42f2-b4d0-a08245f3ba66', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['graylog_events']


checkgroup_parameters.setdefault('graylog_failures', [])

checkgroup_parameters['graylog_failures'] = [
{'id': '21e583cb-6dda-4e0b-abf0-aa52d2d1a158', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['graylog_failures']


checkgroup_parameters.setdefault('graylog_jvm', [])

checkgroup_parameters['graylog_jvm'] = [
{'id': '549a837f-6b01-4fcc-8a66-15df59306f16', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['graylog_jvm']


checkgroup_parameters.setdefault('graylog_license', [])

checkgroup_parameters['graylog_license'] = [
{'id': '8f4fef25-d100-4c1e-9277-f86ee9e250fb', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['graylog_license']


checkgroup_parameters.setdefault('graylog_messages', [])

checkgroup_parameters['graylog_messages'] = [
{'id': 'ec460b40-e02c-4f9d-ae61-c7483a7c24ee', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['graylog_messages']


checkgroup_parameters.setdefault('graylog_nodes', [])

checkgroup_parameters['graylog_nodes'] = [
{'id': '0d94fe91-1687-457b-bc10-80b4ed2e1c6b', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['graylog_nodes']


checkgroup_parameters.setdefault('graylog_sidecars', [])

checkgroup_parameters['graylog_sidecars'] = [
{'id': 'efe49e5d-f5bf-458f-912f-a3840574db62', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['graylog_sidecars']


checkgroup_parameters.setdefault('graylog_sources', [])

checkgroup_parameters['graylog_sources'] = [
{'id': '5f749a16-4bfe-4011-a637-0548c765fa6e', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['graylog_sources']


checkgroup_parameters.setdefault('graylog_streams', [])

checkgroup_parameters['graylog_streams'] = [
{'id': 'f59dc4e8-9908-4166-8a5b-1895aee7c0bf', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['graylog_streams']


checkgroup_parameters.setdefault('hacmp_resources', [])

checkgroup_parameters['hacmp_resources'] = [
{'id': 'b3a58d03-6bbd-4ada-8614-bd64e892ec2a', 'value': {'expect_online_on': 'first'}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['hacmp_resources']


checkgroup_parameters.setdefault('haproxy_frontend', [])

checkgroup_parameters['haproxy_frontend'] = [
{'id': '64ea05b3-c64e-48e2-8493-e469241b73a6', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['haproxy_frontend']


checkgroup_parameters.setdefault('haproxy_server', [])

checkgroup_parameters['haproxy_server'] = [
{'id': 'b3c9a826-0764-44c3-830a-706658f29392', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['haproxy_server']


checkgroup_parameters.setdefault('heartbeat_crm', [])

checkgroup_parameters['heartbeat_crm'] = [
{'id': '033aacd8-edc8-4b24-8b85-683832c06287', 'value': {'max_age': 60}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['heartbeat_crm']


checkgroup_parameters.setdefault('heartbeat_crm_resources', [])

checkgroup_parameters['heartbeat_crm_resources'] = [
{'id': 'c87017f1-61ff-408b-a76c-a21b9d42bee6', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['heartbeat_crm_resources']


checkgroup_parameters.setdefault('heartbeat_rscstatus', [])

checkgroup_parameters['heartbeat_rscstatus'] = [
{'id': '007fef70-385a-47a3-9b89-aedb29a4b3a6', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['heartbeat_rscstatus']


checkgroup_parameters.setdefault('hivemanager_devices', [])

checkgroup_parameters['hivemanager_devices'] = [
{'id': '76cc7a4f-6d0a-45b5-8637-364555b8967c', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['hivemanager_devices']


checkgroup_parameters.setdefault('hivemanager_ng_devices', [])

checkgroup_parameters['hivemanager_ng_devices'] = [
{'id': '5dce87ee-13ac-454b-aa91-3058257469e2', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['hivemanager_ng_devices']


checkgroup_parameters.setdefault('hostsystem_sensors', [])

checkgroup_parameters['hostsystem_sensors'] = [
{'id': 'ff803d5c-483f-473c-a180-cd72e74100fd', 'value': {'rules': []}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['hostsystem_sensors']


checkgroup_parameters.setdefault('hp_hh3c_ext_states', [])

checkgroup_parameters['hp_hh3c_ext_states'] = [
{'id': '809d348b-7340-4df5-b773-9869bf812da7', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['hp_hh3c_ext_states']


checkgroup_parameters.setdefault('hp_msa_psu_voltage', [])

checkgroup_parameters['hp_msa_psu_voltage'] = [
{'id': '7fa7f1d7-ffe2-43bf-892c-6d40ed6eb495', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['hp_msa_psu_voltage']


checkgroup_parameters.setdefault('hpux_multipath', [])

checkgroup_parameters['hpux_multipath'] = [
{'id': 'ade45f5f-8967-40d4-9fd1-67ad3b7f66f0', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['hpux_multipath']


checkgroup_parameters.setdefault('hr_ps', [])

checkgroup_parameters['hr_ps'] = [
{'id': '66db34bd-b267-4b51-8e39-bd4d2d3b09f5', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['hr_ps']


checkgroup_parameters.setdefault('huawei_osn_laser', [])

checkgroup_parameters['huawei_osn_laser'] = [
{'id': '33915401-8ea3-4fcb-a803-c1428bad39ff', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['huawei_osn_laser']


checkgroup_parameters.setdefault('humidity', [])

checkgroup_parameters['humidity'] = [
{'id': '9172e0fe-0f50-458a-8358-3404bd6683ea', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['humidity']


checkgroup_parameters.setdefault('hw_fans', [])

checkgroup_parameters['hw_fans'] = [
{'id': '87421ae9-5460-4d8e-987b-447ed3512feb', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['hw_fans']


checkgroup_parameters.setdefault('hw_fans_perc', [])

checkgroup_parameters['hw_fans_perc'] = [
{'id': 'd4f3fc72-a78e-4645-ab9d-b2b7f11d1980', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['hw_fans_perc']


checkgroup_parameters.setdefault('hw_psu', [])

checkgroup_parameters['hw_psu'] = [
{'id': 'e9835cde-8740-4970-803b-5b92ac9d6b16', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['hw_psu']


checkgroup_parameters.setdefault('hyperv_vm_checkpoints', [])

checkgroup_parameters['hyperv_vm_checkpoints'] = [
{'id': '3dab6b81-3b7f-4f56-b663-001c44cee45a', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['hyperv_vm_checkpoints']


checkgroup_parameters.setdefault('hyperv_vm_general', [])

checkgroup_parameters['hyperv_vm_general'] = [
{'id': 'dd1e1ac5-20d7-48d2-8a29-bf92b6fda97f', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['hyperv_vm_general']


checkgroup_parameters.setdefault('hyperv_vm_integration', [])

checkgroup_parameters['hyperv_vm_integration'] = [
{'id': 'e74ca7ed-5ef4-415f-9810-e1b103cd438b', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['hyperv_vm_integration']


checkgroup_parameters.setdefault('hyperv_vm_nic', [])

checkgroup_parameters['hyperv_vm_nic'] = [
{'id': '6b78ed53-b638-4400-9a7a-b5def75f5b63', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['hyperv_vm_nic']


checkgroup_parameters.setdefault('hyperv_vm_ram', [])

checkgroup_parameters['hyperv_vm_ram'] = [
{'id': 'cbff625e-a7d5-46c8-9bba-d2a8f001a0f3', 'value': {'max_ram': ('fixed', (0.0, 0.0)), 'min_ram': ('fixed', (0.0, 0.0)), 'check_demand': False}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['hyperv_vm_ram']


checkgroup_parameters.setdefault('hyperv_vm_vhd', [])

checkgroup_parameters['hyperv_vm_vhd'] = [
{'id': '87581e8f-6176-4ee1-a1f1-2bd249f334ba', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['hyperv_vm_vhd']


checkgroup_parameters.setdefault('hyperv_vms', [])

checkgroup_parameters['hyperv_vms'] = [
{'id': '462336d7-a5d2-411c-846c-9d199a31b738', 'value': {'vm_target_state': ('map', {})}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['hyperv_vms']


checkgroup_parameters.setdefault('ibm_mq_channels', [])

checkgroup_parameters['ibm_mq_channels'] = [
{'id': 'f274aa20-edb0-4343-b6f9-e21026674525', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['ibm_mq_channels']


checkgroup_parameters.setdefault('ibm_mq_managers', [])

checkgroup_parameters['ibm_mq_managers'] = [
{'id': '67f72ccf-319b-4915-bb27-fec05ffba803', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['ibm_mq_managers']


checkgroup_parameters.setdefault('ibm_mq_plugin', [])

checkgroup_parameters['ibm_mq_plugin'] = [
{'id': '3989f0d2-ae3c-4d0d-aa2d-3fe85cc41ec3', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['ibm_mq_plugin']


checkgroup_parameters.setdefault('ibm_mq_queues', [])

checkgroup_parameters['ibm_mq_queues'] = [
{'id': 'd9f2ea49-0ff2-4bd6-9c96-bdfc4b5e71ce', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['ibm_mq_queues']


checkgroup_parameters.setdefault('ibm_svc_enclosure', [])

checkgroup_parameters['ibm_svc_enclosure'] = [
{'id': 'e5723fa4-ab63-41ce-b505-a18cd215077b', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['ibm_svc_enclosure']


checkgroup_parameters.setdefault('ibm_svc_host', [])

checkgroup_parameters['ibm_svc_host'] = [
{'id': 'c5e110dc-7dfb-4a91-8beb-0a32943d15e7', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['ibm_svc_host']


checkgroup_parameters.setdefault('ibm_svc_mdisk', [])

checkgroup_parameters['ibm_svc_mdisk'] = [
{'id': '9a05a2ad-4b23-4d36-bb7f-10c70ba9d8c4', 'value': {'online_state': 0, 'degraded_state': 1, 'offline_state': 2, 'excluded_state': 2, 'managed_mode': 0, 'array_mode': 0, 'image_mode': 0, 'unmanaged_mode': 1}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['ibm_svc_mdisk']


checkgroup_parameters.setdefault('ibm_svc_mdiskgrp', [])

checkgroup_parameters['ibm_svc_mdiskgrp'] = [
{'id': '0d5f0ed0-2457-4b01-b4ac-9b140025c59f', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['ibm_svc_mdiskgrp']


checkgroup_parameters.setdefault('ibm_svc_total_latency', [])

checkgroup_parameters['ibm_svc_total_latency'] = [
{'id': '53e91745-ac95-4758-8aeb-9bbad0b114e6', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['ibm_svc_total_latency']


checkgroup_parameters.setdefault('ibmsvc_licenses', [])

checkgroup_parameters['ibmsvc_licenses'] = [
{'id': 'ef8ded51-68ac-492a-90bc-94e1409e592f', 'value': {'levels': ('crit_on_all', None)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['ibmsvc_licenses']


checkgroup_parameters.setdefault('iis_app_pool_state', [])

checkgroup_parameters['iis_app_pool_state'] = [
{'id': '5edceffd-d9b5-4c5b-a8f5-7e35ada424c3', 'value': {'state_mapping': {'Uninitialized': 2, 'Initialized': 1, 'Running': 0, 'Disabling': 2, 'Disabled': 2, 'ShutdownPending': 2, 'DeletePending': 2}}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['iis_app_pool_state']


checkgroup_parameters.setdefault('informix_dbspaces', [])

checkgroup_parameters['informix_dbspaces'] = [
{'id': '0c1d9332-46ea-44e7-8462-34aecc1932cf', 'value': {'levels': ('no_levels', None), 'levels_perc': ('fixed', (80.0, 85.0))}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['informix_dbspaces']


checkgroup_parameters.setdefault('informix_locks', [])

checkgroup_parameters['informix_locks'] = [
{'id': '9bf80e10-3240-4a65-875d-81fa41fec324', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['informix_locks']


checkgroup_parameters.setdefault('informix_logusage', [])

checkgroup_parameters['informix_logusage'] = [
{'id': 'dadbd664-1a23-4c5c-8b3d-a72cfeb9faf9', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['informix_logusage']


checkgroup_parameters.setdefault('informix_sessions', [])

checkgroup_parameters['informix_sessions'] = [
{'id': 'd725363e-f93f-4033-8188-9cd49d873b7e', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['informix_sessions']


checkgroup_parameters.setdefault('informix_tabextents', [])

checkgroup_parameters['informix_tabextents'] = [
{'id': '4f3a88a3-c8a2-4f4f-b1dc-baf297493923', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['informix_tabextents']


checkgroup_parameters.setdefault('innovaphone_mem', [])

checkgroup_parameters['innovaphone_mem'] = [
{'id': 'a3556f10-b3a7-4722-a073-3c510e708820', 'value': {'levels': None}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['innovaphone_mem']


checkgroup_parameters.setdefault('inotify', [])

checkgroup_parameters['inotify'] = [
{'id': '9074a809-cff7-4f58-9284-18f9d3346297', 'value': {'age_last_operation': []}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['inotify']


checkgroup_parameters.setdefault('interfaces', [])

checkgroup_parameters['interfaces'] = [
{'id': '556b0b5c-c85d-4c36-9069-56ac275cf630', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['interfaces']


checkgroup_parameters.setdefault('ipmi', [])

checkgroup_parameters['ipmi'] = [
{'id': 'e6e57d4d-2bc7-4598-96c9-3f231afdc455', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['ipmi']


checkgroup_parameters.setdefault('ipsecvpn', [])

checkgroup_parameters['ipsecvpn'] = [
{'id': '03f93fe4-8097-41e7-9397-b9915de6b77f', 'value': {'levels': (1, 2), 'tunnels_ignore_levels': []}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['ipsecvpn']


checkgroup_parameters.setdefault('jenkins_jobs', [])

checkgroup_parameters['jenkins_jobs'] = [
{'id': 'e5ef308f-eb20-4e3a-b065-7d553e308230', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['jenkins_jobs']


checkgroup_parameters.setdefault('jenkins_nodes', [])

checkgroup_parameters['jenkins_nodes'] = [
{'id': 'aad5a944-6373-43a3-8e35-b64010997e5b', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['jenkins_nodes']


checkgroup_parameters.setdefault('jenkins_queue', [])

checkgroup_parameters['jenkins_queue'] = [
{'id': 'd698b2e4-3712-4a04-901c-2e0561910f0f', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['jenkins_queue']


checkgroup_parameters.setdefault('jenkins_system_metrics', [])

checkgroup_parameters['jenkins_system_metrics'] = [
{'id': '5747a3e0-56a6-47d5-989e-6663dcc5f3dc', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['jenkins_system_metrics']


checkgroup_parameters.setdefault('jira_custom_svc', [])

checkgroup_parameters['jira_custom_svc'] = [
{'id': '31c646fd-b61f-4c83-9f1e-1126fd200ea1', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['jira_custom_svc']


checkgroup_parameters.setdefault('jira_workflow', [])

checkgroup_parameters['jira_workflow'] = [
{'id': '7cc6cb84-f211-425a-80e4-6b3e306685d8', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['jira_workflow']


checkgroup_parameters.setdefault('job', [])

checkgroup_parameters['job'] = [
{'id': 'f4fd4e9e-f3cc-4264-919d-553bf2cc4fb0', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['job']


checkgroup_parameters.setdefault('juniper_alarms', [])

checkgroup_parameters['juniper_alarms'] = [
{'id': '445b6850-febc-426e-8263-67c18e0b5c9b', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['juniper_alarms']


checkgroup_parameters.setdefault('juniper_cpu_util', [])

checkgroup_parameters['juniper_cpu_util'] = [
{'id': 'ae91f700-0f37-4f25-808b-bf1f739c8b13', 'value': {'levels': (80.0, 90.0)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['juniper_cpu_util']


checkgroup_parameters.setdefault('juniper_mem', [])

checkgroup_parameters['juniper_mem'] = [
{'id': 'ed2685af-ee51-492c-9681-3c9a609adafc', 'value': {'levels': ('perc_used', (80.0, 90.0))}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['juniper_mem']


checkgroup_parameters.setdefault('juniper_mem_modules', [])

checkgroup_parameters['juniper_mem_modules'] = [
{'id': '273843ab-1efa-46e3-b9b4-b4d8c9e208f0', 'value': {'levels': None}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['juniper_mem_modules']


checkgroup_parameters.setdefault('jvm_gc', [])

checkgroup_parameters['jvm_gc'] = [
{'id': '4a7298b7-ffb7-4577-9094-8b4c4ef22652', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['jvm_gc']


checkgroup_parameters.setdefault('jvm_memory', [])

checkgroup_parameters['jvm_memory'] = [
{'id': '00a67f2f-d107-45f9-8c2d-153742fb0f56', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['jvm_memory']


checkgroup_parameters.setdefault('jvm_memory_pools', [])

checkgroup_parameters['jvm_memory_pools'] = [
{'id': 'dfb3d119-4271-4b2d-8a78-8739afbba16d', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['jvm_memory_pools']


checkgroup_parameters.setdefault('jvm_queue', [])

checkgroup_parameters['jvm_queue'] = [
{'id': '46a02733-f494-47d6-ab87-3582084c964c', 'value': {'levels': None}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['jvm_queue']


checkgroup_parameters.setdefault('jvm_requests', [])

checkgroup_parameters['jvm_requests'] = [
{'id': '72c20312-b0bb-4961-84f0-e124e1f3e012', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['jvm_requests']


checkgroup_parameters.setdefault('jvm_sessions', [])

checkgroup_parameters['jvm_sessions'] = [
{'id': 'feb380c7-5828-44c9-9380-abeb4d962eb4', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['jvm_sessions']


checkgroup_parameters.setdefault('jvm_threading', [])

checkgroup_parameters['jvm_threading'] = [
{'id': '01f65425-af79-4b54-aa03-9d3ce3e2f966', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['jvm_threading']


checkgroup_parameters.setdefault('jvm_tp', [])

checkgroup_parameters['jvm_tp'] = [
{'id': '8e0af932-4614-4a89-b390-abefec562482', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['jvm_tp']


checkgroup_parameters.setdefault('jvm_uptime', [])

checkgroup_parameters['jvm_uptime'] = [
{'id': '6ecc23f4-8185-4b77-bcdb-adc39ec41841', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['jvm_uptime']


checkgroup_parameters.setdefault('kaspersky_av_client', [])

checkgroup_parameters['kaspersky_av_client'] = [
{'id': '66b74419-34f5-44c9-91ac-17231ea1c020', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['kaspersky_av_client']


checkgroup_parameters.setdefault('keepalived', [])

checkgroup_parameters['keepalived'] = [
{'id': 'e04bb920-b596-44f7-9b4b-3dc97eba1e1c', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['keepalived']


checkgroup_parameters.setdefault('kernel_performance', [])

checkgroup_parameters['kernel_performance'] = [
{'id': '2400287a-1f1b-430f-a827-8aa1290b5e95', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['kernel_performance']


checkgroup_parameters.setdefault('kube_collector_info', [])

checkgroup_parameters['kube_collector_info'] = [
{'id': '3e8a392b-25e6-4fa9-abdf-d37aeb497a7e', 'value': {'machine_metrics': 2}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['kube_collector_info']


checkgroup_parameters.setdefault('kube_cpu', [])

checkgroup_parameters['kube_cpu'] = [
{'id': '5a83608b-8ef2-41a7-90b1-cc5b4e773ba9', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['kube_cpu']


checkgroup_parameters.setdefault('kube_cronjob_status', [])

checkgroup_parameters['kube_cronjob_status'] = [
{'id': 'd317a4d7-c732-4405-a7f5-0c072e97bc93', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['kube_cronjob_status']


checkgroup_parameters.setdefault('kube_deployment_conditions', [])

checkgroup_parameters['kube_deployment_conditions'] = [
{'id': '93d35e63-85ce-4db4-85a5-1631e3d85a97', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['kube_deployment_conditions']


checkgroup_parameters.setdefault('kube_memory', [])

checkgroup_parameters['kube_memory'] = [
{'id': '2665208f-a3c2-4291-b054-6c4c372fe62b', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['kube_memory']


checkgroup_parameters.setdefault('kube_node_conditions', [])

checkgroup_parameters['kube_node_conditions'] = [
{'id': 'c9f651ef-1c68-4262-90a3-966d78387c49', 'value': {'conditions': []}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['kube_node_conditions']


checkgroup_parameters.setdefault('kube_node_container_count', [])

checkgroup_parameters['kube_node_container_count'] = [
{'id': '614f332b-8a28-4a03-85f2-89216fb67d9d', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['kube_node_container_count']


checkgroup_parameters.setdefault('kube_node_count', [])

checkgroup_parameters['kube_node_count'] = [
{'id': 'd88a5004-5120-49be-b3d7-0d2bc006bb51', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['kube_node_count']


checkgroup_parameters.setdefault('kube_pod_conditions', [])

checkgroup_parameters['kube_pod_conditions'] = [
{'id': 'f613aef4-8ccd-40ff-abd2-c33787118133', 'value': {'hasnetwork': 'no_levels'}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['kube_pod_conditions']


checkgroup_parameters.setdefault('kube_pod_containers', [])

checkgroup_parameters['kube_pod_containers'] = [
{'id': 'aa051c40-77c1-488f-b41b-8161f81ad7b6', 'value': {'failed_state': 2}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['kube_pod_containers']


checkgroup_parameters.setdefault('kube_pod_resources', [])

checkgroup_parameters['kube_pod_resources'] = [
{'id': 'dade9089-1dfa-4ace-ba3c-83e187102a24', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['kube_pod_resources']


checkgroup_parameters.setdefault('kube_pod_restarts', [])

checkgroup_parameters['kube_pod_restarts'] = [
{'id': '493ed01d-8741-4b0a-8460-e981c6919d76', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['kube_pod_restarts']


checkgroup_parameters.setdefault('kube_pod_status', [])

checkgroup_parameters['kube_pod_status'] = [
{'id': 'd93714ea-4ce1-4392-983d-564bede7bb39', 'value': {'groups': []}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['kube_pod_status']


checkgroup_parameters.setdefault('kube_pvc', [])

checkgroup_parameters['kube_pvc'] = [
{'id': '523af2a4-1bf7-4ce2-b6eb-b89075b0bfff', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['kube_pvc']


checkgroup_parameters.setdefault('kube_replicas', [])

checkgroup_parameters['kube_replicas'] = [
{'id': 'a7675055-9482-4758-8a44-4de84f4398ec', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['kube_replicas']


checkgroup_parameters.setdefault('kube_resource_quota_cpu', [])

checkgroup_parameters['kube_resource_quota_cpu'] = [
{'id': 'da265364-024d-4cce-80cf-a596253f87a9', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['kube_resource_quota_cpu']


checkgroup_parameters.setdefault('kube_resource_quota_memory', [])

checkgroup_parameters['kube_resource_quota_memory'] = [
{'id': '8b1e264b-e257-42fa-b062-c4637880a1cd', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['kube_resource_quota_memory']


checkgroup_parameters.setdefault('lamp_operation_time', [])

checkgroup_parameters['lamp_operation_time'] = [
{'id': '86223ebe-6976-4275-bec8-e6c3b908173f', 'value': {'levels': (3600000, 5400000)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['lamp_operation_time']


checkgroup_parameters.setdefault('liebert_cooling', [])

checkgroup_parameters['liebert_cooling'] = [
{'id': '1daabe20-3604-4629-b4a5-188b0bcee8d3', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['liebert_cooling']


checkgroup_parameters.setdefault('liebert_cooling_position', [])

checkgroup_parameters['liebert_cooling_position'] = [
{'id': '3e852ec2-4c32-4780-aa45-e7338186fb74', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['liebert_cooling_position']


checkgroup_parameters.setdefault('livestatus_status', [])

checkgroup_parameters['livestatus_status'] = [
{'id': '9bbfb376-f028-479f-b059-684319a906ac', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['livestatus_status']


checkgroup_parameters.setdefault('lnx_quota', [])

checkgroup_parameters['lnx_quota'] = [
{'id': '2b898dec-ea2c-4486-8e9e-8efc237275cb', 'value': {'user': True, 'group': False}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['lnx_quota']


checkgroup_parameters.setdefault('logins', [])

checkgroup_parameters['logins'] = [
{'id': '7262b583-0900-4afa-a89c-47aa9a2a0ee0', 'value': {'levels': None}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['logins']


checkgroup_parameters.setdefault('logwatch_ec', [])

checkgroup_parameters['logwatch_ec'] = [
{'id': 'd8d235c8-eb12-42ea-bbe0-833b038e8f69', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['logwatch_ec']


checkgroup_parameters.setdefault('lsnat', [])

checkgroup_parameters['lsnat'] = [
{'id': '9775301b-02ce-4eb0-8d3e-cdb6cd6ded96', 'value': {'current_bindings': None}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['lsnat']


checkgroup_parameters.setdefault('lvm_lvs_pools', [])

checkgroup_parameters['lvm_lvs_pools'] = [
{'id': 'ff008460-5801-432c-9ac2-22b4581925a5', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['lvm_lvs_pools']


checkgroup_parameters.setdefault('mail_latency', [])

checkgroup_parameters['mail_latency'] = [
{'id': '35d67eba-8beb-4fe8-82ce-2213633e089d', 'value': {'levels': None}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mail_latency']


checkgroup_parameters.setdefault('mail_queue_length', [])

checkgroup_parameters['mail_queue_length'] = [
{'id': 'e60ab970-e752-4553-880e-3d47d1b9037f', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mail_queue_length']


checkgroup_parameters.setdefault('mail_queue_length_single', [])

checkgroup_parameters['mail_queue_length_single'] = [
{'id': '742e457f-d1db-4b42-95ff-290084f50277', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mail_queue_length_single']


checkgroup_parameters.setdefault('mbg_lantime_state', [])

checkgroup_parameters['mbg_lantime_state'] = [
{'id': 'f47d5e7a-b791-4887-bd59-dd0a2559c4a8', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mbg_lantime_state']


checkgroup_parameters.setdefault('mcafee_av_client', [])

checkgroup_parameters['mcafee_av_client'] = [
{'id': '6af96a39-0b79-4a7a-a0f7-3ab8884c5674', 'value': {'signature_age': (86400, 604800)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mcafee_av_client']


checkgroup_parameters.setdefault('mcafee_emailgateway_bridge', [])

checkgroup_parameters['mcafee_emailgateway_bridge'] = [
{'id': '6bd4e554-8814-4746-82a3-097d7eefca21', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mcafee_emailgateway_bridge']


checkgroup_parameters.setdefault('mcafee_web_gateway', [])

checkgroup_parameters['mcafee_web_gateway'] = [
{'id': '5668a76b-327c-40d8-b78f-dfbf3d74cc24', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mcafee_web_gateway']


checkgroup_parameters.setdefault('mcafee_web_gateway_misc', [])

checkgroup_parameters['mcafee_web_gateway_misc'] = [
{'id': 'a384d751-45a8-4c4d-9d84-f0565337732d', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mcafee_web_gateway_misc']


checkgroup_parameters.setdefault('mem_pages', [])

checkgroup_parameters['mem_pages'] = [
{'id': 'c6c48726-3d94-4fa7-80b8-1854a8614e84', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mem_pages']


checkgroup_parameters.setdefault('memory', [])

checkgroup_parameters['memory'] = [
{'id': '91d7e90c-6e2f-46d1-b3ce-6a382ff66049', 'value': {'levels': (150.0, 200.0)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['memory']


checkgroup_parameters.setdefault('memory_arbor', [])

checkgroup_parameters['memory_arbor'] = [
{'id': 'c329a6d6-8f2a-449f-a4a1-f7120e7764b0', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['memory_arbor']


checkgroup_parameters.setdefault('memory_available', [])

checkgroup_parameters['memory_available'] = [
{'id': '2b969d06-dfb5-4946-9e55-042103306581', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['memory_available']


checkgroup_parameters.setdefault('memory_linux', [])

checkgroup_parameters['memory_linux'] = [
{'id': '7c93cd79-29e0-4b74-9805-37b18d033ef1', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['memory_linux']


checkgroup_parameters.setdefault('memory_multiitem', [])

checkgroup_parameters['memory_multiitem'] = [
{'id': '0d7cd439-70fe-4ec5-8682-0633ffcd4149', 'value': {'levels': None}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['memory_multiitem']


checkgroup_parameters.setdefault('memory_pagefile_win', [])

checkgroup_parameters['memory_pagefile_win'] = [
{'id': 'c0558cb2-727f-4faa-9534-f190f6d7c003', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['memory_pagefile_win']


checkgroup_parameters.setdefault('memory_percentage_used', [])

checkgroup_parameters['memory_percentage_used'] = [
{'id': 'baef242f-3c2e-499c-be87-87db4115dc52', 'value': {'levels': ('fixed', (70.0, 80.0))}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['memory_percentage_used']


checkgroup_parameters.setdefault('memory_percentage_used_multiitem', [])

checkgroup_parameters['memory_percentage_used_multiitem'] = [
{'id': '68157e59-0fca-4634-9c07-d9964513a045', 'value': {'levels': (80.0, 90.0)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['memory_percentage_used_multiitem']


checkgroup_parameters.setdefault('memory_relative', [])

checkgroup_parameters['memory_relative'] = [
{'id': 'a5b926b0-e4dc-44d8-b0ac-dbf3ff97f871', 'value': {'levels': None}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['memory_relative']


checkgroup_parameters.setdefault('memory_simple', [])

checkgroup_parameters['memory_simple'] = [
{'id': 'efec1b0f-52a8-44f4-b8a0-933d7bb6056d', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['memory_simple']


checkgroup_parameters.setdefault('memory_simple_single', [])

checkgroup_parameters['memory_simple_single'] = [
{'id': 'a626c15a-3d79-493f-a3bb-06751d24c092', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['memory_simple_single']


checkgroup_parameters.setdefault('memory_utilization', [])

checkgroup_parameters['memory_utilization'] = [
{'id': '6caad413-1f02-4bf5-9cda-f86e21f0c93c', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['memory_utilization']


checkgroup_parameters.setdefault('memory_utilization_multiitem', [])

checkgroup_parameters['memory_utilization_multiitem'] = [
{'id': '86d0abf3-70b3-41ed-9911-cd91778e4379', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['memory_utilization_multiitem']


checkgroup_parameters.setdefault('metric_backend_omd', [])

checkgroup_parameters['metric_backend_omd'] = [
{'id': '771ab72f-e651-4c1c-b0ae-9e408df4ae5a', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['metric_backend_omd']


checkgroup_parameters.setdefault('mobileiron_compliance', [])

checkgroup_parameters['mobileiron_compliance'] = [
{'id': '5b730923-460a-46c2-ac25-153f6b5fc1f1', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mobileiron_compliance']


checkgroup_parameters.setdefault('mobileiron_statistics', [])

checkgroup_parameters['mobileiron_statistics'] = [
{'id': 'ee6bb08e-78d2-49dd-9aff-13d3e9759364', 'value': {'non_compliant_summary_levels': (10.0, 20.0)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mobileiron_statistics']


checkgroup_parameters.setdefault('mobileiron_versions', [])

checkgroup_parameters['mobileiron_versions'] = [
{'id': '59530c47-beef-416c-994c-9fb8df311310', 'value': {'ios_version_regexp': '', 'android_version_regexp': '', 'os_version_other': 0, 'patchlevel_unparsable': 0, 'patchlevel_age': 7776000, 'os_build_unparsable': 0, 'os_age': 7776000}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mobileiron_versions']


checkgroup_parameters.setdefault('mongodb_asserts', [])

checkgroup_parameters['mongodb_asserts'] = [
{'id': '7c98e4cc-9281-4ae4-8301-badd26d6fed9', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mongodb_asserts']


checkgroup_parameters.setdefault('mongodb_cluster', [])

checkgroup_parameters['mongodb_cluster'] = [
{'id': 'd4a295a9-a3d5-4c99-904b-c671542fd290', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mongodb_cluster']


checkgroup_parameters.setdefault('mongodb_collections', [])

checkgroup_parameters['mongodb_collections'] = [
{'id': 'dde90557-9eb2-4620-b418-cb21ef071cfe', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mongodb_collections']


checkgroup_parameters.setdefault('mongodb_flushing', [])

checkgroup_parameters['mongodb_flushing'] = [
{'id': '3b555001-3169-43e0-9379-36a04708461b', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mongodb_flushing']


checkgroup_parameters.setdefault('mongodb_locks', [])

checkgroup_parameters['mongodb_locks'] = [
{'id': '4629b159-8c5e-4d22-9c91-d869a744c581', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mongodb_locks']


checkgroup_parameters.setdefault('mongodb_mem', [])

checkgroup_parameters['mongodb_mem'] = [
{'id': '893093d1-33f5-4861-ad6a-876d20b644ee', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mongodb_mem']


checkgroup_parameters.setdefault('mongodb_replica_set', [])

checkgroup_parameters['mongodb_replica_set'] = [
{'id': '735bc428-ee67-49eb-a7d4-382bd6529b2a', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mongodb_replica_set']


checkgroup_parameters.setdefault('motion', [])

checkgroup_parameters['motion'] = [
{'id': '4ae5c809-65e7-4720-b717-497ee14125fb', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['motion']


checkgroup_parameters.setdefault('mq_queues', [])

checkgroup_parameters['mq_queues'] = [
{'id': '749d71fa-650b-42c2-9c10-81f508f4f84d', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mq_queues']


checkgroup_parameters.setdefault('msexch_copyqueue', [])

checkgroup_parameters['msexch_copyqueue'] = [
{'id': '67ab6417-3d97-495f-9bee-004e1c8131e5', 'value': {'levels': None}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['msexch_copyqueue']


checkgroup_parameters.setdefault('msoffice_licenses', [])

checkgroup_parameters['msoffice_licenses'] = [
{'id': '611b9fdd-76c4-4271-b554-13adf6060b7a', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['msoffice_licenses']


checkgroup_parameters.setdefault('msoffice_serviceplans', [])

checkgroup_parameters['msoffice_serviceplans'] = [
{'id': 'd1b91628-5682-42f4-b001-05c20ddd6679', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['msoffice_serviceplans']


checkgroup_parameters.setdefault('mssql_backup', [])

checkgroup_parameters['mssql_backup'] = [
{'id': '1bb5753d-2be0-46f3-a954-9ef3e2952887', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mssql_backup']


checkgroup_parameters.setdefault('mssql_backup_per_type', [])

checkgroup_parameters['mssql_backup_per_type'] = [
{'id': 'a53b1760-fce6-4ce4-b2df-77a325fabc90', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mssql_backup_per_type']


checkgroup_parameters.setdefault('mssql_connections', [])

checkgroup_parameters['mssql_connections'] = [
{'id': 'ba79e952-67da-47ca-8e53-8586a2b070ae', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mssql_connections']


checkgroup_parameters.setdefault('mssql_counters_locks', [])

checkgroup_parameters['mssql_counters_locks'] = [
{'id': '07fbf7d7-8d96-4bd1-8902-1996c911a831', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mssql_counters_locks']


checkgroup_parameters.setdefault('mssql_counters_page_life_expectancy', [])

checkgroup_parameters['mssql_counters_page_life_expectancy'] = [
{'id': '873bbbb9-eae1-4ac3-bd0f-6204cbb0795a', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mssql_counters_page_life_expectancy']


checkgroup_parameters.setdefault('mssql_databases', [])

checkgroup_parameters['mssql_databases'] = [
{'id': '4d9e1767-624f-4b5c-8618-420230809559', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mssql_databases']


checkgroup_parameters.setdefault('mssql_datafiles', [])

checkgroup_parameters['mssql_datafiles'] = [
{'id': 'cffa7285-931c-4ac7-a39f-d12bdfe0a32d', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mssql_datafiles']


checkgroup_parameters.setdefault('mssql_file_sizes', [])

checkgroup_parameters['mssql_file_sizes'] = [
{'id': 'aed03b3d-ab8e-4a9f-8bd4-06646dfed732', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mssql_file_sizes']


checkgroup_parameters.setdefault('mssql_instance', [])

checkgroup_parameters['mssql_instance'] = [
{'id': '855bd641-44b1-4844-a677-6c7bc99c4b6c', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mssql_instance']


checkgroup_parameters.setdefault('mssql_instance_blocked_sessions', [])

checkgroup_parameters['mssql_instance_blocked_sessions'] = [
{'id': '809ba72c-f4c1-4246-95d4-9a962bd0b9de', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mssql_instance_blocked_sessions']


checkgroup_parameters.setdefault('mssql_jobs', [])

checkgroup_parameters['mssql_jobs'] = [
{'id': 'ae077b9e-b5af-4e13-a944-fa6f9b32af1f', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mssql_jobs']


checkgroup_parameters.setdefault('mssql_mirroring', [])

checkgroup_parameters['mssql_mirroring'] = [
{'id': 'd4e87983-fd49-40dc-8e53-53d170e46ba6', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mssql_mirroring']


checkgroup_parameters.setdefault('mssql_page_activity', [])

checkgroup_parameters['mssql_page_activity'] = [
{'id': 'e6a3bd74-931f-442f-aa18-cace6a82b75a', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mssql_page_activity']


checkgroup_parameters.setdefault('mssql_stats', [])

checkgroup_parameters['mssql_stats'] = [
{'id': '75b60638-daca-4781-83bd-1edf9fa99567', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mssql_stats']


checkgroup_parameters.setdefault('mssql_tablespaces', [])

checkgroup_parameters['mssql_tablespaces'] = [
{'id': 'fd1e3d80-891d-4ab2-91a8-7901e2a86a43', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mssql_tablespaces']


checkgroup_parameters.setdefault('mssql_transactionlogs', [])

checkgroup_parameters['mssql_transactionlogs'] = [
{'id': '4b7e23a1-d3ba-4373-998e-2544f45b5ea7', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mssql_transactionlogs']


checkgroup_parameters.setdefault('msx_database', [])

checkgroup_parameters['msx_database'] = [
{'id': 'eb150920-6f87-4ae3-9f19-ebc6a4b273c9', 'value': {'read_attached_latency_s': ('fixed', (0.2, 0.25)), 'read_recovery_latency_s': ('fixed', (0.15, 0.2)), 'write_latency_s': ('fixed', (0.04, 0.05)), 'log_latency_s': ('fixed', (0.005, 0.01))}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['msx_database']


checkgroup_parameters.setdefault('msx_info_store', [])

checkgroup_parameters['msx_info_store'] = [
{'id': '5ee861eb-6e42-4fae-ac0d-c97a00886a20', 'value': {'store_latency_s': ('fixed', (0.04, 0.05)), 'clienttype_latency_s': ('fixed', (0.04, 0.05)), 'clienttype_requests': ('fixed', (60, 70))}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['msx_info_store']


checkgroup_parameters.setdefault('msx_queues', [])

checkgroup_parameters['msx_queues'] = [
{'id': 'a69729cb-96db-4e35-b095-6f25bc075e49', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['msx_queues']


checkgroup_parameters.setdefault('msx_rpcclientaccess', [])

checkgroup_parameters['msx_rpcclientaccess'] = [
{'id': 'a12263b8-0f3b-46de-86ad-cb37e8b183f2', 'value': {'latency_s': ('fixed', (0.2, 0.25)), 'requests': ('fixed', (30, 40))}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['msx_rpcclientaccess']


checkgroup_parameters.setdefault('mtr', [])

checkgroup_parameters['mtr'] = [
{'id': 'a5b1891f-7e20-4a72-93f0-0044d903d131', 'value': {'rta': (150, 250), 'rtstddev': (150, 250), 'pl': (10, 25)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mtr']


checkgroup_parameters.setdefault('multipath', [])

checkgroup_parameters['multipath'] = [
{'id': '2d47327c-f255-43ae-ad4f-9d068260b7e7', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['multipath']


checkgroup_parameters.setdefault('multipath_count', [])

checkgroup_parameters['multipath_count'] = [
{'id': 'e1a6efb0-bb3c-405b-9f59-59a3ae0da79d', 'value': {'levels_map': None}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['multipath_count']


checkgroup_parameters.setdefault('mysql_connections', [])

checkgroup_parameters['mysql_connections'] = [
{'id': 'e6843f05-f00d-42c0-abe2-895f8867a26f', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mysql_connections']


checkgroup_parameters.setdefault('mysql_db_size', [])

checkgroup_parameters['mysql_db_size'] = [
{'id': 'c32af2a1-8ec7-4b0f-9e3e-3986696d5f11', 'value': {'levels': None}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mysql_db_size']


checkgroup_parameters.setdefault('mysql_innodb_io', [])

checkgroup_parameters['mysql_innodb_io'] = [
{'id': 'c39cb833-83d1-4622-84a5-c68a9d411944', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mysql_innodb_io']


checkgroup_parameters.setdefault('mysql_sessions', [])

checkgroup_parameters['mysql_sessions'] = [
{'id': '65853b61-4cfc-4c8e-aa53-0a5471bc7e81', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mysql_sessions']


checkgroup_parameters.setdefault('mysql_slave', [])

checkgroup_parameters['mysql_slave'] = [
{'id': 'd667f133-9686-426d-b55a-67b2b328dae0', 'value': {'seconds_behind_master': ('fixed', (0.0, 0.0))}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['mysql_slave']


checkgroup_parameters.setdefault('netapp_disks', [])

checkgroup_parameters['netapp_disks'] = [
{'id': '450884c9-0d73-4003-85ca-d5d9951dce19', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['netapp_disks']


checkgroup_parameters.setdefault('netapp_fcportio', [])

checkgroup_parameters['netapp_fcportio'] = [
{'id': '54e180dc-1f71-4a62-9a76-8cac8f58912e', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['netapp_fcportio']


checkgroup_parameters.setdefault('netapp_luns', [])

checkgroup_parameters['netapp_luns'] = [
{'id': '80f45870-0488-4b84-8108-8f12ec14ee45', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['netapp_luns']


checkgroup_parameters.setdefault('netapp_snapshots', [])

checkgroup_parameters['netapp_snapshots'] = [
{'id': '4a858ef4-a3b6-484f-802f-7e25d7092af0', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['netapp_snapshots']


checkgroup_parameters.setdefault('netapp_system_time_offset', [])

checkgroup_parameters['netapp_system_time_offset'] = [
{'id': '73f8a930-8059-488c-b881-d57e1000c821', 'value': {'upper_levels': ('fixed', (30.0, 60.0))}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['netapp_system_time_offset']


checkgroup_parameters.setdefault('netapp_volumes', [])

checkgroup_parameters['netapp_volumes'] = [
{'id': '2f930eab-ac31-4c49-bb3f-038a16534a9b', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['netapp_volumes']


checkgroup_parameters.setdefault('netscaler_dnsrates', [])

checkgroup_parameters['netscaler_dnsrates'] = [
{'id': '180fdbee-7861-405a-8d02-381456919013', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['netscaler_dnsrates']


checkgroup_parameters.setdefault('netscaler_ha', [])

checkgroup_parameters['netscaler_ha'] = [
{'id': '89c11083-94c5-4ee2-b07c-a2aeed221b38', 'value': {'failover_monitoring': ('disabled', None)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['netscaler_ha']


checkgroup_parameters.setdefault('netscaler_mem', [])

checkgroup_parameters['netscaler_mem'] = [
{'id': 'dd219a37-589d-4dcd-b7ab-56075b63d4d2', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['netscaler_mem']


checkgroup_parameters.setdefault('netscaler_sslcerts', [])

checkgroup_parameters['netscaler_sslcerts'] = [
{'id': '0b13f859-e5f7-4d3f-84ab-4f2c5c214286', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['netscaler_sslcerts']


checkgroup_parameters.setdefault('netscaler_tcp_conns', [])

checkgroup_parameters['netscaler_tcp_conns'] = [
{'id': '774116f8-ccba-43b1-b942-f91ebf7869c0', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['netscaler_tcp_conns']


checkgroup_parameters.setdefault('netscaler_vserver', [])

checkgroup_parameters['netscaler_vserver'] = [
{'id': 'af36a4d2-a3bd-4a0b-b74d-d044f3a91740', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['netscaler_vserver']


checkgroup_parameters.setdefault('network_fs', [])

checkgroup_parameters['network_fs'] = [
{'id': '9afd81cd-2d59-40c2-8786-a6f708625223', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['network_fs']


checkgroup_parameters.setdefault('network_io', [])

checkgroup_parameters['network_io'] = [
{'id': '609ae212-92e9-433d-aabe-c56360b2e586', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['network_io']


checkgroup_parameters.setdefault('nfsiostats', [])

checkgroup_parameters['nfsiostats'] = [
{'id': 'a6ad5450-4241-43e0-860d-18804f3ed786', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['nfsiostats']


checkgroup_parameters.setdefault('nginx_status', [])

checkgroup_parameters['nginx_status'] = [
{'id': '2475c674-2bee-4817-b92b-1316cde7fd30', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['nginx_status']


checkgroup_parameters.setdefault('nimble_latency', [])

checkgroup_parameters['nimble_latency'] = [
{'id': '1238a2d1-2c96-4c12-8550-a36dcda5dfd7', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['nimble_latency']


checkgroup_parameters.setdefault('ntp_peer', [])

checkgroup_parameters['ntp_peer'] = [
{'id': 'f3ea76c1-b95a-4db9-ba2f-bbdcf15001d7', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['ntp_peer']


checkgroup_parameters.setdefault('ntp_time', [])

checkgroup_parameters['ntp_time'] = [
{'id': 'cfdf9134-f654-4357-a7d7-bc2ee8e47127', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['ntp_time']


checkgroup_parameters.setdefault('nvidia_smi_en_de_coder_util', [])

checkgroup_parameters['nvidia_smi_en_de_coder_util'] = [
{'id': 'cba86905-b8cf-4dbd-92e2-0533e47d3b4e', 'value': {'encoder_levels': None, 'decoder_levels': None}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['nvidia_smi_en_de_coder_util']


checkgroup_parameters.setdefault('nvidia_smi_gpu_util', [])

checkgroup_parameters['nvidia_smi_gpu_util'] = [
{'id': 'b72d2d2d-f61b-43f1-b029-4ac0da7cd5ec', 'value': {'levels': None}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['nvidia_smi_gpu_util']


checkgroup_parameters.setdefault('nvidia_smi_memory_util', [])

checkgroup_parameters['nvidia_smi_memory_util'] = [
{'id': 'e7ca397f-fe10-4b74-9702-1d5441261468', 'value': {'levels_total': None, 'levels_bar1': None, 'levels_fb': None}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['nvidia_smi_memory_util']


checkgroup_parameters.setdefault('nvidia_smi_power', [])

checkgroup_parameters['nvidia_smi_power'] = [
{'id': '9025741d-0228-4f61-9230-44ddebe9fb47', 'value': {'levels': None}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['nvidia_smi_power']


checkgroup_parameters.setdefault('ocprot_current', [])

checkgroup_parameters['ocprot_current'] = [
{'id': '8301dd6f-c5a3-4ee0-bbab-1f0cba059b47', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['ocprot_current']


checkgroup_parameters.setdefault('openhardwaremonitor_smart', [])

checkgroup_parameters['openhardwaremonitor_smart'] = [
{'id': 'ab9052e3-d8e4-4768-99c0-81123f539b4a', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['openhardwaremonitor_smart']


checkgroup_parameters.setdefault('oracle_crs_res', [])

checkgroup_parameters['oracle_crs_res'] = [
{'id': '9e36558e-07d4-4f57-8bb9-46005d961db8', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['oracle_crs_res']


checkgroup_parameters.setdefault('oracle_dataguard_stats', [])

checkgroup_parameters['oracle_dataguard_stats'] = [
{'id': '8fb91157-33fc-4096-8442-61480b109f95', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['oracle_dataguard_stats']


checkgroup_parameters.setdefault('oracle_instance', [])

checkgroup_parameters['oracle_instance'] = [
{'id': 'add0dd7b-7b73-450f-b533-26402aea201a', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['oracle_instance']


checkgroup_parameters.setdefault('oracle_jobs', [])

checkgroup_parameters['oracle_jobs'] = [
{'id': 'd6d7c9f7-90dc-46db-bb60-3f1a5f980530', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['oracle_jobs']


checkgroup_parameters.setdefault('oracle_locks', [])

checkgroup_parameters['oracle_locks'] = [
{'id': 'e951c361-cba4-407e-a2e6-e4125171b4da', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['oracle_locks']


checkgroup_parameters.setdefault('oracle_logswitches', [])

checkgroup_parameters['oracle_logswitches'] = [
{'id': '596ae2f0-2e4a-409f-bf5f-3a55367ccce9', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['oracle_logswitches']


checkgroup_parameters.setdefault('oracle_longactivesessions', [])

checkgroup_parameters['oracle_longactivesessions'] = [
{'id': 'be0c3334-24b4-4af5-a204-f174f8872b4b', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['oracle_longactivesessions']


checkgroup_parameters.setdefault('oracle_performance', [])

checkgroup_parameters['oracle_performance'] = [
{'id': '8b99d6d4-f90d-4746-b318-6f6388ccd338', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['oracle_performance']


checkgroup_parameters.setdefault('oracle_processes', [])

checkgroup_parameters['oracle_processes'] = [
{'id': '3df1428a-8d42-4b5c-a171-6558b5c2f600', 'value': {'levels': (70.0, 90.0)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['oracle_processes']


checkgroup_parameters.setdefault('oracle_recovery_area', [])

checkgroup_parameters['oracle_recovery_area'] = [
{'id': '35d45ab8-1810-4d08-b8c6-63fb3f0578ff', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['oracle_recovery_area']


checkgroup_parameters.setdefault('oracle_recovery_status', [])

checkgroup_parameters['oracle_recovery_status'] = [
{'id': 'e207b3be-455e-4e15-82f0-72aa6ebde5d8', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['oracle_recovery_status']


checkgroup_parameters.setdefault('oracle_rman', [])

checkgroup_parameters['oracle_rman'] = [
{'id': '9f12fe8a-bf70-4614-8454-77296dfc7be7', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['oracle_rman']


checkgroup_parameters.setdefault('oracle_sessions', [])

checkgroup_parameters['oracle_sessions'] = [
{'id': '14aa290b-e582-4856-a39a-f39f2028d217', 'value': {'sessions_abs': None}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['oracle_sessions']


checkgroup_parameters.setdefault('oracle_sql', [])

checkgroup_parameters['oracle_sql'] = [
{'id': '37a52f75-df2a-4058-9829-dd8bd3ad5918', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['oracle_sql']


checkgroup_parameters.setdefault('oracle_tablespaces', [])

checkgroup_parameters['oracle_tablespaces'] = [
{'id': '700d42a5-dd98-4dda-91f0-9cfbce239c37', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['oracle_tablespaces']


checkgroup_parameters.setdefault('oracle_undostat', [])

checkgroup_parameters['oracle_undostat'] = [
{'id': 'e20b2720-4952-4915-9e98-87eb386dc1ab', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['oracle_undostat']


checkgroup_parameters.setdefault('overall_utilization_multiitem', [])

checkgroup_parameters['overall_utilization_multiitem'] = [
{'id': '79a1064b-3cbb-466b-841c-9e155033921d', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['overall_utilization_multiitem']


checkgroup_parameters.setdefault('ovs_bonding', [])

checkgroup_parameters['ovs_bonding'] = [
{'id': 'c9cc7669-be03-4f77-84fe-59081dc344a8', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['ovs_bonding']


checkgroup_parameters.setdefault('palo_alto', [])

checkgroup_parameters['palo_alto'] = [
{'id': '5626b70d-5bcd-47d8-ae36-fc02dd83d2b5', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['palo_alto']


checkgroup_parameters.setdefault('palo_alto_sessions', [])

checkgroup_parameters['palo_alto_sessions'] = [
{'id': 'ba947886-f3a0-4c10-878d-86845b65232a', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['palo_alto_sessions']


checkgroup_parameters.setdefault('palo_alto_users_rule', [])

checkgroup_parameters['palo_alto_users_rule'] = [
{'id': 'd7301e4f-bd09-4ff0-acd0-e29005362c74', 'value': {'levels': ('perc_user', (0.0, 0.0))}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['palo_alto_users_rule']


checkgroup_parameters.setdefault('pci_io_utilization_multiitem', [])

checkgroup_parameters['pci_io_utilization_multiitem'] = [
{'id': '1ab7be58-d855-4e9c-af12-dd5dc79d5edd', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['pci_io_utilization_multiitem']


checkgroup_parameters.setdefault('pdu_gude', [])

checkgroup_parameters['pdu_gude'] = [
{'id': '2b5e73fd-db26-4dcc-92ff-533e5f3e0871', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['pdu_gude']


checkgroup_parameters.setdefault('pf_used_states', [])

checkgroup_parameters['pf_used_states'] = [
{'id': '815f1dd1-0bd4-46e9-a4be-367c422f1fda', 'value': {'used': None}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['pf_used_states']


checkgroup_parameters.setdefault('pfm_health', [])

checkgroup_parameters['pfm_health'] = [
{'id': 'f76d9134-ff40-4624-bd87-6b2afcba40fb', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['pfm_health']


checkgroup_parameters.setdefault('pfsense_counter', [])

checkgroup_parameters['pfsense_counter'] = [
{'id': '2ce67893-104b-4882-87f7-87d58a124cc4', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['pfsense_counter']


checkgroup_parameters.setdefault('plesk_backups', [])

checkgroup_parameters['plesk_backups'] = [
{'id': '20bd1b65-46ff-4dd8-b96c-eb4aebfb293e', 'value': {'no_backup_configured_state': 1, 'no_backup_found_state': 1}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['plesk_backups']


checkgroup_parameters.setdefault('pll_lock_voltage', [])

checkgroup_parameters['pll_lock_voltage'] = [
{'id': 'dcf76741-ad0c-468c-9bf1-e17b9211f992', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['pll_lock_voltage']


checkgroup_parameters.setdefault('plug_count', [])

checkgroup_parameters['plug_count'] = [
{'id': 'f8c502dd-bcdd-4116-b1b4-9906a55d7e20', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['plug_count']


checkgroup_parameters.setdefault('plugs', [])

checkgroup_parameters['plugs'] = [
{'id': 'e92791c9-ed84-4706-9d15-b0585e47baaa', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['plugs']


checkgroup_parameters.setdefault('podman_container_health', [])

checkgroup_parameters['podman_container_health'] = [
{'id': 'c0557abd-fa1f-48c6-817e-29c082bff62d', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['podman_container_health']


checkgroup_parameters.setdefault('podman_container_restarts', [])

checkgroup_parameters['podman_container_restarts'] = [
{'id': '8c4e8517-7410-4e42-bd89-d3af1f09cc98', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['podman_container_restarts']


checkgroup_parameters.setdefault('podman_container_status', [])

checkgroup_parameters['podman_container_status'] = [
{'id': '07da46db-004b-46c8-adfd-d3e8e36379d5', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['podman_container_status']


checkgroup_parameters.setdefault('podman_containers', [])

checkgroup_parameters['podman_containers'] = [
{'id': 'f400bb6f-41fb-4bf7-bfc2-1ae5c41afce4', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['podman_containers']


checkgroup_parameters.setdefault('podman_disk_usage', [])

checkgroup_parameters['podman_disk_usage'] = [
{'id': '57c99da4-1100-49a3-8f98-6a02664fcb9a', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['podman_disk_usage']


checkgroup_parameters.setdefault('podman_pods', [])

checkgroup_parameters['podman_pods'] = [
{'id': '3bd0aebb-017c-4d74-ab7c-1f1e0f99e66e', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['podman_pods']


checkgroup_parameters.setdefault('postgres_instance_sessions', [])

checkgroup_parameters['postgres_instance_sessions'] = [
{'id': 'e470182f-2818-4f93-a961-e60eda5bb5a5', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['postgres_instance_sessions']


checkgroup_parameters.setdefault('postgres_locks', [])

checkgroup_parameters['postgres_locks'] = [
{'id': 'c979758e-ce79-44ab-a331-e74203399af1', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['postgres_locks']


checkgroup_parameters.setdefault('postgres_maintenance', [])

checkgroup_parameters['postgres_maintenance'] = [
{'id': '2b69947a-0cef-47af-b8da-70434b1e6a21', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['postgres_maintenance']


checkgroup_parameters.setdefault('postgres_stat_database', [])

checkgroup_parameters['postgres_stat_database'] = [
{'id': '724713c3-bead-4236-9a7f-5bebc9be6e09', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['postgres_stat_database']


checkgroup_parameters.setdefault('power_multiitem', [])

checkgroup_parameters['power_multiitem'] = [
{'id': '8517cdd6-aac9-4e04-a272-cc96f3b6a620', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['power_multiitem']


checkgroup_parameters.setdefault('power_presence', [])

checkgroup_parameters['power_presence'] = [
{'id': 'c64bcf11-ff50-42e0-9bee-dcb8b038cf09', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['power_presence']


checkgroup_parameters.setdefault('printer_input', [])

checkgroup_parameters['printer_input'] = [
{'id': '503257ee-04e4-47e9-94c1-57243984237f', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['printer_input']


checkgroup_parameters.setdefault('printer_output', [])

checkgroup_parameters['printer_output'] = [
{'id': 'f990cbae-15ea-43e9-84c5-d7c35be0d642', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['printer_output']


checkgroup_parameters.setdefault('printer_supply', [])

checkgroup_parameters['printer_supply'] = [
{'id': 'ae84e4bd-5c25-4912-889d-d863c812ae78', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['printer_supply']


checkgroup_parameters.setdefault('prism_alerts', [])

checkgroup_parameters['prism_alerts'] = [
{'id': '4afe68e5-150a-4003-a1e9-51b1aa5345ca', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['prism_alerts']


checkgroup_parameters.setdefault('prism_cluster_cpu', [])

checkgroup_parameters['prism_cluster_cpu'] = [
{'id': '937a949d-dcaf-4f46-819e-a3ca760374cc', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['prism_cluster_cpu']


checkgroup_parameters.setdefault('prism_cluster_io', [])

checkgroup_parameters['prism_cluster_io'] = [
{'id': '5ed8a800-f384-4be3-a9ce-a77ebb548e82', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['prism_cluster_io']


checkgroup_parameters.setdefault('prism_cluster_mem', [])

checkgroup_parameters['prism_cluster_mem'] = [
{'id': '6bee3c75-6652-4d8c-ac5b-24bd2fd49724', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['prism_cluster_mem']


checkgroup_parameters.setdefault('prism_host_cpu', [])

checkgroup_parameters['prism_host_cpu'] = [
{'id': 'c73a4dc9-2e25-4aa6-aee1-fd5abfd74a9a', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['prism_host_cpu']


checkgroup_parameters.setdefault('prism_host_disks', [])

checkgroup_parameters['prism_host_disks'] = [
{'id': '3dfdabb8-1b24-47e3-96de-c195955a9dd0', 'value': {'mounted': True}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['prism_host_disks']


checkgroup_parameters.setdefault('prism_host_mem', [])

checkgroup_parameters['prism_host_mem'] = [
{'id': '91857a87-1f90-424a-a711-e12777d58afd', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['prism_host_mem']


checkgroup_parameters.setdefault('prism_hosts', [])

checkgroup_parameters['prism_hosts'] = [
{'id': '2232eff6-d485-482e-b85b-159083241b8f', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['prism_hosts']


checkgroup_parameters.setdefault('prism_protection_domains', [])

checkgroup_parameters['prism_protection_domains'] = [
{'id': '72174e4c-bb28-4f04-ab70-2bc2e65a4563', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['prism_protection_domains']


checkgroup_parameters.setdefault('prism_remote_support', [])

checkgroup_parameters['prism_remote_support'] = [
{'id': '98445928-6863-44b4-9b0f-e70916e8447c', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['prism_remote_support']


checkgroup_parameters.setdefault('prism_vm_cpu', [])

checkgroup_parameters['prism_vm_cpu'] = [
{'id': 'f69620a9-eff5-45e9-9698-35c1124a207d', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['prism_vm_cpu']


checkgroup_parameters.setdefault('prism_vm_memory', [])

checkgroup_parameters['prism_vm_memory'] = [
{'id': 'a21650e4-54f7-4442-8c4b-bec908e44523', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['prism_vm_memory']


checkgroup_parameters.setdefault('prism_vm_status', [])

checkgroup_parameters['prism_vm_status'] = [
{'id': '9a3c0ee6-de9a-4e8f-8a25-49e7728b7a16', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['prism_vm_status']


checkgroup_parameters.setdefault('prism_vm_tools', [])

checkgroup_parameters['prism_vm_tools'] = [
{'id': '15e82898-fc4f-45a9-b958-d3a5af603313', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['prism_vm_tools']


checkgroup_parameters.setdefault('prism_vms', [])

checkgroup_parameters['prism_vms'] = [
{'id': '1b907f16-a372-416e-8699-4f660b782422', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['prism_vms']


checkgroup_parameters.setdefault('prometheus_custom', [])

checkgroup_parameters['prometheus_custom'] = [
{'id': '2b891018-cb3e-4bf1-99ee-4b1034464f54', 'value': {'metric_list': []}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['prometheus_custom']


checkgroup_parameters.setdefault('proxmox_ve_cpu_util', [])

checkgroup_parameters['proxmox_ve_cpu_util'] = [
{'id': 'ce8a8adf-4178-444b-9b1c-a7bd735ba2a8', 'value': {'util': ('fixed', (90.0, 95.0))}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['proxmox_ve_cpu_util']


checkgroup_parameters.setdefault('proxmox_ve_disk_percentage_used', [])

checkgroup_parameters['proxmox_ve_disk_percentage_used'] = [
{'id': 'c541f61c-e074-4803-850d-d232a51c11b9', 'value': {'levels': (80.0, 90.0)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['proxmox_ve_disk_percentage_used']


checkgroup_parameters.setdefault('proxmox_ve_disk_throughput', [])

checkgroup_parameters['proxmox_ve_disk_throughput'] = [
{'id': 'aca53616-3bca-4284-a46c-b50492733104', 'value': {'read_levels': ('fixed', (50000000, 100000000)), 'write_levels': ('fixed', (50000000, 100000000))}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['proxmox_ve_disk_throughput']


checkgroup_parameters.setdefault('proxmox_ve_ha_manager_status', [])

checkgroup_parameters['proxmox_ve_ha_manager_status'] = [
{'id': '4f58f04e-9491-4934-8051-879f3a4d02b0', 'value': {'differing_service_state': 1}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['proxmox_ve_ha_manager_status']


checkgroup_parameters.setdefault('proxmox_ve_mem_usage', [])

checkgroup_parameters['proxmox_ve_mem_usage'] = [
{'id': '49c172f6-4af0-4eb5-b3ed-4cef6a989e6a', 'value': {'levels': (80.0, 90.0)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['proxmox_ve_mem_usage']


checkgroup_parameters.setdefault('proxmox_ve_network_throughput', [])

checkgroup_parameters['proxmox_ve_network_throughput'] = [
{'id': '03c624a5-04d9-49be-9755-a444bea22c0b', 'value': {'in_levels': ('fixed', (50000000, 100000000)), 'out_levels': ('fixed', (50000000, 100000000))}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['proxmox_ve_network_throughput']


checkgroup_parameters.setdefault('proxmox_ve_node_cpu_allocation', [])

checkgroup_parameters['proxmox_ve_node_cpu_allocation'] = [
{'id': '64dcefea-b71f-4b25-a6a2-0a47128a76e8', 'value': {'cpu_allocation_ratio': ('fixed', (150.0, 200.0))}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['proxmox_ve_node_cpu_allocation']


checkgroup_parameters.setdefault('proxmox_ve_node_info', [])

checkgroup_parameters['proxmox_ve_node_info'] = [
{'id': '3a3aa335-ec03-4b66-9809-04231cf0d578', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['proxmox_ve_node_info']


checkgroup_parameters.setdefault('proxmox_ve_node_mem_allocation', [])

checkgroup_parameters['proxmox_ve_node_mem_allocation'] = [
{'id': '74319e4d-06f0-47b9-a807-e95e1bfaa98b', 'value': {'mem_allocation_ratio': ('fixed', (100.0, 120.0))}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['proxmox_ve_node_mem_allocation']


checkgroup_parameters.setdefault('proxmox_ve_replication', [])

checkgroup_parameters['proxmox_ve_replication'] = [
{'id': '7cc0ce8b-613a-4395-a033-0ed9ae64966c', 'value': {'time_since_last_replication': ('fixed', (0.0, 0.0)), 'no_replications_state': 0}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['proxmox_ve_replication']


checkgroup_parameters.setdefault('proxmox_ve_vm_backup_status', [])

checkgroup_parameters['proxmox_ve_vm_backup_status'] = [
{'id': '5bf5680f-c618-490b-b37a-4e492a29b474', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['proxmox_ve_vm_backup_status']


checkgroup_parameters.setdefault('proxmox_ve_vm_info', [])

checkgroup_parameters['proxmox_ve_vm_info'] = [
{'id': 'a215fd38-4b0d-4865-8143-6b4df9f019dd', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['proxmox_ve_vm_info']


checkgroup_parameters.setdefault('proxmox_ve_vm_snapshot_age', [])

checkgroup_parameters['proxmox_ve_vm_snapshot_age'] = [
{'id': '5187a98b-d4bc-4d12-9a57-092af61321c2', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['proxmox_ve_vm_snapshot_age']


checkgroup_parameters.setdefault('ps', [])

checkgroup_parameters['ps'] = [
{'id': '9ae16f6b-4e09-47bc-bc84-8ecdfdaca57c', 'value': {'cpu_rescale_max': True}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['ps']


checkgroup_parameters.setdefault('ps_voltage', [])

checkgroup_parameters['ps_voltage'] = [
{'id': '78644133-a11c-44fd-ba93-86bb786f9bbc', 'value': {'levels_lower': (0.0, 0.0), 'levels_upper': (0.0, 0.0)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['ps_voltage']


checkgroup_parameters.setdefault('psu_wattage', [])

checkgroup_parameters['psu_wattage'] = [
{'id': '056b45b2-e173-4dcf-aa0e-c69f5c16bdbe', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['psu_wattage']


checkgroup_parameters.setdefault('pulse_secure_disk_util', [])

checkgroup_parameters['pulse_secure_disk_util'] = [
{'id': 'd27da454-8de1-486f-b76d-2464ef2d2479', 'value': {'upper_levels': (80.0, 90.0)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['pulse_secure_disk_util']


checkgroup_parameters.setdefault('pulse_secure_mem_util', [])

checkgroup_parameters['pulse_secure_mem_util'] = [
{'id': 'a3f4ded6-f6f8-4faf-acf8-d335ec9ef970', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['pulse_secure_mem_util']


checkgroup_parameters.setdefault('pulse_secure_users', [])

checkgroup_parameters['pulse_secure_users'] = [
{'id': 'a3bbdec3-bad5-48b3-bf50-980aa2074a3e', 'value': {'upper_number_of_users': None}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['pulse_secure_users']


checkgroup_parameters.setdefault('pure_storage_capacity', [])

checkgroup_parameters['pure_storage_capacity'] = [
{'id': '3d23cf46-ebe4-476f-a6ed-dd240e47bacf', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['pure_storage_capacity']


checkgroup_parameters.setdefault('quantum_storage_status', [])

checkgroup_parameters['quantum_storage_status'] = [
{'id': '0b07eb5e-6cf7-470f-b93e-83c632e2809f', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['quantum_storage_status']


checkgroup_parameters.setdefault('rabbitmq_cluster_messages', [])

checkgroup_parameters['rabbitmq_cluster_messages'] = [
{'id': '79d9b8fb-b99f-499c-990a-4ec30d867b7d', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['rabbitmq_cluster_messages']


checkgroup_parameters.setdefault('rabbitmq_cluster_stats', [])

checkgroup_parameters['rabbitmq_cluster_stats'] = [
{'id': '4d905c90-4887-460c-bf46-ab1b7e27b05e', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['rabbitmq_cluster_stats']


checkgroup_parameters.setdefault('rabbitmq_nodes', [])

checkgroup_parameters['rabbitmq_nodes'] = [
{'id': '4c4cecee-4d26-4a82-b3c9-0f00aed1f264', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['rabbitmq_nodes']


checkgroup_parameters.setdefault('rabbitmq_nodes_filedesc', [])

checkgroup_parameters['rabbitmq_nodes_filedesc'] = [
{'id': '36957acb-b549-4722-889b-32f5f3525c6f', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['rabbitmq_nodes_filedesc']


checkgroup_parameters.setdefault('rabbitmq_nodes_gc', [])

checkgroup_parameters['rabbitmq_nodes_gc'] = [
{'id': '311beb50-77d9-4883-926d-72e09d9d7178', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['rabbitmq_nodes_gc']


checkgroup_parameters.setdefault('rabbitmq_nodes_proc', [])

checkgroup_parameters['rabbitmq_nodes_proc'] = [
{'id': '5445dc55-b4a7-4eb8-a6d4-05576ddd64c7', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['rabbitmq_nodes_proc']


checkgroup_parameters.setdefault('rabbitmq_nodes_sockets', [])

checkgroup_parameters['rabbitmq_nodes_sockets'] = [
{'id': '880c99aa-7796-4120-965e-d47de7ef3eba', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['rabbitmq_nodes_sockets']


checkgroup_parameters.setdefault('rabbitmq_nodes_uptime', [])

checkgroup_parameters['rabbitmq_nodes_uptime'] = [
{'id': '49882f8f-0023-4edd-9c43-3f5c3efc6cf1', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['rabbitmq_nodes_uptime']


checkgroup_parameters.setdefault('rabbitmq_queues', [])

checkgroup_parameters['rabbitmq_queues'] = [
{'id': '3a8f6428-7413-480c-9b74-8c88e4729487', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['rabbitmq_queues']


checkgroup_parameters.setdefault('rabbitmq_vhosts', [])

checkgroup_parameters['rabbitmq_vhosts'] = [
{'id': '633d2f92-1726-40a6-a4ad-1c3d435a3545', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['rabbitmq_vhosts']


checkgroup_parameters.setdefault('raid_disk', [])

checkgroup_parameters['raid_disk'] = [
{'id': 'b6a64d96-7886-474d-96aa-e3b8aab9ec95', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['raid_disk']


checkgroup_parameters.setdefault('raid_summary', [])

checkgroup_parameters['raid_summary'] = [
{'id': '2e0e0f22-1262-4c70-83a0-da1dba801f96', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['raid_summary']


checkgroup_parameters.setdefault('rds_licenses', [])

checkgroup_parameters['rds_licenses'] = [
{'id': '8a531833-e6e5-4e84-af20-dab0e9475aea', 'value': {'levels': ('crit_on_all', None)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['rds_licenses']


checkgroup_parameters.setdefault('read_hits', [])

checkgroup_parameters['read_hits'] = [
{'id': 'dfa3c9f2-e6cf-44bd-bc7f-4d389fafd6e9', 'value': {'levels_lower': (85.0, 70.0)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['read_hits']


checkgroup_parameters.setdefault('redfish_storage', [])

checkgroup_parameters['redfish_storage'] = [
{'id': 'e3a74639-1992-4d09-b9a9-262ec32097cb', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['redfish_storage']


checkgroup_parameters.setdefault('redis_info', [])

checkgroup_parameters['redis_info'] = [
{'id': '02ac0ad3-0260-4f67-9b84-5a077b3cde08', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['redis_info']


checkgroup_parameters.setdefault('redis_info_clients', [])

checkgroup_parameters['redis_info_clients'] = [
{'id': 'fd6681a6-14bd-4e72-90d4-c3058a78f1ba', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['redis_info_clients']


checkgroup_parameters.setdefault('redis_info_persistence', [])

checkgroup_parameters['redis_info_persistence'] = [
{'id': '18fa71b0-fb3a-40f2-8a91-e3d8ba932aae', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['redis_info_persistence']


checkgroup_parameters.setdefault('replication_lag', [])

checkgroup_parameters['replication_lag'] = [
{'id': 'f61ef425-288d-4530-892d-6761b265a642', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['replication_lag']


checkgroup_parameters.setdefault('residual_current', [])

checkgroup_parameters['residual_current'] = [
{'id': 'edb21317-36d8-4b0a-bfe3-c6c6ba5457d8', 'value': {'warn_missing_data': True, 'warn_missing_levels': True}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['residual_current']


checkgroup_parameters.setdefault('robotmk_kpi_checking', [])

checkgroup_parameters['robotmk_kpi_checking'] = [
{'id': 'bab0b96f-8201-4198-b814-22ad84bdf307', 'value': {'runtime_thresholds': ('fixed', (0.0, 0.0))}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['robotmk_kpi_checking']


checkgroup_parameters.setdefault('robotmk_plan', [])

checkgroup_parameters['robotmk_plan'] = [
{'id': '2916b6a7-98a0-4217-8e23-58d1173364be', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['robotmk_plan']


checkgroup_parameters.setdefault('robotmk_test', [])

checkgroup_parameters['robotmk_test'] = [
{'id': 'c315906c-f44f-4e02-baa9-15f76194c2d5', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['robotmk_test']


checkgroup_parameters.setdefault('ruckus_ap', [])

checkgroup_parameters['ruckus_ap'] = [
{'id': 'a724c6a5-e2b1-4bbf-ad4d-e7bd91373a59', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['ruckus_ap']


checkgroup_parameters.setdefault('ruckus_mac', [])

checkgroup_parameters['ruckus_mac'] = [
{'id': '6044b3fe-4ec3-424d-ab64-be298b08ec7b', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['ruckus_mac']


checkgroup_parameters.setdefault('safenet_hsm_eventstats', [])

checkgroup_parameters['safenet_hsm_eventstats'] = [
{'id': '2038b527-2a24-4e42-a252-8463fc8ae8d1', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['safenet_hsm_eventstats']


checkgroup_parameters.setdefault('safenet_hsm_operstats', [])

checkgroup_parameters['safenet_hsm_operstats'] = [
{'id': 'c1e277ed-868f-47fd-9e9e-362666bea3c1', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['safenet_hsm_operstats']


checkgroup_parameters.setdefault('safenet_ntls_clients', [])

checkgroup_parameters['safenet_ntls_clients'] = [
{'id': '681913c1-49f6-4cca-bf83-59a2c37f2f32', 'value': {'levels': ('fixed', (1000, 2000))}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['safenet_ntls_clients']


checkgroup_parameters.setdefault('safenet_ntls_links', [])

checkgroup_parameters['safenet_ntls_links'] = [
{'id': '83b69a50-4718-4bf6-9dd6-6377939edf7e', 'value': {'levels': ('fixed', (1000, 2000))}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['safenet_ntls_links']


checkgroup_parameters.setdefault('sansymphony_alerts', [])

checkgroup_parameters['sansymphony_alerts'] = [
{'id': '622bfbf8-e30c-4a7b-b623-1c83c7cf2af5', 'value': {'levels': (1, 2)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['sansymphony_alerts']


checkgroup_parameters.setdefault('sansymphony_pool', [])

checkgroup_parameters['sansymphony_pool'] = [
{'id': '76d9dc31-4106-4cd5-8fc2-255d8afd7ac9', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['sansymphony_pool']


checkgroup_parameters.setdefault('sap_dialog', [])

checkgroup_parameters['sap_dialog'] = [
{'id': '35c4bcaf-ad07-4254-ba7f-aa20a0dbfc25', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['sap_dialog']


checkgroup_parameters.setdefault('sap_hana_backup', [])

checkgroup_parameters['sap_hana_backup'] = [
{'id': '89c948d7-809b-4f4e-82c2-ac5b6ae34c7f', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['sap_hana_backup']


checkgroup_parameters.setdefault('sap_hana_license', [])

checkgroup_parameters['sap_hana_license'] = [
{'id': 'bd99e569-e23f-49fa-80ff-ac9a5749f02b', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['sap_hana_license']


checkgroup_parameters.setdefault('sap_hana_memory', [])

checkgroup_parameters['sap_hana_memory'] = [
{'id': '94c998b0-9712-424e-aa13-d4a04231b92e', 'value': {'levels': ('perc_used', (80.0, 90.0))}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['sap_hana_memory']


checkgroup_parameters.setdefault('sap_hana_replication_status', [])

checkgroup_parameters['sap_hana_replication_status'] = [
{'id': '2c9b8f8c-9220-45fd-86b9-35546606ffb8', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['sap_hana_replication_status']


checkgroup_parameters.setdefault('saprouter_cert_age', [])

checkgroup_parameters['saprouter_cert_age'] = [
{'id': '60a74f6b-0182-4998-88a4-6e913d149b10', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['saprouter_cert_age']


checkgroup_parameters.setdefault('scratch_tapes', [])

checkgroup_parameters['scratch_tapes'] = [
{'id': '570e147e-7a4c-4bf7-8bc0-ae100fb7ac63', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['scratch_tapes']


checkgroup_parameters.setdefault('services', [])

checkgroup_parameters['services'] = [
{'id': 'a2c08908-bdf1-40f7-8e12-8a804c963234', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['services']


checkgroup_parameters.setdefault('services_summary', [])

checkgroup_parameters['services_summary'] = [
{'id': 'f55b3f84-c76a-4fe5-96c5-e8319a5f6d6c', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['services_summary']


checkgroup_parameters.setdefault('siemens_plc_counter', [])

checkgroup_parameters['siemens_plc_counter'] = [
{'id': 'a997675c-b1df-4ec9-8488-a0be9ad32409', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['siemens_plc_counter']


checkgroup_parameters.setdefault('siemens_plc_duration', [])

checkgroup_parameters['siemens_plc_duration'] = [
{'id': '73bff26b-fbd2-4d1c-aa73-809c2d190c16', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['siemens_plc_duration']


checkgroup_parameters.setdefault('siemens_plc_flag', [])

checkgroup_parameters['siemens_plc_flag'] = [
{'id': '022644b7-deb2-4b25-b941-58e51ee5872c', 'value': {'expected_state': True}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['siemens_plc_flag']


checkgroup_parameters.setdefault('signal_quality', [])

checkgroup_parameters['signal_quality'] = [
{'id': '49bbd6b8-e8b9-4c68-8372-3ca73f7b40e6', 'value': {'levels_lower': (0.0, 0.0)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['signal_quality']


checkgroup_parameters.setdefault('single_humidity', [])

checkgroup_parameters['single_humidity'] = [
{'id': 'e6573171-daf5-4340-9d22-9b6523829f11', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['single_humidity']


checkgroup_parameters.setdefault('skype', [])

checkgroup_parameters['skype'] = [
{'id': '27ff14aa-7c22-4b3f-a350-3fa32de6b07f', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['skype']


checkgroup_parameters.setdefault('skype_conferencing', [])

checkgroup_parameters['skype_conferencing'] = [
{'id': 'd329bd78-72a9-4725-b023-e3603c37fd39', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['skype_conferencing']


checkgroup_parameters.setdefault('skype_edge', [])

checkgroup_parameters['skype_edge'] = [
{'id': '960e506c-9e7c-44f3-be4c-3fe92cb79078', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['skype_edge']


checkgroup_parameters.setdefault('skype_edgeauth', [])

checkgroup_parameters['skype_edgeauth'] = [
{'id': '8e3e9ebe-f2fe-4c19-839b-c6c4dfccdf12', 'value': {'bad_requests': {'upper': (20, 40)}}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['skype_edgeauth']


checkgroup_parameters.setdefault('skype_mediation_server', [])

checkgroup_parameters['skype_mediation_server'] = [
{'id': '3c50a231-c74b-4a94-8bea-903be544652a', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['skype_mediation_server']


checkgroup_parameters.setdefault('skype_mobile', [])

checkgroup_parameters['skype_mobile'] = [
{'id': 'ae54e153-6152-494e-b0d8-5157fada404d', 'value': {'requests_processing': {'upper': (10000, 20000)}}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['skype_mobile']


checkgroup_parameters.setdefault('skype_proxy', [])

checkgroup_parameters['skype_proxy'] = [
{'id': 'e1888685-067b-4598-b556-1a824e77dde0', 'value': {'throttled_connections': {'upper': (3, 6)}}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['skype_proxy']


checkgroup_parameters.setdefault('skype_sip', [])

checkgroup_parameters['skype_sip'] = [
{'id': '892662eb-5323-4072-b192-2a3958a35ff3', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['skype_sip']


checkgroup_parameters.setdefault('skype_xmpp', [])

checkgroup_parameters['skype_xmpp'] = [
{'id': '8c33424e-3533-4aef-8d2c-725b01b7fe5a', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['skype_xmpp']


checkgroup_parameters.setdefault('sles_license', [])

checkgroup_parameters['sles_license'] = [
{'id': 'f18577e7-cce2-4789-831a-cea1ffbb8b66', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['sles_license']


checkgroup_parameters.setdefault('smart_ata', [])

checkgroup_parameters['smart_ata'] = [
{'id': '54184a1c-edbe-4b32-a611-2d568e4dd601', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['smart_ata']


checkgroup_parameters.setdefault('smart_nvme', [])

checkgroup_parameters['smart_nvme'] = [
{'id': 'b3a9ae2b-01a5-4c22-b8c3-0a1a4bf8fb50', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['smart_nvme']


checkgroup_parameters.setdefault('smoke', [])

checkgroup_parameters['smoke'] = [
{'id': '0dd85ec5-7100-400d-a5e2-215ffc7eb545', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['smoke']


checkgroup_parameters.setdefault('snapvault', [])

checkgroup_parameters['snapvault'] = [
{'id': '805301f3-bfec-452f-b0ec-2928575c07d6', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['snapvault']


checkgroup_parameters.setdefault('snat_usage', [])

checkgroup_parameters['snat_usage'] = [
{'id': '6b534d46-15be-4dd1-a541-d2b298ff3e10', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['snat_usage']


checkgroup_parameters.setdefault('solaris_services', [])

checkgroup_parameters['solaris_services'] = [
{'id': '73b6c528-c468-43cc-9284-52c2856a7793', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['solaris_services']


checkgroup_parameters.setdefault('solaris_services_summary', [])

checkgroup_parameters['solaris_services_summary'] = [
{'id': '847c3966-53db-46e5-8997-d0c7a77a1a1b', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['solaris_services_summary']


checkgroup_parameters.setdefault('sophos_cpu', [])

checkgroup_parameters['sophos_cpu'] = [
{'id': '01b8fe6b-f383-4086-ab39-79eda7155f5c', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['sophos_cpu']


checkgroup_parameters.setdefault('sophos_disk', [])

checkgroup_parameters['sophos_disk'] = [
{'id': '4bda658f-897e-4bb1-ae09-9bcd56a0cfc0', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['sophos_disk']


checkgroup_parameters.setdefault('sophos_memory', [])

checkgroup_parameters['sophos_memory'] = [
{'id': 'f92f4307-cca4-4843-861a-db9ea7d78e91', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['sophos_memory']


checkgroup_parameters.setdefault('splunk_alerts', [])

checkgroup_parameters['splunk_alerts'] = [
{'id': 'ea5e7a1b-c434-47a0-9457-d66d8b95dbef', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['splunk_alerts']


checkgroup_parameters.setdefault('splunk_health', [])

checkgroup_parameters['splunk_health'] = [
{'id': 'ba479af9-441c-40f8-bfbc-6f074b156bda', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['splunk_health']


checkgroup_parameters.setdefault('splunk_jobs', [])

checkgroup_parameters['splunk_jobs'] = [
{'id': '3293ed22-8f04-4d66-b806-b12772f3708a', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['splunk_jobs']


checkgroup_parameters.setdefault('splunk_license_state', [])

checkgroup_parameters['splunk_license_state'] = [
{'id': '1f30907b-8772-44ee-86d2-1cd67140a432', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['splunk_license_state']


checkgroup_parameters.setdefault('splunk_license_usage', [])

checkgroup_parameters['splunk_license_usage'] = [
{'id': 'd50dbcf5-6ff2-4758-8ab9-85d385515866', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['splunk_license_usage']


checkgroup_parameters.setdefault('sshd_config', [])

checkgroup_parameters['sshd_config'] = [
{'id': 'e2e833a2-5211-4683-b687-65be8cfe87ea', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['sshd_config']


checkgroup_parameters.setdefault('steelhead_connections', [])

checkgroup_parameters['steelhead_connections'] = [
{'id': '06309fb4-3f97-49a9-b3ff-b75b31c0ac83', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['steelhead_connections']


checkgroup_parameters.setdefault('storage_iops', [])

checkgroup_parameters['storage_iops'] = [
{'id': 'b46a3bb7-684c-4169-8071-8d25d6b4dea6', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['storage_iops']


checkgroup_parameters.setdefault('storage_throughput', [])

checkgroup_parameters['storage_throughput'] = [
{'id': 'fb6e18da-dd45-442a-aefc-fbe23335c482', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['storage_throughput']


checkgroup_parameters.setdefault('storcli_pdisks', [])

checkgroup_parameters['storcli_pdisks'] = [
{'id': '326587ad-7a9e-4a8c-9c83-e84cce6dcb9c', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['storcli_pdisks']


checkgroup_parameters.setdefault('storcli_vdrives', [])

checkgroup_parameters['storcli_vdrives'] = [
{'id': '078b2ced-d5d9-4ef2-b1d3-fb2cdb36293e', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['storcli_vdrives']


checkgroup_parameters.setdefault('stormshield_quality', [])

checkgroup_parameters['stormshield_quality'] = [
{'id': '21652fa8-e695-4d23-a968-45e8efb0aa7a', 'value': {'quality': ('fixed', (80.0, 50.0))}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['stormshield_quality']


checkgroup_parameters.setdefault('switch_contact', [])

checkgroup_parameters['switch_contact'] = [
{'id': 'c39fd443-e0b9-46e0-bd9b-084f2c5ac548', 'value': {'state': 'open'}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['switch_contact']


checkgroup_parameters.setdefault('sym_brightmail_queues', [])

checkgroup_parameters['sym_brightmail_queues'] = [
{'id': '2380d724-7ae1-49a9-88be-26b85130354b', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['sym_brightmail_queues']


checkgroup_parameters.setdefault('synology_update', [])

checkgroup_parameters['synology_update'] = [
{'id': 'd866c73e-60e4-4bfc-99ed-e29fd11fcf24', 'value': {'ok_states': [2], 'warn_states': [5], 'crit_states': [1, 4]}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['synology_update']


checkgroup_parameters.setdefault('systemd_services_summary', [])

checkgroup_parameters['systemd_services_summary'] = [
{'id': '91b4c1a6-839a-4c8d-bd24-557c89b5bcfc', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['systemd_services_summary']


checkgroup_parameters.setdefault('systemd_sockets_summary', [])

checkgroup_parameters['systemd_sockets_summary'] = [
{'id': '016c6b6b-8263-4c5e-bead-a5a9f2e1ab8c', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['systemd_sockets_summary']


checkgroup_parameters.setdefault('systemd_units_services', [])

checkgroup_parameters['systemd_units_services'] = [
{'id': 'bf342077-4917-4f31-b73f-54dc057ebb2b', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['systemd_units_services']


checkgroup_parameters.setdefault('systemd_units_sockets', [])

checkgroup_parameters['systemd_units_sockets'] = [
{'id': '7a02fb95-84b6-4bb9-a439-932cfa251cbe', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['systemd_units_sockets']


checkgroup_parameters.setdefault('systemtime', [])

checkgroup_parameters['systemtime'] = [
{'id': 'b4043e86-dc9a-42a4-a98e-aff307ba47c3', 'value': {'levels': (30, 60)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['systemtime']


checkgroup_parameters.setdefault('tcp_conn_stats', [])

checkgroup_parameters['tcp_conn_stats'] = [
{'id': '797c32cc-061b-4837-b042-d7565f6c8ed3', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['tcp_conn_stats']


checkgroup_parameters.setdefault('temperature', [])

checkgroup_parameters['temperature'] = [
{'id': 'f9158bde-5850-478f-a33a-707a1115f824', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['temperature']


checkgroup_parameters.setdefault('threads', [])

checkgroup_parameters['threads'] = [
{'id': 'fadc4077-e45e-4159-bd40-f7d6d87ced5a', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['threads']


checkgroup_parameters.setdefault('threepar_capacity', [])

checkgroup_parameters['threepar_capacity'] = [
{'id': '2d7afe16-ae69-4bab-8513-f26693235146', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['threepar_capacity']


checkgroup_parameters.setdefault('threepar_cpgs', [])

checkgroup_parameters['threepar_cpgs'] = [
{'id': 'f3714091-24e9-4fb3-ac72-3a035ad33429', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['threepar_cpgs']


checkgroup_parameters.setdefault('threepar_ports', [])

checkgroup_parameters['threepar_ports'] = [
{'id': 'dd6fcd89-0324-4aab-adea-6265ed10df9e', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['threepar_ports']


checkgroup_parameters.setdefault('threepar_remotecopy', [])

checkgroup_parameters['threepar_remotecopy'] = [
{'id': '7bef48f9-8c1a-4ab7-88c1-f89844067657', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['threepar_remotecopy']


checkgroup_parameters.setdefault('timesyncd_time', [])

checkgroup_parameters['timesyncd_time'] = [
{'id': '59554fad-1c12-4dbc-abc4-daa28e4bd33c', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['timesyncd_time']


checkgroup_parameters.setdefault('ucs_bladecenter_chassis_voltage', [])

checkgroup_parameters['ucs_bladecenter_chassis_voltage'] = [
{'id': 'ecb573df-64bd-4479-b0a0-eaf0229e8044', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['ucs_bladecenter_chassis_voltage']


checkgroup_parameters.setdefault('ucs_bladecenter_faultinst', [])

checkgroup_parameters['ucs_bladecenter_faultinst'] = [
{'id': 'e46b75a0-66e2-4090-a532-9c65857491ca', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['ucs_bladecenter_faultinst']


checkgroup_parameters.setdefault('ucs_c_rack_server_led', [])

checkgroup_parameters['ucs_c_rack_server_led'] = [
{'id': '5ce490f5-3f3d-42d6-8d64-134dd45b70fc', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['ucs_c_rack_server_led']


checkgroup_parameters.setdefault('ups_capacity', [])

checkgroup_parameters['ups_capacity'] = [
{'id': '544e42b6-f5a5-414a-86de-3d60a00b4607', 'value': {'capacity': (95, 90)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['ups_capacity']


checkgroup_parameters.setdefault('ups_out_load', [])

checkgroup_parameters['ups_out_load'] = [
{'id': '4b7daaf1-ed05-4d27-8945-b42959acbd33', 'value': {'levels': (85, 90)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['ups_out_load']


checkgroup_parameters.setdefault('ups_outphase', [])

checkgroup_parameters['ups_outphase'] = [
{'id': '3fcd019a-2acf-4ca7-a63a-5c3ec1e6be22', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['ups_outphase']


checkgroup_parameters.setdefault('ups_test', [])

checkgroup_parameters['ups_test'] = [
{'id': '22e17c30-e533-4248-8a87-e71878bc810d', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['ups_test']


checkgroup_parameters.setdefault('uptime', [])

checkgroup_parameters['uptime'] = [
{'id': '79c35c72-e708-4e4c-8f23-7fa77d52da39', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['uptime']


checkgroup_parameters.setdefault('uptime_multiitem', [])

checkgroup_parameters['uptime_multiitem'] = [
{'id': '7b941919-3a4f-469a-bb6b-c2606f48762a', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['uptime_multiitem']


checkgroup_parameters.setdefault('varnish_backend', [])

checkgroup_parameters['varnish_backend'] = [
{'id': 'cc511e1a-1722-4b7b-96ca-192462774412', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['varnish_backend']


checkgroup_parameters.setdefault('varnish_backend_success_ratio', [])

checkgroup_parameters['varnish_backend_success_ratio'] = [
{'id': '258f0a3f-9d7e-42a4-9ef9-3ddd58ac0c77', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['varnish_backend_success_ratio']


checkgroup_parameters.setdefault('varnish_cache', [])

checkgroup_parameters['varnish_cache'] = [
{'id': '906e21c7-3c9f-4aef-805a-3b4a1b92e6c2', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['varnish_cache']


checkgroup_parameters.setdefault('varnish_cache_hit_ratio', [])

checkgroup_parameters['varnish_cache_hit_ratio'] = [
{'id': '38a33281-2ae9-4962-9074-8cc3831e39bb', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['varnish_cache_hit_ratio']


checkgroup_parameters.setdefault('varnish_client', [])

checkgroup_parameters['varnish_client'] = [
{'id': '50b4eb56-8756-4148-aa94-ffefb97637cc', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['varnish_client']


checkgroup_parameters.setdefault('varnish_esi', [])

checkgroup_parameters['varnish_esi'] = [
{'id': '9d774fb1-d0ca-4408-b1a6-32b5c8d4e3f7', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['varnish_esi']


checkgroup_parameters.setdefault('varnish_fetch', [])

checkgroup_parameters['varnish_fetch'] = [
{'id': '23a1c6c5-1660-4f5b-afc7-a3f21a8f395a', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['varnish_fetch']


checkgroup_parameters.setdefault('varnish_objects', [])

checkgroup_parameters['varnish_objects'] = [
{'id': '5d1b016d-4499-4e68-8e94-24fb7615ed2e', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['varnish_objects']


checkgroup_parameters.setdefault('varnish_worker', [])

checkgroup_parameters['varnish_worker'] = [
{'id': '3b6fca27-2e63-426f-a91a-1e4ca249d03c', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['varnish_worker']


checkgroup_parameters.setdefault('varnish_worker_thread_ratio', [])

checkgroup_parameters['varnish_worker_thread_ratio'] = [
{'id': 'f9aee1dc-1f79-4f11-9d02-b0de295d7b10', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['varnish_worker_thread_ratio']


checkgroup_parameters.setdefault('veeam_backup', [])

checkgroup_parameters['veeam_backup'] = [
{'id': 'e36a8318-40d1-43bc-b20b-169afa0ca84b', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['veeam_backup']


checkgroup_parameters.setdefault('veeam_cdp_jobs', [])

checkgroup_parameters['veeam_cdp_jobs'] = [
{'id': '3ef4b142-7fa5-4fa3-aafa-fe95927d6ae9', 'value': {'age': (108000, 172800)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['veeam_cdp_jobs']


checkgroup_parameters.setdefault('veeam_tapejobs', [])

checkgroup_parameters['veeam_tapejobs'] = [
{'id': 'ac73039b-b8c6-455c-a4c6-23d670f139f7', 'value': {'levels_upper': (0, 0)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['veeam_tapejobs']


checkgroup_parameters.setdefault('veritas_vcs', [])

checkgroup_parameters['veritas_vcs'] = [
{'id': '2fe72d13-6602-4287-9fe8-59228620bafc', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['veritas_vcs']


checkgroup_parameters.setdefault('viprinet_router', [])

checkgroup_parameters['viprinet_router'] = [
{'id': 'cbc0dbea-5c5d-4ac9-b30a-64067319d754', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['viprinet_router']


checkgroup_parameters.setdefault('vm_guest_tools', [])

checkgroup_parameters['vm_guest_tools'] = [
{'id': '703f82e7-ee0f-4178-8eef-55bb2e7c955e', 'value': {'guestToolsCurrent': 0, 'guestToolsNeedUpgrade': 1, 'guestToolsNotInstalled': 2, 'guestToolsUnmanaged': 0}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['vm_guest_tools']


checkgroup_parameters.setdefault('vm_heartbeat', [])

checkgroup_parameters['vm_heartbeat'] = [
{'id': '7ffceed8-5785-40bf-ad4f-bb8800fc627c', 'value': {'heartbeat_missing': 2, 'heartbeat_intermittend': 1, 'heartbeat_no_tools': 1, 'heartbeat_ok': 0}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['vm_heartbeat']


checkgroup_parameters.setdefault('vm_snapshots', [])

checkgroup_parameters['vm_snapshots'] = [
{'id': '14017cc1-16c2-4513-9e95-3d0368f83349', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['vm_snapshots']


checkgroup_parameters.setdefault('vms_procs', [])

checkgroup_parameters['vms_procs'] = [
{'id': 'a45fa4ba-ce53-4b57-a083-2b68b7b488ae', 'value': {'levels_upper': None}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['vms_procs']


checkgroup_parameters.setdefault('voltage', [])

checkgroup_parameters['voltage'] = [
{'id': 'eabc8ce1-9c24-4366-b658-cb222076f1b5', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['voltage']


checkgroup_parameters.setdefault('volume_groups', [])

checkgroup_parameters['volume_groups'] = [
{'id': 'b6f3134a-3be1-4d57-9d7d-b5e1d74e10b2', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['volume_groups']


checkgroup_parameters.setdefault('vpn_tunnel', [])

checkgroup_parameters['vpn_tunnel'] = [
{'id': '24bd192c-019c-4263-8904-ce08402a93b1', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['vpn_tunnel']


checkgroup_parameters.setdefault('w32time_peers', [])

checkgroup_parameters['w32time_peers'] = [
{'id': '31c083de-c066-478e-97ca-003e54da84c5', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['w32time_peers']


checkgroup_parameters.setdefault('w32time_peers_summary', [])

checkgroup_parameters['w32time_peers_summary'] = [
{'id': '6c748b70-52bf-427e-93f6-cd1b4a0cb84b', 'value': {'universal': False}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['w32time_peers_summary']


checkgroup_parameters.setdefault('w32time_status', [])

checkgroup_parameters['w32time_status'] = [
{'id': 'ca3953dc-d2b4-404c-9ce7-14d61811826a', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['w32time_status']


checkgroup_parameters.setdefault('webserver', [])

checkgroup_parameters['webserver'] = [
{'id': '364f37ad-e6b0-43a5-b4e4-54da659ebb2c', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['webserver']


checkgroup_parameters.setdefault('win_dhcp_pools', [])

checkgroup_parameters['win_dhcp_pools'] = [
{'id': 'e430ec53-247a-4851-8d3f-4b3b0e1745b9', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['win_dhcp_pools']


checkgroup_parameters.setdefault('win_license', [])

checkgroup_parameters['win_license'] = [
{'id': 'bfa29207-512d-4e5c-a8a0-561fc9782646', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['win_license']


checkgroup_parameters.setdefault('windows_multipath', [])

checkgroup_parameters['windows_multipath'] = [
{'id': '22aca362-b408-40bb-ae40-b79a7fb86675', 'value': {'active_paths': 0}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['windows_multipath']


checkgroup_parameters.setdefault('windows_printer_queues', [])

checkgroup_parameters['windows_printer_queues'] = [
{'id': '38ff2fa4-0226-40b1-87ba-ecbcad62e19e', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['windows_printer_queues']


checkgroup_parameters.setdefault('windows_tasks', [])

checkgroup_parameters['windows_tasks'] = [
{'id': 'd23e5740-4079-4256-8cf7-6408cb21996f', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['windows_tasks']


checkgroup_parameters.setdefault('windows_updates', [])

checkgroup_parameters['windows_updates'] = [
{'id': '93c0fea8-7988-4de7-8ece-fbf7be1f331f', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['windows_updates']


checkgroup_parameters.setdefault('winperf_ts_sessions', [])

checkgroup_parameters['winperf_ts_sessions'] = [
{'id': '7ad78a1f-6688-4fec-a26b-f4bd44a6a523', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['winperf_ts_sessions']


checkgroup_parameters.setdefault('wlc_clients', [])

checkgroup_parameters['wlc_clients'] = [
{'id': 'dcc196bd-fcf5-480e-a28e-c4816f4ea30e', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['wlc_clients']


checkgroup_parameters.setdefault('wut_webio', [])

checkgroup_parameters['wut_webio'] = [
{'id': '8045d022-ca61-44e7-b116-ec393d0e2c41', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['wut_webio']


checkgroup_parameters.setdefault('zorp_connections', [])

checkgroup_parameters['zorp_connections'] = [
{'id': '2826f2bc-3ad5-4c70-bc11-54b8b504a56b', 'value': {'levels': ('fixed', (15, 20))}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['zorp_connections']


checkgroup_parameters.setdefault('zypper', [])

checkgroup_parameters['zypper'] = [
{'id': '2721272d-9990-4fba-b649-0e47f2f086e8', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['zypper']


globals().setdefault('clustered_services', [])

clustered_services = [
{'id': 'b72f8667-6aad-4503-a10d-e3509b381fc1', 'value': True, 'condition': {}, 'options': {'disabled': False}},
] + clustered_services


globals().setdefault('clustered_services_configuration', [])

clustered_services_configuration = [
{'id': '59164424-ef6c-47f0-b8eb-fc61e3d62dc8', 'value': ('native', {}), 'condition': {}, 'options': {'disabled': False}},
] + clustered_services_configuration


globals().setdefault('clustered_services_mapping', [])

clustered_services_mapping = [
{'id': 'd58ca113-4a20-4cf9-935a-4fb27212c8fd', 'value': '', 'condition': {}, 'options': {'disabled': False}},
] + clustered_services_mapping


globals().setdefault('cmc_graphite_host_metrics', [])

cmc_graphite_host_metrics = [
{'id': '536b1ebf-742a-4fd4-ad76-5b00ed8655e7', 'value': ['VALUE'], 'condition': {}, 'options': {'disabled': False}},
] + cmc_graphite_host_metrics


globals().setdefault('cmc_graphite_service_metrics', [])

cmc_graphite_service_metrics = [
{'id': '770255fb-8c03-438e-829e-8447c6a8df59', 'value': ['VALUE'], 'condition': {}, 'options': {'disabled': False}},
] + cmc_graphite_service_metrics


globals().setdefault('cmc_service_check_timeout', [])

cmc_service_check_timeout = [
{'id': 'e09dac82-a9f3-414b-9b9c-a4e740df5c92', 'value': 60, 'condition': {}, 'options': {'disabled': False}},
] + cmc_service_check_timeout


globals().setdefault('cmc_service_flap_settings', [])

cmc_service_flap_settings = [
{'id': '511504d1-0761-4875-9738-569877b0009e', 'value': (3.0, 5.0, 0.1), 'condition': {}, 'options': {'disabled': False}},
] + cmc_service_flap_settings


globals().setdefault('cmc_service_long_output_in_monitoring_history', [])

cmc_service_long_output_in_monitoring_history = [
{'id': '5a899103-db59-4b98-a4f5-85dccf21386d', 'value': False, 'condition': {}, 'options': {'disabled': False}},
] + cmc_service_long_output_in_monitoring_history


globals().setdefault('cmc_service_rrd_config', [])

cmc_service_rrd_config = [
{'id': '4f2d1723-bae6-40c0-8c04-54f64f790afb', 'value': {'format': 'cmc_single', 'cfs': ['MIN', 'MAX', 'AVERAGE'], 'step': 60, 'rras': [(50.0, 1, 2880), (50.0, 5, 2880), (50.0, 30, 4320), (50.0, 360, 5840)]}, 'condition': {}, 'options': {'disabled': False}},
] + cmc_service_rrd_config


globals().setdefault('cpu_utilization_multiitem_discovery', [])

cpu_utilization_multiitem_discovery = [
{'id': '528e790d-32ee-4b43-aea8-b2c77b3d8c37', 'value': {'individual': True}, 'condition': {}, 'options': {'disabled': False}},
] + cpu_utilization_multiitem_discovery


globals().setdefault('custom_checks', [])

custom_checks = [
{'id': '51474042-db29-4124-ae54-7f2e77ced8d8', 'value': {'service_description': 'Example check'}, 'condition': {}, 'options': {'disabled': False}},
] + custom_checks


globals().setdefault('custom_service_attributes', [])

custom_service_attributes = [
{'id': '47550b03-dccb-472a-89c8-6536f0a2d6d3', 'value': [('EXAMPLE_ATTR', 'example_value')], 'condition': {}, 'options': {'disabled': False}},
] + custom_service_attributes


globals().setdefault('datadog_monitors_discovery', [])

datadog_monitors_discovery = [
{'id': '6a42818a-327a-4151-aa0a-b8ac973ab5a7', 'value': {'states_discover': ['Alert', 'Ignored', 'No Data', 'OK', 'Skipped', 'Unknown', 'Warn']}, 'condition': {}, 'options': {'disabled': False}},
] + datadog_monitors_discovery


globals().setdefault('discovery_alertmanager', [])

discovery_alertmanager = [
{'id': '91818d59-9557-41a3-a37b-3b85985143e5', 'value': {'group_services': ('one_service', None)}, 'condition': {}, 'options': {'disabled': False}},
] + discovery_alertmanager


globals().setdefault('discovery_cisco_dom_rules', [])

discovery_cisco_dom_rules = [
{'id': '467401ac-11ec-4923-be56-b325f687867c', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + discovery_cisco_dom_rules


globals().setdefault('discovery_cisco_meraki_switch_ports_statuses', [])

discovery_cisco_meraki_switch_ports_statuses = [
{'id': '1ba48639-4af2-4083-8b59-5454526f383e', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + discovery_cisco_meraki_switch_ports_statuses


globals().setdefault('discovery_cmciii', [])

discovery_cmciii = [
{'id': '3bd82605-5f22-48df-8390-1533aa52a5c3', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + discovery_cmciii


globals().setdefault('discovery_hr_processes_rules', [])

discovery_hr_processes_rules = [
{'id': '8db617be-c0c8-4eee-a074-1ea97b05e4c6', 'value': {'descr': 'Example Process', 'default_params': {}}, 'condition': {}, 'options': {'disabled': False}},
] + discovery_hr_processes_rules


globals().setdefault('discovery_mssql_backup', [])

discovery_mssql_backup = [
{'id': '93fb5a97-dabf-49c0-9958-a86f698beb7a', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + discovery_mssql_backup


globals().setdefault('discovery_netapp_api_fan_rules', [])

discovery_netapp_api_fan_rules = [
{'id': '534461fc-b7d4-40e9-9610-e7f4093273cc', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + discovery_netapp_api_fan_rules


globals().setdefault('discovery_netapp_api_ports_ignored', [])

discovery_netapp_api_ports_ignored = [
{'id': '427d8a18-ca12-4663-9b3e-42376ed5027f', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + discovery_netapp_api_ports_ignored


globals().setdefault('discovery_netapp_api_psu_rules', [])

discovery_netapp_api_psu_rules = [
{'id': '53afb4e1-d5b8-4775-9ac6-d83765c18349', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + discovery_netapp_api_psu_rules


globals().setdefault('discovery_qtree', [])

discovery_qtree = [
{'id': 'c89bab97-96f2-42d1-8478-e0b65d706b66', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + discovery_qtree


globals().setdefault('discovery_redfish_drives', [])

discovery_redfish_drives = [
{'id': '0351d5f8-5156-4eb8-8806-e3f4f1a6d05b', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + discovery_redfish_drives


globals().setdefault('discovery_redfish_ethernetinterfaces', [])

discovery_redfish_ethernetinterfaces = [
{'id': '4bae4613-d0cd-4e62-9590-0e8079044a61', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + discovery_redfish_ethernetinterfaces


globals().setdefault('discovery_redfish_outlets', [])

discovery_redfish_outlets = [
{'id': '3848c64c-afab-4d9c-8ae2-288211330a9f', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + discovery_redfish_outlets


globals().setdefault('discovery_redfish_volumes', [])

discovery_redfish_volumes = [
{'id': '5f57f9a3-3938-4691-a1c6-460f5a2639d9', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + discovery_redfish_volumes


globals().setdefault('discovery_rules_vnx_quotas', [])

discovery_rules_vnx_quotas = [
{'id': '8f31f8da-e3aa-4351-87ef-8920c4886012', 'value': {'dms_names': [], 'mp_names': []}, 'condition': {}, 'options': {'disabled': False}},
] + discovery_rules_vnx_quotas


globals().setdefault('discovery_snapvault', [])

discovery_snapvault = [
{'id': 'a77f11c6-ffc1-4a81-8fdd-5b6ad91bd6eb', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + discovery_snapvault


globals().setdefault('discovery_systemd_units_services', [])

discovery_systemd_units_services = [
{'id': 'f0cd4e7c-3970-45ec-91c7-bb5079ba7b92', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + discovery_systemd_units_services


globals().setdefault('discovery_systemd_units_sockets', [])

discovery_systemd_units_sockets = [
{'id': '4d0ca33d-62ec-40ba-abc1-295d009a455d', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + discovery_systemd_units_sockets


globals().setdefault('discovery_win_dhcp_pools', [])

discovery_win_dhcp_pools = [
{'id': '46458ea5-b4b5-4f7e-bc7a-38104b28290f', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + discovery_win_dhcp_pools


globals().setdefault('diskstat_inventory', [])

diskstat_inventory = [
{'id': '9f6ed96c-34f0-4d37-bbcd-ab9da9d553ad', 'value': {'summary': True, 'lvm': False, 'vxvm': False, 'diskless': False}, 'condition': {}, 'options': {'disabled': False}},
] + diskstat_inventory


globals().setdefault('dyndns_hosts', [])

dyndns_hosts = [
{'id': 'b55650aa-d007-4a34-9a71-899ffb581542', 'value': True, 'condition': {}, 'options': {'disabled': False}},
] + dyndns_hosts


globals().setdefault('elasticsearch_indices_disovery', [])

elasticsearch_indices_disovery = [
{'id': 'a3891f5b-f160-4a29-ac02-bd09aada5e13', 'value': {'grouping': ('enabled', ['example'])}, 'condition': {}, 'options': {'disabled': False}},
] + elasticsearch_indices_disovery


globals().setdefault('esx_vsphere_objects_discovery', [])

esx_vsphere_objects_discovery = [
{'id': '9dcf8de8-7652-4903-8df0-6240901ed027', 'value': {'templates': True}, 'condition': {}, 'options': {'disabled': False}},
] + esx_vsphere_objects_discovery


globals().setdefault('ewon_discovery_rules', [])

ewon_discovery_rules = [
{'id': '27cba969-ed6c-40e1-90cd-a05bfff27977', 'value': {'device': None}, 'condition': {}, 'options': {'disabled': False}},
] + ewon_discovery_rules


extra_host_conf.setdefault('notification_options', [])

extra_host_conf['notification_options'] = [
{'id': '814bf932-6341-4f96-983d-283525b5416d', 'value': 'd,r,f,s', 'condition': {}},
] + extra_host_conf['notification_options']


extra_service_conf.setdefault('_ESCAPE_PLUGIN_OUTPUT', [])

extra_service_conf['_ESCAPE_PLUGIN_OUTPUT'] = [
{'id': '23f617c4-5d9e-46cb-8f59-e1a1c0d711ac', 'value': '1', 'condition': {}, 'options': {'disabled': False}},
] + extra_service_conf['_ESCAPE_PLUGIN_OUTPUT']


extra_service_conf.setdefault('_ec_sl', [])

extra_service_conf['_ec_sl'] = [
{'id': 'f3177783-8f93-42cf-a116-ebabb6ed2f72', 'value': 0, 'condition': {}, 'options': {'disabled': False}},
] + extra_service_conf['_ec_sl']


extra_service_conf.setdefault('_sla_config', [])

extra_service_conf['_sla_config'] = [
{'id': 'd9ece721-ba1e-4d2d-921c-beab94153c7c', 'value': '', 'condition': {}, 'options': {'disabled': False}},
] + extra_service_conf['_sla_config']


extra_service_conf.setdefault('active_checks_enabled', [])

extra_service_conf['active_checks_enabled'] = [
{'id': 'cf184240-0086-49d3-a1f4-14d13af6cbc3', 'value': '1', 'condition': {}, 'options': {'disabled': False}},
] + extra_service_conf['active_checks_enabled']


extra_service_conf.setdefault('check_interval', [])

extra_service_conf['check_interval'] = [
{'id': 'b3847203-84b3-4f5b-ac67-0f06d4403905', 'value': 1440, 'condition': {'service_description': [{'$regex': 'Check_MK HW/SW Inventory$'}]}, 'options': {'description': 'Restrict HW/SW Inventory to once a day'}},
] + extra_service_conf['check_interval']


extra_service_conf.setdefault('check_period', [])

extra_service_conf['check_period'] = [
{'id': '4f4b32e5-54e4-40eb-a1aa-5bf86e9c248a', 'value': '24X7', 'condition': {}, 'options': {'disabled': False}},
] + extra_service_conf['check_period']


extra_service_conf.setdefault('display_name', [])

extra_service_conf['display_name'] = [
{'id': 'fd2e0140-71b8-44f5-84cb-7c5feb8f1243', 'value': '', 'condition': {}, 'options': {'disabled': False}},
] + extra_service_conf['display_name']


extra_service_conf.setdefault('first_notification_delay', [])

extra_service_conf['first_notification_delay'] = [
{'id': '887827f3-4500-483b-99dc-c909262d1603', 'value': 5.0, 'condition': {}, 'options': {'disabled': False}},
] + extra_service_conf['first_notification_delay']


extra_service_conf.setdefault('flap_detection_enabled', [])

extra_service_conf['flap_detection_enabled'] = [
{'id': '4215f625-ad92-4d04-8694-e3bc16340c7a', 'value': '1', 'condition': {}, 'options': {'disabled': False}},
] + extra_service_conf['flap_detection_enabled']


extra_service_conf.setdefault('icon_image', [])

extra_service_conf['icon_image'] = [
{'id': '17a81287-4638-4db1-9525-18923e1dc716', 'value': None, 'condition': {}, 'options': {'disabled': False}},
] + extra_service_conf['icon_image']


extra_service_conf.setdefault('max_check_attempts', [])

extra_service_conf['max_check_attempts'] = [
{'id': '4c9e9cc8-0406-44ea-be5e-1de708516a1d', 'value': 1, 'condition': {}, 'options': {'disabled': False}},
] + extra_service_conf['max_check_attempts']


extra_service_conf.setdefault('notes_url', [])

extra_service_conf['notes_url'] = [
{'id': '28b04d4e-f67e-4364-967a-3dcd3869602d', 'value': '', 'condition': {}, 'options': {'disabled': False}},
] + extra_service_conf['notes_url']


extra_service_conf.setdefault('notification_interval', [])

extra_service_conf['notification_interval'] = [
{'id': 'a01b666b-324d-4bcc-a41d-8ad76fa05b51', 'value': None, 'condition': {}, 'options': {'disabled': False}},
] + extra_service_conf['notification_interval']


extra_service_conf.setdefault('notification_options', [])

extra_service_conf['notification_options'] = [
{'id': 'd46b6075-027b-4f59-9bcb-af744e650315', 'value': 'w,u,c,r,f,s', 'condition': {}, 'options': {'disabled': False}},
] + extra_service_conf['notification_options']


extra_service_conf.setdefault('notification_period', [])

extra_service_conf['notification_period'] = [
{'id': 'bd0b38e3-1436-4dc5-93be-ac464bf72f86', 'value': '24X7', 'condition': {}, 'options': {'disabled': False}},
] + extra_service_conf['notification_period']


extra_service_conf.setdefault('notifications_enabled', [])

extra_service_conf['notifications_enabled'] = [
{'id': '78bb6aa1-6c01-44b1-8e87-9016cf03f68a', 'value': '1', 'condition': {}, 'options': {'disabled': False}},
] + extra_service_conf['notifications_enabled']


extra_service_conf.setdefault('passive_checks_enabled', [])

extra_service_conf['passive_checks_enabled'] = [
{'id': '988e90e8-dd9f-4bcf-84ce-b1416ab4594b', 'value': '1', 'condition': {}, 'options': {'disabled': False}},
] + extra_service_conf['passive_checks_enabled']


extra_service_conf.setdefault('process_perf_data', [])

extra_service_conf['process_perf_data'] = [
{'id': '1098c10e-4cbc-4154-980a-dedf43337f0a', 'value': '1', 'condition': {}, 'options': {'disabled': False}},
] + extra_service_conf['process_perf_data']


extra_service_conf.setdefault('retry_interval', [])

extra_service_conf['retry_interval'] = [
{'id': 'f4f1fbce-b444-4bff-90b5-0dd3e7bfe170', 'value': 1.0, 'condition': {}, 'options': {'disabled': False}},
] + extra_service_conf['retry_interval']


extra_service_conf.setdefault('service_period', [])

extra_service_conf['service_period'] = [
{'id': '8e0d8e9b-5e7d-423f-b9de-2f8e7b16b288', 'value': '24X7', 'condition': {}, 'options': {'disabled': False}},
] + extra_service_conf['service_period']


globals().setdefault('fileinfo_groups', [])

fileinfo_groups = [
{'id': '6fd7cfbb-7806-4a37-bf04-8925a63cbd4c', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + fileinfo_groups


globals().setdefault('filesystem_groups', [])

filesystem_groups = [
{'id': '22592a2f-e2df-4301-97bd-d5d30cadb1d3', 'value': {'groups': []}, 'condition': {}, 'options': {'disabled': False}},
] + filesystem_groups


globals().setdefault('host_check_commands', [])

host_check_commands = [
{'id': '24da4ccd-0d1b-40e3-af87-0097df8668f2', 'value': ('service', 'Docker container status'), 'condition': {'host_label_groups': [('and', [('and', 'cmk/docker_object:container')])]}, 'options': {'description': 'Make all docker container host states base on the "Docker container status" service'}},
] + host_check_commands


globals().setdefault('host_contactgroups', [])

host_contactgroups = [
{'id': 'efd67dab-68f8-4d3c-a417-9f7e29ab48d5', 'value': 'all', 'condition': {}, 'options': {'description': 'Put all hosts into the contact group "all"'}},
] + host_contactgroups


globals().setdefault('ignored_checks', [])

ignored_checks = [
{'id': 'c258185f-0962-4909-ba7e-bdc82400657e', 'value': [], 'condition': {}, 'options': {'disabled': False}},
] + ignored_checks


globals().setdefault('ignored_services', [])

ignored_services = [
{'id': 'f8c38924-0787-430a-a1dc-802e1a92d99d', 'value': True, 'condition': {}, 'options': {'disabled': False}},
] + ignored_services


globals().setdefault('inv_domino_tasks_rules', [])

inv_domino_tasks_rules = [
{'id': '43047ad2-c52a-49c9-bf26-e7b7309e39d0', 'value': {'descr': 'Example Process', 'match': 'foo', 'default_params': {'levels': (1, 1, 99999, 99999)}}, 'condition': {}, 'options': {'disabled': False}},
] + inv_domino_tasks_rules


globals().setdefault('inventory_df_rules', [])

inventory_df_rules = [
{'id': 'b0ee8a51-703c-47e4-aec4-76430281604d', 'value': {'ignore_fs_types': ['tmpfs', 'nfs', 'smbfs', 'cifs', 'iso9660'], 'never_ignore_mountpoints': ['~.*/omd/sites/[^/]+/tmp$']}, 'condition': {'host_label_groups': [('and', [('and', 'cmk/check_mk_server:yes'), ('and', '')])]}},
] + inventory_df_rules


globals().setdefault('inventory_fujitsu_ca_ports', [])

inventory_fujitsu_ca_ports = [
{'id': '16eeb257-f746-4492-b754-3ea8ea3fefea', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + inventory_fujitsu_ca_ports


globals().setdefault('inventory_heartbeat_crm_rules', [])

inventory_heartbeat_crm_rules = [
{'id': '881a7632-f34b-4d8b-b165-2ca9d3f98350', 'value': {'naildown_dc': False, 'naildown_resources': False}, 'condition': {}, 'options': {'disabled': False}},
] + inventory_heartbeat_crm_rules


globals().setdefault('inventory_if_rules', [])

inventory_if_rules = [
{'id': '47bdcb52-c917-4b22-8268-aaef98d74879', 'value': {'discovery_single': (True, {'item_appearance': 'index', 'pad_portnumbers': True}), 'matching_conditions': (True, {})}, 'condition': {}, 'options': {'disabled': False}},
] + inventory_if_rules


globals().setdefault('inventory_ipmi_rules', [])

inventory_ipmi_rules = [
{'id': '65a8aabe-9c7f-4f23-b26f-01217f55fd8f', 'value': {'discovery_mode': ('summarize', {})}, 'condition': {}, 'options': {'disabled': False}},
] + inventory_ipmi_rules


globals().setdefault('inventory_mssql_counters_rules', [])

inventory_mssql_counters_rules = [
{'id': '65ba2e7d-052f-4cee-a57f-a6afe092d4af', 'value': {'add_zero_based_services': False}, 'condition': {}, 'options': {'disabled': False}},
] + inventory_mssql_counters_rules


globals().setdefault('inventory_multipath_rules', [])

inventory_multipath_rules = [
{'id': 'f46212f8-f9d5-49d7-81b4-68a3efed5c81', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + inventory_multipath_rules


globals().setdefault('inventory_processes_rules', [])

inventory_processes_rules = [
{'id': 'da7e80af-e863-4e14-bd8b-15173aa26d5d', 'value': {'descr': 'example', 'default_params': {'cpu_rescale_max': True}}, 'condition': {}, 'options': {'disabled': False}},
] + inventory_processes_rules


globals().setdefault('inventory_sap_values', [])

inventory_sap_values = [
{'id': '3b4e13f7-425b-4850-b7db-8591df0fa0a3', 'value': {'match': ('exact', 'SAP CCMS Monitor Templates/Dialog Overview/Dialog Response Time/ResponseTime')}, 'condition': {}, 'options': {'disabled': False}},
] + inventory_sap_values


globals().setdefault('inventory_services_rules', [])

inventory_services_rules = [
{'id': 'b4951872-c869-4b42-bf35-ef06ce1151a4', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + inventory_services_rules


globals().setdefault('inventory_solaris_services_rules', [])

inventory_solaris_services_rules = [
{'id': 'b6982924-dae0-4d38-8c6c-ffc4dc6fd5bb', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + inventory_solaris_services_rules


globals().setdefault('logwatch_groups', [])

logwatch_groups = [
{'id': '66475027-4993-4995-a149-136e042f032d', 'value': {'grouping_patterns': []}, 'condition': {}, 'options': {'disabled': False}},
] + logwatch_groups


globals().setdefault('logwatch_rules', [])

logwatch_rules = [
{'id': '4872aa89-83a5-4040-970f-2722074df2f3', 'value': {'reclassify_patterns': []}, 'condition': {}, 'options': {'disabled': False}},
] + logwatch_rules


globals().setdefault('management_board_config', [])

management_board_config = [
{'id': 'b9fd5b3b-8c9f-4068-826c-c910cbcc9311', 'value': ('snmp', 'public'), 'condition': {}, 'options': {'disabled': False}},
] + management_board_config


globals().setdefault('management_bulkwalk_hosts', [])

management_bulkwalk_hosts = [
{'id': '59d84cde-ee3a-4f8d-8bec-fce35a2b0d15', 'value': True, 'condition': {}, 'options': {'description': 'All management boards use SNMPv2 and bulk walk'}},
] + management_bulkwalk_hosts


globals().setdefault('mssql_transactionlogs_discovery', [])

mssql_transactionlogs_discovery = [
{'id': '933a2cca-99f3-4c11-8237-999f1790e24f', 'value': {'summarize_datafiles': False, 'summarize_transactionlogs': False}, 'condition': {}, 'options': {'disabled': False}},
] + mssql_transactionlogs_discovery


notification_parameters.setdefault('asciimail', [])

notification_parameters['asciimail'] = [
{'id': '2e5cc777-9fb0-4095-bf58-ab308ec55c52', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + notification_parameters['asciimail']


notification_parameters.setdefault('cisco_webex_teams', [])

notification_parameters['cisco_webex_teams'] = [
{'id': 'd48f73ba-35b1-4ee9-8274-ed2f60b8d3ef', 'value': {'webhook_url': ('webhook_url', 'https://hooks.example.com/services/example/webhook')}, 'condition': {}, 'options': {'disabled': False}},
] + notification_parameters['cisco_webex_teams']


notification_parameters.setdefault('ilert', [])

notification_parameters['ilert'] = [
{'id': '0479838f-c124-430a-889c-37035d19932c', 'value': {'ilert_api_key': ('cmk_postprocessed', 'explicit_password', ('uuid4c0e0979-710c-4a08-925a-0e4ae5608e6d', 'example_api_key_12345'))}, 'condition': {}, 'options': {'disabled': False}},
] + notification_parameters['ilert']


notification_parameters.setdefault('jira_issues', [])

notification_parameters['jira_issues'] = [
{'id': '1fbb3baa-2d39-406f-a042-dec8294b1d7e', 'value': {'url': 'https://example.com', 'auth': ('auth_basic', {'username': 'admin', 'password': ('cmk_postprocessed', 'explicit_password', ('uuid1662119b-3a3e-4a07-b862-f20414b89e36', 'example_password_123'))}), 'project': 'EXAMPLE', 'issuetype': 'Bug', 'host_customid': 'example_value', 'service_customid': 'example_value', 'monitoring': 'https://monitoring.example.com'}, 'condition': {}, 'options': {'disabled': False}},
] + notification_parameters['jira_issues']


notification_parameters.setdefault('mail', [])

notification_parameters['mail'] = [
{'id': '1f60e04e-06bd-4172-b919-bfb6c2fabdd6', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + notification_parameters['mail']


notification_parameters.setdefault('mkeventd', [])

notification_parameters['mkeventd'] = [
{'id': 'fa485448-ca9e-4ff0-84dc-f7d125392ccb', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + notification_parameters['mkeventd']


notification_parameters.setdefault('msteams', [])

notification_parameters['msteams'] = [
{'id': '16e65f9f-2461-40aa-a854-196082863aba', 'value': {'webhook_url': ('webhook_url', 'https://hooks.example.com/services/example/webhook')}, 'condition': {}, 'options': {'disabled': False}},
] + notification_parameters['msteams']


notification_parameters.setdefault('opsgenie_issues', [])

notification_parameters['opsgenie_issues'] = [
{'id': '8596b8e7-552a-4efc-82e4-5b540522fb0e', 'value': {'password': ('cmk_postprocessed', 'explicit_password', ('uuid46e65c13-fb2c-4830-bd88-11db9738eded', 'example_password_123'))}, 'condition': {}, 'options': {'disabled': False}},
] + notification_parameters['opsgenie_issues']


notification_parameters.setdefault('pagerduty', [])

notification_parameters['pagerduty'] = [
{'id': 'fc08c09b-5535-456a-aa59-40244e0d390c', 'value': {'routing_key': ('cmk_postprocessed', 'explicit_password', ('uuidae56e934-c477-4da1-95cc-875757dacd81', 'example_routing_key_12345')), 'webhook_url': 'https://events.pagerduty.com/v2/enqueue'}, 'condition': {}, 'options': {'disabled': False}},
] + notification_parameters['pagerduty']


notification_parameters.setdefault('pushover', [])

notification_parameters['pushover'] = [
{'id': '51c20382-108d-433a-897d-e85bd01a1b5c', 'value': {'api_key': 'abcdefghijklmnopqrstuvwxyz1234', 'recipient_key': 'abcdefghijklmnopqrstuvwxyz5678'}, 'condition': {}, 'options': {'disabled': False}},
] + notification_parameters['pushover']


notification_parameters.setdefault('servicenow', [])

notification_parameters['servicenow'] = [
{'id': '2ecff9b5-d596-494f-9b8a-b750c30910d2', 'value': {'url': 'https://example.com', 'auth': ('auth_basic', {'username': 'admin', 'password': ('cmk_postprocessed', 'explicit_password', ('uuid7023020d-fa6f-4253-bddf-11f8b10cfd88', 'example_password_123'))}), 'mgmt_type': ('incident', {'caller': 'example_value'})}, 'condition': {}, 'options': {'disabled': False}},
] + notification_parameters['servicenow']


notification_parameters.setdefault('signl4', [])

notification_parameters['signl4'] = [
{'id': '448868b3-b9c5-4063-bd42-4a667b2d1cd6', 'value': {'password': ('cmk_postprocessed', 'explicit_password', ('uuid79abd223-0e0f-4e57-89f2-247143aa3ba0', 'example_password_123'))}, 'condition': {}, 'options': {'disabled': False}},
] + notification_parameters['signl4']


notification_parameters.setdefault('slack', [])

notification_parameters['slack'] = [
{'id': '5e10325b-462a-44a5-9b8a-cd55a66af0c6', 'value': {'webhook_url': ('webhook_url', 'https://hooks.slack.com/services/example/webhook/url')}, 'condition': {}, 'options': {'disabled': False}},
] + notification_parameters['slack']


notification_parameters.setdefault('sms_api', [])

notification_parameters['sms_api'] = [
{'id': '559199d8-27e3-4c35-8fba-59535250d68f', 'value': {'modem_type': 'trb140', 'url': 'https://example.com', 'proxy_url': ('cmk_postprocessed', 'environment_proxy', ''), 'username': 'admin', 'password': ('cmk_postprocessed', 'explicit_password', ('uuidf8e830f2-a72d-4b86-981e-07ae4bae0496', 'example_password_123')), 'timeout': '10'}, 'condition': {}, 'options': {'disabled': False}},
] + notification_parameters['sms_api']


notification_parameters.setdefault('spectrum', [])

notification_parameters['spectrum'] = [
{'id': '50da36ba-e825-4f3b-80a7-d03f42c51f7a', 'value': {'destination': '192.168.1.1', 'community': ('cmk_postprocessed', 'explicit_password', ('uuid9ad4b134-c012-4f9e-bbc8-82a56b7b3fef', 'public')), 'baseoid': '1.3.6.1.4.1.1234'}, 'condition': {}, 'options': {'disabled': False}},
] + notification_parameters['spectrum']


notification_parameters.setdefault('victorops', [])

notification_parameters['victorops'] = [
{'id': '37182f9b-fef2-4a48-ad7c-39046c7e3346', 'value': {'webhook_url': ('webhook_url', 'https://alert.victorops.com/integrations/example/webhook')}, 'condition': {}, 'options': {'disabled': False}},
] + notification_parameters['victorops']


globals().setdefault('ntp_discovery', [])

ntp_discovery = [
{'id': '9881191f-4118-4892-9864-2ef6998744f4', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + ntp_discovery


globals().setdefault('only_hosts', [])

if only_hosts is None:
    only_hosts = []

only_hosts = [
{'id': '10843c55-11ea-4eb2-bfbc-bce65cd2ae22', 'value': True, 'condition': {'host_tags': {'criticality': {'$ne': 'offline'}}}, 'options': {'description': 'Do not monitor hosts with the tag "offline"'}},
] + only_hosts


globals().setdefault('oracle_performance_discovery', [])

oracle_performance_discovery = [
{'id': '1889c375-e5c7-43a4-bb7a-1ede1213aa15', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + oracle_performance_discovery


globals().setdefault('periodic_discovery', [])

periodic_discovery = [
{'id': '95a56ffc-f17e-44e7-a162-be656f19bedf', 'value': {'severity_unmonitored': 1, 'severity_changed_service_labels': 0, 'severity_changed_service_params': 0, 'severity_vanished': 0, 'severity_new_host_label': 1, 'check_interval': 120.0}, 'condition': {}, 'options': {'description': 'Perform every two hours a service discovery'}},
] + periodic_discovery


globals().setdefault('piggyback_translation', [])

piggyback_translation = [
{'id': 'e31c1eec-5b83-414b-a576-32161b696b78', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + piggyback_translation


globals().setdefault('piggybacked_host_files', [])

piggybacked_host_files = [
{'id': '3a024476-f23b-4001-a5c6-58e30f6f513e', 'value': {'global_max_cache_age': 'global', 'global_validity': {}, 'per_piggybacked_host': []}, 'condition': {}, 'options': {'disabled': False}},
] + piggybacked_host_files


globals().setdefault('ping_levels', [])

ping_levels = [
{'id': '0365b634-30bf-40a3-8516-08e86051508e', 'value': {'loss': (80.0, 100.0), 'packets': 6, 'timeout': 20, 'rta': (1500.0, 3000.0)}, 'condition': {'host_tags': {'networking': 'wan'}}, 'options': {'description': 'Allow longer round trip times when pinging WAN hosts'}},
] + ping_levels


globals().setdefault('primary_address_family', [])

primary_address_family = [
{'id': 'dc1466b0-1390-4a91-b361-fe93e21f0aff', 'value': 'ipv4', 'condition': {}, 'options': {'disabled': False}},
] + primary_address_family


globals().setdefault('rmon_discovery', [])

rmon_discovery = [
{'id': 'a73d902c-d064-4db3-821d-90917715cfc5', 'value': {'discover': True}, 'condition': {}, 'options': {'disabled': False}},
] + rmon_discovery


globals().setdefault('sap_value_groups', [])

sap_value_groups = [
{'id': '009c54fc-2b1c-4545-a850-a9fa8c871b52', 'value': {'grouping_patterns': []}, 'condition': {}, 'options': {'disabled': False}},
] + sap_value_groups


globals().setdefault('service_contactgroups', [])

service_contactgroups = [
{'id': 'f104e1d6-84d0-4e38-828b-ee7099118255', 'value': 'all', 'condition': {}, 'options': {'disabled': False}},
] + service_contactgroups


globals().setdefault('service_description_translation', [])

service_description_translation = [
{'id': '14ff8b83-66bb-45c7-af4d-49fafce1bbe2', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + service_description_translation


globals().setdefault('service_groups', [])

service_groups = [
{'id': '00011190-bf2f-4013-abe6-6bf3441b828c', 'value': 'example_service_group', 'condition': {}, 'options': {'disabled': False}},
] + service_groups


globals().setdefault('service_label_rules', [])

service_label_rules = [
{'id': '3c856a71-c153-4614-bcce-0f268b35dc5a', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + service_label_rules


globals().setdefault('service_recurring_downtimes', [])

service_recurring_downtimes = [
{'id': 'a694fe0e-7997-4479-a079-8d5d8d1e3b8e', 'value': {'comment': 'Default recurring downtime', 'start_time': 1775120012.0, 'interval': 3, 'duration': 7200}, 'condition': {}, 'options': {'disabled': False}},
] + service_recurring_downtimes


globals().setdefault('service_state_translation', [])

service_state_translation = [
{'id': '86fcfe0e-8423-414e-bd0a-d131bd041016', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + service_state_translation


globals().setdefault('service_tag_rules', [])

service_tag_rules = [
{'id': '201379f5-cbc1-4907-b857-61c517c6f5a8', 'value': [('agent', 'cmk-agent')], 'condition': {}, 'options': {'disabled': False}},
] + service_tag_rules


globals().setdefault('snmp_backend_hosts', [])

snmp_backend_hosts = [
{'id': '0e05eb2d-f293-4d3c-b47e-97de509bf417', 'value': 'inline', 'condition': {}, 'options': {'disabled': False}},
] + snmp_backend_hosts


globals().setdefault('snmp_bulk_size', [])

snmp_bulk_size = [
{'id': '0b3724b8-26d2-4194-ab7d-89745fce4ffd', 'value': 10, 'condition': {}, 'options': {'disabled': False}},
] + snmp_bulk_size


globals().setdefault('snmp_character_encodings', [])

snmp_character_encodings = [
{'id': '86298f0e-41e4-4e33-8b75-2206617ba2a8', 'value': 'utf-8', 'condition': {}, 'options': {'disabled': False}},
] + snmp_character_encodings


globals().setdefault('snmp_check_interval', [])

snmp_check_interval = [
{'id': '1e3b0ffa-4e4b-4337-bf90-89661e4f8076', 'value': ([], ('uncached', None)), 'condition': {}, 'options': {'disabled': False}},
] + snmp_check_interval


globals().setdefault('snmp_communities', [])

snmp_communities = [
{'id': '5128f460-4a5a-411f-817d-8ec7a97938a0', 'value': 'public', 'condition': {}, 'options': {'disabled': False}},
] + snmp_communities


globals().setdefault('snmp_exclude_sections', [])

snmp_exclude_sections = [
{'id': 'eb1535ff-5b78-4d70-8889-01f9fa51e367', 'value': {'sections_disabled': [], 'sections_enabled': []}, 'condition': {}, 'options': {'disabled': False}},
] + snmp_exclude_sections


globals().setdefault('snmp_limit_oid_range', [])

snmp_limit_oid_range = [
{'id': '15cc121f-3ba2-4d80-8a02-af155844822f', 'value': ('if64_tplink', None), 'condition': {}, 'options': {'disabled': False}},
] + snmp_limit_oid_range


globals().setdefault('snmp_ports', [])

snmp_ports = [
{'id': '7216e93c-6735-427b-9283-ec1349b9192e', 'value': 161, 'condition': {}, 'options': {'disabled': False}},
] + snmp_ports


globals().setdefault('snmp_timing', [])

snmp_timing = [
{'id': 'ae1d19b9-a2be-449e-af91-577ec1094bbe', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + snmp_timing


globals().setdefault('snmp_without_sys_descr', [])

snmp_without_sys_descr = [
{'id': '6f1d109f-ac14-404c-8086-cbb9c036d925', 'value': True, 'condition': {}, 'options': {'disabled': False}},
] + snmp_without_sys_descr


globals().setdefault('snmpv2c_hosts', [])

snmpv2c_hosts = [
{'id': '5a834baf-6ccf-45fa-ad01-f2c1581efe49', 'value': True, 'condition': {}, 'options': {'disabled': False}},
] + snmpv2c_hosts


globals().setdefault('snmpv3_contexts', [])

snmpv3_contexts = [
{'id': 'e38247bb-4680-43b7-ab8d-e94054a689da', 'value': (None, ['example_context'], 'stop_on_timeout'), 'condition': {}, 'options': {'disabled': False}},
] + snmpv3_contexts


special_agents.setdefault('acme_sbc', [])

special_agents['acme_sbc'] = [
{'id': 'a8590c32-d39c-495f-88de-eadb356ec7f5', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['acme_sbc']


special_agents.setdefault('activemq', [])

special_agents['activemq'] = [
{'id': '28bc9125-0fab-42f0-9041-15bd64ca1117', 'value': {'servername': 'example.com', 'port': 8161, 'protocol': 'http', 'use_piggyback': False}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['activemq']


special_agents.setdefault('allnet_ip_sensoric', [])

special_agents['allnet_ip_sensoric'] = [
{'id': 'cd68ef3a-2361-46e4-8d30-3e1fa462e6d3', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['allnet_ip_sensoric']


special_agents.setdefault('appdynamics', [])

special_agents['appdynamics'] = [
{'id': '8a4c22b5-2c98-4e90-90b6-0e97c850d10d', 'value': {'username': 'admin', 'password': ('cmk_postprocessed', 'explicit_password', ('uuiddd71ab90-a8c7-478b-97c5-6a6cbb538af9', 'example')), 'application': 'ExampleApp'}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['appdynamics']


special_agents.setdefault('aws', [])

special_agents['aws'] = [
{'id': '04323f5c-8783-4d3d-b380-3c9ecfbdb944', 'value': {'auth': ('access_key', {'access_key_id': '', 'secret_access_key': ('cmk_postprocessed', 'explicit_password', ('71eb5729-9d17-4972-b0d1-f2f2616db527', 'example'))}), 'access': {}, 'global_services': {}, 'regions': [], 'regional_services': {'ec2': {'selection': 'all', 'limits': True}, 'ebs': {'selection': 'all', 'limits': True}, 's3': {'selection': 'all', 'limits': True}, 'glacier': {'selection': 'all', 'limits': True}, 'elb': {'selection': 'all', 'limits': True}, 'elbv2': {'selection': 'all', 'limits': True}, 'rds': {'selection': 'all', 'limits': True}, 'cloudwatch_alarms': {'alarms': 'all', 'limits': True}, 'dynamodb': {'selection': 'all', 'limits': True}, 'wafv2': {'selection': 'all', 'limits': True, 'cloudfront': None}}, 'piggyback_naming_convention': 'ip_region_instance'}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['aws']


special_agents.setdefault('aws_status', [])

special_agents['aws_status'] = [
{'id': '6a3e6cb7-13d9-4042-983b-dbc597dbb0ef', 'value': {'regions_to_monitor': []}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['aws_status']


special_agents.setdefault('azure', [])

special_agents['azure'] = [
{'id': '51513b55-a700-4aba-813d-21c7c4fc580f', 'value': {'tenant': 'example', 'client': 'example', 'secret': ('cmk_postprocessed', 'explicit_password', ('uuid482e2e7d-8c38-4efc-b083-0d143ccd70b5', 'example')), 'authority': 'global_', 'services': ['Microsoft_Compute_slash_virtualMachines', 'Microsoft_DBforMySQL_slash_flexibleServers', 'Microsoft_DBforMySQL_slash_servers', 'Microsoft_DBforPostgreSQL_slash_flexibleServers', 'Microsoft_DBforPostgreSQL_slash_servers', 'Microsoft_Network_slash_loadBalancers', 'Microsoft_Network_slash_trafficmanagerprofiles', 'Microsoft_Network_slash_virtualNetworkGateways', 'Microsoft_Sql_slash_servers_slash_databases', 'Microsoft_Storage_slash_storageAccounts', 'Microsoft_Web_slash_sites', 'usage_details'], 'config': {}}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['azure']


special_agents.setdefault('bazel_cache', [])

special_agents['bazel_cache'] = [
{'id': 'ce690428-9bf1-43af-b2a0-32eacae5d230', 'value': {'protocol': 'https', 'no_cert_check': False}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['bazel_cache']


special_agents.setdefault('bi', [])

special_agents['bi'] = [
{'id': '919ee816-f5ba-4bdf-84bb-ae50c66670af', 'value': {'options': []}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['bi']


special_agents.setdefault('cisco_meraki', [])

special_agents['cisco_meraki'] = [
{'id': 'd2c3c8d0-596d-4686-9092-ef58e6f2c120', 'value': {'api_key': ('cmk_postprocessed', 'explicit_password', ('uuida01ee604-96b5-4251-9935-c9146aa8636e', 'exampleapikey12345'))}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['cisco_meraki']


special_agents.setdefault('cisco_prime', [])

special_agents['cisco_prime'] = [
{'id': '5c027816-e8e0-437e-a101-b9b129867dd3', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['cisco_prime']


special_agents.setdefault('couchbase', [])

special_agents['couchbase'] = [
{'id': 'e35cff1c-c71e-445c-9ad0-737124a69af2', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['couchbase']


special_agents.setdefault('datadog', [])

special_agents['datadog'] = [
{'id': '536aeb2a-8531-4f9c-a2ce-4214ada6bdf9', 'value': {'instance': {'api_key': ('cmk_postprocessed', 'explicit_password', ('uuid9609fde3-5f31-4014-9496-1be5e7ce2305', 'exampleapikey')), 'app_key': ('cmk_postprocessed', 'explicit_password', ('uuidf07d552f-15fb-4bd4-9765-e3890162b5e4', 'exampleappkey')), 'api_host': 'https://api.datadoghq.eu'}}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['datadog']


special_agents.setdefault('ddn_s2a', [])

special_agents['ddn_s2a'] = [
{'id': '7a38bcd6-836c-4a7c-a7eb-ecaae18d97d0', 'value': {'username': 'admin', 'password': ('cmk_postprocessed', 'explicit_password', ('uuid4358b7cc-d07a-4db5-8331-60106a339282', 'example'))}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['ddn_s2a']


special_agents.setdefault('elasticsearch', [])

special_agents['elasticsearch'] = [
{'id': '6e93a7c3-daba-49ec-a00e-4f5dd6b60f25', 'value': {'hosts': ['example.com'], 'protocol': 'https', 'port': 9200, 'cluster_health': False, 'nodes': False}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['elasticsearch']


special_agents.setdefault('fritzbox', [])

special_agents['fritzbox'] = [
{'id': 'c6c6cca9-d589-4c36-abbc-b4ce1dc17b42', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['fritzbox']


special_agents.setdefault('gerrit', [])

special_agents['gerrit'] = [
{'id': '11e55620-db3a-4794-98c4-e69bd1b66649', 'value': {'instance': 'gerrit.example.com', 'user': 'admin', 'password': ('cmk_postprocessed', 'explicit_password', ('uuid49dbc1f3-674b-40ad-ae1d-745fd4b80db3', 'example'))}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['gerrit']


special_agents.setdefault('graylog', [])

special_agents['graylog'] = [
{'id': 'bd20164c-a974-4ab3-b70a-81ad50ceda1b', 'value': {'instance': 'graylog.example.com', 'user': 'admin', 'password': ('cmk_postprocessed', 'explicit_password', ('uuidef72da93-9e6c-4263-b664-83edf50418f9', 'example')), 'protocol': 'https', 'since': 1800.0, 'sections': ['alerts', 'cluster_stats', 'cluster_traffic', 'failures', 'jvm', 'license', 'messages', 'nodes', 'sidecars', 'sources', 'streams', 'events'], 'display_node_details': 'host', 'display_sidecar_details': 'host', 'display_source_details': 'host'}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['graylog']


special_agents.setdefault('hivemanager', [])

special_agents['hivemanager'] = [
{'id': '8f649685-1f6b-4bbb-ac28-f3827cee04e8', 'value': {'username': 'admin', 'password': ('cmk_postprocessed', 'explicit_password', ('uuid5e331f4d-54f1-4d44-9269-cf34eecaca57', 'example'))}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['hivemanager']


special_agents.setdefault('hivemanager_ng', [])

special_agents['hivemanager_ng'] = [
{'id': '109f2980-c682-4fe4-9eb7-ed738cf28292', 'value': {'url': 'https://example.com', 'vhm_id': 'example-vhm', 'api_token': 'exampletoken', 'client_id': 'example-client', 'client_secret': ('cmk_postprocessed', 'explicit_password', ('uuida11a0ebb-9a8e-4176-986f-08acb96e275d', 'example')), 'redirect_url': 'https://example.com/callback'}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['hivemanager_ng']


special_agents.setdefault('hp_msa', [])

special_agents['hp_msa'] = [
{'id': '5e9d7818-1d08-4971-bc61-4a98ce04f06e', 'value': {'username': 'admin', 'password': ('cmk_postprocessed', 'explicit_password', ('uuid02be3258-9057-42d7-920b-6781e200c9ae', 'example'))}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['hp_msa']


special_agents.setdefault('ibmsvc', [])

special_agents['ibmsvc'] = [
{'id': '4cfde11a-fce9-4619-bd09-5321250ff791', 'value': {'user': '', 'accept_any_hostkey': False, 'infos': ['lshost', 'lslicense', 'lsmdisk', 'lsmdiskgrp', 'lsnode', 'lsnodestats', 'lssystem', 'lssystemstats', 'lsportfc', 'lsenclosure', 'lsenclosurestats', 'lsarray', 'disks']}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['ibmsvc']


special_agents.setdefault('innovaphone', [])

special_agents['innovaphone'] = [
{'id': 'bccf02c5-539b-4cb1-b135-69bfb45abb1e', 'value': {'cert_verification': True, 'auth_basic': {'username': 'admin', 'password': ('cmk_postprocessed', 'explicit_password', ('uuidf6b41056-d441-4f11-b460-4f6d5b3f383e', 'example'))}}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['innovaphone']


special_agents.setdefault('ipmi_sensors', [])

special_agents['ipmi_sensors'] = [
{'id': '26efa9be-8171-4d2f-bde2-f439fe87dd86', 'value': {'agent': ('freeipmi', {'username': 'admin', 'password': ('cmk_postprocessed', 'explicit_password', ('uuide4b52702-1e84-46e6-8753-ec0575854533', 'example')), 'privilege_lvl': 'operator', 'cipher_suite_id': 'suite_3'})}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['ipmi_sensors']


special_agents.setdefault('jenkins', [])

special_agents['jenkins'] = [
{'id': 'd7706758-bb81-40ba-aabb-d4876ba0c57c', 'value': {'instance': 'jenkins.example.com', 'user': 'admin', 'password': ('cmk_postprocessed', 'explicit_password', ('uuide6de0846-38f9-4c1b-ac0b-d8cd6c3451d9', 'example')), 'protocol': 'https', 'sections': ['instance', 'jobs', 'nodes', 'queue']}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['jenkins']


special_agents.setdefault('jira', [])

special_agents['jira'] = [
{'id': 'e9d0f0c9-87db-4beb-bc80-237db840b697', 'value': {'user': 'admin', 'password': ('cmk_postprocessed', 'explicit_password', ('uuid17b899d8-d6ad-4048-a090-81cc7825b416', 'example')), 'protocol': 'https'}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['jira']


special_agents.setdefault('jolokia', [])

special_agents['jolokia'] = [
{'id': '0294db2c-5ea8-44c5-b622-74a50117050f', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['jolokia']


special_agents.setdefault('mobileiron', [])

special_agents['mobileiron'] = [
{'id': '1f49e6b6-e055-461c-b463-b58dd753bfe7', 'value': {'username': 'admin', 'password': ('cmk_postprocessed', 'explicit_password', ('uuid5258876b-4f65-4ac9-babd-607d4c79c3e8', 'example')), 'partition': ['example-partition'], 'key_fields': 'deviceModel_serialNumber', 'android_regex': ['.*']}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['mobileiron']


special_agents.setdefault('mqtt', [])

special_agents['mqtt'] = [
{'id': '405743b8-9308-43ed-b332-2a7d967b6f95', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['mqtt']


special_agents.setdefault('netapp_ontap', [])

special_agents['netapp_ontap'] = [
{'id': 'bdc55e9a-911a-449d-8f21-67fdd59ce25c', 'value': {'username': 'admin', 'password': ('cmk_postprocessed', 'explicit_password', ('uuid14222e36-ae13-444f-85bd-363120e89b6a', 'example')), 'no_cert_check': False, 'fetched_resources': ['volumes', 'volumes_counters', 'disk', 'luns', 'aggr', 'qtree_quota', 'snapvault', 'interfaces', 'ports', 'fc_interfaces', 'node', 'vs_status', 'vs_traffic', 'fan', 'temp', 'psu', 'environment', 'alerts']}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['netapp_ontap']


special_agents.setdefault('prism', [])

special_agents['prism'] = [
{'id': '19ce4cd0-80e3-446e-a737-2ec50a1d111c', 'value': {'username': 'admin', 'password': ('cmk_postprocessed', 'explicit_password', ('uuid6790f5ee-be22-402d-b390-f81a3c883210', 'example')), 'no_cert_check': False}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['prism']


special_agents.setdefault('pure_storage_fa', [])

special_agents['pure_storage_fa'] = [
{'id': '736511b4-048c-4339-b773-35edf8740707', 'value': {'api_token': ('cmk_postprocessed', 'explicit_password', ('uuid53f2fd74-e23a-422d-88eb-294f99398d74', 'exampletoken')), 'ssl': ('deactivated', None), 'timeout': 5.0}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['pure_storage_fa']


special_agents.setdefault('rabbitmq', [])

special_agents['rabbitmq'] = [
{'id': '996056e4-d3d7-4c37-aa0d-7df7202d6593', 'value': {'user': 'admin', 'password': ('cmk_postprocessed', 'explicit_password', ('uuidda790abe-78f8-480c-b64c-c1305b5bbb93', 'example')), 'protocol': 'https', 'sections': ['cluster', 'nodes', 'vhosts', 'queues']}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['rabbitmq']


special_agents.setdefault('random', [])

special_agents['random'] = [
{'id': '12cecfd5-e239-464d-99f4-cf8f0add233b', 'value': {'random': None}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['random']


special_agents.setdefault('redfish', [])

special_agents['redfish'] = [
{'id': 'bb6bed93-cb30-4cc8-b5b4-cd1f827820bf', 'value': {'user': 'admin', 'password': ('cmk_postprocessed', 'explicit_password', ('uuid3789733b-82e1-4807-8786-317912b65975', 'example')), 'port': 443, 'proto': 'https', 'retries': 2, 'timeout': 3.0, 'debug': False}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['redfish']


special_agents.setdefault('redfish_power', [])

special_agents['redfish_power'] = [
{'id': '91d0eefe-0c4d-4913-8bba-20aebe0eedbd', 'value': {'user': 'admin', 'password': ('cmk_postprocessed', 'explicit_password', ('uuid9079acec-eb7d-444c-9352-03695394dd83', 'example')), 'port': 443, 'proto': 'https', 'retries': 2, 'timeout': 3.0}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['redfish_power']


special_agents.setdefault('siemens_plc', [])

special_agents['siemens_plc'] = [
{'id': '1361b63b-fd28-4ac9-a62c-e1468bdd4074', 'value': {'devices': [], 'values': []}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['siemens_plc']


special_agents.setdefault('smb_share', [])

special_agents['smb_share'] = [
{'id': '8d590106-4b68-413f-a624-3d3e178c77c7', 'value': {'patterns': []}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['smb_share']


special_agents.setdefault('splunk', [])

special_agents['splunk'] = [
{'id': 'b1aeea2b-3ee1-49ee-b701-aa5618b3ef4a', 'value': {'user': 'admin', 'password': ('cmk_postprocessed', 'explicit_password', ('uuid1b8894a0-5c53-45c5-a2b3-c51dd4543872', 'example')), 'protocol': 'https', 'infos': ['license_state', 'license_usage', 'system_msg', 'jobs', 'health', 'alerts']}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['splunk']


special_agents.setdefault('storeonce', [])

special_agents['storeonce'] = [
{'id': '05761149-07f8-4dbc-b8df-e2390c0c4890', 'value': {'user': 'admin', 'password': ('cmk_postprocessed', 'explicit_password', ('uuid480d5a9a-977b-43b3-b40a-d469485fd6aa', 'example')), 'ignore_tls': False}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['storeonce']


special_agents.setdefault('storeonce4x', [])

special_agents['storeonce4x'] = [
{'id': '82ab33ae-fc25-4df7-955a-98a299049922', 'value': {'user': 'admin', 'password': ('cmk_postprocessed', 'explicit_password', ('uuid4bd04290-756a-4ae1-8f90-89ae371be14e', 'example')), 'ignore_tls': False}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['storeonce4x']


special_agents.setdefault('three_par', [])

special_agents['three_par'] = [
{'id': 'c1f32b4e-4f04-4505-bae3-ef21ed739b5d', 'value': {'user': 'admin', 'password': ('cmk_postprocessed', 'explicit_password', ('uuidd9dd0a56-0b63-4eda-ae23-d91d34942f28', 'example')), 'port': 8080, 'verify_cert': False, 'values': ['system', 'cpgs', 'volumes', 'hosts', 'capacity', 'ports', 'remotecopy']}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['three_par']


special_agents.setdefault('tinkerforge', [])

special_agents['tinkerforge'] = [
{'id': '1c526aae-2f2f-4b53-b2d1-c479fe7ad6f9', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['tinkerforge']


special_agents.setdefault('ucs_bladecenter', [])

special_agents['ucs_bladecenter'] = [
{'id': '87679f68-ed23-4ba5-84a0-61d24f1b692a', 'value': {'username': 'admin', 'password': ('cmk_postprocessed', 'explicit_password', ('uuid936fcf22-e49c-4c0c-9157-ce32d2037370', 'example')), 'certificate_validation': True}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['ucs_bladecenter']


special_agents.setdefault('vnx_quotas', [])

special_agents['vnx_quotas'] = [
{'id': '3bb25348-75dc-44b3-8864-b4965974bdd7', 'value': {'user': 'admin', 'password': ('cmk_postprocessed', 'explicit_password', ('uuidff16c330-6091-4eaf-a171-465fa050cc15', 'example')), 'nas_db': '/nas/db'}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['vnx_quotas']


special_agents.setdefault('zerto', [])

special_agents['zerto'] = [
{'id': '64b16341-2d83-48f5-a7f3-9ac262a54002', 'value': {'username': 'admin', 'password': ('cmk_postprocessed', 'explicit_password', ('uuide72c0d4c-7474-47e2-a9f4-8bdae3619f2d', 'example')), 'cert_verification': ('insecure', {'verify': False})}, 'condition': {}, 'options': {'disabled': False}},
] + special_agents['zerto']


static_checks.setdefault('acme_certificates', [])

static_checks['acme_certificates'] = [
{'id': 'c450919d-0fd5-47fa-9673-73d8395c9618', 'value': ('acme_certificates', 'example', {'expire_lower': ('fixed', (604800.0, 2592000.0))}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['acme_certificates']


static_checks.setdefault('acme_sbc_snmp', [])

static_checks['acme_sbc_snmp'] = [
{'id': '4fadb64c-dc23-4c3e-a0d5-95ff948f96d5', 'value': ('acme_sbc_snmp', None, {'lower_levels': ('fixed', (75, 50))}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['acme_sbc_snmp']


static_checks.setdefault('ad_replication', [])

static_checks['ad_replication'] = [
{'id': '4ab17f2f-e6cf-421c-8651-41974b5e03fb', 'value': ('ad_replication', 'example', {'failure_levels': (0, 0)}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['ad_replication']


static_checks.setdefault('adva_ifs', [])

static_checks['adva_ifs'] = [
{'id': '0f5bd887-5ac5-4553-8bea-b8415d77220c', 'value': ('adva_fsp_if', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['adva_ifs']


static_checks.setdefault('agent_update', [])

static_checks['agent_update'] = [
{'id': '765dfb77-b2e9-4ed6-b33d-69341f3d5cc5', 'value': ('checkmk_agent', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['agent_update']


static_checks.setdefault('airflow', [])

static_checks['airflow'] = [
{'id': '297d76d2-394e-4e4f-b8bd-b0cda4ae50d0', 'value': ('apc_inrow_airflow', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['airflow']


static_checks.setdefault('airflow_deviation', [])

static_checks['airflow_deviation'] = [
{'id': '960e4eee-671b-4732-a82e-0b1731a32848', 'value': ('wagner_titanus_topsense_airflow_deviation', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['airflow_deviation']


static_checks.setdefault('alertmanager_rule_state', [])

static_checks['alertmanager_rule_state'] = [
{'id': '5476885f-cd64-46e1-aa2b-db3b45143c2f', 'value': ('alertmanager_groups', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['alertmanager_rule_state']


static_checks.setdefault('alertmanager_rule_state_summary', [])

static_checks['alertmanager_rule_state_summary'] = [
{'id': '178b66e6-1f38-4340-95ef-2652035963ab', 'value': ('alertmanager_summary', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['alertmanager_rule_state_summary']


static_checks.setdefault('antivir_update_age', [])

static_checks['antivir_update_age'] = [
{'id': 'c7d7ae57-8844-4e66-8e36-0f4ced8396b3', 'value': ('symantec_av_updates', None, {'levels': None}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['antivir_update_age']


static_checks.setdefault('apache_status', [])

static_checks['apache_status'] = [
{'id': 'c4dc5c8a-14f9-4575-8629-179c5a1fa0a7', 'value': ('apache_status', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['apache_status']


static_checks.setdefault('apc_ats_output', [])

static_checks['apc_ats_output'] = [
{'id': '92f28b4b-0028-459b-9544-79fc601fef7c', 'value': ('apc_ats_output', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['apc_ats_output']


static_checks.setdefault('apc_system_events', [])

static_checks['apc_system_events'] = [
{'id': '3a8f583f-f248-4c30-a0a4-437dbeeb6376', 'value': ('apc_inrow_system_events', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['apc_system_events']


static_checks.setdefault('apt', [])

static_checks['apt'] = [
{'id': '64015423-9392-4a5a-8bc9-3fa0f3dda04a', 'value': ('apt', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['apt']


static_checks.setdefault('asm_diskgroup', [])

static_checks['asm_diskgroup'] = [
{'id': '18be6592-80e4-46ba-856c-c35b1dae7b28', 'value': ('oracle_asm_diskgroup', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['asm_diskgroup']


static_checks.setdefault('aws_cloudwatch_alarms_limits', [])

static_checks['aws_cloudwatch_alarms_limits'] = [
{'id': '73f6861f-0774-425a-9789-252e02d2cb8d', 'value': ('aws_cloudwatch_alarms_limits', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['aws_cloudwatch_alarms_limits']


static_checks.setdefault('aws_costs_and_usage', [])

static_checks['aws_costs_and_usage'] = [
{'id': 'e423b516-61c2-4eba-8894-0db84c20eb47', 'value': ('aws_costs_and_usage', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['aws_costs_and_usage']


static_checks.setdefault('aws_dynamodb_capacity', [])

static_checks['aws_dynamodb_capacity'] = [
{'id': '0023e030-b256-470a-a889-18003690acb0', 'value': ('aws_dynamodb_table_read_capacity', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['aws_dynamodb_capacity']


static_checks.setdefault('aws_dynamodb_latency', [])

static_checks['aws_dynamodb_latency'] = [
{'id': '774997ac-6a53-45a9-8c7d-a56bc35c3fb1', 'value': ('aws_dynamodb_table_latency', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['aws_dynamodb_latency']


static_checks.setdefault('aws_dynamodb_limits', [])

static_checks['aws_dynamodb_limits'] = [
{'id': '7fd5a6f1-7f4b-4522-a025-a4927995ef64', 'value': ('aws_dynamodb_limits', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['aws_dynamodb_limits']


static_checks.setdefault('aws_ebs_burst_balance', [])

static_checks['aws_ebs_burst_balance'] = [
{'id': '82c8d06b-ca1d-4d3b-ba7c-0713cdb1aebe', 'value': ('aws_ebs_burst_balance', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['aws_ebs_burst_balance']


static_checks.setdefault('aws_ebs_limits', [])

static_checks['aws_ebs_limits'] = [
{'id': '586f9a69-f288-4e1f-9350-b65a86021864', 'value': ('aws_ebs_limits', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['aws_ebs_limits']


static_checks.setdefault('aws_ec2_cpu_credits', [])

static_checks['aws_ec2_cpu_credits'] = [
{'id': '82986217-fc76-4c40-aa54-68601a24633a', 'value': ('aws_ec2_cpu_credits', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['aws_ec2_cpu_credits']


static_checks.setdefault('aws_ec2_limits', [])

static_checks['aws_ec2_limits'] = [
{'id': 'e593eb74-d470-4578-bbd7-fb31cb4a7275', 'value': ('aws_ec2_limits', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['aws_ec2_limits']


static_checks.setdefault('aws_elb_backend_connection_errors', [])

static_checks['aws_elb_backend_connection_errors'] = [
{'id': 'c7f54963-6c99-48f1-8fa4-6aa7809f9a67', 'value': ('aws_elb_backend_connection_errors', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['aws_elb_backend_connection_errors']


static_checks.setdefault('aws_elb_healthy_hosts', [])

static_checks['aws_elb_healthy_hosts'] = [
{'id': '1fd59acf-4a73-4ce5-b1dd-bc3122188361', 'value': ('aws_elb_healthy_hosts', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['aws_elb_healthy_hosts']


static_checks.setdefault('aws_elb_http', [])

static_checks['aws_elb_http'] = [
{'id': '8d4735e3-2807-4b2c-adf2-d1941bdc5309', 'value': ('aws_elb_http_backend', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['aws_elb_http']


static_checks.setdefault('aws_elb_latency', [])

static_checks['aws_elb_latency'] = [
{'id': '32321665-8dfb-49da-b6ef-0892ccae3396', 'value': ('aws_elb_latency', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['aws_elb_latency']


static_checks.setdefault('aws_elb_limits', [])

static_checks['aws_elb_limits'] = [
{'id': '2d19d120-c305-48d2-ad31-8f9f39480e84', 'value': ('aws_elb_limits', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['aws_elb_limits']


static_checks.setdefault('aws_elb_statistics', [])

static_checks['aws_elb_statistics'] = [
{'id': '1bab9db4-e61e-4de8-a755-6144aec40f6f', 'value': ('aws_elb', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['aws_elb_statistics']


static_checks.setdefault('aws_elbv2_lcu', [])

static_checks['aws_elbv2_lcu'] = [
{'id': '785d14bc-6ef7-418e-8a04-dd659d022f82', 'value': ('aws_elbv2_application', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['aws_elbv2_lcu']


static_checks.setdefault('aws_elbv2_limits', [])

static_checks['aws_elbv2_limits'] = [
{'id': '4f45b1b6-4de0-40e0-bf48-2503bf845b57', 'value': ('aws_elbv2_limits', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['aws_elbv2_limits']


static_checks.setdefault('aws_elbv2_target_errors', [])

static_checks['aws_elbv2_target_errors'] = [
{'id': '08753fc5-3d79-4b9e-994c-72f03e4ff077', 'value': ('aws_elbv2_application_target_groups_http', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['aws_elbv2_target_errors']


static_checks.setdefault('aws_glacier_limits', [])

static_checks['aws_glacier_limits'] = [
{'id': '91a97053-0c94-4152-a273-71c2f8261de4', 'value': ('aws_glacier_limits', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['aws_glacier_limits']


static_checks.setdefault('aws_glacier_vault_archives', [])

static_checks['aws_glacier_vault_archives'] = [
{'id': '0f2f633e-df00-4aad-a308-eff1f80cdf89', 'value': ('aws_glacier', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['aws_glacier_vault_archives']


static_checks.setdefault('aws_glacier_vaults', [])

static_checks['aws_glacier_vaults'] = [
{'id': 'ed411321-4bfe-4316-b4ff-37f6447fb015', 'value': ('aws_glacier_summary', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['aws_glacier_vaults']


static_checks.setdefault('aws_rds_connections', [])

static_checks['aws_rds_connections'] = [
{'id': 'c59e4949-d855-4a05-99cb-bb9b6c2f17a8', 'value': ('aws_rds_connections', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['aws_rds_connections']


static_checks.setdefault('aws_rds_cpu_credits', [])

static_checks['aws_rds_cpu_credits'] = [
{'id': 'e79a9d9e-a43f-468d-86ed-2b3d84f2a4df', 'value': ('aws_rds_cpu_credits', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['aws_rds_cpu_credits']


static_checks.setdefault('aws_rds_disk_usage', [])

static_checks['aws_rds_disk_usage'] = [
{'id': '7d025cac-6ecc-4d65-94a9-3ed9e4d2ea0c', 'value': ('aws_rds_bin_log_usage', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['aws_rds_disk_usage']


static_checks.setdefault('aws_rds_limits', [])

static_checks['aws_rds_limits'] = [
{'id': 'dd34f8f1-de77-468d-bcf2-b4d56bb8af3e', 'value': ('aws_rds_limits', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['aws_rds_limits']


static_checks.setdefault('aws_rds_replica_lag', [])

static_checks['aws_rds_replica_lag'] = [
{'id': '93458089-31f3-4580-a05e-d2ac78432c66', 'value': ('aws_rds_replica_lag', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['aws_rds_replica_lag']


static_checks.setdefault('aws_reservation_utilization', [])

static_checks['aws_reservation_utilization'] = [
{'id': '1d16f752-91be-45a9-a778-b8d901943155', 'value': ('aws_reservation_utilization', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['aws_reservation_utilization']


static_checks.setdefault('aws_s3_buckets', [])

static_checks['aws_s3_buckets'] = [
{'id': '19d9acc9-429d-439d-b0c0-423aa9b871cc', 'value': ('aws_s3_summary', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['aws_s3_buckets']


static_checks.setdefault('aws_s3_buckets_objects', [])

static_checks['aws_s3_buckets_objects'] = [
{'id': '6c4d86be-5946-425e-80e3-a11c39d5bd01', 'value': ('aws_s3', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['aws_s3_buckets_objects']


static_checks.setdefault('aws_s3_http_errors', [])

static_checks['aws_s3_http_errors'] = [
{'id': '93d39e14-e5cd-42ce-8e8c-aff2fef5d236', 'value': ('aws_s3_requests_http_errors', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['aws_s3_http_errors']


static_checks.setdefault('aws_s3_latency', [])

static_checks['aws_s3_latency'] = [
{'id': '2cb64a6b-e1bc-429c-9f75-12cc417571e9', 'value': ('aws_s3_requests_latency', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['aws_s3_latency']


static_checks.setdefault('aws_s3_limits', [])

static_checks['aws_s3_limits'] = [
{'id': '1c0c8827-1698-433d-9250-712bfb3840f5', 'value': ('aws_s3_limits', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['aws_s3_limits']


static_checks.setdefault('aws_s3_requests', [])

static_checks['aws_s3_requests'] = [
{'id': 'b1139ebb-59ae-4770-9c76-329d23da8538', 'value': ('aws_s3_requests', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['aws_s3_requests']


static_checks.setdefault('aws_wafv2_limits', [])

static_checks['aws_wafv2_limits'] = [
{'id': 'cf77680f-500e-4c40-846b-18bb3570a266', 'value': ('aws_wafv2_limits', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['aws_wafv2_limits']


static_checks.setdefault('aws_wafv2_web_acl', [])

static_checks['aws_wafv2_web_acl'] = [
{'id': '6253b6a2-982c-4daf-ba90-9aa0ffb01eea', 'value': ('aws_wafv2_web_acl', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['aws_wafv2_web_acl']


static_checks.setdefault('azure_ad', [])

static_checks['azure_ad'] = [
{'id': '0572d887-0626-400b-95fa-7c6b128d462a', 'value': ('azure_ad_sync', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['azure_ad']


static_checks.setdefault('azure_agent_info', [])

static_checks['azure_agent_info'] = [
{'id': 'c366aad7-3dc2-4f14-94ac-4733b4a24fe9', 'value': ('azure_agent_info', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['azure_agent_info']


static_checks.setdefault('azure_databases_cpu', [])

static_checks['azure_databases_cpu'] = [
{'id': '8614583f-00a3-4975-90a5-26cc4cb2e683', 'value': ('azure_databases_cpu', 'example', {'cpu_percent': ('fixed', (85.0, 95.0))}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['azure_databases_cpu']


static_checks.setdefault('azure_databases_deadlock', [])

static_checks['azure_databases_deadlock'] = [
{'id': '1905d1d5-1796-4dd7-895c-2efc68788662', 'value': ('azure_databases_deadlock', 'example', {'deadlocks': ('fixed', (10.0, 100.0))}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['azure_databases_deadlock']


static_checks.setdefault('azure_databases_dtu', [])

static_checks['azure_databases_dtu'] = [
{'id': 'a11c61f5-72a7-48c4-a7f9-695469df035a', 'value': ('azure_databases_dtu', 'example', {'dtu_percent': ('fixed', (40.0, 50.0))}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['azure_databases_dtu']


static_checks.setdefault('azure_databases_storage', [])

static_checks['azure_databases_storage'] = [
{'id': 'f0f955fa-dba7-4f4e-8601-968461635c46', 'value': ('azure_databases_storage', 'example', {'storage_percent': ('fixed', (85.0, 95.0))}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['azure_databases_storage']


static_checks.setdefault('azure_db_storage', [])

static_checks['azure_db_storage'] = [
{'id': '1f9c937b-6a20-438b-b20a-adc5eb0ec542', 'value': ('azure_mysql_storage', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['azure_db_storage']


static_checks.setdefault('azure_load_balancer_health', [])

static_checks['azure_load_balancer_health'] = [
{'id': '21d37a2b-e403-4d3b-a1ca-b565b6ddbf56', 'value': ('azure_load_balancer_health', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['azure_load_balancer_health']


static_checks.setdefault('azure_storageaccounts', [])

static_checks['azure_storageaccounts'] = [
{'id': '6388ed95-690c-4adc-8358-344caf95b634', 'value': ('azure_storageaccounts', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['azure_storageaccounts']


static_checks.setdefault('azure_traffic_manager_probe_state', [])

static_checks['azure_traffic_manager_probe_state'] = [
{'id': '27f9cd68-93a7-4b86-97fd-64287eb46667', 'value': ('azure_traffic_manager_probe_state', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['azure_traffic_manager_probe_state']


static_checks.setdefault('azure_traffic_manager_qps', [])

static_checks['azure_traffic_manager_qps'] = [
{'id': 'abe883c0-9363-4631-aa31-99f29a69e3e3', 'value': ('azure_traffic_manager_qps', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['azure_traffic_manager_qps']


static_checks.setdefault('azure_usagedetails', [])

static_checks['azure_usagedetails'] = [
{'id': 'ca839c25-154b-4ec4-95a8-ec3f0dce9998', 'value': ('azure_usagedetails', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['azure_usagedetails']


static_checks.setdefault('azure_v2_agent_info', [])

static_checks['azure_v2_agent_info'] = [
{'id': 'f6711744-8f2a-4860-8274-c42ab1b07ac4', 'value': ('azure_v2_agent_info', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['azure_v2_agent_info']


static_checks.setdefault('azure_v2_virtualnetworkgateways', [])

static_checks['azure_v2_virtualnetworkgateways'] = [
{'id': '92e440d1-52a1-44cd-a38d-578a9ca3f740', 'value': ('azure_v2_virtual_network_gateways', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['azure_v2_virtualnetworkgateways']


static_checks.setdefault('azure_v2_vm_burst_cpu_credits', [])

static_checks['azure_v2_vm_burst_cpu_credits'] = [
{'id': '4bfc4f78-f3b1-4ec9-8f0b-f5258799af72', 'value': ('azure_v2_vm_burst_cpu_credits', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['azure_v2_vm_burst_cpu_credits']


static_checks.setdefault('azure_v2_vms', [])

static_checks['azure_v2_vms'] = [
{'id': '188a26e6-611d-4f64-a8ca-d7c19ff00ff5', 'value': ('azure_v2_virtual_machine', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['azure_v2_vms']


static_checks.setdefault('azure_virtualnetworkgateways', [])

static_checks['azure_virtualnetworkgateways'] = [
{'id': '35a4ce83-6efc-4fce-936b-6dd3bd38daa3', 'value': ('azure_virtual_network_gateways', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['azure_virtualnetworkgateways']


static_checks.setdefault('azure_vm_burst_cpu_credits', [])

static_checks['azure_vm_burst_cpu_credits'] = [
{'id': '2ceae136-b3ab-48ab-82ba-e496054d64ea', 'value': ('azure_vm_burst_cpu_credits', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['azure_vm_burst_cpu_credits']


static_checks.setdefault('azure_vm_disk', [])

static_checks['azure_vm_disk'] = [
{'id': 'ea845140-95d1-471f-97ef-db16d4be09aa', 'value': ('azure_vm_disk', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['azure_vm_disk']


static_checks.setdefault('azure_vms', [])

static_checks['azure_vms'] = [
{'id': 'e264c848-ad42-4b50-bf68-5254795cc728', 'value': ('azure_virtual_machine', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['azure_vms']


static_checks.setdefault('azure_vms_summary', [])

static_checks['azure_vms_summary'] = [
{'id': 'a0a1a49d-261e-41da-b9d2-f7ec9a3f280b', 'value': ('azure_virtual_machine_summary', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['azure_vms_summary']


static_checks.setdefault('backup_timemachine', [])

static_checks['backup_timemachine'] = [
{'id': '1dc37612-0780-49e0-959a-620d9bb432fc', 'value': ('timemachine', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['backup_timemachine']


static_checks.setdefault('battery', [])

static_checks['battery'] = [
{'id': '83a381f9-d4b2-4eab-a709-1d483ba66c1b', 'value': ('cisco_meraki_org_sensor_battery', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['battery']


static_checks.setdefault('bazel_version', [])

static_checks['bazel_version'] = [
{'id': 'afc62dd1-6267-4d12-98d3-02a1f6c755d5', 'value': ('bazel_cache_version', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['bazel_version']


static_checks.setdefault('bgp_peer', [])

static_checks['bgp_peer'] = [
{'id': '79ceb300-a33a-4f2d-90ca-2fa2445395ec', 'value': ('bgp_peer', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['bgp_peer']


static_checks.setdefault('blank_tapes', [])

static_checks['blank_tapes'] = [
{'id': '0dd0de31-1880-4057-9ec8-0468063ab13a', 'value': ('oracle_diva_csm_tapes', None, {'levels_lower': None}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['blank_tapes']


static_checks.setdefault('bluecat_command_server', [])

static_checks['bluecat_command_server'] = [
{'id': '9c32b4d6-0634-4380-802b-06b92be87490', 'value': ('bluecat_command_server', None, {'oper_states': {'warning': [2, 3, 4], 'critical': [5]}}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['bluecat_command_server']


static_checks.setdefault('bluecat_dhcp', [])

static_checks['bluecat_dhcp'] = [
{'id': '0dec0ecf-994a-498d-9de8-5ca2c1372896', 'value': ('bluecat_dhcp', None, {'oper_states': {'warning': [2, 3, 4], 'critical': [5]}}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['bluecat_dhcp']


static_checks.setdefault('bluecat_dns', [])

static_checks['bluecat_dns'] = [
{'id': '4e711cee-df80-4c27-a540-e1e0a22ea50b', 'value': ('bluecat_dns', None, {'oper_states': {'warning': [2, 3, 4], 'critical': [5]}}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['bluecat_dns']


static_checks.setdefault('bluecat_ha', [])

static_checks['bluecat_ha'] = [
{'id': '972db615-63fc-47a5-818e-1f965cfd3cd7', 'value': ('bluecat_ha', None, {'oper_states': {'warning': [5, 6, 7], 'critical': [4, 8]}}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['bluecat_ha']


static_checks.setdefault('bluecat_ntp', [])

static_checks['bluecat_ntp'] = [
{'id': '26c8aae7-2e07-4e96-acf8-514490f79e19', 'value': ('bluecat_ntp', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['bluecat_ntp']


static_checks.setdefault('bonding', [])

static_checks['bonding'] = [
{'id': 'ebfc32b5-1c25-4ae2-8a4d-03b73b1b7390', 'value': ('bonding', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['bonding']


static_checks.setdefault('bossock_fibers', [])

static_checks['bossock_fibers'] = [
{'id': '1d879504-b2de-4a63-ac93-028cd718db27', 'value': ('hitachi_hnas_bossock', 'example', {'levels': None}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['bossock_fibers']


static_checks.setdefault('brightness', [])

static_checks['brightness'] = [
{'id': 'c07a7979-92f3-45a6-8269-8146fd2016fc', 'value': ('tinkerforge_ambient', '', {'levels': (50.0, 100.0)}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['brightness']


static_checks.setdefault('brocade_fcport', [])

static_checks['brocade_fcport'] = [
{'id': 'c1567391-6cfe-41dc-abce-af0cd80a5d25', 'value': ('brocade_fcport', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['brocade_fcport']


static_checks.setdefault('brocade_optical', [])

static_checks['brocade_optical'] = [
{'id': '546e3ec1-9101-4851-8c34-0ba010d75249', 'value': ('brocade_optical', 'example', {'temp': True, 'tx_light': False, 'rx_light': False, 'lanes': False}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['brocade_optical']


static_checks.setdefault('brocade_sfp', [])

static_checks['brocade_sfp'] = [
{'id': '5e59dfdd-2493-484f-be1f-92787d5ee6b0', 'value': ('brocade_sfp', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['brocade_sfp']


static_checks.setdefault('bvip_link', [])

static_checks['bvip_link'] = [
{'id': 'a310ab92-3567-4d3c-9dad-d7c2ca79668c', 'value': ('bvip_link', None, {'ok_states': [0, 4, 5], 'warn_states': [7], 'crit_states': [1, 2, 3]}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['bvip_link']


static_checks.setdefault('byte_count', [])

static_checks['byte_count'] = [
{'id': 'd86363fc-8a5d-4684-a0b7-181e18ab6e13', 'value': ('azure_load_balancer_byte_count', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['byte_count']


static_checks.setdefault('carbon_monoxide', [])

static_checks['carbon_monoxide'] = [
{'id': 'd1916540-3838-41ff-bbe2-6a12c574f966', 'value': ('kentix_co', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['carbon_monoxide']


static_checks.setdefault('checkpoint_connections', [])

static_checks['checkpoint_connections'] = [
{'id': '439bb868-b048-4226-b2ed-d687420e9ebe', 'value': ('checkpoint_connections', None, {'levels': (40000, 50000)}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['checkpoint_connections']


static_checks.setdefault('checkpoint_packets', [])

static_checks['checkpoint_packets'] = [
{'id': '3d46143a-7920-4c55-b95d-a27f9db3a5d0', 'value': ('checkpoint_packets', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['checkpoint_packets']


static_checks.setdefault('checkpoint_tunnels', [])

static_checks['checkpoint_tunnels'] = [
{'id': 'a80546d8-4e77-4a94-af23-81f330f4ed04', 'value': ('checkpoint_tunnels', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['checkpoint_tunnels']


static_checks.setdefault('checkpoint_vsx_connections', [])

static_checks['checkpoint_vsx_connections'] = [
{'id': '702641dd-72f7-4918-abfa-eff1d5467bb9', 'value': ('checkpoint_vsx_connections', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['checkpoint_vsx_connections']


static_checks.setdefault('checkpoint_vsx_packets', [])

static_checks['checkpoint_vsx_packets'] = [
{'id': 'c6450ed7-ce34-46ac-8ac9-bb5c258ba05c', 'value': ('checkpoint_vsx_packets', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['checkpoint_vsx_packets']


static_checks.setdefault('checkpoint_vsx_traffic', [])

static_checks['checkpoint_vsx_traffic'] = [
{'id': '4bc8ee16-3ff4-4d25-929c-d2be68023c8f', 'value': ('checkpoint_vsx_traffic', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['checkpoint_vsx_traffic']


static_checks.setdefault('cisco_asa_failover', [])

static_checks['cisco_asa_failover'] = [
{'id': '5cc60650-e983-4d02-ac62-770d6ef2c50e', 'value': ('cisco_asa_failover', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['cisco_asa_failover']


static_checks.setdefault('cisco_cpu_memory', [])

static_checks['cisco_cpu_memory'] = [
{'id': '1dde7905-3033-4f98-a3cb-25ed77632904', 'value': ('cisco_cpu_memory', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['cisco_cpu_memory']


static_checks.setdefault('cisco_dom', [])

static_checks['cisco_dom'] = [
{'id': '545537a5-7d66-49cb-a4d0-b37f49884b5e', 'value': ('cisco_temperature_dom', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['cisco_dom']


static_checks.setdefault('cisco_fw_connections', [])

static_checks['cisco_fw_connections'] = [
{'id': '53b15553-77c7-4ba8-93cf-e697f5ed7310', 'value': ('cisco_asa_connections', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['cisco_fw_connections']


static_checks.setdefault('cisco_ip_sla', [])

static_checks['cisco_ip_sla'] = [
{'id': '02e43f42-c193-4559-b95e-4e17174278ce', 'value': ('cisco_ip_sla', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['cisco_ip_sla']


static_checks.setdefault('cisco_mem', [])

static_checks['cisco_mem'] = [
{'id': '406628c5-c3f1-49b1-8a0f-2d1a9423a3de', 'value': ('cisco_mem', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['cisco_mem']


static_checks.setdefault('cisco_meraki_org_device_status', [])

static_checks['cisco_meraki_org_device_status'] = [
{'id': '61e23397-a81e-458e-87fb-52b4d23fe70d', 'value': ('cisco_meraki_org_device_status', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['cisco_meraki_org_device_status']


static_checks.setdefault('cisco_meraki_org_device_status_ps', [])

static_checks['cisco_meraki_org_device_status_ps'] = [
{'id': '2f9c5ea6-a6da-46a5-a003-5b2188c97ba6', 'value': ('cisco_meraki_org_device_status_ps', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['cisco_meraki_org_device_status_ps']


static_checks.setdefault('cisco_meraki_org_licenses_overview', [])

static_checks['cisco_meraki_org_licenses_overview'] = [
{'id': '83249bfb-3611-4902-928f-53c4a1a4b791', 'value': ('cisco_meraki_org_licenses_overview', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['cisco_meraki_org_licenses_overview']


static_checks.setdefault('cisco_prime_wifi_access_points', [])

static_checks['cisco_prime_wifi_access_points'] = [
{'id': '12bd8469-acc6-43da-8c16-5927ce35ce04', 'value': ('cisco_prime_wifi_access_points', None, {'levels': (20.0, 40.0)}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['cisco_prime_wifi_access_points']


static_checks.setdefault('cisco_prime_wifi_connections', [])

static_checks['cisco_prime_wifi_connections'] = [
{'id': '3f18129c-42c9-41a1-ba44-44f3ff3c73d4', 'value': ('cisco_prime_wifi_connections', None, {'levels_lower': None}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['cisco_prime_wifi_connections']


static_checks.setdefault('cisco_prime_wlan_controller_access_points', [])

static_checks['cisco_prime_wlan_controller_access_points'] = [
{'id': '5b98d18b-bf0b-42bd-801e-709f6c888a48', 'value': ('cisco_prime_wlan_controller_access_points', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['cisco_prime_wlan_controller_access_points']


static_checks.setdefault('cisco_prime_wlan_controller_clients', [])

static_checks['cisco_prime_wlan_controller_clients'] = [
{'id': 'f3650379-2b7d-4327-b252-999509ef6d38', 'value': ('cisco_prime_wlan_controller_clients', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['cisco_prime_wlan_controller_clients']


static_checks.setdefault('cisco_prime_wlan_controller_last_backup', [])

static_checks['cisco_prime_wlan_controller_last_backup'] = [
{'id': '45569758-22b3-461b-abf1-fe7d7725a131', 'value': ('cisco_prime_wlan_controller_last_backup', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['cisco_prime_wlan_controller_last_backup']


static_checks.setdefault('cisco_qos', [])

static_checks['cisco_qos'] = [
{'id': '6be98574-848c-4fe1-8cc5-974752a01479', 'value': ('cisco_qos', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['cisco_qos']


static_checks.setdefault('cisco_stack', [])

static_checks['cisco_stack'] = [
{'id': 'ceea7952-be5a-43be-8c45-152da2d66d0b', 'value': ('cisco_stack', '', {'waiting': 0, 'progressing': 0, 'added': 0, 'ready': 0, 'sdmMismatch': 1, 'verMismatch': 1, 'featureMismatch': 1, 'newMasterInit': 0, 'provisioned': 0, 'invalid': 2, 'removed': 2}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['cisco_stack']


static_checks.setdefault('cisco_supervisor_mem', [])

static_checks['cisco_supervisor_mem'] = [
{'id': '9d0d8160-fbda-43d5-8aa8-95bbd163944e', 'value': ('cisco_sys_mem', None, {'levels': None}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['cisco_supervisor_mem']


static_checks.setdefault('cisco_vpn_sessions', [])

static_checks['cisco_vpn_sessions'] = [
{'id': '5c83a903-bd56-4197-91ea-38515873deed', 'value': ('cisco_vpn_sessions', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['cisco_vpn_sessions']


static_checks.setdefault('cisco_wlc', [])

static_checks['cisco_wlc'] = [
{'id': '2a86892e-246f-4cb3-a91b-5409775c530b', 'value': ('cisco_wlc', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['cisco_wlc']


static_checks.setdefault('citrix_desktops_registered', [])

static_checks['citrix_desktops_registered'] = [
{'id': '3c79d1ff-1588-41b9-8851-a0ecc66850b5', 'value': ('citrix_controller_registered', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['citrix_desktops_registered']


static_checks.setdefault('citrix_licenses', [])

static_checks['citrix_licenses'] = [
{'id': 'd10aead5-5eee-47e6-b7fd-613c3a24d1de', 'value': ('citrix_licenses', 'example', {'levels': ('crit_on_all', None)}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['citrix_licenses']


static_checks.setdefault('citrix_load', [])

static_checks['citrix_load'] = [
{'id': '9a4affb7-5b82-49b3-88b5-4af2c4967232', 'value': ('citrix_serverload', None, {'levels': None}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['citrix_load']


static_checks.setdefault('citrix_sessions', [])

static_checks['citrix_sessions'] = [
{'id': '3c74c719-4fdf-4aa1-a748-baa6affb7e8f', 'value': ('citrix_controller_sessions', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['citrix_sessions']


static_checks.setdefault('citrix_state', [])

static_checks['citrix_state'] = [
{'id': 'd75a929f-28e1-43b8-90de-a399ca6f8947', 'value': ('citrix_state', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['citrix_state']


static_checks.setdefault('clr_memory', [])

static_checks['clr_memory'] = [
{'id': '5c2ef4a5-f621-4c06-bb60-2b73ac387094', 'value': ('dotnet_clrmemory', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['clr_memory']


static_checks.setdefault('cluster_status', [])

static_checks['cluster_status'] = [
{'id': '346894b5-14b4-4a03-8b84-d9f8ee0f16b2', 'value': ('f5_bigip_cluster_status', None, {'type': 'active_standby'}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['cluster_status']


static_checks.setdefault('couchbase_cache', [])

static_checks['couchbase_cache'] = [
{'id': '7b7d5552-bcb1-4e6c-bc5a-d2d8019f5efa', 'value': ('couchbase_buckets_cache', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['couchbase_cache']


static_checks.setdefault('couchbase_fragmentation', [])

static_checks['couchbase_fragmentation'] = [
{'id': '8249b30b-df8f-4d6c-b0cb-3ead7186132d', 'value': ('couchbase_buckets_fragmentation', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['couchbase_fragmentation']


static_checks.setdefault('couchbase_items', [])

static_checks['couchbase_items'] = [
{'id': '4267fa6d-b9a3-4919-a383-e67175562c37', 'value': ('couchbase_buckets_items', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['couchbase_items']


static_checks.setdefault('couchbase_ops', [])

static_checks['couchbase_ops'] = [
{'id': '48342698-6339-48f4-a4d5-3d2cfa46d4af', 'value': ('couchbase_buckets_operations', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['couchbase_ops']


static_checks.setdefault('couchbase_ops_buckets', [])

static_checks['couchbase_ops_buckets'] = [
{'id': 'c4f50f2f-d120-40c1-9965-c32ee589f5d4', 'value': ('couchbase_buckets_operations_total', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['couchbase_ops_buckets']


static_checks.setdefault('couchbase_ops_nodes', [])

static_checks['couchbase_ops_nodes'] = [
{'id': 'a50bc2c7-147a-49b2-b4b9-9a40bd065ae5', 'value': ('couchbase_nodes_operations_total', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['couchbase_ops_nodes']


static_checks.setdefault('couchbase_size_couch', [])

static_checks['couchbase_size_couch'] = [
{'id': '5bb3ad03-edb8-4a5c-a436-389cd4c3be55', 'value': ('couchbase_nodes_size_couch_views', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['couchbase_size_couch']


static_checks.setdefault('couchbase_size_docs', [])

static_checks['couchbase_size_docs'] = [
{'id': '3a1ce8e7-47f2-4129-a96b-9d3d2bff111a', 'value': ('couchbase_nodes_size_docs', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['couchbase_size_docs']


static_checks.setdefault('couchbase_size_spacial', [])

static_checks['couchbase_size_spacial'] = [
{'id': '514175fa-dfd6-4c5b-906f-e3f1c3bb94f4', 'value': ('couchbase_nodes_size_spacial_views', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['couchbase_size_spacial']


static_checks.setdefault('couchbase_status', [])

static_checks['couchbase_status'] = [
{'id': '14d9ff64-5157-400c-b522-70bd54edae00', 'value': ('couchbase_nodes_info', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['couchbase_status']


static_checks.setdefault('couchbase_vbuckets', [])

static_checks['couchbase_vbuckets'] = [
{'id': '7956f050-6732-4d08-bb64-8b27d962dcbb', 'value': ('couchbase_buckets_vbuckets', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['couchbase_vbuckets']


static_checks.setdefault('cpu_iowait', [])

static_checks['cpu_iowait'] = [
{'id': '80ae1e80-f54a-4d8d-9bdd-7ae65a2b4bf4', 'value': ('kernel_util', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['cpu_iowait']


static_checks.setdefault('cpu_load', [])

static_checks['cpu_load'] = [
{'id': '96206b87-0bcd-4356-b09c-c56113a568b8', 'value': ('blade_bx_load', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['cpu_load']


static_checks.setdefault('cpu_utilization', [])

static_checks['cpu_utilization'] = [
{'id': 'a75e1073-da62-4318-8435-cd848184299d', 'value': ('alcatel_timetra_cpu', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['cpu_utilization']


static_checks.setdefault('cpu_utilization_esx_vsphere_hostsystem', [])

static_checks['cpu_utilization_esx_vsphere_hostsystem'] = [
{'id': '901f3718-366e-4cf0-9551-584223f32e44', 'value': ('esx_vsphere_hostsystem_cpu_usage', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['cpu_utilization_esx_vsphere_hostsystem']


static_checks.setdefault('cpu_utilization_multiitem', [])

static_checks['cpu_utilization_multiitem'] = [
{'id': 'f57ac2a2-3844-441d-859b-d4e0a7ed94d6', 'value': ('arris_cmts_cpu', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['cpu_utilization_multiitem']


static_checks.setdefault('cpu_utilization_os', [])

static_checks['cpu_utilization_os'] = [
{'id': '4919c548-3e77-40bc-b99c-dab1bffc0c0d', 'value': ('bintec_cpu', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['cpu_utilization_os']


static_checks.setdefault('cpu_utilization_with_item', [])

static_checks['cpu_utilization_with_item'] = [
{'id': 'f6eb221b-1edb-4e43-bac6-cd239943a0e6', 'value': ('azure_mysql_cpu', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['cpu_utilization_with_item']


static_checks.setdefault('credentials_expiration', [])

static_checks['credentials_expiration'] = [
{'id': '02a1e5b6-c134-46b6-8c45-a4405ed5c77d', 'value': ('azure_app_registration', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['credentials_expiration']


static_checks.setdefault('cups_queues', [])

static_checks['cups_queues'] = [
{'id': 'b736cd03-c04f-4132-951e-af438cbbb666', 'value': ('cups_queues', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['cups_queues']


static_checks.setdefault('database_connections', [])

static_checks['database_connections'] = [
{'id': '5e911aa0-032e-4e0f-ba8d-6f130aa944cc', 'value': ('azure_mysql_connections', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['database_connections']


static_checks.setdefault('datadog_monitors_check', [])

static_checks['datadog_monitors_check'] = [
{'id': '8cbfe66d-d657-4c5a-9702-4305d6992811', 'value': ('datadog_monitors', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['datadog_monitors_check']


static_checks.setdefault('db2_backup', [])

static_checks['db2_backup'] = [
{'id': '1b6b9f74-cea3-49b9-9ef0-fcddeecadd2b', 'value': ('db2_backup', '', {'levels': None}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['db2_backup']


static_checks.setdefault('db2_connections', [])

static_checks['db2_connections'] = [
{'id': '85253da7-8f46-4270-afcd-2e03da525662', 'value': ('db2_connections', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['db2_connections']


static_checks.setdefault('db2_counters', [])

static_checks['db2_counters'] = [
{'id': '92cd21b0-d22d-4726-aabf-0df75bd7030b', 'value': ('db2_counters', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['db2_counters']


static_checks.setdefault('db2_logsize', [])

static_checks['db2_logsize'] = [
{'id': '874c51ae-7d25-430a-83a3-057fa990a7f8', 'value': ('db2_logsizes', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['db2_logsize']


static_checks.setdefault('db2_mem', [])

static_checks['db2_mem'] = [
{'id': '725e6fd3-1089-4551-931d-954a707b183d', 'value': ('db2_mem', '', {'levels_lower': None}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['db2_mem']


static_checks.setdefault('db2_sortoverflow', [])

static_checks['db2_sortoverflow'] = [
{'id': '978a1ccb-4367-4e16-a5dd-72c1b199c036', 'value': ('db2_sort_overflow', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['db2_sortoverflow']


static_checks.setdefault('db2_tablespaces', [])

static_checks['db2_tablespaces'] = [
{'id': '28f26be8-8046-4c0d-bc96-bda648357c45', 'value': ('db2_tablespaces', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['db2_tablespaces']


static_checks.setdefault('db_bloat', [])

static_checks['db_bloat'] = [
{'id': 'f53a4438-5921-4c9e-a77b-3d20a408886d', 'value': ('postgres_bloat', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['db_bloat']


static_checks.setdefault('db_connections', [])

static_checks['db_connections'] = [
{'id': '90087da1-46ae-4fa5-b1ac-ebd567902b70', 'value': ('postgres_connections', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['db_connections']


static_checks.setdefault('db_connections_mongodb', [])

static_checks['db_connections_mongodb'] = [
{'id': 'd61eff59-27a7-47d4-943d-519494ac332b', 'value': ('mongodb_connections', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['db_connections_mongodb']


static_checks.setdefault('db_usage', [])

static_checks['db_usage'] = [
{'id': 'd49bb504-0db9-4190-a164-ba8e9676897a', 'value': ('primekey_db_usage', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['db_usage']


static_checks.setdefault('ddn_s2a_port_errors', [])

static_checks['ddn_s2a_port_errors'] = [
{'id': 'e7acc222-e0f6-4e4f-8f53-e7c05e82c8e8', 'value': ('ddn_s2a_errors', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['ddn_s2a_port_errors']


static_checks.setdefault('ddn_s2a_wait', [])

static_checks['ddn_s2a_wait'] = [
{'id': '6204b9fa-def1-442c-af63-ba1fe5788ee4', 'value': ('ddn_s2a_statsdelay', 'Disk', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['ddn_s2a_wait']


static_checks.setdefault('disk_failures', [])

static_checks['disk_failures'] = [
{'id': '5cdffbfb-c006-4b72-910c-1858770996c1', 'value': ('ddn_s2a_faultsbasic_disks', None, {'levels': None}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['disk_failures']


static_checks.setdefault('disk_io', [])

static_checks['disk_io'] = [
{'id': '291cc518-694d-4e7b-b1ef-68f645db1bd2', 'value': ('winperf_phydisk', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['disk_io']


static_checks.setdefault('diskstat', [])

static_checks['diskstat'] = [
{'id': '79b4e763-b615-441d-bb6f-454783036f90', 'value': ('aws_ebs', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['diskstat']


static_checks.setdefault('docker_node_containers', [])

static_checks['docker_node_containers'] = [
{'id': 'f23487ca-ba8f-4a40-ad7e-7ac9c80e4cd3', 'value': ('docker_node_info_containers', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['docker_node_containers']


static_checks.setdefault('docker_node_disk_usage', [])

static_checks['docker_node_disk_usage'] = [
{'id': '333c2fa3-b1ba-4ee6-90e5-58765579809a', 'value': ('docker_node_disk_usage', 'buildcache', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['docker_node_disk_usage']


static_checks.setdefault('docsis_channels_downstream', [])

static_checks['docsis_channels_downstream'] = [
{'id': '9b903151-fafa-430f-a5e4-08f67d39d8aa', 'value': ('docsis_channels_downstream', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['docsis_channels_downstream']


static_checks.setdefault('docsis_channels_upstream', [])

static_checks['docsis_channels_upstream'] = [
{'id': '2891d835-6982-4729-b1fb-d0973cb08db1', 'value': ('docsis_channels_upstream', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['docsis_channels_upstream']


static_checks.setdefault('docsis_cm_status', [])

static_checks['docsis_cm_status'] = [
{'id': '34743c00-54f2-4ed9-b1fa-0e255f71dbcf', 'value': ('docsis_cm_status', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['docsis_cm_status']


static_checks.setdefault('domino_mailqueues', [])

static_checks['domino_mailqueues'] = [
{'id': '4c58701d-2bd2-438d-b90a-6ddbe0e5b211', 'value': ('domino_mailqueues', 'lnDeadMail', {'queue_length': (300, 350)}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['domino_mailqueues']


static_checks.setdefault('domino_tasks', [])

static_checks['domino_tasks'] = [
{'id': 'eb7d8d24-6377-4ae4-b2c7-5e2fce1637f4', 'value': ('domino_tasks', 'example', {'levels': (1, 1, 99999, 99999)}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['domino_tasks']


static_checks.setdefault('domino_transactions', [])

static_checks['domino_transactions'] = [
{'id': 'df9d7c50-f0fd-405e-963a-9cbab27504a7', 'value': ('domino_transactions', None, {'levels': None}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['domino_transactions']


static_checks.setdefault('domino_users', [])

static_checks['domino_users'] = [
{'id': '46f4a0cb-8cc7-4cb3-afae-70b6ac2787ea', 'value': ('domino_users', None, {'levels': None}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['domino_users']


static_checks.setdefault('drbd', [])

static_checks['drbd'] = [
{'id': 'cfd4a9fd-8882-4e92-97ad-0c57897b6d52', 'value': ('drbd', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['drbd']


static_checks.setdefault('eaton_enviroment', [])

static_checks['eaton_enviroment'] = [
{'id': '4d219d25-0f78-4778-aae0-77916029d26e', 'value': ('ups_eaton_enviroment', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['eaton_enviroment']


static_checks.setdefault('efreq', [])

static_checks['efreq'] = [
{'id': 'a609b7ae-4e8a-40df-9db4-d28fd0ffd9ed', 'value': ('janitza_umg_freq', 'example', {'levels_lower': (40, 45)}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['efreq']


static_checks.setdefault('el_inphase', [])

static_checks['el_inphase'] = [
{'id': '016b5eaf-6a16-45f6-b190-a039db8f8aa5', 'value': ('acme_voltage', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['el_inphase']


static_checks.setdefault('elasticsearch_cluster_health', [])

static_checks['elasticsearch_cluster_health'] = [
{'id': '4f1edfd2-169b-40aa-b6c4-e2fa70c0e132', 'value': ('elasticsearch_cluster_health', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['elasticsearch_cluster_health']


static_checks.setdefault('elasticsearch_cluster_shards', [])

static_checks['elasticsearch_cluster_shards'] = [
{'id': '59f66e45-01bd-4781-a83b-b54898739a45', 'value': ('elasticsearch_cluster_health_shards', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['elasticsearch_cluster_shards']


static_checks.setdefault('elasticsearch_cluster_tasks', [])

static_checks['elasticsearch_cluster_tasks'] = [
{'id': '17ff300a-9c26-4b1c-aff8-e3f5d747295b', 'value': ('elasticsearch_cluster_health_tasks', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['elasticsearch_cluster_tasks']


static_checks.setdefault('elasticsearch_indices', [])

static_checks['elasticsearch_indices'] = [
{'id': '32ff818a-1603-4d57-b257-b1335539af26', 'value': ('elasticsearch_indices', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['elasticsearch_indices']


static_checks.setdefault('elasticsearch_nodes', [])

static_checks['elasticsearch_nodes'] = [
{'id': '41b549ad-037f-4f5e-bf4d-8ff023f80df1', 'value': ('elasticsearch_nodes', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['elasticsearch_nodes']


static_checks.setdefault('emc_datadomain_mtree', [])

static_checks['emc_datadomain_mtree'] = [
{'id': 'c43fa708-91c1-4f61-a2c5-5a4bcb45ba07', 'value': ('emc_datadomain_mtree', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['emc_datadomain_mtree']


static_checks.setdefault('enterasys_powersupply', [])

static_checks['enterasys_powersupply'] = [
{'id': '4b6dd5a7-da35-43b4-b9be-6f0edcfc2a75', 'value': ('enterasys_powersupply', '', {'redundancy_ok_states': [1]}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['enterasys_powersupply']


static_checks.setdefault('entersekt_certexpiry', [])

static_checks['entersekt_certexpiry'] = [
{'id': 'f1ddb91a-cdb1-4a49-928a-9f53c2775b11', 'value': ('entersekt_certexpiry', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['entersekt_certexpiry']


static_checks.setdefault('entersekt_ecerterrors', [])

static_checks['entersekt_ecerterrors'] = [
{'id': '78eb6c62-094e-4db3-aaa7-6c72b2e4ceff', 'value': ('entersekt_ecerterrors', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['entersekt_ecerterrors']


static_checks.setdefault('entersekt_emrerrors', [])

static_checks['entersekt_emrerrors'] = [
{'id': '5a6284be-1fbf-4c58-b2de-bb8fd8593f81', 'value': ('entersekt_emrerrors', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['entersekt_emrerrors']


static_checks.setdefault('entersekt_soaperrors', [])

static_checks['entersekt_soaperrors'] = [
{'id': '368e00e8-b475-4914-bb39-67cb35bf998d', 'value': ('entersekt_soaperrors', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['entersekt_soaperrors']


static_checks.setdefault('epower', [])

static_checks['epower'] = [
{'id': 'ef961f58-6f94-424f-ae5d-8201a3d05a79', 'value': ('epower', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['epower']


static_checks.setdefault('epower_single', [])

static_checks['epower_single'] = [
{'id': '22fe6fd3-2d79-4a4c-9ad3-bac2959c7b4e', 'value': ('bvip_poe', None, {'levels': None}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['epower_single']


static_checks.setdefault('esx_host_memory', [])

static_checks['esx_host_memory'] = [
{'id': '05a2e6f8-5f0b-4332-8c09-f1de04705552', 'value': ('esx_vsphere_hostsystem_mem_usage', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['esx_host_memory']


static_checks.setdefault('esx_hostystem_maintenance', [])

static_checks['esx_hostystem_maintenance'] = [
{'id': 'a24a7325-2fdd-48fa-a021-fec08ed414a3', 'value': ('esx_vsphere_hostsystem_maintenance', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['esx_hostystem_maintenance']


static_checks.setdefault('esx_licenses', [])

static_checks['esx_licenses'] = [
{'id': 'c2859783-013d-43df-b3ce-cbcce93fe4bb', 'value': ('esx_vsphere_licenses', 'example', {'levels': ('crit_on_all', None)}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['esx_licenses']


static_checks.setdefault('esx_vsphere_datastores', [])

static_checks['esx_vsphere_datastores'] = [
{'id': '7ab592f1-80c0-4da8-9798-085d5c07e78d', 'value': ('esx_vsphere_datastores', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['esx_vsphere_datastores']


static_checks.setdefault('esx_vsphere_objects', [])

static_checks['esx_vsphere_objects'] = [
{'id': '010b3687-a613-4274-a297-0a474668f06c', 'value': ('esx_vsphere_objects', 'VM example-host', {'states': {'standBy': 1, 'poweredOn': 0, 'poweredOff': 1, 'suspended': 1, 'unknown': 3}}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['esx_vsphere_objects']


static_checks.setdefault('esx_vsphere_objects_count', [])

static_checks['esx_vsphere_objects_count'] = [
{'id': '42f6088b-643a-4448-bf39-ce58302c8cf3', 'value': ('esx_vsphere_objects_count', None, {'distribution': []}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['esx_vsphere_objects_count']


static_checks.setdefault('esx_vsphere_vm_memory', [])

static_checks['esx_vsphere_vm_memory'] = [
{'id': '9f63b8d0-4e90-41b4-96fe-1339448f537d', 'value': ('esx_vsphere_vm_mem_usage', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['esx_vsphere_vm_memory']


static_checks.setdefault('etherbox_smoke', [])

static_checks['etherbox_smoke'] = [
{'id': '08ef4725-6dc5-4ee9-b2a3-0d3cee6df89e', 'value': ('etherbox_smoke', '', {'smoke_handling': ('binary', (0, 0))}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['etherbox_smoke']


static_checks.setdefault('etherbox_voltage', [])

static_checks['etherbox_voltage'] = [
{'id': '85a949cb-2063-407a-9c8a-674f7226a5e7', 'value': ('etherbox_voltage', 'example', {'levels': ('fixed', (0.0, 0.0))}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['etherbox_voltage']


static_checks.setdefault('evolt', [])

static_checks['evolt'] = [
{'id': '4bbd1c3d-a369-428b-9f0b-8cc1352fced8', 'value': ('emc_isilon_power', 'example', {'levels_lower': (210.0, 180.0)}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['evolt']


static_checks.setdefault('ewon', [])

static_checks['ewon'] = [
{'id': 'b63852fd-a303-449a-a0de-0d7c97d314c8', 'value': ('ewon', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['ewon']


static_checks.setdefault('f5_bigip_cluster_v11', [])

static_checks['f5_bigip_cluster_v11'] = [
{'id': 'ec7abc7f-2bca-483a-bc96-a4e57ea1e4c4', 'value': ('f5_bigip_cluster_v11', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['f5_bigip_cluster_v11']


static_checks.setdefault('f5_bigip_snat', [])

static_checks['f5_bigip_snat'] = [
{'id': '744b7da7-ddf6-43e9-bae3-496b89e6016b', 'value': ('f5_bigip_snat', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['f5_bigip_snat']


static_checks.setdefault('f5_bigip_vserver', [])

static_checks['f5_bigip_vserver'] = [
{'id': 'a1431af9-0596-4473-ad5f-3c09c401d1c3', 'value': ('f5_bigip_vserver', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['f5_bigip_vserver']


static_checks.setdefault('f5_connections', [])

static_checks['f5_connections'] = [
{'id': '5a3799a9-8d10-40ed-a11b-7be76e11a551', 'value': ('f5_bigip_conns', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['f5_connections']


static_checks.setdefault('f5_pools', [])

static_checks['f5_pools'] = [
{'id': 'd203be56-40d7-4bb9-98ae-6fe070fbbbc4', 'value': ('f5_bigip_pool', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['f5_pools']


static_checks.setdefault('fan_failures', [])

static_checks['fan_failures'] = [
{'id': '2fe74358-9a4d-4311-88b3-c864dc7917f8', 'value': ('ddn_s2a_faultsbasic_fans', None, {'levels': None}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['fan_failures']


static_checks.setdefault('fc_port', [])

static_checks['fc_port'] = [
{'id': '028190c1-d72a-4064-841b-87ded85151e7', 'value': ('fc_port', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['fc_port']


static_checks.setdefault('fcp', [])

static_checks['fcp'] = [
{'id': '41b66fd2-ee7d-47f1-8cd2-6fcd7969589b', 'value': ('netapp_ontap_fcp', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['fcp']


static_checks.setdefault('fcport_words', [])

static_checks['fcport_words'] = [
{'id': '679a04ee-0193-43a4-975e-9875f9c413cd', 'value': ('atto_fibrebridge_fcport', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['fcport_words']


static_checks.setdefault('filehandler', [])

static_checks['filehandler'] = [
{'id': '49c6e55e-72fe-494a-8755-fbfb34466de2', 'value': ('filehandler', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['filehandler']


static_checks.setdefault('fileinfo', [])

static_checks['fileinfo'] = [
{'id': 'f183d9aa-e3e9-4c3f-be9e-c20eb6b1dbca', 'value': ('fileinfo', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['fileinfo']


static_checks.setdefault('fileinfo_groups_checking', [])

static_checks['fileinfo_groups_checking'] = [
{'id': '8ab8a23e-6d7d-461f-a010-d93263bf2887', 'value': ('fileinfo_groups', '', {'group_patterns': []}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['fileinfo_groups_checking']


static_checks.setdefault('filestats', [])

static_checks['filestats'] = [
{'id': '8f437321-1a19-4d9c-bec0-9c3bd95bce58', 'value': ('filestats', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['filestats']


static_checks.setdefault('filestats_single', [])

static_checks['filestats_single'] = [
{'id': '04e6a0a0-5e0c-4629-be15-a0a5819c6764', 'value': ('filestats_single', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['filestats_single']


static_checks.setdefault('filesystem', [])

static_checks['filesystem'] = [
{'id': 'cae60f1e-a5af-4df8-b77b-1f9cc49d3d55', 'value': ('3par_volumes', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['filesystem']


static_checks.setdefault('fireeye_active_vms', [])

static_checks['fireeye_active_vms'] = [
{'id': '899a7df4-145a-4962-aa1a-6635da18187c', 'value': ('fireeye_active_vms', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['fireeye_active_vms']


static_checks.setdefault('fireeye_content', [])

static_checks['fireeye_content'] = [
{'id': 'd7b204aa-b792-4cf6-bb82-e89856da4c19', 'value': ('fireeye_content', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['fireeye_content']


static_checks.setdefault('fireeye_lic', [])

static_checks['fireeye_lic'] = [
{'id': '84eec3f9-bda3-4251-9251-078e3dd31dbb', 'value': ('fireeye_lic_expiration', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['fireeye_lic']


static_checks.setdefault('fireeye_mail', [])

static_checks['fireeye_mail'] = [
{'id': 'c124578c-725b-4702-9e07-c18d3bf1f37f', 'value': ('fireeye_mail', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['fireeye_mail']


static_checks.setdefault('fireeye_mailq', [])

static_checks['fireeye_mailq'] = [
{'id': 'b4bc85f1-3a93-493a-af8a-11bc53db1bec', 'value': ('fireeye_mailq', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['fireeye_mailq']


static_checks.setdefault('fireeye_quarantine', [])

static_checks['fireeye_quarantine'] = [
{'id': 'fba7a0d7-15a0-4348-b473-e32017ecb38b', 'value': ('fireeye_quarantine', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['fireeye_quarantine']


static_checks.setdefault('firewall_if', [])

static_checks['firewall_if'] = [
{'id': '29f3c1b7-4de4-4313-b725-d00671a96c64', 'value': ('pfsense_if', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['firewall_if']


static_checks.setdefault('fortiauthenticator_auth_fail', [])

static_checks['fortiauthenticator_auth_fail'] = [
{'id': 'e1e2d939-c6e1-4a3d-aeb6-775ffddaea0c', 'value': ('fortiauthenticator_auth_fail', None, {'auth_fails': (100, 200)}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['fortiauthenticator_auth_fail']


static_checks.setdefault('fortigate_antivirus', [])

static_checks['fortigate_antivirus'] = [
{'id': '144e848b-c43f-4cba-ac7f-d8007ef7964c', 'value': ('fortigate_antivirus', 'example', {'detections': (100.0, 300.0)}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['fortigate_antivirus']


static_checks.setdefault('fortigate_ips', [])

static_checks['fortigate_ips'] = [
{'id': 'd2f09369-e0e3-4875-a5cd-f25c0d2c0e13', 'value': ('fortigate_ips', 'example', {'detections': (100.0, 300.0)}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['fortigate_ips']


static_checks.setdefault('fortigate_node_memory', [])

static_checks['fortigate_node_memory'] = [
{'id': 'a0f70fb1-b6c5-49a3-a3d5-06d23f672f10', 'value': ('fortigate_node_memory', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['fortigate_node_memory']


static_checks.setdefault('fortigate_node_sessions', [])

static_checks['fortigate_node_sessions'] = [
{'id': '68b032f3-de2c-44e2-b126-d017973eea1f', 'value': ('fortigate_node_sessions', 'example', {'levels': None}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['fortigate_node_sessions']


static_checks.setdefault('fortigate_sessions', [])

static_checks['fortigate_sessions'] = [
{'id': '82855e69-82e8-46e9-a5d4-7406889cd7c2', 'value': ('fortigate_sessions', None, {'levels': None}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['fortigate_sessions']


static_checks.setdefault('fortigate_sslvpn', [])

static_checks['fortigate_sslvpn'] = [
{'id': '16bf6aa1-088e-4c07-b93e-099b98940d09', 'value': ('fortigate_sslvpn', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['fortigate_sslvpn']


static_checks.setdefault('fortimail_cpu_load', [])

static_checks['fortimail_cpu_load'] = [
{'id': 'eb43e4ce-2b3a-426e-b44a-5da843c7a49d', 'value': ('fortimail_cpu_load', None, {'cpu_load': None}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['fortimail_cpu_load']


static_checks.setdefault('fortimail_disk_usage', [])

static_checks['fortimail_disk_usage'] = [
{'id': 'f57ff25f-7d77-4196-9a32-0830abed365b', 'value': ('fortimail_disk_usage', None, {'disk_usage': (80.0, 90.0)}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['fortimail_disk_usage']


static_checks.setdefault('fortimail_queue', [])

static_checks['fortimail_queue'] = [
{'id': '77df2f5c-c01c-47a1-bfa7-a7a3b651c363', 'value': ('fortimail_queue', 'example', {'queue_length': (100, 200)}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['fortimail_queue']


static_checks.setdefault('fortinet_signatures', [])

static_checks['fortinet_signatures'] = [
{'id': '1bbd1ea0-c440-45ec-a8e8-39d8db0969c9', 'value': ('fortigate_signatures', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['fortinet_signatures']


static_checks.setdefault('fortisandbox_queues', [])

static_checks['fortisandbox_queues'] = [
{'id': '75c444ed-518f-41a4-86bc-07ab5b885c35', 'value': ('fortisandbox_queues', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['fortisandbox_queues']


static_checks.setdefault('fpga_utilization', [])

static_checks['fpga_utilization'] = [
{'id': 'bfbd6454-f671-495a-a9b7-ee242e443dc3', 'value': ('hitachi_hnas_fpga', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['fpga_utilization']


static_checks.setdefault('fs_mount_options', [])

static_checks['fs_mount_options'] = [
{'id': 'fe518001-83aa-406a-b231-06babd45b5c8', 'value': ('mounts', 'example', {'expected_mount_options': []}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['fs_mount_options']


static_checks.setdefault('gcp_cost', [])

static_checks['gcp_cost'] = [
{'id': 'f6eec194-026b-4b0e-b035-77ae77f3ec76', 'value': ('gcp_cost', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['gcp_cost']


static_checks.setdefault('gcp_filestore_disk', [])

static_checks['gcp_filestore_disk'] = [
{'id': '24167e00-4633-4ded-8297-3524e7d60186', 'value': ('gcp_filestore_disk', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['gcp_filestore_disk']


static_checks.setdefault('gcp_gce_cpu', [])

static_checks['gcp_gce_cpu'] = [
{'id': '0155dde2-9b71-4f61-b190-190b02482b59', 'value': ('gcp_gce_cpu', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['gcp_gce_cpu']


static_checks.setdefault('gcp_gce_disk', [])

static_checks['gcp_gce_disk'] = [
{'id': 'adc4b27c-26ce-4922-934e-ccabca7600c4', 'value': ('gcp_gce_disk_summary', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['gcp_gce_disk']


static_checks.setdefault('gcp_gce_storage', [])

static_checks['gcp_gce_storage'] = [
{'id': 'd4f0871e-3b1e-40c6-b8cb-10f3c55dec2a', 'value': ('gcp_gce_storage', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['gcp_gce_storage']


static_checks.setdefault('gcp_gcs_network', [])

static_checks['gcp_gcs_network'] = [
{'id': 'abb82fda-caf9-4b0b-882d-4a5af89c5d12', 'value': ('gcp_gcs_network', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['gcp_gcs_network']


static_checks.setdefault('gcp_gcs_objects', [])

static_checks['gcp_gcs_objects'] = [
{'id': '64b969af-5223-4f28-a233-971cd029e039', 'value': ('gcp_gcs_objects', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['gcp_gcs_objects']


static_checks.setdefault('gcp_gcs_requests', [])

static_checks['gcp_gcs_requests'] = [
{'id': 'e5439ac6-f775-47ec-b43e-a53144d1dee3', 'value': ('gcp_gcs_requests', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['gcp_gcs_requests']


static_checks.setdefault('gcp_http_lb_latencies', [])

static_checks['gcp_http_lb_latencies'] = [
{'id': '5d5369c0-a389-40a3-8ddd-f9d800434ff0', 'value': ('gcp_http_lb_latencies', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['gcp_http_lb_latencies']


static_checks.setdefault('gcp_http_lb_requests', [])

static_checks['gcp_http_lb_requests'] = [
{'id': 'eb1a48e5-58f0-4b64-ba0e-857fc293b138', 'value': ('gcp_http_lb_requests', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['gcp_http_lb_requests']


static_checks.setdefault('gcp_replication_lag', [])

static_checks['gcp_replication_lag'] = [
{'id': '9d774d4f-5e00-4fc4-883d-aa134e0dc385', 'value': ('gcp_sql_replication', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['gcp_replication_lag']


static_checks.setdefault('gcp_sql_cpu', [])

static_checks['gcp_sql_cpu'] = [
{'id': '98d6e9c5-13dd-4b82-ba38-3640a58ad3f0', 'value': ('gcp_sql_cpu', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['gcp_sql_cpu']


static_checks.setdefault('gcp_sql_disk', [])

static_checks['gcp_sql_disk'] = [
{'id': '3b6730bd-1a39-4764-b328-cbbe01410990', 'value': ('gcp_sql_disk', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['gcp_sql_disk']


static_checks.setdefault('gcp_sql_memory', [])

static_checks['gcp_sql_memory'] = [
{'id': '6b4fc512-d90f-490d-9b2a-343ac14864d5', 'value': ('gcp_sql_memory', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['gcp_sql_memory']


static_checks.setdefault('gcp_sql_network', [])

static_checks['gcp_sql_network'] = [
{'id': 'aead9714-90db-4967-a89b-ef43c8a05755', 'value': ('gcp_sql_network', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['gcp_sql_network']


static_checks.setdefault('gcp_sql_status', [])

static_checks['gcp_sql_status'] = [
{'id': 'cc90299e-7702-4249-b2a5-9ff4cf579db0', 'value': ('gcp_sql_status', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['gcp_sql_status']


static_checks.setdefault('general_flash_usage', [])

static_checks['general_flash_usage'] = [
{'id': 'c9e046ad-6ee8-4fab-af86-b6f806856ecb', 'value': ('juniper_trpz_flash', None, {'levels': (0.0, 0.0)}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['general_flash_usage']


static_checks.setdefault('generic_number', [])

static_checks['generic_number'] = [
{'id': 'bc783597-7534-4091-9fc1-ea21ec5dc957', 'value': ('jolokia_generic', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['generic_number']


static_checks.setdefault('generic_rate', [])

static_checks['generic_rate'] = [
{'id': 'abac66e9-a0eb-4d8a-92ec-554d5a47e1fc', 'value': ('arbor_pravail_drop_rate', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['generic_rate']


static_checks.setdefault('generic_string', [])

static_checks['generic_string'] = [
{'id': '2fd2800e-05a6-4586-97a5-c50fd25ad9c1', 'value': ('jolokia_generic_string', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['generic_string']


static_checks.setdefault('gerrit_version', [])

static_checks['gerrit_version'] = [
{'id': 'c7e65347-5824-439a-af38-108310e4e8bc', 'value': ('gerrit_version', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['gerrit_version']


static_checks.setdefault('globalprotect_utilization', [])

static_checks['globalprotect_utilization'] = [
{'id': 'ec50195e-0cb7-43e6-b62c-be07e7384f3d', 'value': ('globalprotect_utilization', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['globalprotect_utilization']


static_checks.setdefault('graylog_alerts', [])

static_checks['graylog_alerts'] = [
{'id': 'c59761bf-40dd-4575-8378-321d938bc23e', 'value': ('graylog_alerts', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['graylog_alerts']


static_checks.setdefault('graylog_cluster_stats', [])

static_checks['graylog_cluster_stats'] = [
{'id': '35eb4541-8543-4155-8b88-0974a47348cf', 'value': ('graylog_cluster_stats', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['graylog_cluster_stats']


static_checks.setdefault('graylog_cluster_stats_elastic', [])

static_checks['graylog_cluster_stats_elastic'] = [
{'id': '2f4ad2b7-7223-4fbf-ade7-9c5861e0ce90', 'value': ('graylog_cluster_stats_elastic', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['graylog_cluster_stats_elastic']


static_checks.setdefault('graylog_cluster_stats_mongodb', [])

static_checks['graylog_cluster_stats_mongodb'] = [
{'id': '2f3383cd-87ef-46db-b168-e0a6c04ee536', 'value': ('graylog_cluster_stats_mongodb', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['graylog_cluster_stats_mongodb']


static_checks.setdefault('graylog_cluster_traffic', [])

static_checks['graylog_cluster_traffic'] = [
{'id': 'e8bcea86-d5ea-4520-91d5-4c1c1b781543', 'value': ('graylog_cluster_traffic', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['graylog_cluster_traffic']


static_checks.setdefault('graylog_events', [])

static_checks['graylog_events'] = [
{'id': 'bff5e82b-5a57-4532-a80d-e28ab3726be5', 'value': ('graylog_events', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['graylog_events']


static_checks.setdefault('graylog_failures', [])

static_checks['graylog_failures'] = [
{'id': 'a679614b-48e4-4269-8c24-a09897cea3d4', 'value': ('graylog_failures', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['graylog_failures']


static_checks.setdefault('graylog_jvm', [])

static_checks['graylog_jvm'] = [
{'id': '40c2f617-e090-4c1f-8d3e-f663b4f98f28', 'value': ('graylog_jvm', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['graylog_jvm']


static_checks.setdefault('graylog_license', [])

static_checks['graylog_license'] = [
{'id': 'e0e5452c-8885-47e8-9f67-990a4e640828', 'value': ('graylog_license', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['graylog_license']


static_checks.setdefault('graylog_messages', [])

static_checks['graylog_messages'] = [
{'id': 'd3d8c09f-d6d7-474b-8981-31c0e4dfcc3c', 'value': ('graylog_messages', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['graylog_messages']


static_checks.setdefault('graylog_nodes', [])

static_checks['graylog_nodes'] = [
{'id': '0b2a1ce7-569d-465a-bd66-c7356752218e', 'value': ('graylog_nodes', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['graylog_nodes']


static_checks.setdefault('graylog_sidecars', [])

static_checks['graylog_sidecars'] = [
{'id': 'b568c66f-97b6-4ebb-8d65-234e71eade6b', 'value': ('graylog_sidecars', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['graylog_sidecars']


static_checks.setdefault('graylog_sources', [])

static_checks['graylog_sources'] = [
{'id': '51c15732-ea9f-4aca-8838-dbbd52939c02', 'value': ('graylog_sources', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['graylog_sources']


static_checks.setdefault('graylog_streams', [])

static_checks['graylog_streams'] = [
{'id': '6e57d5c7-7afc-49d8-8dfc-8e815589817f', 'value': ('graylog_streams', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['graylog_streams']


static_checks.setdefault('hacmp_resources', [])

static_checks['hacmp_resources'] = [
{'id': '09951488-ff45-4036-9ddf-ecd856cf75b0', 'value': ('aix_hacmp_resources', '', {'expect_online_on': 'first'}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['hacmp_resources']


static_checks.setdefault('haproxy_frontend', [])

static_checks['haproxy_frontend'] = [
{'id': 'd9f1d1c1-b68e-467a-921d-027f6cf521b0', 'value': ('haproxy_frontend', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['haproxy_frontend']


static_checks.setdefault('haproxy_server', [])

static_checks['haproxy_server'] = [
{'id': 'a6acd213-de8e-4720-a682-9efe8532e659', 'value': ('haproxy_backend', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['haproxy_server']


static_checks.setdefault('heartbeat_crm', [])

static_checks['heartbeat_crm'] = [
{'id': 'e6b1e0de-90c3-4b04-897d-74599e414e51', 'value': ('heartbeat_crm', None, {'max_age': 60}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['heartbeat_crm']


static_checks.setdefault('heartbeat_crm_resources', [])

static_checks['heartbeat_crm_resources'] = [
{'id': '449f6f79-5a31-4f57-8f93-49db7ae09672', 'value': ('heartbeat_crm_resources', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['heartbeat_crm_resources']


static_checks.setdefault('heartbeat_rscstatus', [])

static_checks['heartbeat_rscstatus'] = [
{'id': 'de661b73-4228-4473-a1b9-971f70e3ba4d', 'value': ('heartbeat_rscstatus', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['heartbeat_rscstatus']


static_checks.setdefault('hivemanager_devices', [])

static_checks['hivemanager_devices'] = [
{'id': '57ea5f4c-3662-4055-ac0f-6a04ce58de83', 'value': ('hivemanager_devices', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['hivemanager_devices']


static_checks.setdefault('hivemanager_ng_devices', [])

static_checks['hivemanager_ng_devices'] = [
{'id': '9920924a-1fd1-464a-8525-98468f2f34ca', 'value': ('hivemanager_ng_devices', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['hivemanager_ng_devices']


static_checks.setdefault('hostsystem_sensors', [])

static_checks['hostsystem_sensors'] = [
{'id': 'f3c00e2d-8051-4684-b844-963914a988f7', 'value': ('esx_vsphere_sensors', None, {'rules': []}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['hostsystem_sensors']


static_checks.setdefault('hp_hh3c_ext_states', [])

static_checks['hp_hh3c_ext_states'] = [
{'id': '684f2414-02ef-47bb-b8b8-2c6b6f3e25b9', 'value': ('hp_hh3c_ext_states', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['hp_hh3c_ext_states']


static_checks.setdefault('hp_msa_psu_voltage', [])

static_checks['hp_msa_psu_voltage'] = [
{'id': 'ef0de888-c737-4036-87b3-1b6d364d39f9', 'value': ('hp_msa_psu_sensor', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['hp_msa_psu_voltage']


static_checks.setdefault('hpux_multipath', [])

static_checks['hpux_multipath'] = [
{'id': '0cf504ed-3f9e-45f7-88ad-8101f739fbdc', 'value': ('hpux_multipath', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['hpux_multipath']


static_checks.setdefault('hr_ps', [])

static_checks['hr_ps'] = [
{'id': 'd894df0b-cb01-427c-809c-edfdce7bb7d7', 'value': ('hr_ps', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['hr_ps']


static_checks.setdefault('huawei_osn_laser', [])

static_checks['huawei_osn_laser'] = [
{'id': '61dc9e69-caff-41c4-aacd-b662706f63a1', 'value': ('huawei_osn_laser', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['huawei_osn_laser']


static_checks.setdefault('humidity', [])

static_checks['humidity'] = [
{'id': 'dee3c0c8-03a5-4499-b71d-c616209b67fc', 'value': ('akcp_exp_humidity', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['humidity']


static_checks.setdefault('hw_errors', [])

static_checks['hw_errors'] = [
{'id': 'bb9ae266-ee5d-40df-ab7b-c6eb9a6ec5de', 'value': ('nvidia_errors', None, None), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['hw_errors']


static_checks.setdefault('hw_fans', [])

static_checks['hw_fans'] = [
{'id': '046742f1-c7df-4411-be62-7c27212d9ba7', 'value': ('bintec_sensors_fan', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['hw_fans']


static_checks.setdefault('hw_fans_perc', [])

static_checks['hw_fans_perc'] = [
{'id': '5dd55a8a-a9ee-40f4-9f36-6aad06d68b70', 'value': ('blade_bx_powerfan', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['hw_fans_perc']


static_checks.setdefault('hw_psu', [])

static_checks['hw_psu'] = [
{'id': '582e01f4-745a-4269-ac21-bd8f44b94318', 'value': ('netapp_ontap_environment', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['hw_psu']


static_checks.setdefault('hyperv_vms', [])

static_checks['hyperv_vms'] = [
{'id': '5ec1d4be-c601-46c2-81c2-10d2485b814d', 'value': ('hyperv_vms', 'example', {'vm_target_state': ('map', {})}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['hyperv_vms']


static_checks.setdefault('ibm_mq_channels', [])

static_checks['ibm_mq_channels'] = [
{'id': '74403776-9b7a-491b-8a6f-41a99756752e', 'value': ('ibm_mq_channels', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['ibm_mq_channels']


static_checks.setdefault('ibm_mq_managers', [])

static_checks['ibm_mq_managers'] = [
{'id': '9351ce59-e7c9-4690-8d94-e8936a4b3c98', 'value': ('ibm_mq_managers', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['ibm_mq_managers']


static_checks.setdefault('ibm_mq_plugin', [])

static_checks['ibm_mq_plugin'] = [
{'id': '7c5cdcdb-0c24-405a-8afd-6496a1127fae', 'value': ('ibm_mq_plugin', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['ibm_mq_plugin']


static_checks.setdefault('ibm_mq_queues', [])

static_checks['ibm_mq_queues'] = [
{'id': 'e2db6c62-e34d-4764-988c-74bc03b0ad9b', 'value': ('ibm_mq_queues', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['ibm_mq_queues']


static_checks.setdefault('ibm_svc_enclosure', [])

static_checks['ibm_svc_enclosure'] = [
{'id': '80eccdce-6e36-4fc0-8c80-98f99b01452d', 'value': ('ibm_svc_enclosure', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['ibm_svc_enclosure']


static_checks.setdefault('ibm_svc_host', [])

static_checks['ibm_svc_host'] = [
{'id': '4611f3cd-1252-4f31-af81-500bd1d259da', 'value': ('ibm_svc_host', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['ibm_svc_host']


static_checks.setdefault('ibm_svc_mdisk', [])

static_checks['ibm_svc_mdisk'] = [
{'id': 'f33c6a8d-8475-4f29-ac9c-aecd2f4e5bdc', 'value': ('ibm_svc_mdisk', 'example', {'online_state': 0, 'degraded_state': 1, 'offline_state': 2, 'excluded_state': 2, 'managed_mode': 0, 'array_mode': 0, 'image_mode': 0, 'unmanaged_mode': 1}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['ibm_svc_mdisk']


static_checks.setdefault('ibm_svc_mdiskgrp', [])

static_checks['ibm_svc_mdiskgrp'] = [
{'id': '4104525e-11d8-46df-91ca-73b2d429e5a1', 'value': ('ibm_svc_mdiskgrp', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['ibm_svc_mdiskgrp']


static_checks.setdefault('ibm_svc_total_latency', [])

static_checks['ibm_svc_total_latency'] = [
{'id': 'a91530c3-047f-4ebb-97db-4e0920ad97fb', 'value': ('ibm_svc_systemstats_disk_latency', 'Drives', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['ibm_svc_total_latency']


static_checks.setdefault('ibmsvc_licenses', [])

static_checks['ibmsvc_licenses'] = [
{'id': '905c27cb-e461-4c43-9910-417942080285', 'value': ('ibm_svc_license', 'example', {'levels': ('crit_on_all', None)}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['ibmsvc_licenses']


static_checks.setdefault('iis_app_pool_state', [])

static_checks['iis_app_pool_state'] = [
{'id': 'c4053479-269c-40cc-80d3-df500719b809', 'value': ('iis_app_pool_state', '', {'state_mapping': {'Uninitialized': 2, 'Initialized': 1, 'Running': 0, 'Disabling': 2, 'Disabled': 2, 'ShutdownPending': 2, 'DeletePending': 2}}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['iis_app_pool_state']


static_checks.setdefault('informix_dbspaces', [])

static_checks['informix_dbspaces'] = [
{'id': 'f265961e-fd40-4425-9b2e-65b801a05c82', 'value': ('informix_dbspaces', 'example', {'levels': ('no_levels', None), 'levels_perc': ('fixed', (80.0, 85.0))}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['informix_dbspaces']


static_checks.setdefault('informix_locks', [])

static_checks['informix_locks'] = [
{'id': 'd36f3030-1d4d-4078-b3a7-0bd7eab2e0bc', 'value': ('informix_locks', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['informix_locks']


static_checks.setdefault('informix_logusage', [])

static_checks['informix_logusage'] = [
{'id': 'a4663030-bdb6-405e-99cd-9abfc9229d39', 'value': ('informix_logusage', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['informix_logusage']


static_checks.setdefault('informix_sessions', [])

static_checks['informix_sessions'] = [
{'id': '3e85e88e-ebdb-4af0-aa87-18e9d97ec034', 'value': ('informix_sessions', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['informix_sessions']


static_checks.setdefault('informix_tabextents', [])

static_checks['informix_tabextents'] = [
{'id': 'e18612a5-f31b-4ef0-a2b0-4f97d140c2a3', 'value': ('informix_tabextents', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['informix_tabextents']


static_checks.setdefault('innovaphone_mem', [])

static_checks['innovaphone_mem'] = [
{'id': '1dc8dd02-7fbb-4b54-a7be-ccacbbfaa5f2', 'value': ('innovaphone_mem', None, {'levels': None}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['innovaphone_mem']


static_checks.setdefault('inotify', [])

static_checks['inotify'] = [
{'id': '3d98fa97-eeaf-405e-bebc-b5052fc6e4a6', 'value': ('inotify', '', {'age_last_operation': []}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['inotify']


static_checks.setdefault('interfaces', [])

static_checks['interfaces'] = [
{'id': '5e8c7a16-cb8a-43c1-b714-dae4fbae81cf', 'value': ('aws_ec2_network_io', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['interfaces']


static_checks.setdefault('ipmi', [])

static_checks['ipmi'] = [
{'id': 'fabe0efe-214a-4ab4-a9ef-8b330fe93df8', 'value': ('ipmi', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['ipmi']


static_checks.setdefault('ipsecvpn', [])

static_checks['ipsecvpn'] = [
{'id': '7068135f-702a-469a-bd2e-897e019f73b2', 'value': ('fortigate_ipsecvpn', None, {'levels': (1, 2), 'tunnels_ignore_levels': []}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['ipsecvpn']


static_checks.setdefault('jenkins_jobs', [])

static_checks['jenkins_jobs'] = [
{'id': '6bd4046c-6f29-4a26-924c-6008bc299381', 'value': ('jenkins_jobs', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['jenkins_jobs']


static_checks.setdefault('jenkins_nodes', [])

static_checks['jenkins_nodes'] = [
{'id': '6221f223-56dd-4c1a-875a-6eccf39a947d', 'value': ('jenkins_nodes', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['jenkins_nodes']


static_checks.setdefault('jenkins_queue', [])

static_checks['jenkins_queue'] = [
{'id': '4ad43e26-b332-4b14-a260-8f48fcf372b8', 'value': ('jenkins_queue', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['jenkins_queue']


static_checks.setdefault('jenkins_system_metrics', [])

static_checks['jenkins_system_metrics'] = [
{'id': '4b1e47d4-b129-4229-a602-1af28d4968cc', 'value': ('jenkins_system_metrics', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['jenkins_system_metrics']


static_checks.setdefault('jira_custom_svc', [])

static_checks['jira_custom_svc'] = [
{'id': 'e8b8dfa7-3893-4867-be04-d17f5c7815e4', 'value': ('jira_custom_svc', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['jira_custom_svc']


static_checks.setdefault('jira_workflow', [])

static_checks['jira_workflow'] = [
{'id': 'c99dce96-6151-47c3-9f82-79c741085e9a', 'value': ('jira_workflow', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['jira_workflow']


static_checks.setdefault('job', [])

static_checks['job'] = [
{'id': '11accd46-914d-40c6-9748-64eb55e18525', 'value': ('job', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['job']


static_checks.setdefault('juniper_alarms', [])

static_checks['juniper_alarms'] = [
{'id': 'bbf04521-c789-4dc4-91c2-53200c624117', 'value': ('juniper_alarm', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['juniper_alarms']


static_checks.setdefault('juniper_cpu_util', [])

static_checks['juniper_cpu_util'] = [
{'id': 'ed993ef9-7371-45b4-b43d-6287614a14a7', 'value': ('juniper_cpu_util', 'example', {'levels': (80.0, 90.0)}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['juniper_cpu_util']


static_checks.setdefault('juniper_mem', [])

static_checks['juniper_mem'] = [
{'id': 'beed7bfd-981c-4407-b912-ecc4d8c64938', 'value': ('juniper_screenos_mem', None, {'levels': ('perc_used', (80.0, 90.0))}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['juniper_mem']


static_checks.setdefault('juniper_mem_modules', [])

static_checks['juniper_mem_modules'] = [
{'id': 'daebf9a8-86ae-4f7d-988e-8a8cc8d73330', 'value': ('juniper_mem', 'example', {'levels': None}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['juniper_mem_modules']


static_checks.setdefault('jvm_gc', [])

static_checks['jvm_gc'] = [
{'id': 'e3895226-be62-4178-8e65-f5d22d1d04ea', 'value': ('jolokia_jvm_garbagecollectors', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['jvm_gc']


static_checks.setdefault('jvm_memory', [])

static_checks['jvm_memory'] = [
{'id': 'f16f1073-7b9f-450c-9b2a-10af5641e6f2', 'value': ('appdynamics_memory', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['jvm_memory']


static_checks.setdefault('jvm_memory_pools', [])

static_checks['jvm_memory_pools'] = [
{'id': '23efd4a9-b117-4aa1-be94-0a82e4cae54c', 'value': ('jolokia_jvm_memory_pools', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['jvm_memory_pools']


static_checks.setdefault('jvm_queue', [])

static_checks['jvm_queue'] = [
{'id': '31ac324e-38bf-4dde-ac0a-53e80b554517', 'value': ('jolokia_metrics_bea_queue', 'example', {'levels': None}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['jvm_queue']


static_checks.setdefault('jvm_requests', [])

static_checks['jvm_requests'] = [
{'id': '0dc77a4b-3d31-4654-b7d8-ba115c103739', 'value': ('jolokia_metrics_serv_req', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['jvm_requests']


static_checks.setdefault('jvm_sessions', [])

static_checks['jvm_sessions'] = [
{'id': '7bae96ea-d2a9-406d-ad12-c7da11bc0e38', 'value': ('appdynamics_sessions', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['jvm_sessions']


static_checks.setdefault('jvm_threading', [])

static_checks['jvm_threading'] = [
{'id': 'a97d9298-a1ad-4ce4-9ed7-af00e26f868f', 'value': ('jolokia_jvm_threading', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['jvm_threading']


static_checks.setdefault('jvm_tp', [])

static_checks['jvm_tp'] = [
{'id': 'fdc5f61b-f64a-418f-ab85-e161ae7dc126', 'value': ('jolokia_jvm_threading_pool', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['jvm_tp']


static_checks.setdefault('jvm_uptime', [])

static_checks['jvm_uptime'] = [
{'id': '234a005b-ee29-40d7-9553-4b21a308ccd5', 'value': ('jolokia_jvm_runtime', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['jvm_uptime']


static_checks.setdefault('kaspersky_av_client', [])

static_checks['kaspersky_av_client'] = [
{'id': '3f162154-69f4-428d-83f6-bf4ae1f95eb2', 'value': ('kaspersky_av_client', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['kaspersky_av_client']


static_checks.setdefault('keepalived', [])

static_checks['keepalived'] = [
{'id': '75fd9775-06c6-4ce6-a170-e0333c1007d2', 'value': ('keepalived', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['keepalived']


static_checks.setdefault('kernel_performance', [])

static_checks['kernel_performance'] = [
{'id': '4dfed830-cbc4-4af5-a04f-d5aebcf49385', 'value': ('kernel_performance', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['kernel_performance']


static_checks.setdefault('kube_collector_info', [])

static_checks['kube_collector_info'] = [
{'id': 'f4901322-82f2-4db0-8fd5-931d7c862472', 'value': ('kube_collector_info', None, {'machine_metrics': 2}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['kube_collector_info']


static_checks.setdefault('kube_cpu', [])

static_checks['kube_cpu'] = [
{'id': '419b3266-b3e9-4dd0-880a-780df8f096da', 'value': ('kube_cpu', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['kube_cpu']


static_checks.setdefault('kube_cronjob_status', [])

static_checks['kube_cronjob_status'] = [
{'id': 'e361bbb2-64e4-4772-b2bc-e6bda9bef65d', 'value': ('kube_cronjob_status', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['kube_cronjob_status']


static_checks.setdefault('kube_deployment_conditions', [])

static_checks['kube_deployment_conditions'] = [
{'id': 'ca5eba92-94d4-4809-bbc0-f537a4e1add4', 'value': ('kube_deployment_conditions', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['kube_deployment_conditions']


static_checks.setdefault('kube_memory', [])

static_checks['kube_memory'] = [
{'id': 'e6b81ecb-562e-4519-93d2-4fefc56bc1f5', 'value': ('kube_memory', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['kube_memory']


static_checks.setdefault('kube_node_conditions', [])

static_checks['kube_node_conditions'] = [
{'id': '2ca32477-ae1b-499e-8082-e90618f59196', 'value': ('kube_node_conditions', None, {'conditions': []}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['kube_node_conditions']


static_checks.setdefault('kube_node_container_count', [])

static_checks['kube_node_container_count'] = [
{'id': '979f78e5-b878-4796-b8f0-841b29ce0145', 'value': ('kube_node_container_count', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['kube_node_container_count']


static_checks.setdefault('kube_node_count', [])

static_checks['kube_node_count'] = [
{'id': 'a251007c-d512-48f2-897b-7ac7820d0843', 'value': ('kube_node_count', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['kube_node_count']


static_checks.setdefault('kube_pod_conditions', [])

static_checks['kube_pod_conditions'] = [
{'id': '7bff2051-f8d4-4937-8994-91d89d9cc6f2', 'value': ('kube_pod_conditions', None, {'hasnetwork': 'no_levels'}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['kube_pod_conditions']


static_checks.setdefault('kube_pod_containers', [])

static_checks['kube_pod_containers'] = [
{'id': 'd8ad499e-25ab-4d3e-9626-8ae382be3fde', 'value': ('kube_pod_containers', 'example', {'failed_state': 2}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['kube_pod_containers']


static_checks.setdefault('kube_pod_resources', [])

static_checks['kube_pod_resources'] = [
{'id': 'a6f9cfbf-bd54-4478-b335-e6452047d4c8', 'value': ('kube_pod_resources', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['kube_pod_resources']


static_checks.setdefault('kube_pod_restarts', [])

static_checks['kube_pod_restarts'] = [
{'id': '3f511001-18cd-4211-ac94-ffd2fa0e7032', 'value': ('kube_pod_restarts', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['kube_pod_restarts']


static_checks.setdefault('kube_pod_status', [])

static_checks['kube_pod_status'] = [
{'id': '6187d915-8c0f-4e3c-97ce-708537530e01', 'value': ('kube_pod_status', None, {'groups': []}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['kube_pod_status']


static_checks.setdefault('kube_pvc', [])

static_checks['kube_pvc'] = [
{'id': '24665661-55eb-4c58-a975-5829aac60449', 'value': ('kube_pvc', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['kube_pvc']


static_checks.setdefault('kube_replicas', [])

static_checks['kube_replicas'] = [
{'id': '8d23fb4f-237f-4704-a801-4ab4f60198c2', 'value': ('kube_replicas', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['kube_replicas']


static_checks.setdefault('kube_resource_quota_cpu', [])

static_checks['kube_resource_quota_cpu'] = [
{'id': 'dafae79e-5477-4b48-83f5-44dc37935c99', 'value': ('kube_resource_quota_cpu', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['kube_resource_quota_cpu']


static_checks.setdefault('kube_resource_quota_memory', [])

static_checks['kube_resource_quota_memory'] = [
{'id': 'f6792ad8-f01f-4995-a657-63fdc1a9fa00', 'value': ('kube_resource_quota_memory', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['kube_resource_quota_memory']


static_checks.setdefault('lamp_operation_time', [])

static_checks['lamp_operation_time'] = [
{'id': 'e90ddbec-4b02-49d4-8d9a-5b88abdbf7b5', 'value': ('epson_beamer_lamp', None, {'levels': (3600000, 5400000)}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['lamp_operation_time']


static_checks.setdefault('liebert_cooling', [])

static_checks['liebert_cooling'] = [
{'id': '89b6d357-a082-415f-9ddd-5d641c62d4fd', 'value': ('liebert_cooling', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['liebert_cooling']


static_checks.setdefault('liebert_cooling_position', [])

static_checks['liebert_cooling_position'] = [
{'id': '4ca9f6db-022b-4334-8383-892cf5c204a5', 'value': ('liebert_cooling_position', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['liebert_cooling_position']


static_checks.setdefault('livestatus_status', [])

static_checks['livestatus_status'] = [
{'id': '6f1afccb-42cb-4d58-97e0-cce22734d8c0', 'value': ('livestatus_status', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['livestatus_status']


static_checks.setdefault('lnx_quota', [])

static_checks['lnx_quota'] = [
{'id': '7a53176c-4768-4890-8d0f-7cba72eaf7aa', 'value': ('lnx_quota', 'example', {'user': True, 'group': False}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['lnx_quota']


static_checks.setdefault('logins', [])

static_checks['logins'] = [
{'id': 'fbd2a72f-512b-4eac-8e59-09472cd64aed', 'value': ('logins', None, {'levels': None}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['logins']


static_checks.setdefault('logwatch_ec', [])

static_checks['logwatch_ec'] = [
{'id': '510abdd5-a78f-4b4e-b524-87b464b88221', 'value': ('logwatch_ec', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['logwatch_ec']


static_checks.setdefault('lsnat', [])

static_checks['lsnat'] = [
{'id': '5366b82c-47f3-4501-937a-67b0a0811182', 'value': ('enterasys_lsnat', None, {'current_bindings': None}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['lsnat']


static_checks.setdefault('lvm_lvs_pools', [])

static_checks['lvm_lvs_pools'] = [
{'id': '9d38fe24-ac63-4934-a9c7-23ed6e59c48a', 'value': ('lvm_lvs', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['lvm_lvs_pools']


static_checks.setdefault('mail_latency', [])

static_checks['mail_latency'] = [
{'id': 'a725113f-603a-4493-b921-cefd75654044', 'value': ('barracuda_mail_latency', None, {'levels': None}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mail_latency']


static_checks.setdefault('mail_queue_length', [])

static_checks['mail_queue_length'] = [
{'id': '6c72b69d-65dc-4f7f-807d-c70f83fec0e2', 'value': ('postfix_mailq', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mail_queue_length']


static_checks.setdefault('mail_queue_length_single', [])

static_checks['mail_queue_length_single'] = [
{'id': '61a77c5f-6142-43a6-8e9a-b74fc2649625', 'value': ('barracuda_mailqueues', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mail_queue_length_single']


static_checks.setdefault('mbg_lantime_state', [])

static_checks['mbg_lantime_state'] = [
{'id': '5be16bd4-9da1-4284-ae9a-eb8d2c566b6e', 'value': ('mbg_lantime_ng_state', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mbg_lantime_state']


static_checks.setdefault('mcafee_av_client', [])

static_checks['mcafee_av_client'] = [
{'id': 'a7a6a36a-a2d6-4d96-9013-5bb21f25d4a9', 'value': ('mcafee_av_client', None, {'signature_age': (86400, 604800)}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mcafee_av_client']


static_checks.setdefault('mcafee_emailgateway_bridge', [])

static_checks['mcafee_emailgateway_bridge'] = [
{'id': 'f601130d-f2e3-4f00-8fb9-0ff2e6a48288', 'value': ('mcafee_emailgateway_bridge', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mcafee_emailgateway_bridge']


static_checks.setdefault('mcafee_web_gateway', [])

static_checks['mcafee_web_gateway'] = [
{'id': 'f013e3b8-96ba-4e1b-9ada-a5874543a6d6', 'value': ('mcafee_webgateway', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mcafee_web_gateway']


static_checks.setdefault('mcafee_web_gateway_misc', [])

static_checks['mcafee_web_gateway_misc'] = [
{'id': 'feba326a-2f34-43c4-8d86-4fa6317fc987', 'value': ('mcafee_webgateway_http_client_requests', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mcafee_web_gateway_misc']


static_checks.setdefault('mem_pages', [])

static_checks['mem_pages'] = [
{'id': '1b21ddf5-3475-4f4a-898e-63ae631e8f10', 'value': ('winperf_mem', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mem_pages']


static_checks.setdefault('memory', [])

static_checks['memory'] = [
{'id': '0b58ab01-8135-4ca2-9052-529f5dd1ae32', 'value': ('fortigate_memory', None, {'levels': (150.0, 200.0)}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['memory']


static_checks.setdefault('memory_arbor', [])

static_checks['memory_arbor'] = [
{'id': '92d92222-5329-4068-84c2-9f2e841104a4', 'value': ('arbor_memory', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['memory_arbor']


static_checks.setdefault('memory_available', [])

static_checks['memory_available'] = [
{'id': 'd87d8994-0505-4b03-b589-59434ea9decc', 'value': ('azure_vm_memory', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['memory_available']


static_checks.setdefault('memory_linux', [])

static_checks['memory_linux'] = [
{'id': '0880c8c4-b719-48b8-8497-48f7bde93f28', 'value': ('mem_linux', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['memory_linux']


static_checks.setdefault('memory_multiitem', [])

static_checks['memory_multiitem'] = [
{'id': '4b80a9d8-3c06-470f-86b1-a2a054cbbf8b', 'value': ('arris_cmts_mem', 'example', {'levels': None}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['memory_multiitem']


static_checks.setdefault('memory_pagefile_win', [])

static_checks['memory_pagefile_win'] = [
{'id': '7f2d97a5-37c3-491a-b288-777490845d6e', 'value': ('mem_win', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['memory_pagefile_win']


static_checks.setdefault('memory_percentage_used', [])

static_checks['memory_percentage_used'] = [
{'id': 'd7974994-45f7-4f88-aa71-424d39041c91', 'value': ('memory_utilization', None, {'levels': ('fixed', (70.0, 80.0))}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['memory_percentage_used']


static_checks.setdefault('memory_percentage_used_multiitem', [])

static_checks['memory_percentage_used_multiitem'] = [
{'id': '004d7389-1275-43a1-a76f-fa130606b49d', 'value': ('huawei_switch_mem', 'example', {'levels': (80.0, 90.0)}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['memory_percentage_used_multiitem']


static_checks.setdefault('memory_relative', [])

static_checks['memory_relative'] = [
{'id': '4ffa8427-3bd2-473d-a884-bdaf3d2e4857', 'value': ('brocade_sys_mem', None, {'levels': None}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['memory_relative']


static_checks.setdefault('memory_simple', [])

static_checks['memory_simple'] = [
{'id': 'f4be24dd-374d-418d-9fd9-d50cd936c113', 'value': ('f5_bigip_mem', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['memory_simple']


static_checks.setdefault('memory_simple_single', [])

static_checks['memory_simple_single'] = [
{'id': '9c6e2d05-6cac-451e-990f-ec49281b2cfc', 'value': ('checkpoint_memory', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['memory_simple_single']


static_checks.setdefault('memory_utilization', [])

static_checks['memory_utilization'] = [
{'id': 'b42a8c4e-76e5-46bd-a5c4-a9092addc99a', 'value': ('azure_mysql_memory', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['memory_utilization']


static_checks.setdefault('memory_utilization_multiitem', [])

static_checks['memory_utilization_multiitem'] = [
{'id': '0525732c-7ec1-42bd-86f6-beafa8c8e6b9', 'value': ('ucs_c_rack_server_util_mem', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['memory_utilization_multiitem']


static_checks.setdefault('mobileiron_compliance', [])

static_checks['mobileiron_compliance'] = [
{'id': '65cc424d-ed30-4ef4-8954-9a0674a2668f', 'value': ('mobileiron_compliance', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mobileiron_compliance']


static_checks.setdefault('mobileiron_statistics', [])

static_checks['mobileiron_statistics'] = [
{'id': '03a3851e-3e21-42e5-bba6-0c05a0f1248e', 'value': ('mobileiron_statistics', None, {'non_compliant_summary_levels': (10.0, 20.0)}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mobileiron_statistics']


static_checks.setdefault('mobileiron_versions', [])

static_checks['mobileiron_versions'] = [
{'id': '527da807-2496-4d12-843b-f06da730111f', 'value': ('mobileiron_versions', None, {'ios_version_regexp': '', 'android_version_regexp': '', 'os_version_other': 0, 'patchlevel_unparsable': 0, 'patchlevel_age': 7776000, 'os_build_unparsable': 0, 'os_age': 7776000}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mobileiron_versions']


static_checks.setdefault('mongodb_asserts', [])

static_checks['mongodb_asserts'] = [
{'id': 'c3c962d6-d1c3-4dd5-ba29-a63774821e69', 'value': ('mongodb_asserts', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mongodb_asserts']


static_checks.setdefault('mongodb_cluster', [])

static_checks['mongodb_cluster'] = [
{'id': '830ad285-c1e1-4148-a428-c3c033745bc5', 'value': ('mongodb_cluster', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mongodb_cluster']


static_checks.setdefault('mongodb_collections', [])

static_checks['mongodb_collections'] = [
{'id': 'ff79b488-969f-4de5-b60b-f1cd9f4ade08', 'value': ('mongodb_collections', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mongodb_collections']


static_checks.setdefault('mongodb_flushing', [])

static_checks['mongodb_flushing'] = [
{'id': '0af9b0d3-9e00-4a18-85cf-30ae64221e5d', 'value': ('mongodb_flushing', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mongodb_flushing']


static_checks.setdefault('mongodb_locks', [])

static_checks['mongodb_locks'] = [
{'id': 'c113aee5-1379-47e6-9524-d3e1fd045855', 'value': ('mongodb_locks', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mongodb_locks']


static_checks.setdefault('mongodb_mem', [])

static_checks['mongodb_mem'] = [
{'id': 'c7313ca3-dd6d-4ae9-a6e5-9e047be7166d', 'value': ('mongodb_mem', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mongodb_mem']


static_checks.setdefault('mongodb_replica_set', [])

static_checks['mongodb_replica_set'] = [
{'id': '7fc45c99-c7ee-48f9-a4ab-c709db777653', 'value': ('mongodb_replica_set', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mongodb_replica_set']


static_checks.setdefault('motion', [])

static_checks['motion'] = [
{'id': '9962c39e-a757-4297-9baa-7a1aa3324eb7', 'value': ('kentix_motion', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['motion']


static_checks.setdefault('mq_queues', [])

static_checks['mq_queues'] = [
{'id': 'c54964a2-f293-430e-8542-86ddff8ded9c', 'value': ('mq_queues', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mq_queues']


static_checks.setdefault('msexch_copyqueue', [])

static_checks['msexch_copyqueue'] = [
{'id': 'cca3a1cc-81d8-4126-b566-035b4fefe8b5', 'value': ('msexch_dag_copyqueue', '', {'levels': None}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['msexch_copyqueue']


static_checks.setdefault('msoffice_licenses', [])

static_checks['msoffice_licenses'] = [
{'id': 'eddaa1fc-ddab-4f85-afcf-ec3ec746ecdd', 'value': ('msoffice_licenses', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['msoffice_licenses']


static_checks.setdefault('msoffice_serviceplans', [])

static_checks['msoffice_serviceplans'] = [
{'id': '431e1501-91b3-4e26-9b3a-f10c90c47486', 'value': ('msoffice_serviceplans', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['msoffice_serviceplans']


static_checks.setdefault('mssql_backup', [])

static_checks['mssql_backup'] = [
{'id': '4c7fbf86-32fd-434e-993a-edc30d064017', 'value': ('mssql_backup', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mssql_backup']


static_checks.setdefault('mssql_backup_per_type', [])

static_checks['mssql_backup_per_type'] = [
{'id': 'b70d42a8-d223-44b8-a88c-285b8aaf16f4', 'value': ('mssql_backup_per_type', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mssql_backup_per_type']


static_checks.setdefault('mssql_connections', [])

static_checks['mssql_connections'] = [
{'id': '56275a6e-9444-4bba-9acb-2b67dd8932b6', 'value': ('mssql_connections', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mssql_connections']


static_checks.setdefault('mssql_counters_locks', [])

static_checks['mssql_counters_locks'] = [
{'id': '7091e9d6-d9a4-4e0b-91c4-511c591b27c7', 'value': ('mssql_counters_locks', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mssql_counters_locks']


static_checks.setdefault('mssql_counters_page_life_expectancy', [])

static_checks['mssql_counters_page_life_expectancy'] = [
{'id': '1b5369b1-af9f-4158-9554-19d0d47961ba', 'value': ('mssql_counters_page_life_expectancy', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mssql_counters_page_life_expectancy']


static_checks.setdefault('mssql_databases', [])

static_checks['mssql_databases'] = [
{'id': '8a2e2fd7-290e-4316-a898-96a74dd3a7d6', 'value': ('mssql_databases', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mssql_databases']


static_checks.setdefault('mssql_datafiles', [])

static_checks['mssql_datafiles'] = [
{'id': '4eea95fb-66a9-4e7d-bb37-158d79dcfe94', 'value': ('mssql_datafiles', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mssql_datafiles']


static_checks.setdefault('mssql_file_sizes', [])

static_checks['mssql_file_sizes'] = [
{'id': 'fa8a0692-3130-4888-a131-79df93e0863d', 'value': ('mssql_counters_file_sizes', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mssql_file_sizes']


static_checks.setdefault('mssql_instance', [])

static_checks['mssql_instance'] = [
{'id': '4e4d24e9-008f-4945-ad3e-906c7b5ecd42', 'value': ('mssql_instance', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mssql_instance']


static_checks.setdefault('mssql_instance_blocked_sessions', [])

static_checks['mssql_instance_blocked_sessions'] = [
{'id': '21eb3fbe-24d0-4b87-95e9-5412e1568754', 'value': ('mssql_blocked_sessions', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mssql_instance_blocked_sessions']


static_checks.setdefault('mssql_jobs', [])

static_checks['mssql_jobs'] = [
{'id': '50dfd92a-3bfc-484a-a343-ea826aa67b5b', 'value': ('mssql_jobs', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mssql_jobs']


static_checks.setdefault('mssql_mirroring', [])

static_checks['mssql_mirroring'] = [
{'id': 'ab057b2f-8a7c-4bd5-960b-dbc58a007e37', 'value': ('mssql_mirroring', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mssql_mirroring']


static_checks.setdefault('mssql_page_activity', [])

static_checks['mssql_page_activity'] = [
{'id': 'b9207941-084e-4877-96ed-33463eaa2705', 'value': ('mssql_counters_pageactivity', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mssql_page_activity']


static_checks.setdefault('mssql_stats', [])

static_checks['mssql_stats'] = [
{'id': '6212e2eb-5165-4cd3-aa55-2e808cd2dfae', 'value': ('mssql_counters_locks_per_batch', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mssql_stats']


static_checks.setdefault('mssql_tablespaces', [])

static_checks['mssql_tablespaces'] = [
{'id': '32687cf9-651b-4035-b1dd-9f7fe60a3b5f', 'value': ('mssql_tablespaces', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mssql_tablespaces']


static_checks.setdefault('mssql_transactionlogs', [])

static_checks['mssql_transactionlogs'] = [
{'id': 'd1724f49-ea1a-428d-b09b-8bebc6ca302d', 'value': ('mssql_transactionlogs', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mssql_transactionlogs']


static_checks.setdefault('msx_database', [])

static_checks['msx_database'] = [
{'id': '19ebb3f8-d98e-4e72-9146-f2fb20ef3baf', 'value': ('msexch_database', 'example', {'read_attached_latency_s': ('fixed', (0.2, 0.25)), 'read_recovery_latency_s': ('fixed', (0.15, 0.2)), 'write_latency_s': ('fixed', (0.04, 0.05)), 'log_latency_s': ('fixed', (0.005, 0.01))}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['msx_database']


static_checks.setdefault('msx_info_store', [])

static_checks['msx_info_store'] = [
{'id': 'f9e6bfe5-b941-4256-9b28-b3e964051218', 'value': ('msexch_isclienttype', 'example', {'store_latency_s': ('fixed', (0.04, 0.05)), 'clienttype_latency_s': ('fixed', (0.04, 0.05)), 'clienttype_requests': ('fixed', (60, 70))}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['msx_info_store']


static_checks.setdefault('msx_queues', [])

static_checks['msx_queues'] = [
{'id': 'c7611fa5-49e5-4b67-8892-e2b049b7b9f4', 'value': ('winperf_msx_queues', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['msx_queues']


static_checks.setdefault('msx_rpcclientaccess', [])

static_checks['msx_rpcclientaccess'] = [
{'id': 'd8218ac6-8c84-4580-ade6-79cc30e1b334', 'value': ('msexch_rpcclientaccess', None, {'latency_s': ('fixed', (0.2, 0.25)), 'requests': ('fixed', (30, 40))}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['msx_rpcclientaccess']


static_checks.setdefault('mtr', [])

static_checks['mtr'] = [
{'id': '4f595c9b-cbdf-4fd1-bd9d-02581a4e2f00', 'value': ('mtr', 'example', {'rta': (150, 250), 'rtstddev': (150, 250), 'pl': (10, 25)}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mtr']


static_checks.setdefault('multipath', [])

static_checks['multipath'] = [
{'id': '6e04e99b-8a11-4050-9f10-b0fc139fedf8', 'value': ('multipath', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['multipath']


static_checks.setdefault('multipath_count', [])

static_checks['multipath_count'] = [
{'id': 'df743eea-17b3-4620-844f-c792a86d2ee7', 'value': ('esx_vsphere_hostsystem_multipath', 'example', {'levels_map': None}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['multipath_count']


static_checks.setdefault('mysql_connections', [])

static_checks['mysql_connections'] = [
{'id': 'cd24b8c5-7169-49f9-9d56-9f940047fb44', 'value': ('mysql_connections', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mysql_connections']


static_checks.setdefault('mysql_db_size', [])

static_checks['mysql_db_size'] = [
{'id': 'fcedd71f-a997-4d72-af32-e362a1e709bc', 'value': ('mysql_capacity', '', {'levels': None}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mysql_db_size']


static_checks.setdefault('mysql_innodb_io', [])

static_checks['mysql_innodb_io'] = [
{'id': '46e104e6-b4cb-4aae-9ada-45dc7e9cb29d', 'value': ('mysql_innodb_io', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mysql_innodb_io']


static_checks.setdefault('mysql_sessions', [])

static_checks['mysql_sessions'] = [
{'id': '12b3477b-f492-4535-a5b9-6d41729ee48a', 'value': ('mysql_sessions', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mysql_sessions']


static_checks.setdefault('mysql_slave', [])

static_checks['mysql_slave'] = [
{'id': '667fd150-0ac7-4619-bc2d-29a8a23dccd5', 'value': ('mysql_replica_slave', '', {'seconds_behind_master': ('fixed', (0.0, 0.0))}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['mysql_slave']


static_checks.setdefault('netapp_disks', [])

static_checks['netapp_disks'] = [
{'id': '151de387-ce0d-4c7a-ba71-46eb089e4fbc', 'value': ('ibm_svc_disks', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['netapp_disks']


static_checks.setdefault('netapp_fcportio', [])

static_checks['netapp_fcportio'] = [
{'id': 'dd095c78-3b0b-465f-9afa-7506538ccd29', 'value': ('netapp_fcpio', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['netapp_fcportio']


static_checks.setdefault('netapp_luns', [])

static_checks['netapp_luns'] = [
{'id': 'e743f839-47f1-4358-805d-1160ff9dab01', 'value': ('netapp_ontap_luns', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['netapp_luns']


static_checks.setdefault('netapp_snapshots', [])

static_checks['netapp_snapshots'] = [
{'id': '5e4f228e-3ba3-4f82-8c48-7946e27282ff', 'value': ('netapp_ontap_snapshots', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['netapp_snapshots']


static_checks.setdefault('netapp_system_time_offset', [])

static_checks['netapp_system_time_offset'] = [
{'id': '4ce046fa-492b-4871-acee-b1b796365719', 'value': ('netapp_ontap_time', 'example', {'upper_levels': ('fixed', (30.0, 60.0))}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['netapp_system_time_offset']


static_checks.setdefault('netapp_volumes', [])

static_checks['netapp_volumes'] = [
{'id': '7cea8452-5ce1-4566-9c56-d7775fb22afa', 'value': ('netapp_ontap_volumes', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['netapp_volumes']


static_checks.setdefault('netscaler_dnsrates', [])

static_checks['netscaler_dnsrates'] = [
{'id': 'ec138d66-7cce-4a31-9c0d-142862059a32', 'value': ('netscaler_dnsrates', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['netscaler_dnsrates']


static_checks.setdefault('netscaler_mem', [])

static_checks['netscaler_mem'] = [
{'id': '23d92779-4916-4256-8717-c6fe6f040373', 'value': ('netscaler_mem', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['netscaler_mem']


static_checks.setdefault('netscaler_sslcerts', [])

static_checks['netscaler_sslcerts'] = [
{'id': '5fe6ca1c-bc5f-447d-ae82-3ee945d3acb5', 'value': ('netscaler_sslcertificates', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['netscaler_sslcerts']


static_checks.setdefault('netscaler_tcp_conns', [])

static_checks['netscaler_tcp_conns'] = [
{'id': '0a71489d-bfe5-48a5-bbb0-c106f680a174', 'value': ('netscaler_tcp_conns', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['netscaler_tcp_conns']


static_checks.setdefault('netscaler_vserver', [])

static_checks['netscaler_vserver'] = [
{'id': '2a5cdb9e-adb2-4826-a6af-c1c8f08e8c01', 'value': ('netscaler_vserver', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['netscaler_vserver']


static_checks.setdefault('network_fs', [])

static_checks['network_fs'] = [
{'id': '8f1e7693-1f1f-472d-bd44-f797a4eaaa95', 'value': ('cifsmounts', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['network_fs']


static_checks.setdefault('network_io', [])

static_checks['network_io'] = [
{'id': '5972ea52-2686-4e08-ac53-62856761d457', 'value': ('azure_mysql_network', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['network_io']


static_checks.setdefault('nfsiostats', [])

static_checks['nfsiostats'] = [
{'id': '140725dc-3b7b-4a12-9780-36b643c2b2b3', 'value': ('nfsiostat', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['nfsiostats']


static_checks.setdefault('nginx_status', [])

static_checks['nginx_status'] = [
{'id': '31ea4cbd-1287-4768-9dfb-a07656dd1306', 'value': ('nginx_status', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['nginx_status']


static_checks.setdefault('nimble_latency', [])

static_checks['nimble_latency'] = [
{'id': 'd31623da-a776-4142-b573-285928442d30', 'value': ('nimble_latency', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['nimble_latency']


static_checks.setdefault('ntp_peer', [])

static_checks['ntp_peer'] = [
{'id': '60f02f0b-f340-46c7-8f4b-01a05968bae3', 'value': ('ntp', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['ntp_peer']


static_checks.setdefault('ntp_time', [])

static_checks['ntp_time'] = [
{'id': '0d6214a2-1d9b-48ec-b83b-2fd534fb6628', 'value': ('chrony', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['ntp_time']


static_checks.setdefault('nvidia_smi_en_de_coder_util', [])

static_checks['nvidia_smi_en_de_coder_util'] = [
{'id': '62ddd9ca-e629-44c5-beb2-d0e83a1dc18f', 'value': ('nvidia_smi_en_de_coder_util', 'example', {'encoder_levels': None, 'decoder_levels': None}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['nvidia_smi_en_de_coder_util']


static_checks.setdefault('nvidia_smi_gpu_util', [])

static_checks['nvidia_smi_gpu_util'] = [
{'id': '459c0e8d-fc0a-4ed1-83e2-9ff6b88c20cf', 'value': ('nvidia_smi_gpu_util', 'example', {'levels': None}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['nvidia_smi_gpu_util']


static_checks.setdefault('nvidia_smi_memory_util', [])

static_checks['nvidia_smi_memory_util'] = [
{'id': '2aaa4820-4109-44ef-b4ba-55d7666a8fdb', 'value': ('nvidia_smi_memory_util', '', {'levels_total': None, 'levels_bar1': None, 'levels_fb': None}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['nvidia_smi_memory_util']


static_checks.setdefault('nvidia_smi_power', [])

static_checks['nvidia_smi_power'] = [
{'id': 'aac16c8c-a4b2-4842-9781-aa5dbd7704fd', 'value': ('nvidia_smi_power', 'example', {'levels': None}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['nvidia_smi_power']


static_checks.setdefault('ocprot_current', [])

static_checks['ocprot_current'] = [
{'id': 'f5acabd7-454b-45e4-819d-fdb3e91cd4c3', 'value': ('raritan_pdu_ocprot', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['ocprot_current']


static_checks.setdefault('openhardwaremonitor_smart', [])

static_checks['openhardwaremonitor_smart'] = [
{'id': '62d3c1cd-1e2c-4737-b9fc-aa5866ac1aef', 'value': ('openhardwaremonitor_smart', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['openhardwaremonitor_smart']


static_checks.setdefault('oracle_crs_res', [])

static_checks['oracle_crs_res'] = [
{'id': '983343bf-6c23-4842-a220-a4cda027c1d2', 'value': ('oracle_crs_res', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['oracle_crs_res']


static_checks.setdefault('oracle_dataguard_stats', [])

static_checks['oracle_dataguard_stats'] = [
{'id': '2b7514f8-9e95-483d-a5a2-7513edef6b95', 'value': ('oracle_dataguard_stats', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['oracle_dataguard_stats']


static_checks.setdefault('oracle_instance', [])

static_checks['oracle_instance'] = [
{'id': '00785e59-90c8-4184-a4ea-14ca20607fb3', 'value': ('oracle_instance', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['oracle_instance']


static_checks.setdefault('oracle_jobs', [])

static_checks['oracle_jobs'] = [
{'id': '7ec5d86a-d6e8-4f5c-a022-3a0e4f226f03', 'value': ('oracle_jobs', 'ORCL.EXAMPLE_JOB', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['oracle_jobs']


static_checks.setdefault('oracle_locks', [])

static_checks['oracle_locks'] = [
{'id': '5fe3cb0a-4234-4a34-bf1c-9e1786e3e4cb', 'value': ('oracle_locks', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['oracle_locks']


static_checks.setdefault('oracle_logswitches', [])

static_checks['oracle_logswitches'] = [
{'id': '6c7ff48d-1a0b-41bb-9ce7-22cc8a3e6263', 'value': ('oracle_logswitches', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['oracle_logswitches']


static_checks.setdefault('oracle_longactivesessions', [])

static_checks['oracle_longactivesessions'] = [
{'id': '36d8637a-9766-41b7-ad79-5b8a988006b1', 'value': ('oracle_longactivesessions', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['oracle_longactivesessions']


static_checks.setdefault('oracle_performance', [])

static_checks['oracle_performance'] = [
{'id': '0e4057b4-380e-4cbe-9a2e-533aec3738d8', 'value': ('oracle_performance_dbtime', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['oracle_performance']


static_checks.setdefault('oracle_processes', [])

static_checks['oracle_processes'] = [
{'id': '6d2f419d-c862-4cf6-850e-45745f5f0095', 'value': ('oracle_processes', 'example', {'levels': (70.0, 90.0)}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['oracle_processes']


static_checks.setdefault('oracle_recovery_area', [])

static_checks['oracle_recovery_area'] = [
{'id': '9864ba19-4ceb-4a9b-8706-9ab0c462db6c', 'value': ('oracle_recovery_area', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['oracle_recovery_area']


static_checks.setdefault('oracle_recovery_status', [])

static_checks['oracle_recovery_status'] = [
{'id': 'a557a30a-2da0-41cb-b90c-817d3eb71004', 'value': ('oracle_recovery_status', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['oracle_recovery_status']


static_checks.setdefault('oracle_rman', [])

static_checks['oracle_rman'] = [
{'id': 'cd854597-9ff7-49a7-8fcb-73781890adcc', 'value': ('oracle_rman', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['oracle_rman']


static_checks.setdefault('oracle_sessions', [])

static_checks['oracle_sessions'] = [
{'id': '450f85bc-2095-4e7e-a9d8-24b25d224c28', 'value': ('oracle_sessions', 'example', {'sessions_abs': None}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['oracle_sessions']


static_checks.setdefault('oracle_sql', [])

static_checks['oracle_sql'] = [
{'id': '1e30b501-07ed-4c4b-b9d7-c7211702886c', 'value': ('oracle_sql', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['oracle_sql']


static_checks.setdefault('oracle_tablespaces', [])

static_checks['oracle_tablespaces'] = [
{'id': '7967211a-8d68-4f63-901f-74312b8f1dc1', 'value': ('oracle_tablespaces', 'ORCL.EXAMPLE_TS', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['oracle_tablespaces']


static_checks.setdefault('oracle_undostat', [])

static_checks['oracle_undostat'] = [
{'id': '72411001-86e2-4a43-bf8f-74b91c474d6a', 'value': ('oracle_undostat', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['oracle_undostat']


static_checks.setdefault('overall_utilization_multiitem', [])

static_checks['overall_utilization_multiitem'] = [
{'id': '9e0cabdc-4521-49f5-8ae3-0d59aa38ae38', 'value': ('ucs_c_rack_server_util', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['overall_utilization_multiitem']


static_checks.setdefault('ovs_bonding', [])

static_checks['ovs_bonding'] = [
{'id': '65e12e67-c90a-40c0-a175-d0b97b12821b', 'value': ('ovs_bonding', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['ovs_bonding']


static_checks.setdefault('palo_alto', [])

static_checks['palo_alto'] = [
{'id': 'a4cb6799-332b-4fbe-8faf-ac581b292feb', 'value': ('palo_alto', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['palo_alto']


static_checks.setdefault('palo_alto_sessions', [])

static_checks['palo_alto_sessions'] = [
{'id': '298318d4-62cc-4bc1-998a-605b1c6ca0c4', 'value': ('palo_alto_sessions', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['palo_alto_sessions']


static_checks.setdefault('palo_alto_users_rule', [])

static_checks['palo_alto_users_rule'] = [
{'id': 'd5b7411f-5cd3-42ff-8a57-12139047b7d0', 'value': ('palo_alto_users', None, {'levels': ('perc_user', (0.0, 0.0))}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['palo_alto_users_rule']


static_checks.setdefault('pci_io_utilization_multiitem', [])

static_checks['pci_io_utilization_multiitem'] = [
{'id': '146bb451-f01e-4d91-816a-4a94f002e3b6', 'value': ('ucs_c_rack_server_util_pci_io', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['pci_io_utilization_multiitem']


static_checks.setdefault('pdu_gude', [])

static_checks['pdu_gude'] = [
{'id': 'b1075bbd-17f5-48b6-afa4-4a5d47ba2ece', 'value': ('pdu_gude', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['pdu_gude']


static_checks.setdefault('pf_used_states', [])

static_checks['pf_used_states'] = [
{'id': '3dd9487b-b20d-4a69-a1b3-e85a021f763d', 'value': ('genua_pfstate', None, {'used': None}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['pf_used_states']


static_checks.setdefault('pfm_health', [])

static_checks['pfm_health'] = [
{'id': '98ba3e23-8079-45c8-b449-d9d8af73d25b', 'value': ('fjdarye_pcie_flash_modules', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['pfm_health']


static_checks.setdefault('pfsense_counter', [])

static_checks['pfsense_counter'] = [
{'id': 'b67c4782-bef9-4ed3-83ee-caa7cef91dc0', 'value': ('pfsense_counter', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['pfsense_counter']


static_checks.setdefault('plesk_backups', [])

static_checks['plesk_backups'] = [
{'id': '1a7e6c26-ed8e-465b-9782-5fd21ca5d920', 'value': ('plesk_backups', 'example', {'no_backup_configured_state': 1, 'no_backup_found_state': 1}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['plesk_backups']


static_checks.setdefault('pll_lock_voltage', [])

static_checks['pll_lock_voltage'] = [
{'id': 'bb3cf8ad-cbdd-466c-b90b-ee5f860cd1ce', 'value': ('icom_repeater_pll_volt', 'RX', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['pll_lock_voltage']


static_checks.setdefault('plug_count', [])

static_checks['plug_count'] = [
{'id': 'a35c3c2a-7322-40b4-8f22-76c6ff13ebfc', 'value': ('raritan_pdu_outletcount', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['plug_count']


static_checks.setdefault('plugs', [])

static_checks['plugs'] = [
{'id': '4b570af6-7321-4d58-b890-29f53730e59b', 'value': ('raritan_pdu_plugs', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['plugs']


static_checks.setdefault('postgres_instance_sessions', [])

static_checks['postgres_instance_sessions'] = [
{'id': '6afa3564-1c34-4334-9e03-09a3ee32d708', 'value': ('postgres_sessions', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['postgres_instance_sessions']


static_checks.setdefault('postgres_locks', [])

static_checks['postgres_locks'] = [
{'id': '6330fa4c-25a9-4011-be20-26e5b7052214', 'value': ('postgres_locks', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['postgres_locks']


static_checks.setdefault('postgres_maintenance', [])

static_checks['postgres_maintenance'] = [
{'id': 'fea03858-48fb-4fbd-902c-637afcdf1309', 'value': ('postgres_stats', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['postgres_maintenance']


static_checks.setdefault('postgres_stat_database', [])

static_checks['postgres_stat_database'] = [
{'id': 'a3afc10c-be75-4e05-b259-71bee1db937f', 'value': ('postgres_stat_database', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['postgres_stat_database']


static_checks.setdefault('power_multiitem', [])

static_checks['power_multiitem'] = [
{'id': 'c93adb6f-b75b-49d2-a41f-098c25bbb6b9', 'value': ('ucs_c_rack_server_power', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['power_multiitem']


static_checks.setdefault('power_presence', [])

static_checks['power_presence'] = [
{'id': 'd485a730-9427-41ed-a433-20ec3056a96f', 'value': ('entity_sensors_power_presence', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['power_presence']


static_checks.setdefault('printer_input', [])

static_checks['printer_input'] = [
{'id': '98b9c0d0-1afc-4c11-8560-9396fb47bf1f', 'value': ('printer_input', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['printer_input']


static_checks.setdefault('printer_output', [])

static_checks['printer_output'] = [
{'id': '5bb253d8-016a-469a-9659-cdb7b9e93ef8', 'value': ('printer_output', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['printer_output']


static_checks.setdefault('printer_supply', [])

static_checks['printer_supply'] = [
{'id': '73fa6f00-ef61-44b9-b6c9-e9f0932ea6e3', 'value': ('printer_supply', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['printer_supply']


static_checks.setdefault('prism_alerts', [])

static_checks['prism_alerts'] = [
{'id': '92810248-0288-4c7d-8af0-e5eaf158d7a8', 'value': ('prism_alerts', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['prism_alerts']


static_checks.setdefault('prism_cluster_cpu', [])

static_checks['prism_cluster_cpu'] = [
{'id': '07293c22-89fc-4af2-856b-02ec2ebf4827', 'value': ('prism_cluster_cpu', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['prism_cluster_cpu']


static_checks.setdefault('prism_cluster_io', [])

static_checks['prism_cluster_io'] = [
{'id': '991bf5ba-3c2e-4e82-b1f5-c2ab1288952b', 'value': ('prism_cluster_io', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['prism_cluster_io']


static_checks.setdefault('prism_cluster_mem', [])

static_checks['prism_cluster_mem'] = [
{'id': '42ee2d8f-a9a6-4117-b9e8-bdaf8ee6c330', 'value': ('prism_cluster_mem', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['prism_cluster_mem']


static_checks.setdefault('prism_host_cpu', [])

static_checks['prism_host_cpu'] = [
{'id': '0b22b31a-bc11-484a-ac31-33c038a5ba4d', 'value': ('prism_host_stats_cpu', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['prism_host_cpu']


static_checks.setdefault('prism_host_disks', [])

static_checks['prism_host_disks'] = [
{'id': '0b8826b3-e7e2-407c-ba87-64036112067a', 'value': ('prism_host_disks', 'example', {'mounted': True}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['prism_host_disks']


static_checks.setdefault('prism_host_mem', [])

static_checks['prism_host_mem'] = [
{'id': 'd4b77a92-a3ef-4eed-bc3a-1e0047f3f91d', 'value': ('prism_host_stats_mem', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['prism_host_mem']


static_checks.setdefault('prism_hosts', [])

static_checks['prism_hosts'] = [
{'id': '126ebaf5-329b-4a4d-b42c-181c7524227b', 'value': ('prism_hosts', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['prism_hosts']


static_checks.setdefault('prism_protection_domains', [])

static_checks['prism_protection_domains'] = [
{'id': 'c8826185-0da8-4cf6-aa34-9be374a8f298', 'value': ('prism_protection_domains', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['prism_protection_domains']


static_checks.setdefault('prism_remote_support', [])

static_checks['prism_remote_support'] = [
{'id': 'a3fdb216-d819-4d20-961d-c2008c52ee4d', 'value': ('prism_remote_support', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['prism_remote_support']


static_checks.setdefault('prism_vm_cpu', [])

static_checks['prism_vm_cpu'] = [
{'id': 'a4b8cd10-d4aa-48f5-8576-2c4f93945e54', 'value': ('prism_vm_stats_cpu', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['prism_vm_cpu']


static_checks.setdefault('prism_vm_memory', [])

static_checks['prism_vm_memory'] = [
{'id': '43243aa5-17ed-41ae-a27c-39f57802ae80', 'value': ('prism_vm_stats_mem', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['prism_vm_memory']


static_checks.setdefault('prism_vm_status', [])

static_checks['prism_vm_status'] = [
{'id': '0ef10d64-d3f0-4918-abcf-7f7229cb6c3b', 'value': ('prism_vm_status', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['prism_vm_status']


static_checks.setdefault('prism_vm_tools', [])

static_checks['prism_vm_tools'] = [
{'id': '6555663e-7a57-4493-988e-87f1022ece72', 'value': ('prism_vm_tools', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['prism_vm_tools']


static_checks.setdefault('prism_vms', [])

static_checks['prism_vms'] = [
{'id': '194fceab-a8d1-4926-97d8-0869468930b6', 'value': ('prism_vms', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['prism_vms']


static_checks.setdefault('prometheus_custom', [])

static_checks['prometheus_custom'] = [
{'id': '9c08774b-199e-4af3-b27d-8137337675b0', 'value': ('prometheus_custom', 'example', {'metric_list': []}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['prometheus_custom']


static_checks.setdefault('proxmox_ve_disk_percentage_used', [])

static_checks['proxmox_ve_disk_percentage_used'] = [
{'id': 'b922ced2-ae73-46eb-a09a-3b2dc19d3f93', 'value': ('proxmox_ve_disk_usage', None, {'levels': (80.0, 90.0)}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['proxmox_ve_disk_percentage_used']


static_checks.setdefault('proxmox_ve_mem_usage', [])

static_checks['proxmox_ve_mem_usage'] = [
{'id': 'f6b8f272-292a-488d-8ecc-057a2e11ce60', 'value': ('proxmox_ve_mem_usage', None, {'levels': (80.0, 90.0)}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['proxmox_ve_mem_usage']


static_checks.setdefault('proxmox_ve_node_info', [])

static_checks['proxmox_ve_node_info'] = [
{'id': '0fc1ffbc-e08c-42ea-aaac-fe57340b1af5', 'value': ('proxmox_ve_node_info', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['proxmox_ve_node_info']


static_checks.setdefault('proxmox_ve_vm_backup_status', [])

static_checks['proxmox_ve_vm_backup_status'] = [
{'id': '75ffb998-2a84-43f0-8b28-b73648a12d7f', 'value': ('proxmox_ve_vm_backup_status', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['proxmox_ve_vm_backup_status']


static_checks.setdefault('proxmox_ve_vm_info', [])

static_checks['proxmox_ve_vm_info'] = [
{'id': 'c787c18e-f4c5-406a-bc33-091470ecaca4', 'value': ('proxmox_ve_vm_info', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['proxmox_ve_vm_info']


static_checks.setdefault('proxmox_ve_vm_snapshot_age', [])

static_checks['proxmox_ve_vm_snapshot_age'] = [
{'id': '8a15b3a2-59e0-4f45-a3e3-aa55b911d79d', 'value': ('proxmox_ve_vm_snapshot_age', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['proxmox_ve_vm_snapshot_age']


static_checks.setdefault('ps', [])

static_checks['ps'] = [
{'id': '25e5f815-44ab-4087-af33-d4399f15f0a4', 'value': ('ps', 'example', {'cpu_rescale_max': True}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['ps']


static_checks.setdefault('ps_voltage', [])

static_checks['ps_voltage'] = [
{'id': 'f5063e79-550c-4b64-b264-8f4f089a7761', 'value': ('icom_repeater_ps_volt', None, {'levels_lower': (0.0, 0.0), 'levels_upper': (0.0, 0.0)}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['ps_voltage']


static_checks.setdefault('psu_wattage', [])

static_checks['psu_wattage'] = [
{'id': 'f275563f-012a-47cc-9500-79ab59d1b48e', 'value': ('aruba_psu_wattage', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['psu_wattage']


static_checks.setdefault('pulse_secure_disk_util', [])

static_checks['pulse_secure_disk_util'] = [
{'id': '43b9c4a6-f065-4f08-a26b-537a2f19727d', 'value': ('pulse_secure_disk_util', None, {'upper_levels': (80.0, 90.0)}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['pulse_secure_disk_util']


static_checks.setdefault('pulse_secure_mem_util', [])

static_checks['pulse_secure_mem_util'] = [
{'id': '37de0bad-298f-46ed-bd69-63a7a5f19df5', 'value': ('pulse_secure_mem_util', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['pulse_secure_mem_util']


static_checks.setdefault('pulse_secure_users', [])

static_checks['pulse_secure_users'] = [
{'id': '2a47589c-2c17-47b9-942e-671c22748700', 'value': ('pulse_secure_users', None, {'upper_number_of_users': None}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['pulse_secure_users']


static_checks.setdefault('pure_storage_capacity', [])

static_checks['pure_storage_capacity'] = [
{'id': '98f6e456-85cf-4e90-8185-9a79ba2e85c7', 'value': ('pure_storage_fa_arrays', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['pure_storage_capacity']


static_checks.setdefault('quantum_storage_status', [])

static_checks['quantum_storage_status'] = [
{'id': '6d4e20f3-7d56-4964-b467-5e309ca6a6b9', 'value': ('quantum_storage_status', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['quantum_storage_status']


static_checks.setdefault('rabbitmq_cluster_messages', [])

static_checks['rabbitmq_cluster_messages'] = [
{'id': 'facc32ed-f63d-4d46-91d0-9cc8e481c5c1', 'value': ('rabbitmq_cluster_messages', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['rabbitmq_cluster_messages']


static_checks.setdefault('rabbitmq_cluster_stats', [])

static_checks['rabbitmq_cluster_stats'] = [
{'id': '24174618-aef2-4c0b-8bfa-ab346f0ed418', 'value': ('rabbitmq_cluster_stats', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['rabbitmq_cluster_stats']


static_checks.setdefault('rabbitmq_nodes', [])

static_checks['rabbitmq_nodes'] = [
{'id': 'a3cf73b2-34c1-4a9b-816c-9cf0c6b0468f', 'value': ('rabbitmq_nodes', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['rabbitmq_nodes']


static_checks.setdefault('rabbitmq_nodes_filedesc', [])

static_checks['rabbitmq_nodes_filedesc'] = [
{'id': 'f33803c8-0a04-4537-a629-b4187725dfa5', 'value': ('rabbitmq_nodes_filedesc', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['rabbitmq_nodes_filedesc']


static_checks.setdefault('rabbitmq_nodes_gc', [])

static_checks['rabbitmq_nodes_gc'] = [
{'id': '8dd147d4-158b-49f6-9615-69392d425249', 'value': ('rabbitmq_nodes_gc', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['rabbitmq_nodes_gc']


static_checks.setdefault('rabbitmq_nodes_proc', [])

static_checks['rabbitmq_nodes_proc'] = [
{'id': '7b419b99-42e6-4218-b9f7-8ead7a3ec6c9', 'value': ('rabbitmq_nodes_proc', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['rabbitmq_nodes_proc']


static_checks.setdefault('rabbitmq_nodes_sockets', [])

static_checks['rabbitmq_nodes_sockets'] = [
{'id': 'ea953254-a49e-4eed-8f23-3e940801d7e1', 'value': ('rabbitmq_nodes_sockets', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['rabbitmq_nodes_sockets']


static_checks.setdefault('rabbitmq_nodes_uptime', [])

static_checks['rabbitmq_nodes_uptime'] = [
{'id': '5a323ca6-2c4b-47fa-8834-88718e753f51', 'value': ('rabbitmq_nodes_uptime', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['rabbitmq_nodes_uptime']


static_checks.setdefault('rabbitmq_queues', [])

static_checks['rabbitmq_queues'] = [
{'id': 'c5b1d589-61c5-4404-af9d-53219f4339f4', 'value': ('rabbitmq_queues', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['rabbitmq_queues']


static_checks.setdefault('rabbitmq_vhosts', [])

static_checks['rabbitmq_vhosts'] = [
{'id': '4aa18c5f-70b3-4373-9bbc-031832061f4c', 'value': ('rabbitmq_vhosts', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['rabbitmq_vhosts']


static_checks.setdefault('raid', [])

static_checks['raid'] = [
{'id': '22703c43-abef-424a-9a05-5def4efd7d04', 'value': ('3ware_units', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['raid']


static_checks.setdefault('raid_disk', [])

static_checks['raid_disk'] = [
{'id': '22a6f034-3327-4686-a200-7fc0dffa62fe', 'value': ('3ware_disks', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['raid_disk']


static_checks.setdefault('raid_summary', [])

static_checks['raid_summary'] = [
{'id': '7ca87e4c-6a93-46cf-bd5c-ef8e1f2c0f7e', 'value': ('fjdarye_disks_summary', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['raid_summary']


static_checks.setdefault('rds_licenses', [])

static_checks['rds_licenses'] = [
{'id': '9d51ef97-4183-483e-aadc-ecb916aafcac', 'value': ('rds_licenses', 'example', {'levels': ('crit_on_all', None)}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['rds_licenses']


static_checks.setdefault('read_hits', [])

static_checks['read_hits'] = [
{'id': '81483217-7371-461a-b8e5-026467aa6ceb', 'value': ('ddn_s2a_stats_readhits', 'example', {'levels_lower': (85.0, 70.0)}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['read_hits']


static_checks.setdefault('redis_info', [])

static_checks['redis_info'] = [
{'id': 'cee814b9-408a-4312-b867-844fc2c0556d', 'value': ('redis_info', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['redis_info']


static_checks.setdefault('redis_info_clients', [])

static_checks['redis_info_clients'] = [
{'id': '8d51ca3a-010e-4685-9289-b6936f2e5acf', 'value': ('redis_info_clients', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['redis_info_clients']


static_checks.setdefault('redis_info_persistence', [])

static_checks['redis_info_persistence'] = [
{'id': '208b9946-8617-4133-8ce5-87f059d595bf', 'value': ('redis_info_persistence', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['redis_info_persistence']


static_checks.setdefault('replication_lag', [])

static_checks['replication_lag'] = [
{'id': '6cbfc993-972c-458e-b6c2-5e005ff1ac77', 'value': ('azure_mysql_replication', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['replication_lag']


static_checks.setdefault('ruckus_ap', [])

static_checks['ruckus_ap'] = [
{'id': '41ce8743-df16-427b-a0a0-81a5a4755619', 'value': ('ruckus_spot_ap', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['ruckus_ap']


static_checks.setdefault('safenet_hsm_eventstats', [])

static_checks['safenet_hsm_eventstats'] = [
{'id': '3c31ca53-34db-4685-b0c2-6b07c266eba7', 'value': ('safenet_hsm_events', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['safenet_hsm_eventstats']


static_checks.setdefault('safenet_hsm_operstats', [])

static_checks['safenet_hsm_operstats'] = [
{'id': 'fa0e8eaf-32e7-40ca-91fd-c90573c910fa', 'value': ('safenet_hsm', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['safenet_hsm_operstats']


static_checks.setdefault('safenet_ntls_clients', [])

static_checks['safenet_ntls_clients'] = [
{'id': 'fada08cf-f007-4f6e-adf8-750aac9a811b', 'value': ('safenet_ntls_clients', None, {'levels': ('fixed', (1000, 2000))}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['safenet_ntls_clients']


static_checks.setdefault('safenet_ntls_links', [])

static_checks['safenet_ntls_links'] = [
{'id': '889c4367-297b-4ca7-8c98-9fc02f56064d', 'value': ('safenet_ntls_links', None, {'levels': ('fixed', (1000, 2000))}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['safenet_ntls_links']


static_checks.setdefault('sansymphony_alerts', [])

static_checks['sansymphony_alerts'] = [
{'id': 'edfe1ee0-6b5c-465a-ac7c-a9727e6cd3da', 'value': ('sansymphony_alerts', None, {'levels': (1, 2)}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['sansymphony_alerts']


static_checks.setdefault('sansymphony_pool', [])

static_checks['sansymphony_pool'] = [
{'id': 'c978150a-f987-4a87-953f-a2159b91a8ee', 'value': ('sansymphony_pool', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['sansymphony_pool']


static_checks.setdefault('sap_dialog', [])

static_checks['sap_dialog'] = [
{'id': '22c09fba-7f33-4a42-a0a4-4aab68775633', 'value': ('sap_dialog', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['sap_dialog']


static_checks.setdefault('sap_hana_backup', [])

static_checks['sap_hana_backup'] = [
{'id': 'deba55a6-ef2f-43df-8229-1e1c3559cdc8', 'value': ('sap_hana_backup', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['sap_hana_backup']


static_checks.setdefault('sap_hana_license', [])

static_checks['sap_hana_license'] = [
{'id': '294a41f8-f910-4986-9ce1-136d96ffbd61', 'value': ('sap_hana_license', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['sap_hana_license']


static_checks.setdefault('sap_hana_memory', [])

static_checks['sap_hana_memory'] = [
{'id': '949c461e-1151-4fa8-a751-d258c3e6bee1', 'value': ('sap_hana_memrate', 'example', {'levels': ('perc_used', (80.0, 90.0))}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['sap_hana_memory']


static_checks.setdefault('sap_hana_replication_status', [])

static_checks['sap_hana_replication_status'] = [
{'id': '52bbbf27-84fb-4843-8a9d-56ddcc3e9bd6', 'value': ('sap_hana_replication_status', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['sap_hana_replication_status']


static_checks.setdefault('saprouter_cert_age', [])

static_checks['saprouter_cert_age'] = [
{'id': '5f53ac3d-a724-44c3-bd65-c00426e38b06', 'value': ('saprouter_cert', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['saprouter_cert_age']


static_checks.setdefault('scratch_tapes', [])

static_checks['scratch_tapes'] = [
{'id': 'b9b1b34a-d9c7-477a-a796-b63b29502929', 'value': ('tsm_scratch', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['scratch_tapes']


static_checks.setdefault('services', [])

static_checks['services'] = [
{'id': 'fe2a4f99-5bfe-4795-a5e5-ef7f20f35ee9', 'value': ('services', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['services']


static_checks.setdefault('services_summary', [])

static_checks['services_summary'] = [
{'id': 'f86928b6-ef7d-46cb-885c-67eea2000363', 'value': ('services_summary', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['services_summary']


static_checks.setdefault('siemens_plc_counter', [])

static_checks['siemens_plc_counter'] = [
{'id': 'd1661d94-54e9-4ece-8367-fa4366350446', 'value': ('siemens_plc_counter', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['siemens_plc_counter']


static_checks.setdefault('siemens_plc_duration', [])

static_checks['siemens_plc_duration'] = [
{'id': '339026ac-1b40-419e-80cf-a371f0240657', 'value': ('siemens_plc_duration', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['siemens_plc_duration']


static_checks.setdefault('siemens_plc_flag', [])

static_checks['siemens_plc_flag'] = [
{'id': '0ba1360d-5589-4d2c-8492-a89feb81584e', 'value': ('siemens_plc_flag', 'example', {'expected_state': True}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['siemens_plc_flag']


static_checks.setdefault('signal_quality', [])

static_checks['signal_quality'] = [
{'id': '29a4fca1-46c1-4f4a-ab01-764ba0b72d82', 'value': ('mikrotik_signal', 'example', {'levels_lower': (0.0, 0.0)}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['signal_quality']


static_checks.setdefault('single_humidity', [])

static_checks['single_humidity'] = [
{'id': 'b78e88a6-860d-4084-a63e-c3ee6dd5c0ed', 'value': ('knuerr_rms_humidity', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['single_humidity']


static_checks.setdefault('skype', [])

static_checks['skype'] = [
{'id': 'd9f29b45-8249-40f5-8044-adb9e8daa228', 'value': ('skype', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['skype']


static_checks.setdefault('skype_conferencing', [])

static_checks['skype_conferencing'] = [
{'id': 'a3ec0fae-4bdd-4097-8752-5c049de19c98', 'value': ('skype_conferencing', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['skype_conferencing']


static_checks.setdefault('skype_edge', [])

static_checks['skype_edge'] = [
{'id': 'a99efe68-5865-4cd0-8b2e-87312c788225', 'value': ('skype_edge', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['skype_edge']


static_checks.setdefault('skype_edgeauth', [])

static_checks['skype_edgeauth'] = [
{'id': '35484198-8acd-422d-a94b-c21a5309c51e', 'value': ('skype_edge_auth', None, {'bad_requests': {'upper': (20, 40)}}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['skype_edgeauth']


static_checks.setdefault('skype_mediation_server', [])

static_checks['skype_mediation_server'] = [
{'id': '60b5c333-ff5b-4663-8de1-6fcb32a2e091', 'value': ('skype_mediation_server', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['skype_mediation_server']


static_checks.setdefault('skype_mobile', [])

static_checks['skype_mobile'] = [
{'id': 'dd076252-5660-4a52-9ad4-9500c93a2bb9', 'value': ('skype_mobile', None, {'requests_processing': {'upper': (10000, 20000)}}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['skype_mobile']


static_checks.setdefault('skype_proxy', [])

static_checks['skype_proxy'] = [
{'id': '180074fb-fcdf-4840-aa32-7791937a16b3', 'value': ('skype_data_proxy', 'example', {'throttled_connections': {'upper': (3, 6)}}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['skype_proxy']


static_checks.setdefault('skype_sip', [])

static_checks['skype_sip'] = [
{'id': '1ac03cba-30f9-40e7-aaef-11e712e62a68', 'value': ('skype_sip_stack', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['skype_sip']


static_checks.setdefault('skype_xmpp', [])

static_checks['skype_xmpp'] = [
{'id': 'd75fc2b6-3528-484d-b782-a64091338391', 'value': ('skype_xmpp_proxy', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['skype_xmpp']


static_checks.setdefault('sles_license', [])

static_checks['sles_license'] = [
{'id': '0a908fae-1b6a-47c8-bc2c-007f03573862', 'value': ('suseconnect', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['sles_license']


static_checks.setdefault('smart_ata', [])

static_checks['smart_ata'] = [
{'id': '4bfb1b0a-302b-4be4-884e-b6f828535db1', 'value': ('smart_ata_stats', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['smart_ata']


static_checks.setdefault('smart_nvme', [])

static_checks['smart_nvme'] = [
{'id': '6581213f-5de0-4c9b-83a6-251c7ad0801e', 'value': ('smart_nvme_stats', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['smart_nvme']


static_checks.setdefault('smoke', [])

static_checks['smoke'] = [
{'id': 'c9ffc197-008d-4168-9684-57719cf5147f', 'value': ('kentix_amp_sensors_smoke', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['smoke']


static_checks.setdefault('snapvault', [])

static_checks['snapvault'] = [
{'id': '014bf9fd-f226-4705-859a-2f3804b78888', 'value': ('netapp_ontap_snapvault', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['snapvault']


static_checks.setdefault('snat_usage', [])

static_checks['snat_usage'] = [
{'id': '026bbe15-dc46-44ba-8193-a23e000e2559', 'value': ('azure_load_balancer_snat', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['snat_usage']


static_checks.setdefault('solaris_services', [])

static_checks['solaris_services'] = [
{'id': '10ab63a9-18d8-4e72-95b4-74257b60d518', 'value': ('solaris_services', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['solaris_services']


static_checks.setdefault('solaris_services_summary', [])

static_checks['solaris_services_summary'] = [
{'id': '93db80be-efbc-4791-bb68-9659aa997a7d', 'value': ('solaris_services_summary', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['solaris_services_summary']


static_checks.setdefault('sophos_cpu', [])

static_checks['sophos_cpu'] = [
{'id': '51129a22-eb3e-40ee-9b5b-a14a4847641a', 'value': ('sophos_cpu', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['sophos_cpu']


static_checks.setdefault('sophos_disk', [])

static_checks['sophos_disk'] = [
{'id': '48919749-86b0-4690-ab50-932d9182c40c', 'value': ('sophos_disk', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['sophos_disk']


static_checks.setdefault('sophos_memory', [])

static_checks['sophos_memory'] = [
{'id': '1d94648f-16b4-42cd-928a-458c6aff031d', 'value': ('sophos_memory', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['sophos_memory']


static_checks.setdefault('splunk_alerts', [])

static_checks['splunk_alerts'] = [
{'id': '5b0c294f-2f36-4e3d-9d43-ea581bdc6d05', 'value': ('splunk_alerts', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['splunk_alerts']


static_checks.setdefault('splunk_health', [])

static_checks['splunk_health'] = [
{'id': 'b889fa48-c2c3-4620-a2d7-570ffd3656b9', 'value': ('splunk_health', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['splunk_health']


static_checks.setdefault('splunk_jobs', [])

static_checks['splunk_jobs'] = [
{'id': '76596b7a-c1a7-4416-b999-d2c936b7c604', 'value': ('splunk_jobs', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['splunk_jobs']


static_checks.setdefault('splunk_license_state', [])

static_checks['splunk_license_state'] = [
{'id': '3262d0e7-0d02-4547-b8eb-197a82d6a9ac', 'value': ('splunk_license_state', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['splunk_license_state']


static_checks.setdefault('splunk_license_usage', [])

static_checks['splunk_license_usage'] = [
{'id': '17fe8e40-590a-476b-8e00-a85a2c949f86', 'value': ('splunk_license_usage', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['splunk_license_usage']


static_checks.setdefault('sshd_config', [])

static_checks['sshd_config'] = [
{'id': 'c19b49a6-4a8c-4679-ae6f-3c2efc9c3d76', 'value': ('sshd_config', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['sshd_config']


static_checks.setdefault('steelhead_connections', [])

static_checks['steelhead_connections'] = [
{'id': 'cbaf4602-0f2e-4b05-846b-33f91f2f50bb', 'value': ('steelhead_connections', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['steelhead_connections']


static_checks.setdefault('storage_iops', [])

static_checks['storage_iops'] = [
{'id': 'c9477662-b77c-4d6e-af11-481b07c0c65c', 'value': ('ddn_s2a_stats_io', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['storage_iops']


static_checks.setdefault('storage_throughput', [])

static_checks['storage_throughput'] = [
{'id': '9db21957-4501-49f8-a51f-f96c058c536e', 'value': ('ddn_s2a_stats', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['storage_throughput']


static_checks.setdefault('storcli_pdisks', [])

static_checks['storcli_pdisks'] = [
{'id': '26f8ff73-e60c-45ac-8603-94f0b609db2c', 'value': ('megaraid_pdisks', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['storcli_pdisks']


static_checks.setdefault('storcli_vdrives', [])

static_checks['storcli_vdrives'] = [
{'id': 'f2ffaf66-bed8-4164-9d4b-1339c5bacc06', 'value': ('megaraid_ldisks', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['storcli_vdrives']


static_checks.setdefault('stormshield_quality', [])

static_checks['stormshield_quality'] = [
{'id': '86b332eb-663c-487b-b37e-59be59966d80', 'value': ('stormshield_cluster_node', 'example', {'quality': ('fixed', (80.0, 50.0))}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['stormshield_quality']


static_checks.setdefault('switch_contact', [])

static_checks['switch_contact'] = [
{'id': '15cc7e3c-b95f-49fd-a30c-ff566666b52d', 'value': ('etherbox_switch', 'example', {'state': 'open'}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['switch_contact']


static_checks.setdefault('sym_brightmail_queues', [])

static_checks['sym_brightmail_queues'] = [
{'id': '91059d7a-a116-46e3-acd5-93b85876110c', 'value': ('sym_brightmail_queues', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['sym_brightmail_queues']


static_checks.setdefault('synology_update', [])

static_checks['synology_update'] = [
{'id': 'e3d6d74e-8876-444e-be1d-b8259f0d13bb', 'value': ('synology_update', None, {'ok_states': [2], 'warn_states': [5], 'crit_states': [1, 4]}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['synology_update']


static_checks.setdefault('systemd_services_summary', [])

static_checks['systemd_services_summary'] = [
{'id': '7a591053-35f2-4d86-b7ca-594931231aac', 'value': ('systemd_units_services_summary', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['systemd_services_summary']


static_checks.setdefault('systemd_sockets_summary', [])

static_checks['systemd_sockets_summary'] = [
{'id': '2b568b0e-b27f-4bbe-b61d-22ea9a027bd2', 'value': ('systemd_units_sockets_summary', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['systemd_sockets_summary']


static_checks.setdefault('systemd_units_services', [])

static_checks['systemd_units_services'] = [
{'id': 'b2933ddf-99ec-485d-b5df-6146ac7178c2', 'value': ('systemd_units_services', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['systemd_units_services']


static_checks.setdefault('systemd_units_sockets', [])

static_checks['systemd_units_sockets'] = [
{'id': '8294ed27-8388-4077-8922-2ae3da0ec5e4', 'value': ('systemd_units_sockets', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['systemd_units_sockets']


static_checks.setdefault('systemtime', [])

static_checks['systemtime'] = [
{'id': '7ac071d2-524c-4281-9456-99cda40c72a4', 'value': ('systemtime', None, {'levels': (30, 60)}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['systemtime']


static_checks.setdefault('tcp_conn_stats', [])

static_checks['tcp_conn_stats'] = [
{'id': '76638451-c231-4a53-8eaf-ce29cf583f73', 'value': ('tcp_conn_stats', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['tcp_conn_stats']


static_checks.setdefault('tcp_connections', [])

static_checks['tcp_connections'] = [
{'id': '882fe364-0150-4af6-8d96-cf4077802d4e', 'value': ('netstat', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['tcp_connections']


static_checks.setdefault('temperature', [])

static_checks['temperature'] = [
{'id': '5bb97a24-0e2e-484e-b315-4184a346ce38', 'value': ('acme_temp', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['temperature']


static_checks.setdefault('threads', [])

static_checks['threads'] = [
{'id': '651c9b4b-eaa4-4227-9149-4d166b93613e', 'value': ('bluecat_threads', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['threads']


static_checks.setdefault('threepar_capacity', [])

static_checks['threepar_capacity'] = [
{'id': '5414614d-d31d-4ac1-aab0-81bfa40bd833', 'value': ('3par_capacity', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['threepar_capacity']


static_checks.setdefault('threepar_cpgs', [])

static_checks['threepar_cpgs'] = [
{'id': '0415b0ad-7851-45f0-9d23-a6fce47e8f9f', 'value': ('3par_cpgs_usage', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['threepar_cpgs']


static_checks.setdefault('threepar_ports', [])

static_checks['threepar_ports'] = [
{'id': 'a7caf9da-e6aa-47af-96cb-29c98fd8134a', 'value': ('3par_ports', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['threepar_ports']


static_checks.setdefault('threepar_remotecopy', [])

static_checks['threepar_remotecopy'] = [
{'id': 'bbb7735a-eeac-4bff-9f29-977e676ade89', 'value': ('3par_remotecopy', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['threepar_remotecopy']


static_checks.setdefault('timesyncd_time', [])

static_checks['timesyncd_time'] = [
{'id': '11b22a27-5476-40e0-a38d-dc419dd22d9c', 'value': ('timesyncd', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['timesyncd_time']


static_checks.setdefault('ucs_bladecenter_chassis_voltage', [])

static_checks['ucs_bladecenter_chassis_voltage'] = [
{'id': '0e7ab7db-5599-47f0-ac2a-fbf56f412e36', 'value': ('ucs_bladecenter_psu', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['ucs_bladecenter_chassis_voltage']


static_checks.setdefault('ucs_bladecenter_faultinst', [])

static_checks['ucs_bladecenter_faultinst'] = [
{'id': '718652f9-45b5-4905-aec0-264153403d3a', 'value': ('ucs_bladecenter_faultinst', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['ucs_bladecenter_faultinst']


static_checks.setdefault('ucs_c_rack_server_led', [])

static_checks['ucs_c_rack_server_led'] = [
{'id': '66002ac0-e67d-4891-b0b3-9f6ff5e05aef', 'value': ('ucs_c_rack_server_led', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['ucs_c_rack_server_led']


static_checks.setdefault('ups_capacity', [])

static_checks['ups_capacity'] = [
{'id': 'c09f6e03-29d1-476b-a6b9-911f51fc2400', 'value': ('ups_capacity', None, {'capacity': (95, 90)}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['ups_capacity']


static_checks.setdefault('ups_out_load', [])

static_checks['ups_out_load'] = [
{'id': '462d2c90-6168-489a-b26d-1ab31937ee60', 'value': ('ups_out_load', 'example', {'levels': (85, 90)}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['ups_out_load']


static_checks.setdefault('ups_outphase', [])

static_checks['ups_outphase'] = [
{'id': '82d3b64e-8dd4-4cbd-8220-6ec6cad055d7', 'value': ('apc_symmetra_elphase', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['ups_outphase']


static_checks.setdefault('ups_test', [])

static_checks['ups_test'] = [
{'id': '815934ce-34b9-4e61-8390-6cb429fd089c', 'value': ('apc_symmetra_test', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['ups_test']


static_checks.setdefault('uptime', [])

static_checks['uptime'] = [
{'id': '20807517-89d5-49d3-9172-38afe2e16d40', 'value': ('ddn_s2a_uptime', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['uptime']


static_checks.setdefault('uptime_multiitem', [])

static_checks['uptime_multiitem'] = [
{'id': 'f225fbff-8e9e-4d03-bbe6-fc61e3a82e1d', 'value': ('couchbase_nodes_uptime', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['uptime_multiitem']


static_checks.setdefault('varnish_backend', [])

static_checks['varnish_backend'] = [
{'id': '16a0a031-359f-4d59-959b-0976874457ba', 'value': ('varnish_backend', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['varnish_backend']


static_checks.setdefault('varnish_backend_success_ratio', [])

static_checks['varnish_backend_success_ratio'] = [
{'id': 'eee803da-baf3-4686-8860-ca2219d5c8b2', 'value': ('varnish_backend_success_ratio', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['varnish_backend_success_ratio']


static_checks.setdefault('varnish_cache', [])

static_checks['varnish_cache'] = [
{'id': '4a209f9f-0fb9-4d18-adac-0125bd76458a', 'value': ('varnish_cache', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['varnish_cache']


static_checks.setdefault('varnish_cache_hit_ratio', [])

static_checks['varnish_cache_hit_ratio'] = [
{'id': 'a48feb90-2a91-4df5-9824-52d5cbc0e102', 'value': ('varnish_cache_hit_ratio', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['varnish_cache_hit_ratio']


static_checks.setdefault('varnish_client', [])

static_checks['varnish_client'] = [
{'id': '3020e774-4307-4343-93e5-386d79b65fd6', 'value': ('varnish_client', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['varnish_client']


static_checks.setdefault('varnish_esi', [])

static_checks['varnish_esi'] = [
{'id': '50171f61-e648-4fe7-a565-03cb04bbb929', 'value': ('varnish_esi', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['varnish_esi']


static_checks.setdefault('varnish_fetch', [])

static_checks['varnish_fetch'] = [
{'id': '7b232ba8-1dbb-4552-bc3f-775ecbffa641', 'value': ('varnish_fetch', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['varnish_fetch']


static_checks.setdefault('varnish_objects', [])

static_checks['varnish_objects'] = [
{'id': 'cfc8d116-dec6-4586-8739-e31a6219edfb', 'value': ('varnish_objects', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['varnish_objects']


static_checks.setdefault('varnish_worker', [])

static_checks['varnish_worker'] = [
{'id': 'bf3e83fb-3b22-46cd-86b4-f55647fa7b94', 'value': ('varnish_worker', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['varnish_worker']


static_checks.setdefault('varnish_worker_thread_ratio', [])

static_checks['varnish_worker_thread_ratio'] = [
{'id': '25852774-fc13-4d26-a4f4-3229a1e00828', 'value': ('varnish_worker_thread_ratio', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['varnish_worker_thread_ratio']


static_checks.setdefault('veeam_backup', [])

static_checks['veeam_backup'] = [
{'id': '5a80be83-a1c8-4fc4-8912-9516631a79d5', 'value': ('veeam_client', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['veeam_backup']


static_checks.setdefault('veeam_cdp_jobs', [])

static_checks['veeam_cdp_jobs'] = [
{'id': '72498fec-2172-40d9-a43f-d7babd8e0600', 'value': ('veeam_cdp_jobs', 'example', {'age': (108000, 172800)}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['veeam_cdp_jobs']


static_checks.setdefault('veeam_tapejobs', [])

static_checks['veeam_tapejobs'] = [
{'id': '2060b07e-8fc4-440f-840c-2ac1bd491d26', 'value': ('veeam_tapejobs', 'example', {'levels_upper': (0, 0)}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['veeam_tapejobs']


static_checks.setdefault('veritas_vcs', [])

static_checks['veritas_vcs'] = [
{'id': 'ffee91ab-38a7-4d19-8343-e3b724bc04dc', 'value': ('veritas_vcs', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['veritas_vcs']


static_checks.setdefault('viprinet_router', [])

static_checks['viprinet_router'] = [
{'id': '03e7f745-53e3-4fb8-8d6f-5304ad7770ca', 'value': ('viprinet_router', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['viprinet_router']


static_checks.setdefault('vm_guest_tools', [])

static_checks['vm_guest_tools'] = [
{'id': '3fd9e5c0-5783-4d85-a163-59a7127f388e', 'value': ('esx_vsphere_vm_guest_tools', None, {'guestToolsCurrent': 0, 'guestToolsNeedUpgrade': 1, 'guestToolsNotInstalled': 2, 'guestToolsUnmanaged': 0}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['vm_guest_tools']


static_checks.setdefault('vm_heartbeat', [])

static_checks['vm_heartbeat'] = [
{'id': 'f769730a-9387-4857-8f0f-a51d4158041b', 'value': ('esx_vsphere_vm_heartbeat', None, {'heartbeat_missing': 2, 'heartbeat_intermittend': 1, 'heartbeat_no_tools': 1, 'heartbeat_ok': 0}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['vm_heartbeat']


static_checks.setdefault('vm_snapshots', [])

static_checks['vm_snapshots'] = [
{'id': '2c143748-166c-497b-acf6-8791e0b6df18', 'value': ('hyperv_checkpoints', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['vm_snapshots']


static_checks.setdefault('vm_state', [])

static_checks['vm_state'] = [
{'id': 'ae0051a3-3e35-49a3-9cc9-d409c8a794ec', 'value': ('vbox_guest', None, None), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['vm_state']


static_checks.setdefault('vms_procs', [])

static_checks['vms_procs'] = [
{'id': 'af878f74-2ea4-4137-a63c-219351a6cec3', 'value': ('vms_system_procs', None, {'levels_upper': None}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['vms_procs']


static_checks.setdefault('voltage', [])

static_checks['voltage'] = [
{'id': '0e842317-9693-48dc-a189-e158b5d7ab6f', 'value': ('enviromux_all_external_voltage', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['voltage']


static_checks.setdefault('volume_groups', [])

static_checks['volume_groups'] = [
{'id': 'ad2fe350-3b5f-4f4e-a2db-6761bc34a7c4', 'value': ('lvm_vgs', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['volume_groups']


static_checks.setdefault('vpn_tunnel', [])

static_checks['vpn_tunnel'] = [
{'id': 'a0535728-98e6-4f63-9277-a185259e982d', 'value': ('cisco_vpn_tunnel', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['vpn_tunnel']


static_checks.setdefault('webserver', [])

static_checks['webserver'] = [
{'id': 'be154804-a464-47f0-a5f2-dbf1f086d949', 'value': ('azure_sites', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['webserver']


static_checks.setdefault('win_dhcp_pools', [])

static_checks['win_dhcp_pools'] = [
{'id': 'da614384-a4e9-4219-aaa8-8585b9af9e79', 'value': ('isc_dhcpd', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['win_dhcp_pools']


static_checks.setdefault('win_license', [])

static_checks['win_license'] = [
{'id': '7b2ef190-22c0-4736-82d2-fa63adb8263c', 'value': ('win_license', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['win_license']


static_checks.setdefault('windows_multipath', [])

static_checks['windows_multipath'] = [
{'id': 'ef399140-c3b5-46fd-a245-f662fc94d435', 'value': ('windows_multipath', None, {'active_paths': 0}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['windows_multipath']


static_checks.setdefault('windows_printer_queues', [])

static_checks['windows_printer_queues'] = [
{'id': 'c9fe0b41-6fa3-487d-b8a3-9a507a26a043', 'value': ('win_printers', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['windows_printer_queues']


static_checks.setdefault('windows_tasks', [])

static_checks['windows_tasks'] = [
{'id': 'e5d71a68-14ae-4d06-894f-48e37855abf4', 'value': ('windows_tasks', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['windows_tasks']


static_checks.setdefault('windows_updates', [])

static_checks['windows_updates'] = [
{'id': 'f6e2be1c-7dd0-4842-ae30-ed2e96cb55ef', 'value': ('windows_updates', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['windows_updates']


static_checks.setdefault('winperf_ts_sessions', [])

static_checks['winperf_ts_sessions'] = [
{'id': 'fd0e3697-f58f-4937-8a94-93881804d84f', 'value': ('winperf_ts_sessions', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['winperf_ts_sessions']


static_checks.setdefault('wlc_clients', [])

static_checks['wlc_clients'] = [
{'id': '80a69a0a-90cc-46cb-9c0f-4323ec806f2b', 'value': ('wlc_clients', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['wlc_clients']


static_checks.setdefault('wmic_process', [])

static_checks['wmic_process'] = [
{'id': '3e5670da-2bfb-4baa-a147-9c3386fa18cc', 'value': ('wmic_process', 'example', ('example.exe', 0, 0, 0, 0, 0.0, 0.0)), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['wmic_process']


static_checks.setdefault('wut_webio', [])

static_checks['wut_webio'] = [
{'id': 'fa875059-fc65-4936-a154-abd40f92d984', 'value': ('wut_webio', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['wut_webio']


static_checks.setdefault('zertificon_mail_queues', [])

static_checks['zertificon_mail_queues'] = [
{'id': '1d260c41-4aac-4564-bc8e-477a5e19955e', 'value': ('zertificon_mail_queues', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['zertificon_mail_queues']


static_checks.setdefault('zorp_connections', [])

static_checks['zorp_connections'] = [
{'id': '3ac8b36d-1c58-4d2e-a255-9a66bd2fb024', 'value': ('zorp_connections', None, {'levels': ('fixed', (15, 20))}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['zorp_connections']


static_checks.setdefault('zpool_status', [])

static_checks['zpool_status'] = [
{'id': 'bf3752ac-e122-4a80-81a2-bd15086b0321', 'value': ('zpool_status', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['zpool_status']


static_checks.setdefault('zypper', [])

static_checks['zypper'] = [
{'id': '4a50cf77-b7a3-47ea-8d14-98d9a0b77c5c', 'value': ('zypper', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['zypper']


globals().setdefault('tcp_connect_timeouts', [])

tcp_connect_timeouts = [
{'id': '6d983bff-c647-4855-ba2e-81ab1bb7f041', 'value': 5.0, 'condition': {}, 'options': {'disabled': False}},
] + tcp_connect_timeouts


globals().setdefault('usewalk_hosts', [])

usewalk_hosts = [
{'id': 'ac08b2d6-ed09-46f4-9ae8-04faaedb0206', 'value': True, 'condition': {}, 'options': {'disabled': False}},
] + usewalk_hosts


globals().setdefault('windows_tasks_discovery', [])

windows_tasks_discovery = [
{'id': '21bf6755-2354-464e-b298-05879860cfcb', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + windows_tasks_discovery


globals().setdefault('winperf_msx_queues_inventory', [])

winperf_msx_queues_inventory = [
{'id': 'e19dbcd2-bdd0-419f-9d5a-f5f7bebb9f58', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + winperf_msx_queues_inventory


checkgroup_parameters.setdefault('apc_symentra', [])

checkgroup_parameters['apc_symentra'] = [
{'id': '7dff0c15-704c-418e-9e2f-497e64eca176', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['apc_symentra']


checkgroup_parameters.setdefault('emcvnx_disks', [])

checkgroup_parameters['emcvnx_disks'] = [
{'id': 'a6ff5e78-389f-4d84-a0d6-42325739859f', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['emcvnx_disks']


checkgroup_parameters.setdefault('emcvnx_storage_pools', [])

checkgroup_parameters['emcvnx_storage_pools'] = [
{'id': '0cd137a4-ea28-47a9-a3df-52c42cef7b86', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['emcvnx_storage_pools']


checkgroup_parameters.setdefault('emcvnx_storage_pools_tiering', [])

checkgroup_parameters['emcvnx_storage_pools_tiering'] = [
{'id': '13f02700-cce2-4eb5-88e5-be248e4896d2', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['emcvnx_storage_pools_tiering']


checkgroup_parameters.setdefault('entersekt_soaprrors', [])

checkgroup_parameters['entersekt_soaprrors'] = [
{'id': '2c01b3ad-09aa-425e-bf83-c9c1b2b1625a', 'value': {}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['entersekt_soaprrors']


checkgroup_parameters.setdefault('sp_util', [])

checkgroup_parameters['sp_util'] = [
{'id': 'a842bffe-df5d-4aeb-be39-ba5536c1ccbc', 'value': {'levels': (50.0, 60.0)}, 'condition': {}, 'options': {'disabled': False}},
] + checkgroup_parameters['sp_util']


static_checks.setdefault('apc_symentra', [])

static_checks['apc_symentra'] = [
{'id': '060d52fa-c5cb-49b4-b250-15a88caa6a0d', 'value': ('apc_symmetra', None, {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['apc_symentra']


static_checks.setdefault('emcvnx_disks', [])

static_checks['emcvnx_disks'] = [
{'id': '5a4df565-2df9-4877-919b-4a12a1226c87', 'value': ('emcvnx_disks', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['emcvnx_disks']


static_checks.setdefault('emcvnx_storage_pools', [])

static_checks['emcvnx_storage_pools'] = [
{'id': '6fbf3034-1f86-4edc-b622-61adbc8572f4', 'value': ('emcvnx_storage_pools', '', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['emcvnx_storage_pools']


static_checks.setdefault('emcvnx_storage_pools_tiering', [])

static_checks['emcvnx_storage_pools_tiering'] = [
{'id': '48ae4636-bdc1-4858-9eea-25c436512e0b', 'value': ('emcvnx_storage_pools_tiering', 'example', {}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['emcvnx_storage_pools_tiering']


static_checks.setdefault('sp_util', [])

static_checks['sp_util'] = [
{'id': 'ef8e613e-b28b-470e-ad24-aa1f38628fc1', 'value': ('emcvnx_sp_util', None, {'levels': (50.0, 60.0)}), 'condition': {}, 'options': {'disabled': False}},
] + static_checks['sp_util']
