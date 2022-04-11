#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Create an initial Checkmk configuration for new sites"""

import os
from datetime import datetime
from typing import Any, Dict

from cmk.utils import store
from cmk.utils.encryption import raw_certificates_from_file
from cmk.utils.paths import site_cert_file
from cmk.utils.tags import sample_tag_config, TagConfig
from cmk.utils.type_defs import EventRule

from cmk.gui.log import logger
from cmk.gui.plugins.watolib.utils import sample_config_generator_registry, SampleConfigGenerator
from cmk.gui.userdb import create_cmk_automation_user
from cmk.gui.watolib.config_domains import ConfigDomainCACertificates
from cmk.gui.watolib.global_settings import save_global_settings
from cmk.gui.watolib.groups import AllGroupSpecs, GroupName, save_group_information
from cmk.gui.watolib.hosts_and_folders import Folder
from cmk.gui.watolib.notifications import save_notification_rules
from cmk.gui.watolib.rulesets import FolderRulesets
from cmk.gui.watolib.tags import TagConfigFile
from cmk.gui.watolib.utils import multisite_dir, wato_root_dir


# TODO: Must only be unlocked when it was not locked before. We should find a more
# robust way for doing something like this. If it is locked before, it can now happen
# that this call unlocks the wider locking when calling this funktion in a wrong way.
def init_wato_datastructures(with_wato_lock: bool = False) -> None:
    if (
        os.path.exists(ConfigDomainCACertificates.trusted_cas_file)
        and not _need_to_create_sample_config()
    ):
        return

    def init():
        if not os.path.exists(ConfigDomainCACertificates.trusted_cas_file):
            ConfigDomainCACertificates().activate()
        _create_sample_config()

    if with_wato_lock:
        with store.lock_checkmk_configuration():
            init()
    else:
        init()


def _need_to_create_sample_config() -> bool:
    if (
        os.path.exists(multisite_dir() + "tags.mk")
        or os.path.exists(wato_root_dir() + "rules.mk")
        or os.path.exists(wato_root_dir() + "groups.mk")
        or os.path.exists(wato_root_dir() + "notifications.mk")
        or os.path.exists(wato_root_dir() + "global.mk")
    ):
        return False
    return True


def _create_sample_config() -> None:
    """Create a very basic sample configuration

    But only if none of the files that we will create already exists. That is
    e.g. the case after an update from an older version where no sample config
    had been created.
    """
    if not _need_to_create_sample_config():
        return

    logger.debug("Start creating the sample config")
    for generator in sample_config_generator_registry.get_generators():
        try:
            logger.debug("Starting [%s]", generator.ident())
            generator.generate()
            logger.debug("Finished [%s]", generator.ident())
        except Exception:
            logger.exception("Exception in sample config generator [%s]", generator.ident())

    logger.debug("Finished creating the sample config")


@sample_config_generator_registry.register
class ConfigGeneratorBasicWATOConfig(SampleConfigGenerator):
    @classmethod
    def ident(cls) -> str:
        return "basic_wato_config"

    @classmethod
    def sort_index(cls) -> int:
        return 10

    def generate(self) -> None:
        save_global_settings(self._initial_global_settings())

        # A contact group for all hosts and services
        groups: AllGroupSpecs = {
            "contact": {GroupName("all"): {"alias": "Everything"}},
        }
        save_group_information(groups)

        self._initialize_tag_config()

        # Rules that match the upper host tag definition
        ruleset_config = {
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
                    "options": {
                        "description": "Allow longer round trip times when pinging WAN hosts"
                    },
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
                    "options": {
                        "description": 'Hosts with the tag "snmp-v1" must not use bulkwalk'
                    },
                },
            ],
            # All SNMP managment boards should use SNMP v2c if not specially tagged
            "management_bulkwalk_hosts": [
                {
                    "id": "59d84cde-ee3a-4f8d-8bec-fce35a2b0d15",
                    "condition": {},
                    "value": True,
                    "options": {
                        "description": "All management boards use SNMP v2 (incl. bulk walks) by default"
                    },
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
                    "condition": {"host_labels": {"cmk/docker_object": "container"}},
                    "value": ("service", "Docker container status"),
                    "options": {
                        "description": 'Make all docker container host states base on the "Docker container status" service',
                    },
                },
            ],
            # Enable HW/SW inventory + status data inventory for docker
            # containers, kubernetes objects and Check-MK servers by default to
            # simplify the setup procedure for them
            "active_checks": {
                "cmk_inv": [
                    {
                        "id": "7ba2ac2a-5a49-47ce-bc3c-1630fb191c7f",
                        "condition": {
                            "host_labels": {
                                "cmk/docker_object": "node",
                            }
                        },
                        "value": {"status_data_inventory": True},
                    },
                    {
                        "id": "b4b151f9-c7cc-4127-87a6-9539931fcd73",
                        "condition": {
                            "host_labels": {
                                "cmk/check_mk_server": "yes",
                            }
                        },
                        "value": {"status_data_inventory": True},
                    },
                    {
                        "id": "2527cb37-e9da-4a15-a7d9-80825a7f6661",
                        "condition": {
                            "host_labels": {
                                "cmk/kubernetes": "yes",
                            }
                        },
                        "value": {"status_data_inventory": True},
                    },
                ]
            },
            # Interval for HW/SW-Inventory check
            "extra_service_conf": {
                "check_interval": [
                    {
                        "id": "b3847203-84b3-4f5b-ac67-0f06d4403905",
                        "condition": {
                            "service_description": [{"$regex": "Check_MK HW/SW Inventory$"}]
                        },
                        "value": 1440,
                        "options": {"description": "Restrict HW/SW-Inventory to once a day"},
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
                    "condition": {
                        "host_labels": {
                            "cmk/check_mk_server": "yes",
                        },
                    },
                    "value": {
                        "ignore_fs_types": ["tmpfs", "nfs", "smbfs", "cifs", "iso9660"],
                        "never_ignore_mountpoints": ["~.*/omd/sites/[^/]+/tmp$"],
                    },
                },
            ],
        }

        rulesets = FolderRulesets(Folder.root_folder())
        rulesets.load()
        rulesets.from_config(Folder.root_folder(), ruleset_config)
        rulesets.save()

        notification_rules = [
            EventRule(
                allow_disable=True,
                contact_all=False,
                contact_all_with_email=False,
                contact_object=True,
                description="Notify all contacts of a host/service via HTML email",
                disabled=False,
                notify_plugin=("mail", {}),
            ),
        ]
        save_notification_rules(notification_rules)

    def _initial_global_settings(self) -> Dict[str, Any]:
        settings = {
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
                "megraid_vdisks",
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
            "enable_rulebased_notifications": True,
            "log_logon_failures": True,
            "lock_on_logon_failures": 10,
            "trusted_certificate_authorities": {
                "use_system_wide_cas": True,
                # Add the CA of the site to the trusted CAs. This has the benefit that remote sites
                # automatically trust central sites in distributed setups where the config is replicated.
                "trusted_cas": (
                    (site_cas := raw_certificates_from_file(site_cert_file))
                    and [site_cas[-1]]
                    or []
                ),
            },
        }

        return settings

    def _initialize_tag_config(self) -> None:
        tag_config = TagConfig.from_config(sample_tag_config())
        TagConfigFile().save(tag_config.get_dict_format())


@sample_config_generator_registry.register
class ConfigGeneratorAcknowledgeInitialWerks(SampleConfigGenerator):
    """This is not really the correct place for such kind of action, but the best place we could
    find to execute it only for new created sites."""

    @classmethod
    def ident(cls) -> str:
        return "acknowledge_initial_werks"

    @classmethod
    def sort_index(cls) -> int:
        return 40

    def generate(self) -> None:
        # Local import has been added to quick-fix an import cycle between cmk.gui.werks and watolib
        import cmk.gui.werks as werks

        werks.acknowledge_all_werks(check_permission=False)


@sample_config_generator_registry.register
class ConfigGeneratorAutomationUser(SampleConfigGenerator):
    """Create the default Checkmk "automation" user"""

    @classmethod
    def ident(cls) -> str:
        return "create_automation_user"

    @classmethod
    def sort_index(cls) -> int:
        return 60

    def generate(self) -> None:
        create_cmk_automation_user(datetime.now())
