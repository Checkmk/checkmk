#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any, Literal, NamedTuple, TypedDict, Union

from pydantic import BaseModel

from cmk.utils.cpu_tracking import Snapshot
from cmk.utils.structured_data import SDPath
from cmk.utils.type_defs import (
    ContactgroupName,
    DisabledNotificationsOptions,
    EventRule,
    HostName,
    Labels,
    MetricName,
    ServiceName,
    UserId,
)

from cmk.gui.exceptions import FinalizeRequest
from cmk.gui.utils.speaklater import LazyString

SizePT = float
SizeMM = float
HTTPVariables = list[tuple[str, int | str | None]]
LivestatusQuery = str
PermissionName = str
RoleName = str
CSSSpec = list[str]
ChoiceText = str
ChoiceId = str | None
Choice = tuple[ChoiceId, ChoiceText]
Choices = list[Choice]  # TODO: Change to Sequence, perhaps DropdownChoiceEntries[str]


@dataclass
class UserRole:
    name: str
    alias: str
    builtin: bool = False
    permissions: dict[str, bool] = field(default_factory=dict)
    basedon: str | None = None

    def to_dict(self) -> dict:
        userrole_dict = {
            "alias": self.alias,
            "permissions": self.permissions,
            "builtin": self.builtin,
        }

        if not self.builtin:
            userrole_dict["basedon"] = self.basedon

        return userrole_dict


class ChoiceGroup(NamedTuple):
    title: str
    choices: Choices


GroupedChoices = list[ChoiceGroup]


class WebAuthnCredential(TypedDict):
    credential_id: str
    registered_at: int
    alias: str
    credential_data: bytes


class TwoFactorCredentials(TypedDict):
    webauthn_credentials: dict[str, WebAuthnCredential]
    backup_codes: list[str]


SessionId = str
AuthType = Literal["automation", "cookie", "web_server", "http_header", "bearer"]


@dataclass
class SessionInfo:
    session_id: SessionId
    started_at: int
    last_activity: int
    csrf_token: str = field(default_factory=lambda: str(uuid.uuid4()))
    flashes: list[str] = field(default_factory=list)
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
    connector: str | None
    contactgroups: list[ContactgroupName]
    customer: str | None
    disable_notifications: DisabledNotificationsOptions
    email: str  # TODO: Why do we have "email" *and* "mail"?
    enforce_pw_change: bool | None
    fallback_contact: bool | None
    force_authuser: bool
    host_notification_options: str
    idle_timeout: Any  # TODO: Improve this
    language: str
    last_pw_change: int
    locked: bool | None
    mail: str  # TODO: Why do we have "email" *and* "mail"?
    notification_method: Any  # TODO: Improve this
    notification_period: str
    notification_rules: list[EventRule]  # yes, we actually modify this! :-/
    notifications_enabled: bool | None
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


Users = dict[UserId, UserSpec]  # TODO: Improve this type

# Visual specific
FilterName = str
FilterHTTPVariables = Mapping[str, str]
VisualName = str
VisualTypeName = Literal["dashboards", "views", "reports"]
VisualContext = Mapping[FilterName, FilterHTTPVariables]
InfoName = str
SingleInfos = Sequence[InfoName]


class _VisualMandatory(TypedDict):
    owner: str
    name: str
    context: VisualContext
    single_infos: SingleInfos
    add_context_to_title: bool
    title: str | LazyString
    description: str | LazyString
    topic: str
    sort_index: int
    is_show_more: bool
    icon: Icon | None
    hidden: bool
    hidebutton: bool
    public: bool | tuple[Literal["contact_groups"], Sequence[str]]


class LinkFromSpec(TypedDict, total=False):
    single_infos: SingleInfos
    host_labels: Labels
    has_inventory_tree: Sequence[SDPath]
    has_inventory_tree_history: Sequence[SDPath]


class Visual(_VisualMandatory):
    link_from: LinkFromSpec


class VisualLinkSpec(NamedTuple):
    type_name: VisualTypeName
    name: VisualName

    @classmethod
    def from_raw(cls, value: VisualName | tuple[VisualTypeName, VisualName]) -> VisualLinkSpec:
        # With Checkmk 2.0 we introduced the option to link to dashboards. Now the link_view is not
        # only a string (view_name) anymore, but a tuple of two elemets: ('<visual_type_name>',
        # '<visual_name>'). Transform the old value to the new format.
        if isinstance(value, tuple):
            return cls(value[0], value[1])

        return cls("views", value)

    def to_raw(self) -> tuple[VisualTypeName, VisualName]:
        return self.type_name, self.name


# View specific
Row = dict[str, Any]  # TODO: Improve this type
Rows = list[Row]
PainterName = str
SorterName = str
ViewName = str
ColumnName = str
PainterParameters = dict  # TODO: Improve this type


@dataclass(frozen=True)
class PainterSpec:
    name: PainterName
    parameters: PainterParameters | None = None
    link_spec: VisualLinkSpec | None = None
    tooltip: ColumnName | None = None
    join_index: ColumnName | None = None
    column_title: str | None = None

    @classmethod
    def from_raw(cls, value: tuple) -> PainterSpec:
        # Some legacy views have optional fields like "tooltip" set to "" instead of None
        # in their definitions. Consolidate this case to None.
        value = (value[0],) + tuple(p or None for p in value[1:]) + (None,) * (5 - len(value))

        if isinstance(value[0], tuple):
            name, parameters = value[0]
        else:
            name = value[0]
            parameters = None

        return cls(
            name=name,
            parameters=parameters,
            link_spec=None if value[1] is None else VisualLinkSpec.from_raw(value[1]),
            tooltip=value[2],
            join_index=value[3],
            column_title=value[4],
        )

    def to_raw(
        self,
    ) -> tuple[
        PainterName | tuple[PainterName, PainterParameters],
        tuple[VisualTypeName, VisualName] | None,
        ColumnName | None,
        ColumnName | None,
        str | None,
    ]:
        return (
            self.name if self.parameters is None else (self.name, self.parameters),
            None if self.link_spec is None else self.link_spec.to_raw(),
            self.tooltip,
            self.join_index,
            self.column_title,
        )

    def __repr__(self) -> str:
        """
        Used to serialize user-defined visuals
        """
        return str(self.to_raw())


@dataclass(frozen=True)
class SorterSpec:
    # The sorter parameters should be moved to a separate attribute instead
    sorter: SorterName | tuple[SorterName, Mapping[str, str]]
    negate: bool
    join_key: str | None = None

    def to_raw(
        self,
    ) -> tuple[SorterName | tuple[SorterName, Mapping[str, str]], bool, str | None]:
        return (
            self.sorter,
            self.negate,
            self.join_key,
        )

    def __repr__(self) -> str:
        """
        Used to serialize user-defined visuals
        """
        return str(self.to_raw())


class _ViewSpecMandatory(Visual):
    datasource: str
    layout: str  # TODO: Replace with literal? See layout_registry.get_choices()
    group_painters: Sequence[PainterSpec]
    painters: Sequence[PainterSpec]
    browser_reload: int
    num_columns: int
    column_headers: Literal["off", "pergroup", "repeat"]
    sorters: Sequence[SorterSpec]


class ViewSpec(_ViewSpecMandatory, total=False):
    add_headers: str
    # View editor only adds them in case they are truish. In our builtin specs these flags are also
    # partially set in case they are falsy
    mobile: bool
    mustsearch: bool
    force_checkboxes: bool
    user_sortable: bool
    play_sounds: bool


AllViewSpecs = dict[tuple[UserId, ViewName], ViewSpec]
PermittedViewSpecs = dict[ViewName, ViewSpec]

SorterFunction = Callable[[ColumnName, Row, Row], int]
FilterHeader = str


class GroupSpec(TypedDict):
    title: str
    pattern: str
    min_items: int


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
            raise ValueError(f"key {key!r} already set")
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
    emblem: str | None


Icon = str | _Icon


class TopicMenuItem(NamedTuple):
    name: str
    title: str
    sort_index: int
    url: str
    target: str = "main"
    is_show_more: bool = False
    icon: Icon | None = None
    button_title: str | None = None


class TopicMenuTopic(NamedTuple):
    name: str
    title: str
    items: list[TopicMenuItem]
    max_entries: int = 10
    icon: Icon | None = None
    hide: bool = False


class MegaMenu(NamedTuple):
    name: str
    title: str | LazyString
    icon: Icon
    sort_index: int
    topics: Callable[[], list[TopicMenuTopic]]
    search: ABCMegaMenuSearch | None = None
    info_line: Callable[[], str] | None = None
    hide: Callable[[], bool] = lambda: False


SearchQuery = str


@dataclass
class SearchResult:
    """Representation of a single result"""

    title: str
    url: str
    context: str = ""


SearchResultsByTopic = Iterable[tuple[str, Iterable[SearchResult]]]

# Metric & graph specific

UnitRenderFunc = Callable[[Any], str]


class _UnitInfoRequired(TypedDict):
    title: str
    symbol: str
    render: UnitRenderFunc
    js_render: str


GraphTitleFormat = Literal["plain", "add_host_name", "add_host_alias", "add_service_description"]
GraphUnitRenderFunc = Callable[[list[float]], tuple[str, list[str]]]


class UnitInfo(_UnitInfoRequired, TypedDict, total=False):
    id: str
    stepping: str
    color: str
    graph_unit: GraphUnitRenderFunc
    description: str
    valuespec: Any  # TODO: better typing
    conversions: Mapping[str, Callable[[float | int], float | int]]


class _TranslatedMetricRequired(TypedDict):
    scale: list[float]


class TranslatedMetric(_TranslatedMetricRequired, total=False):
    # All keys seem to be optional. At least in one situation there is a translation object
    # constructed which only has the scale member (see
    # CustomGraphPage._show_metric_type_combined_summary)
    orig_name: list[str]
    value: float
    scalar: dict[str, float]
    auto_graph: bool
    title: str
    unit: UnitInfo
    color: str


GraphPresentation = str  # TODO: Improve Literal["lines", "stacked", "sum", "average", "min", "max"]
GraphConsoldiationFunction = Literal["max", "min", "average"]

RenderingExpression = tuple[Any, ...]
TranslatedMetrics = dict[str, TranslatedMetric]
MetricExpression = str
LineType = str  # TODO: Literal["line", "area", "stack", "-line", "-area", "-stack"]
# We still need "Union" because of https://github.com/python/mypy/issues/11098
MetricDefinition = Union[
    tuple[MetricExpression, LineType],
    tuple[MetricExpression, LineType, str | LazyString],
]
PerfometerSpec = dict[str, Any]
PerfdataTuple = tuple[str, float, str, float | None, float | None, float | None, float | None]
Perfdata = list[PerfdataTuple]
RGBColor = tuple[float, float, float]  # (1.5, 0.0, 0.5)


class RowShading(TypedDict):
    enabled: bool
    odd: RGBColor
    even: RGBColor
    heading: RGBColor


class GraphSpec(TypedDict):
    pass


class _TemplateGraphSpecMandatory(GraphSpec):
    site: str | None
    host_name: HostName
    service_description: ServiceName


class TemplateGraphSpec(_TemplateGraphSpecMandatory, total=False):
    graph_index: int | None
    graph_id: str | None


class ExplicitGraphSpec(GraphSpec, total=False):
    # This is added during run time by GraphIdentificationExplicit.create_graph_recipes. Where is it
    # used?
    specification: tuple[Literal["explicit"], GraphSpec]  # TODO: Correct would be ExplicitGraphSpec
    # I'd bet they are not mandatory. Needs to be figured out
    title: str
    unit: str
    consolidation_function: GraphConsoldiationFunction | None
    explicit_vertical_range: tuple[float | None, float | None]
    omit_zero_metrics: bool
    horizontal_rules: list  # TODO: Be more specific
    context: VisualContext
    add_context_to_title: bool
    metrics: list  # TODO: Be more specific


class _CombinedGraphSpecMandatory(GraphSpec):
    datasource: str
    single_infos: SingleInfos
    presentation: GraphPresentation
    context: VisualContext


class CombinedGraphSpec(_CombinedGraphSpecMandatory, total=False):
    selected_metric: MetricDefinition
    consolidation_function: GraphConsoldiationFunction
    graph_template: str


class _SingleTimeseriesGraphSpecMandatory(GraphSpec):
    site: str
    metric: MetricName


class SingleTimeseriesGraphSpec(_SingleTimeseriesGraphSpecMandatory, total=False):
    host: HostName
    service: ServiceName
    service_description: ServiceName
    color: str | None


TemplateGraphIdentifier = tuple[Literal["template"], TemplateGraphSpec]
CombinedGraphIdentifier = tuple[Literal["combined"], CombinedGraphSpec]
CustomGraphIdentifier = tuple[Literal["custom"], str]
ExplicitGraphIdentifier = tuple[Literal["explicit"], ExplicitGraphSpec]
SingleTimeseriesGraphIdentifier = tuple[Literal["single_timeseries"], SingleTimeseriesGraphSpec]

# We still need "Union" because of https://github.com/python/mypy/issues/11098
GraphIdentifier = Union[
    CustomGraphIdentifier,
    tuple[Literal["forecast"], str],
    TemplateGraphIdentifier,
    CombinedGraphIdentifier,
    ExplicitGraphIdentifier,
    SingleTimeseriesGraphIdentifier,
]


class RenderableRecipe(NamedTuple):
    title: str
    expression: RenderingExpression
    color: str
    line_type: str
    visible: bool


ActionResult = FinalizeRequest | None


@dataclass
class ViewProcessTracking:
    amount_unfiltered_rows: int = 0
    amount_filtered_rows: int = 0
    amount_rows_after_limit: int = 0
    duration_fetch_rows: Snapshot = Snapshot.null()
    duration_filter_rows: Snapshot = Snapshot.null()
    duration_view_render: Snapshot = Snapshot.null()


class CustomAttr(TypedDict, total=True):
    title: str
    help: str
    name: str
    topic: str
    type: str
    add_custom_macro: bool
    show_in_table: bool


class Key(BaseModel):
    certificate: str
    private_key: str
    alias: str
    owner: UserId
    date: float
    # Before 2.2 this field was only used for WATO backup keys. Now we add it to all key, because it
    # won't hurt for other types of keys (e.g. the bakery signing keys). We set a default of False
    # to initialize it for all existing keys assuming it was already downloaded. It is still only
    # used in the context of the backup keys.
    not_downloaded: bool = False
