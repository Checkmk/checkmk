#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable

mock_discovery_result = {
    'check_table': [
        ('old', 'cpu.loads', 'cpu_load', None, 'cpuload_default_levels', (5.0, 10.0), 'CPU load', 0,
         '15 min load: 1.32 at 8 Cores (0.17 per Core)', [('load1', 2.7, 40.0, 80.0, 0, 8),
                                                          ('load5', 1.63, 40.0, 80.0, 0, 8),
                                                          ('load15', 1.32, 40.0, 80.0, 0, 8)], {}),
        ('old', 'cpu.threads', 'threads', None, '{}', {
            'levels': (2000, 4000)
        }, 'Number of threads', 0, 'Count: 1708 threads, Usage: 1.35%',
         [('threads', 1708, 2000.0, 4000.0), ('thread_usage', 1.3496215054443164, None, None)], {}),
        ('new', 'df', 'filesystem', '/opt/omd/sites/heute/tmp', {
            'include_volume_name': False
        }, {
             'include_volume_name': False,
             'inodes_levels': (10.0, 5.0),
             'levels': (80.0, 90.0),
             'levels_low': (50.0, 60.0),
             'magic_normsize': 20,
             'show_inodes': 'onlow',
             'show_levels': 'onmagic',
             'show_reserved': False,
             'trend_perfdata': True,
             'trend_range': 24
         }, 'Filesystem /opt/omd/sites/heute/tmp', 0, '0.08% used (6.30 MB of 7.76 GB)',
         [('fs_used', 6.30078125, 6356.853125, 7151.459765625, 0, 7946.06640625),
          ('fs_size', 7946.06640625), ('fs_used_percent', 0.07929434424363863),
          ('inodes_used', 1558, 1830773.7, 1932483.3499999999, 0.0, 2034193.0)], {}),
        ('new', 'df', 'filesystem', '/opt/omd/sites/old/tmp', {
            'include_volume_name': False
        }, {
             'include_volume_name': False,
             'inodes_levels': (10.0, 5.0),
             'levels': (80.0, 90.0),
             'levels_low': (50.0, 60.0),
             'magic_normsize': 20,
             'show_inodes': 'onlow',
             'show_levels': 'onmagic',
             'show_reserved': False,
             'trend_perfdata': True,
             'trend_range': 24
         }, 'Filesystem /opt/omd/sites/old/tmp', 0, '0% used (0.00 B of 7.76 GB)', [
             ('fs_used', 0.0, 6356.853125, 7151.459765625, 0, 7946.06640625),
             ('fs_size', 7946.06640625), ('fs_used_percent', 0.0),
             ('inodes_used', 1, 1830773.7, 1932483.3499999999, 0.0, 2034193.0)
         ], {}),
        ('new', 'df', 'filesystem', '/opt/omd/sites/stable/tmp', {
            'include_volume_name': False
        }, {
             'include_volume_name': False,
             'inodes_levels': (10.0, 5.0),
             'levels': (80.0, 90.0),
             'levels_low': (50.0, 60.0),
             'magic_normsize': 20,
             'show_inodes': 'onlow',
             'show_levels': 'onmagic',
             'show_reserved': False,
             'trend_perfdata': True,
             'trend_range': 24
         }, 'Filesystem /opt/omd/sites/stable/tmp', 0, '0.12% used (9.43 MB of 7.76 GB)',
         [('fs_used', 9.42578125, 6356.853125, 7151.459765625, 0, 7946.06640625),
          ('fs_size', 7946.06640625), ('fs_used_percent', 0.11862197933037819),
          ('inodes_used', 1412, 1830773.7, 1932483.3499999999, 0.0, 2034193.0)], {}),
        ('new', 'df', 'filesystem', '/', {
            'include_volume_name': False
        }, {
             'include_volume_name': False,
             'inodes_levels': (10.0, 5.0),
             'levels': (80.0, 90.0),
             'levels_low': (50.0, 60.0),
             'magic_normsize': 20,
             'show_inodes': 'onlow',
             'show_levels': 'onmagic',
             'show_reserved': False,
             'trend_perfdata': True,
             'trend_range': 24
         }, 'Filesystem /', 0, '25.24% used (117.68 of 466.31 GB)',
         [('fs_used', 120506.43359375, 382000.025, 429750.028125, 0, 477500.03125),
          ('fs_size', 477500.03125), ('fs_used_percent', 25.236947792084568),
          ('inodes_used', 1131429, 28009267.2, 29565337.599999998, 0.0, 31121408.0)], {}),
        ('old', 'df', 'filesystem', '/boot/efi', "{'include_volume_name': False}", {
            'include_volume_name': False,
            'inodes_levels': (10.0, 5.0),
            'levels': (80.0, 90.0),
            'levels_low': (50.0, 60.0),
            'magic_normsize': 20,
            'show_inodes': 'onlow',
            'show_levels': 'onmagic',
            'show_reserved': False,
            'trend_perfdata': True,
            'trend_range': 24
        }, 'Filesystem /boot/efi', 0, '3.0% used (15.33 of 510.98 MB)',
         [('fs_used', 15.328125, 408.7875, 459.8859375, 0, 510.984375), ('fs_size', 510.984375),
          ('fs_used_percent', 2.9997247958902853)], {}),
        ('new', 'df', 'filesystem', '/boot', {
            'include_volume_name': False
        }, {
             'include_volume_name': False,
             'inodes_levels': (10.0, 5.0),
             'levels': (80.0, 90.0),
             'levels_low': (50.0, 60.0),
             'magic_normsize': 20,
             'show_inodes': 'onlow',
             'show_levels': 'onmagic',
             'show_reserved': False,
             'trend_perfdata': True,
             'trend_range': 24
         }, 'Filesystem /boot', 0, '30.85% used (217.37 of 704.48 MB)',
         [('fs_used', 217.3671875, 563.5875, 634.0359375, 0, 704.484375), ('fs_size', 704.484375),
          ('fs_used_percent', 30.854791846873823),
          ('inodes_used', 305, 42163.200000000004, 44505.6, 0.0, 46848.0)], {}),
        ('old', 'kernel.performance', 'kernel_performance', None, '{}', {}, 'Kernel Performance', 0,
         'WAITING - Counter based check, cannot be done offline', [
             ('process_creations', 0.0, None, None), ('context_switches', 0.0, None, None),
             ('major_page_faults', 0.0, None, None), ('page_swap_in', 0.0, None, None),
             ('page_swap_out', 0.0, None, None)
         ], {}),
        ('old', 'kernel.util', 'cpu_iowait', None, '{}', {}, 'CPU utilization', 0,
         'User: 14.7%, System: 12.14%, Wait: 0.1%, Total CPU: 26.95%', [
             ('user', 14.70410082412248, None, None), ('system', 12.142805812602681, None, None),
             ('wait', 0.10180487170606699, None, None),
             ('util', 26.948711508431227, None, None, 0, None)
         ], {}),
        ('old', 'lnx_thermal', 'temperature', 'Zone 0', '{}', {
            'device_levels_handling': 'devdefault',
            'levels': (70.0, 80.0)
        }, 'Temperature Zone 0', 0, '25.0 °C', [('temp', 25.0, 107.0, 107.0)], {}),
        ('old', 'lnx_thermal', 'temperature', 'Zone 1', '{}', {
            'device_levels_handling': 'devdefault',
            'levels': (70.0, 80.0)
        }, 'Temperature Zone 1', 0, '20.0 °C', [('temp', 20.0, 70.0, 80.0)], {}),
        ('old', 'lnx_thermal', 'temperature', 'Zone 2', '{}', {
            'device_levels_handling': 'devdefault',
            'levels': (70.0, 80.0)
        }, 'Temperature Zone 2', 0, '54.0 °C', [('temp', 54.0, 78.0, 88.0)], {}),
        ('old', 'lnx_thermal', 'temperature', 'Zone 3', '{}', {
            'device_levels_handling': 'devdefault',
            'levels': (70.0, 80.0)
        }, 'Temperature Zone 3', 0, '35.0 °C', [('temp', 35.0, 70.0, 80.0)], {}),
        ('old', 'lnx_thermal', 'temperature', 'Zone 4', '{}', {
            'device_levels_handling': 'devdefault',
            'levels': (70.0, 80.0)
        }, 'Temperature Zone 4', 0, '41.0 °C', [('temp', 41.0, 70.0, 80.0)], {}),
        ('old', 'lnx_thermal', 'temperature', 'Zone 5', '{}', {
            'device_levels_handling': 'devdefault',
            'levels': (70.0, 80.0)
        }, 'Temperature Zone 5', 0, '55.5 °C', [('temp', 55.5, 115.0, 115.0)], {}),
        ('old', 'lnx_thermal', 'temperature', 'Zone 6', '{}', {
            'device_levels_handling': 'devdefault',
            'levels': (70.0, 80.0)
        }, 'Temperature Zone 6', 0, '64.0 °C', [('temp', 64.0, 99.0, 127.0)], {}),
        ('old', 'lnx_thermal', 'temperature', 'Zone 7', '{}', {
            'device_levels_handling': 'devdefault',
            'levels': (70.0, 80.0)
        }, 'Temperature Zone 7', 1, '74.0 °C (warn/crit at 70.0/80.0 °C)', [('temp', 74.0, 70.0,
                                                                             80.0)], {}),
        ('old', 'lnx_thermal', 'temperature', 'Zone 8', '{}', {
            'device_levels_handling': 'devdefault',
            'levels': (70.0, 80.0)
        }, 'Temperature Zone 8', 0, '38.0 °C', [('temp', 38.0, 70.0, 80.0)], {}),
        ('new', 'mem.linux', 'memory_linux', None, {}, {
            'levels_commitlimit': ('perc_free', (20.0, 10.0)),
            'levels_committed': ('perc_used', (100.0, 150.0)),
            'levels_hardwarecorrupted': ('abs_used', (1, 1)),
            'levels_pagetables': ('perc_used', (8.0, 16.0)),
            'levels_shm': ('perc_used', (20.0, 30.0)),
            'levels_total': ('perc_used', (120.0, 150.0)),
            'levels_virtual': ('perc_used', (80.0, 90.0)),
            'levels_vmalloc': ('abs_free', (52428800, 31457280))
        }, 'Memory', 2,
         'Total virtual memory: 49.43% - 8.14 GB of 16.48 GB, RAM: 47.68% - 7.40 GB of 15.52 GB, Swap: 77.91% - 763.52 MB of 980.00 MB, Largest Free VMalloc Chunk: 0% free - 0.00 B of 32.00 TB VMalloc Area (warn/crit below 50.00 MB/30.00 MB free)(!!)',
         [('active', 8891592704), ('active_anon', 7336378368), ('active_file', 1555214336),
          ('anon_huge_pages', 0), ('anon_pages', 7420919808), ('bounce', 0), ('buffers', 272564224),
          ('cached', 3219124224), ('caches', 4009385984), ('cma_free', 0), ('cma_total', 0),
          ('commit_limit', 9359654912), ('committed_as', 16258154496), ('dirty', 14913536),
          ('hardware_corrupted', 0), ('inactive', 2157494272), ('inactive_anon', 1121906688),
          ('inactive_file', 1035587584), ('kreclaimable', 361406464), ('kernel_stack', 28037120),
          ('mapped', 970366976), ('mem_available', 7177719808), ('mem_free', 4710035456),
          ('mem_total', 16664109056), ('mem_used', 7944687616),
          ('mem_used_percent', 47.675441809110545), ('mlocked', 81920), ('nfs_unstable', 0),
          ('page_tables', 84729856), ('pending', 14913536), ('percpu', 9633792),
          ('sreclaimable', 361406464), ('sunreclaim', 257396736), ('shmem', 934322176),
          ('shmem_huge_pages', 0), ('shmem_pmd_mapped', 0), ('slab', 618803200),
          ('swap_cached', 156291072), ('swap_free', 226992128), ('swap_total', 1027600384),
          ('swap_used', 800608256), ('total_total', 17691709440), ('total_used', 8745295872),
          ('unevictable', 19808256), ('writeback', 0), ('writeback_tmp', 0)], {}),
        ('old', 'mkeventd_status', None, 'heute', '{}', {}, 'OMD heute Event Console', 0,
         'WAITING - Counter based check, cannot be done offline',
         [('num_open_events', 0), ('process_virtual_size', 218300416),
          ('average_message_rate', 0.0), ('average_rule_hit_rate', 0.0),
          ('average_rule_trie_rate', 0.0), ('average_drop_rate', 0.0), ('average_event_rate', 0.0),
          ('average_connect_rate', 0.0), ('average_request_time', 0.00027762370400620984)], {}),
        ('old', 'mkeventd_status', None, 'stable', '{}', {}, 'OMD stable Event Console', 0,
         'WAITING - Counter based check, cannot be done offline',
         [('num_open_events', 0), ('process_virtual_size', 205152256),
          ('average_message_rate', 0.0), ('average_rule_hit_rate', 0.0),
          ('average_rule_trie_rate', 0.0), ('average_drop_rate', 0.0), ('average_event_rate', 0.0),
          ('average_connect_rate', 0.0), ('average_request_time', 0.00039733688471126213)], {}),
        ('old', 'mknotifyd', None, 'heute', '{}', {}, 'OMD heute Notification Spooler', 0,
         'Version: 2020.06.08, Spooler running', [('last_updated', 20), ('new_files', 0)], {}),
        ('old', 'mknotifyd', None, 'stable', '{}', {}, 'OMD stable Notification Spooler', 0,
         'Version: 1.6.0-2020.06.05, Spooler running', [('last_updated', 12),
                                                        ('new_files', 0)], {}),
        ('old', 'mounts', 'fs_mount_options', '/', "['errors=remount-ro', 'relatime', 'rw']",
         ['errors=remount-ro', 'relatime',
          'rw'], 'Mount options of /', 0, 'Mount options exactly as expected', [], {}),
        ('old', 'mounts', 'fs_mount_options', '/boot', "['relatime', 'rw']", ['relatime', 'rw'],
         'Mount options of /boot', 0, 'Mount options exactly as expected', [], {}),
        ('old', 'mounts', 'fs_mount_options', '/boot/efi',
         "['codepage=437', 'dmask=0077', 'errors=remount-ro', 'fmask=0077', 'iocharset=iso8859-1', 'relatime', 'rw', 'shortname=mixed']",
         [
             'codepage=437', 'dmask=0077', 'errors=remount-ro', 'fmask=0077', 'iocharset=iso8859-1',
             'relatime', 'rw', 'shortname=mixed'
         ], 'Mount options of /boot/efi', 0, 'Mount options exactly as expected', [], {}),
        ('old', 'omd_apache', None, 'heute', 'None', None, 'OMD heute apache', 0,
         'WAITING - Counter based check, cannot be done offline', [('requests_images', 0.0),
                                                                   ('requests_cmk_other', 0.0),
                                                                   ('requests_cmk_snapins', 0.0),
                                                                   ('requests_styles', 0.0),
                                                                   ('requests_scripts', 0.0),
                                                                   ('requests_cmk_wato', 0.0),
                                                                   ('requests_cmk_views', 0.0),
                                                                   ('requests_cmk_bi', 0.0),
                                                                   ('requests_cmk_dashboards', 0.0),
                                                                   ('requests_nagvis_snapin', 0.0),
                                                                   ('requests_nagvis_ajax', 0.0),
                                                                   ('requests_nagvis_other', 0.0),
                                                                   ('requests_other', 0.0),
                                                                   ('secs_cmk_other', 0.0),
                                                                   ('secs_cmk_snapins', 0.0),
                                                                   ('secs_scripts', 0.0),
                                                                   ('secs_cmk_wato', 0.0),
                                                                   ('secs_images', 0.0),
                                                                   ('secs_styles', 0.0),
                                                                   ('secs_cmk_views', 0.0),
                                                                   ('secs_cmk_bi', 0.0),
                                                                   ('secs_cmk_dashboards', 0.0),
                                                                   ('secs_nagvis_snapin', 0.0),
                                                                   ('secs_nagvis_ajax', 0.0),
                                                                   ('secs_nagvis_other', 0.0),
                                                                   ('secs_other', 0.0),
                                                                   ('bytes_scripts', 0.0),
                                                                   ('bytes_styles', 0.0),
                                                                   ('bytes_cmk_other', 0.0),
                                                                   ('bytes_cmk_snapins', 0.0),
                                                                   ('bytes_cmk_wato', 0.0),
                                                                   ('bytes_images', 0.0),
                                                                   ('bytes_cmk_views', 0.0),
                                                                   ('bytes_cmk_bi', 0.0),
                                                                   ('bytes_cmk_dashboards', 0.0),
                                                                   ('bytes_nagvis_snapin', 0.0),
                                                                   ('bytes_nagvis_ajax', 0.0),
                                                                   ('bytes_nagvis_other', 0.0),
                                                                   ('bytes_other', 0.0)], {}),
        ('old', 'omd_apache', None, 'stable', 'None', None, 'OMD stable apache', 0,
         'WAITING - Counter based check, cannot be done offline', [('requests_cmk_other', 0.0),
                                                                   ('requests_cmk_views', 0.0),
                                                                   ('requests_cmk_wato', 0.0),
                                                                   ('requests_cmk_bi', 0.0),
                                                                   ('requests_cmk_snapins', 0.0),
                                                                   ('requests_cmk_dashboards', 0.0),
                                                                   ('requests_nagvis_snapin', 0.0),
                                                                   ('requests_nagvis_ajax', 0.0),
                                                                   ('requests_nagvis_other', 0.0),
                                                                   ('requests_images', 0.0),
                                                                   ('requests_styles', 0.0),
                                                                   ('requests_scripts', 0.0),
                                                                   ('requests_other', 0.0),
                                                                   ('secs_cmk_other', 0.0),
                                                                   ('secs_cmk_views', 0.0),
                                                                   ('secs_cmk_wato', 0.0),
                                                                   ('secs_cmk_bi', 0.0),
                                                                   ('secs_cmk_snapins', 0.0),
                                                                   ('secs_cmk_dashboards', 0.0),
                                                                   ('secs_nagvis_snapin', 0.0),
                                                                   ('secs_nagvis_ajax', 0.0),
                                                                   ('secs_nagvis_other', 0.0),
                                                                   ('secs_images', 0.0),
                                                                   ('secs_styles', 0.0),
                                                                   ('secs_scripts', 0.0),
                                                                   ('secs_other', 0.0),
                                                                   ('bytes_cmk_other', 0.0),
                                                                   ('bytes_cmk_views', 0.0),
                                                                   ('bytes_cmk_wato', 0.0),
                                                                   ('bytes_cmk_bi', 0.0),
                                                                   ('bytes_cmk_snapins', 0.0),
                                                                   ('bytes_cmk_dashboards', 0.0),
                                                                   ('bytes_nagvis_snapin', 0.0),
                                                                   ('bytes_nagvis_ajax', 0.0),
                                                                   ('bytes_nagvis_other', 0.0),
                                                                   ('bytes_images', 0.0),
                                                                   ('bytes_styles', 0.0),
                                                                   ('bytes_scripts', 0.0),
                                                                   ('bytes_other', 0.0)], {}),
        ('old', 'systemd_units.services_summary', 'systemd_services_summary', 'Summary', '{}', {
            'states': {
                'active': 0,
                'failed': 2,
                'inactive': 0
            },
            'states_default': 2
        }, 'Systemd Service Summary', 0,
         "138 services in total, Service 'kubelet' activating for: 0.00 s, 5 disabled services", [],
         {}),
        ('old', 'tcp_conn_stats', 'tcp_conn_stats', None, 'tcp_conn_stats_default_levels', {},
         'TCP Connections', 0,
         'CLOSE_WAIT: 5, ESTABLISHED: 13, FIN_WAIT2: 1, LISTEN: 21, SYN_SENT: 1, TIME_WAIT: 108', [
             ('CLOSED', 0, None, None), ('CLOSE_WAIT', 5, None, None), ('CLOSING', 0, None, None),
             ('ESTABLISHED', 13, None, None), ('FIN_WAIT1', 0, None, None),
             ('FIN_WAIT2', 1, None, None), ('LAST_ACK', 0, None, None), ('LISTEN', 21, None, None),
             ('SYN_RECV', 0, None, None), ('SYN_SENT', 1, None, None),
             ('TIME_WAIT', 108, None, None)
         ], {}),
        ('old', 'uptime', 'uptime', None, '{}', {}, 'Uptime', 0,
         'Up since Tue Jun  2 07:50:48 2020, uptime: 7 days, 7:30:46', [('uptime', 631846.94, None,
                                                                         None)], {}),
        ('active', 'cmk_inv', None, 'Check_MK HW/SW Inventory', '{}', {},
         'Check_MK HW/SW Inventory', None, 'WAITING - Active check, cannot be done offline', [], {})
    ],
    'host_labels': {
        'cmk/check_mk_server': {
            'plugin_name': 'labels',
            'value': 'yes'
        }
    },
    'output': "+ FETCHING DATA\n [agent] Using data from cache file /omd/sites/heute/tmp/check_mk/cache/heute\n [agent] Use cached data\n [piggyback] Execute data source\nNo piggyback files for 'heute'. Skip processing.\nNo piggyback files for '127.0.0.1'. Skip processing.\n+ EXECUTING DISCOVERY PLUGINS (29)\nkernel does not support discovery. Skipping it.\n+ EXECUTING HOST LABEL DISCOVERY\n"
}


def test_openapi_discovery(wsgi_app, with_automation_user, suppress_automation_calls):
    username, secret = with_automation_user
    local_automation = suppress_automation_calls.local_automation
    local_automation.return_value = mock_discovery_result
    wsgi_app.set_authorization(('Bearer', username + " " + secret))

    base = '/NO_SITE/check_mk/api/v0'

    _host_created = wsgi_app.call_method(
        'post',
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "foobar", "folder": "/"}',
        status=200,
        content_type='application/json',
    )

    _resp = wsgi_app.call_method(
        'post',
        base +
        "/objects/host/foobar/actions/discover-services/mode/tabula-rasa",
        status=204
    )

    # TODO: Unify and test services collections
