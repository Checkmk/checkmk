#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping

from cmk.utils.rulesets.ruleset_matcher import RuleConditionsSpec, RuleOptionsSpec, RuleSpec

_CMK_SERVER_CONDITION = RuleConditionsSpec(
    host_label_groups=[("and", [("and", "cmk/check_mk_server:yes"), ("and", "")])]
)

_SHIPPED_RULE_OPTIONS = RuleOptionsSpec(
    disabled=False,
    comment=(
        "This rule is shipped with Checkmk."
        " It is added to give insights on the resource usage of Checkmk servers."
        " If you do not want these services, consider disabling this rule, rather than deleting it."
        " If you delete all of these rules, they might come back after an update.\n"
    ),
)

_PS_COMMON_OPTS = {"user": False, "default_params": {"cpu_rescale_max": True}}

PS_DISCOVERY_RULES: list[RuleSpec[Mapping[str, object]]] = [  # sorted by descr
    {
        "id": id_,
        "value": {"descr": f"%u {ps_name}", "match": match, **_PS_COMMON_OPTS},
        "condition": _CMK_SERVER_CONDITION,
        "options": {
            "description": f"Shipped rule to monitor sites {ps_name}",
            **_SHIPPED_RULE_OPTIONS,
        },
    }
    for id_, ps_name, match in [
        (
            "94a0ead4-a9d8-428d-8b06-10b9f3b5fe26",
            "active check helpers",
            "~/omd/sites/[^/]+/lib/cmc/checkhelper",
        ),
        (
            "94190e27-2836-488a-b6b4-e13f694a455e",
            "agent receiver",
            "~gunicorn:.*cmk.agent_receiver",
        ),
        (
            "6b3a78b3-b4e9-4aca-b427-2f656809bf49",
            "alert helper",
            "~python3 /omd/sites/[^/]+/bin/cmk --handle-alerts",
        ),
        (
            "7eda3d76-62ff-4ff6-b84b-a26ce202c577",
            "apache",
            "~.*/omd/sites/[^/]+/etc/apache/apache.conf$",
        ),
        (
            "94190e27-2836-488a-b6b4-f23f694a455e",
            "automation helpers",
            "~.*cmk-automation-helper.*",
        ),
        (
            "feaa2248-08b8-47a3-bc3c-a5502d2b9f3a",
            "checker helpers",
            "~python3 /omd/sites/[^/]+/bin/cmk .*--checker",
        ),
        (
            "9440a0b2-5eb2-4f52-ac4b-17c6ddecd1f2",
            "cmc",
            "~/omd/sites/[^/]+/bin/cmc",
        ),
        (
            "f56e8b7a-98f0-4597-a030-1f1f6dc2347d",
            "dcd",
            "~dcd",
        ),
        (
            "2105c8a7-5672-4242-98f6-fd6ce8b8f3a7",
            "event console",
            "~python3 /omd/sites/[^/]+/bin/mkeventd$",
        ),
        (
            "0846dd4c-cc62-4adf-9400-7f20a651f996",
            "fetcher helpers",
            "~python3 /omd/sites/[^/]+/bin/fetcher",
        ),
        (
            "9e123cf5-3717-47a1-ba7a-b00f9ede3435",
            "jaeger",
            "~/omd/sites/[^/]+/bin/jaeger",
        ),
        (
            "df8832aa-3054-4a62-96b8-d960381e6726",
            "livestatus proxy",
            "~liveproxyd",
        ),
        (
            "f64f23d9-55c5-490c-a7dd-b38a108155e2",
            "notification spooler",
            "~python3 /omd/sites/[^/]+/bin/mknotifyd$",
        ),
        (
            "459dd81c-cd2c-40bb-ac43-d25440778e7a",
            "notify helper",
            "~python3 /omd/sites/[^/]+/bin/cmk --notify --keepalive$",
        ),
        (
            "aa86dbc4-c390-48f7-b0ed-44231aa79b7c",
            "piggyback hub",
            "~python3 /omd/sites/[^/]+/bin/cmk-piggyback-hub",
        ),
        (
            "65a3dca4-8d71-45d8-8887-53ef0c63d06f",
            "rabbitmq",
            "~(?:.*bin/rabbitmq-server)",
        ),
        (
            "b0d6dc83-fd0e-4382-921b-94415b353eaf",
            "real-time helper",
            "~python3 /omd/sites/[^/]+/bin/cmk --real-time-checks",
        ),
        (
            "33e44415-a74c-4146-a6c7-65473eff71ca",
            "redis-server",
            "~/omd/sites/[^/]+/bin/redis-server",
        ),
        (
            "0bd2b6cc-bc5c-4244-9658-928870f68f35",
            "rrd helper",
            "~python3 /omd/sites/[^/]+/bin/cmk( -)?-create-rrd",
        ),
        (
            "bf1601b9-69bb-4f1d-8384-e5e057069656",
            "rrdcached",
            "~/omd/sites/[^/]+/bin/rrdcached",
        ),
    ]
]


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
            "condition": _CMK_SERVER_CONDITION,
            "value": {
                "ignore_fs_types": ["tmpfs", "nfs", "smbfs", "cifs", "iso9660"],
                "never_ignore_mountpoints": ["~.*/omd/sites/[^/]+/tmp$"],
            },
        },
    ],
    "inventory_processes_rules": PS_DISCOVERY_RULES,
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
