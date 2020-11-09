#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Mode for managing sites"""

import traceback
import time
import multiprocessing
import socket
import contextlib
import binascii
import queue
from typing import (Dict, List, NamedTuple, Union, Tuple as _Tuple, Optional, Type, Iterator,
                    overload)

from six import ensure_binary, ensure_str
from OpenSSL import crypto  # type: ignore[import]
from OpenSSL import SSL  # type: ignore[attr-defined]
# mypy can't find x509 for some reason (is a c extension involved?)
from cryptography.x509.oid import ExtensionOID, NameOID  # type: ignore[import]
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes

import cmk.utils.version as cmk_version
import cmk.utils.paths

from cmk.gui.sites import SiteStatus
import cmk.gui.sites
import cmk.gui.config as config
import cmk.gui.watolib as watolib
import cmk.gui.forms as forms
import cmk.gui.log as log
from cmk.gui.utils.html import HTML
from cmk.gui.table import table_element
from cmk.gui.valuespec import (
    Dictionary,
    ID,
    Integer,
    FixedValue,
    TextUnicode,
    TextAscii,
    Checkbox,
    Tuple,
    Alternative,
    DropdownChoice,
    MonitoredHostname,
    HTTPUrl,
)

from cmk.gui.pages import page_registry, AjaxPage
from cmk.gui.plugins.wato.utils import mode_registry, sort_sites
from cmk.gui.plugins.watolib.utils import config_variable_registry
from cmk.gui.plugins.wato.utils.base_modes import WatoMode, ActionResult, redirect, mode_url
from cmk.gui.plugins.wato.utils.html_elements import wato_html_head
from cmk.gui.utils.flashed_messages import flash
from cmk.gui.i18n import _
from cmk.gui.globals import html, request
from cmk.gui.exceptions import MKUserError, MKGeneralException, FinalizeRequest
from cmk.gui.log import logger
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.page_menu import (
    PageMenu,
    PageMenuDropdown,
    PageMenuTopic,
    PageMenuEntry,
    make_simple_link,
    make_simple_form_page_menu,
)

from cmk.gui.watolib.sites import is_livestatus_encrypted
from cmk.gui.watolib.activate_changes import clear_site_replication_status
from cmk.gui.wato.pages.global_settings import ABCGlobalSettingsMode, ABCEditGlobalSettingMode

from cmk.gui.utils.urls import makeuri_contextless, make_confirm_link


def _site_globals_editable(site_id, site):
    # Site is a remote site of another site. Allow to edit probably pushed site
    # specific globals when remote WATO is enabled
    if watolib.is_wato_slave_site():
        return True

    # Local site: Don't enable site specific locals when no remote sites configured
    if not config.has_wato_slave_sites():
        return False

    return site["replication"] or config.site_is_local(site_id)


def _get_demo_message():
    return _("With the Checkmk Enterprise Free Edition you can create a distributed setup "
             "with two sites, one central and one remote site. In case you want to test "
             "more complex distributed setups, please "
             "<a href=\"mailto:info@checkmk.com\">contact us</a>.")


@mode_registry.register
class ModeEditSite(WatoMode):
    @classmethod
    def name(cls):
        return "edit_site"

    @classmethod
    def permissions(cls):
        return ["sites"]

    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeDistributedMonitoring

    # pylint does not understand this overloading
    @overload
    @classmethod
    def mode_url(cls, *, site: str) -> str:  # pylint: disable=arguments-differ
        ...

    @overload
    @classmethod
    def mode_url(cls, **kwargs: str) -> str:
        ...

    @classmethod
    def mode_url(cls, **kwargs: str) -> str:
        return super().mode_url(**kwargs)

    def __init__(self):
        super().__init__()
        self._site_mgmt = watolib.SiteManagementFactory().factory()

        self._site_id = html.request.get_ascii_input("site")
        self._clone_id = html.request.get_ascii_input("clone")
        self._new = self._site_id is None

        if cmk_version.is_demo() and self._new:
            num_sites = len(self._site_mgmt.load_sites())
            if num_sites > 1:
                raise MKUserError(None, _get_demo_message())

        configured_sites = self._site_mgmt.load_sites()

        if self._clone_id:
            try:
                self._site = configured_sites[self._clone_id]
            except KeyError:
                raise MKUserError(None, _("The requested site does not exist"))

        elif self._new:
            self._site = {
                "replicate_mkps": True,
                "replicate_ec": True,
                "socket": ("tcp", {
                    "address": ("", 6557),
                    "tls": ("encrypted", {
                        "verify": True,
                    })
                }),
                "timeout": 5,
                "disable_wato": True,
                "user_login": True,
                "replication": None,
            }

            if watolib.ConfigDomainLiveproxy.enabled():
                self._site.update({
                    "proxy": {},
                    "timeout": 2,
                })

        else:
            assert self._site_id is not None
            try:
                self._site = configured_sites[self._site_id]
            except KeyError:
                raise MKUserError(None, _("The requested site does not exist"))

    def title(self):
        if self._new:
            return _("Add site connection")
        return _("Edit site connection %s") % self._site_id

    def _breadcrumb_url(self) -> str:
        assert self._site_id is not None
        return self.mode_url(site=self._site_id)

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        menu = make_simple_form_page_menu(breadcrumb, form_name="site", button_name="save")
        if not self._new and isinstance(self._site_id, str):
            menu.dropdowns.insert(
                1, _page_menu_dropdown_site_details(self._site_id, self._site, self.name()))
        return menu

    def action(self) -> ActionResult:
        if not html.check_transaction():
            return redirect(mode_url("sites"))

        vs = self._valuespec()
        site_spec = vs.from_html_vars("site")
        vs.validate_value(site_spec, "site")

        # Extract the ID. It is not persisted in the site value
        if self._new:
            self._site_id = site_spec["id"]
        del site_spec["id"]
        assert self._site_id is not None

        configured_sites = self._site_mgmt.load_sites()

        # Take over all unknown elements from existing site specs, like for
        # example, the replication secret
        for key, value in configured_sites.get(self._site_id, {}).items():
            site_spec.setdefault(key, value)

        self._site_mgmt.validate_configuration(self._site_id, site_spec, configured_sites)

        self._site = configured_sites[self._site_id] = site_spec
        self._site_mgmt.save_sites(configured_sites)

        if self._new:
            msg = _("Created new connection to site %s") % self._site_id
        else:
            msg = _("Modified site connection %s") % self._site_id

        # Don't know exactly what have been changed, so better issue a change
        # affecting all domains
        watolib.add_change("edit-sites",
                           msg,
                           sites=[self._site_id],
                           domains=watolib.ABCConfigDomain.enabled_domains())

        # In case a site is not being replicated anymore, confirm all changes for this site!
        if not site_spec["replication"]:
            clear_site_replication_status(self._site_id)

        if self._site_id != config.omd_site():
            # On central site issue a change only affecting the GUI
            watolib.add_change("edit-sites",
                               msg,
                               sites=[config.omd_site()],
                               domains=[watolib.ConfigDomainGUI])

        flash(msg)
        return redirect(mode_url("sites"))

    def page(self):
        html.begin_form("site")

        self._valuespec().render_input("site", self._site)

        forms.end()
        html.hidden_fields()
        html.end_form()

    def _valuespec(self):
        basic_elements = self._basic_elements()
        livestatus_elements = self._livestatus_elements()
        replication_elements = self._replication_elements()

        return Dictionary(
            elements=basic_elements + livestatus_elements + replication_elements,
            headers=[
                (_("Basic settings"), [key for key, _vs in basic_elements]),
                (_("Status connection"), [key for key, _vs in livestatus_elements]),
                (_("Configuration connection"), [key for key, _vs in replication_elements]),
            ],
            render="form",
            form_narrow=True,
            optional_keys=[],
        )

    def _basic_elements(self):
        if self._new:
            vs_site_id = ID(
                title=_("Site ID"),
                size=60,
                allow_empty=False,
                help=_("The site ID must be identical (case sensitive) with "
                       "the instance's exact name."),
                validate=self._validate_site_id,
            )
        else:
            vs_site_id = FixedValue(
                self._site_id,
                title=_("Site ID"),
            )

        return [
            ("id", vs_site_id),
            ("alias",
             TextUnicode(
                 title=_("Alias"),
                 size=60,
                 help=_("An alias or description of the site."),
                 allow_empty=False,
             )),
        ]

    def _validate_site_id(self, value, varprefix):
        if value in self._site_mgmt.load_sites():
            raise MKUserError("id", _("This id is already being used by another connection."))

    def _livestatus_elements(self):
        proxy_docu_url = "https://checkmk.com/checkmk_multisite_modproxy.html"
        status_host_docu_url = "https://checkmk.com/checkmk_multisite_statushost.html"
        site_choices = [
            (sk, si.get("alias", sk)) for (sk, si) in self._site_mgmt.load_sites().items()
        ]

        return [
            ("socket", self._site_mgmt.connection_method_valuespec()),
            ("proxy", self._site_mgmt.livestatus_proxy_valuespec()),
            ("timeout",
             Integer(
                 title=_("Connect timeout"),
                 size=2,
                 unit=_("Seconds"),
                 minvalue=0,
                 help=_("This sets the time that the GUI waits for a connection "
                        "to the site to be established before the site is "
                        "considered to be unreachable. It is highly recommended to set a value "
                        "as low as possible here because this setting directly affects the GUI "
                        "response time when the destionation is not reachable. When using the "
                        "Livestatus Proxy Daemon the GUI connects to the local proxy, in this "
                        "situation a lower value, like 2 seconds is recommended."),
             )),
            ("persist",
             Checkbox(
                 title=_("Persistent Connection"),
                 label=_("Use persistent connections"),
                 help=
                 _("If you enable persistent connections then Multisite will try to keep open "
                   "the connection to the remote sites. This brings a great speed up in high-latency "
                   "situations but locks a number of threads in the Livestatus module of the target site."
                  ),
             )),
            ("url_prefix",
             TextAscii(
                 title=_("URL prefix"),
                 size=60,
                 help=
                 _("The URL prefix will be prepended to links of addons like NagVis "
                   "when a link to such applications points to a host or "
                   "service on that site. You can either use an absolute URL prefix like <tt>http://some.host/mysite/</tt> "
                   "or a relative URL like <tt>/mysite/</tt>. When using relative prefixes you needed a mod_proxy "
                   "configuration in your local system apache that proxies such URLs to the according remote site. "
                   "Please refer to the <a target=_blank href='%s'>online documentation</a> for details. "
                   "The prefix should end with a slash. Omit the <tt>/nagvis/</tt> from the prefix."
                  ) % proxy_docu_url,
                 allow_empty=True,
             )),
            ("status_host",
             Alternative(
                 title=_("Status host"),
                 elements=[
                     FixedValue(None, title=_("No status host"), totext=""),
                     Tuple(
                         title=_("Use the following status host"),
                         orientation="horizontal",
                         elements=[
                             DropdownChoice(
                                 title=_("Site:"),
                                 choices=site_choices,
                                 sorted=True,
                             ),
                             self._vs_host(),
                         ],
                     ),
                 ],
                 help=
                 _("By specifying a status host for each non-local connection "
                   "you prevent Multisite from running into timeouts when remote sites do not respond. "
                   "You need to add the remote monitoring servers as hosts into your local monitoring "
                   "site and use their host state as a reachability state of the remote site. Please "
                   "refer to the <a target=_blank href='%s'>online documentation</a> for details.")
                 % status_host_docu_url,
             )),
            ("disabled",
             Checkbox(
                 title=_("Disable in status GUI"),
                 label=_("Temporarily disable this connection"),
                 help=_(
                     "If you disable a connection, then no data of this site will be shown in the status GUI. "
                     "The replication is not affected by this, however."),
             )),
        ]

    def _vs_host(self):
        return MonitoredHostname(
            title=_("Host:"),
            allow_empty=False,
        )

    def _replication_elements(self):
        return [
            ("replication",
             DropdownChoice(
                 title=_("Enable replication"),
                 choices=[
                     (None, _("No replication with this site")),
                     ("slave", _("Push configuration to this site")),
                 ],
                 help=_("WATO replication allows you to manage several monitoring sites with a "
                        "logically centralized WATO. Remote sites receive their configuration "
                        "from the central sites. <br><br>Note: Remote sites "
                        "do not need any replication configuration. They will be remote-controlled "
                        "by the central sites."),
             )),
            ("multisiteurl",
             HTTPUrl(
                 title=_("URL of remote site"),
                 help=_(
                     "URL of the remote Check_MK including <tt>/check_mk/</tt>. "
                     "This URL is in many cases the same as the URL-Prefix but with <tt>check_mk/</tt> "
                     "appended, but it must always be an absolute URL. Please note, that "
                     "that URL will be fetched by the Apache server of the local "
                     "site itself, whilst the URL-Prefix is used by your local Browser."),
                 allow_empty=True,
             )),
            ("disable_wato",
             Checkbox(
                 title=_("Disable remote configuration"),
                 label=_('Disable configuration via WATO on this site'),
                 help=_(
                     'It is a good idea to disable access to WATO completely on the remote site. '
                     'Otherwise a user who does not now about the replication could make local '
                     'changes that are overridden at the next configuration activation.'),
             )),
            ("insecure",
             Checkbox(
                 title=_("Ignore TLS errors"),
                 label=_('Ignore SSL certificate errors'),
                 help=_('This might be needed to make the synchronization accept problems with '
                        'SSL certificates when using an SSL secured connection.'),
             )),
            ("user_login",
             Checkbox(
                 title=_('Direct login to Web GUI allowed'),
                 label=_('Users are allowed to directly login into the Web GUI of this site'),
                 help=_(
                     'When enabled, this site is marked for synchronisation every time a Web GUI '
                     'related option is changed and users are allowed to login '
                     'to the Web GUI of this site.'),
             )),
            ("user_sync", self._site_mgmt.user_sync_valuespec(self._site_id)),
            ("replicate_ec",
             Checkbox(
                 title=_("Replicate Event Console config"),
                 label=_("Replicate Event Console configuration to this site"),
                 help=
                 _("This option enables the distribution of global settings and rules of the Event Console "
                   "to the remote site. Any change in the local Event Console settings will mark the site "
                   "as <i>need sync</i>. A synchronization will automatically reload the Event Console of "
                   "the remote site."),
             )),
            ("replicate_mkps",
             Checkbox(
                 title=_("Replicate extensions"),
                 label=_("Replicate extensions (MKPs and files in <tt>~/local/</tt>)"),
                 help=
                 _("If you enable the replication of MKPs then during each <i>Activate Changes</i> MKPs "
                   "that are installed on your central site and all other files below the <tt>~/local/</tt> "
                   "directory will be also transferred to the remote site. Note: <b>all other MKPs and files "
                   "below <tt>~/local/</tt> on the remote site will be removed</b>."),
             )),
        ]


@mode_registry.register
class ModeDistributedMonitoring(WatoMode):
    @classmethod
    def name(cls):
        return "sites"

    @classmethod
    def permissions(cls):
        return ["sites"]

    def __init__(self):
        super().__init__()
        self._site_mgmt = watolib.SiteManagementFactory().factory()

    def title(self):
        return _("Distributed Monitoring")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="connections",
                    title=_("Connections"),
                    topics=[
                        PageMenuTopic(
                            title=_("Connections"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Add connection"),
                                    icon_name="new",
                                    item=make_simple_link(
                                        makeuri_contextless(request, [("mode", "edit_site")]),),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                            ],
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
        )

    def action(self) -> ActionResult:
        delete_id = html.request.get_ascii_input("_delete")
        if delete_id and html.check_transaction():
            self._action_delete(delete_id)

        logout_id = html.request.get_ascii_input("_logout")
        if logout_id:
            return self._action_logout(logout_id)

        login_id = html.request.get_ascii_input("_login")
        if login_id:
            return self._action_login(login_id)
        return None

    # Mypy wants the explicit return, pylint does not like it.
    def _action_delete(self, delete_id) -> ActionResult:  # pylint: disable=useless-return
        # TODO: Can we delete this ancient code? The site attribute is always available
        # these days and the following code does not seem to have any effect.
        configured_sites = self._site_mgmt.load_sites()
        # The last connection can always be deleted. In that case we
        # fall back to non-distributed-WATO and the site attribute
        # will be removed.
        test_sites = dict(configured_sites.items())
        del test_sites[delete_id]

        # Prevent deletion of the local site. This does not make sense, even on
        # standalone sites or distributed remote sites.
        if delete_id == config.omd_site():
            raise MKUserError(None, _("You can not delete the connection to the local site."))

        # Make sure that site is not being used by hosts and folders
        if delete_id in watolib.Folder.root_folder().all_site_ids():
            search_url = html.makeactionuri_contextless([
                ("host_search_change_site", "on"),
                ("host_search_site", DropdownChoice.option_id(delete_id)),
                ("host_search", "1"),
                ("folder", ""),
                ("mode", "search"),
                ("filled_in", "edit_host"),
            ])
            raise MKUserError(
                None,
                _("You cannot delete this connection. It has folders/hosts "
                  "assigned to it. You can use the <a href=\"%s\">host "
                  "search</a> to get a list of the hosts.") % search_url)

        self._site_mgmt.delete_site(delete_id)
        return redirect(mode_url("sites"))

    def _action_logout(self, logout_id: str) -> ActionResult:
        configured_sites = self._site_mgmt.load_sites()
        site = configured_sites[logout_id]
        if "secret" in site:
            del site["secret"]
        self._site_mgmt.save_sites(configured_sites)
        watolib.add_change("edit-site",
                           _("Logged out of remote site %s") % html.render_tt(site["alias"]),
                           domains=[watolib.ConfigDomainGUI],
                           sites=[watolib.default_site()])
        flash(_("Logged out."))
        return redirect(mode_url("sites"))

    def _action_login(self, login_id: str) -> ActionResult:
        configured_sites = self._site_mgmt.load_sites()
        if html.request.get_ascii_input("_abort"):
            return redirect(mode_url("sites"))

        if not html.check_transaction():
            return None

        site = configured_sites[login_id]
        error = None
        # Fetch name/password of admin account
        if html.request.has_var("_name"):
            name = html.request.get_unicode_input_mandatory("_name", "").strip()
            passwd = html.request.get_ascii_input_mandatory("_passwd", "").strip()
            try:
                if not html.get_checkbox("_confirm"):
                    raise MKUserError(
                        "_confirm",
                        _("You need to confirm that you want to "
                          "overwrite the remote site configuration."))

                secret = watolib.do_site_login(login_id, name, passwd)

                site["secret"] = secret
                self._site_mgmt.save_sites(configured_sites)
                message = _("Successfully logged into remote site %s.") % html.render_tt(
                    site["alias"])
                watolib.log_audit(None, "edit-site", message)
                flash(message)
                return None

            except watolib.MKAutomationException as e:
                error = _("Cannot connect to remote site: %s") % e

            except MKUserError as e:
                html.add_user_error(e.varname, e)
                error = "%s" % e

            except Exception as e:
                logger.exception("error logging in")
                if config.debug:
                    raise
                error = (_("Internal error: %s\n%s") % (e, traceback.format_exc())).replace(
                    "\n", "\n<br>")
                html.add_user_error("_name", error)

        wato_html_head(title=_("Login into site \"%s\"") % site["alias"],
                       breadcrumb=self.breadcrumb())
        if error:
            html.show_error(error)

        html.p(
            _("For the initial login into the remote site %s "
              "we need once your administration login for the Multsite "
              "GUI on that site. Your credentials will only be used for "
              "the initial handshake and not be stored. If the login is "
              "successful then both side will exchange a login secret "
              "which is used for the further remote calls.") % html.render_tt(site["alias"]))

        html.begin_form("login", method="POST")
        forms.header(_('Login credentials'))
        forms.section(_('Administrator name'))
        html.text_input("_name")
        html.set_focus("_name")
        forms.section(_('Administrator password'))
        html.password_input("_passwd")
        forms.section(_('Confirm overwrite'))
        html.checkbox("_confirm",
                      False,
                      label=_("Confirm overwrite of the remote site configuration"))
        forms.end()
        html.button("_do_login", _("Login"))
        html.button("_abort", _("Abort"))
        html.hidden_field("_login", login_id)
        html.hidden_fields()
        html.end_form()
        html.footer()
        return FinalizeRequest(code=200)

    def page(self):
        sites = sort_sites(self._site_mgmt.load_sites())

        if cmk_version.is_demo():
            html.show_message(_get_demo_message())

        html.div("", id_="message_container")
        with table_element(
                "sites",
                _("Connections"),
                empty_text=_(
                    "You have not configured any local or remotes sites. Multisite will "
                    "implicitely add the data of the local monitoring site. If you add remotes "
                    "sites, please do not forget to add your local monitoring site also, if "
                    "you want to display its data.")) as table:

            for site_id, site in sites:
                table.row()

                self._show_buttons(table, site_id, site)
                self._show_basic_settings(table, site_id, site)
                self._show_status_connection_config(table, site_id, site)
                self._show_status_connection_status(table, site_id, site)
                self._show_config_connection_config(table, site_id, site)
                self._show_config_connection_status(table, site_id, site)

        html.javascript("cmk.sites.fetch_site_status();")

    def _show_buttons(self, table, site_id, site):
        table.cell(_("Actions"), css="buttons")
        edit_url = watolib.folder_preserving_link([("mode", "edit_site"), ("site", site_id)])
        html.icon_button(edit_url, _("Properties"), "edit")

        clone_url = watolib.folder_preserving_link([("mode", "edit_site"), ("clone", site_id)])
        html.icon_button(clone_url, _("Clone this connection in order to create a new one"),
                         "clone")

        # Prevent deletion of the local site. This does not make sense, even on
        # standalone sites or distributed remote sites.
        if site_id == config.omd_site():
            html.empty_icon_button()
        else:
            delete_url = make_confirm_link(
                url=html.makeactionuri([("_delete", site_id)]),
                message=_("Do you really want to delete the connection to the site %s?") %
                html.render_tt(site_id))
            html.icon_button(delete_url, _("Delete"), "delete")

        if _site_globals_editable(site_id, site):
            globals_url = watolib.folder_preserving_link([("mode", "edit_site_globals"),
                                                          ("site", site_id)])

            has_site_globals = bool(site.get("globals"))
            title = _("Site specific global configuration")
            if has_site_globals:
                icon = "site_globals_modified"
                title += " (%s)" % (_("%d specific settings") % len(site.get("globals")))
            else:
                icon = "site_globals"

            html.icon_button(globals_url, title, icon)

    def _show_basic_settings(self, table, site_id, site):
        table.text_cell(_("ID"), site_id)
        table.text_cell(_("Alias"), site.get("alias", ""))

    def _show_status_connection_config(self, table, site_id, site):
        table.cell(_("Status connection"))
        vs_connection = self._site_mgmt.connection_method_valuespec()
        html.write(vs_connection.value_to_text(site["socket"]))

    def _show_status_connection_status(self, table, site_id, site):
        table.text_cell("")

        encrypted_url = watolib.folder_preserving_link([("mode", "site_livestatus_encryption"),
                                                        ("site", site_id)])
        html.icon_button(encrypted_url, _("Show details about livestatus encryption"), "encrypted")

        # The status is fetched asynchronously for all sites. Show a temporary loading icon.
        html.open_div(id_="livestatus_status_%s" % site_id, class_="connection_status")
        html.icon("reload",
                  _("Fetching livestatus status"),
                  class_=["reloading", "replication_status_loading"])
        html.close_div()

    def _show_config_connection_config(self, table, site_id, site):
        table.text_cell(_("Configuration connection"))
        if not site["replication"]:
            html.write_text(_("Not enabled"))
            return

        html.write_text(_("Enabled"))
        parts = []
        if site.get("replicate_ec"):
            parts.append("EC")
        if site.get("replicate_mkps"):
            parts.append("MKPs")
        if parts:
            html.write_text(" (%s)" % ", ".join(parts))

    def _show_config_connection_status(self, table, site_id, site):
        table.text_cell("")

        if site["replication"]:
            if site.get("secret"):
                logout_url = make_confirm_link(url=watolib.make_action_link([("mode", "sites"),
                                                                             ("_logout", site_id)]),
                                               message=_("Do you really want to log out of '%s'?") %
                                               html.render_tt(site["alias"]))
                html.icon_button(logout_url, _("Logout"), "autherr")
            else:
                login_url = watolib.make_action_link([("mode", "sites"), ("_login", site_id)])
                html.icon_button(login_url, _("Login"), "authok")

        html.open_div(id_="replication_status_%s" % site_id, class_="connection_status")
        if site.get("replication"):
            # The status is fetched asynchronously for all sites. Show a temporary loading icon.
            html.icon("reload",
                      _("Fetching replication status"),
                      class_=["reloading", "replication_status_loading"])
        html.close_div()


@page_registry.register_page("wato_ajax_fetch_site_status")
class ModeAjaxFetchSiteStatus(AjaxPage):
    """AJAX handler for asynchronous fetching of the site status"""
    def page(self):
        config.user.need_permission("wato.sites")

        site_states = {}

        sites = list(watolib.SiteManagementFactory().factory().load_sites().items())
        replication_sites = [e for e in sites if e[1]["replication"]]
        replication_status = ReplicationStatusFetcher().fetch(replication_sites)

        for site_id, site in sites:
            site_states[site_id] = {
                "livestatus": self._render_status_connection_status(site_id, site),
                "replication": self._render_configuration_connection_status(
                    site_id, site, replication_status),
            }
        return site_states

    def _render_configuration_connection_status(self, site_id, site, replication_status):
        """Check whether or not the replication connection is possible.

        This deals with these situations:
        - No connection possible
        - connection possible but site down
        - Not logged in
        - And of course: Everything is fine
        """
        if not site["replication"]:
            return ""

        status = replication_status[site_id]
        if status.success:
            icon = "success"
            msg = _("Online (Version: %s, Edition: %s)") % (status.response.version,
                                                            status.response.edition)
        else:
            icon = "failed"
            msg = "%s" % status.response

        return (html.render_icon(icon, title=msg) +
                html.render_span(msg, style="vertical-align:middle"))

    def _render_status_connection_status(self, site_id, site):
        site_status: SiteStatus = cmk.gui.sites.states().get(site_id, SiteStatus({}))
        if site.get("disabled", False) is True:
            status = status_msg = "disabled"
        else:
            status = status_msg = site_status.get("state", "unknown")

        if "exception" in site_status:
            message = "%s" % site_status["exception"]
        else:
            message = status_msg.title()

        icon = "success" if status == "online" else "failed"
        return (html.render_icon(icon, title=message) +
                html.render_span(message, style="vertical-align:middle"))


PingResult = NamedTuple("PingResult", [
    ("version", str),
    ("edition", str),
])

ReplicationStatus = NamedTuple("ReplicationStatus", [
    ("site_id", str),
    ("success", bool),
    ("response", Union[PingResult, Exception]),
])


class ReplicationStatusFetcher:
    """Helper class to retrieve the replication status of all relevant sites"""
    def __init__(self):
        super().__init__()
        self._logger = logger.getChild("replication-status")

    def fetch(self, sites: List[_Tuple[str, Dict]]) -> Dict[str, PingResult]:
        self._logger.debug("Fetching replication status for %d sites" % len(sites))
        results_by_site = {}

        # Results are fetched simultaneously from the remote sites
        result_queue = multiprocessing.JoinableQueue()  # type: ignore[var-annotated]

        processes = []
        for site_id, site in sites:
            process = multiprocessing.Process(target=self._fetch_for_site,
                                              args=(site_id, site, result_queue))
            process.start()
            processes.append((site_id, process))

        # Now collect the results from the queue until all processes are finished
        while any(p.is_alive() for site_id, p in processes):
            try:
                result = result_queue.get_nowait()
                result_queue.task_done()
                results_by_site[result.site_id] = result

            except queue.Empty:
                time.sleep(0.5)  # wait some time to prevent CPU hogs

            except Exception as e:
                logger.exception("error collecting replication results from site %s",
                                 result.site_id)
                html.show_error("%s: %s" % (result.site_id, e))

        self._logger.debug("Got results")
        return results_by_site

    def _fetch_for_site(self, site_id, site, result_queue):
        """Executes the tests on the site. This method is executed in a dedicated
        subprocess (One per site)"""
        self._logger.debug("[%s] Starting" % site_id)
        try:
            # TODO: Would be better to clean all open fds that are not needed, but we don't
            # know the FDs of the result_queue pipe. Can we find it out somehow?
            # Cleanup resources of the apache
            # TODO: Needs to be solved for analzye_configuration too
            #for x in range(3, 256):
            #    try:
            #        os.close(x)
            #    except OSError, e:
            #        if e.errno == errno.EBADF:
            #            pass
            #        else:
            #            raise

            # Reinitialize logging targets
            log.init_logging()  # NOTE: We run in a subprocess!

            result = ReplicationStatus(
                site_id=site_id,
                success=True,
                response=PingResult(**watolib.do_remote_automation(site, "ping", [], timeout=5)),
            )
            self._logger.debug("[%s] Finished" % site_id)
        except Exception as e:
            self._logger.debug("[%s] Failed" % site_id, exc_info=True)
            result = ReplicationStatus(
                site_id=site_id,
                success=False,
                response=e,
            )
        finally:
            result_queue.put(result)
            result_queue.close()
            result_queue.join_thread()
            result_queue.join()


@mode_registry.register
class ModeEditSiteGlobals(ABCGlobalSettingsMode):
    @classmethod
    def name(cls):
        return "edit_site_globals"

    @classmethod
    def permissions(cls):
        return ["sites"]

    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeEditSite

    # pylint does not understand this overloading
    @overload
    @classmethod
    def mode_url(cls, *, site: str) -> str:  # pylint: disable=arguments-differ
        ...

    @overload
    @classmethod
    def mode_url(cls, **kwargs: str) -> str:
        ...

    @classmethod
    def mode_url(cls, **kwargs: str) -> str:
        return super().mode_url(**kwargs)

    def __init__(self):
        super().__init__()
        self._site_id = html.request.get_ascii_input_mandatory("site")
        self._site_mgmt = watolib.SiteManagementFactory().factory()
        self._configured_sites = self._site_mgmt.load_sites()
        try:
            self._site = self._configured_sites[self._site_id]
        except KeyError:
            raise MKUserError("site", _("This site does not exist."))

        # 2. Values of global settings
        self._global_settings = watolib.load_configuration_settings()

        # 3. Site specific global settings

        if watolib.is_wato_slave_site():
            self._current_settings = watolib.load_configuration_settings(site_specific=True)
        else:
            self._current_settings = self._site.get("globals", {})

    def title(self):
        return _("Edit site specific global settings of %s") % self._site_id

    def _breadcrumb_url(self) -> str:
        return self.mode_url(site=self._site_id)

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(
            dropdowns=[
                _page_menu_dropdown_site_details(self._site_id, self._site, self.name()),
            ],
            breadcrumb=breadcrumb,
        )

    # TODO: Consolidate with ModeEditGlobals.action()
    def action(self) -> ActionResult:
        varname = html.request.get_ascii_input("_varname")
        action = html.request.get_ascii_input("_action")
        if not varname:
            return None

        config_variable = config_variable_registry[varname]()
        def_value = self._global_settings.get(varname, self._default_values[varname])

        if not html.check_transaction():
            return None

        if varname in self._current_settings:
            self._current_settings[varname] = not self._current_settings[varname]
        else:
            self._current_settings[varname] = not def_value

        msg = _("Changed site specific configuration variable %s to %s.") % \
            (varname, _("on") if self._current_settings[varname] else _("off"))

        self._site.setdefault("globals", {})[varname] = self._current_settings[varname]
        self._site_mgmt.save_sites(self._configured_sites, activate=False)

        watolib.add_change(
            "edit-configvar",
            msg,
            sites=[self._site_id],
            need_restart=config_variable.need_restart(),
        )

        if action == "_reset":
            flash(msg)
        return redirect(mode_url("edit_site_globals"))

    def _edit_mode(self):
        return "edit_site_configvar"

    def page(self):
        html.help(
            _("Here you can configure global settings, that should just be applied "
              "on that site. <b>Note</b>: this only makes sense if the site "
              "is part of a distributed setup."))

        if not watolib.is_wato_slave_site():
            if not config.has_wato_slave_sites():
                html.show_error(
                    _("You can not configure site specific global settings "
                      "in non distributed setups."))
                return

            if not self._site["replication"] and not config.site_is_local(self._site_id):
                html.show_error(
                    _("This site is not the central site nor a replication "
                      "remote site. You cannot configure specific settings for it."))
                return

        self._show_configuration_variables(self._groups(show_all=True))


@mode_registry.register
class ModeEditSiteGlobalSetting(ABCEditGlobalSettingMode):
    @classmethod
    def name(cls):
        return "edit_site_configvar"

    @classmethod
    def permissions(cls):
        return ["global"]

    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeEditSiteGlobals

    def _from_vars(self):
        super()._from_vars()
        self._site_id = html.request.var("site")
        if self._site_id:
            self._configured_sites = watolib.SiteManagementFactory().factory().load_sites()
            try:
                site = self._configured_sites[self._site_id]
            except KeyError:
                raise MKUserError("site", _("Invalid site"))

        self._current_settings = site.setdefault("globals", {})
        self._global_settings = watolib.load_configuration_settings()

    def title(self):
        return _("Site-specific global configuration for %s") % self._site_id

    def _affected_sites(self):
        return [self._site_id]

    def _save(self):
        watolib.SiteManagementFactory().factory().save_sites(self._configured_sites, activate=False)
        if self._site_id == config.omd_site():
            watolib.save_site_global_settings(self._current_settings)

    def _show_global_setting(self):
        forms.section(_("Global setting"))
        html.write_html(HTML(self._valuespec.value_to_text(self._global_settings[self._varname])))


ChainVerifyResult = NamedTuple("ChainVerifyResult", [
    ("cert_pem", str),
    ("error_number", int),
    ("error_depth", int),
    ("error_message", str),
    ("is_valid", bool),
])

CertificateDetails = NamedTuple("CertificateDetails", [
    ("issued_to", str),
    ("issued_by", str),
    ("valid_from", str),
    ("valid_till", str),
    ("signature_algorithm", str),
    ("digest_sha256", str),
    ("serial_number", int),
    ("is_ca", bool),
    ("verify_result", ChainVerifyResult),
])


@mode_registry.register
class ModeSiteLivestatusEncryption(WatoMode):
    @classmethod
    def name(cls):
        return "site_livestatus_encryption"

    @classmethod
    def permissions(cls):
        return ["sites"]

    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeEditSite

    def __init__(self):
        super().__init__()
        self._site_id = html.request.get_ascii_input_mandatory("site")
        self._site_mgmt = watolib.SiteManagementFactory().factory()
        self._configured_sites = self._site_mgmt.load_sites()
        try:
            self._site = self._configured_sites[self._site_id]
        except KeyError:
            raise MKUserError("site", _("This site does not exist."))

    def title(self):
        return _("Livestatus encryption of %s") % self._site_id

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(
            dropdowns=[
                _page_menu_dropdown_site_details(self._site_id, self._site, self.name()),
            ],
            breadcrumb=breadcrumb,
        )

    def action(self) -> ActionResult:
        if not html.check_transaction():
            return None

        action = html.request.get_ascii_input_mandatory("_action")
        if action != "trust":
            return None

        digest_sha256 = html.request.get_ascii_input("_digest")

        try:
            cert_details = self._fetch_certificate_details()
        except Exception as e:
            logger.exception("Failed to fetch peer certificate")
            html.show_error(_("Failed to fetch peer certificate (%s)") % e)
            return None

        cert_pem = None
        for cert_detail in cert_details:
            if cert_detail.digest_sha256 == digest_sha256:
                cert_pem = cert_detail.verify_result.cert_pem

        if cert_pem is None:
            raise MKGeneralException(_("Failed to find matching certificate in chain"))

        config_variable = config_variable_registry["trusted_certificate_authorities"]()

        global_settings = watolib.load_configuration_settings()
        trusted = global_settings.get(
            "trusted_certificate_authorities",
            watolib.ABCConfigDomain.get_all_default_globals()["trusted_certificate_authorities"])
        trusted_cas = trusted.setdefault("trusted_cas", [])

        if cert_pem in trusted_cas:
            raise MKUserError(
                None,
                _("The CA is already a <a href=\"%s\">trusted CA</a>.") %
                "wato.py?mode=edit_configvar&varname=trusted_certificate_authorities")

        trusted_cas.append(cert_pem)
        global_settings["trusted_certificate_authorities"] = trusted

        watolib.add_change("edit-configvar",
                           _("Added CA with fingerprint %s to trusted certificate authorities") %
                           digest_sha256,
                           domains=[config_variable.domain()],
                           need_restart=config_variable.need_restart())
        watolib.save_global_settings(global_settings)

        flash(_("Added CA with fingerprint %s to trusted certificate authorities") % digest_sha256)
        return None

    def page(self):
        if not is_livestatus_encrypted(self._site):
            html.show_message(
                _("The livestatus connection to this site configured not to be encrypted."))
            return

        if self._site["socket"][1]["tls"][1]["verify"] is False:
            html.show_warning(
                _("Encrypted connections to this site are made without "
                  "certificate verification."))

        try:
            cert_details = self._fetch_certificate_details()
        except Exception as e:
            logger.exception("Failed to fetch peer certificate")
            html.show_error(_("Failed to fetch peer certificate (%s)") % e)
            return

        html.h3(_("Certificate details"))
        html.open_table(class_=["data", "headerleft"])

        server_cert = cert_details[0]
        for title, css_class, value in [
            (_("Issued to"), None, server_cert.issued_to),
            (_("Issued by"), None, server_cert.issued_by),
            (_("Valid from"), None, server_cert.valid_from),
            (_("Valid till"), None, server_cert.valid_till),
            (_("Signature algorithm"), None, server_cert.signature_algorithm),
            (_("Fingerprint (SHA256)"), None, server_cert.digest_sha256),
            (_("Serial number"), None, server_cert.serial_number),
            (_("Trusted"), self._cert_trusted_css_class(server_cert),
             self._render_cert_trusted(server_cert)),
        ]:
            html.open_tr()
            html.th(title)
            html.td(value, class_=css_class)
            html.close_tr()
        html.close_table()

        with table_element("certificate_chain", _("Certificate chain")) as table:
            for cert_detail in reversed(cert_details[1:]):
                table.row()
                table.cell(_("Actions"), css="buttons")
                if cert_detail.is_ca:
                    url = html.makeactionuri([
                        ("_action", "trust"),
                        ("_digest", cert_detail.digest_sha256),
                    ])
                    html.icon_button(url=url, title=_("Add to trusted CAs"), icon="trust")
                table.text_cell(_("Issued to"), cert_detail.issued_to)
                table.text_cell(_("Issued by"), cert_detail.issued_by)
                table.text_cell(_("Is CA"), _("Yes") if cert_detail.is_ca else _("No"))
                table.text_cell(_("Fingerprint"), cert_detail.digest_sha256)
                table.text_cell(_("Valid till"), cert_detail.valid_till)
                table.text_cell(_("Trusted"),
                                self._render_cert_trusted(cert_detail),
                                css=self._cert_trusted_css_class(cert_detail))

    def _render_cert_trusted(self, cert):
        if cert.verify_result.is_valid:
            return _("Yes")

        return _("No (Error: %s, Code: %d, Depth: %d)") % (cert.verify_result.error_message,
                                                           cert.verify_result.error_number,
                                                           cert.verify_result.error_depth)

    def _cert_trusted_css_class(self, cert):
        return "state state0" if cert.verify_result.is_valid else "state state2"

    def _fetch_certificate_details(self) -> List[CertificateDetails]:
        """Creates a list of certificate details for the chain certs"""
        verify_chain_results = self._fetch_certificate_chain_verify_results()
        if not verify_chain_results:
            raise MKGeneralException(_("Failed to fetch the certificate chain"))

        def get_name(name_obj):
            return name_obj.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value

        cert_details = []
        for result in verify_chain_results:
            # use cryptography module over OpenSSL because it is easier to do the x509 parsing
            crypto_cert = x509.load_pem_x509_certificate(ensure_binary(result.cert_pem),
                                                         default_backend())

            cert_details.append(
                CertificateDetails(
                    issued_to=get_name(crypto_cert.subject),
                    issued_by=get_name(crypto_cert.issuer),
                    valid_from=str(crypto_cert.not_valid_before),
                    valid_till=str(crypto_cert.not_valid_after),
                    signature_algorithm=crypto_cert.signature_hash_algorithm.name,
                    digest_sha256=ensure_str(
                        binascii.hexlify(crypto_cert.fingerprint(hashes.SHA256()))),
                    serial_number=crypto_cert.serial_number,
                    is_ca=self._is_ca_certificate(crypto_cert),
                    verify_result=result,
                ))

        return cert_details

    def _is_ca_certificate(self, crypto_cert: 'SSL.Certificate') -> bool:
        try:
            key_usage = crypto_cert.extensions.get_extension_for_oid(ExtensionOID.KEY_USAGE)
            use_key_for_signing = key_usage.value.key_cert_sign is True
        except x509.extensions.ExtensionNotFound:
            use_key_for_signing = False

        try:
            basic_constraints = crypto_cert.extensions.get_extension_for_oid(
                ExtensionOID.BASIC_CONSTRAINTS)
            is_ca = basic_constraints.value.ca is True
        except x509.extensions.ExtensionNotFound:
            is_ca = False

        return is_ca and use_key_for_signing

    def _fetch_certificate_chain_verify_results(self) -> List[ChainVerifyResult]:
        """Opens a SSL connection and performs a handshake to get the certificate chain"""

        ctx = SSL.Context(SSL.SSLv23_METHOD)
        # On this page we don't want to fail because of invalid certificates,
        # but SSL.VERIFY_PEER must be set to trigger the verify_cb. This callback
        # will then accept any certificate offered.
        #ctx.set_verify(SSL.VERIFY_PEER, verify_cb)
        ctx.load_verify_locations(cmk.utils.paths.omd_root + "/var/ssl/ca-certificates.crt")

        family_spec, address_spec = self._site["socket"]
        address_family = socket.AF_INET if family_spec == "tcp" else socket.AF_INET6
        with contextlib.closing(
                SSL.Connection(ctx, socket.socket(address_family, socket.SOCK_STREAM))) as sock:

            # pylint does not get the object type of sock right
            sock.connect(address_spec["address"])
            sock.do_handshake()
            certificate_chain = sock.get_peer_cert_chain()

            return self._verify_certificate_chain(sock, certificate_chain)

    def _verify_certificate_chain(self, connection: SSL.Connection,
                                  certificate_chain: List[crypto.X509]) -> List[ChainVerifyResult]:
        verify_chain_results = []

        # Used to record all certificates and verification results for later displaying
        for cert in certificate_chain:
            # This is mainly done to get the textual error message without accessing internals of the SSL modules
            error_number, error_depth, error_message = 0, 0, ""
            try:
                x509_store = connection.get_context().get_cert_store()
                x509_store_context = crypto.X509StoreContext(x509_store, cert)
                x509_store_context.verify_certificate()
            except crypto.X509StoreContextError as e:
                error_number, error_depth, error_message = e.args[0]

            verify_chain_results.append(
                ChainVerifyResult(
                    cert_pem=crypto.dump_certificate(crypto.FILETYPE_PEM, cert),
                    error_number=error_number,
                    error_depth=error_depth,
                    error_message=error_message,
                    is_valid=error_number == 0,
                ))

        return verify_chain_results


def _page_menu_dropdown_site_details(site_id: str, site: Dict,
                                     current_mode: str) -> PageMenuDropdown:
    return PageMenuDropdown(
        name="connections",
        title=_("Connections"),
        topics=[
            PageMenuTopic(
                title=_("This connection"),
                entries=list(_page_menu_entries_site_details(site_id, site, current_mode)),
            ),
        ],
    )


def _page_menu_entries_site_details(site_id: str, site: Dict,
                                    current_mode: str) -> Iterator[PageMenuEntry]:
    if current_mode != "edit_site_globals" and _site_globals_editable(site_id, site):
        yield PageMenuEntry(
            title=_("Global settings"),
            icon_name="configuration",
            item=make_simple_link(
                makeuri_contextless(request, [("mode", "edit_site_globals"), ("site", site_id)]),),
        )

    if current_mode != "edit_site":
        yield PageMenuEntry(
            title=_("Edit connection"),
            icon_name="edit",
            item=make_simple_link(
                makeuri_contextless(request, [("mode", "edit_site"), ("site", site_id)]),),
        )

    if current_mode != "site_livestatus_encryption":
        yield PageMenuEntry(
            title=_("Status encryption"),
            icon_name="encrypted",
            item=make_simple_link(
                makeuri_contextless(
                    request,
                    [("mode", "site_livestatus_encryption"), ("site", site_id)],
                )),
        )
