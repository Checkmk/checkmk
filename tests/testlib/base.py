#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

from _pytest.monkeypatch import MonkeyPatch

from tests.testlib.utils import get_standard_linux_agent_output

import cmk.utils.tags
from cmk.utils.type_defs import HostAddress, HostName

import cmk.base.config as config
from cmk.base import autochecks


class _AutochecksMocker(autochecks.AutochecksManager):
    def __init__(self):
        super().__init__()
        self.raw_autochecks: dict[HostName, Sequence[autochecks.AutocheckEntry]] = {}

    def _read_raw_autochecks(self, hostname: HostName) -> Sequence[autochecks.AutocheckEntry]:
        return self.raw_autochecks.get(hostname, [])


class Scenario:
    """Helper class to modify the Check_MK base configuration for unit tests"""

    @staticmethod
    def _get_config_cache() -> config.ConfigCache:
        cc = config.get_config_cache()
        assert isinstance(cc, config.ConfigCache)
        return cc

    def __init__(self, site_id: str = "unit") -> None:
        super().__init__()

        tag_config = cmk.utils.tags.sample_tag_config()
        self.tags = cmk.utils.tags.get_effective_tag_config(tag_config)
        self.site_id = site_id
        self._autochecks_mocker = _AutochecksMocker()

        self.config: dict[str, Any] = {
            "tag_config": tag_config,
            "distributed_wato_site": site_id,
            "all_hosts": [],
            "host_paths": {},
            "host_tags": {},
            "host_labels": {},
            "clusters": {},
        }
        self.config_cache = self._get_config_cache()

    def add_host(
        self,
        hostname: HostName,
        tags: Optional[dict[str, str]] = None,
        host_path: str = "/wato/hosts.mk",
        labels: Optional[dict[str, str]] = None,
        ipaddress: Optional[HostAddress] = None,
    ) -> None:
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

    def fake_standard_linux_agent_output(self, *test_hosts: str) -> None:
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

    def add_cluster(
        self,
        hostname: HostName,
        tags: Optional[dict[str, str]] = None,
        host_path: str = "/wato/hosts.mk",
        nodes: Optional[Sequence[HostName]] = None,
    ) -> None:
        if tags is None:
            tags = {}
        assert isinstance(tags, dict)

        if nodes is None:
            nodes = []

        self.config["clusters"][hostname] = nodes
        self.config["host_paths"][hostname] = host_path
        self.config["host_tags"][hostname] = self._get_effective_tag_config(tags)

    # TODO: This immitates the logic of cmk.gui.watolib.CREHost.tag_groups which
    # is currently responsible for calulcating the host tags of a host.
    # Would be better to untie the GUI code there and move it over to cmk.utils.tags.
    def _get_effective_tag_config(self, tags: Mapping[str, str]) -> Mapping[str, str]:
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

    def set_option(self, varname, option) -> None:
        self.config[varname] = option

    def set_ruleset(self, varname, ruleset) -> None:
        self.config[varname] = ruleset

    def set_autochecks(
        self, hostname: HostName, entries: Sequence[autochecks.AutocheckEntry]
    ) -> None:
        self._autochecks_mocker.raw_autochecks[hostname] = entries

    def apply(self, monkeypatch: MonkeyPatch) -> config.ConfigCache:
        check_vars: Dict = {}
        for key, value in self.config.items():
            if key in config._check_variables:
                check_vars.setdefault(key, value)
                continue
            monkeypatch.setattr(config, key, value)

        self.config_cache = self._get_config_cache()
        self.config_cache.initialize()
        config.set_check_variables(check_vars)

        if self._autochecks_mocker.raw_autochecks:
            monkeypatch.setattr(
                self.config_cache,
                "_autochecks_manager",
                self._autochecks_mocker,
                raising=False,
            )

        return self.config_cache


class CEEScenario(Scenario):
    """Helper class to modify the Check_MK base configuration for unit tests"""

    @staticmethod
    def _get_config_cache() -> config.CEEConfigCache:
        cc = config.get_config_cache()
        assert isinstance(cc, config.CEEConfigCache)
        return cc

    def apply(self, monkeypatch: MonkeyPatch) -> config.CEEConfigCache:
        cc = super().apply(monkeypatch)
        assert isinstance(cc, config.CEEConfigCache)
        return cc
