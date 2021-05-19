#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import (
    Any,
    Dict,
    Literal,
    Iterable,
    Mapping,
    MutableMapping,
    Optional,
    Sequence,
    Tuple,
    TypedDict,
    Union,
)

from cmk.utils.type_defs import Seconds

################################################################################


# Horrible ValueSpec...
class UseSNMPTrapTranslation(TypedDict, total=False):
    add_description: Literal[True]


SNMPTrapTranslation = Union[Literal[False], Tuple[Literal[True], UseSNMPTrapTranslation]]

################################################################################


class EMailActionConfig(TypedDict):
    to: str
    subject: str
    body: str


class EMailAction(TypedDict):
    id: str
    disabled: bool
    action: Tuple[Literal['email'], EMailActionConfig]


class ScriptActionConfig(TypedDict):
    script: str


class ScriptAction(TypedDict):
    id: str
    disabled: bool
    action: Tuple[Literal['script'], ScriptActionConfig]


Action = Union[EMailAction, ScriptAction]

################################################################################


class EventLimit(TypedDict):
    action: str
    limit: int


class HostnameTranslation(TypedDict, total=False):
    case: Union[Literal['lower'], Literal['upper']]
    drop_domain: bool
    mapping: Iterable[Tuple[str, str]]
    regex: Iterable[Tuple[str, str]]


class ReplicationBase(TypedDict):
    connect_timeout: int
    interval: int
    master: Tuple[str, int]


class Replication(ReplicationBase, total=False):
    fallback: int
    disabled: Literal['true']
    logging: Literal['true']
    takeover: int


class ContactGroups(TypedDict):
    groups: Iterable[str]
    notify: bool
    precedence: Union[Literal['host'], Literal['rule']]


class ServiceLevel(TypedDict):
    value: int
    precedence: Union[Literal['message'], Literal['rule']]


class Rule(TypedDict):
    contact_groups: ContactGroups
    livetime: Tuple[Seconds, Union[Literal['open'], Literal['ack']]]
    sl: ServiceLevel


# This is what we get from the outside.
class ConfigFromWATO(TypedDict):
    actions: Sequence[Action]
    archive_mode: str
    archive_orphans: bool
    debug_rules: bool
    event_limit: Mapping[str, EventLimit]
    eventsocket_queue_len: int
    history_lifetime: int
    history_rotation: str
    hostname_translation: HostnameTranslation  # TODO: Mutable???
    housekeeping_interval: int
    log_level: MutableMapping[str, int]  # TODO: Mutable???
    log_messages: bool
    log_rulehits: bool
    mkp_rule_packs: Mapping[Any, Any]  # TODO: Move to Config (not from WATO!). TypedDict
    remote_status: Optional[Tuple[int, bool, Optional[Sequence[str]]]]
    replication: Optional[Replication]
    retention_interval: int
    rule_optimizer: bool
    rule_packs: Sequence[Dict[str, Any]]  # TODO: Mutable??? TypedDict
    rules: Iterable[Rule]
    snmp_credentials: Iterable[Mapping[str, str]]
    socket_queue_len: int
    statistics_interval: int
    translate_snmptraps: SNMPTrapTranslation


# After loading, we add two fields: 'action' for more efficient access to actions plus a timestamp
# used for replication.
class Config(ConfigFromWATO):
    action: Mapping[str, Action]
    last_reload: int
