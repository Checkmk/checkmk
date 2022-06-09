#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""LDAP configuration and diagnose page"""

import re
from typing import Iterable, List, Optional, Type

import cmk.utils.version as cmk_version

import cmk.gui.userdb as userdb
import cmk.gui.watolib.changes as _changes
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.page_menu import (
    make_form_submit_link,
    make_simple_form_page_menu,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuSearch,
    PageMenuTopic,
)
from cmk.gui.plugins.userdb.ldap_connector import (
    ldap_attr_of_connection,
    ldap_attribute_plugins_elements,
    ldap_filter_of_connection,
    LDAPAttributePluginGroupsToRoles,
    LDAPUserConnector,
)
from cmk.gui.plugins.userdb.utils import (
    get_connection,
    load_connection_config,
    save_connection_config,
)
from cmk.gui.plugins.wato.utils import (
    IndividualOrStoredPassword,
    make_confirm_link,
    mode_registry,
    mode_url,
    redirect,
    WatoMode,
)
from cmk.gui.site_config import get_login_sites
from cmk.gui.table import table_element
from cmk.gui.type_defs import ActionResult, PermissionName
from cmk.gui.utils.html import HTML
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import DocReference, makeuri_contextless
from cmk.gui.valuespec import (
    Age,
    CascadingDropdown,
    CascadingDropdownChoice,
    Dictionary,
    DictionaryEntry,
    DropdownChoice,
    FixedValue,
    Float,
    Integer,
    LDAPDistinguishedName,
    ListOfStrings,
    rule_option_elements,
    TextInput,
    Transform,
    Tuple,
)
from cmk.gui.watolib.config_domains import ConfigDomainGUI
from cmk.gui.watolib.hosts_and_folders import folder_preserving_link, make_action_link

if cmk_version.is_managed_edition():
    import cmk.gui.cme.managed as managed  # pylint: disable=no-name-in-module
else:
    managed = None  # type: ignore[assignment]

# .
#   .--Valuespec-----------------------------------------------------------.
#   |           __     __    _                                             |
#   |           \ \   / /_ _| |_   _  ___  ___ _ __   ___  ___             |
#   |            \ \ / / _` | | | | |/ _ \/ __| '_ \ / _ \/ __|            |
#   |             \ V / (_| | | |_| |  __/\__ \ |_) |  __/ (__             |
#   |              \_/ \__,_|_|\__,_|\___||___/ .__/ \___|\___|            |
#   |                                         |_|                          |
#   '----------------------------------------------------------------------'


class LDAPConnectionValuespec(Transform):
    def __init__(self, new, connection_id):
        self._new = new
        self._connection_id = connection_id
        self._connection = get_connection(self._connection_id)

        general_elements = self._general_elements()
        connection_elements = self._connection_elements()
        user_elements = self._user_elements()
        group_elements = self._group_elements()
        other_elements = self._other_elements()

        valuespec = Dictionary(
            title=_("LDAP Connection"),
            elements=general_elements
            + connection_elements
            + user_elements
            + group_elements
            + other_elements,
            headers=[
                (_("General Properties"), [key for key, _vs in general_elements]),
                (_("LDAP Connection"), [key for key, _vs in connection_elements]),
                (_("Users"), [key for key, _vs in user_elements]),
                (_("Groups"), [key for key, _vs in group_elements]),
                (_("Attribute Sync Plugins"), ["active_plugins"]),
                (_("Other"), ["cache_livetime"]),
            ],
            render="form",
            form_narrow=True,
            optional_keys=[
                "port",
                "use_ssl",
                "bind",
                "page_size",
                "response_timeout",
                "failover_servers",
                "user_filter",
                "user_filter_group",
                "user_id",
                "lower_user_ids",
                "connect_timeout",
                "version",
                "group_filter",
                "group_member",
                "suffix",
                "create_only_on_login",
            ],
            validate=self._validate_ldap_connection,
        )

        super().__init__(valuespec=valuespec, forth=LDAPUserConnector.transform_config)

    def _general_elements(self) -> List[DictionaryEntry]:
        general_elements: List[DictionaryEntry] = []

        if self._new:
            id_element: DictionaryEntry = (
                "id",
                TextInput(
                    title=_("ID"),
                    help=_(
                        "The ID of the connection must be a unique text. It will be used as an internal key "
                        "when objects refer to the connection."
                    ),
                    allow_empty=False,
                    size=12,
                    validate=self._validate_ldap_connection_id,
                ),
            )
        else:
            id_element = (
                "id",
                FixedValue(
                    value=self._connection_id,
                    title=_("ID"),
                ),
            )

        general_elements += [id_element]

        if cmk_version.is_managed_edition():
            general_elements += managed.customer_choice_element()

        general_elements += rule_option_elements()

        return general_elements

    def _connection_elements(self):
        connection_elements = [
            (
                "directory_type",
                CascadingDropdown(
                    title=_("Directory type"),
                    help=_(
                        "Select the software the LDAP directory is based on. Depending on "
                        "the selection e.g. the attribute names used in LDAP queries will "
                        "be altered."
                    ),
                    choices=[
                        ("ad", _("Active Directory"), self._vs_directory_options("ad")),
                        ("openldap", _("OpenLDAP"), self._vs_directory_options("openldap")),
                        (
                            "389directoryserver",
                            _("389 Directory Server"),
                            self._vs_directory_options("389directoryserver"),
                        ),
                    ],
                ),
            ),
            (
                "bind",
                Tuple(
                    title=_("Bind credentials"),
                    help=_(
                        "Set the credentials to be used to connect to the LDAP server. The "
                        "used account must not be allowed to do any changes in the directory "
                        "the whole connection is read only. "
                        "In some environment an anonymous connect/bind is allowed, in this "
                        "case you don't have to configure anything here."
                        "It must be possible to list all needed user and group objects from the "
                        "directory."
                    ),
                    elements=[
                        LDAPDistinguishedName(
                            title=_("Bind DN"),
                            help=_(
                                "Specify the distinguished name to be used to bind to "
                                "the LDAP directory, e. g. <tt>CN=ldap,OU=users,DC=example,DC=com</tt>"
                            ),
                            size=63,
                        ),
                        IndividualOrStoredPassword(
                            title=_("Bind password"),
                            help=_(
                                "Specify the password to be used to bind to " "the LDAP directory."
                            ),
                        ),
                    ],
                ),
            ),
            (
                "port",
                Integer(
                    title=_("TCP port"),
                    help=_(
                        "This variable allows to specify the TCP port to "
                        "be used to connect to the LDAP server. "
                    ),
                    minvalue=1,
                    maxvalue=65535,
                    default_value=389,
                ),
            ),
            (
                "use_ssl",
                FixedValue(
                    title=_("Use SSL"),
                    help=_(
                        "Connect to the LDAP server with a SSL encrypted connection. The "
                        '<a href="wato.py?mode=edit_configvar&site=&varname=trusted_certificate_authorities">trusted '
                        "certificates authorities</a> configured in Check_MK will be used to validate the "
                        "certificate provided by the LDAP server."
                    ),
                    value=True,
                    totext=_("Encrypt the network connection using SSL."),
                ),
            ),
            (
                "connect_timeout",
                Float(
                    title=_("Connect timeout"),
                    help=_("Timeout for the initial connection to the LDAP server in seconds."),
                    unit=_("Seconds"),
                    minvalue=1.0,
                    default_value=2.0,
                ),
            ),
            (
                "version",
                DropdownChoice(
                    title=_("LDAP version"),
                    help=_(
                        "Select the LDAP version the LDAP server is serving. Most modern "
                        "servers use LDAP version 3."
                    ),
                    choices=[(2, "2"), (3, "3")],
                    default_value=3,
                ),
            ),
            (
                "page_size",
                Integer(
                    title=_("Page size"),
                    help=_(
                        "LDAP searches can be performed in paginated mode, for example to improve "
                        "the performance. This enables pagination and configures the size of the pages."
                    ),
                    minvalue=1,
                    default_value=1000,
                ),
            ),
            (
                "response_timeout",
                Integer(
                    title=_("Response timeout"),
                    unit=_("Seconds"),
                    help=_("Timeout for LDAP query responses."),
                    minvalue=0,
                    default_value=5,
                ),
            ),
            (
                "suffix",
                TextInput(
                    allow_empty=False,
                    title=_("LDAP connection suffix"),
                    help=_(
                        "The LDAP connection suffix can be used to distinguish equal named objects "
                        "(name conflicts), for example user accounts, from different LDAP connections.<br>"
                        "It is used in the following situations:<br><br>"
                        "During LDAP synchronization, the LDAP sync might discover that a user to be "
                        "synchronized from from the current LDAP is already being synchronized from "
                        "another LDAP connection. Without the suffix configured this results in a name "
                        "conflict and the later user not being synchronized. If the connection has a "
                        "suffix configured, this suffix is added to the later username in case of the name "
                        "conflict to resolve it. The user will then be named <tt>[username]@[suffix]</tt> "
                        "instead of just <tt>[username]</tt>.<br><br>"
                        "In the case a user which users name is existing in multiple LDAP directories, "
                        "but associated to different persons, your user can insert <tt>[username]@[suffix]</tt>"
                        " during login instead of just the plain <tt>[username]</tt> to tell which LDAP "
                        "directory he is assigned to. Users without name conflict just need to provide their "
                        "regular username as usual."
                    ),
                    regex=re.compile(r"^[A-Z0-9.-]+(?:\.[A-Z]{2,24})?$", re.I),
                    validate=self._validate_ldap_connection_suffix,
                ),
            ),
        ]

        return connection_elements

    def _vs_directory_options(self, ty: str) -> Dictionary:
        connect_to_choices: List[CascadingDropdownChoice] = [
            (
                "fixed_list",
                _("Manually specify list of LDAP servers"),
                Dictionary(
                    elements=[
                        (
                            "server",
                            TextInput(
                                title=_("LDAP Server"),
                                help=_(
                                    "Set the host address of the LDAP server. Might be an IP address or "
                                    "resolvable hostname."
                                ),
                                allow_empty=False,
                            ),
                        ),
                        (
                            "failover_servers",
                            ListOfStrings(
                                title=_("Failover Servers"),
                                help=_(
                                    "When the connection to the first server fails with connect specific errors "
                                    "like timeouts or some other network related problems, the connect mechanism "
                                    "will try to use this server instead of the server configured above. If you "
                                    "use persistent connections (default), the connection is being used until the "
                                    "LDAP is not reachable or the local webserver is restarted."
                                ),
                                allow_empty=False,
                            ),
                        ),
                    ],
                    optional_keys=["failover_servers"],
                ),
            ),
        ]

        if ty == "ad":
            connect_to_choices.append(
                (
                    "discover",
                    _("Automatically discover LDAP server"),
                    Dictionary(
                        elements=[
                            (
                                "domain",
                                TextInput(
                                    title=_("DNS domain name to discover LDAP servers of"),
                                    help=_(
                                        "Configure the DNS domain name of your Active directory domain here, Check_MK "
                                        "will then query this domain for it's closest domain controller to communicate "
                                        "with."
                                    ),
                                    allow_empty=False,
                                ),
                            ),
                        ],
                        optional_keys=[],
                    ),
                ),
            )

        return Dictionary(
            elements=[
                (
                    "connect_to",
                    CascadingDropdown(
                        title=_("Connect to"),
                        choices=connect_to_choices,
                    ),
                ),
            ],
            optional_keys=[],
        )

    def _user_elements(self):
        user_elements = [
            (
                "user_dn",
                LDAPDistinguishedName(
                    title=_("User base DN"),
                    help=_(
                        "Give a base distinguished name here, e. g. <tt>OU=users,DC=example,DC=com</tt><br> "
                        "All user accounts to synchronize must be located below this one."
                    ),
                    size=80,
                ),
            ),
            (
                "user_scope",
                DropdownChoice(
                    title=_("Search scope"),
                    help=_(
                        "Scope to be used in LDAP searches. In most cases <i>Search whole subtree below "
                        "the base DN</i> is the best choice. "
                        "It searches for matching objects recursively."
                    ),
                    choices=[
                        ("sub", _("Search whole subtree below the base DN")),
                        ("base", _("Search only the entry at the base DN")),
                        ("one", _("Search all entries one level below the base DN")),
                    ],
                    default_value="sub",
                ),
            ),
            (
                "user_filter",
                TextInput(
                    title=_("Search filter"),
                    help=_(
                        "Using this option you can define an optional LDAP filter which is used during "
                        "LDAP searches. It can be used to only handle a subset of the users below the given "
                        "base DN.<br><br>Some common examples:<br><br> "
                        "All user objects in LDAP:<br> "
                        "<tt>(&(objectclass=user)(objectcategory=person))</tt><br> "
                        "Members of a group:<br> "
                        "<tt>(&(objectclass=user)(objectcategory=person)(memberof=CN=cmk-users,OU=groups,DC=example,DC=com))</tt><br> "
                        "Members of a nested group:<br> "
                        "<tt>(&(objectclass=user)(objectcategory=person)(memberof:1.2.840.113556.1.4.1941:=CN=cmk-users,OU=groups,DC=example,DC=com))</tt><br>"
                    ),
                    size=80,
                    default_value=lambda: ldap_filter_of_connection(
                        self._connection_id, "users", False
                    ),
                ),
            ),
            (
                "user_filter_group",
                LDAPDistinguishedName(
                    title=_("Filter group (see help)"),
                    help=_(
                        "Using this option you can define the DN of a group object which is used to filter the users. "
                        "Only members of this group will then be synchronized. This is a filter which can be "
                        'used to extend capabilities of the regular "Search Filter". Using the search filter '
                        "you can only define filters which directly apply to the user objects. To filter by "
                        "group memberships, you can use the <tt>memberOf</tt> attribute of the user objects in some "
                        "directories. But some directories do not have such attributes because the memberships "
                        "are stored in the group objects as e.g. <tt>member</tt> attributes. You should use the "
                        "regular search filter whenever possible and only use this filter when it is really "
                        "neccessary. Finally you can say, you should not use this option when using Active Directory. "
                        "This option is neccessary in OpenLDAP directories when you like to filter by group membership.<br><br>"
                        "If using, give a plain distinguished name of a group here, e. g. "
                        "<tt>CN=cmk-users,OU=groups,DC=example,DC=com</tt>"
                    ),
                    size=80,
                ),
            ),
            (
                "user_id",
                TextInput(
                    title=_("User-ID attribute"),
                    help=_(
                        "The attribute used to identify the individual users. It must have "
                        "unique values to make an user identifyable by the value of this "
                        "attribute."
                    ),
                    default_value=lambda: ldap_attr_of_connection(self._connection_id, "user_id"),
                ),
            ),
            (
                "lower_user_ids",
                FixedValue(
                    title=_("Lower case User-IDs"),
                    help=_("Convert imported User-IDs to lower case during synchronization."),
                    value=True,
                    totext=_("Enforce lower case User-IDs."),
                ),
            ),
            (
                "user_id_umlauts",
                Transform(
                    valuespec=DropdownChoice(
                        title=_("Umlauts in User-IDs (deprecated)"),
                        help=_(
                            "Checkmk was not not supporting special characters (like Umlauts) in "
                            "User-IDs. To deal with LDAP users having umlauts in their User-IDs "
                            "you had the choice to replace umlauts with other characters. This option "
                            "is still available for compatibility reasons, but you are adviced to use "
                            'the "keep" option for new installations.'
                        ),
                        choices=[
                            ("keep", _("Keep special characters")),
                            ("replace", _('Replace umlauts like "&uuml;" with "ue"')),
                        ],
                        default_value="keep",
                    ),
                    forth=lambda x: "keep" if (x == "skip") else x,
                ),
            ),
            (
                "create_only_on_login",
                FixedValue(
                    title=_("Create users only on login"),
                    value=True,
                    totext=_(
                        "Instead of creating the user accounts during the regular sync, create "
                        "the user on the first login."
                    ),
                ),
            ),
        ]

        return user_elements

    def _group_elements(self):
        group_elements = [
            (
                "group_dn",
                LDAPDistinguishedName(
                    title=_("Group base DN"),
                    help=_(
                        "Give a base distinguished name here, e. g. <tt>OU=groups,DC=example,DC=com</tt><br> "
                        "All groups used must be located below this one."
                    ),
                    size=80,
                ),
            ),
            (
                "group_scope",
                DropdownChoice(
                    title=_("Search scope"),
                    help=_(
                        "Scope to be used in group related LDAP searches. In most cases "
                        "<i>Search whole subtree below the base DN</i> "
                        "is the best choice. It searches for matching objects in the given base "
                        "recursively."
                    ),
                    choices=[
                        ("sub", _("Search whole subtree below the base DN")),
                        ("base", _("Search only the entry at the base DN")),
                        ("one", _("Search all entries one level below the base DN")),
                    ],
                    default_value="sub",
                ),
            ),
            (
                "group_filter",
                TextInput(
                    title=_("Search filter"),
                    help=_(
                        "Using this option you can define an optional LDAP filter which is used "
                        "during group related LDAP searches. It can be used to only handle a "
                        "subset of the groups below the given base DN.<br><br>"
                        "e.g. <tt>(objectclass=group)</tt>"
                    ),
                    size=80,
                    default_value=lambda: ldap_filter_of_connection(
                        self._connection_id, "groups", False
                    ),
                ),
            ),
            (
                "group_member",
                TextInput(
                    title=_("Member attribute"),
                    help=_("The attribute used to identify users group memberships."),
                    default_value=lambda: ldap_attr_of_connection(self._connection_id, "member"),
                ),
            ),
        ]

        return group_elements

    def _other_elements(self):
        other_elements = [
            (
                "active_plugins",
                Dictionary(
                    title=_("Attribute sync plugins"),
                    help=_(
                        "It is possible to fetch several attributes of users, like Email or full names, "
                        "from the LDAP directory. This is done by plugins which can individually enabled "
                        "or disabled. When enabling a plugin, it is used upon the next synchonisation of "
                        "user accounts for gathering their attributes. The user options which get imported "
                        "into Check_MK from LDAP will be locked in WATO."
                    ),
                    elements=lambda: ldap_attribute_plugins_elements(self._connection),
                    default_keys=["email", "alias", "auth_expire"],
                ),
            ),
            (
                "cache_livetime",
                Age(
                    title=_("Sync interval"),
                    help=_(
                        "This option defines the interval of the LDAP synchronization. This setting is only "
                        "used by sites which have the "
                        '<a href="wato.py?mode=sites">Automatic User '
                        "Synchronization</a> enabled.<br><br>"
                        "Please note: Passwords of the users are never stored in WATO and therefor never cached!"
                    ),
                    minvalue=60,
                    default_value=300,
                    display=["days", "hours", "minutes"],
                ),
            ),
        ]

        return other_elements

    def _validate_ldap_connection_id(self, value, varprefix):
        if value in [c["id"] for c in active_config.user_connections]:
            raise MKUserError(
                varprefix,
                _("This ID is already used by another connection. Please choose another one."),
            )

    def _validate_ldap_connection(self, value, varprefix):
        for role_id, group_specs in value["active_plugins"].get("groups_to_roles", {}).items():
            if role_id == "nested":
                continue  # This is the option to enabled/disable nested group handling, not a role to DN entry

            for index, group_spec in enumerate(group_specs):
                dn, connection_id = group_spec

                if connection_id is None:
                    group_dn = value["group_dn"]

                else:
                    connection = get_connection(connection_id)
                    if not connection:
                        continue
                    assert isinstance(connection, LDAPUserConnector)
                    group_dn = connection.get_group_dn()

                if not group_dn:
                    raise MKUserError(
                        varprefix,
                        _(
                            "You need to configure the group base DN to be able to "
                            "use the roles synchronization plugin."
                        ),
                    )

                if not dn.lower().endswith(group_dn.lower()):
                    varname = "connection_p_active_plugins_p_groups_to_roles_p_%s_1_%d" % (
                        role_id,
                        index,
                    )
                    raise MKUserError(
                        varname, _("The configured DN does not match the group base DN.")
                    )

    def _validate_ldap_connection_suffix(self, value, varprefix):
        for connection in active_config.user_connections:
            suffix = connection.get("suffix")
            if suffix is None:
                continue

            connection_id = connection["id"]
            if connection_id != self._connection_id and value == suffix:
                raise MKUserError(
                    varprefix,
                    _("This suffix is already used by connection %s." "Please choose another one.")
                    % connection_id,
                )


class LDAPMode(WatoMode):
    def _add_change(self, action_name, text):
        _changes.add_change(action_name, text, domains=[ConfigDomainGUI], sites=get_login_sites())


@mode_registry.register
class ModeLDAPConfig(LDAPMode):
    @classmethod
    def name(cls) -> str:
        return "ldap_config"

    @classmethod
    def permissions(cls) -> list[PermissionName]:
        return ["global"]

    def title(self) -> str:
        return _("LDAP connections")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        page_menu: PageMenu = PageMenu(
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
                                        folder_preserving_link([("mode", "edit_ldap_connection")])
                                    ),
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
            inpage_search=PageMenuSearch(),
        )
        page_menu.add_doc_reference(title=self.title(), doc_ref=DocReference.LDAP)
        return page_menu

    def _page_menu_entries_related(self) -> Iterable[PageMenuEntry]:
        yield PageMenuEntry(
            title=_("Users"),
            icon_name="users",
            item=make_simple_link(
                makeuri_contextless(
                    request,
                    [("mode", "users")],
                    filename="wato.py",
                )
            ),
        )

    def action(self) -> ActionResult:
        if not transactions.check_transaction():
            return redirect(self.mode_url())

        connections = load_connection_config(lock=True)
        if request.has_var("_delete"):
            index = request.get_integer_input_mandatory("_delete")
            connection = connections[index]
            self._add_change(
                "delete-ldap-connection", _("Deleted LDAP connection %s") % (connection["id"])
            )
            del connections[index]
            save_connection_config(connections)

        elif request.has_var("_move"):
            from_pos = request.get_integer_input_mandatory("_move")
            to_pos = request.get_integer_input_mandatory("_index")
            connection = connections[from_pos]
            self._add_change(
                "move-ldap-connection",
                _("Changed position of LDAP connection %s to %d") % (connection["id"], to_pos),
            )
            del connections[from_pos]  # make to_pos now match!
            connections[to_pos:to_pos] = [connection]
            save_connection_config(connections)

        return redirect(self.mode_url())

    def page(self) -> None:
        with table_element() as table:
            for index, connection in enumerate(load_connection_config()):
                table.row()

                table.cell(_("Actions"), css=["buttons"])
                edit_url = folder_preserving_link(
                    [("mode", "edit_ldap_connection"), ("id", connection["id"])]
                )
                delete_url = make_confirm_link(
                    url=make_action_link([("mode", "ldap_config"), ("_delete", index)]),
                    message=_("Do you really want to delete the LDAP connection <b>%s</b>?")
                    % connection["id"],
                )
                drag_url = make_action_link([("mode", "ldap_config"), ("_move", index)])
                clone_url = folder_preserving_link(
                    [("mode", "edit_ldap_connection"), ("clone", connection["id"])]
                )

                html.icon_button(edit_url, _("Edit this LDAP connection"), "edit")
                html.icon_button(clone_url, _("Create a copy of this LDAP connection"), "clone")
                html.element_dragger_url("tr", base_url=drag_url)
                html.icon_button(delete_url, _("Delete this LDAP connection"), "delete")

                table.cell("", css=["narrow"])
                if connection.get("disabled"):
                    html.icon(
                        "disabled",
                        _("This connection is currently not being used for synchronization."),
                    )
                else:
                    html.empty_icon_button()

                table.cell(_("ID"), connection["id"])

                if cmk_version.is_managed_edition():
                    table.cell(_("Customer"), managed.get_customer_name(connection))

                table.cell(_("Description"))
                url = connection.get("docu_url")
                if url:
                    html.icon_button(
                        url, _("Context information about this connection"), "url", target="_blank"
                    )
                    html.write_text("&nbsp;")
                html.write_text(connection["description"])


@mode_registry.register
class ModeEditLDAPConnection(LDAPMode):
    @classmethod
    def name(cls) -> str:
        return "edit_ldap_connection"

    @classmethod
    def permissions(cls) -> list[PermissionName]:
        return ["global"]

    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeLDAPConfig

    def _from_vars(self):
        self._connection_id = request.get_ascii_input("id")
        self._connection_cfg = {}
        self._connections = load_connection_config(lock=transactions.is_transaction())

        if self._connection_id is None:
            clone_id = request.var("clone")
            if clone_id is not None:
                self._connection_cfg = self._get_connection_cfg_and_index(clone_id)[0]

            self._new = True
            return

        self._new = False
        self._connection_cfg, self._connection_nr = self._get_connection_cfg_and_index(
            self._connection_id
        )

    def _get_connection_cfg_and_index(self, connection_id):
        for index, cfg in enumerate(self._connections):
            if cfg["id"] == connection_id:
                return cfg, index

        if not self._connection_cfg:
            raise MKUserError(None, _("The requested connection does not exist."))
        return None

    def title(self) -> str:
        if self._new:
            return _("Add LDAP connection")
        assert self._connection_id is not None
        return _("Edit LDAP connection: %s") % self._connection_id

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        menu = make_simple_form_page_menu(
            _("Connection"),
            breadcrumb,
            form_name="connection",
            button_name="_save",
            save_title=_("Save"),
        )
        menu.dropdowns[0].topics[0].entries.insert(
            1,
            PageMenuEntry(
                title=_("Save & test"),
                icon_name="save",
                item=make_form_submit_link(form_name="connection", button_name="_test"),
                is_shortcut=True,
                is_suggested=True,
            ),
        )

        return menu

    def action(self) -> ActionResult:
        if not transactions.check_transaction():
            return None

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
        active_config.user_connections = (
            self._connections
        )  # make directly available on current page
        if request.var("_save"):
            return redirect(mode_url("ldap_config"))
        # Handle the case where a user hit "Save & Test" during creation
        return redirect(self.mode_url(_test="1", id=self._connection_id))

    def page(self) -> None:
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
        html.h2(_("Diagnostics"))
        if not request.var("_test") or not self._connection_id:
            html.show_message(
                HTML(
                    "<p>%s</p><p>%s</p>"
                    % (
                        _(
                            "You can verify the single parts of your ldap configuration using this "
                            "dialog. Simply make your configuration in the form on the left side and "
                            'hit the "Save & Test" button to execute the tests. After '
                            "the page reload, you should see the results of the test here."
                        ),
                        _(
                            "If you need help during configuration or experience problems, please refer "
                            'to the <a target="_blank" '
                            'href="https://checkmk.com/checkmk_multisite_ldap_integration.html">'
                            "LDAP Documentation</a>."
                        ),
                    )
                )
            )
        else:
            connection = userdb.get_connection(self._connection_id)
            assert isinstance(connection, LDAPUserConnector)

            for address in connection.servers():
                html.h3("%s: %s" % (_("Server"), address))
                with table_element("test", searchable=False) as table:
                    for title, test_func in self._tests():
                        table.row()
                        try:
                            state, msg = test_func(connection, address)
                        except Exception as e:
                            state = False
                            msg = _("Exception: %s") % e
                            logger.exception("error testing LDAP %s for %s", title, address)

                        if state:
                            img = html.render_icon("success", _("Success"))
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
            (_("Connection"), self._test_connect),
            (_("User Base-DN"), self._test_user_base_dn),
            (_("Count Users"), self._test_user_count),
            (_("Group Base-DN"), self._test_group_base_dn),
            (_("Count Groups"), self._test_group_count),
            (_("Sync-Plugin: Roles"), self._test_groups_to_roles),
        ]

    def _test_connect(self, connection, address):
        conn, msg = connection.connect_server(address)
        if conn:
            return (True, _("Connection established. The connection settings seem to be ok."))
        return (False, msg)

    def _test_user_base_dn(self, connection, address):
        if not connection.has_user_base_dn_configured():
            return (False, _("The User Base DN is not configured."))
        connection.connect(enforce_new=True, enforce_server=address)
        if connection.user_base_dn_exists():
            return (True, _("The User Base DN could be found."))
        if connection.has_bind_credentials_configured():
            return (
                False,
                _(
                    "The User Base DN could not be found. Maybe the provided "
                    "user (provided via bind credentials) has no permission to "
                    "access the Base DN or the credentials are wrong."
                ),
            )
        return (
            False,
            _(
                "The User Base DN could not be found. Seems you need "
                "to configure proper bind credentials."
            ),
        )

    def _test_user_count(self, connection, address):
        if not connection.has_user_base_dn_configured():
            return (False, _("The User Base DN is not configured."))
        connection.connect(enforce_new=True, enforce_server=address)
        try:
            ldap_users = connection.get_users()
            msg = _("Found no user object for synchronization. Please check your filter settings.")
        except Exception as e:
            ldap_users = None
            msg = "%s" % e
            if "successful bind must be completed" in msg:
                if not connection.has_bind_credentials_configured():
                    return (False, _("Please configure proper bind credentials."))
                return (
                    False,
                    _(
                        "Maybe the provided user (provided via bind credentials) has not "
                        "enough permissions or the credentials are wrong."
                    ),
                )

        if ldap_users and len(ldap_users) > 0:
            return (True, _("Found %d users for synchronization.") % len(ldap_users))
        return (False, msg)

    def _test_group_base_dn(self, connection, address):
        if not connection.has_group_base_dn_configured():
            return (False, _("The Group Base DN is not configured, not fetching any groups."))
        connection.connect(enforce_new=True, enforce_server=address)
        if connection.group_base_dn_exists():
            return (True, _("The Group Base DN could be found."))
        return (False, _("The Group Base DN could not be found."))

    def _test_group_count(self, connection, address):
        if not connection.has_group_base_dn_configured():
            return (False, _("The Group Base DN is not configured, not fetching any groups."))
        connection.connect(enforce_new=True, enforce_server=address)
        try:
            ldap_groups = connection.get_groups()
            msg = _("Found no group object for synchronization. Please check your filter settings.")
        except Exception as e:
            ldap_groups = None
            msg = "%s" % e
            if "successful bind must be completed" in msg:
                if not connection.has_bind_credentials_configured():
                    return (False, _("Please configure proper bind credentials."))
                return (
                    False,
                    _(
                        "Maybe the provided user (provided via bind credentials) has not "
                        "enough permissions or the credentials are wrong."
                    ),
                )
        if ldap_groups and len(ldap_groups) > 0:
            return (True, _("Found %d groups for synchronization.") % len(ldap_groups))
        return (False, msg)

    def _test_groups_to_roles(self, connection, address):
        active_plugins = connection.active_plugins()
        if "groups_to_roles" not in active_plugins:
            return True, _("Skipping this test (Plugin is not enabled)")

        params = active_plugins["groups_to_roles"]
        connection.connect(enforce_new=True, enforce_server=address)

        plugin = LDAPAttributePluginGroupsToRoles()
        ldap_groups = plugin.fetch_needed_groups_for_groups_to_roles(connection, params)

        num_groups = 0
        for role_id, group_specs in active_plugins["groups_to_roles"].items():
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
                    return False, _("Could not find the group specified for role %s") % role_id

                num_groups += 1
        return True, _("Found all %d groups.") % num_groups

    def _valuespec(self):
        return LDAPConnectionValuespec(self._new, self._connection_id)
