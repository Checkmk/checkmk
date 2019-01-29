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

import cmk.gui.userdb as userdb
import cmk.gui.config as config
from cmk.gui.globals import html
from cmk.gui.i18n import _, _u
from cmk.gui.exceptions import MKUserError
from cmk.gui.valuespec import (
    TextAscii,
    DualListChoice,
    Checkbox,
    DropdownChoice,
)
from cmk.gui.watolib.hosts_and_folders import Folder
from cmk.gui.watolib.host_tags import group_hosttags_by_topic
from cmk.gui.watolib.utils import (
    host_attribute_matches,
    convert_cgroups_from_tuple,
)

# Global datastructure holding all attributes (in a defined order)
# as pairs of (attr, topic). Topic is the title under which the
# attribute is being displayed. All builtin attributes use the
# topic None. As long as only one topic is used, no topics will
# be displayed. They are useful if you have a great number of
# custom attributes.
# TODO: Cleanup this duplicated data structure into a single one.
_host_attributes = []

# Dictionary for quick access
_host_attribute = {}


def get_sorted_host_attribute_topics(for_what):
    # show attributes grouped by topics, in order of their
    # appearance. If only one topic exists, do not show topics
    # Make sure, that the topics "Basic settings" and host tags
    # are always show first.
    # TODO: Clean this up! Implement some explicit sorting
    topics = [None]
    if config.host_tag_groups():
        topics.append(_("Address"))
        topics.append(_("Data sources"))
        topics.append(_("Host tags"))

    # The remaining topics are shown in the order of the
    # appearance of the attribute declarations:
    for attr, topic in all_host_attributes():
        if topic not in topics and attr.is_visible(for_what):
            topics.append(topic)

    return [(t, _("Basic settings") if t is None else _u(t)) for t in topics]


def get_sorted_host_attributes_by_topic(topic):
    # Hack to sort the address family host tag attribute above the IPv4/v6 addresses
    # TODO: Clean this up by implementing some sort of explicit sorting
    def sort_host_attributes(a, b):
        if a[0].name() == "tag_address_family":
            return -1
        return 0

    sorted_attributes = []
    for attr, atopic in sorted(all_host_attributes(), cmp=sort_host_attributes):
        if atopic == topic:
            sorted_attributes.append(attr)
    return sorted_attributes


def all_host_attributes():
    return _host_attributes


def attributes():
    return _host_attribute


# Declare attributes with this method
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
    if depends_on_tags is None:
        depends_on_tags = []

    if depends_on_roles is None:
        depends_on_roles = []

    _host_attributes.append((a, topic))
    _host_attribute[a.name()] = a
    a._show_in_table = show_in_table
    a._show_in_folder = show_in_folder
    a._show_in_host_search = show_in_host_search
    a._show_in_form = show_in_form
    a._show_inherited_value = show_inherited_value
    a._depends_on_tags = depends_on_tags
    a._depends_on_roles = depends_on_roles
    a._editable = editable
    a._from_config = from_config

    if may_edit:
        a.may_edit = may_edit


def undeclare_host_attribute(attrname):
    global _host_attributes

    if attrname in _host_attribute:
        attr = _host_attribute[attrname]
        del _host_attribute[attrname]
        _host_attributes = [ha for ha in _host_attributes if ha[0].name() != attr.name()]


def undeclare_host_tag_attribute(tag_id):
    attrname = "tag_" + tag_id
    undeclare_host_attribute(attrname)


def update_config_based_host_attributes():
    _clear_config_based_host_attributes()
    _declare_host_tag_attributes()
    declare_custom_host_attrs()

    Folder.invalidate_caches()


def _clear_config_based_host_attributes():
    for name, attr in attributes().items():
        if attr.from_config():
            undeclare_host_attribute(name)


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
    for attr in config.wato_host_attrs:
        if attr['type'] == "TextAscii":
            vs = TextAscii(title=attr['title'], help=attr['help'])
        else:
            raise NotImplementedError()

        if attr['add_custom_macro']:
            a = NagiosValueSpecAttribute(attr["name"], "_" + attr["name"], vs)
        else:
            a = ValueSpecAttribute(attr["name"], vs)

        declare_host_attribute(
            a,
            show_in_table=attr['show_in_table'],
            topic=attr['topic'],
            from_config=True,
        )


def host_attribute(name):
    return _host_attribute[name]


# Read attributes from HTML variables
def collect_attributes(for_what, do_validate=True, varprefix=""):
    host = {}
    for attr, _topic in all_host_attributes():
        attrname = attr.name()
        if not html.request.var(for_what + "_change_%s" % attrname, False):
            continue

        value = attr.from_html_vars(varprefix)

        if do_validate and attr.needs_validation(for_what):
            attr.validate_input(value, varprefix)

        host[attrname] = value
    return host


# TODO: Refactor declare_host_attribute() setting private attributes here
class Attribute(object):
    # The constructor stores name and title. If those are
    # dynamic then leave them out and override name() and
    # title()
    def __init__(self, name=None, title=None, help_txt=None, default_value=None):
        self._name = name
        self._title = title
        self._help = help_txt
        self._default_value = default_value

        self._show_in_table = True
        self._show_in_folder = True
        self._show_in_host_search = False
        self._show_in_form = True
        self._show_inherited_value = True
        self._depends_on_tags = []
        self._depends_on_roles = []
        self._editable = True
        self._from_config = False

    # Return the name (= identifier) of the attribute
    def name(self):
        return self._name

    # Return the name of the Nagios configuration variable
    # if this is a Nagios-bound attribute (e.g. "alias" or "_SERIAL")
    def nagios_name(self):
        return None

    # Return the title to be displayed to the user
    def title(self):
        return self._title

    # Return an optional help text
    def help(self):
        return self._help

    # Return the default value for new hosts
    def default_value(self):
        return self._default_value

    # Render HTML code displaying a value
    def paint(self, value, hostname):
        return "", value

    # Whether or not the user is able to edit this attribute. If
    # not, the value is shown read-only (when the user is permitted
    # to see the attribute).
    def may_edit(self):
        return True

    # Whether or not to show this attribute in tables.
    # This value is set by declare_host_attribute
    def show_in_table(self):
        return self._show_in_table

    # Whether or not to show this attribute in the edit form.
    # This value is set by declare_host_attribute
    def show_in_form(self):
        return self._show_in_form

    # Whether or not to make this attribute configurable in
    # files and folders (as defaule value for the hosts)
    def show_in_folder(self):
        return self._show_in_folder

    # Whether or not to make this attribute configurable in
    # the host search form
    def show_in_host_search(self):
        return self._show_in_host_search

    # Whether or not this attribute can be edited after creation
    # of the object
    def editable(self):
        return self._editable

    # Whether it is allowed that a host has no explicit
    # value here (inherited or direct value). An mandatory
    # has *no* default value.
    def is_mandatory(self):
        return False

    # Return information about the user roles we depend on.
    # The method is usually not overridden, but the variable
    # _depends_on_roles is set by declare_host_attribute().
    def depends_on_roles(self):
        return self._depends_on_roles

    # Return information about whether or not either the
    # inherited value or the default value should be shown
    # for an attribute.
    # _depends_on_roles is set by declare_host_attribute().
    def show_inherited_value(self):
        return self._show_inherited_value

    # Return information about the host tags we depend on.
    # The method is usually not overridden, but the variable
    # _depends_on_tags is set by declare_host_attribute().
    def depends_on_tags(self):
        return self._depends_on_tags

    # Whether or not this attribute has been created from the
    # config of the site.
    # The method is usually not overridden, but the variable
    # _from_config is set by declare_host_attribute().
    def from_config(self):
        return self._from_config

    # Render HTML input fields displaying the value and
    # make it editable. If filter == True, then the field
    # is to be displayed in filter mode (as part of the
    # search filter)
    def render_input(self, varprefix, value):
        pass

    # Create value from HTML variables.
    def from_html_vars(self, varprefix):
        return None

    # Check whether this attribute needs to be validated at all
    # Attributes might be permanently hidden (show_in_form = False)
    # or dynamically hidden by the depends_on_tags, editable features
    def needs_validation(self, for_what):
        if not self.is_visible(for_what):
            return False
        return html.request.var('attr_display_%s' % self._name, "1") == "1"

    # Gets the type of current view as argument and returns whether or not
    # this attribute is shown in this type of view
    def is_visible(self, for_what):
        if for_what in ["host", "cluster", "bulk"] and not self.show_in_form():
            return False
        elif for_what == "folder" and not self.show_in_folder():
            return False
        elif for_what == "host_search" and not self.show_in_host_search():
            return False
        return True

    # Check if the value entered by the user is valid.
    # This method may raise MKUserError in case of invalid user input.
    def validate_input(self, value, varprefix):
        pass

    # If this attribute should be present in Nagios as
    # a host custom macro, then the value of that macro
    # should be returned here - otherwise None
    def to_nagios(self, value):
        return None

    # Checks if the give value matches the search attributes
    # that are represented by the current HTML variables.
    def filter_matches(self, crit, value, hostname):
        return crit == value

    # Host tags to set for this host
    def get_tag_list(self, value):
        return []

    @property
    def is_checkbox_tag(self):
        return False

    @property
    def is_tag_attribute(self):
        return False


# A simple text attribute. It is stored in
# a Python unicode string
class TextAttribute(Attribute):
    def __init__(self,
                 name,
                 title,
                 help_txt=None,
                 default_value="",
                 mandatory=False,
                 allow_empty=True,
                 size=25):
        Attribute.__init__(self, name, title, help_txt, default_value)
        self._mandatory = mandatory
        self._allow_empty = allow_empty
        self._size = size

    def paint(self, value, hostname):
        if not value:
            return "", ""
        return "", value

    def is_mandatory(self):
        return self._mandatory

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
        if self._mandatory and not value:
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


# An attribute using the generic ValueSpec mechanism
class ValueSpecAttribute(Attribute):
    def __init__(self, name, vs):
        Attribute.__init__(self, name)
        self._valuespec = vs

    def valuespec(self):
        return self._valuespec

    def title(self):
        return self._valuespec.title()

    def help(self):
        return self._valuespec.help()

    def default_value(self):
        return self._valuespec.default_value()

    def paint(self, value, hostname):
        return "", \
            self._valuespec.value_to_text(value)

    def render_input(self, varprefix, value):
        self._valuespec.render_input(varprefix + self._name, value)

    def from_html_vars(self, varprefix):
        return self._valuespec.from_html_vars(varprefix + self._name)

    def validate_input(self, value, varprefix):
        self._valuespec.validate_value(value, varprefix + self._name)


# A simple text attribute that is not editable by the user.
# It can be used to store context information from other
# systems (e.g. during an import of a host database from
# another system).
class FixedTextAttribute(TextAttribute):
    def __init__(self, name, title, help_txt=None):
        TextAttribute.__init__(self, name, title, help_txt, None)
        self._mandatory = False

    def render_input(self, varprefix, value):
        if value is not None:
            html.hidden_field(varprefix + "attr_" + self.name(), value)
            html.write(value)

    def from_html_vars(self, varprefix):
        return html.request.var(varprefix + "attr_" + self.name())


# A text attribute that is stored in a Nagios custom macro
class NagiosTextAttribute(TextAttribute):
    def __init__(self,
                 name,
                 nag_name,
                 title,
                 help_txt=None,
                 default_value="",
                 mandatory=False,
                 allow_empty=True,
                 size=25):
        TextAttribute.__init__(self, name, title, help_txt, default_value, mandatory, allow_empty,
                               size)
        self.nag_name = nag_name

    def nagios_name(self):
        return self.nag_name

    def to_nagios(self, value):
        if value:
            return value
        return None


# An attribute for selecting one item out of list using
# a drop down box (<select>). Enumlist is a list of
# pairs of keyword / title. The type of value is string.
# In all cases where no value is defined or the value is
# not in the enumlist, the default value is being used.
class EnumAttribute(Attribute):
    def __init__(self, name, title, help_txt, default_value, enumlist):
        Attribute.__init__(self, name, title, help_txt, default_value)
        self._enumlist = enumlist
        self._enumdict = dict(enumlist)

    def paint(self, value, hostname):
        return "", self._enumdict.get(value, self.default_value())

    def render_input(self, varprefix, value):
        html.dropdown(varprefix + "attr_" + self.name(), self._enumlist, value)

    def from_html_vars(self, varprefix):
        return html.request.var(varprefix + "attr_" + self.name(), self.default_value())


class HostTagAttribute(ValueSpecAttribute):
    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def is_checkbox_tag(self):
        # type: () -> bool
        raise NotImplementedError()

    def __init__(self, valuespec, tag_id, tag_list):
        self._taglist = tag_list
        super(HostTagAttribute, self).__init__(name="tag_" + tag_id, vs=valuespec)

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


class HostTagListAttribute(HostTagAttribute):
    """A selection dropdown for a host tag"""

    def __init__(self, tag_id, title, tag_list):
        vs = DropdownChoice(
            title=title,
            choices=self._get_tag_choices(tag_list),
            default_value=tag_list[0][0],
            on_change="cmk.wato.fix_visibility();",
            encode_value=False,
        )
        super(HostTagListAttribute, self).__init__(vs, tag_id, tag_list)

    @property
    def is_checkbox_tag(self):
        return False

    @property
    def is_tag_attribute(self):
        return True


class HostTagCheckboxAttribute(HostTagAttribute):
    """A checkbox for a host tag group"""

    def __init__(self, tag_id, title, tag_list):
        vs = Checkbox(
            title=title,
            label=_u(tag_list[0][1]),
            true_label=title,
            false_label="%s %s" % (_("Not"), title),
            onclick="cmk.wato.fix_visibility();",
        )
        super(HostTagCheckboxAttribute, self).__init__(vs, tag_id, tag_list)

    @property
    def is_checkbox_tag(self):
        return True

    def render_input(self, varprefix, value):
        super(HostTagCheckboxAttribute, self).render_input(varprefix, bool(value))

    def from_html_vars(self, varprefix):
        if super(HostTagCheckboxAttribute, self).from_html_vars(varprefix):
            return self._taglist[0][0]
        return None


class NagiosValueSpecAttribute(ValueSpecAttribute):
    def __init__(self, name, nag_name, vs):
        ValueSpecAttribute.__init__(self, name, vs)
        self.nag_name = nag_name

    def nagios_name(self):
        return self.nag_name

    def to_nagios(self, value):
        value = self._valuespec.value_to_text(value)
        if value:
            return value
        return None


# Attribute needed for folder permissions
class ContactGroupsAttribute(Attribute):
    # The constructor stores name and title. If those are
    # dynamic than leave them out and override name() and
    # title()
    def __init__(self):
        url = "wato.py?mode=rulesets&group=grouping"
        Attribute.__init__(
            self, "contactgroups", _("Permissions"),
            _("Only members of the contact groups listed here have WATO permission "
              "to the host / folder. If you want, you can make those contact groups "
              "automatically also <b>monitoring contacts</b>. This is completely "
              "optional. Assignment of host and services to contact groups "
              "can be done by <a href='%s'>rules</a> as well.") % url)
        self._default_value = (True, [])
        self._contactgroups = None
        self._users = None
        self._loaded_at = None

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
        self._vs_contactgroups().render_input(varprefix + self._name, value['groups'])

        html.hr()

        if is_host:
            html.checkbox(
                varprefix + self._name + "_use",
                value["use"],
                label=_("Add these contact groups to the host"))

        elif not is_search:
            html.checkbox(
                varprefix + self._name + "_recurse_perms",
                value["recurse_perms"],
                label=_("Give these groups also <b>permission on all subfolders</b>"))
            html.hr()
            html.checkbox(
                varprefix + self._name + "_use",
                value["use"],
                label=_("Add these groups as <b>contacts</b> to all hosts in this folder"))
            html.br()
            html.checkbox(
                varprefix + self._name + "_recurse_use",
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
            varprefix + self._name + "_use_for_services",
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

        cgs = self._vs_contactgroups().from_html_vars(varprefix + self._name)

        return {
            "groups": cgs,
            "recurse_perms": html.get_checkbox(varprefix + self._name + "_recurse_perms"),
            "use": html.get_checkbox(varprefix + self._name + "_use"),
            "use_for_services": html.get_checkbox(varprefix + self._name + "_use_for_services"),
            "recurse_use": html.get_checkbox(varprefix + self._name + "_recurse_use"),
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
