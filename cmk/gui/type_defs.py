#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from __future__ import annotations

import uuid
from collections.abc import Callable, Hashable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Annotated,
    Any,
    Literal,
    NamedTuple,
    NewType,
    NotRequired,
    override,
    Self,
    TypedDict,
    TypeVar,
)

from pydantic import BaseModel, PlainValidator, WithJsonSchema

from cmk.ccc.cpu_tracking import Snapshot
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.crypto.certificate import Certificate, CertificatePEM, CertificateWithPrivateKey
from cmk.crypto.hash import HashAlgorithm
from cmk.crypto.keys import EncryptedPrivateKeyPEM, PrivateKey
from cmk.crypto.password import Password
from cmk.crypto.password_hashing import PasswordHash
from cmk.crypto.secrets import Secret
from cmk.gui.exceptions import FinalizeRequest
from cmk.gui.utils.speaklater import LazyString
from cmk.inventory.structured_data import SDPath
from cmk.shared_typing.icon import IconNames as IconNames
from cmk.shared_typing.icon import IconSizes as IconSizes
from cmk.utils.labels import Labels
from cmk.utils.metrics import MetricName
from cmk.utils.notify_types import DisabledNotificationsOptions, EventRule
from cmk.utils.password_store import PasswordId

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
ChoiceMapping = Mapping[str, ChoiceText]
GraphPresentation = Literal["lines", "stacked", "sum", "average", "min", "max"]


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

DismissableWarning = Literal[
    "notification_fallback", "immediate_slideout_change", "changes-info", "agent_slideout"
]


SessionState = Literal[
    "credentials_needed",
    "second_factor_auth_needed",
    "second_factor_setup_needed",
    "password_change_needed",
    "logged_in",
]


class SessionStateMachine:
    """A state machine for the login process.

    config = 2fa enabled
    auth_needed = enforcement

    Valid transitions:
        credentials_needed          -> (any)
        second_factor_auth_needed   -> password_change_needed, logged_in
        second_factor_setup_needed  -> password_change_needed, logged_in
        password_change_needed      -> logged_in
        (any)                       -> credentials_needed
    """

    def __init__(self, initial_state: SessionState = "credentials_needed") -> None:
        self.state = initial_state

    def transition(
        self,
        *,
        check_if_2fa_auth_is_needed: Callable[[], bool],
        check_if_2fa_setup_is_needed: Callable[[], bool],
        check_if_pw_change_is_needed: Callable[[], bool],
    ) -> SessionState:
        # note those checks can be expensive operations, e.g. loading user info from disk; that's
        # why they are callbacks
        match self.state:
            case "credentials_needed":
                self.credentials_verified(
                    check_if_2fa_auth_is_needed=check_if_2fa_auth_is_needed,
                    check_if_2fa_setup_is_needed=check_if_2fa_setup_is_needed,
                    check_if_pw_change_is_needed=check_if_pw_change_is_needed,
                )
            case "second_factor_auth_needed":
                self.second_factor_authenticated(check_if_pw_change_is_needed)
            case "second_factor_setup_needed":
                self.second_factor_configured(check_if_pw_change_is_needed)
            case "password_change_needed":
                self.password_changed()
            case "logged_in":
                return self.state
            case _:
                raise ValueError(f"Invalid state to transition: {self.state}")

        return self.state

    def credentials_verified(
        self,
        *,
        check_if_2fa_auth_is_needed: Callable[[], bool],
        check_if_2fa_setup_is_needed: Callable[[], bool],
        check_if_pw_change_is_needed: Callable[[], bool],
    ) -> None:
        # NOTE: order matters here
        if check_if_2fa_auth_is_needed():
            self.state = "second_factor_auth_needed"
            return

        if check_if_2fa_setup_is_needed():
            self.state = "second_factor_setup_needed"
            return

        if check_if_pw_change_is_needed():
            self.state = "password_change_needed"
            return

        self.state = "logged_in"

    def second_factor_configured(self, check_if_pw_change_is_needed: Callable[[], bool]) -> None:
        if check_if_pw_change_is_needed():
            self.state = "password_change_needed"
        else:
            self.state = "logged_in"

    def second_factor_authenticated(self, check_if_pw_change_is_needed: Callable[[], bool]) -> None:
        if check_if_pw_change_is_needed():
            self.state = "password_change_needed"
        else:
            self.state = "logged_in"

    def password_changed(self) -> None:
        self.state = "logged_in"


@dataclass
class SessionInfo:
    session_id: SessionId
    started_at: int
    last_activity: int
    csrf_token: str = field(default_factory=lambda: str(uuid.uuid4()))
    flashes: list[tuple[str, str]] = field(default_factory=list)
    encrypter_secret: str = field(default_factory=lambda: Secret.generate(32).b64_str)
    # Enable a 'login' state for enforcing two factor
    two_factor_required: bool = False
    # We don't care about the specific object, because it's internal to the fido2 library
    webauthn_action_state: WebAuthnActionState | None = None

    # None is only required for bootstrapping the object; valid sessions always have an auth_type
    auth_type: AuthType | None = None

    session_state: SessionState = field(default="credentials_needed")

    @property
    def is_logged_out(self) -> bool:
        return self.session_state == "credentials_needed"

    def logout(self) -> None:
        """Called when a user logged out"""
        self.session_state = "credentials_needed"


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
    """This is not complete, but they don't yet...  Also we have a user_attribute_registry

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
    # TODO: do we need session_info in the user?
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
VisualPublic = bool | tuple[Literal["contact_groups", "sites"], Sequence[str]]
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
    icon: DynamicIcon | None
    hidden: bool
    hidebutton: bool
    public: VisualPublic
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


# NOTE: keep in sync with `DashboardEmbeddedViewSpec`
class ViewSpec(Visual):
    datasource: str
    layout: str  # TODO: Replace with literal? See layout_registry.get_choices()
    group_painters: Sequence[ColumnSpec]
    painters: Sequence[ColumnSpec]
    browser_reload: int
    num_columns: int
    column_headers: Literal["off", "pergroup"]
    sorters: Sequence[SorterSpec]
    add_headers: NotRequired[str]
    row_limit: NotRequired[int]  # Custom row limit for this view (overrides soft/hard limits)
    # View editor only adds them in case they are truish. In our built-in specs these flags are also
    # partially set in case they are falsy
    mobile: NotRequired[bool]
    mustsearch: NotRequired[bool]
    force_checkboxes: NotRequired[bool]
    user_sortable: NotRequired[bool]
    play_sounds: NotRequired[bool]
    inventory_join_macros: NotRequired[InventoryJoinMacrosSpec]
    modified_at: NotRequired[str]  # timestamp in ISO format


# NOTE: keep in sync with `ViewSpec`
# Trimmed down version of `ViewSpec` for embedded views in dashboards
class DashboardEmbeddedViewSpec(TypedDict):
    # from Visual
    single_infos: SingleInfos
    # from ViewSpec
    datasource: str
    layout: str
    group_painters: Sequence[ColumnSpec]
    painters: Sequence[ColumnSpec]
    browser_reload: int
    num_columns: int
    column_headers: Literal["off", "pergroup"]
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
    modified_at: NotRequired[str]  # timestamp in ISO format


AllViewSpecs = dict[tuple[UserId, ViewName], ViewSpec]
PermittedViewSpecs = dict[ViewName, ViewSpec]

SorterFunction = Callable[[ColumnName, Row, Row], int]
FilterHeader = str


class GroupSpec(TypedDict):
    title: str
    pattern: str
    min_items: int


K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


class SetOnceDict(dict[K, V]):
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
    def __setitem__(self, key: K, value: V) -> None:
        if key in self:
            raise ValueError(f"key {key!r} already set")
        dict.__setitem__(self, key, value)

    @override
    def __delitem__(self, key: K) -> None:
        raise NotImplementedError("Deleting items are not supported.")


DynamicIconName = NewType("DynamicIconName", str)


class _Icon(TypedDict):
    icon: DynamicIconName
    emblem: str | None


DynamicIcon = DynamicIconName | _Icon


@dataclass(frozen=True)
class StaticIcon:
    icon: IconNames
    emblem: str | None = None


SearchQuery = str


@dataclass
class SearchResult:
    """Representation of a single result"""

    title: str
    url: str
    context: str = ""
    loading_transition: str | None = None


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


class KeyId(str):
    """KeyId type used for dictionary keys of KeypairStore & agent signature keys.
    Accepts str|int|uuid.UUID on initialization and coerces to str internally.
    Earlier key_id were integers, later changed to UUIDs. To support both types transparently,
    we accept str|int|uuid.UUID here.
    """

    def __new__(cls, value: str | int | uuid.UUID) -> Self:
        return super().__new__(cls, str(value))

    @classmethod
    def generate(cls) -> Self:
        return cls(uuid.uuid4())


GlobalSettings = Mapping[str, Any]


class IconSpec(TypedDict):
    icon: DynamicIconName
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


class RenderMode(Enum):
    BACKEND = "backend"
    FRONTEND = "frontend"


class ReadOnlySpec(TypedDict):
    enabled: bool | tuple[float, float]
    message: str
    rw_users: Sequence[UserId]


class AgentControllerCertificates(TypedDict):
    lifetime_in_months: int


class PasswordPolicy(TypedDict):
    min_length: NotRequired[int]
    num_groups: NotRequired[int]
    max_age: NotRequired[int]


class GraphTimerange(TypedDict):
    title: str
    duration: int


# Need to use functional syntax because of the no-cert-check attribute
NtopConnectionSpec = TypedDict(
    "NtopConnectionSpec",
    {
        "is_activated": bool,
        # Was introduced later
        "is_host_filter_activated": NotRequired[bool],
        "hostaddress": str,
        "port": int,
        "protocol": Literal["https", "http"],
        "no-cert-check": bool,
        "admin_username": str,
        "admin_password": PasswordId,
        "use_custom_attribute_as_ntop_username": Literal[False, "ntop_alias"],
    },
)
