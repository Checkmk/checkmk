#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterable, Mapping

from cmk.ccc.hostaddress import HostName

from cmk.gui.i18n import _

from .host_attributes import HostAttributes
from .hosts_and_folders import CollectedHostAttributes
from .search import (
    ABCMatchItemGenerator,
    MatchItem,
    MatchItems,
)


class MatchItemGeneratorHosts(ABCMatchItemGenerator):
    def __init__(
        self,
        name: str,
        host_collector: Callable[[], Mapping[HostName, CollectedHostAttributes]],
    ) -> None:
        super().__init__(name)
        self._host_collector = host_collector

    @staticmethod
    def _get_additional_match_texts(host_attributes: HostAttributes) -> Iterable[str]:
        yield from (
            val
            for val in [
                host_attributes["alias"],
                host_attributes["ipaddress"],
                host_attributes["ipv6address"],
            ]
            if val
        )
        yield from (
            str(ip_address)
            for ip_addresses in [
                host_attributes["additional_ipv4addresses"],
                host_attributes["additional_ipv6addresses"],
            ]
            for ip_address in ip_addresses
        )

    def generate_match_items(self) -> MatchItems:
        yield from (
            MatchItem(
                title=host_name,
                topic=_("Hosts"),
                url=host_attributes["edit_url"],
                match_texts=[
                    host_name,
                    *self._get_additional_match_texts(host_attributes),
                ],
            )
            for host_name, host_attributes in self._host_collector().items()
        )

    @staticmethod
    def is_affected_by_change(change_action_name: str) -> bool:
        return "host" in change_action_name

    @property
    def is_localization_dependent(self) -> bool:
        return False
