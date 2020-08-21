#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.base.config as config
import cmk.base.autochecks as autochecks
import cmk.utils.tags

KNOWN_AUTO_MIGRATION_FAILURES = [
    # this is a list of auto conversions currently
    # failing. These are used in various tests, to predict the
    # expected console output. In an ideal world, this list will (!)
    # be empty. If that is the case, please remove it entirely.
    ('section', 'if'),
    ('section', 'if64'),
    ('section', 'if64adm'),
    ('section', 'if_brocade'),
    ('section', 'if_fortigate'),
    ('section', 'if_lancom'),
    ('section', 'juniper_trpz_aps'),
    ('section', 'juniper_trpz_aps_sessions'),
    ('section', 'logwatch'),
    ('section', 'mssql_counters'),
    ('section', 'netscaler_sslcertificates'),
    ('section', 'netscaler_vserver'),
    ('section', 'oracle_asm_diskgroup'),
    ('section', 'oracle_rman'),
    ('section', 'oracle_tablespaces'),
    ('section', 'printer_pages'),
    ('section', 'services'),
    ('section', 'site_object_status'),
    ('section', 'site_object_counts'),
    ('section', 'tsm_stagingpools'),
    ('check', 'docker_container_status'),
    ('check', 'docker_container_status_health'),
    ('check', 'docker_container_status_uptime'),
    ('check', 'if64'),
    ('check', 'if64adm'),
    ('check', 'if_fortigate'),
    ('check', 'ipmi'),
    ('check', 'juniper_trpz_aps'),
    ('check', 'juniper_trpz_aps_sessions'),
    ('check', 'k8s_stats_fs'),
    ('check', 'k8s_stats_network'),
    ('check', 'livestatus_status'),
    ('check', 'logwatch'),
    ('check', 'logwatch_ec'),
    ('check', 'logwatch_ec_single'),
    ('check', 'logwatch_groups'),
    ('check', 'mssql_counters'),
    ('check', 'mssql_counters_cache_hits'),
    ('check', 'mssql_counters_file_sizes'),
    ('check', 'mssql_counters_locks'),
    ('check', 'mssql_counters_locks_per_batch'),
    ('check', 'mssql_counters_pageactivity'),
    ('check', 'mssql_counters_sqlstats'),
    ('check', 'mssql_counters_transactions'),
    ('check', 'netapp_api_vf_stats'),
    ('check', 'netapp_api_vf_stats_traffic'),
    ('check', 'netscaler_sslcertificates'),
    ('check', 'netscaler_vserver'),
    ('check', 'oracle_asm_diskgroup'),
    ('check', 'oracle_rman'),
    ('check', 'oracle_tablespaces'),
    ('check', 'ps_perf'),
    ('check', 'services'),
    ('check', 'services_summary'),
    ('check', 'site_object_counts'),
    ('check', 'tsm_stagingpools'),
]


class Scenario:
    """Helper class to modify the Check_MK base configuration for unit tests"""
    def __init__(self, site_id="unit"):
        super(Scenario, self).__init__()

        tag_config = cmk.utils.tags.sample_tag_config()
        self.tags = cmk.utils.tags.get_effective_tag_config(tag_config)
        self.site_id = site_id
        self._autochecks = {}

        self.config = {
            "tag_config": tag_config,
            "distributed_wato_site": site_id,
            "all_hosts": [],
            "host_paths": {},
            "host_tags": {},
            "host_labels": {},
            "clusters": {},
        }
        self.config_cache = config.get_config_cache()

    def add_host(self, hostname, tags=None, host_path="/wato/hosts.mk", labels=None):
        if tags is None:
            tags = {}
        assert isinstance(tags, dict)

        if labels is None:
            labels = {}
        assert isinstance(labels, dict)

        self.config["all_hosts"].append(hostname)
        self.config["host_paths"][hostname] = host_path
        self.config["host_tags"][hostname] = self._get_effective_tag_config(tags)
        self.config["host_labels"][hostname] = labels
        return self

    def add_cluster(self, hostname, tags=None, host_path="/wato/hosts.mk", nodes=None):
        if tags is None:
            tags = {}
        assert isinstance(tags, dict)

        if nodes is None:
            nodes = []

        self.config["clusters"][hostname] = nodes
        self.config["host_paths"][hostname] = host_path
        self.config["host_tags"][hostname] = self._get_effective_tag_config(tags)
        return self

    # TODO: This immitates the logic of cmk.gui.watolib.CREHost.tag_groups which
    # is currently responsible for calulcating the host tags of a host.
    # Would be better to untie the GUI code there and move it over to cmk.utils.tags.
    def _get_effective_tag_config(self, tags):
        """Returns a full set of tag groups

        It contains the merged default tag groups and their default values
        overwritten by the given tags.

        Auxiliary tags will be added automatically.
        """

        # TODO: Compute this dynamically with self.tags
        tag_config = {
            'piggyback': 'auto-piggyback',
            'networking': 'lan',
            'agent': 'cmk-agent',
            'criticality': 'prod',
            'snmp_ds': 'no-snmp',
            'site': self.site_id,
            'address_family': 'ip-v4-only',
        }
        tag_config.update(tags)

        # NOTE: tag_config is modified within loop!
        for tg_id, tag_id in list(tag_config.items()):
            if tg_id == "site":
                continue

            tag_group = self.tags.get_tag_group(tg_id)
            if tag_group is None:
                raise Exception("Unknown tag group: %s" % tg_id)

            if tag_id not in tag_group.get_tag_ids():
                raise Exception("Unknown tag ID %s in tag group %s" % (tag_id, tg_id))

            tag_config.update(tag_group.get_tag_group_config(tag_id))

        return tag_config

    def set_option(self, varname, option):
        self.config[varname] = option
        return self

    def set_ruleset(self, varname, ruleset):
        self.config[varname] = ruleset
        return self

    def set_autochecks(self, hostname, services):
        self._autochecks[hostname] = services

    def apply(self, monkeypatch):
        for key, value in self.config.items():
            monkeypatch.setattr(config, key, value)

        self.config_cache = config.get_config_cache()
        self.config_cache.initialize()

        if self._autochecks:
            # TODO: This monkeypatching is horrible, it totally breaks any abstraction!
            monkeypatch.setattr(self.config_cache._autochecks_manager,
                                "_raw_autochecks",
                                dict(self._autochecks.items()),
                                raising=False)

            monkeypatch.setattr(
                autochecks.AutochecksManager, "_read_raw_autochecks_uncached",
                lambda self, hostname, service_description: self._raw_autochecks.get(hostname, []))

        return self.config_cache
