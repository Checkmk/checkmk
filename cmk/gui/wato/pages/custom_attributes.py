#!/usr/bin/env python
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
"""Mange custom attributes of users and hosts"""

import abc
import os
import pprint
import re

import cmk.gui.config as config
import cmk.gui.forms as forms
from cmk.gui.table import table_element
import cmk.gui.userdb as userdb
import cmk.gui.watolib as watolib
import cmk.utils.store as store
from cmk.gui.exceptions import MKUserError
from cmk.gui.globals import html
from cmk.gui.i18n import _
from cmk.gui.watolib.host_attributes import (
    host_attribute_topic_registry,
    transform_pre_16_host_topics,
)
from cmk.gui.watolib.hosts_and_folders import Folder
from cmk.gui.plugins.wato import WatoMode, add_change, mode_registry, wato_confirm


def update_user_custom_attrs():
    userdb.update_config_based_user_attributes()
    userdb.rewrite_users()


def _update_host_custom_attrs():
    config.load_config()
    Folder.invalidate_caches()
    Folder.root_folder().rewrite_hosts_files()


def load_custom_attrs_from_mk_file(lock):
    filename = os.path.join(watolib.multisite_dir(), "custom_attrs.mk")
    vars_ = store.load_mk_file(filename, {
        'wato_user_attrs': [],
        'wato_host_attrs': [],
    }, lock=lock)

    attrs = {}
    for what in ["user", "host"]:
        attributes = vars_.get("wato_%s_attrs" % what, [])
        if what == "host":
            attributes = transform_pre_16_host_topics(attributes)
        attrs[what] = attributes
    return attrs


def save_custom_attrs_to_mk_file(attrs):
    output = watolib.wato_fileheader()
    for what in ["user", "host"]:
        if what in attrs and len(attrs[what]) > 0:
            output += "if type(wato_%s_attrs) != list:\n    wato_%s_attrs = []\n" % (what, what)
            output += "wato_%s_attrs += %s\n\n" % (what, pprint.pformat(attrs[what]))

    store.mkdir(watolib.multisite_dir())
    store.save_file(watolib.multisite_dir() + "custom_attrs.mk", output)


def custom_attr_types():
    return [
        ('TextAscii', _('Simple Text')),
    ]


class ModeEditCustomAttr(WatoMode):
    __metaclass__ = abc.ABCMeta

    @property
    def _attrs(self):
        return self._all_attrs[self._type]

    def _from_vars(self):
        self._name = html.request.var("edit")  # missing -> new custom attr
        self._new = self._name is None

        # TODO: Inappropriate Intimacy: custom host attributes should not now about
        #       custom user attributes and vice versa. The only reason they now about
        #       each other now is that they are stored in one file.
        self._all_attrs = load_custom_attrs_from_mk_file(lock=html.is_transaction())

        if not self._new:
            self._attr = [a for a in self._attrs if a['name'] == self._name]
            if not self._attr:
                raise MKUserError(None, _('The attribute does not exist.'))
            else:
                self._attr = self._attr[0]
        else:
            self._attr = {}

    @abc.abstractproperty
    def _type(self):
        raise NotImplementedError()

    @abc.abstractproperty
    def _topics(self):
        raise NotImplementedError()

    @abc.abstractproperty
    def _default_topic(self):
        raise NotImplementedError()

    @abc.abstractproperty
    def _macro_help(self):
        raise NotImplementedError()

    @abc.abstractproperty
    def _macro_label(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def _update_config(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def title(self):
        raise NotImplementedError()

    def _add_extra_attrs_from_html_vars(self):
        pass

    def _add_extra_form_sections(self):
        pass

    def action(self):
        # TODO: remove subclass specific things specifict things (everything with _type == 'user')
        if not html.check_transaction():
            return

        title = html.get_unicode_input("title").strip()
        if not title:
            raise MKUserError("title", _("Please specify a title."))

        for this_attr in self._attrs:
            if title == this_attr['title'] and self._name != this_attr['name']:
                raise MKUserError(
                    "alias",
                    _("This alias is already used by the attribute %s.") % this_attr['name'])

        topic = html.request.var('topic', '').strip()
        help_txt = html.get_unicode_input('help').strip()
        show_in_table = html.get_checkbox('show_in_table')
        add_custom_macro = html.get_checkbox('add_custom_macro')

        if self._new:
            self._name = html.request.var("name", '').strip()
            if not self._name:
                raise MKUserError("name", _("Please specify a name for the new attribute."))
            if ' ' in self._name:
                raise MKUserError("name", _("Sorry, spaces are not allowed in attribute names."))
            if not re.match("^[-a-z0-9A-Z_]*$", self._name):
                raise MKUserError(
                    "name",
                    _("Invalid attribute name. Only the characters a-z, A-Z, 0-9, _ and - are allowed."
                     ))
            if [a for a in self._attrs if a['name'] == self._name]:
                raise MKUserError("name", _("Sorry, there is already an attribute with that name."))

            ty = html.request.var('type', '').strip()
            if ty not in [t[0] for t in custom_attr_types()]:
                raise MKUserError('type', _('The choosen attribute type is invalid.'))

            self._attr = {
                'name': self._name,
                'type': ty,
            }
            self._attrs.append(self._attr)

            add_change("edit-%sattr" % self._type,
                       _("Create new %s attribute %s") % (self._type, self._name))
        else:
            add_change("edit-%sattr" % self._type,
                       _("Modified %s attribute %s") % (self._type, self._name))
        self._attr.update({
            'title': title,
            'topic': topic,
            'help': help_txt,
            'show_in_table': show_in_table,
            'add_custom_macro': add_custom_macro,
        })

        self._add_extra_attrs_from_html_vars()

        save_custom_attrs_to_mk_file(self._all_attrs)
        self._update_config()

        return self._type + "_attrs"

    def page(self):
        # TODO: remove subclass specific things specifict things (everything with _type == 'user')
        html.begin_form("attr")
        forms.header(_("Properties"))
        forms.section(_("Name"), simple=not self._new)
        html.help(
            _("The name of the attribute is used as an internal key. It cannot be "
              "changed later."))
        if self._new:
            html.text_input("name", self._attr.get('name'))
            html.set_focus("name")
        else:
            html.write_text(self._name)
            html.set_focus("title")

        forms.section(_("Title") + "<sup>*</sup>")
        html.help(_("The title is used to label this attribute."))
        html.text_input("title", self._attr.get('title'))

        forms.section(_('Topic'))
        html.help(_('The attribute is added to this section in the edit dialog.'))
        html.dropdown('topic', self._topics, deflt=self._attr.get('topic', self._default_topic))

        forms.section(_('Help Text') + "<sup>*</sup>")
        html.help(_('You might want to add some helpful description for the attribute.'))
        html.text_area('help', self._attr.get('help', ''))

        forms.section(_('Data type'))
        html.help(_('The type of information to be stored in this attribute.'))
        if self._new:
            html.dropdown('type', custom_attr_types(), deflt=self._attr.get('type'))
        else:
            html.write(dict(custom_attr_types())[self._attr.get('type')])

        self._add_extra_form_sections()

        forms.section(_('Show in WATO host table'))
        html.help(
            _('This attribute is only visibile on the edit host and folder pages by default, but '
              'you can also make it visible in the host overview tables of WATO.'))
        html.checkbox('show_in_table',
                      self._attr.get('show_in_table', False),
                      label=_("Show the setting of the attribute in the WATO host list table"))

        forms.section(_('Add to monitoring configuration'))
        html.help(self._macro_help)
        html.checkbox('add_custom_macro',
                      self._attr.get('add_custom_macro', False),
                      label=self._macro_label)

        forms.end()
        html.show_localization_hint()
        html.button("save", _("Save"))
        html.hidden_fields()
        html.end_form()


@mode_registry.register
class ModeEditCustomUserAttr(ModeEditCustomAttr):
    @classmethod
    def name(cls):
        return "edit_user_attr"

    @classmethod
    def permissions(cls):
        return ["users", "custom_attributes"]

    @property
    def _type(self):
        return 'user'

    @property
    def _topics(self):
        return [
            ('ident', _('Identity')),
            ('security', _('Security')),
            ('notify', _('Notifications')),
            ('personal', _('Personal Settings')),
        ]

    @property
    def _default_topic(self):
        return 'personal'

    @property
    def _macro_help(self):
        return _(
            'The attribute can be added to the contact definiton in order to use it for notifications.'
        )

    @property
    def _macro_label(self):
        return _("Make this variable available in notifications")

    def _update_config(self):
        update_user_custom_attrs()

    def _add_extra_attrs_from_html_vars(self):
        self._attr['user_editable'] = html.get_checkbox('user_editable')

    def _add_extra_form_sections(self):
        forms.section(_('Editable by Users'))
        html.help(_('It is possible to let users edit their custom attributes.'))
        html.checkbox('user_editable',
                      self._attr.get('user_editable', True),
                      label=_("Users can change this attribute in their personal settings"))

    def title(self):
        if self._new:
            return _("Create User Attribute")
        return _("Edit User Attribute")

    def buttons(self):
        html.context_button(_("Back"), watolib.folder_preserving_link([("mode", "user_attrs")]),
                            "back")


@mode_registry.register
class ModeEditCustomHostAttr(ModeEditCustomAttr):
    @classmethod
    def name(cls):
        return "edit_host_attr"

    @classmethod
    def permissions(cls):
        return ["hosts", "manage_hosts", "custom_attributes"]

    @property
    def _type(self):
        return 'host'

    @property
    def _topics(self):
        return host_attribute_topic_registry.get_choices()

    @property
    def _default_topic(self):
        return "custom_attributes"

    @property
    def _macro_help(self):
        return _(
            "The attribute can be added to the host definition in order to use it as custom host attribute "
            "(sometimes called monitoring macro) in different places, for example as in check commands or "
            "notifications. You can also only display this attribute in the status GUI when enabling this "
            "option.")

    @property
    def _macro_label(self):
        return _(
            "Make this custom attribute available to check commands, notifications and the status GUI"
        )

    def _update_config(self):
        _update_host_custom_attrs()

    def title(self):
        if self._new:
            return _("Create Host Attribute")
        return _("Edit Host Attribute")

    def buttons(self):
        html.context_button(_("Back"), watolib.folder_preserving_link([("mode", "host_attrs")]),
                            "back")


class ModeCustomAttrs(WatoMode):
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        super(ModeCustomAttrs, self).__init__()
        # TODO: Inappropriate Intimacy: custom host attributes should not now about
        #       custom user attributes and vice versa. The only reason they now about
        #       each other now is that they are stored in one file.
        self._all_attrs = load_custom_attrs_from_mk_file(lock=html.is_transaction())

    @property
    def _attrs(self):
        return self._all_attrs[self._type]

    @abc.abstractproperty
    def _type(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def title(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def _update_config(self):
        raise NotImplementedError()

    def action(self):
        if html.request.var('_delete'):
            delname = html.request.var("_delete")

            # FIXME: Raise an error if the attribute is still used

            confirm_txt = _('Do you really want to delete the custom attribute "%s"?') % (delname)

            c = wato_confirm(_("Confirm deletion of attribute \"%s\"") % delname, confirm_txt)
            if c:
                for index, attr in enumerate(self._attrs):
                    if attr['name'] == delname:
                        self._attrs.pop(index)
                save_custom_attrs_to_mk_file(self._all_attrs)
                self._update_config()
                add_change("edit-%sattrs" % self._type, _("Deleted attribute %s") % (delname))
            elif c is False:
                return ""

    def page(self):
        if not self._attrs:
            html.div(_("No custom attributes are defined yet."), class_="info")
            return

        with table_element(self._type + "attrs") as table:
            for custom_attr in sorted(self._attrs, key=lambda x: x['title']):
                table.row()

                table.cell(_("Actions"), css="buttons")
                edit_url = watolib.folder_preserving_link([("mode", "edit_%s_attr" % self._type),
                                                           ("edit", custom_attr['name'])])
                delete_url = html.makeactionuri([("_delete", custom_attr['name'])])
                html.icon_button(edit_url, _("Properties"), "edit")
                html.icon_button(delete_url, _("Delete"), "delete")

                table.text_cell(_("Name"), custom_attr['name'])
                table.text_cell(_("Title"), custom_attr['title'])
                table.cell(_("Type"), dict(custom_attr_types())[custom_attr['type']])


@mode_registry.register
class ModeCustomUserAttrs(ModeCustomAttrs):
    @classmethod
    def name(cls):
        return "user_attrs"

    @classmethod
    def permissions(cls):
        return ["users", "custom_attributes"]

    @property
    def _type(self):
        return 'user'

    def _update_config(self):
        update_user_custom_attrs()

    def title(self):
        return _("Custom User Attributes")

    def buttons(self):
        html.context_button(_("Users"), watolib.folder_preserving_link([("mode", "users")]), "back")
        html.context_button(_("New attribute"),
                            watolib.folder_preserving_link([("mode", "edit_user_attr")]), "new")


@mode_registry.register
class ModeCustomHostAttrs(ModeCustomAttrs):
    @classmethod
    def name(cls):
        return "host_attrs"

    @classmethod
    def permissions(cls):
        return ["hosts", "manage_hosts", "custom_attributes"]

    @property
    def _type(self):
        return 'host'

    def _update_config(self):
        _update_host_custom_attrs()

    def title(self):
        return _("Custom Host Attributes")

    def buttons(self):
        html.context_button(_("Folder"), watolib.folder_preserving_link([("mode", "folder")]),
                            "back")
        html.context_button(_("New attribute"),
                            watolib.folder_preserving_link([("mode", "edit_host_attr")]), "new")

    def get_attributes(self):
        return self._attrs
