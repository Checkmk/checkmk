#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, NamedTuple, Optional, Tuple

from .agent_based_api.v1 import (
    all_of,
    check_levels,
    exists,
    not_exists,
    register,
    Service,
    SNMPTree,
)
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable


class Section(NamedTuple):
    postfix: int
    incoming: int
    active: int
    deferred: int
    hold: int
    maildrop: int
    z1: int


def parse_zertificon_mail_queues(string_table: StringTable) -> Optional[Section]:
    """
    >>> parse_zertificon_mail_queues([["1", "2", "3", "4", "5", "6", "7"]])
    Section(postfix=1, incoming=2, active=3, deferred=4, hold=5, maildrop=6, z1=7)
    """
    return (
        Section(
            *map(
                int,
                string_table[0],
            )
        )
        if string_table and all(string_table[0])
        else None
    )


register.snmp_section(
    name="zertificon_mail_queues",
    # This condition will never match, therefore, zertificon_mail_queues is only available as an
    # enforced service. This is necessary because Zertificon appliances cannot be decisively
    # identified based on their SNMP data. Hence, no sensible detection condition can be formulated.
    detect=all_of(
        exists(".1.3.6.1.2.1.1.1.0"),
        not_exists(".1.3.6.1.2.1.1.1.0"),
    ),
    fetch=SNMPTree(
        ".1.3.6.1.4.1.2021.8.1.100",
        [
            "5",
            "6",
            "7",
            "8",
            "9",
            "10",
            "17",
        ],
    ),
    parse_function=parse_zertificon_mail_queues,
)


def discover_zertificon_mail_queues(section: Section) -> DiscoveryResult:
    yield Service()


def check_zertificon_mail_queues(
    params: Mapping[str, Tuple[int, int]],
    section: Section,
) -> CheckResult:
    yield from check_levels(
        section.postfix,
        levels_upper=params.get("postfix"),
        metric_name="mail_queue_postfix_total",
        label="Total number of mails in Postfix queue",
        render_func=str,
        boundaries=(0, None),
        notice_only=True,
    )
    yield from check_levels(
        section.incoming,
        levels_upper=params.get("incoming"),
        metric_name="mail_queue_incoming_length",
        label="Incoming mails in queue",
        render_func=str,
        boundaries=(0, None),
        notice_only=True,
    )
    yield from check_levels(
        section.active,
        levels_upper=params.get("active"),
        metric_name="mail_queue_active_length",
        label="Active mails in queue",
        render_func=str,
        boundaries=(0, None),
        notice_only=True,
    )
    yield from check_levels(
        section.deferred,
        levels_upper=params.get("deferred"),
        metric_name="mail_queue_deferred_length",
        label="Deferred mails in queue",
        render_func=str,
        boundaries=(0, None),
        notice_only=True,
    )
    yield from check_levels(
        section.hold,
        levels_upper=params.get("hold"),
        metric_name="mail_queue_hold_length",
        label="Hold mails in queue",
        render_func=str,
        boundaries=(0, None),
        notice_only=True,
    )
    yield from check_levels(
        section.maildrop,
        levels_upper=params.get("maildrop"),
        metric_name="mail_queue_drop_length",
        label="Maildrop mails in queue",
        render_func=str,
        boundaries=(0, None),
        notice_only=True,
    )
    yield from check_levels(
        section.z1,
        levels_upper=params.get("z1"),
        metric_name="mail_queue_z1_messenger",
        label="Z1 Messenger mails in queue",
        render_func=str,
        boundaries=(0, None),
        notice_only=True,
    )


register.check_plugin(
    name="zertificon_mail_queues",
    service_name="Zertificon Mail Queues",
    discovery_function=discover_zertificon_mail_queues,
    check_function=check_zertificon_mail_queues,
    check_default_parameters={},
    check_ruleset_name="zertificon_mail_queues",
)
