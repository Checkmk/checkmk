#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Collection, Iterator, KeysView, Mapping, MutableMapping, Sequence
from re import Pattern
from typing import Any, Literal, TypeAlias, TypedDict

from cmk.ccc.exceptions import MKException

from cmk.utils.translations import TranslationOptions

TextPattern = str | Pattern[str]
TextMatchResult = Literal[False] | Sequence[str]


class MatchGroups(TypedDict, total=False):
    match_groups_message: TextMatchResult
    match_groups_message_ok: TextMatchResult
    match_groups_syslog_application: TextMatchResult
    match_groups_syslog_application_ok: TextMatchResult


# Horrible ValueSpec...
class UseSNMPTrapTranslation(TypedDict, total=False):
    add_description: Literal[True]


SNMPTrapTranslation = Literal[False] | tuple[Literal[True], UseSNMPTrapTranslation]


class EMailActionConfig(TypedDict):
    to: str
    subject: str
    body: str


class EMailAction(TypedDict):
    id: str
    title: str
    hidden: bool
    disabled: bool
    action: tuple[Literal["email"], EMailActionConfig]


class ScriptActionConfig(TypedDict):
    script: str


class ScriptAction(TypedDict):
    id: str
    title: str
    hidden: bool
    disabled: bool
    action: tuple[Literal["script"], ScriptActionConfig]


Action = EMailAction | ScriptAction


class EventLimit(TypedDict):
    action: str
    limit: int


class EventLimits(TypedDict):
    by_host: EventLimit
    by_rule: EventLimit
    overall: EventLimit


LogLevel = int

# TODO: Use keys which are valid identifiers
LogConfig = TypedDict(
    "LogConfig",
    {
        "cmk.mkeventd": LogLevel,
        "cmk.mkeventd.EventServer": LogLevel,
        "cmk.mkeventd.EventServer.snmp": LogLevel,
        "cmk.mkeventd.EventStatus": LogLevel,
        "cmk.mkeventd.StatusServer": LogLevel,
        "cmk.mkeventd.lock": LogLevel,
    },
)


class ReplicationBase(TypedDict):
    connect_timeout: int
    interval: int
    master: tuple[str, int]


class Replication(ReplicationBase, total=False):
    fallback: int
    disabled: Literal["true"]
    logging: Literal["true"]
    takeover: int


class ContactGroups(TypedDict):
    groups: Collection[str]
    notify: bool
    precedence: Literal["host", "rule"]


# number of second with an optional timzone offest from UTC in hours
ExpectInterval: TypeAlias = int | tuple[int, int]


class Expect(TypedDict):
    interval: ExpectInterval
    count: int
    merge: Literal["open", "acked", "never"]


class ServiceLevel(TypedDict):
    value: int
    precedence: Literal["message", "rule"]


StatePatterns = TypedDict(
    "StatePatterns",
    {
        "0": TextPattern,
        "1": TextPattern,
        "2": TextPattern,
    },
    total=False,
)

State = Literal[-1, 0, 1, 2, 3] | tuple[Literal["text_pattern"], StatePatterns]


class Count(TypedDict):
    count: int
    period: int  # seconds
    algorithm: Literal["interval", "tokenbucket", "dynabucket"]
    count_duration: int | None  # seconds
    count_ack: bool
    separate_host: bool
    separate_application: bool
    separate_match_groups: bool


# TODO: This is only a rough approximation.
class Rule(TypedDict, total=False):
    actions: Collection[str]
    actions_in_downtime: bool
    autodelete: bool
    cancel_actions: Collection[str]
    cancel_action_phases: str
    cancel_application: TextPattern
    cancel_priority: tuple[int, int]
    comment: str
    contact_groups: ContactGroups
    count: Count
    customer: str  # TODO: This is a GUI-only feature, which doesn't belong here at all.
    description: str
    docu_url: str
    disabled: bool
    expect: Expect
    event_limit: EventLimit
    hits: int
    id: str
    invert_matching: bool
    livetime: tuple[int, Collection[Literal["open", "ack"]]]
    match: TextPattern
    match_application: TextPattern
    match_facility: int
    match_host: TextPattern
    match_ipaddress: str
    match_ok: TextPattern
    match_priority: tuple[int, int]
    match_site: Collection[str]
    match_sl: tuple[int, int]
    match_timeperiod: str
    pack: str
    set_application: str
    set_comment: str
    set_contact: str
    set_host: str
    set_text: str
    sl: ServiceLevel
    state: State
    drop: bool | Literal["skip_pack"]


class ECRulePackSpec(TypedDict, total=False):
    id: str
    title: str
    disabled: bool
    rules: Collection[Rule]
    customer: str  # TODO: This is a GUI-only feature, which doesn't belong here at all.


class MkpRulePackBindingError(MKException):
    """Base class for exceptions related to rule pack binding."""


class MkpRulePackProxy(MutableMapping[str, Any]):
    """
    An object of this class represents an entry (i.e. a rule pack) in
    mkp_rule_packs. It is used as a reference to an EC rule pack
    that either can be exported or is already exported in a MKP.

    A newly created instance is not yet connected to a specific rule pack.
    This is achieved via the method bind_to.
    """

    def __init__(self, rule_pack_id: str) -> None:
        super().__init__()
        # Ideally the 'id_' would not be necessary and the proxy object would
        # be bound to it's referenced object upon initialization. Unfortunately,
        # this is not possible because the mknotifyd.mk could specify referenced
        # objects as well.
        self.id_ = rule_pack_id
        self.rule_pack: ECRulePackSpec | None = None

    def __getitem__(self, key: str) -> Any:
        if self.rule_pack is None:
            raise MkpRulePackBindingError("Proxy is not bound")
        return self.rule_pack[key]  # type: ignore[literal-required] # TODO: Nuke this!

    def __setitem__(self, key: str, value: Any) -> None:
        if self.rule_pack is None:
            raise MkpRulePackBindingError("Proxy is not bound")
        self.rule_pack[key] = value  # type: ignore[literal-required] # TODO: Nuke this!

    def __delitem__(self, key: str) -> None:
        if self.rule_pack is None:
            raise MkpRulePackBindingError("Proxy is not bound")
        del self.rule_pack[key]  # type: ignore[misc] # TODO: Nuke this!

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}("{self.id_}")'

    # __iter__ and __len__ are only defined as a workaround for a buggy entry
    # in the typeshed
    def __iter__(self) -> Iterator[str]:
        yield from self.keys()

    def __len__(self) -> int:
        return len(self.keys())

    def keys(self) -> KeysView[str]:
        """List of keys of this rule pack."""
        if self.rule_pack is None:
            raise MkpRulePackBindingError("Proxy is not bound")
        return self.rule_pack.keys()

    def bind_to(self, mkp_rule_pack: ECRulePackSpec) -> None:
        """Binds this rule pack to the given MKP rule pack."""
        if self.id_ != mkp_rule_pack["id"]:
            raise MkpRulePackBindingError(
                f"The IDs of {self} and {mkp_rule_pack} cannot be different."
            )

        self.rule_pack = mkp_rule_pack

    def get_rule_pack_spec(self) -> ECRulePackSpec:
        if self.rule_pack is None:
            raise MkpRulePackBindingError("Proxy is not bound")
        return self.rule_pack

    @property
    def is_bound(self) -> bool:
        """Has this rule pack been bound via bind_to()?"""
        return self.rule_pack is not None


ECRulePack = ECRulePackSpec | MkpRulePackProxy

AuthenticationProtocol = Literal[
    "md5",
    "sha",
    "SHA-224",
    "SHA-256",
    "SHA-384",
    "SHA-512",
]

PrivacyProtocol = Literal[
    "DES",
    "AES",
    "3DES-EDE",
    "AES-192",
    "AES-256",
    "AES-192-Blumenthal",
    "AES-256-Blumenthal",
]

SNMPV1V2Credentials = str
SNMPV3NoAuthNoPrivCredentials = tuple[Literal["noAuthNoPriv"], str]
SNMPV3AuthNoPrivCredentials = tuple[Literal["authNoPriv"], AuthenticationProtocol, str, str]
SNMPV3AuthPrivCredentials = tuple[
    Literal["authPriv"], AuthenticationProtocol, str, str, PrivacyProtocol, str
]
SNMPCredentials = (
    SNMPV1V2Credentials
    | SNMPV3NoAuthNoPrivCredentials
    | SNMPV3AuthNoPrivCredentials
    | SNMPV3AuthPrivCredentials
)


class SNMPCredentialBase(TypedDict):
    description: str
    credentials: SNMPCredentials


class SNMPCredential(SNMPCredentialBase, total=False):
    engine_ids: Collection[str]


# This is what we get from the outside.
class ConfigFromWATO(TypedDict):
    actions: Sequence[Action]
    archive_mode: Literal["file", "mongodb", "sqlite"]
    archive_orphans: bool
    debug_rules: bool
    event_limit: EventLimits
    eventsocket_queue_len: int
    history_lifetime: int
    history_rotation: Literal["daily", "weekly"]
    hostname_translation: TranslationOptions  # TODO: Mutable???
    housekeeping_interval: int
    log_level: LogConfig  # TODO: Mutable???
    log_messages: bool
    log_rulehits: bool
    remote_status: tuple[int, bool, Sequence[str] | None] | None
    replication: Replication | None
    retention_interval: int
    rule_optimizer: bool
    rule_packs: Sequence[ECRulePack]
    rules: Collection[Rule]
    sqlite_housekeeping_interval: int
    sqlite_freelist_size: int
    snmp_credentials: Collection[SNMPCredential]
    socket_queue_len: int
    statistics_interval: int
    translate_snmptraps: SNMPTrapTranslation


class Config(ConfigFromWATO):
    """
    After loading, we add two fields: 'action' for more efficient access to actions plus a timestamp
    used for replication.
    """

    action: Mapping[str, Action]
    last_reload: int
