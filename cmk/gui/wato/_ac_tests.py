#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import multiprocessing
import os
import subprocess
from collections.abc import Iterator, Sequence
from pathlib import Path

import requests
import urllib3

from livestatus import LocalConnection, SiteConfiguration

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.site import omd_site, SiteId
from cmk.ccc.user import UserId
from cmk.ccc.version import __version__, Version

from cmk.utils.paths import (
    local_agent_based_plugins_dir,
    local_checks_dir,
    local_gui_plugins_dir,
    local_inventory_dir,
    local_legacy_check_manpages_dir,
    local_pnp_templates_dir,
    local_web_dir,
)
from cmk.utils.rulesets.definition import RuleGroup, RuleGroupType

import cmk.gui.userdb.ldap_connector as ldap
import cmk.gui.utils
from cmk.gui import userdb
from cmk.gui.backup.handler import Config as BackupConfig
from cmk.gui.config import active_config
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.site_config import (
    has_wato_slave_sites,
    is_wato_slave_site,
    wato_slave_sites,
)
from cmk.gui.userdb import active_connections as active_connections_
from cmk.gui.userdb import htpasswd
from cmk.gui.utils.urls import doc_reference_url, DocReference, werk_reference_url, WerkReference
from cmk.gui.watolib.analyze_configuration import (
    ACResultState,
    ACSingleResult,
    ACTest,
    ACTestCategories,
    ACTestRegistry,
)
from cmk.gui.watolib.check_mk_automations import find_unknown_check_parameter_rule_sets
from cmk.gui.watolib.config_domain_name import ABCConfigDomain
from cmk.gui.watolib.config_domains import ConfigDomainOMD
from cmk.gui.watolib.rulesets import AllRulesets, SingleRulesetRecursively
from cmk.gui.watolib.sites import site_management_registry

from cmk.crypto.password import Password

# Disable python warnings in background job output or logs like "Unverified
# HTTPS request is being made". We warn the user using analyze configuration.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def register(ac_test_registry: ACTestRegistry) -> None:
    ac_test_registry.register(ACTestPersistentConnections)
    ac_test_registry.register(ACTestLiveproxyd)
    ac_test_registry.register(ACTestLivestatusUsage)
    ac_test_registry.register(ACTestTmpfs)
    ac_test_registry.register(ACTestLDAPSecured)
    ac_test_registry.register(ACTestLivestatusSecured)
    ac_test_registry.register(ACTestNumberOfUsers)
    ac_test_registry.register(ACTestHTTPSecured)
    ac_test_registry.register(ACTestOldDefaultCredentials)
    ac_test_registry.register(ACTestBackupConfigured)
    ac_test_registry.register(ACTestBackupNotEncryptedConfigured)
    ac_test_registry.register(ACTestEscapeHTMLDisabled)
    ac_test_registry.register(ACTestApacheNumberOfProcesses)
    ac_test_registry.register(ACTestApacheProcessUsage)
    ac_test_registry.register(ACTestCheckMKHelperUsage)
    ac_test_registry.register(ACTestCheckMKFetcherUsage)
    ac_test_registry.register(ACTestCheckMKCheckerUsage)
    ac_test_registry.register(ACTestGenericCheckHelperUsage)
    ac_test_registry.register(ACTestSizeOfExtensions)
    ac_test_registry.register(ACTestBrokenGUIExtension)
    ac_test_registry.register(ACTestESXDatasources)
    ac_test_registry.register(ACTestDeprecatedRuleSets)
    ac_test_registry.register(ACTestUnknownCheckParameterRuleSets)
    ac_test_registry.register(ACTestDeprecatedV1CheckPlugins)
    ac_test_registry.register(ACTestDeprecatedCheckPlugins)
    ac_test_registry.register(ACTestDeprecatedInventoryPlugins)
    ac_test_registry.register(ACTestDeprecatedCheckManpages)
    ac_test_registry.register(ACTestDeprecatedGUIExtensions)
    ac_test_registry.register(ACTestDeprecatedLegacyGUIExtensions)
    ac_test_registry.register(ACTestDeprecatedPNPTemplates)
    ac_test_registry.register(ACTestUnexpectedAllowedIPRanges)
    ac_test_registry.register(ACTestCheckMKCheckerNumber)


class ACTestPersistentConnections(ACTest):
    def category(self) -> str:
        return ACTestCategories.performance

    def title(self) -> str:
        return _("Persistent connections")

    def help(self) -> str:
        return _(
            "Persistent connections may be a configuration to improve the performance of the GUI, "
            "but be aware that you really need to tune your system to make it work properly. "
            "When you have enabled persistent connections, the single GUI pages may use already "
            "established connections of the Apache process. This saves the time that is needed "
            "for establishing the Livestatus connections. But you need to be aware that each "
            "Apache process that is running is keeping a persistent connection to each configured "
            "site via Livestatus open. This means you need to balance the maximum Apache "
            "processes with the maximum parallel Livestatus connections. Otherwise Livestatus "
            "requests will be blocked by existing and possibly idle connections."
        )

    def is_relevant(self) -> bool:
        # This check is only executed on the central instance of multisite setups
        return len(active_config.sites) > 1

    def execute(self) -> Iterator[ACSingleResult]:
        yield from (
            self._check_site(site_id, active_config.sites[site_id])
            for site_id in active_config.sites
        )

    def _check_site(self, site_id: SiteId, site_config: SiteConfiguration) -> ACSingleResult:
        persist = site_config.get("persist", False)

        if persist and _site_is_using_livestatus_proxy(site_id):
            return ACSingleResult(
                state=ACResultState.WARN,
                text=_(
                    "Persistent connections are nearly useless "
                    "with Livestatus proxy daemon. Better disable it."
                ),
                site_id=site_id,
            )

        if persist:
            # TODO: At least for the local site we could calculate this.
            #       Or should we get the apache config from the remote site via automation?
            return ACSingleResult(
                state=ACResultState.WARN,
                text=_(
                    "Either disable persistent connections or "
                    "carefully review maximum number of Apache processes and "
                    "possible Livestatus connections."
                ),
                site_id=site_id,
            )

        return ACSingleResult(
            state=ACResultState.OK,
            text=_("Is not using persistent connections."),
            site_id=site_id,
        )


class ACTestLiveproxyd(ACTest):
    def category(self) -> str:
        return ACTestCategories.performance

    def title(self) -> str:
        return _("Use Livestatus Proxy Daemon")

    def help(self) -> str:
        return _(
            "The Livestatus Proxy Daemon is available with the Checkmk Enterprise Edition "
            "and improves the management of the inter site connections using livestatus. Using "
            "the Livestatus Proxy Daemon improves the responsiveness and performance of your "
            "GUI and will decrease resource usage."
        )

    def is_relevant(self) -> bool:
        # This check is only executed on the central instance of multisite setups
        return len(active_config.sites) > 1

    def execute(self) -> Iterator[ACSingleResult]:
        yield from (self._check_site(site_id) for site_id in active_config.sites)

    def _check_site(self, site_id: SiteId) -> ACSingleResult:
        if _site_is_using_livestatus_proxy(site_id):
            return ACSingleResult(
                state=ACResultState.OK,
                text=_("Site is using the Livestatus Proxy Daemon"),
                site_id=site_id,
            )

        if not is_wato_slave_site():
            return ACSingleResult(
                state=ACResultState.WARN,
                text=_(
                    "The Livestatus Proxy is not only good for remote sites, "
                    "enable it for your central site"
                ),
                site_id=site_id,
            )

        return ACSingleResult(
            state=ACResultState.WARN,
            text=_("Use the Livestatus Proxy Daemon for your site"),
            site_id=site_id,
        )


class ACTestLivestatusUsage(ACTest):
    def category(self) -> str:
        return ACTestCategories.performance

    def title(self) -> str:
        return _("Livestatus usage")

    def help(self) -> str:
        return _(
            # xgettext: no-python-format
            "<p>Livestatus is used by several components, for example the GUI, to gather "
            "information about the monitored objects from the monitoring core. It is "
            "very important for the overall performance of the monitoring system that "
            "livestatus is reliable and performant.</p>"
            "<p>There should always be enough free livestatus slots to serve new "
            "incoming queries.</p>"
            "<p>You should never reach a livestatus usage of 100% for a longer time. "
            "Consider increasing the number of parallel livestatus connections or track down "
            "the clients to check whether or not you can reduce the usage somehow.</p>"
        )

    def is_relevant(self) -> bool:
        return True

    def execute(self) -> Iterator[ACSingleResult]:
        site_id = omd_site()
        local_connection = LocalConnection()
        site_status = local_connection.query_row(
            "GET status\n"
            "Columns: livestatus_usage livestatus_threads livestatus_active_connections livestatus_overflows_rate"
        )

        usage, threads, active_connections, overflows_rate = site_status

        # Micro Core has an averaged usage pre-calculated. The Nagios core does not have this column.
        # Calculate a non averaged usage instead
        if usage is None:
            usage = float(active_connections) / float(threads)

        usage_perc = 100 * usage

        usage_warn, usage_crit = 80, 95
        if usage_perc >= usage_crit:
            state = ACResultState.CRIT
        elif usage_perc >= usage_warn:
            state = ACResultState.WARN
        else:
            state = ACResultState.OK

        yield ACSingleResult(
            state=state,
            text=_("The current livestatus usage is %.2f%%") % usage_perc,
            site_id=site_id,
        )
        yield ACSingleResult(
            state=state,
            text=_("%d of %d connections used") % (active_connections, threads),
            site_id=site_id,
        )

        # Only available with Micro Core
        if overflows_rate is not None:
            yield ACSingleResult(
                state=state,
                text=_("you have a connection overflow rate of %.2f/s") % overflows_rate,
                site_id=site_id,
            )


class ACTestTmpfs(ACTest):
    def category(self) -> str:
        return ACTestCategories.performance

    def title(self) -> str:
        return _("Temporary filesystem mounted")

    def help(self) -> str:
        return _(
            "<p>By default each Checkmk site has its own temporary file system "
            "(a ramdisk) mounted to <tt>[SITE]/tmp</tt>. In case the mount is not "
            "possible, Checkmk starts without this temporary file system.</p>"
            "<p>Even if this is possible, it is not recommended to use Checkmk this "
            "way, because it may reduce the overall performance of Checkmk.</p>"
        )

    def is_relevant(self) -> bool:
        return True

    def execute(self) -> Iterator[ACSingleResult]:
        site_id = omd_site()
        if self._tmpfs_mounted(omd_site()):
            yield ACSingleResult(
                state=ACResultState.OK,
                text=_("The temporary filesystem is mounted"),
                site_id=site_id,
            )
        else:
            yield ACSingleResult(
                state=ACResultState.WARN,
                text=_(
                    "The temporary filesystem is not mounted. Your installation "
                    "may work with degraded performance."
                ),
                site_id=site_id,
            )

    def _tmpfs_mounted(self, site_id):
        # Borrowed from omd binary
        #
        # Problem here: if /omd is a symbolic link somewhere else,
        # then in /proc/mounts the physical path will appear and be
        # different from tmp_path. We just check the suffix therefore.
        path_suffix = "sites/%s/tmp" % site_id
        with Path("/proc/mounts").open(encoding="utf-8") as f:
            for line in f:
                try:
                    _device, mp, fstype, _options, _dump, _fsck = line.split()
                    if mp.endswith(path_suffix) and fstype == "tmpfs":
                        return True
                except Exception:
                    continue
        return False


class ACTestLDAPSecured(ACTest):
    def category(self) -> str:
        return ACTestCategories.security

    def title(self) -> str:
        return _("Secure LDAP")

    def help(self) -> str:
        return _(
            "When using the regular LDAP protocol all data transfered between the Checkmk "
            "and LDAP servers is sent over the network in plain text (unencrypted). This also "
            "includes the passwords users enter to authenticate with the LDAP Server. It is "
            "highly recommended to enable SSL for securing the transported data."
        )

    # TODO: Only test master site?
    def is_relevant(self) -> bool:
        return bool([c for _cid, c in active_connections_() if c.type() == "ldap"])

    def execute(self) -> Iterator[ACSingleResult]:
        site_id = omd_site()
        for connection_id, connection in active_connections_():
            if connection.type() != "ldap":
                continue

            assert isinstance(connection, ldap.LDAPUserConnector)

            if connection.use_ssl():
                yield ACSingleResult(
                    state=ACResultState.OK,
                    text=_("%s: Uses SSL") % connection_id,
                    site_id=site_id,
                )

            else:
                yield ACSingleResult(
                    state=ACResultState.WARN,
                    text=_("%s: Not using SSL. Consider enabling it in the connection settings.")
                    % connection_id,
                    site_id=site_id,
                )


class ACTestLivestatusSecured(ACTest):
    def category(self) -> str:
        return ACTestCategories.security

    def title(self) -> str:
        return _("Livestatus encryption")

    def help(self) -> str:
        return _(
            "<p>In distributed setups Livestatus is used to transport the status information "
            "gathered in one site to the central site. Since Checkmk 1.6 it is natively "
            "possible and highly recommended to encrypt this Livestatus traffic.</p> "
            "<p>This can be enabled using the global setting "
            '<a href="wato.py?mode=edit_configvar&varname=site_livestatus_tcp">Access to Livestatus via TCP</a>. Before enabling this you should ensure that all your Livestatus clients '
            "are able to handle the SSL encrypted Livestatus communication. Have a look at "
            '<a href="werk.py?werk=7017">werk #7017</a> for further information.</p>'
        )

    def is_relevant(self) -> bool:
        cfg = ConfigDomainOMD().default_globals()
        return bool(cfg["site_livestatus_tcp"])

    def execute(self) -> Iterator[ACSingleResult]:
        site_id = omd_site()
        cfg = ConfigDomainOMD().default_globals()
        if not cfg["site_livestatus_tcp"]:
            yield ACSingleResult(
                state=ACResultState.OK,
                text=_("Livestatus network traffic is encrypted"),
                site_id=site_id,
            )
            return

        if not cfg["site_livestatus_tcp"]["tls"]:
            yield ACSingleResult(
                state=ACResultState.CRIT,
                text=_("Livestatus network traffic is unencrypted"),
                site_id=site_id,
            )


class ACTestNumberOfUsers(ACTest):
    def category(self) -> str:
        return ACTestCategories.performance

    def title(self) -> str:
        return _("Number of users")

    def help(self) -> str:
        return _(
            "<p>Having a large number of users configured in Checkmk may decrease the "
            "performance of the web GUI.</p>"
            "<p>It may be possible that you are using the LDAP sync to create the users. "
            "Please review the filter configuration of the LDAP sync. Maybe you can "
            "decrease the sync scope to get a smaller number of users.</p>"
        )

    def is_relevant(self) -> bool:
        return True

    def execute(self) -> Iterator[ACSingleResult]:
        site_id = omd_site()
        users = userdb.load_users()
        num_users = len(users)
        user_warn_threshold = 500

        if num_users <= user_warn_threshold:
            yield ACSingleResult(
                state=ACResultState.OK,
                text=_("You have %d users configured") % num_users,
                site_id=site_id,
            )
        else:
            yield ACSingleResult(
                state=ACResultState.WARN,
                text=_(
                    "You have %d users configured. Please review the number of "
                    "users you have configured in Checkmk."
                )
                % num_users,
                site_id=site_id,
            )


class ACTestHTTPSecured(ACTest):
    def category(self) -> str:
        return ACTestCategories.security

    def title(self) -> str:
        return _("Secure GUI (HTTP)")

    def help(self) -> str:
        return (
            _(
                "When using the regular HTTP protocol all data transfered between the Checkmk "
                "and the clients using the GUI is sent over the network in plain text (unencrypted). "
                "This includes the passwords users enter to authenticate with Checkmk and other "
                "sensitive information. It is highly recommended to enable SSL for securing the "
                "transported data."
            )
            + " "
            + _(
                'Please note that you have to set <tt>RequestHeader set X-Forwarded-Proto "https"</tt> in '
                "your system Apache configuration to tell the Checkmk GUI about the SSL setup."
            )
        )

    def is_relevant(self) -> bool:
        return True

    def execute(self) -> Iterator[ACSingleResult]:
        site_id = omd_site()
        if request.is_ssl_request:
            yield ACSingleResult(
                state=ACResultState.OK,
                text=_("Site is using HTTPS"),
                site_id=site_id,
            )
        else:
            yield ACSingleResult(
                state=ACResultState.WARN,
                text=_("Site is using plain HTTP. Consider enabling HTTPS."),
                site_id=site_id,
            )


class ACTestOldDefaultCredentials(ACTest):
    def category(self) -> str:
        return ACTestCategories.security

    def title(self) -> str:
        return _("Default credentials")

    def help(self) -> str:
        return _(
            "In versions prior to version 1.4.0 the first administrative user of the "
            "site was named <tt>omdadmin</tt> with the standard password <tt>omd</tt>. "
            "This test warns you in case the site uses these standard credentials. "
            "It is highly recommended to change this password."
        )

    def is_relevant(self) -> bool:
        return userdb.user_exists(UserId("omdadmin"))

    def execute(self) -> Iterator[ACSingleResult]:
        site_id = omd_site()
        if (
            htpasswd.HtpasswdUserConnector(
                {
                    "type": "htpasswd",
                    "id": "htpasswd",
                    "disabled": False,
                }
            ).check_credentials(UserId("omdadmin"), Password("omd"))
            == "omdadmin"
        ):
            yield ACSingleResult(
                state=ACResultState.CRIT,
                text=_(
                    "Found <tt>omdadmin</tt> with default password. "
                    "It is highly recommended to change this password."
                ),
                site_id=site_id,
            )
        else:
            yield ACSingleResult(
                state=ACResultState.OK,
                text=_("Found <tt>omdadmin</tt> using custom password."),
                site_id=site_id,
            )


class ACTestBackupConfigured(ACTest):
    def category(self) -> str:
        return ACTestCategories.reliability

    def title(self) -> str:
        return _("Backup configured")

    def help(self) -> str:
        return _(
            "A reliable backup ensures that your monitoring "
            "environment can be restored in case of data loss.<br><br>We recommend "
            'using the <a href="wato.py?mode=backup">Checkmk backup</a> '
            "feature to create a consistent backup "
            "of your running site.<br><br>Virtual machine snapshots alone are not "
            "sufficient, as they do not guarantee data consistency.<br>"
            "Similarly, third-party backup solutions may fail to capture a "
            "consistent state."
        )

    def is_relevant(self) -> bool:
        return True

    def execute(self) -> Iterator[ACSingleResult]:
        site_id = omd_site()
        n_configured_jobs = len(BackupConfig.load().jobs)
        if n_configured_jobs:
            yield ACSingleResult(
                state=ACResultState.OK,
                text=_("You have configured %d backup jobs") % n_configured_jobs,
                site_id=site_id,
            )
        else:
            yield ACSingleResult(
                state=ACResultState.WARN,
                text=_("There is no backup job configured"),
                site_id=site_id,
            )


class ACTestBackupNotEncryptedConfigured(ACTest):
    def category(self) -> str:
        return ACTestCategories.security

    def title(self) -> str:
        return _("Encrypt backups")

    def help(self) -> str:
        return _(
            "Please check whether or not your backups are stored securely. In "
            "case you are storing your backup on a storage system the storage may "
            "already be secure enough without extra backup encryption. But in "
            "some cases it may be a good idea to store the backup encrypted."
        )

    def is_relevant(self) -> bool:
        return True

    def execute(self) -> Iterator[ACSingleResult]:
        site_id = omd_site()
        for job in BackupConfig.load().jobs.values():
            if job.is_encrypted():
                yield ACSingleResult(
                    state=ACResultState.OK,
                    text=_('The job "%s" is encrypted') % job.title,
                    site_id=site_id,
                )
            else:
                yield ACSingleResult(
                    state=ACResultState.WARN,
                    text=_('There job "%s" is not encrypted') % job.title,
                    site_id=site_id,
                )


class ACTestEscapeHTMLDisabled(ACTest):
    def category(self) -> str:
        return ACTestCategories.security

    def title(self) -> str:
        return _("Escape HTML globally enabled")

    def help(self) -> str:
        return _(
            "By default, for security reasons, the GUI does not interpret any HTML "
            "code received from external sources, like service output or log messages. "
            "But there are specific reasons to deactivate this security feature. E.g. when "
            "you want to display the HTML output produced by a specific check plug-in. "
            "Disabling the escaping also allows the plug-in to execute not only HTML, but "
            "also Javascript code in the context of your browser. This makes it possible to "
            "execute arbitrary Javascript, even for injection attacks.<br>"
            "For this reason, you should only disable this for a small, very specific number of "
            "services, to be sure that not every random check plug-in is able to produce code "
            "which your browser interprets."
        )

    def is_relevant(self) -> bool:
        return True

    def execute(self) -> Iterator[ACSingleResult]:
        site_id = omd_site()
        if not self._get_effective_global_setting("escape_plugin_output"):
            yield ACSingleResult(
                state=ACResultState.CRIT,
                text=_(
                    "Please consider configuring the host or service rulesets "
                    '<a href="%s">Escape HTML in service output</a> or '
                    '<a href="%s">Escape HTML in host output</a> instead '
                    'of <a href="%s">disabling escaping globally</a>'
                )
                % (
                    "wato.py?mode=edit_ruleset&varname=extra_service_conf:_ESCAPE_PLUGIN_OUTPUT",
                    "wato.py?mode=edit_ruleset&varname=extra_host_conf:_ESCAPE_PLUGIN_OUTPUT",
                    "wato.py?mode=edit_configvar&varname=escape_plugin_output",
                ),
                site_id=site_id,
            )
        else:
            yield ACSingleResult(
                state=ACResultState.OK,
                text=_('Escaping is <a href="%s">enabled globally</a>')
                % "wato.py?mode=edit_configvar&varname=escape_plugin_output",
                site_id=site_id,
            )


class ABCACApacheTest(ACTest, abc.ABC):
    """Abstract base class for apache related tests"""

    def _get_number_of_idle_processes(self):
        apache_status = self._get_apache_status()

        for line in apache_status.split("\n"):
            if line.startswith("Scoreboard:"):
                scoreboard = line.split(": ")[1]
                return scoreboard.count(".")

        raise MKGeneralException("Failed to parse the score board")

    def _get_maximum_number_of_processes(self):
        apache_status = self._get_apache_status()

        for line in apache_status.split("\n"):
            if line.startswith("Scoreboard:"):
                scoreboard = line.split(": ")[1]
                return len(scoreboard)

        raise MKGeneralException("Failed to parse the score board")

    def _get_apache_status(self):
        cfg = ConfigDomainOMD().default_globals()
        url = "http://127.0.0.1:%s/server-status?auto" % cfg["site_apache_tcp_port"]

        response = requests.get(url, headers={"Accept": "text/plain"}, timeout=110)
        return response.text


class ACTestApacheNumberOfProcesses(ABCACApacheTest):
    def category(self) -> str:
        return ACTestCategories.performance

    def title(self) -> str:
        return _("Apache number of processes")

    def help(self) -> str:
        return _(
            "<p>The Apache has a number of maximum processes it may start in case of high "
            "load situations. These Apache processes may use a decent amount of memory, so "
            "you need to configure them in a way that your system can handle them without "
            "reaching out of memory situations.</p>"
            "<p>Please note that this value is only a rough estimation, because the memory "
            "usage of the Apache processes may vary with the requests being processed.</p>"
            "<p>Possible actions:<ul>"
            '<li>Change the <a href="wato.py?mode=edit_configvar&varname=apache_process_tuning">number of Apache processes</a></li>'
            "</ul>"
            "</p>"
            "<p>Once you have verified your settings, you can acknowledge this test. The "
            "test will not automatically turn to OK, because it can not exactly estimate "
            "the required memory needed by the Apache processes."
            "</p>"
        )

    def is_relevant(self) -> bool:
        return True

    def execute(self) -> Iterator[ACSingleResult]:
        process_limit = self._get_maximum_number_of_processes()
        average_process_size = self._get_average_process_size()

        estimated_memory_size = process_limit * (average_process_size * 1.2)

        yield ACSingleResult(
            state=ACResultState.WARN,
            text=_(
                "The Apache may start up to %d processes while the current "
                "average process size is %s. With these process limits the Apache may "
                "use up to %s RAM. Please ensure that your system is able to "
                "handle this."
            )
            % (
                process_limit,
                cmk.utils.render.fmt_bytes(average_process_size),
                cmk.utils.render.fmt_bytes(estimated_memory_size),
            ),
            site_id=omd_site(),
        )

    def _get_average_process_size(self):
        try:
            pid_file = cmk.utils.paths.omd_root / "tmp/apache/run/apache.pid"
            with pid_file.open(encoding="utf-8") as f:
                ppid = int(f.read())
        except (OSError, ValueError):
            raise MKGeneralException(_("Failed to read the Apache process ID"))

        sizes = []
        for pid in subprocess.check_output(
            ["ps", "--ppid", "%d" % ppid, "h", "o", "pid"]
        ).splitlines():
            sizes.append(self._get_process_size(pid))

        if not sizes:
            raise MKGeneralException(_("Failed to estimate the Apache process size"))

        return sum(sizes) / float(len(sizes))

    def _get_process_size(self, pid):
        # Summary line seems to be different on the supported distros
        # Ubuntu 17.10 (pmap from procps-ng 3.3.12):
        # mapped: 25036K    writeable/private: 2704K    shared: 28K
        # SLES12
        # 4020K writable-private, 102960K readonly-private, 1856K shared, and 636K referenced
        # SLES12SP3 (pmap using library of procps-ng 3.3.9)
        # 2784K writable-private, 21052K readonly-private, and 28K shared
        # CentOS 5.5 (pmap procps version 3.2.7)
        # mapped: 66176K    writeable/private: 548K    shared: 28K
        # CentOS 7 (pmap from procps-ng 3.3.10)
        # mapped: 115524K    writeable/private: 684K    shared: 28K
        summary_line = subprocess.check_output(["pmap", "-d", "%d" % int(pid)]).splitlines()[-1]

        parts = summary_line.split()
        if parts[1] == b"writable-private,":
            writable_private = parts[0]
        else:
            writable_private = parts[3]

        return int(writable_private[:-1]) * 1024.0


class ACTestApacheProcessUsage(ABCACApacheTest):
    def category(self) -> str:
        return ACTestCategories.performance

    def title(self) -> str:
        return _("Apache process usage")

    def help(self) -> str:
        return _(
            "The Apache has a number maximum processes it can start in case of high "
            "load situations. The usage of these processes should not be too high "
            "in normal situations. Otherwise, if all processes are in use, the "
            "users of the GUI might have to wait too long for a free process, which "
            "would result in a slow GUI."
        )

    def is_relevant(self) -> bool:
        return True

    def execute(self) -> Iterator[ACSingleResult]:
        total_slots = self._get_maximum_number_of_processes()
        open_slots = self._get_number_of_idle_processes()
        used_slots = total_slots - open_slots

        usage = float(used_slots) * 100 / total_slots

        usage_warn, usage_crit = 60, 90
        if usage >= usage_crit:
            state = ACResultState.CRIT
        elif usage >= usage_warn:
            state = ACResultState.WARN
        else:
            state = ACResultState.OK

        yield ACSingleResult(
            state=state,
            text=_(
                "%d of the configured maximum of %d processes have been started. This is a usage of %0.2f %%."
            )
            % (used_slots, total_slots, usage),
            site_id=omd_site(),
        )


class ACTestCheckMKHelperUsage(ACTest):
    def category(self) -> str:
        return ACTestCategories.performance

    def title(self) -> str:
        return _("Checkmk helper usage")

    def help(self) -> str:
        return _(
            # xgettext: no-python-format
            "<p>The Checkmk Micro Core uses Checkmk helper processes to execute "
            "the Checkmk and Checkmk Discovery services of the hosts monitored "
            "with Checkmk. There should always be enough helper processes to handle "
            "the configured checks.</p>"
            "<p>In case the helper pool is 100% used, checks will not be executed in "
            "time, the check latency will grow and the states are not up to date.</p>"
            "<p>Possible actions:<ul>"
            "<li>Check whether or not you can decrease check timeouts</li>"
            '<li>Check which checks / plug-ins are <a href="view.py?view_name=service_check_durations">consuming most helper process time</a></li>'
            '<li>Increase the <a href="wato.py?mode=edit_configvar&varname=cmc_fetcher_helpers">number of Checkmk helpers</a></li>'
            "</ul>"
            "</p>"
            "<p>But you need to be careful that you don't configure too many Checkmk "
            "check helpers, because they consume a lot of memory. Your system needs "
            "to be able to handle the memory demand for all of them at once. An additional "
            "problem is that the Checkmk helpers are initialized in parallel during startup "
            "of the Micro Core, which may cause load peaks when having "
            "a lot of Checkmk helper processes configured.</p>"
        )

    def is_relevant(self) -> bool:
        return self._uses_microcore()

    def execute(self) -> Iterator[ACSingleResult]:
        local_connection = LocalConnection()
        row = local_connection.query_row(
            "GET status\nColumns: helper_usage_checker average_latency_checker\n"
        )

        helper_usage_checker_percent = 100 * row[0]
        average_latency_checker = row[1]

        usage_warn, usage_crit = 85, 95
        if helper_usage_checker_percent >= usage_crit:
            state = ACResultState.CRIT
        elif helper_usage_checker_percent >= usage_warn:
            state = ACResultState.WARN
        else:
            state = ACResultState.OK

        yield ACSingleResult(
            state=state,
            text=_(
                "The current checker usage is %.2f%%. The checkers have an average latency of %.3fs."
            )
            % (helper_usage_checker_percent, average_latency_checker),
            site_id=omd_site(),
        )


class ACTestCheckMKFetcherUsage(ACTest):
    def category(self) -> str:
        return ACTestCategories.performance

    def title(self) -> str:
        return _("Checkmk fetcher usage")

    def help(self) -> str:
        return _(
            # xgettext: no-python-format
            "<p>The Checkmk Micro Core uses Checkmk fetcher processes to obtain data about "
            "the Checkmk and Checkmk Discovery services of the hosts monitored "
            "with Checkmk. There should always be enough fetcher processes to handle "
            "the configured checks just in time.</p>"
            "<p>In case the fetcher helper pool is 100% used, checks will not be executed in "
            "time, the check latency will grow and the states are not up to date.</p>"
            "<p>Possible actions:<ul>"
            "<li>Check whether or not you can decrease check timeouts</li>"
            '<li>Check which checks / plug-ins are <a href="view.py?view_name=service_check_durations">consuming most helper process time</a></li>'
            '<li>Increase the <a href="wato.py?mode=edit_configvar&varname=cmc_fetcher_helpers">number of Checkmk fetchers</a></li>'
            "</ul>"
            "</p>"
            "<p>But you need to be careful that you don't configure too many Checkmk "
            "fetcher helpers, because they consume resources. An additional "
            "problem is that the Checkmk fetchers are initialized in parallel during startup "
            "of the Micro Core, which may cause load peaks when having "
            "a lot of Checkmk helper processes configured.</p>"
        )

    def is_relevant(self) -> bool:
        return self._uses_microcore()

    def execute(self) -> Iterator[ACSingleResult]:
        site_id = omd_site()
        local_connection = LocalConnection()
        row = local_connection.query_row(
            "GET status\nColumns: helper_usage_fetcher average_latency_fetcher\n"
        )

        fetcher_usage_perc = 100 * row[0]
        fetcher_latency = row[1]

        usage_warn, usage_crit = 85, 95
        if fetcher_usage_perc >= usage_crit:
            state = ACResultState.CRIT
        elif fetcher_usage_perc >= usage_warn:
            state = ACResultState.WARN
        else:
            state = ACResultState.OK

        yield ACSingleResult(
            state=state,
            text=_(
                "The current fetcher usage is %.2f%%."
                " The checks have an average check latency of %.3fs."
            )
            % (fetcher_usage_perc, fetcher_latency),
            site_id=site_id,
        )

        # Only report this as warning in case the user increased the default helper configuration
        default_values = ABCConfigDomain.get_all_default_globals()
        if (
            self._get_effective_global_setting("cmc_fetcher_helpers")
            > default_values["cmc_fetcher_helpers"]
            and fetcher_usage_perc < 50
        ):
            yield ACSingleResult(
                state=ACResultState.WARN,
                text=_(
                    "The fetcher usage is below 50%, you may decrease the number of "
                    "fetchers to reduce the memory consumption."
                ),
                site_id=site_id,
            )


class ACTestCheckMKCheckerUsage(ACTest):
    def category(self) -> str:
        return ACTestCategories.performance

    def title(self) -> str:
        return _("Checkmk checker usage")

    def help(self) -> str:
        return _(
            # xgettext: no-python-format
            "<p>The Checkmk Micro Core uses Checkmk checker processes to execute "
            "the Checkmk and Checkmk Discovery services of the hosts monitored "
            "with Checkmk. There should always be enough helper processes to handle "
            "the configured checks.</p>"
            "<p>In case the checker helper pool is 100% used, checks will not be executed in "
            "time, the check latency will grow and the states are not up to date.</p>"
            "<p>Possible actions:<ul>"
            "<li>Check whether or not you can decrease check timeouts</li>"
            '<li>Check which checks / plug-ins are <a href="view.py?view_name=service_check_durations">consuming most helper process time</a></li>'
            '<li>Increase the <a href="wato.py?mode=edit_configvar&varname=cmc_checker_helpers">number of Checkmk checkers</a></li>'
            "</ul>"
            "</p>"
            "<p>But you need to be careful that you don't configure too many Checkmk "
            "checker helpers, because they consume a lot of memory. Your system has "
            "to be able to handle the memory demand for all of them at once. An additional "
            "problem is that the Checkmk helpers are initialized in parallel during startup "
            "of the Micro Core, which may cause load peaks when having "
            "a lot of Checkmk helper processes configured.</p>"
        )

    def is_relevant(self) -> bool:
        return self._uses_microcore()

    def execute(self) -> Iterator[ACSingleResult]:
        site_id = omd_site()
        local_connection = LocalConnection()
        row = local_connection.query_row(
            "GET status\nColumns: helper_usage_checker average_latency_fetcher\n"
        )

        checker_usage_perc = 100 * row[0]
        fetcher_latency = row[1]

        usage_warn, usage_crit = 85, 95
        if checker_usage_perc >= usage_crit:
            state = ACResultState.CRIT
        elif checker_usage_perc >= usage_warn:
            state = ACResultState.WARN
        else:
            state = ACResultState.OK

        yield ACSingleResult(
            state=state,
            text=_(
                "The current checker usage is %.2f%%. "
                "The checks have an average check latency of %.3fs."
            )
            % (checker_usage_perc, fetcher_latency),
            site_id=site_id,
        )

        # Only report this as warning in case the user increased the default helper configuration
        default_values = ABCConfigDomain.get_all_default_globals()
        if (
            self._get_effective_global_setting("cmc_checker_helpers")
            > default_values["cmc_checker_helpers"]
            and checker_usage_perc < 50
        ):
            yield ACSingleResult(
                state=ACResultState.WARN,
                text=_(
                    "The checker usage is below 50%, you may decrease the number of "
                    "checkers to reduce the memory consumption."
                ),
                site_id=site_id,
            )


class ACTestGenericCheckHelperUsage(ACTest):
    def category(self) -> str:
        return ACTestCategories.performance

    def title(self) -> str:
        return _("Check helper usage")

    def help(self) -> str:
        return _(
            # xgettext: no-python-format
            "<p>The Checkmk Micro Core uses generic check helper processes to execute "
            "the active check based services (e.g. check_http, check_...). There should "
            "always be enough helper processes to handle the configured checks.</p>"
            "<p>In case the helper pool is 100% used, checks will not be executed in "
            "time, the check latency will grow and the states are not up to date.</p>"
            "<p>Possible actions:<ul>"
            "<li>Check whether or not you can decrease check timeouts</li>"
            '<li>Check which checks / plug-ins are <a href="view.py?view_name=service_check_durations">consuming most helper process time</a></li>'
            '<li>Increase the <a href="wato.py?mode=edit_configvar&varname=cmc_check_helpers">number of check helpers</a></li>'
            "</ul>"
            "</p>"
        )

    def is_relevant(self) -> bool:
        return self._uses_microcore()

    def execute(self) -> Iterator[ACSingleResult]:
        site_id = omd_site()
        local_connection = LocalConnection()
        row = local_connection.query_row(
            "GET status\nColumns: helper_usage_generic average_latency_generic\n"
        )

        helper_usage_perc = 100 * row[0]
        check_latency_generic = row[1]

        usage_warn, usage_crit = 85, 95
        if helper_usage_perc >= usage_crit:
            state = ACResultState.CRIT
        elif helper_usage_perc >= usage_warn:
            state = ACResultState.WARN
        else:
            state = ACResultState.OK
        yield ACSingleResult(
            state=state,
            text=_("The current check helper usage is %.2f%%") % helper_usage_perc,
            site_id=site_id,
        )

        if check_latency_generic > 1:
            state = ACResultState.CRIT
        else:
            state = ACResultState.OK
        yield ACSingleResult(
            state=state,
            text=_("The active check services have an average check latency of %.3fs.")
            % (check_latency_generic),
            site_id=site_id,
        )


class ACTestSizeOfExtensions(ACTest):
    def category(self) -> str:
        return ACTestCategories.performance

    def title(self) -> str:
        return _("Size of extensions")

    def help(self) -> str:
        return _(
            "<p>In distributed setups it is possible to synchronize the "
            "extensions (MKPs and files in <tt>~/local/</tt>) to the slave sites. "
            "These files are synchronized on every replication with a slave site and "
            "can possibly slow down the synchronization in case the files are large. "
            "You could either disable the MKP sync or check whether or not you need "
            "all the extensions.</p>"
        )

    def is_relevant(self) -> bool:
        return has_wato_slave_sites() and self._replicates_mkps()

    def _replicates_mkps(self) -> bool:
        return any(site.get("replicate_mkps") for site in wato_slave_sites().values())

    def execute(self) -> Iterator[ACSingleResult]:
        size = self._size_of_extensions()
        if size > 100 * 1024 * 1024:
            state = ACResultState.CRIT
        else:
            state = ACResultState.OK

        yield ACSingleResult(
            state=state,
            text=_("Your extensions have a size of %s.") % cmk.utils.render.fmt_bytes(size),
            site_id=omd_site(),
        )

    def _size_of_extensions(self):
        return int(
            subprocess.check_output(["du", "-sb", "%s/local" % cmk.utils.paths.omd_root]).split()[0]
        )


class ACTestBrokenGUIExtension(ACTest):
    def category(self) -> str:
        return ACTestCategories.deprecations

    def title(self) -> str:
        return _("Broken GUI extensions")

    def help(self) -> str:
        return _(
            "Since 1.6.0i1 broken GUI extensions don't block the whole GUI initialization anymore. "
            "Instead of this, the errors are logged in <tt>var/log/web.log</tt>. In addition to this, "
            "the errors are displayed here."
        )

    def is_relevant(self) -> bool:
        return True

    def execute(self) -> Iterator[ACSingleResult]:
        site_id = omd_site()
        errors = cmk.gui.utils.get_failed_plugins()
        if not errors:
            yield ACSingleResult(
                state=ACResultState.OK,
                text=_("No broken extensions were found."),
                site_id=site_id,
            )

        for plugin_filepath, gui_part, plugin_file, error in errors:
            yield ACSingleResult(
                state=ACResultState.CRIT,
                text=_('Loading "%s/%s" failed: %s') % (gui_part, plugin_file, error),
                site_id=site_id,
                path=plugin_filepath,
            )


class ACTestESXDatasources(ACTest):
    def category(self) -> str:
        return ACTestCategories.deprecations

    def title(self) -> str:
        return _("The Checkmk agent is queried via the ESX datasource program")

    def help(self) -> str:
        return _(
            "The Checkmk agent is queried via the datasource program for ESX systems. "
            "This is option will be deleted in a future release. Please configure the "
            "host to contact the Checkmk agent and the configured datasource programs "
            "instead."
        )

    def _get_rules(self):
        collection = SingleRulesetRecursively.load_single_ruleset_recursively(
            RuleGroup.SpecialAgents("vsphere")
        )

        ruleset = collection.get(RuleGroup.SpecialAgents("vsphere"))
        return ruleset.get_rules()

    def is_relevant(self) -> bool:
        return self._get_rules()

    def execute(self) -> Iterator[ACSingleResult]:
        site_id = omd_site()
        all_rules_ok = True
        for folder, rule_index, rule in self._get_rules():
            vsphere_queries_agent = rule.value.get("direct") in ["agent", "hostsystem_agent"]
            if vsphere_queries_agent:
                all_rules_ok = False
                yield ACSingleResult(
                    state=ACResultState.CRIT,
                    text=_("Rule %d in Folder %s is affected") % (rule_index + 1, folder.title()),
                    site_id=site_id,
                )

        if all_rules_ok:
            yield ACSingleResult(
                state=ACResultState.OK,
                text=_("No configured rules are affected"),
                site_id=site_id,
            )


def _try_rel_path(site_id: SiteId, abs_path: Path) -> Path:
    try:
        return abs_path.relative_to(Path("/omd/sites", site_id))
    except ValueError:
        # Not a subpath, should not happen
        return abs_path


def _compute_deprecation_result(
    *,
    version: str,
    deprecated_version: str,
    removed_version: str,
    title_entity: str,
    title_api: str,
    site_id: SiteId,
    path: Path,
) -> ACSingleResult:
    base = Version.from_str(version).base
    deprecated_base = Version.from_str(deprecated_version).base
    removed_base = Version.from_str(removed_version).base
    assert base is not None
    assert removed_base is not None
    assert deprecated_base is not None
    assert removed_base > deprecated_base

    rel_path = _try_rel_path(site_id, path)

    if base > removed_base:
        return ACSingleResult(
            state=ACResultState.CRIT,
            text=_("%s uses an API (%s) which was removed in Checkmk %s (File: %s).")
            % (
                title_entity,
                title_api,
                removed_version,
                rel_path,
            ),
            site_id=site_id,
            path=path,
        )

    if base == removed_base:
        return ACSingleResult(
            state=ACResultState.CRIT,
            text=_(
                "%s uses an API (%s) which was marked as deprecated in"
                " Checkmk %s and is removed in Checkmk %s (File: %s)."
            )
            % (
                title_entity,
                title_api,
                deprecated_version,
                removed_version,
                rel_path,
            ),
            site_id=site_id,
            path=path,
        )

    if base > deprecated_base:
        return ACSingleResult(
            state=ACResultState.WARN,
            text=_(
                "%s uses an API (%s) which was marked as deprecated in"
                " Checkmk %s and will be removed in Checkmk %s (File: %s)."
            )
            % (
                title_entity,
                title_api,
                deprecated_version,
                removed_version,
                rel_path,
            ),
            site_id=site_id,
            path=path,
        )

    if base == deprecated_base:
        return ACSingleResult(
            state=ACResultState.WARN,
            text=_(
                "%s uses an API (%s) which is marked as deprecated in"
                " Checkmk %s and will be removed in Checkmk %s (File: %s)."
            )
            % (
                title_entity,
                title_api,
                deprecated_version,
                removed_version,
                rel_path,
            ),
            site_id=site_id,
            path=path,
        )

    return ACSingleResult(
        state=ACResultState.OK,
        text="",
        site_id=site_id,
        path=path,
    )


class ACTestDeprecatedRuleSets(ACTest):
    def category(self) -> str:
        return ACTestCategories.deprecations

    def title(self) -> str:
        return _("Deprecated rule sets")

    def help(self) -> str:
        return _(
            "These rule sets are configured in your site, but marked as deprecated. They still"
            " work, but need to be migrated to their successor or be removed before the update"
            " to the next major release. There should be a werk for each of these rules providing"
            " you with further information on what to do specifically."
        )

    def is_relevant(self) -> bool:
        return True

    def execute(self) -> Iterator[ACSingleResult]:
        site_id = omd_site()
        unknown_check_parameter_rule_sets = [
            f"{RuleGroupType.CHECKGROUP_PARAMETERS.value}:{r}"
            for r in find_unknown_check_parameter_rule_sets(debug=active_config.debug).result
        ]
        if deprecated_rule_sets := [
            r
            for r in AllRulesets.load_all_rulesets().get_rulesets().values()
            if r.is_deprecated()
            and r.num_rules()
            and r.name not in unknown_check_parameter_rule_sets
        ]:
            for rule_set in deprecated_rule_sets:
                yield ACSingleResult(
                    state=ACResultState.WARN,
                    text=_("Found configured rules of deprecated rule set %r.") % rule_set.name,
                    site_id=site_id,
                )
            return

        yield ACSingleResult(
            state=ACResultState.OK,
            text=_("No deprecated rule sets found."),
            site_id=site_id,
        )


class ACTestUnknownCheckParameterRuleSets(ACTest):
    def category(self) -> str:
        return ACTestCategories.deprecations

    def title(self) -> str:
        return _("Unknown check parameter rule sets")

    def help(self) -> str:
        return _(
            "These rule sets are configured in your site, but not used by any check plug-in."
            " There are two main reasons to have such rule sets configured:"
            "<ol>"
            "<li> Rule sets which were used by builtin check plugins that have been deprecated and"
            " removed in the past. These can be cleaned up without any negative side effect.</li>"
            "<li> Rule sets which belong to disabled or removed extension packages. If you plan to"
            " keep it removed, you can safely clean them up. In case the extension package was"
            " temporarily disabled, you may consider keeping the rule sets in place.</li>"
            "</ol>"
        )

    def is_relevant(self) -> bool:
        return True

    def execute(self) -> Iterator[ACSingleResult]:
        site_id = omd_site()
        if rule_sets := find_unknown_check_parameter_rule_sets(debug=active_config.debug).result:
            for rule_set in rule_sets:
                yield ACSingleResult(
                    state=ACResultState.WARN,
                    text=(
                        _("Found configured rules of unknown check parameter rule set %r.")
                        % rule_set
                    ),
                    site_id=site_id,
                )
            return

        yield ACSingleResult(
            state=ACResultState.OK,
            text=_("No unknown check parameter rule sets found."),
            site_id=site_id,
        )


class ACTestDeprecatedV1CheckPlugins(ACTest):
    def category(self) -> str:
        return ACTestCategories.deprecations

    def title(self) -> str:
        return _("Deprecated check plug-ins (v1)")

    def help(self) -> str:
        return _(
            "The check plug-in API for plug-ins in <tt>%s</tt> is removed."
            " Plug-in files in this folder are ignored."
            " Please migrate the plug-ins to the new API."
            " More information can be found in"
            " <a href='%s'>%s</a> and our"
            " <a href='%s'>User Guide</a>."
        ) % (
            "/".join(local_agent_based_plugins_dir.parts[-4:]),
            werk_reference_url(WerkReference.DECOMMISSION_V1_API),
            WerkReference.DECOMMISSION_V1_API.ref(),
            doc_reference_url(DocReference.DEVEL_CHECK_PLUGINS),
        )

    def _get_files(self) -> Sequence[Path]:
        try:
            return list(local_agent_based_plugins_dir.rglob("*.py"))
        except FileNotFoundError:
            return ()

    def is_relevant(self) -> bool:
        return True

    def execute(self) -> Iterator[ACSingleResult]:
        site_id = omd_site()
        if plugin_files := self._get_files():
            for plugin_filepath in plugin_files:
                yield _compute_deprecation_result(
                    version=__version__,
                    deprecated_version="2.3.0",
                    removed_version="2.4.0",
                    title_entity=_("Check plug-in"),
                    title_api="v1",
                    site_id=site_id,
                    path=plugin_filepath,
                )
            return

        yield ACSingleResult(
            state=ACResultState.OK,
            text=_("No check plug-ins using the deprecated API (v1)"),
            site_id=site_id,
        )


class ACTestDeprecatedCheckPlugins(ACTest):
    def category(self) -> str:
        return ACTestCategories.deprecations

    def title(self) -> str:
        return _("Deprecated check plug-ins (legacy)")

    def help(self) -> str:
        return _(
            "The check plug-in API for plug-ins in <tt>%s</tt> is deprecated."
            " Plug-in files in this folder are still considered, but the API they are using may change at any time without notice."
            " Please migrate the plug-ins to the new API."
            " More information can be found in our <a href='%s'>User Guide</a>."
        ) % (
            "/".join(local_checks_dir.parts[-4:]),
            doc_reference_url(DocReference.DEVEL_CHECK_PLUGINS),
        )

    def _get_files(self) -> Sequence[Path]:
        try:
            return list(local_checks_dir.iterdir())
        except FileNotFoundError:
            return []

    def is_relevant(self) -> bool:
        return True

    def execute(self) -> Iterator[ACSingleResult]:
        site_id = omd_site()
        if files := self._get_files():
            for plugin_filepath in files:
                yield _compute_deprecation_result(
                    version=__version__,
                    deprecated_version="2.3.0",
                    removed_version="2.4.0",
                    title_entity=_("Check plug-in"),
                    title_api=_("legacy"),
                    site_id=site_id,
                    path=plugin_filepath,
                )
            return

        yield ACSingleResult(
            state=ACResultState.OK,
            text=_("No check plug-ins using the deprecated API"),
            site_id=site_id,
        )


class ACTestDeprecatedInventoryPlugins(ACTest):
    def category(self) -> str:
        return ACTestCategories.deprecations

    def title(self) -> str:
        return _("Deprecated HW/SW Inventory plug-ins")

    def help(self) -> str:
        return _(
            "The old inventory plug-in API has been removed in Checkmk version 2.2."
            " Plug-in files in <tt>'%s'</tt> are ignored."
            " Please migrate the plug-ins to the new API."
        ) % str(local_inventory_dir)

    def _get_files(self) -> Sequence[Path]:
        try:
            return list(local_inventory_dir.iterdir())
        except FileNotFoundError:
            return []

    def is_relevant(self) -> bool:
        return True

    def execute(self) -> Iterator[ACSingleResult]:
        site_id = omd_site()
        if files := self._get_files():
            for plugin_filepath in files:
                yield _compute_deprecation_result(
                    version=__version__,
                    deprecated_version="2.1.0",
                    removed_version="2.2.0",
                    title_entity=_("HW/SW Inventory plug-in"),
                    title_api=_("legacy"),
                    site_id=site_id,
                    path=plugin_filepath,
                )
            return

        yield ACSingleResult(
            state=ACResultState.OK,
            text=_("No HW/SW Inventory plug-ins using the deprecated API"),
            site_id=site_id,
        )


class ACTestDeprecatedCheckManpages(ACTest):
    def category(self) -> str:
        return ACTestCategories.deprecations

    def title(self) -> str:
        return _("Deprecated check man pages")

    def help(self) -> str:
        return _(
            "Check man pages in <tt>'%s'</tt> are marked as 'deprecated'"
            " and will be ignored in future Checkmk versions"
            " (official deprecation timeline not decided yet)."
        ) % str(local_legacy_check_manpages_dir)

    def _get_files(self) -> Sequence[Path]:
        try:
            return list(local_legacy_check_manpages_dir.iterdir())
        except FileNotFoundError:
            return []

    def is_relevant(self) -> bool:
        return True

    def execute(self) -> Iterator[ACSingleResult]:
        site_id = omd_site()
        if files := self._get_files():
            for plugin_filepath in files:
                yield _compute_deprecation_result(
                    version=__version__,
                    deprecated_version="2.3.0",
                    removed_version="2.4.0",
                    title_entity=_("Check man page"),
                    title_api=_("legacy"),
                    site_id=site_id,
                    path=plugin_filepath,
                )
            return

        yield ACSingleResult(
            state=ACResultState.OK,
            text=_("No check man pages using the deprecated API"),
            site_id=site_id,
        )


def _walk(folder: Path) -> Iterator[Path]:
    for root, _dirs, files in os.walk(folder):
        for file in files:
            if (path := Path(root, file)).is_file() and path.suffix == ".py":
                yield path


class ACTestDeprecatedGUIExtensions(ACTest):
    def category(self) -> str:
        return ACTestCategories.deprecations

    def title(self) -> str:
        return _("Deprecated GUI extensions")

    def help(self) -> str:
        return _(
            "GUI extensions in <tt>'%s'</tt> are marked as 'deprecated'"
            " and will be ignored in future Checkmk versions"
            " (official deprecation timeline not decided yet)."
        ) % str(local_gui_plugins_dir)

    def _get_files(self) -> Sequence[Path]:
        try:
            return list(_walk(local_gui_plugins_dir))
        except FileNotFoundError:
            return []

    def is_relevant(self) -> bool:
        return True

    def execute(self) -> Iterator[ACSingleResult]:
        site_id = omd_site()
        if files := self._get_files():
            for plugin_filepath in files:
                yield ACSingleResult(
                    state=ACResultState.WARN,
                    text=(
                        _(
                            "GUI extension in %r uses an API which is marked as deprecated and may"
                            " not work anymore due to unknown imports or objects (File: %s)."
                        )
                        % (plugin_filepath.parent.name, _try_rel_path(site_id, plugin_filepath))
                    ),
                    site_id=site_id,
                    path=plugin_filepath,
                )
            return

        yield ACSingleResult(
            state=ACResultState.OK,
            text=_("No GUI extensions using the deprecated API"),
            site_id=site_id,
        )


class ACTestDeprecatedLegacyGUIExtensions(ACTest):
    def category(self) -> str:
        return ACTestCategories.deprecations

    def title(self) -> str:
        return _("Deprecated legacy GUI extensions")

    def help(self) -> str:
        return _(
            "Legacy GUI extensions in <tt>'%s'</tt> are marked as 'deprecated'"
            " and will be ignored in future Checkmk versions"
            " (official deprecation timeline not decided yet)."
        ) % str(local_web_dir)

    def _get_files(self) -> Sequence[Path]:
        try:
            return list(_walk(local_web_dir))
        except FileNotFoundError:
            return []

    def is_relevant(self) -> bool:
        return True

    def execute(self) -> Iterator[ACSingleResult]:
        site_id = omd_site()
        if files := self._get_files():
            for plugin_filepath in files:
                match plugin_filepath.parent.name:
                    case "metrics" | "perfometer":
                        yield _compute_deprecation_result(
                            version=__version__,
                            deprecated_version="2.3.0",
                            removed_version="2.4.0",
                            title_entity=(
                                _("Legacy GUI extension in %r") % plugin_filepath.parent.name
                            ),
                            title_api=_("legacy"),
                            site_id=site_id,
                            path=plugin_filepath,
                        )
                    case "wato":
                        yield _compute_deprecation_result(
                            version=__version__,
                            deprecated_version="2.4.0",
                            removed_version="2.5.0",
                            title_entity=(
                                _("Legacy GUI extension in %r") % plugin_filepath.parent.name
                            ),
                            title_api=_("legacy"),
                            site_id=site_id,
                            path=plugin_filepath,
                        )
                    case _:
                        yield ACSingleResult(
                            state=ACResultState.WARN,
                            text=(
                                _(
                                    "Legacy GUI extension in %r uses an API which is marked as"
                                    " deprecated and may not work anymore due to unknown imports or"
                                    " objects (File: %s)."
                                )
                                % (
                                    plugin_filepath.parent.name,
                                    _try_rel_path(site_id, plugin_filepath),
                                )
                            ),
                            site_id=site_id,
                            path=plugin_filepath,
                        )
            return

        yield ACSingleResult(
            state=ACResultState.OK,
            text=_("No legacy GUI extensions using the deprecated API"),
            site_id=site_id,
        )


class ACTestDeprecatedPNPTemplates(ACTest):
    def category(self) -> str:
        return ACTestCategories.deprecations

    def title(self) -> str:
        return _("Deprecated PNP templates")

    def help(self) -> str:
        return _(
            "PNP templates in <tt>'%s'</tt> are marked as 'deprecated'"
            " and will be ignored in future Checkmk versions"
            " (official deprecation timeline not decided yet)."
        ) % str(local_pnp_templates_dir)

    def _get_files(self) -> Sequence[Path]:
        try:
            return list(local_pnp_templates_dir.iterdir())
        except FileNotFoundError:
            return []

    def is_relevant(self) -> bool:
        return True

    def execute(self) -> Iterator[ACSingleResult]:
        site_id = omd_site()
        if files := self._get_files():
            for plugin_filepath in files:
                yield ACSingleResult(
                    state=ACResultState.CRIT,
                    text=_(
                        "PNP template uses an API which was removed in an ealier Checkmk version (File: %s)."
                    )
                    % _try_rel_path(site_id, plugin_filepath),
                    site_id=site_id,
                    path=plugin_filepath,
                )
            return

        yield ACSingleResult(
            state=ACResultState.OK,
            text=_("No PNP templates using the deprecated API"),
            site_id=site_id,
        )


def _site_is_using_livestatus_proxy(site_id):
    site_configs = site_management_registry["site_management"].load_sites()
    return site_configs[site_id].get("proxy") is not None


class ACTestUnexpectedAllowedIPRanges(ACTest):
    def category(self) -> str:
        return ACTestCategories.security

    def title(self) -> str:
        return _("Restricted address mismatch")

    def help(self) -> str:
        return _(
            "This check returns CRIT if the parameter <b>State in case of restricted address mismatch</b> "
            "in the ruleset <b>Checkmk Agent installation auditing</b> is configured and differs from "
            "states <b>WARN</b> (default) or <b>CRIT</b>. "
            "With the above setting you can overwrite the default service state. This will help "
            "you to reduce above warnings during the update process of your Checkmk sites "
            "and agents. "
            "We recommend to set this option only for the affected hosts as long as you "
            "monitor agents older than Checkmk 2.0. After updating them, you should change "
            "this setting back to it's original value. "
            "Background: With IP access lists you can control which servers are allowed to talk "
            "to these agents. Thus it's a security issue and should not be disabled or set to "
            "<b>OK</b> permanently."
        )

    def is_relevant(self) -> bool:
        return bool(self._get_rules())

    def execute(self) -> Iterator[ACSingleResult]:
        site_id = omd_site()
        rules = self._get_rules()
        if not rules:
            yield ACSingleResult(
                state=ACResultState.OK,
                text=_(
                    "No rule set <b>State in case of restricted address mismatch</b> is configured"
                ),
                site_id=site_id,
            )
            return

        for folder_title, rule_state in rules:
            yield ACSingleResult(
                state=ACResultState.CRIT,
                text=f"Rule in <b>{folder_title}</b> has value <b>{rule_state}</b>",
                site_id=site_id,
            )

    def _get_rules(self):
        ruleset = SingleRulesetRecursively.load_single_ruleset_recursively(
            RuleGroup.CheckgroupParameters("agent_update")
        ).get(RuleGroup.CheckgroupParameters("agent_update"))
        state_map = {0: "OK", 1: "WARN", 2: "CRIT", 3: "UNKNOWN"}
        return [
            (folder.title(), state_map[rule.value.get("restricted_address_mismatch", 1)])
            for folder, _rule_index, rule in ruleset.get_rules()
            if rule.value.get("restricted_address_mismatch", 1) not in (1, 2)
        ]


class ACTestCheckMKCheckerNumber(ACTest):
    def category(self) -> str:
        return ACTestCategories.performance

    def title(self) -> str:
        return _("Checkmk checker count")

    def help(self) -> str:
        return _(
            "The Checkmk Micro Core uses Checkmk checker processes to process the results "
            "from the Checkmk fetchers. Since the checker processes are not IO bound, they are "
            "most effective when each checker gets a dedicated CPU. Configuring more checkers than "
            "the number of available CPUs has a negative effect, because it increases "
            "the amount of context switches."
        )

    def is_relevant(self) -> bool:
        return self._uses_microcore()

    def execute(self) -> Iterator[ACSingleResult]:
        site_id = omd_site()
        try:
            num_cpu = multiprocessing.cpu_count()
        except NotImplementedError:
            yield ACSingleResult(
                state=ACResultState.OK,
                text=_("Cannot test. Unable to determine the number of CPUs on target system."),
                site_id=site_id,
            )
            return

        if self._get_effective_global_setting("cmc_checker_helpers") > num_cpu:
            yield ACSingleResult(
                state=ACResultState.WARN,
                text=_(
                    "Configuring more checkers than the number of available CPUs (%d) have "
                    "a detrimental effect, since they are not IO bound."
                )
                % num_cpu,
                site_id=site_id,
            )
            return

        yield ACSingleResult(
            state=ACResultState.OK,
            text=_("Number of Checkmk checkers is less than number of CPUs"),
            site_id=site_id,
        )
