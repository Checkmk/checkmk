#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""A host attribute is something that is inherited from folders to
hosts. Examples are the IP address and the host tags."""

import abc
import functools
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Type

import cmk.utils.plugin_registry

import cmk.gui.config as config
from cmk.gui.globals import html
from cmk.gui.i18n import _, _u
from cmk.gui.exceptions import MKUserError, MKGeneralException
from cmk.gui.valuespec import (
    TextAscii,
    Transform,
    Checkbox,
    DropdownChoice,
)
from cmk.gui.watolib.utils import host_attribute_matches


class HostAttributeTopic(metaclass=abc.ABCMeta):
    @abc.abstractproperty
    def ident(self) -> str:
        """Unique internal ID of this attribute. Only ASCII characters allowed."""
        raise NotImplementedError()

    @abc.abstractproperty
    def title(self) -> str:
        """Used as title for the attribute topics on the host edit page"""
        raise NotImplementedError()

    @abc.abstractproperty
    def sort_index(self) -> int:
        """The topics are sorted by this number wherever displayed as a list"""
        raise NotImplementedError()


class HostAttributeTopicRegistry(cmk.utils.plugin_registry.Registry[Type[HostAttributeTopic]]):
    def plugin_name(self, instance: Type[HostAttributeTopic]):
        return instance().ident

    def get_choices(self):
        return [
            (t.ident, t.title)
            for t in sorted([t_class() for t_class in self.values()], key=lambda e: e.sort_index)
        ]


host_attribute_topic_registry = HostAttributeTopicRegistry()


# TODO: Move these plugins?
@host_attribute_topic_registry.register
class HostAttributeTopicBasicSettings(HostAttributeTopic):
    @property
    def ident(self):
        return "basic"

    @property
    def title(self):
        return _("Basic settings")

    @property
    def sort_index(self):
        return 0


@host_attribute_topic_registry.register
class HostAttributeTopicAddress(HostAttributeTopic):
    @property
    def ident(self):
        return "address"

    @property
    def title(self):
        return _("Network Address")

    @property
    def sort_index(self):
        return 10


@host_attribute_topic_registry.register
class HostAttributeTopicDataSources(HostAttributeTopic):
    @property
    def ident(self):
        return "data_sources"

    @property
    def title(self):
        return _("Data sources")

    @property
    def sort_index(self):
        return 20


@host_attribute_topic_registry.register
class HostAttributeTopicHostTags(HostAttributeTopic):
    @property
    def ident(self):
        return "host_tags"

    @property
    def title(self):
        return _("Host tags")

    @property
    def sort_index(self):
        return 30


@host_attribute_topic_registry.register
class HostAttributeTopicNetworkScan(HostAttributeTopic):
    @property
    def ident(self):
        return "network_scan"

    @property
    def title(self):
        return _("Network Scan")

    @property
    def sort_index(self):
        return 40


@host_attribute_topic_registry.register
class HostAttributeTopicManagementBoard(HostAttributeTopic):
    @property
    def ident(self):
        return "management_board"

    @property
    def title(self):
        return _("Management Board")

    @property
    def sort_index(self):
        return 50


@host_attribute_topic_registry.register
class HostAttributeTopicCustomAttributes(HostAttributeTopic):
    @property
    def ident(self):
        return "custom_attributes"

    @property
    def title(self):
        return _("Custom attributes")

    @property
    def sort_index(self):
        return 35


@host_attribute_topic_registry.register
class HostAttributeTopicMetaData(HostAttributeTopic):
    @property
    def ident(self):
        return "meta_data"

    @property
    def title(self):
        return _("Creation / Locking")

    @property
    def sort_index(self):
        return 60


class ABCHostAttribute(metaclass=abc.ABCMeta):
    """Base class for all registered host attributes"""
    @classmethod
    def sort_index(cls):
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
    def topic(self) -> Type[HostAttributeTopic]:
        raise NotImplementedError()

    @abc.abstractmethod
    def render_input(self, varprefix, value):
        """Render HTML input fields displaying the value and
        make it editable. If filter == True, then the field
        is to be displayed in filter mode (as part of the
        search filter)"""
        raise NotImplementedError()

    @abc.abstractmethod
    def from_html_vars(self, varprefix):
        """Create value from HTML variables."""
        raise NotImplementedError()

    def nagios_name(self) -> Optional[str]:
        """Return the name of the Nagios configuration variable
        if this is a Nagios-bound attribute (e.g. "alias" or "_SERIAL")"""
        return None

    def help(self) -> Optional[str]:
        """Return an optional help text"""
        return None

    def default_value(self):
        """Return the default value for new hosts"""
        return None

    def paint(self, value, hostname):
        """Render HTML code displaying a value"""
        return "", value

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

    def depends_on_roles(self) -> List[str]:
        """Return information about the user roles we depend on.
        The method is usually not overridden, but the variable
        _depends_on_roles is set by declare_host_attribute()."""
        return []

    def depends_on_tags(self) -> List[str]:
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
        if not self.is_visible(for_what, new):
            return False
        if not html:
            return True
        return html.request.var('attr_display_%s' % self.name(), "1") == "1"

    def is_visible(self, for_what: str, new: bool) -> bool:
        """Gets the type of current view as argument and returns whether or not
        this attribute is shown in this type of view"""

        if new and not self.show_on_create():
            return False

        if for_what in ["host", "cluster", "bulk"] and not self.show_in_form():
            return False

        if for_what == "folder" and not self.show_in_folder():
            return False

        if for_what == "host_search" and not self.show_in_host_search():
            return False

        return True

    def validate_input(self, value, varprefix):
        """Check if the value entered by the user is valid.
        This method may raise MKUserError in case of invalid user input."""

    def to_nagios(self, value):
        """If this attribute should be present in Nagios as a host custom
        macro, then the value of that macro should be returned here - otherwise None"""
        return None

    def filter_matches(self, crit: Any, value: Any, hostname: str) -> bool:
        """Checks if the give value matches the search attributes
        that are represented by the current HTML variables."""
        return crit == value

    def get_tag_groups(self, value: Any) -> Dict[str, str]:
        """Each attribute may set multiple tag groups for a host
        This is used for calculating the effective host tags when writing the hosts.mk"""
        return {}

    @property
    def is_checkbox_tag(self) -> bool:
        return False

    @property
    def is_tag_attribute(self) -> bool:
        return False

    def is_show_more(self) -> bool:
        """Whether or not this attribute is treated as an element only shown on
        show more button in the GUI"""
        return False


class HostAttributeRegistry(cmk.utils.plugin_registry.Registry[Type[ABCHostAttribute]]):
    _index = 0

    def plugin_name(self, instance: Type[ABCHostAttribute]) -> str:
        return instance().name()

    def registration_hook(self, instance: Type[ABCHostAttribute]) -> None:
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

    def attributes(self):
        return [cls() for cls in self.values()]

    def get_sorted_host_attributes(self) -> List[ABCHostAttribute]:
        """Return host attribute objects in the order they should be displayed (in edit dialogs)"""
        return sorted(self.attributes(), key=lambda a: (a.sort_index(), a.topic()().title))

    def get_choices(self):
        return [(a.name(), a.title()) for a in self.get_sorted_host_attributes()]


host_attribute_registry = HostAttributeRegistry()


def get_sorted_host_attribute_topics(for_what: str, new: bool) -> List[Tuple[str, str]]:
    """Return a list of needed topics for the given "what".
    Only returns the topics that are used by a visible attribute"""
    needed_topics: Set[Type[HostAttributeTopic]] = set()
    for attr_class in host_attribute_registry.values():
        attr = attr_class()
        if attr.topic() not in needed_topics and attr.is_visible(for_what, new):
            needed_topics.add(attr.topic())

    return [(t.ident, t.title) for t in sorted([t_class() for t_class in needed_topics],
                                               key=lambda e: (e.sort_index, e.title))]


def get_sorted_host_attributes_by_topic(topic_id):
    # Hack to sort the address family host tag attribute above the IPv4/v6 addresses
    # TODO: Clean this up by implementing some sort of explicit sorting
    def sort_host_attributes(a, b):
        if a.name() == "tag_address_family":
            return -1
        return 0

    sorted_attributes = []
    for attr in sorted(host_attribute_registry.get_sorted_host_attributes(),
                       key=functools.cmp_to_key(sort_host_attributes)):
        if attr.topic() == host_attribute_topic_registry[topic_id]:
            sorted_attributes.append(attr)
    return sorted_attributes


# Is used for dynamic host attribute declaration (based on host tags)
# + Kept for comatibility with pre 1.6 plugins
def declare_host_attribute(a,
                           show_in_table=True,
                           show_in_folder=True,
                           show_in_host_search=True,
                           topic=None,
                           sort_index=None,
                           show_in_form=True,
                           depends_on_tags=None,
                           depends_on_roles=None,
                           editable=True,
                           show_inherited_value=True,
                           may_edit=None,
                           from_config=False):

    if not issubclass(a, ABCHostAttribute):
        raise MKGeneralException(
            _("Failed to load legacy host attribute from local plugins: %r") % a)

    attrs = {}
    if depends_on_tags is not None:
        attrs["_depends_on_tags"] = depends_on_tags
        attrs["depends_on_tags"] = lambda self: self._depends_on_tags

    if depends_on_roles is not None:
        attrs["_depends_on_roles"] = depends_on_roles
        attrs["depends_on_roles"] = lambda self: self._depends_on_roles

    if topic is None or isinstance(topic, str):
        ident = str(topic).replace(" ", "_").lower() if topic else None
        attrs["_topic"] = _declare_host_attribute_topic(ident, topic)
    elif issubclass(topic, HostAttributeTopic):
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

    attrs.update({
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
    })

    # Apply the left over missing attributes that we get from the function arguments
    # by creating the final concrete class of this attribute
    final_class = type("%sConcrete" % a.__name__, (a,), attrs)
    host_attribute_registry.register(final_class)


def _declare_host_attribute_topic(ident, topic_title):
    """We get the "topic title" here. Create a topic class dynamically and
    returns a reference to this class"""
    if ident is None:
        return HostAttributeTopicBasicSettings

    try:
        return host_attribute_topic_registry[ident]
    except KeyError:
        pass

    topic_class = type("DynamicHostAttributeTopic%s" % ident.title(), (HostAttributeTopic,), {
        "ident": ident,
        "title": topic_title,
        "sort_index": 80,
    })
    host_attribute_topic_registry.register(topic_class)
    return topic_class


def undeclare_host_attribute(attrname):
    if attrname in host_attribute_registry:
        host_attribute_registry.unregister(attrname)


def undeclare_host_tag_attribute(tag_id):
    attrname = "tag_" + tag_id
    undeclare_host_attribute(attrname)


_update_config_based_host_attributes_config_hash: Optional[str] = None


def _update_config_based_host_attributes() -> None:
    global _update_config_based_host_attributes_config_hash

    def _compute_config_hash() -> str:
        return str(hash(repr(config.tags.get_dict_format()))) + repr(config.wato_host_attrs)

    # The topic conversion needs to take place before the _compute_config_hash runs
    # The actual generated topics may be pre-1.5 converted topics
    # e.g. "Custom attributes" -> "custom_attributes"
    # If we do not convert the topics here, the config_hash comparison will always fail
    transform_pre_16_host_topics(config.wato_host_attrs)

    if _update_config_based_host_attributes_config_hash == _compute_config_hash():
        return  # No re-register needed :-)

    _clear_config_based_host_attributes()
    _declare_host_tag_attributes()
    declare_custom_host_attrs()

    from cmk.gui.watolib.hosts_and_folders import Folder  # pylint: disable=import-outside-toplevel
    Folder.invalidate_caches()

    _update_config_based_host_attributes_config_hash = _compute_config_hash()


# Make the config module initialize the host attributes after loading the config
config.register_post_config_load_hook(_update_config_based_host_attributes)


def _clear_config_based_host_attributes():
    for attr in host_attribute_registry.attributes():
        if attr.from_config():
            undeclare_host_attribute(attr.name())


def _declare_host_tag_attributes():
    for topic_spec, tag_groups in config.tags.get_tag_groups_by_topic():
        for tag_group in tag_groups:
            # Try to translate the title to a builtin topic ID. In case this is not possible mangle the given
            # custom topic to an internal ID and create the topic on demand.
            # TODO: We need to adapt the tag data structure to contain topic IDs
            topic_id = _transform_attribute_topic_title_to_id(topic_spec)

            # Build an internal ID from the given topic
            if topic_id is None:
                topic_id = str(re.sub(r"[^A-Za-z0-9_]+", "_", topic_spec)).lower()

            if topic_id not in host_attribute_topic_registry:
                topic = _declare_host_attribute_topic(topic_id, topic_spec)
            else:
                topic = host_attribute_topic_registry[topic_id]

            declare_host_attribute(
                _create_tag_group_attribute(tag_group),
                show_in_table=False,
                show_in_folder=True,
                topic=topic,
                sort_index=_tag_attribute_sort_index(tag_group),
                from_config=True,
            )


def _tag_attribute_sort_index(tag_group):
    """Return the host attribute sort index of tag group attributes

    The sort index is not configurable for tag groups, but we want some
    specific sorting at least for attributes that are related to other
    attributes (like the snmp tag group + snmp_community)"""
    if tag_group.id == "agent":
        return 63  # show above snmp_ds
    if tag_group.id == "snmp_ds":
        return 65  # show above snmp_community
    return None


def _create_tag_group_attribute(tag_group):
    if tag_group.is_checkbox_tag_group:
        base_class: Type = ABCHostAttributeHostTagCheckbox
    else:
        base_class = ABCHostAttributeHostTagList

    return type("HostAttributeTag%s" % str(tag_group.id).title(), (base_class,), {
        "_tag_group": tag_group,
        "help": lambda _: tag_group.help,
    })


def declare_custom_host_attrs():
    for attr in transform_pre_16_host_topics(config.wato_host_attrs):
        if attr['type'] == "TextAscii":
            # Hack: The API does not perform validate_datatype and we can currently not enable
            # this as fix in 1.6 (see cmk/gui/plugins/webapi/utils.py::ABCHostAttributeValueSpec.validate_input()).
            # As a local workaround we use a custom validate function here to ensure we only get ascii characters
            vs = TextAscii(title=attr['title'], help=attr['help'], validate=_validate_is_ascii)
        else:
            raise NotImplementedError()

        if attr['add_custom_macro']:
            a = NagiosValueSpecAttribute(attr["name"], "_" + attr["name"], vs)
        else:
            a = ValueSpecAttribute(attr["name"], vs)

        # Previous to 1.6 the topic was a the "topic title". Since 1.6
        # it's the internal ID of the topic. Because referenced topics may
        # have been removed, be compatible and dynamically create a topic
        # in case one is missing.
        topic_class = _declare_host_attribute_topic(attr['topic'], attr['topic'].title())

        declare_host_attribute(
            a,
            show_in_table=attr['show_in_table'],
            topic=topic_class,
            from_config=True,
        )


def _validate_is_ascii(value, varprefix):
    if isinstance(value, str):
        try:
            value.encode("ascii")
        except UnicodeEncodeError:
            raise MKUserError(varprefix, _("Non-ASCII characters are not allowed here."))
    elif isinstance(value, bytes):
        try:
            value.decode("ascii")
        except UnicodeDecodeError:
            raise MKUserError(varprefix, _("Non-ASCII characters are not allowed here."))


def transform_pre_16_host_topics(custom_attributes):
    """Previous to 1.6 the titles of the host attribute topics were stored.

    This lead to issues with localized topics. We now have internal IDs for
    all the topics and try to convert the values here to the new format.

    We translate the titles which have been distributed with Check_MK to their
    internal topic ID. No action should be needed. Custom topics or topics of
    other languages are not translated. The attributes are put into the
    "Custom attributes" topic once. Users will have to re-configure the topic,
    sorry :-/."""
    for custom_attr in custom_attributes:
        if custom_attr["topic"] in host_attribute_topic_registry:
            continue

        custom_attr["topic"] = _transform_attribute_topic_title_to_id(
            custom_attr["topic"]) or "custom_attributes"

    return custom_attributes


def _transform_attribute_topic_title_to_id(topic_title):
    _topic_title_to_id_map = {
        u"Basic settings": "basic",
        u"Address": "address",
        u"Data sources": "data_sources",
        u"Management Board": "management_board",
        u"Network Scan": "network_scan",
        u"Custom attributes": "custom_attributes",
        u"Host tags": "custom_attributes",
        u"Tags": "custom_attributes",
        u"Grundeinstellungen": "basic",
        u"Adresse": "address",
        u"Datenquellen": "data_sources",
        u"Management-Board": "management_board",
        u"Netzwerk-Scan": "network_scan",
        u"Eigene Attribute": "custom_attributes",
        u"Hostmerkmale": "custom_attributes",
        u"Merkmale": "custom_attributes",
    }

    try:
        return _topic_title_to_id_map[topic_title]
    except KeyError:
        return None


def host_attribute(name):
    return host_attribute_registry[name]()


# This is the counterpart of "configure_attributes". Another place which
# is related to these HTTP variables and so on is SearchFolder.
def collect_attributes(for_what, new, do_validate=True, varprefix=""):
    """Read attributes from HTML variables"""
    host = {}
    for attr in host_attribute_registry.attributes():
        attrname = attr.name()
        if not html.request.var(for_what + "_change_%s" % attrname, ""):
            continue

        value = attr.from_html_vars(varprefix)

        if do_validate and attr.needs_validation(for_what, new):
            attr.validate_input(value, varprefix)

        host[attrname] = value
    return host


class ABCHostAttributeText(ABCHostAttribute, metaclass=abc.ABCMeta):
    """A simple text attribute. It is stored in a Python unicode string"""
    @property
    def _allow_empty(self):
        return True

    @property
    def _size(self):
        return 25

    def paint(self, value, hostname):
        if not value:
            return "", ""
        return "", value

    def render_input(self, varprefix, value):
        if value is None:
            value = ""
        html.text_input(varprefix + "attr_" + self.name(), value, size=self._size)

    def from_html_vars(self, varprefix):
        value = html.request.get_unicode_input(varprefix + "attr_" + self.name())
        if value is None:
            value = ""
        return value.strip()

    def validate_input(self, value, varprefix):
        if self.is_mandatory() and not value:
            raise MKUserError(varprefix + "attr_" + self.name(),
                              _("Please specify a value for %s") % self.title())
        if not self._allow_empty and value.strip() == "":
            raise MKUserError(
                varprefix + "attr_" + self.name(),
                _("%s may be missing, if must not be empty if it is set.") % self.title())

    def filter_matches(self, crit, value, hostname):
        if value is None:  # Host does not have this attribute
            value = ""

        return host_attribute_matches(crit, value)

    def default_value(self):
        return ""


class ABCHostAttributeValueSpec(ABCHostAttribute):
    """An attribute using the generic ValueSpec mechanism"""
    @abc.abstractmethod
    def valuespec(self):
        raise NotImplementedError()

    def title(self):
        return self.valuespec().title()

    def help(self):
        return self.valuespec().help()

    def default_value(self):
        return self.valuespec().default_value()

    def is_explicit(self):
        """The return value indicates if this attribute represents an explicit set
        value. Explicit attributes do not require cpu-intensive rule evaluations.
        Instead, an exclicit_host_config entry will be generated, e.g.
        explicit_host_config["alias"][hostname] = value

        Used in: cmk.gui.watolib.hosts_and_folders:CREFolder:_save_hosts_file
        """
        return False

    def paint(self, value, hostname):
        return "", self.valuespec().value_to_text(value)

    def render_input(self, varprefix, value):
        self.valuespec().render_input(varprefix + self.name(), value)

    def from_html_vars(self, varprefix):
        return self.valuespec().from_html_vars(varprefix + self.name())

    def validate_input(self, value, varprefix):
        self.valuespec().validate_value(value, varprefix + self.name())


class ABCHostAttributeFixedText(ABCHostAttributeText, metaclass=abc.ABCMeta):
    """A simple text attribute that is not editable by the user.

    It can be used to store context information from other
    systems (e.g. during an import of a host database from
    another system)."""
    def render_input(self, varprefix, value):
        if value is not None:
            html.hidden_field(varprefix + "attr_" + self.name(), value)
            html.write(value)

    def from_html_vars(self, varprefix):
        return html.request.var(varprefix + "attr_" + self.name())


class ABCHostAttributeNagiosText(ABCHostAttributeText):
    """A text attribute that is stored in a Nagios custom macro"""
    @abc.abstractmethod
    def nagios_name(self):
        raise NotImplementedError()

    def to_nagios(self, value):
        if value:
            return value
        return None


class ABCHostAttributeEnum(ABCHostAttribute):
    """An attribute for selecting one item out of list using a drop down box (<select>)

    Enumlist is a list of pairs of keyword / title. The type of value is
    string.  In all cases where no value is defined or the value is not in the
    enumlist, the default value is being used."""
    @abc.abstractproperty
    def _enumlist(self):
        raise NotImplementedError()

    def paint(self, value, hostname):
        return "", dict(self._enumlist).get(value, self.default_value())

    def render_input(self, varprefix, value):
        html.dropdown(varprefix + "attr_" + self.name(), self._enumlist, value)

    def from_html_vars(self, varprefix):
        return html.request.var(varprefix + "attr_" + self.name(), self.default_value())


class ABCHostAttributeTag(ABCHostAttributeValueSpec, metaclass=abc.ABCMeta):
    @abc.abstractproperty
    def is_checkbox_tag(self) -> bool:
        raise NotImplementedError()

    @abc.abstractproperty
    def _tag_group(self):
        raise NotImplementedError()

    def name(self):
        return "tag_%s" % self._tag_group.id

    @property
    def is_tag_attribute(self):
        return True

    def get_tag_groups(self, value):
        """Return set of tag groups to set (handles secondary tags)"""
        return self._tag_group.get_tag_group_config(value)


class ABCHostAttributeHostTagList(ABCHostAttributeTag, metaclass=abc.ABCMeta):
    """A selection dropdown for a host tag"""
    def valuespec(self):
        # Since encode_value=False is set it is not possible to use empty tag
        # ID selections (Value: "None"). Transform that back and forth to make
        # that work.
        choices = [(k or "", v) for k, v in self._tag_group.get_tag_choices()]
        return Transform(
            DropdownChoice(
                title=self._tag_group.title,
                choices=choices,
                default_value=choices[0][0],
                on_change="cmk.wato.fix_visibility();",
                encode_value=False,
            ),
            forth=lambda s: "" if s is None else s,
            back=lambda s: None if s == "" else s,
        )

    @property
    def is_checkbox_tag(self):
        return False

    @property
    def is_tag_attribute(self):
        return True


class ABCHostAttributeHostTagCheckbox(ABCHostAttributeTag, metaclass=abc.ABCMeta):
    """A checkbox for a host tag group"""
    def valuespec(self):
        choice = self._tag_group.get_tag_choices()[0]
        return Checkbox(
            title=self._tag_group.title,
            label=_u(choice[1]),
            true_label=self._tag_group.title,
            false_label="%s %s" % (_("Not"), self._tag_group.title),
            onclick="cmk.wato.fix_visibility();",
        )

    @property
    def is_checkbox_tag(self):
        return True

    def render_input(self, varprefix, value):
        super(ABCHostAttributeHostTagCheckbox, self).render_input(varprefix, bool(value))

    def from_html_vars(self, varprefix):
        if super(ABCHostAttributeHostTagCheckbox, self).from_html_vars(varprefix):
            return self._tag_value()
        return None

    def _tag_value(self):
        return self._tag_group.get_tag_choices()[0][0]

    def get_tag_groups(self, value):
        if not value:
            return {}
        return super(ABCHostAttributeHostTagCheckbox, self).get_tag_groups(self._tag_value())


class ABCHostAttributeNagiosValueSpec(ABCHostAttributeValueSpec):
    @abc.abstractmethod
    def nagios_name(self):
        raise NotImplementedError()

    def to_nagios(self, value):
        value = self.valuespec().value_to_text(value)
        if value:
            return value
        return None


# TODO: Kept for pre 1.6 plugin compatibility
def TextAttribute(name,
                  title,
                  help_txt=None,
                  default_value="",
                  mandatory=False,
                  allow_empty=True,
                  size=25):
    return type(
        "HostAttribute%s" % name.title(), (ABCHostAttributeText,), {
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
        })


# TODO: Kept for pre 1.6 plugin compatibility
def NagiosTextAttribute(name,
                        nag_name,
                        title,
                        help_txt=None,
                        default_value="",
                        mandatory=False,
                        allow_empty=True,
                        size=25):
    return type(
        "HostAttribute%s" % name.title(), (ABCHostAttributeNagiosText,), {
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
        })


# TODO: Kept for pre 1.6 plugin compatibility
def FixedTextAttribute(name, title, help_txt=None):
    return type(
        "HostAttributeFixedText%s" % name.title(), (ABCHostAttributeFixedText,), {
            "_name": name,
            "name": lambda self: self._name,
            "_title": title,
            "title": lambda self: self._title,
            "_help": help_txt,
            "help": lambda self: self._help,
        })


# TODO: Kept for pre 1.6 plugin compatibility
def ValueSpecAttribute(name, vs):
    return type(
        "HostAttributeValueSpec%s" % name.title(), (ABCHostAttributeValueSpec,), {
            "_name": name,
            "name": lambda self: self._name,
            "_valuespec": vs,
            "valuespec": lambda self: self._valuespec,
        })


# TODO: Kept for pre 1.6 plugin compatibility
def NagiosValueSpecAttribute(name, nag_name, vs):
    return type(
        "NagiosValueSpecAttribute%s" % name.title(), (ABCHostAttributeNagiosValueSpec,), {
            "_name": name,
            "name": lambda self: self._name,
            "_valuespec": vs,
            "valuespec": lambda self: self._valuespec,
            "_nagios_name": nag_name,
            "nagios_name": lambda self: self._nagios_name,
        })


# TODO: Kept for pre 1.6 plugin compatibility
def EnumAttribute(self, name, title, help_txt, default_value, enumlist):
    return type(
        "HostAttributeEnum%s" % name.title(), (ABCHostAttributeEnum,), {
            "_name": name,
            "name": lambda self: self._name,
            "_title": title,
            "title": lambda self: self._title,
            "_help": help_txt,
            "help": lambda self: self._help,
            "_default_value": default_value,
            "default_value": lambda self: self._default_value,
            "_enumlist": enumlist
        })
