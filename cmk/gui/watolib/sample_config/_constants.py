#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# Rules that match the host tag definition from `sample_tag_config`
SHIPPED_RULES = {
    # Make the tag 'offline' remove hosts from the monitoring
    "only_hosts": [
        {
            "id": "10843c55-11ea-4eb2-bfbc-bce65cd2ae22",
            "condition": {"host_tags": {"criticality": {"$ne": "offline"}}},
            "value": True,
            "options": {"description": 'Do not monitor hosts with the tag "offline"'},
        },
    ],
    # Rule for WAN hosts with adapted PING levels
    "ping_levels": [
        {
            "id": "0365b634-30bf-40a3-8516-08e86051508e",
            "condition": {
                "host_tags": {
                    "networking": "wan",
                }
            },
            "value": {
                "loss": (80.0, 100.0),
                "packets": 6,
                "timeout": 20,
                "rta": (1500.0, 3000.0),
            },
            "options": {"description": "Allow longer round trip times when pinging WAN hosts"},
        },
    ],
    # All hosts should use SNMP v2c if not specially tagged
    "bulkwalk_hosts": [
        {
            "id": "b92a5406-1d57-4f1d-953d-225b111239e5",
            "condition": {
                "host_tags": {
                    "snmp": "snmp",
                    "snmp_ds": {"$ne": "snmp-v1"},
                },
            },
            "value": True,
            "options": {"description": 'Hosts with the tag "snmp-v1" must not use bulkwalk'},
        },
    ],
    # All SNMP managment boards should use SNMP v2c if not specially tagged
    "management_bulkwalk_hosts": [
        {
            "id": "59d84cde-ee3a-4f8d-8bec-fce35a2b0d15",
            "condition": {},
            "value": True,
            "options": {"description": "All management boards use SNMPv2 and bulk walk"},
        },
    ],
    # Put all hosts and the contact group 'all'
    "host_contactgroups": [
        {
            "id": "efd67dab-68f8-4d3c-a417-9f7e29ab48d5",
            "condition": {},
            "value": "all",
            "options": {"description": 'Put all hosts into the contact group "all"'},
        },
    ],
    # Docker container specific host check commands
    "host_check_commands": [
        {
            "id": "24da4ccd-0d1b-40e3-af87-0097df8668f2",
            "condition": {"host_label_groups": [("and", [("and", "cmk/docker_object:container")])]},
            "value": ("service", "Docker container status"),
            "options": {
                "description": 'Make all docker container host states base on the "Docker container status" service',
            },
        },
    ],
    # Enable HW/SW Inventory + status data inventory for docker
    # containers, kubernetes objects, robotmk and Check-MK servers by default to
    # simplify the setup procedure for them
    "active_checks": {
        "cmk_inv": [
            {
                "id": "7ba2ac2a-5a49-47ce-bc3c-1630fb191c7f",
                "condition": {"host_label_groups": [("and", [("and", "cmk/docker_object:node")])]},
                "value": {"status_data_inventory": True},
                "options": {
                    "description": "Factory default. Required for the shipped dashboards.",
                },
            },
            {
                "id": "b4b151f9-c7cc-4127-87a6-9539931fcd73",
                "condition": {"host_label_groups": [("and", [("and", "cmk/check_mk_server:yes")])]},
                "value": {"status_data_inventory": True},
                "options": {
                    "description": "Factory default. Required for the shipped dashboards.",
                },
            },
            {
                "id": "2527cb37-e9da-4a15-a7d9-80825a7f6661",
                "condition": {"host_label_groups": [("and", [("and", "cmk/kubernetes:yes")])]},
                "value": {"status_data_inventory": True},
                "options": {
                    "description": "Factory default. Required for the shipped dashboards.",
                },
            },
            {
                "id": "bea23477-f13a-4e9f-a472-08be507aac9e",
                "condition": {"host_label_groups": [("and", [("and", "cmk/rmk/node_type:local")])]},
                "value": {"status_data_inventory": True},
                "options": {
                    "description": "Factory default. Required for the shipped dashboards.",
                },
            },
        ]
    },
    # Interval for HW/SW Inventory check
    "extra_service_conf": {
        "check_interval": [
            {
                "id": "b3847203-84b3-4f5b-ac67-0f06d4403905",
                "condition": {"service_description": [{"$regex": "Check_MK HW/SW Inventory$"}]},
                "value": 1440,
                "options": {"description": "Restrict HW/SW Inventory to once a day"},
            },
        ],
    },
    # Disable unreachable notifications by default
    "extra_host_conf": {
        "notification_options": [
            {
                "id": "814bf932-6341-4f96-983d-283525b5416d",
                "condition": {},
                "value": "d,r,f,s",
            },
        ],
    },
    # Periodic service discovery
    "periodic_discovery": [
        {
            "id": "95a56ffc-f17e-44e7-a162-be656f19bedf",
            "condition": {},
            "value": {
                "severity_unmonitored": 1,
                "severity_changed_service_labels": 0,
                "severity_changed_service_params": 0,
                "severity_vanished": 0,
                "severity_new_host_label": 1,
                "check_interval": 120.0,
            },
            "options": {"description": "Perform every two hours a service discovery"},
        },
    ],
    # Include monitoring of checkmk's tmpfs
    "inventory_df_rules": [
        {
            "id": "b0ee8a51-703c-47e4-aec4-76430281604d",
            "condition": {"host_label_groups": [("and", [("and", "cmk/check_mk_server:yes")])]},
            "value": {
                "ignore_fs_types": ["tmpfs", "nfs", "smbfs", "cifs", "iso9660"],
                "never_ignore_mountpoints": ["~.*/omd/sites/[^/]+/tmp$"],
            },
        },
    ],
}


USE_NEW_DESCRIPTIONS_FOR_SETTING = {
    "use_new_descriptions_for": [
        "aix_memory",
        "barracuda_mailqueues",
        "brocade_sys_mem",
        "casa_cpu_temp",
        "cisco_mem",
        "cisco_mem_asa",
        "cisco_mem_asa64",
        "cmciii_psm_current",
        "cmciii_temp",
        "cmciii_lcp_airin",
        "cmciii_lcp_airout",
        "cmciii_lcp_water",
        "cmk_inventory",
        "db2_mem",
        "df",
        "df_netapp",
        "df_netapp32",
        "docker_container_mem",
        "enterasys_temp",
        "esx_vsphere_datastores",
        "esx_vsphere_hostsystem_mem_usage",
        "esx_vsphere_hostsystem_mem_usage_cluster",
        "etherbox_temp",
        "fortigate_memory",
        "fortigate_memory_base",
        "fortigate_node_memory",
        "hr_fs",
        "hr_mem",
        # TODO: can be removed when
        #  cmk.update_config.plugins.actions.rulesets._force_old_http_service_description
        #  can be removed
        "http",
        "huawei_switch_mem",
        "hyperv_vms",
        "ibm_svc_mdiskgrp",
        "ibm_svc_system",
        "ibm_svc_systemstats_cache",
        "ibm_svc_systemstats_disk_latency",
        "ibm_svc_systemstats_diskio",
        "ibm_svc_systemstats_iops",
        "innovaphone_mem",
        "innovaphone_temp",
        "juniper_mem",
        "juniper_screenos_mem",
        "juniper_trpz_mem",
        "liebert_bat_temp",
        "logwatch",
        "logwatch_groups",
        "mem_used",
        "mem_win",
        "megaraid_bbu",
        "megaraid_pdisks",
        "megaraid_ldisks",
        "megaraid_vdisks",
        "mknotifyd",
        "mknotifyd_connection",
        "mssql_backup",
        "mssql_blocked_sessions",
        "mssql_counters_cache_hits",
        "mssql_counters_file_sizes",
        "mssql_counters_locks",
        "mssql_counters_locks_per_batch",
        "mssql_counters_pageactivity",
        "mssql_counters_sqlstats",
        "mssql_counters_transactions",
        "mssql_databases",
        "mssql_datafiles",
        "mssql_tablespaces",
        "mssql_transactionlogs",
        "mssql_versions",
        "netscaler_mem",
        "nullmailer_mailq",
        "prism_alerts",
        "prism_containers",
        "prism_info",
        "prism_storage_pools",
        "nvidia_temp",
        "postfix_mailq",
        "ps",
        "qmail_stats",
        "raritan_emx",
        "raritan_pdu_inlet",
        "services",
        "solaris_mem",
        "sophos_memory",
        "statgrab_mem",
        "tplink_mem",
        "ups_bat_temp",
        "vms_diskstat_df",
        "wmic_process",
        "zfsget",
    ],
}
