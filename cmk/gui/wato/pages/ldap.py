#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""LDAP configuration and diagnose page"""

from typing import Iterable, Optional, Type

import cmk.utils.version as cmk_version

import cmk.gui.config as config
import cmk.gui.watolib as watolib
import cmk.gui.userdb as userdb
from cmk.gui.table import table_element
from cmk.gui.plugins.userdb.ldap_connector import (
    LDAPUserConnector,
    LDAPAttributePluginGroupsToRoles,
    LDAPConnectionValuespec,
)
from cmk.gui.log import logger
from cmk.gui.htmllib import HTML
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.plugins.userdb.utils import load_connection_config, save_connection_config
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.page_menu import (
    PageMenu,
    PageMenuDropdown,
    PageMenuTopic,
    PageMenuEntry,
    make_simple_link,
    make_simple_form_page_menu,
    make_form_submit_link,
)

from cmk.gui.plugins.wato import (
    WatoMode,
    mode_registry,
    add_change,
    make_action_link,
    wato_confirm,
)

if cmk_version.is_managed_edition():
    import cmk.gui.cme.managed as managed  # pylint: disable=no-name-in-module
else:
    managed = None  # type: ignore[assignment]


class LDAPMode(WatoMode):
    def _add_change(self, action_name, text):
        add_change(action_name,
                   text,
                   domains=[watolib.ConfigDomainGUI],
                   sites=config.get_login_sites())


@mode_registry.register
class ModeLDAPConfig(LDAPMode):
    @classmethod
    def name(cls):
        return "ldap_config"

    @classmethod
    def permissions(cls):
        return ["global"]

    def title(self):
        return _("LDAP connections")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="connections",
                    title=_("Connections"),
                    topics=[
                        PageMenuTopic(
                            title=_("Add connection"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Add connection"),
                                    icon_name="new",
                                    item=make_simple_link(
                                        watolib.folder_preserving_link([("mode",
                                                                         "edit_ldap_connection")])),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                            ],
                        ),
                    ],
                ),
                PageMenuDropdown(
                    name="related",
                    title=_("Related"),
                    topics=[
                        PageMenuTopic(
                            title=_("Setup"),
                            entries=list(self._page_menu_entries_related()),
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
        )

    def _page_menu_entries_related(self) -> Iterable[PageMenuEntry]:
        yield PageMenuEntry(
            title=_("Users"),
            icon_name="users",
            item=make_simple_link(html.makeuri_contextless([("mode", "users")],
                                                           filename="wato.py")),
        )

    def action(self):
        connections = load_connection_config(lock=True)
        if html.request.has_var("_delete"):
            index = html.request.get_integer_input_mandatory("_delete")
            connection = connections[index]
            c = wato_confirm(
                _("Confirm deletion of LDAP connection"),
                _("Do you really want to delete the LDAP connection <b>%s</b>?") %
                (connection["id"]))
            if c:
                self._add_change("delete-ldap-connection",
                                 _("Deleted LDAP connection %s") % (connection["id"]))
                del connections[index]
                save_connection_config(connections)
            elif c is False:
                return ""
            else:
                return

        elif html.request.has_var("_move"):
            if not html.check_transaction():
                return

            from_pos = html.request.get_integer_input_mandatory("_move")
            to_pos = html.request.get_integer_input_mandatory("_index")
            connection = connections[from_pos]
            self._add_change(
                "move-ldap-connection",
                _("Changed position of LDAP connection %s to %d") % (connection["id"], to_pos))
            del connections[from_pos]  # make to_pos now match!
            connections[to_pos:to_pos] = [connection]
            save_connection_config(connections)

    def page(self):
        with table_element() as table:
            for index, connection in enumerate(load_connection_config()):
                table.row()

                table.cell(_("Actions"), css="buttons")
                edit_url = watolib.folder_preserving_link([("mode", "edit_ldap_connection"),
                                                           ("id", connection["id"])])
                delete_url = make_action_link([("mode", "ldap_config"), ("_delete", index)])
                drag_url = make_action_link([("mode", "ldap_config"), ("_move", index)])
                clone_url = watolib.folder_preserving_link([("mode", "edit_ldap_connection"),
                                                            ("clone", connection["id"])])

                html.icon_button(edit_url, _("Edit this LDAP connection"), "edit")
                html.icon_button(clone_url, _("Create a copy of this LDAP connection"), "clone")
                html.element_dragger_url("tr", base_url=drag_url)
                html.icon_button(delete_url, _("Delete this LDAP connection"), "delete")

                table.cell("", css="narrow")
                if connection.get("disabled"):
                    html.icon("disabled",
                              _("This connection is currently not being used for synchronization."))
                else:
                    html.empty_icon_button()

                table.cell(_("ID"), connection["id"])

                if cmk_version.is_managed_edition():
                    table.cell(_("Customer"), managed.get_customer_name(connection))

                table.cell(_("Description"))
                url = connection.get("docu_url")
                if url:
                    html.icon_button(url,
                                     _("Context information about this connection"),
                                     "url",
                                     target="_blank")
                    html.write("&nbsp;")
                html.write_text(connection["description"])


@mode_registry.register
class ModeEditLDAPConnection(LDAPMode):
    @classmethod
    def name(cls):
        return "edit_ldap_connection"

    @classmethod
    def permissions(cls):
        return ["global"]

    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeLDAPConfig

    def _from_vars(self):
        self._connection_id = html.request.get_ascii_input("id")
        self._connection_cfg = {}
        self._connections = load_connection_config(lock=html.is_transaction())

        if self._connection_id is None:
            clone_id = html.request.var("clone")
            if clone_id is not None:
                self._connection_cfg = self._get_connection_cfg_and_index(clone_id)[0]

            self._new = True
            return

        self._new = False
        self._connection_cfg, self._connection_nr = self._get_connection_cfg_and_index(
            self._connection_id)

    def _get_connection_cfg_and_index(self, connection_id):
        for index, cfg in enumerate(self._connections):
            if cfg['id'] == connection_id:
                return cfg, index

        if not self._connection_cfg:
            raise MKUserError(None, _("The requested connection does not exist."))

    def title(self):
        if self._new:
            return _("Add LDAP connection")
        return _("Edit LDAP connection: %s") % html.render_text(self._connection_id)

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        menu = make_simple_form_page_menu(breadcrumb,
                                          form_name="connection",
                                          button_name="_save",
                                          save_title=_("Save"))
        menu.dropdowns[0].topics[0].entries.insert(
            1,
            PageMenuEntry(
                title=_("Save & test"),
                icon_name="save",
                item=make_form_submit_link(form_name="connection", button_name="_test"),
                is_shortcut=True,
                is_suggested=True,
            ))

        return menu

    def action(self):
        if not html.check_transaction():
            return

        vs = self._valuespec()
        self._connection_cfg = vs.from_html_vars("connection")
        vs.validate_value(self._connection_cfg, "connection")

        self._connection_cfg["type"] = "ldap"

        if self._new:
            self._connections.insert(0, self._connection_cfg)
            self._connection_id = self._connection_cfg["id"]
        else:
            self._connection_cfg["id"] = self._connection_id
            self._connections[self._connection_nr] = self._connection_cfg

        assert self._connection_id is not None

        if self._new:
            log_what = "new-ldap-connection"
            log_text = _("Created new LDAP connection")
        else:
            log_what = "edit-ldap-connection"
            log_text = _("Changed LDAP connection %s") % self._connection_id
        self._add_change(log_what, log_text)

        save_connection_config(self._connections)
        config.user_connections = self._connections  # make directly available on current page
        if html.request.var("_save"):
            return "ldap_config"
        # Fix the case where a user hit "Save & Test" during creation
        html.request.set_var('id', self._connection_id)

    def page(self):
        html.open_div(id_="ldap")
        html.open_table()
        html.open_tr()

        html.open_td()
        html.begin_form("connection", method="POST")
        html.prevent_password_auto_completion()
        vs = self._valuespec()
        vs.render_input("connection", self._connection_cfg)
        vs.set_focus("connection")
        html.hidden_fields()
        html.end_form()
        html.close_td()

        html.open_td(style="padding-left:10px;vertical-align:top")
        html.h2(_('Diagnostics'))
        if not html.request.var('_test') or not self._connection_id:
            html.show_message(
                HTML(
                    '<p>%s</p><p>%s</p>' %
                    (_('You can verify the single parts of your ldap configuration using this '
                       'dialog. Simply make your configuration in the form on the left side and '
                       'hit the "Save & Test" button to execute the tests. After '
                       'the page reload, you should see the results of the test here.'),
                     _('If you need help during configuration or experience problems, please refer '
                       'to the <a target="_blank" '
                       'href="https://checkmk.com/checkmk_multisite_ldap_integration.html">'
                       'LDAP Documentation</a>.'))))
        else:
            connection = userdb.get_connection(self._connection_id)
            assert isinstance(connection, LDAPUserConnector)

            for address in connection.servers():
                html.h3("%s: %s" % (_('Server'), address))
                with table_element('test', searchable=False) as table:
                    for title, test_func in self._tests():
                        table.row()
                        try:
                            state, msg = test_func(connection, address)
                        except Exception as e:
                            state = False
                            msg = _('Exception: %s') % html.render_text("%s" % e)
                            logger.exception("error testing LDAP %s for %s", title, address)

                        if state:
                            img = html.render_icon("success", _('Success'))
                        else:
                            img = html.render_icon("failed", _("Failed"))

                        table.cell(_("Test"), title)
                        table.cell(_("State"), img)
                        table.cell(_("Details"), msg)

            connection.disconnect()

        html.close_td()
        html.close_tr()
        html.close_table()
        html.close_div()

    def _tests(self):
        return [
            (_('Connection'), self._test_connect),
            (_('User Base-DN'), self._test_user_base_dn),
            (_('Count Users'), self._test_user_count),
            (_('Group Base-DN'), self._test_group_base_dn),
            (_('Count Groups'), self._test_group_count),
            (_('Sync-Plugin: Roles'), self._test_groups_to_roles),
        ]

    def _test_connect(self, connection, address):
        conn, msg = connection.connect_server(address)
        if conn:
            return (True, _('Connection established. The connection settings seem to be ok.'))
        return (False, msg)

    def _test_user_base_dn(self, connection, address):
        if not connection.has_user_base_dn_configured():
            return (False, _('The User Base DN is not configured.'))
        connection.connect(enforce_new=True, enforce_server=address)
        if connection.user_base_dn_exists():
            return (True, _('The User Base DN could be found.'))
        if connection.has_bind_credentials_configured():
            return (False,
                    _('The User Base DN could not be found. Maybe the provided '
                      'user (provided via bind credentials) has no permission to '
                      'access the Base DN or the credentials are wrong.'))
        return (False,
                _('The User Base DN could not be found. Seems you need '
                  'to configure proper bind credentials.'))

    def _test_user_count(self, connection, address):
        if not connection.has_user_base_dn_configured():
            return (False, _('The User Base DN is not configured.'))
        connection.connect(enforce_new=True, enforce_server=address)
        try:
            ldap_users = connection.get_users()
            msg = _('Found no user object for synchronization. Please check your filter settings.')
        except Exception as e:
            ldap_users = None
            msg = "%s" % e
            if 'successful bind must be completed' in msg:
                if not connection.has_bind_credentials_configured():
                    return (False, _('Please configure proper bind credentials.'))
                return (False,
                        _('Maybe the provided user (provided via bind credentials) has not '
                          'enough permissions or the credentials are wrong.'))

        if ldap_users and len(ldap_users) > 0:
            return (True, _('Found %d users for synchronization.') % len(ldap_users))
        return (False, msg)

    def _test_group_base_dn(self, connection, address):
        if not connection.has_group_base_dn_configured():
            return (False, _('The Group Base DN is not configured, not fetching any groups.'))
        connection.connect(enforce_new=True, enforce_server=address)
        if connection.group_base_dn_exists():
            return (True, _('The Group Base DN could be found.'))
        return (False, _('The Group Base DN could not be found.'))

    def _test_group_count(self, connection, address):
        if not connection.has_group_base_dn_configured():
            return (False, _('The Group Base DN is not configured, not fetching any groups.'))
        connection.connect(enforce_new=True, enforce_server=address)
        try:
            ldap_groups = connection.get_groups()
            msg = _('Found no group object for synchronization. Please check your filter settings.')
        except Exception as e:
            ldap_groups = None
            msg = "%s" % e
            if 'successful bind must be completed' in msg:
                if not connection.has_bind_credentials_configured():
                    return (False, _('Please configure proper bind credentials.'))
                return (False,
                        _('Maybe the provided user (provided via bind credentials) has not '
                          'enough permissions or the credentials are wrong.'))
        if ldap_groups and len(ldap_groups) > 0:
            return (True, _('Found %d groups for synchronization.') % len(ldap_groups))
        return (False, msg)

    def _test_groups_to_roles(self, connection, address):
        active_plugins = connection.active_plugins()
        if 'groups_to_roles' not in active_plugins:
            return True, _('Skipping this test (Plugin is not enabled)')

        params = active_plugins['groups_to_roles']
        connection.connect(enforce_new=True, enforce_server=address)

        plugin = LDAPAttributePluginGroupsToRoles()
        ldap_groups = plugin.fetch_needed_groups_for_groups_to_roles(connection, params)

        num_groups = 0
        for role_id, group_specs in active_plugins['groups_to_roles'].items():
            if not isinstance(group_specs, list):
                group_specs = [group_specs]

            for group_spec in group_specs:
                if isinstance(group_spec, str):
                    dn = group_spec  # be compatible to old config without connection spec
                elif not isinstance(group_spec, tuple):
                    continue  # skip non configured ones (old valuespecs allowed None)
                else:
                    dn = group_spec[0]

                if dn.lower() not in ldap_groups:
                    return False, _('Could not find the group specified for role %s') % role_id

                num_groups += 1
        return True, _('Found all %d groups.') % num_groups

    def _valuespec(self):
        return LDAPConnectionValuespec(self._new, self._connection_id)
