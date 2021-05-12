#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import (
    Any,
    Dict,
    List,
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


# Horrible ValueSpec...
class UseSNMPTrapTranslation(TypedDict, total=False):
    add_description: Literal[True]


SNMPTrapTranslation = Union[Literal[False], Tuple[Literal[True], UseSNMPTrapTranslation]]

ActionType = Union[Literal['email'], Literal['script']]


class ActionSettings(TypedDict):
    # 'email' case
    to: str
    subject: str
    body: str
    # 'script' case
    script: str


class Action(TypedDict):
    id: str
    disabled: bool
    action: Tuple[ActionType, ActionSettings]


# This is what we get from the outside.
class ConfigFromWATO(TypedDict):
    actions: Sequence[Action]
    archive_mode: str
    archive_orphans: bool
    debug_rules: bool
    event_limit: Mapping[str, Mapping[str, Any]]  # TODO: TypedDict
    eventsocket_queue_len: int
    history_lifetime: int
    history_rotation: str
    hostname_translation: MutableMapping[str, Any]  # TODO: Mutable??? TypedDict
    housekeeping_interval: int
    log_level: MutableMapping[str, int]  # TODO: Mutable???
    log_messages: bool
    log_rulehits: bool
    mkp_rule_packs: Mapping[Any, Any]  # TODO: Move to Config (not from WATO!). TypedDict
    remote_status: Optional[Tuple[int, bool, Optional[Sequence[str]]]]
    replication: Optional[Mapping[str, Any]]  # TODO: TypedDict
    retention_interval: int
    rule_optimizer: bool
    rule_packs: Sequence[Dict[str, Any]]  # TODO: Mutable??? TypedDict
    rules: List[Dict[str, Any]]  # TODO: Mutable??? TypedDict
    snmp_credentials: Iterable[Mapping[str, str]]
    socket_queue_len: int
    statistics_interval: int
    translate_snmptraps: SNMPTrapTranslation


# After loading, we add two fields: 'action' for more efficient access to actions plus a timestamp
# used for replication.
class Config(ConfigFromWATO):
    action: Mapping[str, Action]
    last_reload: int
