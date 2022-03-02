#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Defaults for rule pack and configuration"""

import logging
from typing import Any, Iterable

from cmk.utils.i18n import _

from .config import ConfigFromWATO, Rule, SNMPCredential


def default_rule_pack(rules: Iterable[Rule]) -> dict[str, Any]:
    """Returns the default rule pack"""
    return {
        "id": "default",
        "title": _("Default rule pack"),
        "rules": rules,
        "disabled": False,
    }


def default_config() -> ConfigFromWATO:
    """Returns the default configuration"""
    v1_v2_credential: SNMPCredential = {
        "description": '"public" default for receiving SNMPv1/v2 traps',
        "credentials": "public",
    }
    return {
        "rules": [],  # old pre 1.2.7i1 format. Only used if rule_packs is empty
        "rule_packs": [],  # new format with rule packs
        "mkp_rule_packs": {},  # rule packs provided by MKPs and referenced in rule_packs
        "actions": [],
        "debug_rules": False,
        "rule_optimizer": True,
        "log_level": {
            "cmk.mkeventd": logging.INFO,
            "cmk.mkeventd.EventServer": logging.INFO,
            "cmk.mkeventd.EventServer.snmp": logging.INFO,
            "cmk.mkeventd.EventStatus": logging.INFO,
            "cmk.mkeventd.StatusServer": logging.INFO,
            "cmk.mkeventd.lock": logging.INFO,
        },
        "log_rulehits": False,
        "log_messages": False,
        "retention_interval": 60,
        "housekeeping_interval": 60,
        "statistics_interval": 5,
        "history_lifetime": 365,  # days
        "history_rotation": "daily",
        "replication": None,
        "remote_status": None,
        "socket_queue_len": 10,
        "eventsocket_queue_len": 10,
        "hostname_translation": {},
        "archive_orphans": False,
        "archive_mode": "file",
        "translate_snmptraps": False,
        "snmp_credentials": [v1_v2_credential],
        "event_limit": {
            "by_host": {
                "action": "stop_overflow_notify",
                "limit": 1000,
            },
            "by_rule": {
                "action": "stop_overflow_notify",
                "limit": 1000,
            },
            "overall": {"action": "stop_overflow_notify", "limit": 10000},
        },
    }
