#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import (
    Annotated,
    Any,
    Literal,
    NamedTuple,
    NewType,
    NotRequired,
    override,
    TypedDict,
)

from pydantic import BaseModel, PlainValidator, WithJsonSchema

from cmk.ccc.cpu_tracking import Snapshot
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId

from cmk.utils.labels import Labels
from cmk.utils.metrics import MetricName
from cmk.utils.notify_types import DisabledNotificationsOptions, EventRule
from cmk.utils.structured_data import SDPath

from cmk.gui.exceptions import FinalizeRequest
from cmk.gui.http import Request
from cmk.gui.utils.speaklater import LazyString

from cmk.crypto.certificate import Certificate, CertificatePEM, CertificateWithPrivateKey
from cmk.crypto.hash import HashAlgorithm
from cmk.crypto.keys import EncryptedPrivateKeyPEM, PrivateKey
from cmk.crypto.password import Password
from cmk.crypto.password_hashing import PasswordHash
from cmk.crypto.secrets import Secret

_ContactgroupName = str
SizePT = NewType("SizePT", float)
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


class TrustedCertificateAuthorities(TypedDict):
    use_system_wide_cas: bool
    trusted_cas: Sequence[str]


class ChoiceGroup(NamedTuple):
    title: str
    choices: Choices


GroupedChoices = list[ChoiceGroup]


class WebAuthnCredential(TypedDict):
    credential_id: str
    registered_at: int
    alias: str
    credential_data: bytes


class TotpCredential(TypedDict):
    credential_id: str
    secret: bytes
    version: int
    registered_at: int
    alias: str


class TwoFactorCredentials(TypedDict):
    webauthn_credentials: dict[str, WebAuthnCredential]
    backup_codes: list[PasswordHash]
    totp_credentials: dict[str, TotpCredential]


class WebAuthnActionState(TypedDict):
    challenge: str
    user_verification: str


SessionId = str
AuthType = Literal[
    "basic_auth",
    "bearer",
    "cognito",
    "cookie",
    "http_header",
    "internal_token",
    "login_form",
    "remote_site",
    "saml",
    "web_server",
]

DismissableWarning = Literal["notification_fallback", "immediate_slideout_change"]


@dataclass
class SessionInfo:
    session_id: SessionId
    started_at: int
    last_activity: int
    csrf_token: str = field(default_factory=lambda: str(uuid.uuid4()))
    flashes: list[tuple[str, str]] = field(default_factory=list)
    encrypter_secret: str = field(default_factory=lambda: Secret.generate(32).b64_str)
    # In case it is enabled: Was it already authenticated?
    two_factor_completed: bool = False
    # Enable a 'login' state for enforcing two factor
    two_factor_required: bool = False
    # We don't care about the specific object, because it's internal to the fido2 library
    webauthn_action_state: WebAuthnActionState | None = None

    logged_out: bool = field(default=False)
    auth_type: AuthType | None = None

    def invalidate(self) -> None:
        """Called when a user logged out"""
        self.auth_type = None
        self.logged_out = True

    def refresh(self, now: datetime | None = None) -> None:
        """Called on any user activity.

        >>> now = datetime(2022, 1, 1, 0, 0, 0)
        >>> info = SessionInfo(session_id="", started_at=0, last_activity=0)
        >>> info.refresh(now)
        >>> assert info.last_activity == int(now.timestamp())

        Args:
            now:

        Returns:

        """
        if now is None:
            now = datetime.now()
        self.last_activity = int(now.timestamp())


class LastLoginInfo(TypedDict, total=False):
    auth_type: AuthType
    timestamp: int
    remote_address: str


# TODO: verify if the 'idea' is the same as notify_types.DisabledNotificationsOptions
#  but where the 'disable' field is called 'disabled'
class DisableNotificationsAttribute(TypedDict):
    disable: NotRequired[Literal[True]]  # disable or disabled?
    timerange: NotRequired[tuple[float, float]]


# TODO: verify if this is the same notify_types.Contact (merge if yes)
#  should be sure with first validation update
class UserContactDetails(TypedDict):
    alias: str
    disable_notifications: NotRequired[DisabledNotificationsOptions]
    email: NotRequired[str]
    pager: NotRequired[str]
    contactgroups: NotRequired[list[str]]
    fallback_contact: NotRequired[bool]
    user_scheme_serial: NotRequired[int]
    authorized_sites: NotRequired[list[str]]
    customer: NotRequired[str | None]


class UserDetails(TypedDict):
    alias: str
    connector: NotRequired[str | None]
    locked: NotRequired[bool]
    roles: NotRequired[list[str]]
    temperature_unit: NotRequired[Literal["celsius", "fahrenheit"] | None]
    force_authuser: NotRequired[bool]
    nav_hide_icons_title: NotRequired[Literal["hide"] | None]
    icons_per_item: NotRequired[Literal["entry"] | None]
    show_mode: NotRequired[
        Literal["default_show_less", "default_show_more", "enforce_show_more"] | None
    ]
    automation_secret: NotRequired[str]
    language: NotRequired[str]


# TODO: UserSpec gets composed from UserContactDetails and UserDetails so ideally the definition
#  should highlight this fact. For now, we leave it as is and improve the individual fields
class UserSpec(TypedDict, total=False):
    """This is not complete, but they don't yet...  Also we have a
    user_attribute_registry (cmk/gui/plugins/userdb/utils.py)

    I ignored two mypy findings in cmk/gui/userdb.py grep for ignore[misc]
    """

    alias: str
    authorized_sites: Sequence[SiteId] | None  # "None"/field missing => all sites
    automation_secret: NotRequired[str]
    connector: NotRequired[str | None]  # Contains the connection id this user was synced from
    contactgroups: list[_ContactgroupName]
    customer: str | None
    disable_notifications: DisabledNotificationsOptions
    email: NotRequired[str]  # TODO: Why do we have "email" *and* "mail"?
    enforce_pw_change: bool | None
    fallback_contact: bool | None
    force_authuser: NotRequired[bool]
    host_notification_options: str
    idle_timeout: Any  # TODO: Improve this
    is_automation_user: bool
    language: NotRequired[str]
    last_pw_change: int
    last_login: LastLoginInfo | None
    locked: NotRequired[bool]
    mail: str  # TODO: Why do we have "email" *and* "mail"?
    notification_method: Any  # TODO: Improve this
    notification_period: str
    notification_rules: list[EventRule]  # yes, we actually modify this! :-/
    notifications_enabled: bool | None
    num_failed_logins: int
    pager: str
    password: PasswordHash
    roles: list[str]
    serial: int
    service_notification_options: str
    store_automation_secret: bool
    session_info: dict[SessionId, SessionInfo]
    show_mode: NotRequired[
        Literal["default_show_less", "default_show_more", "enforce_show_more"] | None
    ]
    start_url: str | None
    two_factor_credentials: TwoFactorCredentials
    ui_sidebar_position: Literal["left"] | None
    ui_saas_onboarding_button_toggle: Literal["invisible"] | None
    ui_theme: Literal["modern-dark", "facelift"] | None
    user_id: AnnotatedUserId
    user_scheme_serial: int
    nav_hide_icons_title: NotRequired[Literal["hide"] | None]
    icons_per_item: NotRequired[Literal["entry"] | None]
    temperature_unit: NotRequired[Literal["celsius", "fahrenheit"] | None]
    contextual_help_icon: NotRequired[Literal["hide_icon"] | None]
    ldap_pw_last_changed: NotRequired[str]  # On attribute sync, this is added, then removed.


class UserObjectValue(TypedDict):
    attributes: UserSpec
    is_new_user: bool


UserObject = dict[UserId, UserObjectValue]

AnnotatedUserId = Annotated[
    UserId,
    PlainValidator(UserId.parse),
    WithJsonSchema({"type": "string"}, mode="serialization"),
]

Users = dict[AnnotatedUserId, UserSpec]  # TODO: Improve this type

# Visual specific
FilterName = str
FilterHTTPVariables = Mapping[str, str]
VisualName = str
VisualTypeName = Literal["dashboards", "views", "reports"]
VisualContext = Mapping[FilterName, FilterHTTPVariables]
InfoName = str
SingleInfos = Sequence[InfoName]


class LinkFromSpec(TypedDict, total=False):
    single_infos: SingleInfos
    host_labels: Labels
    has_inventory_tree: SDPath
    has_inventory_tree_history: SDPath


class Visual(TypedDict):
    owner: UserId
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
    public: bool | tuple[Literal["contact_groups", "sites"], Sequence[str]]
    packaged: bool
    link_from: LinkFromSpec
    main_menu_search_terms: Sequence[str]


class VisualLinkSpec(NamedTuple):
    type_name: VisualTypeName
    name: VisualName

    @classmethod
    def from_raw(cls, value: VisualName | tuple[VisualTypeName, VisualName]) -> VisualLinkSpec:
        # With Checkmk 2.0 we introduced the option to link to dashboards. Now the link_view is not
        # only a string (view_name) anymore, but a tuple of two elements: ('<visual_type_name>',
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


class PainterParameters(TypedDict, total=False):
    # TODO Improve:
    # First step was: make painter's param a typed dict with all obvious keys
    # but some possible keys are still missing
    aggregation: Literal["min", "max", "avg"] | tuple[str, str]
    color_choices: list[str]
    column_title: str
    ident: str
    max_len: int
    metric: str
    render_states: list[int | str]
    use_short: bool
    uuid: str
    # From join inv painter params
    path_to_table: SDPath
    column_to_display: str
    columns_to_match: list[tuple[str, str]]
    color_levels: tuple[Literal["abs_vals"], tuple[MetricName, tuple[float, float]]]
    # From historic metric painters
    rrd_consolidation: Literal["average", "min", "max"]
    time_range: tuple[str | int, int] | Literal["report"]
    # From graph painters
    graph_render_options: GraphRenderOptionsVS
    set_default_time_range: int


def _make_default_painter_parameters() -> PainterParameters:
    return PainterParameters()


ColumnTypes = Literal["column", "join_column", "join_inv_column"]


class _RawCommonColumnSpec(TypedDict):
    name: PainterName
    parameters: PainterParameters | None
    link_spec: tuple[VisualTypeName, VisualName] | None
    tooltip: ColumnName | None
    column_title: str | None
    column_type: ColumnTypes | None


class _RawLegacyColumnSpec(_RawCommonColumnSpec):
    join_index: ColumnName | None


class _RawColumnSpec(_RawCommonColumnSpec):
    join_value: ColumnName | None


@dataclass(frozen=True)
class ColumnSpec:
    name: PainterName
    parameters: PainterParameters = field(default_factory=_make_default_painter_parameters)
    link_spec: VisualLinkSpec | None = None
    tooltip: ColumnName | None = None
    join_value: ColumnName | None = None
    column_title: str | None = None
    _column_type: ColumnTypes | None = None

    @property
    def column_type(self) -> ColumnTypes:
        if self._column_type in ["column", "join_column", "join_inv_column"]:
            return self._column_type

        # First note:
        #   The "column_type" is used for differentiating ColumnSpecs in the view editor
        #   dialog. ie. "Column", "Joined Column", "Joined inventory column".
        # We have two entry points for ColumnSpec initialization:
        # 1. In "group_painters" or "painters" in views/dashboards/..., eg. views/builtin_views.py
        #    Here the "_column_type" is not set but calculated from "join_value".
        #    This only applies to "column" and "join_column" but not to "join_inv_column"
        #    because there are no such pre-defined ColumnSpecs
        # 2. during loading of visuals
        #    Here the "column_type" is part of the raw ColumnSpec which is add below in "from_raw"
        # Thus we don't need to handle "join_inv_column" here as long as there are no pre-defined
        # ColumnSpecs.
        return self._get_column_type_from_join_value(self.join_value)

    @classmethod
    def from_raw(cls, value: _RawColumnSpec | _RawLegacyColumnSpec | tuple) -> ColumnSpec:
        # TODO
        # 1: The params-None case can be removed with Checkmk 2.3
        # 2: The tuple-case can be removed with Checkmk 2.4.
        # 3: The join_index case can be removed with Checkmk 2.3
        # => The transformation is done via update_config/plugins/actions/cre_visuals.py

        if isinstance(value, dict):

            def _get_join_value(
                value: _RawColumnSpec | _RawLegacyColumnSpec,
            ) -> ColumnName | None:
                if isinstance(join_value := value.get("join_value"), str):
                    return join_value
                if isinstance(join_value := value.get("join_index"), str):
                    return join_value
                return None

            return cls(
                name=value["name"],
                parameters=value["parameters"] or PainterParameters(),
                link_spec=(
                    None
                    if (link_spec := value["link_spec"]) is None
                    else VisualLinkSpec.from_raw(link_spec)
                ),
                tooltip=value["tooltip"] or None,
                join_value=_get_join_value(value),
                column_title=value["column_title"],
                _column_type=value.get("column_type"),
            )

        # Some legacy views have optional fields like "tooltip" set to "" instead of None
        # in their definitions. Consolidate this case to None.
        value = (value[0],) + tuple(p or None for p in value[1:]) + (None,) * (5 - len(value))

        if isinstance(value[0], tuple):
            name, parameters = value[0]
        else:
            name = value[0]
            parameters = PainterParameters()

        join_value = value[3]
        return cls(
            name=name,
            parameters=parameters,
            link_spec=None if value[1] is None else VisualLinkSpec.from_raw(value[1]),
            tooltip=value[2],
            join_value=join_value,
            column_title=value[4],
            _column_type=cls._get_column_type_from_join_value(join_value),
        )

    @staticmethod
    def _get_column_type_from_join_value(
        join_value: ColumnName | None,
    ) -> Literal["column", "join_column"]:
        return "column" if join_value is None else "join_column"

    def to_raw(self) -> _RawColumnSpec:
        return {
            "name": self.name,
            "parameters": self.parameters,
            "link_spec": None if self.link_spec is None else self.link_spec.to_raw(),
            "tooltip": self.tooltip,
            "join_value": self.join_value,
            "column_title": self.column_title,
            "column_type": self.column_type,
        }

    @override
    def __repr__(self) -> str:
        """
        Used to serialize user-defined visuals
        """
        return str(self.to_raw())


@dataclass(frozen=True)
class SorterSpec:
    # The sorter parameters should be moved to a separate attribute instead
    sorter: SorterName | tuple[SorterName, PainterParameters]
    negate: bool
    join_key: str | None = None

    def to_raw(
        self,
    ) -> tuple[SorterName | tuple[SorterName, PainterParameters], bool, str | None]:
        return (
            self.sorter,
            self.negate,
            self.join_key,
        )

    @override
    def __repr__(self) -> str:
        """
        Used to serialize user-defined visuals
        """
        return str(self.to_raw())


class InventoryJoinMacrosSpec(TypedDict):
    macros: list[tuple[str, str]]


class ViewSpec(Visual):
    datasource: str
    layout: str  # TODO: Replace with literal? See layout_registry.get_choices()
    group_painters: Sequence[ColumnSpec]
    painters: Sequence[ColumnSpec]
    browser_reload: int
    num_columns: int
    column_headers: Literal["off", "pergroup", "repeat"]
    sorters: Sequence[SorterSpec]
    add_headers: NotRequired[str]
    # View editor only adds them in case they are truish. In our built-in specs these flags are also
    # partially set in case they are falsy
    mobile: NotRequired[bool]
    mustsearch: NotRequired[bool]
    force_checkboxes: NotRequired[bool]
    user_sortable: NotRequired[bool]
    play_sounds: NotRequired[bool]
    inventory_join_macros: NotRequired[InventoryJoinMacrosSpec]


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

    @override
    def __setitem__(self, key, value):  # type: ignore[no-untyped-def]
        if key in self:
            raise ValueError(f"key {key!r} already set")
        dict.__setitem__(self, key, value)

    @override
    def __delitem__(self, key):  # type: ignore[no-untyped-def]
        raise NotImplementedError("Deleting items are not supported.")


class ABCMainMenuSearch(ABC):
    """Abstract base class for search fields in main menus"""

    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def onopen(self) -> str:
        return 'cmk.popup_menu.focus_search_field("mk_side_search_field_%s");' % self.name

    @abstractmethod
    def show_search_field(self) -> None: ...


class _Icon(TypedDict):
    icon: str
    emblem: str | None


Icon = str | _Icon


@dataclass(kw_only=True, slots=True)
class _MainMenuEntry:
    name: str
    title: str
    sort_index: int
    is_show_more: bool = False
    icon: Icon | None = None


@dataclass(kw_only=True, slots=True)
class MainMenuItem(_MainMenuEntry):
    url: str
    target: str = "main"
    button_title: str | None = None
    main_menu_search_terms: Sequence[str] = ()


@dataclass(kw_only=True, slots=True)
class MainMenuTopicSegment(_MainMenuEntry):
    mode: Literal["multilevel", "indented"]
    entries: list[MainMenuItem | MainMenuTopicSegment]
    max_entries: int = 10
    hide: bool = False


MainMenuTopicEntries = list[MainMenuItem | MainMenuTopicSegment]


class MainMenuTopic(NamedTuple):
    name: str
    title: str
    entries: MainMenuTopicEntries
    max_entries: int = 10
    icon: Icon | None = None
    hide: bool = False


@dataclass(frozen=True)
class MainMenuData: ...


class MainMenuVueApp(NamedTuple):
    name: str
    data: Callable[[Request], MainMenuData]
    class_: list[str] = []


class MainMenu(NamedTuple):
    name: str
    title: str | LazyString
    icon: Icon
    sort_index: int
    topics: Callable[[], list[MainMenuTopic]] | None
    search: ABCMainMenuSearch | None = None
    info_line: Callable[[], str] | None = None
    hide: Callable[[], bool] = lambda: False
    vue_app: MainMenuVueApp | None = None
    onopen: str | None = None


SearchQuery = str


@dataclass
class SearchResult:
    """Representation of a single result"""

    title: str
    url: str
    context: str = ""


SearchResultsByTopic = Iterable[tuple[str, Iterable[SearchResult]]]

# Metric & graph specific


@dataclass(frozen=True)
class PerfDataTuple:
    metric_name: MetricName
    lookup_metric_name: MetricName
    value: float | int
    unit_name: str
    warn: float | None
    crit: float | None
    min: float | None
    max: float | None


Perfdata = list[PerfDataTuple]
RGBColor = tuple[float, float, float]  # (1.5, 0.0, 0.5)


class RowShading(TypedDict):
    enabled: bool
    odd: RGBColor
    even: RGBColor
    heading: RGBColor


GraphTitleFormatVS = Literal["plain", "add_host_name", "add_host_alias", "add_service_description"]


class GraphRenderOptionsVS(TypedDict, total=False):
    border_width: SizeMM
    color_gradient: float
    editing: bool
    fixed_timerange: bool
    font_size: SizePT
    interaction: bool
    preview: bool
    resizable: bool
    show_controls: bool
    show_graph_time: bool
    show_legend: bool
    show_margin: bool
    show_pin: bool
    show_time_axis: bool
    show_time_range_previews: bool
    show_title: bool | Literal["inline"]
    show_vertical_axis: bool
    size: tuple[int, int]
    vertical_axis_width: Literal["fixed"] | tuple[Literal["explicit"], SizePT]
    title_format: Sequence[GraphTitleFormatVS]


ActionResult = FinalizeRequest | None


@dataclass
class ViewProcessTracking:
    amount_unfiltered_rows: int = 0
    amount_filtered_rows: int = 0
    amount_rows_after_limit: int = 0
    duration_fetch_rows: Snapshot = Snapshot.null()
    duration_filter_rows: Snapshot = Snapshot.null()
    duration_view_render: Snapshot = Snapshot.null()


class Key(BaseModel):
    certificate: str
    private_key: str
    alias: str
    owner: AnnotatedUserId
    date: float
    # Before 2.2 this field was only used for Setup backup keys. Now we add it to all key, because it
    # won't hurt for other types of keys (e.g. the bakery signing keys). We set a default of False
    # to initialize it for all existing keys assuming it was already downloaded. It is still only
    # used in the context of the backup keys.
    not_downloaded: bool = False

    def to_certificate_with_private_key(self, passphrase: Password) -> CertificateWithPrivateKey:
        return CertificateWithPrivateKey(
            certificate=self.to_certificate(),
            private_key=PrivateKey.load_pem(EncryptedPrivateKeyPEM(self.private_key), passphrase),
        )

    def to_certificate(self) -> Certificate:
        """convert the string certificate to Certificate object"""
        return Certificate.load_pem(CertificatePEM(self.certificate))

    def fingerprint(self, algorithm: HashAlgorithm) -> str:
        """return the fingerprint aka hash of the certificate as a hey string"""
        return (
            Certificate.load_pem(CertificatePEM(self.certificate))
            .fingerprint(algorithm)
            .hex(":")
            .upper()
        )


GlobalSettings = Mapping[str, Any]


class IconSpec(TypedDict):
    icon: str
    title: NotRequired[str]
    url: NotRequired[tuple[str, str]]
    toplevel: NotRequired[bool]
    sort_index: NotRequired[int]


class BuiltinIconVisibility(TypedDict):
    toplevel: NotRequired[bool]
    sort_index: NotRequired[int]


class CustomAttrSpec(TypedDict):
    type: Literal["TextAscii"]
    name: str
    title: str
    topic: str
    help: str
    # None case should be cleaned up to False
    show_in_table: bool | None
    # None case should be cleaned up to False
    add_custom_macro: bool | None


class CustomHostAttrSpec(CustomAttrSpec): ...


class CustomUserAttrSpec(CustomAttrSpec):
    # None case should be cleaned up to False
    user_editable: bool | None


class VirtualHostTreeSpec(TypedDict):
    id: str
    title: str
    exclude_empty_tag_choices: bool
    tree_spec: Sequence[str]
