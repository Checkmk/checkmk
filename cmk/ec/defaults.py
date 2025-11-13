#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Defaults for rule pack and configuration."""

import logging
from collections.abc import Collection

from cmk.ccc.i18n import _
from cmk.utils.translations import TranslationOptions

from .config import (
    ConfigFromWATO,
    ECRulePackSpec,
    EventLimit,
    EventLimits,
    LogConfig,
    Rule,
    SNMPCredential,
)


def default_rule_pack(rules: Collection[Rule]) -> ECRulePackSpec:
    """Returns the default rule pack."""
    return ECRulePackSpec(
        id="default",
        title=_("Default rule pack"),
        rules=rules,
        disabled=False,
    )


def default_config() -> ConfigFromWATO:
    """Returns the default configuration."""
    return ConfigFromWATO(
        rules=[],  # old pre 1.2.7i1 format. Only used if rule_packs is empty
        rule_packs=[],  # new format with rule packs
        actions=[],
        debug_rules=False,
        rule_optimizer=True,
        log_level=LogConfig(
            {
                "cmk.mkeventd": logging.INFO,
                "cmk.mkeventd.EventServer": logging.INFO,
                "cmk.mkeventd.EventServer.snmp": logging.INFO,
                "cmk.mkeventd.EventStatus": logging.INFO,
                "cmk.mkeventd.StatusServer": logging.INFO,
                "cmk.mkeventd.lock": logging.INFO,
            }
        ),
        log_rulehits=False,
        log_messages=False,
        retention_interval=60,
        housekeeping_interval=60,
        sqlite_housekeeping_interval=3600,  # seconds ValueSpec Age
        sqlite_freelist_size=50 * 1024 * 1024,  # bytes ValueSpec FIlesize
        statistics_interval=5,
        history_lifetime=365,  # days
        history_rotation="daily",
        replication=None,
        remote_status=None,
        socket_queue_len=10,
        eventsocket_queue_len=10,
        hostname_translation=TranslationOptions(),
        archive_orphans=False,
        archive_mode="sqlite",
        translate_snmptraps=False,
        snmp_credentials=[
            SNMPCredential(
                description='"public" default for receiving SNMPv1/v2 traps',
                credentials="public",
            )
        ],
        event_limit=EventLimits(
            by_host=EventLimit(
                action="stop_overflow_notify",
                limit=1000,
            ),
            by_rule=EventLimit(
                action="stop_overflow_notify",
                limit=1000,
            ),
            overall=EventLimit(
                action="stop_overflow_notify",
                limit=10000,
            ),
        ),
    )
