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

import os
import re
import time
import six

import cmk
import cmk.utils.store as store

import cmk.gui.sites
import cmk.gui.config as config
import cmk.gui.userdb as userdb
import cmk.gui.hooks as hooks
from cmk.gui.globals import html
from cmk.gui.i18n import _
from cmk.gui.exceptions import MKUserError
from cmk.gui.valuespec import (
    CascadingDropdown,
    Checkbox,
    TextAscii,
    Float,
    Integer,
    Tuple,
    Dictionary,
    FixedValue,
    Alternative,
    Transform,
    ListOfStrings,
    IPNetwork,
    HostAddress,
    ListChoice,
)

import cmk.gui.watolib.changes
import cmk.gui.watolib.sidebar_reload
from cmk.gui.watolib.hosts_and_folders import Folder
from cmk.gui.watolib.config_domains import (
    ConfigDomainLiveproxy,
    ConfigDomainGUI,
)
from cmk.gui.watolib.utils import (
    default_site,
    multisite_dir,
)

from cmk.gui.plugins.watolib.utils import wato_fileheader

sites_mk = cmk.utils.paths.default_config_dir + "/multisite.d/sites.mk"


class SiteManagementFactory(object):
    @staticmethod
    def factory():
        if cmk.is_raw_edition():
            cls = CRESiteManagement
        else:
            cls = CEESiteManagement

        return cls()


class SiteManagement(object):
    @classmethod
    def connection_method_valuespec(cls):
        return CascadingDropdown(
            orientation="horizontal",
            choices=cls._connection_choices(),
            render=CascadingDropdown.Render.foldable,
        )

    @classmethod
    def _connection_choices(cls):
        conn_choices = [
            ("local", _("Connect to the local site"), FixedValue(
                None,
                totext="",
            )),
            ("tcp", _("Connect via TCP (IPv4)"), cls._tcp_socket_valuespec(ipv6=False)),
            ("tcp6", _("Connect via TCP (IPv6)"), cls._tcp_socket_valuespec(ipv6=True)),
            ("unix", _("Connect via UNIX socket"),
             Dictionary(
                 elements=[
                     ("path", TextAscii(
                         label=_("Path:"),
                         size=40,
                         allow_empty=False,
                     )),
                 ],
                 optional_keys=None,
             )),
        ]
        return conn_choices

    @classmethod
    def _tcp_socket_valuespec(cls, ipv6):
        return Dictionary(
            elements=[
                ("address",
                 Tuple(
                     title=_("TCP address to connect to"),
                     orientation="float",
                     elements=[
                         HostAddress(
                             label=_("Host:"),
                             allow_empty=False,
                             size=15,
                             allow_ipv4_address=not ipv6,
                             allow_ipv6_address=ipv6,
                         ),
                         Integer(
                             label=_("Port:"),
                             minvalue=1,
                             maxvalue=65535,
                             default_value=6557,
                         ),
                     ],
                 )),
            ],
            optional_keys=None,
        )

    @classmethod
    def user_sync_valuespec(cls):
        return CascadingDropdown(
            orientation="horizontal",
            choices=[
                (None, _("Disable automatic user synchronization (use master site users)")),
                ("all", _("Sync users with all connections")),
                ("list", _("Sync with the following LDAP connections"),
                 ListChoice(
                     choices=userdb.connection_choices,
                     allow_empty=False,
                 )),
            ])

    @classmethod
    def validate_configuration(cls, site_id, site_configuration, all_sites):
        if not re.match("^[-a-z0-9A-Z_]+$", site_id):
            raise MKUserError(
                "id", _("The site id must consist only of letters, digit and the underscore."))

        if not site_configuration.get("alias"):
            raise MKUserError(
                "alias",
                _("Please enter an alias name or description for the site %s.") % site_id)

        if site_configuration.get("url_prefix") and site_configuration.get("url_prefix")[-1] != "/":
            raise MKUserError("url_prefix", _("The URL prefix must end with a slash."))

        # Connection
        if site_configuration["socket"][0] == "local" and site_id != config.omd_site():
            raise MKUserError(
                "method_sel",
                _("You can only configure a local site connection for "
                  "the local site. The site IDs ('%s' and '%s') are "
                  "not equal.") % (site_id, config.omd_site()))

        # Timeout
        if "timeout" in site_configuration:
            timeout = site_configuration["timeout"]
            try:
                int(timeout)
            except ValueError:
                raise MKUserError("timeout",
                                  _("The timeout %s is not a valid integer number.") % timeout)

        # Status host
        status_host = site_configuration.get("status_host")
        if status_host:
            status_host_site, status_host_name = status_host
            if status_host_site not in all_sites:
                raise MKUserError("sh_site", _("The site of the status host does not exist."))
            if status_host_site == site_id:
                raise MKUserError("sh_site",
                                  _("You cannot use the site itself as site of the status host."))
            if not status_host_name:
                raise MKUserError("sh_host", _("Please specify the name of the status host."))

        if site_configuration.get("replication"):
            multisiteurl = site_configuration.get("multisiteurl")
            if not site_configuration.get("multisiteurl"):
                raise MKUserError("multisiteurl",
                                  _("Please enter the Multisite URL of the slave site."))

            if not multisiteurl.endswith("/check_mk/"):
                raise MKUserError("multisiteurl", _("The Multisite URL must end with /check_mk/"))

            if not multisiteurl.startswith("http://") and \
               not multisiteurl.startswith("https://"):
                raise MKUserError(
                    "multisiteurl",
                    _("The Multisites URL must begin with <tt>http://</tt> or <tt>https://</tt>."))

            if site_configuration["socket"][0] == "local":
                raise MKUserError("replication",
                                  _("You cannot do replication with the local site."))

        # User synchronization
        user_sync_valuespec = cls.user_sync_valuespec()
        user_sync_valuespec.validate_value(site_configuration.get("user_sync"), "user_sync")

    @classmethod
    def load_sites(cls):
        if not os.path.exists(sites_mk):
            return config.default_single_site_configuration()

        config_vars = {"sites": {}}
        execfile(sites_mk, config_vars, config_vars)

        if not config_vars["sites"]:
            return config.default_single_site_configuration()

        sites = config.migrate_old_site_config(config_vars["sites"])
        for site in sites.itervalues():
            socket = site["socket"]
            if socket[0] == "proxy":
                site["socket"] = ("proxy", cls.transform_old_connection_params(socket[1]))

        return sites

    @classmethod
    def save_sites(cls, sites, activate=True):
        store.mkdir(multisite_dir)
        store.save_to_mk_file(sites_mk, "sites", sites)

        # Do not activate when just the site's global settings have
        # been edited
        if activate:
            config.load_config()  # make new site configuration active
            _update_distributed_wato_file(sites)
            Folder.invalidate_caches()
            cmk.gui.watolib.sidebar_reload.need_sidebar_reload()

            _create_nagvis_backends(sites)

            # Call the sites saved hook
            hooks.call("sites-saved", sites)

    @classmethod
    def delete_site(cls, site_id):
        all_sites = cls.load_sites()
        if site_id not in all_sites:
            raise MKUserError(None, _("Unable to delete unknown site id: %s") % site_id)

        # Make sure that site is not being used by hosts and folders
        if site_id in Folder.root_folder().all_site_ids():
            search_url = html.makeactionuri([
                ("host_search_change_site", "on"),
                ("host_search_site", site_id),
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

        domains = cls._affected_config_domains()

        del all_sites[site_id]
        cls.save_sites(all_sites)
        cmk.gui.watolib.changes.clear_site_replication_status(site_id)
        cmk.gui.watolib.changes.add_change(
            "edit-sites",
            _("Deleted site %s") % html.render_tt(site_id),
            domains=domains,
            sites=[default_site()])
        return None

    @classmethod
    def _affected_config_domains(cls):
        return [ConfigDomainGUI]

    @classmethod
    def transform_old_connection_params(cls, value):
        return value


class CRESiteManagement(SiteManagement):
    pass


# TODO: This has been moved directly into watolib because it was not easily possible
# to extract SiteManagement() to a separate module (depends on Folder, add_change, ...).
# As soon as we have untied this we should re-establish a watolib plugin hierarchy and
# move this to a CEE/CME specific watolib plugin
class CEESiteManagement(SiteManagement):
    @classmethod
    def _connection_choices(cls):
        choices = super(CEESiteManagement, cls)._connection_choices()

        choices.append(("proxy", _("Use Livestatus Proxy Daemon"), Transform(
            Dictionary(
                optional_keys = ["tcp"],
                columns = 1,
                elements = [
                    ("socket", Transform(
                        CascadingDropdown(
                            title = _("Connect to"),
                            orientation="horizontal",
                            choices=super(CEESiteManagement, cls)._connection_choices(),
                        ),
                        forth=cls._transform_old_socket_spec,
                    )),
                    ("tcp", LivestatusViaTCP(
                        title = _("Allow access via TCP"),
                        help = _("This option can be useful to build a cascading distributed setup. "
                                 "The Livestatus Proxy of this site connects to the site configured "
                                 "here via Livestatus and opens up a TCP port for clients. The "
                                 "requests of the clients are forwarded to the destination site. "
                                 "You need to configure a TCP port here that is not used on the "
                                 "local system yet."),
                        tcp_port = 6560,
                    )),
                    ("params", Alternative(
                        title = _("Parameters"),
                        style = "dropdown",
                        elements = [
                            FixedValue(None,
                                title = _("Use global connection parameters"),
                                totext = _("Use the <a href=\"%s\">global parameters</a> for this connection") % \
                                    "wato.py?mode=edit_configvar&site=&varname=liveproxyd_default_connection_params",
                            ),
                            Dictionary(
                                title = _("Use custom connection parameters"),
                                elements = cls.liveproxyd_connection_params_elements(),
                            ),
                        ],
                    )),
                ],
            ),
            forth = cls.transform_old_connection_params,
        )))

        return choices

    # Duplicate code with cmk.cee.liveproxy.Channel._transform_old_socket_spec
    @classmethod
    def _transform_old_socket_spec(cls, sock_spec):
        """Transforms pre 1.6 socket configs"""
        if isinstance(sock_spec, six.string_types):
            return "unix", {
                "path": sock_spec,
            }

        if isinstance(sock_spec, tuple) and len(sock_spec) == 2 and isinstance(sock_spec[1], int):
            return "tcp", {
                "address": sock_spec,
            }

        return sock_spec

    @classmethod
    def liveproxyd_connection_params_elements(cls):
        defaults = ConfigDomainLiveproxy.connection_params_defaults()

        return [
            ("channels",
             Integer(
                 title=_("Number of channels to keep open"),
                 minvalue=2,
                 maxvalue=50,
                 default_value=defaults["channels"],
             )),
            ("heartbeat",
             Tuple(
                 title=_("Regular heartbeat"),
                 orientation="float",
                 elements=[
                     Integer(
                         label=_("One heartbeat every"),
                         unit=_("sec"),
                         minvalue=1,
                         default_value=defaults["heartbeat"][0],
                     ),
                     Float(
                         label=_("with a timeout of"),
                         unit=_("sec"),
                         minvalue=0.1,
                         default_value=defaults["heartbeat"][1],
                         display_format="%.1f"),
                 ])),
            ("channel_timeout",
             Float(
                 title=_("Timeout waiting for a free channel"),
                 minvalue=0.1,
                 default_value=defaults["channel_timeout"],
                 unit=_("sec"),
             )),
            ("query_timeout",
             Float(
                 title=_("Total query timeout"),
                 minvalue=0.1,
                 unit=_("sec"),
                 default_value=defaults["query_timeout"],
             )),
            ("connect_retry",
             Float(
                 title=_("Cooling period after failed connect/heartbeat"),
                 minvalue=0.1,
                 unit=_("sec"),
                 default_value=defaults["connect_retry"],
             )),
            ("cache",
             Checkbox(
                 title=_("Enable Caching"),
                 label=_("Cache several non-status queries"),
                 help=_("This option will enable the caching of several queries that "
                        "need no current data. This reduces the number of Livestatus "
                        "queries to sites and cuts down the response time of remote "
                        "sites with large latencies."),
                 default_value=defaults["cache"],
             )),
        ]

    # Each site had it's individual connection params set all time. Detect whether or
    # not a site is at the default configuration and set the config to
    # "use default connection params". In case the values are not similar to the current
    # defaults just change the data structure to the new one.
    @classmethod
    def transform_old_connection_params(cls, value):
        if "params" in value:
            return value

        new_value = {
            "socket": value.pop("socket"),
            "params": value,
        }

        defaults = ConfigDomainLiveproxy.connection_params_defaults()
        for key, val in value.items():
            if val == defaults[key]:
                del value[key]

        if not value:
            new_value["params"] = None

        return new_value

    @classmethod
    def save_sites(cls, sites, activate=True):
        super(CEESiteManagement, cls).save_sites(sites, activate)

        if activate and config.liveproxyd_enabled:
            cls._save_liveproxyd_config(sites)

    @classmethod
    def _save_liveproxyd_config(cls, sites):
        path = cmk.utils.paths.default_config_dir + "/liveproxyd.mk"

        conf = {}
        for siteid, siteconf in sites.items():
            family_spec, address_spec = siteconf["socket"]
            if family_spec == "proxy":
                conf[siteid] = {
                    "socket": address_spec["socket"],
                }

                if "tcp" in address_spec:
                    conf[siteid]["tcp"] = address_spec["tcp"]

                if address_spec["params"]:
                    conf[siteid].update(address_spec["params"])

        store.save_to_mk_file(path, "sites", conf)

        ConfigDomainLiveproxy().activate()

    @classmethod
    def _affected_config_domains(cls):
        domains = super(CEESiteManagement, cls)._affected_config_domains()
        if config.liveproxyd_enabled:
            domains.append(ConfigDomainLiveproxy)
        return domains


class LivestatusViaTCP(Dictionary):
    def __init__(self, **kwargs):
        kwargs["elements"] = [
            ("port",
             Integer(
                 title=_("TCP port"),
                 minvalue=1,
                 maxvalue=65535,
                 default_value=kwargs.get("tcp_port", 6557),
             )),
            ("only_from",
             ListOfStrings(
                 title=_("Restrict access to IP addresses"),
                 help=_("The access to Livestatus via TCP will only be allowed from the "
                        "configured source IP addresses. You can either configure specific "
                        "IP addresses or networks in the syntax <tt>10.3.3.0/24</tt>."),
                 valuespec=IPNetwork(),
                 orientation="horizontal",
                 allow_empty=False,
                 default_value=["0.0.0.0", "::/0"],
             )),
        ]
        kwargs["optional_keys"] = ["only_from"]
        super(LivestatusViaTCP, self).__init__(**kwargs)


def _create_nagvis_backends(sites_config):
    cfg = [
        '; MANAGED BY CHECK_MK WATO - Last Update: %s' % time.strftime('%Y-%m-%d %H:%M:%S'),
    ]
    for site_id, site in sites_config.items():
        if site == config.omd_site():
            continue  # skip local site, backend already added by omd

        if site['socket'][0] == "proxy":
            socket = cmk.gui.sites.encode_socket_for_livestatus(site_id,
                                                                site["socket"][1]["socket"])
        else:
            socket = cmk.gui.sites.encode_socket_for_livestatus(site_id, site['socket'])

        cfg += [
            '',
            '[backend_%s]' % site_id,
            'backendtype="mklivestatus"',
            'socket="%s"' % socket,
        ]

        if site.get("status_host"):
            cfg.append('statushost="%s"' % ':'.join(site['status_host']))

    store.save_file('%s/etc/nagvis/conf.d/cmk_backends.ini.php' % cmk.utils.paths.omd_root,
                    '\n'.join(cfg))


# Makes sure, that in distributed mode we monitor only
# the hosts that are directly assigned to our (the local)
# site.
def _update_distributed_wato_file(sites):
    # Note: we cannot access config.sites here, since we
    # are currently in the process of saving the new
    # site configuration.
    distributed = False
    for siteid, site in sites.items():
        if site.get("replication"):
            distributed = True
        if config.site_is_local(siteid):
            create_distributed_wato_file(siteid, is_slave=False)

    # Remove the distributed wato file
    # a) If there is no distributed WATO setup
    # b) If the local site could not be gathered
    if not distributed:  # or not found_local:
        _delete_distributed_wato_file()


def create_distributed_wato_file(siteid, is_slave):
    output = wato_fileheader()
    output += ("# This file has been created by the master site\n"
               "# push the configuration to us. It makes sure that\n"
               "# we only monitor hosts that are assigned to our site.\n\n")
    output += "distributed_wato_site = '%s'\n" % siteid
    output += "is_wato_slave_site = %r\n" % is_slave

    store.save_file(cmk.utils.paths.check_mk_config_dir + "/distributed_wato.mk", output)


def _delete_distributed_wato_file():
    p = cmk.utils.paths.check_mk_config_dir + "/distributed_wato.mk"
    # We do not delete the file but empty it. That way
    # we do not need write permissions to the conf.d
    # directory!
    if os.path.exists(p):
        store.save_file(p, "")
