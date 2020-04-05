#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import re
import time
import shutil
import traceback
from typing import (  # pylint: disable=unused-import
    NamedTuple, Type,
)
import six

import cmk.utils.version as cmk_version
import cmk.utils.store as store

import cmk.gui.sites
import cmk.gui.multitar as multitar
import cmk.gui.config as config
import cmk.gui.userdb as userdb
import cmk.gui.hooks as hooks
from cmk.gui.globals import html
from cmk.gui.i18n import _
from cmk.gui.exceptions import MKUserError, MKGeneralException
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
import cmk.gui.watolib.activate_changes
import cmk.gui.watolib.sidebar_reload
from cmk.gui.watolib.config_domains import (
    ConfigDomainLiveproxy,
    ConfigDomainGUI,
    ConfigDomainCACertificates,
)
from cmk.gui.watolib.automation_commands import (
    AutomationCommand,
    automation_command_registry,
)
from cmk.gui.watolib.global_settings import save_site_global_settings
from cmk.gui.watolib.utils import (
    default_site,
    multisite_dir,
)

from cmk.gui.plugins.watolib.utils import wato_fileheader


class SiteManagementFactory(object):
    @staticmethod
    def factory():
        # type: () -> SiteManagement
        if cmk_version.is_raw_edition():
            cls = CRESiteManagement  # type: Type[SiteManagement]
        else:
            cls = CEESiteManagement

        return cls()


class SiteManagement(object):
    @classmethod
    def connection_method_valuespec(cls):
        return CascadingDropdown(
            title=_("Connection"),
            orientation="horizontal",
            choices=cls._connection_choices(),
            render=CascadingDropdown.Render.foldable,
            help=_("When connecting to remote site please make sure "
                   "that Livestatus over TCP is activated there. You can use UNIX sockets "
                   "to connect to foreign sites on localhost. Please make sure that this "
                   "site has proper read and write permissions to the UNIX socket of the "
                   "foreign site."),
        )

    @classmethod
    def livestatus_proxy_valuespec(cls):
        return FixedValue(
            None,
            title=_("Use Livestatus Proxy Daemon"),
            totext=_("Connect directly (not available in CRE)"),
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
                 optional_keys=False,
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
                ("tls", cls._tls_valuespec()),
            ],
            optional_keys=False,
        )

    @classmethod
    def _tls_valuespec(cls):
        return CascadingDropdown(
            title=_("Encryption"),
            choices=[
                (
                    "plain_text",
                    _("Plain text (Unencrypted)"),
                    FixedValue({}, totext=_("Use plain text, unencrypted transport")),
                ),
                ("encrypted", _("Encrypt data using TLS"),
                 Dictionary(
                     elements=[
                         ("verify",
                          Checkbox(
                              title=_("Verify server certificate"),
                              label=_(
                                  "Verify the Livestatus server certificate using the local site CA"
                              ),
                              default_value=True,
                              help=
                              _("Either verify the server certificate using the site local CA or accept "
                                "any certificate offered by the server. It is highly recommended to "
                                "leave this enabled."),
                          )),
                     ],
                     optional_keys=False,
                 )),
            ],
            help=
            _("When connecting to Check_MK versions older than 1.6 you can only use plain text "
              "transport. Starting with Check_MK 1.6 it is possible to use encrypted Livestatus "
              "communication. Sites created with 1.6 will automatically use encrypted communication "
              "by default. Sites created with previous versions need to be configured manually to "
              "enable the encryption. Have a look at <a href=\"werk.py?werk=7017\">werk #7017</a> "
              "for further information."),
        )

    @classmethod
    def user_sync_valuespec(cls):
        return CascadingDropdown(
            title=_("Sync with LDAP connections"),
            orientation="horizontal",
            choices=[
                (None, _("Disable automatic user synchronization (use master site users)")),
                ("all", _("Sync users with all connections")),
                ("list", _("Sync with the following LDAP connections"),
                 ListChoice(
                     choices=userdb.connection_choices,
                     allow_empty=False,
                 )),
            ],
            help=_(
                'By default the users are synchronized automatically in the interval configured '
                'in the connection. For example the LDAP connector synchronizes the users every '
                'five minutes by default. The interval can be changed for each connection '
                'individually in the <a href="wato.py?mode=ldap_config">connection settings</a>. '
                'Please note that the synchronization is only performed on the master site in '
                'distributed setups by default.<br>'
                'The remote sites don\'t perform automatic user synchronizations with the '
                'configured connections. But you can configure each site to either '
                'synchronize the users with all configured connections or a specific list of '
                'connections.'),
        )

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
        if not os.path.exists(cls._sites_mk()):
            return config.default_single_site_configuration()

        raw_sites = store.load_from_mk_file(cls._sites_mk(), "sites", {})
        if not raw_sites:
            return config.default_single_site_configuration()

        sites = config.migrate_old_site_config(raw_sites)
        for site in sites.values():
            if site["proxy"] is not None:
                site["proxy"] = cls.transform_old_connection_params(site["proxy"])

        return sites

    @classmethod
    def save_sites(cls, sites, activate=True):
        # TODO: Clean this up
        from cmk.gui.watolib.hosts_and_folders import Folder
        store.mkdir(multisite_dir())
        store.save_to_mk_file(cls._sites_mk(), "sites", sites)

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
    def _sites_mk(cls):
        return cmk.utils.paths.default_config_dir + "/multisite.d/sites.mk"

    @classmethod
    def delete_site(cls, site_id):
        # TODO: Clean this up
        from cmk.gui.watolib.hosts_and_folders import Folder
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
        cmk.gui.watolib.activate_changes.clear_site_replication_status(site_id)
        cmk.gui.watolib.changes.add_change("edit-sites",
                                           _("Deleted site %s") % site_id,
                                           domains=domains,
                                           sites=[default_site()])

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
    def livestatus_proxy_valuespec(cls):
        return Alternative(
            title=_("Use Livestatus Proxy Daemon"),
            style="dropdown",
            elements=[
                FixedValue(
                    None,
                    title=_("Connect directly, without Livestatus Proxy"),
                    totext="",
                ),
                Transform(
                    Dictionary(
                        title=_("Use Livestatus Proxy Daemon"),
                        optional_keys=["tcp"],
                        columns=1,
                        elements=[
                            ("params",
                             Alternative(
                                 title=_("Parameters"),
                                 style="dropdown",
                                 elements=[
                                     FixedValue(
                                         None,
                                         title=_("Use global connection parameters"),
                                         totext=
                                         _("Use the <a href=\"%s\">global parameters</a> for this connection"
                                          ) %
                                         "wato.py?mode=edit_configvar&site=&varname=liveproxyd_default_connection_params",
                                     ),
                                     Dictionary(
                                         title=_("Use custom connection parameters"),
                                         elements=cls.liveproxyd_connection_params_elements(),
                                     ),
                                 ],
                             )),
                            ("tcp",
                             LivestatusViaTCP(
                                 title=_("Allow access via TCP"),
                                 help=
                                 _("This option can be useful to build a cascading distributed setup. "
                                   "The Livestatus Proxy of this site connects to the site configured "
                                   "here via Livestatus and opens up a TCP port for clients. The "
                                   "requests of the clients are forwarded to the destination site. "
                                   "You need to configure a TCP port here that is not used on the "
                                   "local system yet."),
                                 tcp_port=6560,
                             )),
                        ],
                    ),
                    forth=cls.transform_old_connection_params,
                ),
            ],
        )

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
             Tuple(title=_("Regular heartbeat"),
                   orientation="float",
                   elements=[
                       Integer(
                           label=_("One heartbeat every"),
                           unit=_("sec"),
                           minvalue=1,
                           default_value=defaults["heartbeat"][0],
                       ),
                       Float(label=_("with a timeout of"),
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
            proxy_params = siteconf["proxy"]
            if proxy_params is None:
                continue

            conf[siteid] = {
                "socket": siteconf["socket"],
            }

            conf[siteid]["connect_timeout"] = siteconf.get("timeout", 2)

            if "tcp" in proxy_params:
                conf[siteid]["tcp"] = proxy_params["tcp"]

            if proxy_params["params"]:
                conf[siteid].update(proxy_params["params"])

        store.save_to_mk_file(path, "sites", conf)

        ConfigDomainLiveproxy().activate()

    @classmethod
    def _affected_config_domains(cls):
        domains = super(CEESiteManagement, cls)._affected_config_domains()
        if config.liveproxyd_enabled:
            domains.append(ConfigDomainLiveproxy)
        return domains


# TODO: Change to factory
class LivestatusViaTCP(Dictionary):
    def __init__(self, **kwargs):
        kwargs["elements"] = [
            ("port",
             Integer(
                 title=_("TCP port"),
                 minvalue=1,
                 maxvalue=65535,
                 default_value=kwargs.pop("tcp_port", 6557),
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
            ("tls",
             FixedValue(
                 True,
                 title=_("Encrypt communication"),
                 totext=_("Encrypt TCP Livestatus connections"),
                 help=_("Since Check_MK 1.6 it is possible to encrypt the TCP Livestatus "
                        "connections using SSL. This is enabled by default for sites that "
                        "enable Livestatus via TCP with 1.6 or newer. Sites that already "
                        "have this option enabled keep the communication unencrypted for "
                        "compatibility reasons. However, it is highly recommended to "
                        "migrate to an encrypted communication."),
             )),
        ]
        kwargs["optional_keys"] = ["only_from", "tls"]
        super(LivestatusViaTCP, self).__init__(**kwargs)


def _create_nagvis_backends(sites_config):
    cfg = [
        '; MANAGED BY CHECK_MK WATO - Last Update: %s' % time.strftime('%Y-%m-%d %H:%M:%S'),
    ]
    for site_id, site in sites_config.items():
        if site == config.omd_site():
            continue  # skip local site, backend already added by omd

        socket = _encode_socket_for_nagvis(site_id, site)

        cfg += [
            '',
            '[backend_%s]' % site_id,
            'backendtype="mklivestatus"',
            'socket="%s"' % socket,
        ]

        if site.get("status_host"):
            cfg.append('statushost="%s"' % ':'.join(site['status_host']))

        if site["proxy"] is None and is_livestatus_encrypted(site):
            address_spec = site["socket"][1]
            tls_settings = address_spec["tls"][1]
            cfg.append('verify_tls_peer=%d' % tls_settings["verify"])
            cfg.append('verify_tls_ca_path=%s' % ConfigDomainCACertificates.trusted_cas_file)

    store.save_file('%s/etc/nagvis/conf.d/cmk_backends.ini.php' % cmk.utils.paths.omd_root,
                    '\n'.join(cfg))


def _encode_socket_for_nagvis(site_id, site):
    if site["proxy"] is None and is_livestatus_encrypted(site):
        return "tcp-tls:%s:%d" % site["socket"][1]["address"]
    return cmk.gui.sites.encode_socket_for_livestatus(site_id, site)


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


def is_livestatus_encrypted(site):
    family_spec, address_spec = site["socket"]
    return family_spec in ["tcp", "tcp6"] and address_spec["tls"][0] != "plain_text"


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


PushSnapshotRequest = NamedTuple("PushSnapshotRequest", [
    ("site_id", str),
    ("tar_content", six.binary_type),
])


@automation_command_registry.register
class AutomationPushSnapshot(AutomationCommand):
    def command_name(self):
        return "push-snapshot"

    def get_request(self):
        # type: () -> PushSnapshotRequest
        site_id = html.request.get_ascii_input_mandatory("siteid")
        self._verify_slave_site_config(site_id)

        snapshot = html.request.uploaded_file("snapshot")
        if not snapshot:
            raise MKGeneralException(_('Invalid call: The snapshot is missing.'))

        return PushSnapshotRequest(site_id=site_id, tar_content=six.ensure_binary(snapshot[2]))

    def execute(self, request):
        # type: (PushSnapshotRequest) -> bool
        with store.lock_checkmk_configuration():
            multitar.extract_from_buffer(request.tar_content,
                                         cmk.gui.watolib.activate_changes.get_replication_paths())

            try:
                self._save_site_globals_on_slave_site(request.tar_content)

                # pending changes are lost
                cmk.gui.watolib.activate_changes.confirm_all_local_changes()

                hooks.call("snapshot-pushed")

                # Create rule making this site only monitor our hosts
                create_distributed_wato_file(request.site_id, is_slave=True)
            except Exception:
                raise MKGeneralException(
                    _("Failed to deploy configuration: \"%s\". "
                      "Please note that the site configuration has been synchronized "
                      "partially.") % traceback.format_exc())

            cmk.gui.watolib.changes.log_audit(
                None, "replication",
                _("Synchronized with master (my site id is %s.)") % request.site_id)

            return True

    def _save_site_globals_on_slave_site(self, tarcontent):
        tmp_dir = cmk.utils.paths.tmp_dir + "/sitespecific-%s" % id(html)
        try:
            if not os.path.exists(tmp_dir):
                store.mkdir(tmp_dir)

            multitar.extract_from_buffer(tarcontent, [("dir", "sitespecific", tmp_dir)])

            site_globals = store.load_object_from_file(tmp_dir + "/sitespecific.mk", default={})
            save_site_global_settings(site_globals)
        finally:
            shutil.rmtree(tmp_dir)
