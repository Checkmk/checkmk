#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
"""A host attribute is something that is inherited from folders to
hosts. Examples are the IP address and the host tags."""

import abc
from typing import Optional, Any, Set, List, Tuple, Type, Text  # pylint: disable=unused-import
import six

import cmk.utils.plugin_registry

import cmk.gui.userdb as userdb
import cmk.gui.config as config
from cmk.gui.globals import html
from cmk.gui.i18n import _, _u
from cmk.gui.exceptions import MKUserError, MKGeneralException
from cmk.gui.valuespec import (
    TextAscii,
    DualListChoice,
    Checkbox,
    DropdownChoice,
)
from cmk.gui.watolib.host_tags import group_hosttags_by_topic
from cmk.gui.watolib.utils import (
    host_attribute_matches,
    convert_cgroups_from_tuple,
)


class HostAttributeTopic(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def ident(self):
        # type: () -> str
        """Unique internal ID of this attribute. Only ASCII characters allowed."""
        raise NotImplementedError()

    @abc.abstractproperty
    def title(self):
        # type: () -> Text
        """Used as title for the attribute topics on the host edit page"""
        raise NotImplementedError()

    @abc.abstractproperty
    def sort_index(self):
        # type: () -> int
        """The topics are sorted by this number wherever displayed as a list"""
        raise NotImplementedError()


class HostAttributeTopicRegistry(cmk.utils.plugin_registry.ClassRegistry):
    def plugin_base_class(self):
        return HostAttributeTopic

    def plugin_name(self, plugin_class):
        return plugin_class().ident

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
        return _("Address")

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


class ABCHostAttribute(object):
    """Base class for all registered host attributes"""
    __metaclass__ = abc.ABCMeta
    sort_index = 80

    @abc.abstractmethod
    def name(self):
        # type: () -> str
        """Return the name (= identifier) of the attribute"""
        raise NotImplementedError()

    @abc.abstractmethod
    def title(self):
        # type: () -> Text
        """Return the title to be displayed to the user"""
        raise NotImplementedError()

    @abc.abstractmethod
    def topic(self):
        # type: () -> Type[HostAttributeTopic]
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

    def nagios_name(self):
        # type: () -> Optional[str]
        """Return the name of the Nagios configuration variable
        if this is a Nagios-bound attribute (e.g. "alias" or "_SERIAL")"""
        return None

    def help(self):
        # type: () -> Optional[Text]
        """Return an optional help text"""
        return None

    def default_value(self):
        """Return the default value for new hosts"""
        return None

    def paint(self, value, hostname):
        """Render HTML code displaying a value"""
        return "", value

    def may_edit(self):
        # type: () -> bool
        """Whether or not the user is able to edit this attribute. If
        not, the value is shown read-only (when the user is permitted
        to see the attribute)."""
        return True

    def show_in_table(self):
        # type: () -> bool
        """Whether or not to show this attribute in tables.
        This value is set by declare_host_attribute"""
        return True

    def show_in_form(self):
        # type: () -> bool
        """Whether or not to show this attribute in the edit form.
        This value is set by declare_host_attribute"""
        return True

    def show_in_folder(self):
        # type: () -> bool
        """Whether or not to make this attribute configurable in
        files and folders (as defaule value for the hosts)"""
        return True

    def show_in_host_search(self):
        # type: () -> bool
        """Whether or not to make this attribute configurable in
        the host search form"""
        return True

    def editable(self):
        # type: () -> bool
        """Whether or not this attribute can be edited after creation
        of the object"""
        return True

    def is_mandatory(self):
        # type: () -> bool
        """Whether it is allowed that a host has no explicit
        value here (inherited or direct value). An mandatory
        has *no* default value."""
        return False

    def show_inherited_value(self):
        # type: () -> bool
        """Return information about whether or not either the
        inherited value or the default value should be shown
        for an attribute.
        _depends_on_roles is set by declare_host_attribute()."""
        return True

    def depends_on_roles(self):
        # type: () -> List[str]
        """Return information about the user roles we depend on.
        The method is usually not overridden, but the variable
        _depends_on_roles is set by declare_host_attribute()."""
        return []

    def depends_on_tags(self):
        # type: () -> List[str]
        """Return information about the host tags we depend on.
        The method is usually not overridden, but the variable
        _depends_on_tags is set by declare_host_attribute()."""
        return []

    def from_config(self):
        # type: () -> bool
        """Whether or not this attribute has been created from the
        config of the site.
        The method is usually not overridden, but the variable
        _from_config is set by declare_host_attribute()."""
        return False

    def needs_validation(self, for_what):
        # type: (str) -> bool
        """Check whether this attribute needs to be validated at all
        Attributes might be permanently hidden (show_in_form = False)
        or dynamically hidden by the depends_on_tags, editable features"""
        if not self.is_visible(for_what):
            return False
        return html.request.var('attr_display_%s' % self.name(), "1") == "1"

    def is_visible(self, for_what):
        # type: (str) -> bool
        """Gets the type of current view as argument and returns whether or not
        this attribute is shown in this type of view"""
        if for_what in ["host", "cluster", "bulk"] and not self.show_in_form():
            return False
        elif for_what == "folder" and not self.show_in_folder():
            return False
        elif for_what == "host_search" and not self.show_in_host_search():
            return False
        return True

    def validate_input(self, value, varprefix):
        """Check if the value entered by the user is valid.
        This method may raise MKUserError in case of invalid user input."""
        pass

    def to_nagios(self, value):
        """If this attribute should be present in Nagios as a host custom
        macro, then the value of that macro should be returned here - otherwise None"""
        return None

    def filter_matches(self, crit, value, hostname):
        # type: (Any, Any, str) -> bool
        """Checks if the give value matches the search attributes
        that are represented by the current HTML variables."""
        return crit == value

    def get_tag_list(self, value):
        # type: (Any) -> List[str]
        """Host tags to set for this host"""
        return []

    @property
    def is_checkbox_tag(self):
        # type: () -> bool
        return False

    @property
    def is_tag_attribute(self):
        # type: () -> bool
        return False


class HostAttributeRegistry(cmk.utils.plugin_registry.ClassRegistry):
    _index = 0

    def plugin_base_class(self):
        return ABCHostAttribute

    def plugin_name(self, plugin_class):
        return plugin_class().name()

    # TODO: Transition hack. Change to explicit sorting next.
    def registration_hook(self, plugin_class):
        plugin_class.sort_index = self.__class__._index
        self.__class__._index += 1

    def attributes(self):
        return [cls() for cls in self.values()]

    def get_sorted_host_attributes(self):
        # type: () -> List[ABCHostAttribute]
        """Return host attribute objects in the order they should be displayed (in edit dialogs)"""
        return sorted(self.attributes(), key=lambda a: (a.sort_index, a.topic()))

    def get_choices(self):
        return [(a.name(), a.title()) for a in self.get_sorted_host_attributes()]


host_attribute_registry = HostAttributeRegistry()


def get_sorted_host_attribute_topics(for_what):
    # type: (str) -> List[Tuple[str, Text]]
    """Return a list of needed topics for the given "what".
    Only returns the topics that are used by a visible attribute"""
    needed_topics = set()  # type: Set[Type[HostAttributeTopic]]
    for attr_class in host_attribute_registry.values():
        attr = attr_class()
        if attr.topic() not in needed_topics and attr.is_visible(for_what):
            needed_topics.add(attr.topic())

    return [(t.ident, t.title)
            for t in sorted([t_class() for t_class in needed_topics], key=lambda e: e.sort_index)]


def get_sorted_host_attributes_by_topic(topic_id):
    # Hack to sort the address family host tag attribute above the IPv4/v6 addresses
    # TODO: Clean this up by implementing some sort of explicit sorting
    def sort_host_attributes(a, b):
        if a.name() == "tag_address_family":
            return -1
        return 0

    sorted_attributes = []
    for attr in sorted(
            host_attribute_registry.get_sorted_host_attributes(), cmp=sort_host_attributes):
        if attr.topic() == host_attribute_topic_registry[topic_id]:
            sorted_attributes.append(attr)
    return sorted_attributes


# TODO: Kept for comatibility with pre 1.6 plugins
def declare_host_attribute(a,
                           show_in_table=True,
                           show_in_folder=True,
                           show_in_host_search=True,
                           topic=None,
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

    if topic is None or isinstance(topic, six.string_types):
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
        del host_attribute_registry[attrname]


def undeclare_host_tag_attribute(tag_id):
    attrname = "tag_" + tag_id
    undeclare_host_attribute(attrname)


def update_config_based_host_attributes():
    _clear_config_based_host_attributes()
    _declare_host_tag_attributes()
    declare_custom_host_attrs()

    from cmk.gui.watolib.hosts_and_folders import Folder
    Folder.invalidate_caches()


# Make the config module initialize the host attributes after loading the config
config.register_post_config_load_hook(update_config_based_host_attributes)


def _clear_config_based_host_attributes():
    for attr in host_attribute_registry.attributes():
        if attr.from_config():
            undeclare_host_attribute(attr.name())


def _declare_host_tag_attributes():
    for topic, grouped_tags in group_hosttags_by_topic(config.host_tag_groups()):
        for entry in grouped_tags:
            # if the entry has o fourth component, then its
            # the tag dependency defintion.
            depends_on_tags = []
            depends_on_roles = []
            attr_editable = True
            if len(entry) >= 6:
                attr_editable = entry[5]
            if len(entry) >= 5:
                depends_on_roles = entry[4]
            if len(entry) >= 4:
                depends_on_tags = entry[3]

            if not topic:
                topic = _('Host tags')

            if len(entry[2]) == 1:
                vs = HostTagCheckboxAttribute(*entry[:3])
            else:
                vs = HostTagListAttribute(*entry[:3])

            declare_host_attribute(
                vs,
                show_in_table=False,
                show_in_folder=True,
                editable=attr_editable,
                depends_on_tags=depends_on_tags,
                depends_on_roles=depends_on_roles,
                topic=topic,
                from_config=True,
            )


def declare_custom_host_attrs():
    for attr in transform_pre_16_host_topics(config.wato_host_attrs):
        if attr['type'] == "TextAscii":
            vs = TextAscii(title=attr['title'], help=attr['help'])
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


def transform_pre_16_host_topics(custom_attributes):
    """Previous to 1.6 the titles of the host attribute topics were stored.

    This lead to issues with localized topics. We now have internal IDs for
    all the topics and try to convert the values here to the new format.

    At least for unlocalized topics the conversion works. Localized topics
    are put into the "Custom attributes" topic once. Users will have to
    re-configure the topic, sorry :-/."""
    topics = [a_class() for a_class in host_attribute_topic_registry.values()]
    for custom_attr in custom_attributes:
        found = False
        for topic in topics:
            if custom_attr["topic"] == topic.title:
                custom_attr["topic"] = topic.ident
                found = True
                break

        if not found:
            custom_attr["topic"] = "custom_attributes"

    return custom_attributes


def host_attribute(name):
    return host_attribute_registry[name]()


# Read attributes from HTML variables
def collect_attributes(for_what, do_validate=True, varprefix=""):
    host = {}
    for attr in host_attribute_registry.attributes():
        attrname = attr.name()
        if not html.request.var(for_what + "_change_%s" % attrname, False):
            continue

        value = attr.from_html_vars(varprefix)

        if do_validate and attr.needs_validation(for_what):
            attr.validate_input(value, varprefix)

        host[attrname] = value
    return host


class ABCHostAttributeText(ABCHostAttribute):
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
        value = html.get_unicode_input(varprefix + "attr_" + self.name())
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

    def paint(self, value, hostname):
        return "", self.valuespec().value_to_text(value)

    def render_input(self, varprefix, value):
        self.valuespec().render_input(varprefix + self.name(), value)

    def from_html_vars(self, varprefix):
        return self.valuespec().from_html_vars(varprefix + self.name())

    def validate_input(self, value, varprefix):
        self.valuespec().validate_value(value, varprefix + self.name())


class ABCHostAttributeFixedText(ABCHostAttributeText):
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


class ABCHostAttributeTag(ABCHostAttributeValueSpec):
    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def is_checkbox_tag(self):
        # type: () -> bool
        raise NotImplementedError()

    @abc.abstractproperty
    def _tag_id(self):
        raise NotImplementedError()

    @abc.abstractproperty
    def _taglist(self):
        raise NotImplementedError()

    def name(self):
        return "tag_%s" % self._tag_id

    @property
    def is_tag_attribute(self):
        return True

    def _get_tag_choices(self, tag_list):
        return [(e[0], _u(e[1])) for e in tag_list]

    # TODO: Can we move this to some other place?
    def get_tag_value(self, tags):
        """Special function for computing the setting of a specific
        tag group from the total list of tags of a host"""
        for entry in self._taglist:
            if entry[0] in tags:
                return entry[0]
        return None

    # TODO: Can we move this to some other place?
    def get_tag_list(self, value):
        """Return list of host tags to set (handles secondary tags)"""
        for entry in self._taglist:
            if entry[0] == value:
                if len(entry) >= 3:
                    taglist = [value] + entry[2]
                else:
                    taglist = [value]
                if taglist[0] is None:
                    taglist = taglist[1:]
                return taglist
        return []  # No matching tag


class ABCHostAttributeHostTagList(ABCHostAttributeTag):
    """A selection dropdown for a host tag"""

    def valuespec(self):
        return DropdownChoice(
            title=self.title(),
            choices=self._get_tag_choices(self._taglist),
            default_value=self._taglist[0][0],
            on_change="cmk.wato.fix_visibility();",
            encode_value=False,
        )

    @property
    def is_checkbox_tag(self):
        return False

    @property
    def is_tag_attribute(self):
        return True


class ABCHostAttributeHostTagCheckbox(ABCHostAttributeTag):
    """A checkbox for a host tag group"""

    def valuespec(self):
        return Checkbox(
            title=self.title(),
            label=_u(self._taglist[0][1]),
            true_label=self.title(),
            false_label="%s %s" % (_("Not"), self.title()),
            onclick="cmk.wato.fix_visibility();",
        )

    @property
    def is_checkbox_tag(self):
        return True

    def render_input(self, varprefix, value):
        super(ABCHostAttributeHostTagCheckbox, self).render_input(varprefix, bool(value))

    def from_html_vars(self, varprefix):
        if super(ABCHostAttributeHostTagCheckbox, self).from_html_vars(varprefix):
            return self._taglist[0][0]
        return None


class ABCHostAttributeNagiosValueSpec(ABCHostAttributeValueSpec):
    @abc.abstractmethod
    def nagios_name(self):
        raise NotImplementedError()

    def to_nagios(self, value):
        value = self.valuespec().value_to_text(value)
        if value:
            return value
        return None


@host_attribute_registry.register
class HostAttributeContactGroups(ABCHostAttribute):
    """Attribute needed for folder permissions"""

    def __init__(self):
        ABCHostAttribute.__init__(self)
        self._contactgroups = None
        self._loaded_at = None

    def name(self):
        return "contactgroups"

    def title(self):
        return _("Permissions")

    def topic(self):
        return HostAttributeTopicBasicSettings

    def help(self):
        url = "wato.py?mode=rulesets&group=grouping"
        return _("Only members of the contact groups listed here have WATO permission "
                 "to the host / folder. If you want, you can make those contact groups "
                 "automatically also <b>monitoring contacts</b>. This is completely "
                 "optional. Assignment of host and services to contact groups "
                 "can be done by <a href='%s'>rules</a> as well.") % url

    def show_in_table(self):
        return False

    def show_in_folder(self):
        return True

    def default_value(self):
        return (True, [])

    def paint(self, value, hostname):
        value = convert_cgroups_from_tuple(value)
        texts = []
        self.load_data()
        items = self._contactgroups.items()
        items.sort(cmp=lambda a, b: cmp(a[1]['alias'], b[1]['alias']))
        for name, cgroup in items:
            if name in value["groups"]:
                display_name = cgroup.get("alias", name)
                texts.append('<a href="wato.py?mode=edit_contact_group&edit=%s">%s</a>' %
                             (name, display_name))
        result = ", ".join(texts)
        if texts and value["use"]:
            result += html.render_span(
                html.render_b("*"),
                title=_("These contact groups are also used in the monitoring configuration."))
        return "", result

    def render_input(self, varprefix, value):
        value = convert_cgroups_from_tuple(value)

        # If we're just editing a host, then some of the checkboxes will be missing.
        # This condition is not very clean, but there is no other way to savely determine
        # the context.
        is_host = bool(html.request.var("host")) or html.request.var("mode") == "newhost"
        is_search = varprefix == "host_search"

        # Only show contact groups I'm currently in and contact
        # groups already listed here.
        self.load_data()
        self._vs_contactgroups().render_input(varprefix + self.name(), value['groups'])

        html.hr()

        if is_host:
            html.checkbox(
                varprefix + self.name() + "_use",
                value["use"],
                label=_("Add these contact groups to the host"))

        elif not is_search:
            html.checkbox(
                varprefix + self.name() + "_recurse_perms",
                value["recurse_perms"],
                label=_("Give these groups also <b>permission on all subfolders</b>"))
            html.hr()
            html.checkbox(
                varprefix + self.name() + "_use",
                value["use"],
                label=_("Add these groups as <b>contacts</b> to all hosts in this folder"))
            html.br()
            html.checkbox(
                varprefix + self.name() + "_recurse_use",
                value["recurse_use"],
                label=_("Add these groups as <b>contacts in all subfolders</b>"))

        html.hr()
        html.help(
            _("With this option contact groups that are added to hosts are always "
              "being added to services, as well. This only makes a difference if you have "
              "assigned other contact groups to services via rules in <i>Host & Service Parameters</i>. "
              "As long as you do not have any such rule a service always inherits all contact groups "
              "from its host."))
        html.checkbox(
            varprefix + self.name() + "_use_for_services",
            value.get("use_for_services", False),
            label=_("Always add host contact groups also to its services"))

    def load_data(self):
        # Make cache valid only during this HTTP request
        if self._loaded_at == id(html):
            return
        self._loaded_at = id(html)
        self._contactgroups = userdb.load_group_information().get("contact", {})

    def from_html_vars(self, varprefix):
        self.load_data()

        cgs = self._vs_contactgroups().from_html_vars(varprefix + self.name())

        return {
            "groups": cgs,
            "recurse_perms": html.get_checkbox(varprefix + self.name() + "_recurse_perms"),
            "use": html.get_checkbox(varprefix + self.name() + "_use"),
            "use_for_services": html.get_checkbox(varprefix + self.name() + "_use_for_services"),
            "recurse_use": html.get_checkbox(varprefix + self.name() + "_recurse_use"),
        }

    def filter_matches(self, crit, value, hostname):
        value = convert_cgroups_from_tuple(value)
        # Just use the contact groups for searching
        for contact_group in crit["groups"]:
            if contact_group not in value["groups"]:
                return False
        return True

    def _vs_contactgroups(self):
        cg_choices = sorted([(cg_id, cg_attrs.get("alias", cg_id))
                             for cg_id, cg_attrs in self._contactgroups.items()],
                            key=lambda x: x[1])
        return DualListChoice(choices=cg_choices, rows=20, size=100)


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
            "_help": help,
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
def HostTagListAttribute(tag_id, title, tag_list):
    return type("HostAttributeHostTagList%s" % tag_id.title(), (ABCHostAttributeHostTagList,), {
        "_title": title,
        "title": lambda self: self._title,
        "_tag_id": tag_id,
        "_taglist": tag_list,
    })


# TODO: Kept for pre 1.6 plugin compatibility
def HostTagCheckboxAttribute(tag_id, title, tag_list):
    return type("HostAttributeHostTagCheckbox%s" % tag_id.title(),
                (ABCHostAttributeHostTagCheckbox,), {
                    "_title": title,
                    "title": lambda self: self._title,
                    "_tag_id": tag_id,
                    "_taglist": tag_list,
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
