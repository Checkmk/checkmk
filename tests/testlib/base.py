#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Dict

from tests.testlib.utils import get_standard_linux_agent_output

import cmk.utils.tags

import cmk.base.autochecks as autochecks
import cmk.base.config as config


class _AutochecksMocker:
    def __init__(self):
        self.autochecks = {}

    def get_autochecks_of(
        self, hostname, compute_check_parameters, service_description, get_effective_hostname
    ):
        return [
            autochecks.Service(
                s.check_plugin_name,
                s.item,
                s.description,
                compute_check_parameters(
                    get_effective_hostname(hostname, s.description),
                    s.check_plugin_name,
                    s.item,
                    s.parameters,
                ),
                s.service_labels,
            )
            for s in self.autochecks.get(hostname, ())
        ]

    def discovered_labels_of(self, hostname, service_descr, get_service_description):
        try:
            return {
                service.description: service.service_labels
                for service in self.autochecks.get(hostname, ())
            }[service_descr]
        except KeyError:
            return {}


class Scenario:
    """Helper class to modify the Check_MK base configuration for unit tests"""

    def __init__(self, site_id="unit"):
        super().__init__()

        tag_config = cmk.utils.tags.sample_tag_config()
        self.tags = cmk.utils.tags.get_effective_tag_config(tag_config)
        self.site_id = site_id
        self._autochecks_mocker = _AutochecksMocker()

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

    def add_host(
        self, hostname, tags=None, host_path="/wato/hosts.mk", labels=None, ipaddress=None
    ):
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

        if ipaddress is not None:
            self.config.setdefault("ipaddresses", {})[hostname] = ipaddress

        return self

    def fake_standard_linux_agent_output(self, *test_hosts):
        self.set_ruleset(
            "datasource_programs",
            [
                ("cat %s/<HOST>" % cmk.utils.paths.tcp_cache_dir, [], test_hosts, {}),
            ],
        )
        linux_agent_output = get_standard_linux_agent_output()

        for h in test_hosts:
            cache_path = Path(cmk.utils.paths.tcp_cache_dir, h)
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with cache_path.open("w", encoding="utf-8") as f:
                f.write(linux_agent_output)

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
            "piggyback": "auto-piggyback",
            "networking": "lan",
            "agent": "cmk-agent",
            "criticality": "prod",
            "snmp_ds": "no-snmp",
            "site": self.site_id,
            "address_family": "ip-v4-only",
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
        # these services have no real counterpart in the code:
        #  * the description is used as given
        #    (bypassing the get_service_description callback)
        #  * the parameters are processed according to the config
        #    (calling config.compute_check_parameters)
        self._autochecks_mocker.autochecks[hostname] = services

    def apply(self, monkeypatch):
        check_vars: Dict = {}
        for key, value in self.config.items():
            if key in config._check_variables:
                check_vars.setdefault(key, value)
                continue
            monkeypatch.setattr(config, key, value)

        self.config_cache = config.get_config_cache()
        self.config_cache.initialize()
        config.set_check_variables(check_vars)

        if self._autochecks_mocker.autochecks:
            monkeypatch.setattr(
                self.config_cache,
                "_autochecks_manager",
                self._autochecks_mocker,
                raising=False,
            )

        return self.config_cache
