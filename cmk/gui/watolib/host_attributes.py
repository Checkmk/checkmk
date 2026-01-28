#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="type-arg"

"""A host attribute is something that is inherited from folders to
hosts. Examples are the IP address and the host tags."""

from __future__ import annotations

import abc
import functools
import re
from collections.abc import Callable, Hashable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, NotRequired, TypedDict

from marshmallow import fields

import cmk.ccc.plugin_registry
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.ccc.site import SiteId
from cmk.ccc.translations import TranslationOptions
from cmk.ccc.user import UserId
from cmk.fields import String
from cmk.gui.config import Config
from cmk.gui.exceptions import MKUserError
from cmk.gui.form_specs.unstable import SingleChoiceElementExtended, SingleChoiceExtended
from cmk.gui.form_specs.unstable.legacy_converter import (
    TransformDataForLegacyFormatOrRecomposeFunction,
)
from cmk.gui.hooks import request_memoize
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _, _u
from cmk.gui.type_defs import Choices, CustomHostAttrSpec
from cmk.gui.utils.html import HTML
from cmk.gui.valuespec import Checkbox, DropdownChoice, TextInput, Transform, ValueSpec
from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import BooleanChoice, DefaultValue, FormSpec
from cmk.rulesets.v1.form_specs import String as StringFormSpec
from cmk.snmplib import SNMPCredentials  # astrein: disable=cmk-module-layer-violation
from cmk.utils.labels import Labels
from cmk.utils.tags import TagGroup, TagGroupID, TagID

_ContactgroupName = str


def register(host_attribute_topic_registry_: HostAttributeTopicRegistry) -> None:
    host_attribute_topic_registry_.register(HOST_ATTRIBUTE_TOPIC_BASIC_SETTINGS)
    host_attribute_topic_registry_.register(HOST_ATTRIBUTE_TOPIC_NETWORK_ADDRESS)
    host_attribute_topic_registry_.register(HOST_ATTRIBUTE_TOPIC_MONITORING_DATASOURCES)
    host_attribute_topic_registry_.register(HOST_ATTRIBUTE_TOPIC_HOST_TAGS)
    host_attribute_topic_registry_.register(HOST_ATTRIBUTE_TOPIC_NETWORK_SCAN)
    host_attribute_topic_registry_.register(HOST_ATTRIBUTE_TOPIC_MANAGEMENT_BOARD)
    host_attribute_topic_registry_.register(HOST_ATTRIBUTE_TOPIC_CUSTOM_ATTRIBUTES)
    host_attribute_topic_registry_.register(HOST_ATTRIBUTE_TOPIC_META_DATA)


# Keep in sync with cmk.fetchers._ipmi.IPMICredentials
# C&P to avoid the dependency which pulls in pyghmi
class IPMICredentials(TypedDict, total=False):
    username: str
    password: str


class HostContactGroupSpec(TypedDict):
    groups: list[_ContactgroupName]
    recurse_perms: bool
    use: bool
    use_for_services: bool
    recurse_use: bool


IPRange = (
    tuple[Literal["ip_range"], tuple[str, str]]
    | tuple[Literal["ip_network"], tuple[str, int]]
    | tuple[Literal["ip_list"], Sequence[HostAddress]]
)

ExcludeIPRange = IPRange | tuple[Literal["ip_regex_list"], Sequence[str]]


class NetworkScanSpec(TypedDict):
    ip_ranges: list[IPRange]
    exclude_ranges: list[ExcludeIPRange]
    scan_interval: int
    time_allowed: Sequence[tuple[tuple[int, int], tuple[int, int]]]
    set_ipaddress: bool
    tag_criticality: NotRequired[str]
    max_parallel_pings: NotRequired[int]
    run_as: UserId
    translate_names: NotRequired[TranslationOptions]


class NetworkScanResult(TypedDict):
    start: float | None
    end: float | Literal[True] | None
    state: bool | None
    output: str


class MetaData(TypedDict):
    # All the NotRequired should be investigated and cleaned up via cmk-update-config
    created_at: NotRequired[float]
    created_by: NotRequired[UserId | None]
    updated_at: NotRequired[float]


class MetricsAssociationAttributeFilter(TypedDict):
    key: str
    value: str


class MetricsAssociationAttributeFilters(TypedDict):
    resource_attributes: Sequence[MetricsAssociationAttributeFilter]
    scope_attributes: Sequence[MetricsAssociationAttributeFilter]
    data_point_attributes: Sequence[MetricsAssociationAttributeFilter]


class MetricsAssociationEnabled(TypedDict):
    attribute_filters: MetricsAssociationAttributeFilters
    host_name_resource_attribute_key: str


# Possible improvements for the future:
# - Might help to differentiate between effective attributes and non effective attributes, since
#   in effective attributes many more attributes are mandatory
# - Some attributes are actually folder specific (see ABCHostAttribute.show_in_folder)
# - How to represent the tag group attributes?
#   -> Built-in tags can be defined here while custom(izable) tag groups can not
# - How to represent custom host attributes?
#   -> The values are always of type str, but can have arbritary keys
class BuiltInHostAttributes(TypedDict, total=False):
    """All built-in host attributes to

    Host attributes are set on folders (mostly for inheritance to folders) and on hosts
    directly.
    """

    alias: str
    ipaddress: HostAddress
    ipv6address: HostAddress
    additional_ipv4addresses: Sequence[HostAddress]
    additional_ipv6addresses: Sequence[HostAddress]
    snmp_community: SNMPCredentials
    metrics_association: (
        tuple[Literal["enabled"], MetricsAssociationEnabled] | tuple[Literal["disabled"], None]
    )
    parents: Sequence[HostName]
    network_scan: NetworkScanSpec
    network_scan_result: NetworkScanResult
    management_address: HostAddress
    management_protocol: Literal["snmp", "ipmi"] | None
    management_snmp_community: SNMPCredentials
    management_ipmi_credentials: IPMICredentials
    site: SiteId
    # This is a list of 3 elements. tuple[SiteId, str, str] would be better.
    locked_by: Sequence[str]
    locked_attributes: Sequence[str]
    meta_data: MetaData
    inventory_failed: bool
    waiting_for_discovery: bool
    labels: Labels
    contactgroups: HostContactGroupSpec
    # Commerical editions only
    bake_agent_package: bool
    # Commerical editions only
    cmk_agent_connection: Literal["push-agent", "pull-agent"]
    # Ultimate editions only
    relay: str


class BuiltInHostTagGroups(TypedDict, total=False):
    tag_agent: Literal["cmk-agent", "all-agents", "special-agents", "no-agent"]
    tag_piggyback: Literal["auto-piggyback", "piggyback", "no-piggyback"]
    tag_snmp_ds: Literal["no-snmp", "snmp-v2", "snmp-v1"]
    tag_address_family: Literal["ip-v4-only", "ip-v6-only", "ip-v4v6", "no-ip"]


class HostAttributes(BuiltInHostAttributes, BuiltInHostTagGroups, total=False):
    """Built-in and custom host attributes"""

    # Shipped tag attributes, but could be changed or even removed by users.
    # So we don't define the shipped literals here
    tag_criticality: str


class CollectedHostAttributes(HostAttributes):
    path: str
    # Seems to be added during runtime in some cases. Clean this up
    edit_url: NotRequired[str]


def mask_attributes(attributes: Mapping[str, object]) -> dict[str, object]:
    """Create a copy of the given attributes and mask credential data"""

    MASK_STRING = "******"

    masked = dict(attributes)
    if "snmp_community" in masked:
        masked["snmp_community"] = MASK_STRING
    if "management_snmp_community" in masked:
        masked["management_snmp_community"] = MASK_STRING
    if ipmi := masked.get("management_ipmi_credentials"):
        username = ipmi.get("username", None) if isinstance(ipmi, dict) else None
        masked["management_ipmi_credentials"] = IPMICredentials(
            username=username or "(Unknown)", password=MASK_STRING
        )
    return masked


@dataclass(frozen=True, kw_only=True)
class HostAttributeTopic:
    """Host attribute topic"""

    """Unique internal ID of this attribute. Only ASCII characters allowed."""
    ident: str
    """Used as title for the attribute topics on the host edit page"""
    title: str
    """The topics are sorted by this number wherever displayed as a list"""
    sort_index: int


class HostAttributeTopicRegistry(cmk.ccc.plugin_registry.Registry[HostAttributeTopic]):
    def plugin_name(self, instance: HostAttributeTopic) -> str:
        return instance.ident

    def get_choices(self) -> Choices:
        return [(t.ident, t.title) for t in sorted(self.values(), key=lambda e: e.sort_index)]


host_attribute_topic_registry = HostAttributeTopicRegistry()


# TODO: Move these plugins?
HOST_ATTRIBUTE_TOPIC_BASIC_SETTINGS = HostAttributeTopic(
    ident="basic",
    title=_("Basic settings"),
    sort_index=0,
)

HOST_ATTRIBUTE_TOPIC_NETWORK_ADDRESS = HostAttributeTopic(
    ident="address",
    title=_("Network address"),
    sort_index=10,
)

HOST_ATTRIBUTE_TOPIC_MONITORING_DATASOURCES = HostAttributeTopic(
    ident="monitoring_agents",
    title=_("Monitoring agents"),
    sort_index=20,
)

HOST_ATTRIBUTE_TOPIC_HOST_TAGS = HostAttributeTopic(
    ident="host_tags",
    title=_("Host tags"),
    sort_index=30,
)

HOST_ATTRIBUTE_TOPIC_NETWORK_SCAN = HostAttributeTopic(
    ident="network_scan",
    title=_("Network scan"),
    sort_index=40,
)

HOST_ATTRIBUTE_TOPIC_MANAGEMENT_BOARD = HostAttributeTopic(
    ident="management_board",
    title=_("Management board"),
    sort_index=50,
)

HOST_ATTRIBUTE_TOPIC_CUSTOM_ATTRIBUTES = HostAttributeTopic(
    ident="custom_attributes",
    title=_("Custom attributes"),
    sort_index=35,
)


HOST_ATTRIBUTE_TOPIC_META_DATA = HostAttributeTopic(
    ident="meta_data",
    title=_("Creation / Locking"),
    sort_index=60,
)


class ABCHostAttribute(abc.ABC):
    """Base class for all registered host attributes"""

    @classmethod
    def sort_index(cls) -> int:
        return 85

    @abc.abstractmethod
    def name(self) -> str:
        """Return the name (= identifier) of the attribute"""
        raise NotImplementedError()

    @abc.abstractmethod
    def title(self) -> str:
        """Return the title to be displayed to the user"""
        raise NotImplementedError()

    @abc.abstractmethod
    def topic(self) -> HostAttributeTopic:
        raise NotImplementedError()

    @abc.abstractmethod
    def render_input(self, varprefix: str, value: Any) -> None:
        """Render HTML input fields displaying the value and
        make it editable. If filter == True, then the field
        is to be displayed in filter mode (as part of the
        search filter)"""
        raise NotImplementedError()

    @abc.abstractmethod
    def from_html_vars(self, varprefix: str) -> Any:
        """Create value from HTML variables."""
        raise NotImplementedError()

    def nagios_name(self) -> str | None:
        """Return the name of the Nagios configuration variable
        if this is a Nagios-bound attribute (e.g. "alias" or "_SERIAL")"""
        return None

    def is_explicit(self) -> bool:
        """The return value indicates if this attribute represents an explicit set
        value. Explicit attributes do not require cpu-intensive rule evaluations.
        Instead, an exclicit_host_config entry will be generated, e.g.
        explicit_host_config["alias"][hostname] = value

        Used in: hosts_and_folders:Folder:_save_hosts_file
        """
        return False

    def help(self) -> str | HTML | None:
        """Return an optional help text"""
        return None

    def default_value(self) -> Any:
        """Return the default value for new hosts"""
        return None

    def paint(self, value: Any, hostname: HostName) -> tuple[str, str | HTML]:
        """Render HTML code displaying a value"""
        return "", str(value)

    def may_edit(self) -> bool:
        """Whether or not the user is able to edit this attribute. If
        not, the value is shown read-only (when the user is permitted
        to see the attribute)."""
        return True

    def show_in_table(self) -> bool:
        """Whether or not to show this attribute in tables.
        This value is set by declare_host_attribute"""
        return True

    def show_in_form(self) -> bool:
        """Whether or not to show this attribute in the edit form.
        This value is set by declare_host_attribute"""
        return True

    def show_on_create(self) -> bool:
        """Whether or not to show this attribute during object creation."""
        return True

    def show_in_folder(self) -> bool:
        """Whether or not to make this attribute configurable in
        files and folders (as defaule value for the hosts)"""
        return True

    def show_in_host_search(self) -> bool:
        """Whether or not to make this attribute configurable in
        the host search form"""
        return True

    def show_in_host_cleanup(self) -> bool:
        """Whether or not to make this attribute selectable in
        the host cleanup form"""
        return self.editable()

    def editable(self) -> bool:
        """Whether or not this attribute can be edited using the GUI.
        This makes the attribute a read only attribute in the GUI."""
        return True

    def openapi_editable(self) -> bool:
        """If True, this attribute will be editable through the REST API,
        even when editable() is set to False."""
        return True

    def is_mandatory(self) -> bool:
        """Whether it is allowed that a host has no explicit
        value here (inherited or direct value). An mandatory
        has *no* default value."""
        return False

    def show_inherited_value(self) -> bool:
        """Return information about whether or not either the
        inherited value or the default value should be shown
        for an attribute.
        _depends_on_roles is set by declare_host_attribute()."""
        return True

    def depends_on_roles(self) -> list[str]:
        """Return information about the user roles we depend on.
        The method is usually not overridden, but the variable
        _depends_on_roles is set by declare_host_attribute()."""
        return []

    def depends_on_tags(self) -> list[str]:
        """Return information about the host tags we depend on.
        The method is usually not overridden, but the variable
        _depends_on_tags is set by declare_host_attribute()."""
        return []

    def from_config(self) -> bool:
        """Whether or not this attribute has been created from the
        config of the site.
        The method is usually not overridden, but the variable
        _from_config is set by declare_host_attribute()."""
        return False

    def needs_validation(self, for_what: str, new: bool) -> bool:
        """Check whether this attribute needs to be validated at all
        Attributes might be permanently hidden (show_in_form = False)
        or dynamically hidden by the depends_on_tags, editable features"""
        return (
            self.is_visible(for_what, new)
            and request.var("attr_display_%s" % self.name(), "1") == "1"
        )

    def is_visible(self, for_what: str, new: bool) -> bool:
        """Gets the type of current view as argument and returns whether or not
        this attribute is shown in this type of view"""
        if for_what == "always":
            return True

        if new and not self.show_on_create():
            return False

        if for_what in ["host", "cluster", "bulk"] and not self.show_in_form():
            return False

        if for_what == "folder" and not self.show_in_folder():
            return False

        if for_what == "host_search" and not self.show_in_host_search():
            return False

        return True

    def validate_input(self, value: Any, varprefix: str) -> None:
        """Check if the value entered by the user is valid.
        This method may raise MKUserError in case of invalid user input."""

    def to_nagios(self, value: Any) -> str | None:
        """If this attribute should be present in Nagios as a host custom
        macro, then the value of that macro should be returned here - otherwise None"""
        return None

    def filter_matches(self, crit: Any, value: Any, hostname: HostName) -> bool:
        """Checks if the give value matches the search attributes
        that are represented by the current HTML variables."""
        return crit == value

    def get_tag_groups(self, value: Any) -> Mapping[TagGroupID, TagID]:
        """Each attribute may set multiple tag groups for a host
        This is used for calculating the effective host tags when writing the hosts{.mk|.cfg}

        Only use this for tag group and tag combinations which are defined in the configuration of
        existing tags. The 'site' attribute violates this principle, but is kept for compatibility
        reasons. You may want to use labels instead, which give you more freedom.
        """
        return {}

    def labels(self, value: Any) -> Labels:
        """Set host labels based on the attributes value

        Returns a set of host labels which are added to the effective explicit hosts labels.
        """
        return {}

    @property
    def is_checkbox_tag(self) -> bool:
        return False

    @property
    def is_tag_attribute(self) -> bool:
        return False

    def is_show_more(self, config: Config) -> bool:
        """Whether or not this attribute is treated as an element only shown on
        show more button in the GUI"""
        return False

    @abc.abstractmethod
    def openapi_field(self) -> fields.Field:
        raise NotImplementedError()


class HostAttributeRegistry(cmk.ccc.plugin_registry.Registry[type[ABCHostAttribute]]):
    _index = 0

    def plugin_name(self, instance: type[ABCHostAttribute]) -> str:
        return instance().name()

    def registration_hook(self, instance: type[ABCHostAttribute]) -> None:
        """Add missing sort indizes

        Internally defined attributes have a defined sort index. Attributes defined by the users
        configuration, like tag based attributes or custom host attributes automatically get
        a sort index based on the last index used.
        """
        # FIXME: Replace this automatic implementation of sort_index in derived classes without
        # an own implementation by something more sane.
        if instance.sort_index.__code__ is ABCHostAttribute.sort_index.__code__:
            instance._sort_index = self.__class__._index  # type: ignore[attr-defined]
            instance.sort_index = classmethod(lambda c: c._sort_index)  # type: ignore[assignment]
            self.__class__._index += 1
        else:
            self.__class__._index = max(instance.sort_index(), self.__class__._index)


host_attribute_registry = HostAttributeRegistry()


def sorted_host_attributes(host_attributes: Sequence[ABCHostAttribute]) -> list[ABCHostAttribute]:
    """Return host attribute objects in the order they should be displayed (in edit dialogs)"""
    return sorted(host_attributes, key=lambda a: (a.sort_index(), a.topic().title))


def sorted_host_attribute_topics(
    host_attributes: Mapping[str, ABCHostAttribute], for_what: str, new: bool
) -> list[tuple[str, str]]:
    """Return a list of needed topics for the given "what".
    Only returns the topics that are used by a visible attribute"""
    needed_topics: set[HostAttributeTopic] = set()
    for attr in host_attributes.values():
        if attr.topic().ident not in [t.ident for t in needed_topics] and attr.is_visible(
            for_what, new
        ):
            needed_topics.add(attr.topic())

    return [
        (t.ident, t.title)
        for t in sorted(
            needed_topics,
            key=lambda e: (e.sort_index, e.title),
        )
    ]


def sorted_host_attributes_by_topic(
    host_attributes: Mapping[str, ABCHostAttribute],
    topic_id: str,
) -> list[ABCHostAttribute]:
    # Hack to sort the address family host tag attribute above the IPv4/v6 addresses
    # TODO: Clean this up by implementing some sort of explicit sorting
    def sort_host_attributes(a: ABCHostAttribute, b: ABCHostAttribute) -> int:
        if a.name() == "tag_address_family":
            return -1
        return 0

    sorted_attributes = []
    for attr in sorted(
        sorted_host_attributes(list(host_attributes.values())),
        key=functools.cmp_to_key(sort_host_attributes),
    ):
        if attr.topic().ident == host_attribute_topic_registry[topic_id].ident:
            sorted_attributes.append(attr)
    return sorted_attributes


# Kept for comatibility with pre 1.6 plugins
def declare_host_attribute(
    a: type[ABCHostAttribute],
    show_in_table: bool = True,
    show_in_folder: bool = True,
    show_in_host_search: bool = True,
    topic: str | HostAttributeTopic | None = None,
    sort_index: int | None = None,
    show_in_form: bool = True,
    depends_on_tags: list[str] | None = None,
    depends_on_roles: list[str] | None = None,
    editable: bool = True,
    show_inherited_value: bool = True,
    may_edit: Callable[[], bool] | None = None,
    from_config: bool = False,
) -> None:
    if not issubclass(a, ABCHostAttribute):
        raise MKGeneralException(
            _("Failed to load legacy host attribute from local plug-ins: %r") % a
        )

    attrs: dict[str, Any] = {}
    if depends_on_tags is not None:
        attrs["_depends_on_tags"] = depends_on_tags
        attrs["depends_on_tags"] = lambda self: self._depends_on_tags

    if depends_on_roles is not None:
        attrs["_depends_on_roles"] = depends_on_roles
        attrs["depends_on_roles"] = lambda self: self._depends_on_roles

    if topic is None or isinstance(topic, str):
        ident = str(topic).replace(" ", "_").lower() if topic else None
        attrs["_topic"] = _declare_host_attribute_topic(ident, str(topic))
    elif isinstance(topic, HostAttributeTopic):
        attrs["_topic"] = topic
    else:
        raise NotImplementedError()
    attrs["topic"] = lambda self: self._topic

    if may_edit is not None:
        attrs["_may_edit_func"] = (may_edit,)
        attrs["may_edit"] = lambda self: self._may_edit_func[0]()

    if sort_index is not None:
        attrs["_sort_index"] = sort_index
        attrs["sort_index"] = classmethod(lambda c: c._sort_index)

    attrs.update(
        {
            "_show_in_table": show_in_table,
            "show_in_table": lambda self: self._show_in_table,
            "_show_in_folder": show_in_folder,
            "show_in_folder": lambda self: self._show_in_folder,
            "_show_in_host_search": show_in_host_search,
            "show_in_host_search": lambda self: self._show_in_host_search,
            "_show_in_form": show_in_form,
            "show_in_form": lambda self: self._show_in_form,
            "_show_inherited_value": show_inherited_value,
            "show_inherited_value": lambda self: self._show_inherited_value,
            "_editable": editable,
            "editable": lambda self: self._editable,
            "_from_config": from_config,
            "from_config": lambda self: self._from_config,
        }
    )

    attrs["openapi_field"] = lambda self: String(description=self.help())

    # Apply the left over missing attributes that we get from the function arguments
    # by creating the final concrete class of this attribute
    final_class = type("%sConcrete" % a.__name__, (a,), attrs)
    host_attribute_registry.register(final_class)


def _declare_host_attribute_topic(ident: str | None, topic_title: str) -> HostAttributeTopic:
    """We get the "topic title" here. Create a topic class dynamically and
    returns a reference to this class"""
    if ident is None:
        return HOST_ATTRIBUTE_TOPIC_BASIC_SETTINGS

    if ident in host_attribute_topic_registry:
        return host_attribute_topic_registry[ident]

    topic = HostAttributeTopic(
        ident=ident,
        title=topic_title,
        sort_index=80,
    )
    host_attribute_topic_registry.register(topic)
    return topic


@request_memoize()
def config_based_tag_group_attributes(
    hashable_tag_groups_by_topic: _HashableTagGroupsByTopic,
) -> dict[str, ABCHostAttribute]:
    attributes: dict[str, ABCHostAttribute] = {}
    for topic_spec, tag_groups in hashable_tag_groups_by_topic.tag_groups_by_topic:
        for tag_group in tag_groups:
            # Try to translate the title to a built-in topic ID. In case this is not possible mangle the given
            # custom topic to an internal ID and create the topic on demand.
            # TODO: We need to adapt the tag data structure to contain topic IDs
            topic_id = transform_attribute_topic_title_to_id(topic_spec)

            # Build an internal ID from the given topic
            if topic_id is None:
                topic_id = str(re.sub(r"[^A-Za-z0-9_]+", "_", topic_spec)).lower()

            attribute = type(
                "HostAttributeTag%s" % str(tag_group.id).title(),
                (
                    (
                        ABCHostAttributeHostTagCheckbox
                        if tag_group.is_checkbox_tag_group
                        else ABCHostAttributeHostTagList
                    ),
                ),
                {
                    "_tag_group": tag_group,
                    "help": lambda _: tag_group.help,
                    "_topic": (
                        _declare_host_attribute_topic(topic_id, topic_spec)
                        if topic_id not in host_attribute_topic_registry
                        else host_attribute_topic_registry[topic_id]
                    ),
                    "topic": lambda self: self._topic,
                    "show_in_table": lambda self: False,
                    "show_in_folder": lambda self: True,
                    "from_config": lambda self: True,
                    "openapi_field": lambda self: String(description=self.help()),
                }
                | (
                    {
                        "_sort_index": sort_index,
                        "sort_index": classmethod(lambda c: c._sort_index),
                    }
                    if (sort_index := _tag_attribute_sort_index(tag_group))
                    else {}
                ),
            )()

            attributes[attribute.name()] = attribute
    return attributes


def host_attribute_matches(crit: str, value: str) -> bool:
    """Match *value* against *crit* for host searches.

    When *crit* starts with '~' treat the rest as a case-insensitive
    regular expression, otherwise apply a case-insensitive substring check."""
    if crit and crit[0] == "~":
        return re.search(crit[1:], value, re.IGNORECASE) is not None

    return crit.lower() in value.lower()


def _tag_attribute_sort_index(tag_group: TagGroup) -> int | None:
    """Return the host attribute sort index of tag group attributes

    The sort index is not configurable for tag groups, but we want some
    specific sorting at least for attributes that are related to other
    attributes (like the snmp tag group + snmp_community)"""
    if tag_group.id == "agent":
        return 63  # show above snmp_ds
    if tag_group.id == "snmp_ds":
        return 65  # show above snmp_community
    return None


class _HashableCustomHostAttrs:
    def __init__(self, host_attrs: Sequence[CustomHostAttrSpec]) -> None:
        self.host_attrs = host_attrs

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _HashableCustomHostAttrs):
            return False
        return self.host_attrs == other.host_attrs

    def __hash__(self) -> int:
        return hash(tuple(tuple(x.items()) for x in self.host_attrs))


def _make_hashable_object(obj: object) -> Hashable:
    try:
        # Note: Class instances are always hashed by id() if not specified otherwise
        #       So they have to be immutable
        hash(obj)
        return obj
    except TypeError:
        pass

    if isinstance(obj, dict):
        new_obj = {}
        for key, value in obj.items():
            new_obj[key] = _make_hashable_object(value)
        return frozenset(new_obj)
    if isinstance(obj, list | tuple):
        return tuple(_make_hashable_object(item) for item in obj)

    raise TypeError("Unsupported type for hashable object")


class _HashableTagGroupsByTopic:
    def __init__(self, tag_groups_by_topic: Sequence[tuple[str, Sequence[TagGroup]]]) -> None:
        self.tag_groups_by_topic = tag_groups_by_topic

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _HashableTagGroupsByTopic):
            return False
        return hash(self) == hash(other)

    def __hash__(self) -> int:
        return hash(_make_hashable_object(self.tag_groups_by_topic))


@request_memoize()
def config_based_custom_host_attribute_sync_plugins(
    hashable_host_attrs: _HashableCustomHostAttrs,
) -> dict[str, ABCHostAttribute]:
    attributes: dict[str, ABCHostAttribute] = {}
    for attr in hashable_host_attrs.host_attrs:
        vs = TextInput(
            title=attr["title"],
            help=attr["help"],
        )

        fs = StringFormSpec(
            title=Title(attr["title"]),  # astrein: disable=localization-checker
            help_text=Help(attr["help"]),  # astrein: disable=localization-checker
        )

        a: type[ABCHostAttributeValueSpec]
        if attr["add_custom_macro"]:
            a = NagiosValueSpecAttribute(attr["name"], "_" + attr["name"], vs, fs)
        else:
            a = ValueSpecAttribute(attr["name"], vs, fs)

        final_class = type(
            "%sCustomHostAttr" % a.__name__,
            (a,),
            {
                "from_config": lambda self: True,
                "openapi_field": lambda self: String(description=self.help()),
                # Previous to 1.6 the topic was a the "topic title". Since 1.6
                # it's the internal ID of the topic. Because referenced topics may
                # have been removed, be compatible and dynamically create a topic
                # in case one is missing.
                "_topic": _declare_host_attribute_topic(attr["topic"], attr["topic"].title()),
                "topic": lambda self: self._topic,
            },
        )
        attributes[attr["name"]] = final_class()
    return attributes


def transform_attribute_topic_title_to_id(topic_title: str) -> str | None:
    _topic_title_to_id_map = {
        "Basic settings": "basic",
        "Address": "address",
        "Monitoring agents": "monitoring_agents",
        "Management board": "management_board",
        "Network scan": "network_scan",
        "Custom attributes": "custom_attributes",
        "Host tags": "custom_attributes",
        "Tags": "custom_attributes",
        "Grundeinstellungen": "basic",
        "Adresse": "address",
        "Monitoringagenten": "monitoring_agents",
        "Management-Board": "management_board",
        "Netzwerk-Scan": "network_scan",
        "Eigene Attribute": "custom_attributes",
        "Hostmerkmale": "custom_attributes",
        "Merkmale": "custom_attributes",
    }

    try:
        return _topic_title_to_id_map[topic_title]
    except KeyError:
        return None


def all_host_attributes(
    host_attributes: Sequence[CustomHostAttrSpec],
    tag_groups_by_topic: Sequence[tuple[str, Sequence[TagGroup]]],
) -> dict[str, ABCHostAttribute]:
    result = (
        {ident: cls() for ident, cls in host_attribute_registry.items()}
        | config_based_tag_group_attributes(_HashableTagGroupsByTopic(tag_groups_by_topic))
        | config_based_custom_host_attribute_sync_plugins(_HashableCustomHostAttrs(host_attributes))
    )
    return result


# This is the counterpart of "configure_attributes". Another place which
# is related to these HTTP variables and so on is SearchFolder.
def collect_attributes(
    host_attributes: Mapping[str, ABCHostAttribute],
    for_what: str,
    new: bool,
    do_validate: bool = True,
    varprefix: str = "",
) -> HostAttributes:
    """Read attributes from HTML variables"""
    host = HostAttributes()
    for attr in host_attributes.values():
        attrname = attr.name()
        if not request.var(for_what + "_change_%s" % attrname, ""):
            continue

        value = attr.from_html_vars(varprefix)

        if do_validate and attr.needs_validation(for_what, new):
            attr.validate_input(value, varprefix)

        # Mypy can not help here with the dynamic key
        host[attrname] = value  # type: ignore[literal-required]
    return host


class ABCHostAttributeText(ABCHostAttribute, abc.ABC):
    """A simple text attribute. It is stored in a Python unicode string"""

    @property
    def _allow_empty(self) -> bool:
        return True

    @property
    def _size(self) -> int:
        return 25

    def paint(self, value: str, hostname: HostName) -> tuple[str, str | HTML]:
        if not value:
            return "", ""
        return "", value

    def render_input(self, varprefix: str, value: str | None) -> None:
        if value is None:
            value = ""
        html.text_input(varprefix + "attr_" + self.name(), value, size=self._size)

    def from_html_vars(self, varprefix: str) -> str | None:
        value = request.get_str_input(varprefix + "attr_" + self.name())
        if value is None:
            value = ""
        return value.strip()

    def validate_input(self, value: str | None, varprefix: str) -> None:
        if self.is_mandatory() and not value:
            raise MKUserError(
                varprefix + "attr_" + self.name(),
                _("Please specify a value for %s") % self.title(),
            )
        if not self._allow_empty and (value is None or not value.strip()):
            raise MKUserError(
                varprefix + "attr_" + self.name(),
                _("%s may be missing, it must not be empty if it is set.") % self.title(),
            )

    def filter_matches(self, crit: str, value: str | None, hostname: HostName) -> bool:
        if value is None:  # Host does not have this attribute
            value = ""

        return host_attribute_matches(crit, value)

    def default_value(self) -> str:
        return ""


class ABCHostAttributeValueSpec(ABCHostAttribute):
    """An attribute using the generic ValueSpec mechanism"""

    @abc.abstractmethod
    def valuespec(self) -> ValueSpec:
        raise NotImplementedError()

    def form_spec(self) -> FormSpec:
        raise NotImplementedError()

    def title(self) -> str:
        title = self.valuespec().title()
        assert title is not None
        return title

    def help(self) -> str | HTML | None:
        return self.valuespec().help()

    def default_value(self) -> Any:
        return self.valuespec().default_value()

    def paint(self, value: Any, hostname: HostName) -> tuple[str, str | HTML]:
        return "", self.valuespec().value_to_html(value)

    def render_input(self, varprefix: str, value: Any) -> None:
        self.valuespec().render_input(varprefix + self.name(), value)

    def from_html_vars(self, varprefix: str) -> Any:
        return self.valuespec().from_html_vars(varprefix + self.name())

    def validate_input(self, value: Any, varprefix: str) -> None:
        vs = self.valuespec()
        prefix = varprefix + self.name()
        vs.validate_datatype(value, prefix)
        vs.validate_value(value, prefix)


class ABCHostAttributeFixedText(ABCHostAttributeText, abc.ABC):
    """A simple text attribute that is not editable by the user.

    It can be used to store context information from other
    systems (e.g. during an import of a host database from
    another system)."""

    def render_input(self, varprefix: str, value: str | None) -> None:
        if value is not None:
            html.hidden_field(varprefix + "attr_" + self.name(), value)
            html.write_text_permissive(value)

    def from_html_vars(self, varprefix: str) -> str | None:
        return request.var(varprefix + "attr_" + self.name())


class ABCHostAttributeNagiosText(ABCHostAttributeText):
    """A text attribute that is stored in a Nagios custom macro"""

    @abc.abstractmethod
    def nagios_name(self) -> str:
        raise NotImplementedError()

    def to_nagios(self, value: str) -> str | None:
        if value:
            return value
        return None


class ABCHostAttributeEnum(ABCHostAttribute):
    """An attribute for selecting one item out of list using a drop down box (<select>)

    Enumlist is a list of pairs of keyword / title. The type of value is
    string.  In all cases where no value is defined or the value is not in the
    enumlist, the default value is being used."""

    @property
    @abc.abstractmethod
    def _enumlist(self) -> Sequence[tuple[str, str]]:
        raise NotImplementedError()

    def paint(self, value: Any, hostname: HostName) -> tuple[str, str | HTML]:
        return "", dict(self._enumlist).get(value, self.default_value())

    def render_input(self, varprefix: str, value: str) -> None:
        html.dropdown(varprefix + "attr_" + self.name(), self._enumlist, value)

    def from_html_vars(self, varprefix: str) -> str | None:
        return request.var(varprefix + "attr_" + self.name(), self.default_value())


class ABCHostAttributeTag(ABCHostAttributeValueSpec, abc.ABC):
    @property
    @abc.abstractmethod
    def is_checkbox_tag(self) -> bool:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def _tag_group(self) -> TagGroup:
        raise NotImplementedError()

    def name(self) -> str:
        return "tag_%s" % self._tag_group.id

    @property
    def is_tag_attribute(self) -> bool:
        return True

    def get_tag_groups(self, value: TagID | None) -> Mapping[TagGroupID, TagID]:
        """Return set of tag groups to set (handles secondary tags)"""
        return self._tag_group.get_tag_group_config(value)

    def is_show_more(self, config: Config) -> bool:
        return self._tag_group.id in ["criticality", "networking", "piggyback"]


class ABCHostAttributeHostTagList(ABCHostAttributeTag, abc.ABC):
    """A selection dropdown for a host tag"""

    def valuespec(self) -> ValueSpec:
        # Since encode_value=False is set it is not possible to use empty tag
        # ID selections (Value: "None"). Transform that back and forth to make
        # that work.
        choices = [(k or "", v) for k, v in self._tag_group.get_tag_choices()]
        return Transform(
            valuespec=DropdownChoice(
                title=self._tag_group.title,
                choices=choices,
                default_value=choices[0][0],
                on_change="cmk.wato.fix_visibility();",
                encode_value=False,
            ),
            to_valuespec=lambda s: "" if s is None else s,
            from_valuespec=lambda s: None if s == "" else s,
        )

    def form_spec(self) -> SingleChoiceExtended:
        choices = [(k or "", v) for k, v in self._tag_group.get_tag_choices()]
        return SingleChoiceExtended(
            title=Title(  # astrein: disable=localization-checker
                self._tag_group.title
            ),
            elements=[
                SingleChoiceElementExtended(
                    name=choice[0],
                    title=Title(choice[1]),  # astrein: disable=localization-checker
                )
                for choice in choices
            ],
            prefill=DefaultValue(choices[0][0]),
        )

    @property
    def is_checkbox_tag(self) -> bool:
        return False

    @property
    def is_tag_attribute(self) -> bool:
        return True


class ABCHostAttributeHostTagCheckbox(ABCHostAttributeTag, abc.ABC):
    """A checkbox for a host tag group"""

    def _valuespec(self) -> Checkbox:
        choice = self._tag_group.get_tag_choices()[0]
        return Checkbox(
            title=self._tag_group.title,
            label=_u(choice[1]),
            true_label=self._tag_group.title,
            false_label="{} {}".format(_("Not"), self._tag_group.title),
            onclick="cmk.wato.fix_visibility();",
        )

    def valuespec(self) -> Transform:
        return Transform(
            valuespec=self._valuespec(),
            to_valuespec=lambda s: s == self._tag_value(),
            from_valuespec=lambda s: self._tag_value() if s is True else None,
        )

    def form_spec(self) -> TransformDataForLegacyFormatOrRecomposeFunction:
        return TransformDataForLegacyFormatOrRecomposeFunction(
            wrapped_form_spec=BooleanChoice(
                title=Title(  # astrein: disable=localization-checker
                    self._tag_group.title
                ),
                label=Label(  # astrein: disable=localization-checker
                    self._tag_group.get_tag_choices()[0][1]
                ),
            ),
            from_disk=lambda s: s == self._tag_value(),
            to_disk=lambda s: self._tag_value() if s is True else None,
        )

    @property
    def is_checkbox_tag(self) -> bool:
        return True

    def render_input(self, varprefix: str, value: TagID | None) -> None:
        self._valuespec().render_input(varprefix + self.name(), bool(value))

    def _tag_value(self) -> TagID | None:
        return self._tag_group.get_tag_choices()[0][0]

    def get_tag_groups(self, value: TagID | None) -> Mapping[TagGroupID, TagID]:
        if not value:
            return {}
        return super().get_tag_groups(self._tag_value())


class ABCHostAttributeNagiosValueSpec(ABCHostAttributeValueSpec):
    @abc.abstractmethod
    def nagios_name(self) -> str:
        raise NotImplementedError()

    def to_nagios(self, value: str) -> str | None:
        rendered = self.valuespec().value_to_html(value)
        if rendered:
            return str(rendered)
        return None

    def is_explicit(self) -> bool:
        return True


# TODO: Kept for pre 1.6 plug-in compatibility
def TextAttribute(
    name: str,
    title: str,
    help_txt: str | None = None,
    default_value: str = "",
    mandatory: bool = False,
    allow_empty: bool = True,
    size: int = 25,
) -> type[ABCHostAttributeText]:
    return type(
        "HostAttribute%s" % name.title(),
        (ABCHostAttributeText,),
        {
            "_name": name,
            "name": lambda self: self._name,
            "_title": title,
            "title": lambda self: self._title,
            "_help": help_txt,
            "help": lambda self: self._help,
            "_default_value": default_value,
            "default_value": lambda self: self._default_value,
            "_mandatory": mandatory,
            "is_mandatory": lambda self: self._mandatory,
            "_allow_empty": allow_empty,
            "_size": size,
        },
    )


# TODO: Kept for pre 1.6 plug-in compatibility
def NagiosTextAttribute(
    name: str,
    nag_name: str,
    title: str,
    help_txt: str | None = None,
    default_value: str = "",
    mandatory: bool = False,
    allow_empty: bool = True,
    size: int = 25,
) -> type[ABCHostAttributeNagiosText]:
    return type(
        "HostAttribute%s" % name.title(),
        (ABCHostAttributeNagiosText,),
        {
            "_name": name,
            "name": lambda self: self._name,
            "_title": title,
            "title": lambda self: self._title,
            "_help": help_txt,
            "help": lambda self: self._help,
            "_default_value": default_value,
            "default_value": lambda self: self._default_value,
            "_mandatory": mandatory,
            "is_mandatory": lambda self: self._mandatory,
            "_allow_empty": allow_empty,
            "_size": size,
            "_nagios_name": nag_name,
            "nagios_name": lambda self: self._nagios_name,
        },
    )


# TODO: Kept for pre 1.6 plug-in compatibility
def FixedTextAttribute(
    name: str, title: str, help_txt: str | None = None
) -> type[ABCHostAttributeFixedText]:
    return type(
        "HostAttributeFixedText%s" % name.title(),
        (ABCHostAttributeFixedText,),
        {
            "_name": name,
            "name": lambda self: self._name,
            "_title": title,
            "title": lambda self: self._title,
            "_help": help_txt,
            "help": lambda self: self._help,
        },
    )


# TODO: Kept for pre 1.6 plug-in compatibility
def ValueSpecAttribute(
    name: str, vs: ValueSpec, fs: FormSpec | None = None
) -> type[ABCHostAttributeValueSpec]:
    attrs = {
        "_name": name,
        "name": lambda self: self._name,
        "_valuespec": vs,
        "valuespec": lambda self: self._valuespec,
    }
    if fs is not None:
        attrs["_form_spec"] = fs
        attrs["form_spec"] = lambda self: self._form_spec
    return type(
        "HostAttributeValueSpec%s" % name.title(),
        (ABCHostAttributeValueSpec,),
        attrs,
    )


# TODO: Kept for pre 1.6 plug-in compatibility
def NagiosValueSpecAttribute(
    name: str, nag_name: str, vs: ValueSpec, fs: FormSpec | None = None
) -> type[ABCHostAttributeNagiosValueSpec]:
    attrs = {
        "_name": name,
        "name": lambda self: self._name,
        "_valuespec": vs,
        "valuespec": lambda self: self._valuespec,
        "_nagios_name": nag_name,
        "nagios_name": lambda self: self._nagios_name,
    }
    if fs is not None:
        attrs["_form_spec"] = fs
        attrs["form_spec"] = lambda self: self._form_spec
    return type(
        "NagiosValueSpecAttribute%s" % name.title(),
        (ABCHostAttributeNagiosValueSpec,),
        attrs,
    )


# TODO: Kept for pre 1.6 plug-in compatibility
def EnumAttribute(
    name: str,
    title: str,
    help_txt: str,
    default_value: str,
    enumlist: Sequence[tuple[str, str]],
) -> type[ABCHostAttributeEnum]:
    return type(
        "HostAttributeEnum%s" % name.title(),
        (ABCHostAttributeEnum,),
        {
            "_name": name,
            "name": lambda self: self._name,
            "_title": title,
            "title": lambda self: self._title,
            "_help": help_txt,
            "help": lambda self: self._help,
            "_default_value": default_value,
            "default_value": lambda self: self._default_value,
            "_enumlist": enumlist,
        },
    )


@request_memoize(maxsize=1024)
def get_host_attribute_default_value(host_attribute: ABCHostAttribute) -> Any:
    return host_attribute.default_value()
