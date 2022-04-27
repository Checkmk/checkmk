#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Literal,
    Mapping,
    NamedTuple,
    Optional,
    Sequence,
    Text,
    Tuple,
    TypedDict,
    Union,
)

from cmk.utils.cpu_tracking import Snapshot
from cmk.utils.type_defs import ContactgroupName, DisabledNotificationsOptions, EventRule, UserId

from cmk.gui.exceptions import FinalizeRequest
from cmk.gui.utils.speaklater import LazyString

HTTPVariables = List[Tuple[str, Optional[Union[int, str]]]]
LivestatusQuery = str
PermissionName = str
RoleName = str
CSSSpec = Union[None, str, List[str], List[Optional[str]], str]
ChoiceText = str
ChoiceId = Optional[str]
Choice = Tuple[ChoiceId, ChoiceText]
Choices = List[Choice]  # TODO: Change to Sequence, perhaps DropdownChoiceEntries[str]


class ChoiceGroup(NamedTuple):
    title: Text
    choices: Choices


GroupedChoices = List[ChoiceGroup]


class WebAuthnCredential(TypedDict):
    credential_id: str
    registered_at: int
    alias: str
    credential_data: bytes


class TwoFactorCredentials(TypedDict):
    webauthn_credentials: Dict[str, WebAuthnCredential]
    backup_codes: List[str]


SessionId = str
AuthType = Literal["automation", "cookie", "web_server", "http_header", "bearer"]


@dataclass
class SessionInfo:
    session_id: SessionId
    started_at: int
    last_activity: int
    flashes: List[str] = field(default_factory=list)
    # In case it is enabled: Was it already authenticated?
    two_factor_completed: bool = False
    # We don't care about the specific object, because it's internal to the fido2 library
    webauthn_action_state: object = None

    def to_json(self) -> dict:
        # We assume here that asdict() does the right thing for the
        # webauthn_action_state field. This can be the case, but it's not very
        # obvious.
        return asdict(self)


class UserSpec(TypedDict, total=False):
    """This is not complete, but they don't yet...  Also we have a
    user_attribute_registry (cmk/gui/plugins/userdb/utils.py)

    I ignored two mypy findings in cmk/gui/userdb.py grep for ignore[misc]
    """

    alias: str
    authorized_sites: Any  # TODO: Improve this
    automation_secret: str
    connector: Optional[str]
    contactgroups: list[ContactgroupName]
    customer: Optional[str]
    disable_notifications: DisabledNotificationsOptions
    email: str  # TODO: Why do we have "email" *and* "mail"?
    enforce_pw_change: Optional[bool]
    fallback_contact: Optional[bool]
    force_authuser: bool
    host_notification_options: str
    idle_timeout: Any  # TODO: Improve this
    language: str
    last_pw_change: int
    locked: Optional[bool]
    mail: str  # TODO: Why do we have "email" *and* "mail"?
    notification_method: Any  # TODO: Improve this
    notification_period: str
    notification_rules: list[EventRule]  # yes, we actually modify this! :-/
    notifications_enabled: Optional[bool]
    num_failed_logins: int
    pager: str
    password: str
    roles: list[str]
    serial: int
    service_notification_options: str
    session_info: dict[SessionId, SessionInfo]
    show_mode: str
    start_url: str
    two_factor_credentials: TwoFactorCredentials
    ui_sidebar_position: Any  # TODO: Improve this
    ui_theme: Any  # TODO: Improve this
    user_id: UserId
    user_scheme_serial: int


Users = Dict[UserId, UserSpec]  # TODO: Improve this type

# Visual specific
FilterName = str
FilterHTTPVariables = Mapping[str, str]
Visual = Dict[str, Any]
VisualName = str
VisualTypeName = str
VisualContext = Mapping[FilterName, FilterHTTPVariables]
InfoName = str
SingleInfos = Sequence[InfoName]


class VisualLinkSpec(NamedTuple):
    type_name: VisualTypeName
    name: VisualName


# View specific
Row = Dict[str, Any]  # TODO: Improve this type
Rows = List[Row]
PainterName = str
SorterName = str
ViewName = str
ColumnName = str
PainterParameters = Dict  # TODO: Improve this type
PainterNameSpec = Union[PainterName, Tuple[PainterName, PainterParameters]]


class PainterSpec(
    NamedTuple(  # pylint: disable=typing-namedtuple-call
        "PainterSpec",
        [
            ("painter_name", PainterNameSpec),
            ("link_spec", Optional[VisualLinkSpec]),
            ("tooltip", Optional[ColumnName]),
            ("join_index", Optional[ColumnName]),
            ("column_title", Optional[str]),
        ],
    )
):
    def __new__(cls, *value):
        # Some legacy views have optional fields like "tooltip" set to "" instead of None
        # in their definitions. Consolidate this case to None.
        value = (value[0],) + tuple(p or None for p in value[1:]) + (None,) * (5 - len(value))

        # With Checkmk 2.0 we introduced the option to link to dashboards. Now the link_view is not
        # only a string (view_name) anymore, but a tuple of two elemets: ('<visual_type_name>',
        # '<visual_name>'). Transform the old value to the new format.
        if isinstance(value[1], str):
            value = (value[0], VisualLinkSpec("views", value[1])) + value[2:]
        elif isinstance(value[1], tuple):
            value = (value[0], VisualLinkSpec(*value[1])) + value[2:]

        return super().__new__(cls, *value)

    def __repr__(self):
        return str(
            (self.painter_name, tuple(self.link_spec) if self.link_spec else None) + tuple(self)[2:]
        )


ViewSpec = Dict[str, Any]
AllViewSpecs = Dict[Tuple[UserId, ViewName], ViewSpec]
PermittedViewSpecs = Dict[ViewName, ViewSpec]
SorterFunction = Callable[[ColumnName, Row, Row], int]
FilterHeader = str

# Configuration related
ConfigDomainName = str


class SetOnceDict(dict):
    """A subclass of `dict` on which every key can only ever be set once.

    Apart from preventing keys to be set again, and the fact that keys can't be removed it works
    just like a regular dict.

    Examples:

        >>> d = SetOnceDict()
        >>> d['foo'] = 'bar'
        >>> d['foo'] = 'bar'
        Traceback (most recent call last):
        ...
        ValueError: key 'foo' already set

    """

    def __setitem__(self, key, value):
        if key in self:
            raise ValueError("key %r already set" % (key,))
        dict.__setitem__(self, key, value)

    def __delitem__(self, key):
        raise NotImplementedError("Deleting items are not supported.")


class ABCMegaMenuSearch(ABC):
    """Abstract base class for search fields in mega menus"""

    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def onopen(self) -> str:
        return 'cmk.popup_menu.focus_search_field("mk_side_search_field_%s");' % self.name

    @abstractmethod
    def show_search_field(self) -> None:
        ...


class _Icon(TypedDict):
    icon: str
    emblem: Optional[str]


Icon = Union[str, _Icon]


class TopicMenuItem(NamedTuple):
    name: str
    title: str
    sort_index: int
    url: str
    target: str = "main"
    is_show_more: bool = False
    icon: Optional[Icon] = None
    button_title: Optional[str] = None


class TopicMenuTopic(NamedTuple):
    name: "str"
    title: "str"
    items: List[TopicMenuItem]
    max_entries: int = 10
    icon: Optional[Icon] = None
    hide: bool = False


class MegaMenu(NamedTuple):
    name: str
    title: Union[str, LazyString]
    icon: Icon
    sort_index: int
    topics: Callable[[], List[TopicMenuTopic]]
    search: Optional[ABCMegaMenuSearch] = None
    info_line: Optional[Callable[[], str]] = None


SearchQuery = str


@dataclass
class SearchResult:
    """Representation of a single result"""

    title: str
    url: str
    context: str = ""


SearchResultsByTopic = Iterable[Tuple[str, Iterable[SearchResult]]]

# Metric & graph specific


class _UnitInfoRequired(TypedDict):
    title: str
    symbol: str
    render: Callable[[Any], str]
    js_render: str


class UnitInfo(_UnitInfoRequired, TypedDict, total=False):
    id: str
    stepping: str
    color: str
    graph_unit: Callable[[List[Union[int, float]]], Tuple[str, List[str]]]
    description: str
    valuespec: Any  # TODO: better typing


class _TranslatedMetricRequired(TypedDict):
    scale: List[float]


class TranslatedMetric(_TranslatedMetricRequired, total=False):
    # All keys seem to be optional. At least in one situation there is a translation object
    # constructed which only has the scale member (see
    # CustomGraphPage._show_metric_type_combined_summary)
    orig_name: List[str]
    value: float
    scalar: Dict[str, float]
    auto_graph: bool
    title: str
    unit: UnitInfo
    color: str


GraphIdentifier = Tuple[str, Any]
RenderingExpression = Tuple[Any, ...]
TranslatedMetrics = Dict[str, TranslatedMetric]
MetricExpression = str
LineType = str  # TODO: Literal["line", "area", "stack", "-line", "-area", "-stack"]
MetricDefinition = Union[
    Tuple[MetricExpression, LineType], Tuple[MetricExpression, LineType, Union[str, LazyString]]
]
PerfometerSpec = Dict[str, Any]
PerfdataTuple = Tuple[
    str, float, str, Optional[float], Optional[float], Optional[float], Optional[float]
]
Perfdata = List[PerfdataTuple]


class RenderableRecipe(NamedTuple):
    title: str
    expression: RenderingExpression
    color: str
    line_type: str
    visible: bool


ActionResult = Optional[FinalizeRequest]


@dataclass
class ViewProcessTracking:
    amount_unfiltered_rows: int = 0
    amount_filtered_rows: int = 0
    amount_rows_after_limit: int = 0
    duration_fetch_rows: Snapshot = Snapshot.null()
    duration_filter_rows: Snapshot = Snapshot.null()
    duration_view_render: Snapshot = Snapshot.null()


CustomAttr = TypedDict(
    "CustomAttr",
    {
        "title": str,
        "help": str,
        "name": str,
        "topic": str,
        "type": str,
        "add_custom_macro": bool,
        "show_in_table": bool,
    },
    total=True,
)
