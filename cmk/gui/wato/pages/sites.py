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
"""Mode for managing sites"""

import re
import traceback

import cmk
import cmk.gui.config as config
import cmk.gui.watolib as watolib
import cmk.gui.userdb as userdb
import cmk.gui.forms as forms
from cmk.gui.table import table_element
from cmk.gui.valuespec import (
    MonitoredHostname,)

from cmk.gui.plugins.wato.utils import mode_registry, sort_sites
from cmk.gui.plugins.wato.utils.base_modes import WatoMode
from cmk.gui.plugins.wato.utils.html_elements import wato_html_head, wato_confirm
from cmk.gui.plugins.wato.utils.context_buttons import global_buttons
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.exceptions import MKUserError
from cmk.gui.log import logger

from cmk.gui.watolib.activate_changes import clear_site_replication_status
from cmk.gui.wato.pages.global_settings import GlobalSettingsMode, is_a_checkbox


# TODO: Rename to SitesMode()
class ModeSites(WatoMode):
    def __init__(self):
        super(ModeSites, self).__init__()
        self._site_mgmt = watolib.SiteManagementFactory().factory()

    def buttons(self):
        global_buttons()


@mode_registry.register
class ModeEditSite(ModeSites):
    @classmethod
    def name(cls):
        return "edit_site"

    @classmethod
    def permissions(cls):
        return ["sites"]

    def __init__(self):
        super(ModeEditSite, self).__init__()
        self._from_html_vars()

        self._new = self._site_id is None
        self._new_site = {}
        configured_sites = self._site_mgmt.load_sites()

        if self._clone_id:
            self._site = configured_sites[self._clone_id]

        elif self._new:
            self._site = {"replicate_mkps": True}

        else:
            self._site = configured_sites.get(self._site_id, {})

    def _from_html_vars(self):
        self._site_id = html.request.var("edit")
        self._clone_id = html.request.var("clone")
        self._id = html.request.var("id")
        self._url_prefix = html.request.var("url_prefix", "").strip()
        self._timeout = html.request.var("timeout", "").strip()
        self._sh_site = html.request.var("sh_site")

        self._sh_host = self._vs_host().from_html_vars("sh_host")
        self._vs_host().validate_value(self._sh_host, "sh_Host")

        self._repl = html.request.var("replication")
        self._multisiteurl = html.request.var("multisiteurl", "").strip()

    def title(self):
        if self._new:
            return _("Create new site connection")
        return _("Edit site connection %s") % self._site_id

    def buttons(self):
        super(ModeEditSite, self).buttons()
        html.context_button(
            _("All Sites"), watolib.folder_preserving_link([("mode", "sites")]), "back")
        if not self._new and self._site.get("replication"):
            html.context_button(
                _("Site-Globals"),
                watolib.folder_preserving_link([("mode", "edit_site_globals"),
                                                ("site", self._site_id)]), "configuration")

    def action(self):
        if not html.check_transaction():
            return "sites"

        if self._new:
            self._id = self._id.strip()
        else:
            self._id = self._site_id

        configured_sites = self._site_mgmt.load_sites()
        if self._new and self._id in configured_sites:
            raise MKUserError("id", _("This id is already being used by another connection."))

        if not re.match("^[-a-z0-9A-Z_]+$", self._id):
            raise MKUserError(
                "id", _("The site id must consist only of letters, digit and the underscore."))

        detail_msg = self._set_site_attributes()
        configured_sites[self._id] = self._new_site
        self._site_mgmt.save_sites(configured_sites)

        if self._new:
            msg = _("Created new connection to site %s") % html.render_tt(self._id)
        else:
            msg = _("Modified site connection %s") % html.render_tt(self._id)

        # Don't know exactly what have been changed, so better issue a change
        # affecting all domains
        watolib.add_change(
            "edit-sites", msg, sites=[self._id], domains=watolib.ConfigDomain.enabled_domains())

        # In case a site is not being replicated anymore, confirm all changes for this site!
        if not self._repl:
            clear_site_replication_status(self._id)

        if self._id != config.omd_site():
            # On central site issue a change only affecting the GUI
            watolib.add_change(
                "edit-sites", msg, sites=[config.omd_site()], domains=[watolib.ConfigDomainGUI])

        return "sites", detail_msg

    def _set_site_attributes(self):
        # Save copy of old site for later
        configured_sites = self._site_mgmt.load_sites()
        if not self._new:
            old_site = configured_sites[self._site_id]

        self._new_site = {}
        self._new_site["alias"] = html.get_unicode_input("alias", "").strip()
        if self._url_prefix:
            self._new_site["url_prefix"] = self._url_prefix
        self._new_site["disabled"] = html.get_checkbox("disabled")

        # Connection
        vs_connection = self._site_mgmt.connection_method_valuespec()
        method = vs_connection.from_html_vars("method")
        vs_connection.validate_value(method, "method")
        self._new_site["socket"] = method

        # Timeout
        if self._timeout != "":
            try:
                self._new_site["timeout"] = int(self._timeout)
            except ValueError:
                raise MKUserError(
                    "timeout",
                    _("The timeout %s is not a valid integer number.") % self._timeout)

        # Persist
        self._new_site["persist"] = html.get_checkbox("persist")

        # Status host
        if self._sh_site:
            self._new_site["status_host"] = (self._sh_site, self._sh_host)
        else:
            self._new_site["status_host"] = None

        # Replication
        if self._repl == "none":
            self._repl = None
        self._new_site["replication"] = self._repl
        self._new_site["multisiteurl"] = self._multisiteurl

        # Save Multisite-URL even if replication is turned off. That way that
        # setting is not lost if replication is turned off for a while.

        # Disabling of WATO
        self._new_site["disable_wato"] = html.get_checkbox("disable_wato")

        # Handle the insecure replication flag
        self._new_site["insecure"] = html.get_checkbox("insecure")

        # Allow direct user login
        self._new_site["user_login"] = html.get_checkbox("user_login")

        # User synchronization
        user_sync = self._site_mgmt.user_sync_valuespec().from_html_vars("user_sync")
        self._new_site["user_sync"] = user_sync

        # Event Console Replication
        self._new_site["replicate_ec"] = html.get_checkbox("replicate_ec")

        # MKPs and ~/local/
        self._new_site["replicate_mkps"] = html.get_checkbox("replicate_mkps")

        # Secret is not checked here, just kept
        if not self._new and "secret" in old_site:
            self._new_site["secret"] = old_site["secret"]

        # Do not forget to add those settings (e.g. "globals") that
        # are not edited with this dialog
        if not self._new:
            for key in old_site.keys():
                if key not in self._new_site:
                    self._new_site[key] = old_site[key]

        self._site_mgmt.validate_configuration(self._site_id or self._id, self._new_site,
                                               configured_sites)

    def page(self):
        html.begin_form("site")

        self._page_basic_settings()
        self._page_livestatus_settings()
        self._page_replication_configuration()

        forms.end()
        html.button("save", _("Save"))
        html.hidden_fields()
        html.end_form()

    def _page_basic_settings(self):
        forms.header(_("Basic settings"))
        # ID
        forms.section(_("Site ID"), simple=not self._new)
        if self._new:
            html.text_input("id", self._site_id or self._clone_id)
            html.set_focus("id")
        else:
            html.write_text(self._site_id)

        html.help(
            _("The site ID must be identical (case sensitive) with the instance's exact name."))
        # Alias
        forms.section(_("Alias"))
        html.text_input("alias", self._site.get("alias", ""), size=60)
        if not self._new:
            html.set_focus("alias")
        html.help(_("An alias or description of the site."))

    def _page_livestatus_settings(self):
        forms.header(_("Livestatus settings"))
        forms.section(_("Connection"))
        method = self._site.get("socket", None)

        self._site_mgmt.connection_method_valuespec().render_input("method", method)
        html.help(
            _("When connecting to remote site please make sure "
              "that Livestatus over TCP is activated there. You can use UNIX sockets "
              "to connect to foreign sites on localhost. Please make sure that this "
              "site has proper read and write permissions to the UNIX socket of the "
              "foreign site."))

        # Timeout
        forms.section(_("Connect Timeout"))
        timeout = self._site.get("timeout", 10)
        html.number_input("timeout", timeout, size=2)
        html.write_text(_(" seconds"))
        html.help(
            _("This sets the time that Multisite waits for a connection "
              "to the site to be established before the site is considered to be unreachable. "
              "If not set, the operating system defaults are begin used and just one login attempt is being. "
              "performed."))

        # Persistent connections
        forms.section(_("Persistent Connection"), simple=True)
        html.checkbox(
            "persist", self._site.get("persist", False), label=_("Use persistent connections"))
        html.help(
            _("If you enable persistent connections then Multisite will try to keep open "
              "the connection to the remote sites. This brings a great speed up in high-latency "
              "situations but locks a number of threads in the Livestatus module of the target site."
             ))

        # URL-Prefix
        docu_url = "https://mathias-kettner.com/checkmk_multisite_modproxy.html"
        forms.section(_("URL prefix"))
        html.text_input("url_prefix", self._site.get("url_prefix", ""), size=60)
        html.help(
            _("The URL prefix will be prepended to links of addons like PNP4Nagios "
              "or the classical Nagios GUI when a link to such applications points to a host or "
              "service on that site. You can either use an absolute URL prefix like <tt>http://some.host/mysite/</tt> "
              "or a relative URL like <tt>/mysite/</tt>. When using relative prefixes you needed a mod_proxy "
              "configuration in your local system apache that proxies such URLs to the according remote site. "
              "Please refer to the <a target=_blank href='%s'>online documentation</a> for details. "
              "The prefix should end with a slash. Omit the <tt>/pnp4nagios/</tt> from the prefix.")
            % docu_url)

        # Status-Host
        docu_url = "https://mathias-kettner.com/checkmk_multisite_statushost.html"
        forms.section(_("Status host"))

        sh = self._site.get("status_host")
        if sh:
            self._sh_site, self._sh_host = sh
        else:
            self._sh_site = ""
            self._sh_host = ""

        html.write_text(_("host: "))
        self._vs_host().render_input("sh_host", self._sh_host)

        html.write_text(_(" on monitoring site: "))

        choices = [("", _("(no status host)"))] + [
            (sk, si.get("alias", sk)) for (sk, si) in self._site_mgmt.load_sites().items()
        ]
        html.dropdown("sh_site", choices, deflt=self._sh_site, ordered=True)

        html.help(
            _("By specifying a status host for each non-local connection "
              "you prevent Multisite from running into timeouts when remote sites do not respond. "
              "You need to add the remote monitoring servers as hosts into your local monitoring "
              "site and use their host state as a reachability state of the remote site. Please "
              "refer to the <a target=_blank href='%s'>online documentation</a> for details.") %
            docu_url)

        # Disabled
        forms.section(_("Disable"), simple=True)
        html.checkbox(
            "disabled",
            self._site.get("disabled", False),
            label=_("Temporarily disable this connection"))
        html.help(
            _("If you disable a connection, then no data of this site will be shown in the status GUI. "
              "The replication is not affected by this, however."))

    def _vs_host(self):
        return MonitoredHostname()

    def _page_replication_configuration(self):
        # Replication
        forms.header(_("Configuration Replication (Distributed WATO)"))
        forms.section(_("Replication method"))
        html.dropdown(
            "replication", [(None, _("No replication with this site")),
                            ("slave", _("Slave: push configuration to this site"))],
            deflt=self._site.get("replication"))
        html.help(
            _("WATO replication allows you to manage several monitoring sites with a "
              "logically centralized WATO. Slave sites receive their configuration "
              "from master sites. <br><br>Note: Slave sites "
              "do not need any replication configuration. They will be remote-controlled "
              "by the master sites."))

        forms.section(_("Multisite-URL of remote site"))
        html.text_input("multisiteurl", self._site.get("multisiteurl", ""), size=60)
        html.help(
            _("URL of the remote Check_MK including <tt>/check_mk/</tt>. "
              "This URL is in many cases the same as the URL-Prefix but with <tt>check_mk/</tt> "
              "appended, but it must always be an absolute URL. Please note, that "
              "that URL will be fetched by the Apache server of the local "
              "site itself, whilst the URL-Prefix is used by your local Browser."))

        forms.section(_("WATO"), simple=True)
        html.checkbox(
            "disable_wato",
            self._site.get("disable_wato", True),
            label=_('Disable configuration via WATO on this site'))
        html.help(
            _('It is a good idea to disable access to WATO completely on the slave site. '
              'Otherwise a user who does not now about the replication could make local '
              'changes that are overridden at the next configuration activation.'))

        forms.section(_("SSL"), simple=True)
        html.checkbox(
            "insecure", self._site.get("insecure", False), label=_('Ignore SSL certificate errors'))
        html.help(
            _('This might be needed to make the synchronization accept problems with '
              'SSL certificates when using an SSL secured connection.'))

        forms.section(_('Direct login to Web GUI allowed'), simple=True)
        html.checkbox(
            'user_login',
            self._site.get('user_login', True),
            label=_('Users are allowed to directly login into the Web GUI of this site'))
        html.help(
            _('When enabled, this site is marked for synchronisation every time a Web GUI '
              'related option is changed in the master site.'))

        forms.section(_("Sync with LDAP connections"), simple=True)
        self._site_mgmt.user_sync_valuespec().render_input(
            "user_sync",
            self._site.get("user_sync",
                           None if self._new else userdb.user_sync_default_config(self._site_id)))
        html.br()
        html.help(
            _('By default the users are synchronized automatically in the interval configured '
              'in the connection. For example the LDAP connector synchronizes the users every '
              'five minutes by default. The interval can be changed for each connection '
              'individually in the <a href="wato.py?mode=ldap_config">connection settings</a>. '
              'Please note that the synchronization is only performed on the master site in '
              'distributed setups by default.<br>'
              'The remote sites don\'t perform automatic user synchronizations with the '
              'configured connections. But you can configure each site to either '
              'synchronize the users with all configured connections or a specific list of '
              'connections.'))

        if config.mkeventd_enabled:
            forms.section(_('Event Console'), simple=True)
            html.checkbox(
                'replicate_ec',
                self._site.get("replicate_ec", True),
                label=_("Replicate Event Console configuration to this site"))
            html.help(
                _("This option enables the distribution of global settings and rules of the Event Console "
                  "to the remote site. Any change in the local Event Console settings will mark the site "
                  "as <i>need sync</i>. A synchronization will automatically reload the Event Console of "
                  "the remote site."))

        forms.section(_("Extensions"), simple=True)
        html.checkbox(
            "replicate_mkps",
            self._site.get("replicate_mkps", False),
            label=_("Replicate extensions (MKPs and files in <tt>~/local/</tt>)"))
        html.help(
            _("If you enable the replication of MKPs then during each <i>Activate Changes</i> MKPs "
              "that are installed on your master site and all other files below the <tt>~/local/</tt> "
              "directory will be also transferred to the slave site. Note: <b>all other MKPs and files "
              "below <tt>~/local/</tt> on the slave will be removed</b>."))


@mode_registry.register
class ModeDistributedMonitoring(ModeSites):
    @classmethod
    def name(cls):
        return "sites"

    @classmethod
    def permissions(cls):
        return ["sites"]

    def title(self):
        return _("Distributed Monitoring")

    def buttons(self):
        super(ModeDistributedMonitoring, self).buttons()
        html.context_button(
            _("New connection"), watolib.folder_preserving_link([("mode", "edit_site")]), "new")

    def action(self):
        delete_id = html.request.var("_delete")
        if delete_id and html.transaction_valid():
            self._action_delete(delete_id)

        logout_id = html.request.var("_logout")
        if logout_id:
            return self._action_logout(logout_id)

        login_id = html.request.var("_login")
        if login_id:
            return self._action_login(login_id)

    def _action_delete(self, delete_id):
        configured_sites = self._site_mgmt.load_sites()
        # The last connection can always be deleted. In that case we
        # fall back to non-distributed-WATO and the site attribute
        # will be removed.
        test_sites = dict(configured_sites.items())
        del test_sites[delete_id]

        # Make sure that site is not being used by hosts and folders
        if delete_id in watolib.Folder.root_folder().all_site_ids():
            search_url = html.makeactionuri([
                ("host_search_change_site", "on"),
                ("host_search_site", delete_id),
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


        c = wato_confirm(_("Confirm deletion of site %s") % html.render_tt(delete_id),
                         _("Do you really want to delete the connection to the site %s?") % \
                         html.render_tt(delete_id))
        if c:
            self._site_mgmt.delete_site(delete_id)
            return None

        elif c is False:
            return ""

        return None

    def _action_logout(self, logout_id):
        configured_sites = self._site_mgmt.load_sites()
        site = configured_sites[logout_id]
        c = wato_confirm(_("Confirm logout"),
                         _("Do you really want to log out of '%s'?") % \
                         html.render_tt(site["alias"]))
        if c:
            if "secret" in site:
                del site["secret"]
            self._site_mgmt.save_sites(configured_sites)
            watolib.add_change(
                "edit-site",
                _("Logged out of remote site %s") % html.render_tt(site["alias"]),
                domains=[watolib.ConfigDomainGUI],
                sites=[watolib.default_site()])
            return None, _("Logged out.")

        elif c is False:
            return ""

        else:
            return None

    def _action_login(self, login_id):
        configured_sites = self._site_mgmt.load_sites()
        if html.request.var("_abort"):
            return "sites"

        if not html.check_transaction():
            return

        site = configured_sites[login_id]
        error = None
        # Fetch name/password of admin account
        if html.request.has_var("_name"):
            name = html.request.var("_name", "").strip()
            passwd = html.request.var("_passwd", "").strip()
            try:
                if not html.get_checkbox("_confirm"):
                    raise MKUserError(
                        "_confirm",
                        _("You need to confirm that you want to "
                          "overwrite the remote site configuration."))

                response = watolib.do_site_login(login_id, name, passwd)

                if isinstance(response, dict):
                    if cmk.is_managed_edition() and response["edition_short"] != "cme":
                        raise MKUserError(
                            None,
                            _("The Check_MK Managed Services Edition can only "
                              "be connected with other sites using the CME."))
                    secret = response["login_secret"]
                else:
                    secret = response

                site["secret"] = secret
                self._site_mgmt.save_sites(configured_sites)
                message = _("Successfully logged into remote site %s.") % html.render_tt(
                    site["alias"])
                watolib.log_audit(None, "edit-site", message)
                return None, message

            except watolib.MKAutomationException as e:
                error = _("Cannot connect to remote site: %s") % e

            except MKUserError as e:
                html.add_user_error(e.varname, e)
                error = "%s" % e

            except Exception as e:
                logger.exception()
                if config.debug:
                    raise
                html.add_user_error("_name", error)
                error = (_("Internal error: %s\n%s") % (e, traceback.format_exc())).replace(
                    "\n", "\n<br>")

        wato_html_head(_("Login into site \"%s\"") % site["alias"])
        if error:
            html.show_error(error)

        html.p(
            _("For the initial login into the slave site %s "
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
        html.checkbox(
            "_confirm", False, label=_("Confirm overwrite of the remote site configuration"))
        forms.end()
        html.button("_do_login", _("Login"))
        html.button("_abort", _("Abort"))
        html.hidden_field("_login", login_id)
        html.hidden_fields()
        html.end_form()
        html.footer()
        return False

    def page(self):
        with table_element(
                "sites",
                _("Connections to local and remote sites"),
                empty_text=_(
                    "You have not configured any local or remotes sites. Multisite will "
                    "implicitely add the data of the local monitoring site. If you add remotes "
                    "sites, please do not forget to add your local monitoring site also, if "
                    "you want to display its data.")) as table:

            sites = sort_sites(self._site_mgmt.load_sites().items())
            for site_id, site in sites:
                table.row()

                self._page_buttons(table, site_id, site)
                self._page_basic_settings(table, site_id, site)
                self._page_livestatus_settings(table, site_id, site)
                self._page_replication_configuration(table, site_id, site)

    def _page_buttons(self, table, site_id, site):
        table.cell(_("Actions"), css="buttons")
        edit_url = watolib.folder_preserving_link([("mode", "edit_site"), ("edit", site_id)])
        html.icon_button(edit_url, _("Properties"), "edit")

        clone_url = watolib.folder_preserving_link([("mode", "edit_site"), ("clone", site_id)])
        html.icon_button(clone_url, _("Clone this connection in order to create a new one"),
                         "clone")

        delete_url = html.makeactionuri([("_delete", site_id)])
        html.icon_button(delete_url, _("Delete"), "delete")

        if (config.has_wato_slave_sites()
            and (site.get("replication") or config.site_is_local(site_id))) \
           or watolib.is_wato_slave_site():
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

    def _page_basic_settings(self, table, site_id, site):
        table.text_cell(_("ID"), site_id)
        table.text_cell(_("Alias"), site.get("alias", ""))

    def _page_livestatus_settings(self, table, site_id, site):
        # Socket
        table.cell(_("Socket"))
        vs_connection = self._site_mgmt.connection_method_valuespec()
        html.write(vs_connection.value_to_text(site["socket"]))

        # Status host
        if site.get("status_host"):
            sh_site, sh_host = site["status_host"]
            table.text_cell(_("Status host"), "%s/%s" % (sh_site, sh_host))
        else:
            table.text_cell(_("Status host"))

        # Disabled
        if site.get("disabled", False) is True:
            table.text_cell(_("Disabled"), "<b>%s</b>" % _("yes"))
        else:
            table.text_cell(_("Disabled"), _("no"))

        # Timeout
        if "timeout" in site:
            table.text_cell(_("Timeout"), _("%d sec") % int(site["timeout"]), css="number")
        else:
            table.text_cell(_("Timeout"), "")

        # Persist
        if site.get("persist", False):
            table.text_cell(_("Pers."), "<b>%s</b>" % _("yes"))
        else:
            table.text_cell(_("Pers."), _("no"))

    def _page_replication_configuration(self, table, site_id, site):
        # Replication
        if site.get("replication"):
            repl = _("Slave")
            if site.get("replicate_ec"):
                repl += ", " + _("EC")
            if site.get("replicate_mkps"):
                repl += ", " + _("MKPs")
        else:
            repl = ""
        table.text_cell(_("Replication"), repl)

        # Login-Button for Replication
        table.cell(_("Login"))
        if repl:
            if site.get("secret"):
                logout_url = watolib.make_action_link([("mode", "sites"), ("_logout", site_id)])
                html.buttonlink(logout_url, _("Logout"))
            else:
                login_url = watolib.make_action_link([("mode", "sites"), ("_login", site_id)])
                html.buttonlink(login_url, _("Login"))


@mode_registry.register
class ModeEditSiteGlobals(ModeSites, GlobalSettingsMode):
    @classmethod
    def name(cls):
        return "edit_site_globals"

    @classmethod
    def permissions(cls):
        return ["sites"]

    def __init__(self):
        super(ModeEditSiteGlobals, self).__init__()
        self._site_id = html.request.var("site")
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
        return _("Edit site specific global settings of %r") % self._site_id

    def buttons(self):
        super(ModeEditSiteGlobals, self).buttons()
        html.context_button(
            _("All Sites"), watolib.folder_preserving_link([("mode", "sites")]), "back")
        html.context_button(
            _("Connection"),
            watolib.folder_preserving_link([("mode", "edit_site"), ("edit", self._site_id)]),
            "sites")

    # TODO: Consolidate with ModeEditGlobals.action()
    def action(self):
        varname = html.request.var("_varname")
        action = html.request.var("_action")
        if not varname:
            return

        config_variable = watolib.config_variable_registry[varname]()
        def_value = self._global_settings.get(varname, self._default_values[varname])

        if action == "reset" and not is_a_checkbox(config_variable.valuespec()):
            c = wato_confirm(
                _("Removing site specific configuration variable"),
                _("Do you really want to remove the configuration variable <b>%s</b> "
                  "of the specific configuration of this site and that way use the global value "
                  "of <b><tt>%s</tt></b>?") %
                (varname, config_variable.valuespec().value_to_text(def_value)))

        else:
            if not html.check_transaction():
                return
            # No confirmation for direct toggle
            c = True

        if c:
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
                return "edit_site_globals", msg
            return "edit_site_globals"

        elif c is False:
            return ""

        else:
            return None

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

            if not self._site.get("replication") and not config.site_is_local(self._site_id):
                html.show_error(
                    _("This site is not the master site nor a replication slave. "
                      "You cannot configure specific settings for it."))
                return

        self._show_configuration_variables(self._groups(show_all=True))
