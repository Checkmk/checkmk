#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import multiprocessing
import subprocess
from pathlib import Path
from typing import Iterator, Type

import requests
import urllib3  # type: ignore[import]

from livestatus import LocalConnection

from cmk.utils.site import omd_site
from cmk.utils.type_defs import UserId

import cmk.gui.plugins.userdb.htpasswd
import cmk.gui.plugins.userdb.ldap_connector as ldap
import cmk.gui.userdb as userdb
import cmk.gui.utils
import cmk.gui.watolib as watolib
from cmk.gui.exceptions import MKGeneralException
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import ConfigDomainOMD, SiteBackupJobs
from cmk.gui.plugins.watolib.utils import ABCConfigDomain
from cmk.gui.site_config import (
    get_site_config,
    has_wato_slave_sites,
    is_wato_slave_site,
    sitenames,
    wato_slave_sites,
)
from cmk.gui.watolib.analyze_configuration import (
    ac_test_registry,
    ACResult,
    ACResultCRIT,
    ACResultOK,
    ACResultWARN,
    ACTest,
    ACTestCategories,
)
from cmk.gui.watolib.global_settings import rulebased_notifications_enabled
from cmk.gui.watolib.sites import SiteManagementFactory

# Disable python warnings in background job output or logs like "Unverified
# HTTPS request is being made". We warn the user using analyze configuration.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@ac_test_registry.register
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
            "processes with the maximum parallel livestatus connections. Otherwise livestatus "
            "requests will be blocked by existing and possibly idle connections."
        )

    def is_relevant(self) -> bool:
        # This check is only executed on the central instance of multisite setups
        return len(sitenames()) > 1

    def execute(self) -> Iterator[ACResult]:
        for site_id in sitenames():
            site_config = get_site_config(site_id)
            for result in self._check_site(site_id, site_config):
                result.site_id = site_id
                yield result

    def _check_site(self, site_id, site_config):
        persist = site_config.get("persist", False)

        if persist and _site_is_using_livestatus_proxy(site_id):
            yield ACResultWARN(
                _(
                    "Persistent connections are nearly useless "
                    "with Livestatus Proxy Daemon. Better disable it."
                )
            )

        elif persist:
            # TODO: At least for the local site we could calculate this.
            #       Or should we get the apache config from the remote site via automation?
            yield ACResultWARN(
                _(
                    "Either disable persistent connections or "
                    "carefully review maximum number of Apache processes and "
                    "possible livestatus connections."
                )
            )

        else:
            yield ACResultOK(_("Is not using persistent connections."))


@ac_test_registry.register
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
        return len(sitenames()) > 1

    def execute(self) -> Iterator[ACResult]:
        for site_id in sitenames():
            for result in self._check_site(site_id):
                result.site_id = site_id
                yield result

    def _check_site(self, site_id):
        if _site_is_using_livestatus_proxy(site_id):
            yield ACResultOK(_("Site is using the Livestatus Proxy Daemon"))

        elif not is_wato_slave_site():
            yield ACResultWARN(
                _(
                    "The Livestatus Proxy is not only good for slave sites, "
                    "enable it for your master site"
                )
            )

        else:
            yield ACResultWARN(_("Use the Livestatus Proxy Daemon for your site"))


@ac_test_registry.register
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

    def execute(self) -> Iterator[ACResult]:
        local_connection = LocalConnection()
        site_status = local_connection.query_row(
            "GET status\n"
            "Columns: livestatus_usage livestatus_threads livestatus_active_connections livestatus_overflows_rate"
        )

        usage, threads, active_connections, overflows_rate = site_status

        # Microcore has an averaged usage pre-calculated. The Nagios core does not have this column.
        # Calculate a non averaged usage instead
        if usage is None:
            usage = float(active_connections) / float(threads)

        usage_perc = 100 * usage

        usage_warn, usage_crit = 80, 95
        if usage_perc >= usage_crit:
            cls: Type[ACResult] = ACResultCRIT
        elif usage_perc >= usage_warn:
            cls = ACResultWARN
        else:
            cls = ACResultOK

        yield cls(_("The current livestatus usage is %.2f%%") % usage_perc)
        yield cls(_("%d of %d connections used") % (active_connections, threads))

        # Only available with Microcore
        if overflows_rate is not None:
            yield cls(_("you have a connection overflow rate of %.2f/s") % overflows_rate)


@ac_test_registry.register
class ACTestTmpfs(ACTest):
    def category(self) -> str:
        return ACTestCategories.performance

    def title(self) -> str:
        return _("Temporary filesystem mounted")

    def help(self) -> str:
        return _(
            "<p>By default each Checkmk site has it's own temporary filesystem "
            "(a ramdisk) mounted to <tt>[SITE]/tmp</tt>. In case the mount is not "
            "possible Checkmk starts without this temporary filesystem.</p>"
            "<p>Even if this is possible, it is not recommended to use Checkmk this "
            "way because it may reduce the overall performance of Checkmk.</p>"
        )

    def is_relevant(self) -> bool:
        return True

    def execute(self) -> Iterator[ACResult]:
        if self._tmpfs_mounted(omd_site()):
            yield ACResultOK(_("The temporary filesystem is mounted"))
        else:
            yield ACResultWARN(
                _(
                    "The temporary filesystem is not mounted. Your installation "
                    "may work with degraded performance."
                )
            )

    def _tmpfs_mounted(self, site_id):
        # Borrowed from omd binary
        #
        # Problem here: if /omd is a symbolic link somewhere else,
        # then in /proc/mounts the physical path will appear and be
        # different from tmp_path. We just check the suffix therefore.
        path_suffix = "sites/%s/tmp" % site_id
        for line in Path("/proc/mounts").open(encoding="utf-8"):
            try:
                _device, mp, fstype, _options, _dump, _fsck = line.split()
                if mp.endswith(path_suffix) and fstype == "tmpfs":
                    return True
            except Exception:
                continue
        return False


@ac_test_registry.register
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
        return bool([c for _cid, c in userdb.active_connections() if c.type() == "ldap"])

    def execute(self) -> Iterator[ACResult]:
        for connection_id, connection in userdb.active_connections():
            if connection.type() != "ldap":
                continue

            assert isinstance(connection, ldap.LDAPUserConnector)

            if connection.use_ssl():
                yield ACResultOK(_("%s: Uses SSL") % connection_id)

            else:
                yield ACResultWARN(
                    _("%s: Not using SSL. Consider enabling it in the " "connection settings.")
                    % connection_id
                )


@ac_test_registry.register
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

    def execute(self) -> Iterator[ACResult]:
        cfg = ConfigDomainOMD().default_globals()
        if not cfg["site_livestatus_tcp"]:
            yield ACResultOK(_("Livestatus network traffic is encrypted"))
            return

        if not cfg["site_livestatus_tcp"]["tls"]:
            yield ACResultCRIT(_("Livestatus network traffic is unencrypted"))


@ac_test_registry.register
class ACTestNumberOfUsers(ACTest):
    def category(self) -> str:
        return ACTestCategories.performance

    def title(self) -> str:
        return _("Number of users")

    def help(self) -> str:
        return _(
            "<p>Having a large number of users configured in Checkmk may decrease the "
            "performance of the Web GUI.</p>"
            "<p>It may be possible that you are using the LDAP sync to create the users. "
            "Please review the filter configuration of the LDAP sync. Maybe you can "
            "decrease the sync scope to get a smaller number of users.</p>"
        )

    def is_relevant(self) -> bool:
        return True

    def execute(self) -> Iterator[ACResult]:
        users = userdb.load_users()
        num_users = len(users)
        user_warn_threshold = 500

        if num_users <= user_warn_threshold:
            yield ACResultOK(_("You have %d users configured") % num_users)
        else:
            yield ACResultWARN(
                _(
                    "You have %d users configured. Please review the number of "
                    "users you have configured in Checkmk."
                )
                % num_users
            )


@ac_test_registry.register
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

    def execute(self) -> Iterator[ACResult]:
        if request.is_ssl_request:
            yield ACResultOK(_("Site is using HTTPS"))
        else:
            yield ACResultWARN(_("Site is using plain HTTP. Consider enabling HTTPS."))


@ac_test_registry.register
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

    def execute(self) -> Iterator[ACResult]:
        if (
            cmk.gui.plugins.userdb.htpasswd.HtpasswdUserConnector({}).check_credentials(
                UserId("omdadmin"), "omd"
            )
            == "omdadmin"
        ):
            yield ACResultCRIT(
                _(
                    "Found <tt>omdadmin</tt> with default password. "
                    "It is highly recommended to change this password."
                )
            )
        else:
            yield ACResultOK(_("Found <tt>omdadmin</tt> using custom password."))


@ac_test_registry.register
class ACTestMknotifydCommunicationEncrypted(ACTest):
    def category(self) -> str:
        return ACTestCategories.security

    def title(self) -> str:
        return _("Encrypt notification daemon communication")

    def help(self) -> str:
        return _(
            "Since version 2.1 it is possible to encrypt the communication of the notification "
            "daemon with TLS. After an upgrade of an existing site incoming connections will still "
            "use plain text communication and outgoing connections will try to use TLS and fall "
            "back to plain text communication if the remote site does not support TLS. It is "
            "recommended to enforce TLS encryption as soon as all sites support it."
        )

    def is_relevant(self) -> bool:
        return True

    def execute(self) -> Iterator[ACResult]:
        only_encrypted = True
        config = self._get_effective_global_setting("notification_spooler_config")

        if (incoming := config.get("incoming", {})) and incoming.get("encryption") == "unencrypted":
            only_encrypted = False
            yield ACResultCRIT(
                _("Incoming connections on port %s communicate via plain text")
                % incoming["listen_port"]
            )

        for outgoing in config["outgoing"]:
            socket = f"{outgoing['address']}:{outgoing['port']}"
            if outgoing["encryption"] == "upgradable":
                only_encrypted = False
                yield ACResultWARN(
                    _("Encryption for %s is only used if it is enabled on the remote site") % socket
                )
            if outgoing["encryption"] == "unencrypted":
                only_encrypted = False
                yield ACResultCRIT(_("Plain text communication is enabled for %s") % socket)

        if only_encrypted:
            yield ACResultOK("Encrypted communication is enabled for all configured connections")


@ac_test_registry.register
class ACTestBackupConfigured(ACTest):
    def category(self) -> str:
        return ACTestCategories.reliability

    def title(self) -> str:
        return _("Backup configured")

    def help(self) -> str:
        return _(
            "<p>You should have a backup configured for being able to restore your "
            "monitoring environment in case of a data loss.<br>"
            "In case you a using a virtual machine as Checkmk server and perform snapshot based "
            "backups, you should be safe.</p>"
            "<p>In case you are using a 3rd party backup solution the backed up data may not be "
            "reliably backed up or not up-to-date in the moment of the backup.</p>"
            "<p>It is recommended to use the Checkmk backup to create a backup of the runnning "
            "site to be sure that the data is consistent. If you need to, you can then use "
            "the 3rd party tool to archive the Checkmk backups.</p>"
        )

    def is_relevant(self) -> bool:
        return True

    def execute(self) -> Iterator[ACResult]:
        jobs = SiteBackupJobs()
        if jobs.choices():
            yield ACResultOK(_("You have configured %d backup jobs") % len(jobs.choices()))
        else:
            yield ACResultWARN(_("There is no backup job configured"))


@ac_test_registry.register
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

    def execute(self) -> Iterator[ACResult]:
        jobs = SiteBackupJobs()
        for job in jobs.objects.values():
            if job.is_encrypted():
                yield ACResultOK(_('The job "%s" is encrypted') % job.title())
            else:
                yield ACResultWARN(_('There job "%s" is not encrypted') % job.title())


@ac_test_registry.register
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
            "you want to display the HTML output produced by a specific check plugin."
            "Disabling the escaping also allows the plugin to execute not only HTML, but "
            "also Javascript code in the context of your browser. This makes it possible to "
            "execute arbitrary Javascript, even for injection attacks.<br>"
            "For this reason, you should only disable this for a small, very specific number of "
            "services, to be sure that not every random check plugin is able to produce code "
            "which your browser interprets."
        )

    def is_relevant(self) -> bool:
        return True

    def execute(self) -> Iterator[ACResult]:
        if not self._get_effective_global_setting("escape_plugin_output"):
            yield ACResultCRIT(
                _(
                    "Please consider configuring the host or service rulesets "
                    '<a href="%s">Escape HTML in service output</a> or '
                    '<a href="%s">Escape HTML in host output</a> instead '
                    'of <a href="%s">disabling escaping globally</a>'
                )
                % (
                    "wato.py?mode=edit_ruleset&varname=extra_service_conf:_ESCAPE_PLUGIN_OUTPUT",
                    "wato.py?mode=edit_ruleset&varname=extra_host_conf:_ESCAPE_PLUGIN_OUTPUT",
                    "wato.py?mode=edit_configvar&varname=escape_plugin_output",
                )
            )
        else:
            yield ACResultOK(
                _('Escaping is <a href="%s">enabled globally</a>')
                % "wato.py?mode=edit_configvar&varname=escape_plugin_output"
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

        response = requests.get(url, headers={"Accept": "text/plain"})
        return response.text


@ac_test_registry.register
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

    def execute(self) -> Iterator[ACResult]:
        process_limit = self._get_maximum_number_of_processes()
        average_process_size = self._get_average_process_size()

        estimated_memory_size = process_limit * (average_process_size * 1.2)

        yield ACResultWARN(
            _(
                "The Apache may start up to %d processes while the current "
                "average process size is %s. With these process limits the Apache may "
                "use up to %s RAM. Please ensure that your system is able to "
                "handle this."
            )
            % (
                process_limit,
                cmk.utils.render.fmt_bytes(average_process_size),
                cmk.utils.render.fmt_bytes(estimated_memory_size),
            )
        )

    def _get_average_process_size(self):
        try:
            pid_file = cmk.utils.paths.omd_root / "tmp/apache/run/apache.pid"
            with pid_file.open(encoding="utf-8") as f:
                ppid = int(f.read())
        except (IOError, ValueError):
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


@ac_test_registry.register
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

    def execute(self) -> Iterator[ACResult]:
        total_slots = self._get_maximum_number_of_processes()
        open_slots = self._get_number_of_idle_processes()
        used_slots = total_slots - open_slots

        usage = float(used_slots) * 100 / total_slots

        usage_warn, usage_crit = 60, 90
        if usage >= usage_crit:
            cls: Type[ACResult] = ACResultCRIT
        elif usage >= usage_warn:
            cls = ACResultWARN
        else:
            cls = ACResultOK

        yield cls(
            _(
                "%d of the configured maximum of %d processes have been started. This is a usage of %0.2f %%."
            )
            % (used_slots, total_slots, usage)
        )


@ac_test_registry.register
class ACTestCheckMKHelperUsage(ACTest):
    def category(self) -> str:
        return ACTestCategories.performance

    def title(self) -> str:
        return _("Checkmk helper usage")

    def help(self) -> str:
        return _(
            # xgettext: no-python-format
            "<p>The Checkmk Microcore uses Checkmk helper processes to execute "
            "the Checkmk and Checkmk Discovery services of the hosts monitored "
            "with Checkmk. There should always be enough helper processes to handle "
            "the configured checks.</p>"
            "<p>In case the helper pool is 100% used, checks will not be executed in "
            "time, the check latency will grow and the states are not up to date.</p>"
            "<p>Possible actions:<ul>"
            "<li>Check whether or not you can decrease check timeouts</li>"
            '<li>Check which checks / plugins are <a href="view.py?view_name=service_check_durations">consuming most helper process time</a></li>'
            '<li>Increase the <a href="wato.py?mode=edit_configvar&varname=cmc_fetcher_helpers">number of Checkmk helpers</a></li>'
            "</ul>"
            "</p>"
            "<p>But you need to be careful that you don't configure too many Checkmk "
            "check helpers, because they consume a lot of memory. Your system needs "
            "to be able to handle the memory demand for all of them at once. An additional "
            "problem is that the Checkmk helpers are initialized in parallel during startup "
            "of the Microcore, which may cause load peaks when having "
            "a lot of Checkmk helper processes configured.</p>"
        )

    def is_relevant(self) -> bool:
        return self._uses_microcore()

    def execute(self) -> Iterator[ACResult]:
        local_connection = LocalConnection()
        row = local_connection.query_row(
            "GET status\nColumns: helper_usage_cmk average_latency_cmk\n"
        )

        helper_usage_perc = 100 * row[0]
        check_latecy_cmk = row[1]

        usage_warn, usage_crit = 85, 95
        if helper_usage_perc >= usage_crit:
            cls: Type[ACResult] = ACResultCRIT
        elif helper_usage_perc >= usage_warn:
            cls = ACResultWARN
        else:
            cls = ACResultOK

        yield cls(
            _(
                "The current Checkmk helper usage is %.2f%%. The Checkmk services have an "
                "average check latency of %.3fs."
            )
            % (helper_usage_perc, check_latecy_cmk)
        )


@ac_test_registry.register
class ACTestCheckMKFetcherUsage(ACTest):
    def category(self) -> str:
        return ACTestCategories.performance

    def title(self) -> str:
        return _("Checkmk fetcher usage")

    def help(self) -> str:
        return _(
            # xgettext: no-python-format
            "<p>The Checkmk Microcore uses Checkmk fetcher processes to obtain data about "
            "the Checkmk and Checkmk Discovery services of the hosts monitored "
            "with Checkmk. There should always be enough fetcher processes to handle "
            "the configured checks just in time.</p>"
            "<p>In case the fetcher helper pool is 100% used, checks will not be executed in "
            "time, the check latency will grow and the states are not up to date.</p>"
            "<p>Possible actions:<ul>"
            "<li>Check whether or not you can decrease check timeouts</li>"
            '<li>Check which checks / plugins are <a href="view.py?view_name=service_check_durations">consuming most helper process time</a></li>'
            '<li>Increase the <a href="wato.py?mode=edit_configvar&varname=cmc_fetcher_helpers">number of Checkmk fetchers</a></li>'
            "</ul>"
            "</p>"
            "<p>But you need to be careful that you don't configure too many Checkmk "
            "fetcher helpers, because they consume resources. An additional "
            "problem is that the Checkmk fetchers are initialized in parallel during startup "
            "of the Microcore, which may cause load peaks when having "
            "a lot of Checkmk helper processes configured.</p>"
        )

    def is_relevant(self) -> bool:
        return self._uses_microcore()

    def execute(self) -> Iterator[ACResult]:
        local_connection = LocalConnection()
        row = local_connection.query_row(
            "GET status\nColumns: helper_usage_fetcher average_latency_fetcher\n"
        )

        fetcher_usage_perc = 100 * row[0]
        fetcher_latency = row[1]

        usage_warn, usage_crit = 85, 95
        if fetcher_usage_perc >= usage_crit:
            cls: Type[ACResult] = ACResultCRIT
        elif fetcher_usage_perc >= usage_warn:
            cls = ACResultWARN
        else:
            cls = ACResultOK

        yield cls(
            _(
                "The current fetcher usage is %.2f%%."
                " The checks have an average check latency of %.3fs."
            )
            % (fetcher_usage_perc, fetcher_latency)
        )

        # Only report this as warning in case the user increased the default helper configuration
        default_values = ABCConfigDomain.get_all_default_globals()
        if (
            self._get_effective_global_setting("cmc_fetcher_helpers")
            > default_values["cmc_fetcher_helpers"]
            and fetcher_usage_perc < 50
        ):
            yield ACResultWARN(
                _(
                    "The fetcher usage is below 50%, you may decrease the number of "
                    "fetchers to reduce the memory consumption."
                )
            )


@ac_test_registry.register
class ACTestCheckMKCheckerUsage(ACTest):
    def category(self) -> str:
        return ACTestCategories.performance

    def title(self) -> str:
        return _("Checkmk checker usage")

    def help(self) -> str:
        return _(
            # xgettext: no-python-format
            "<p>The Checkmk Microcore uses Checkmk checker processes to execute "
            "the Checkmk and Checkmk Discovery services of the hosts monitored "
            "with Checkmk. There should always be enough helper processes to handle "
            "the configured checks.</p>"
            "<p>In case the checker helper pool is 100% used, checks will not be executed in "
            "time, the check latency will grow and the states are not up to date.</p>"
            "<p>Possible actions:<ul>"
            "<li>Check whether or not you can decrease check timeouts</li>"
            '<li>Check which checks / plugins are <a href="view.py?view_name=service_check_durations">consuming most helper process time</a></li>'
            '<li>Increase the <a href="wato.py?mode=edit_configvar&varname=cmc_checker_helpers">number of Checkmk checkers</a></li>'
            "</ul>"
            "</p>"
            "<p>But you need to be careful that you don't configure too many Checkmk "
            "checker helpers, because they consume a lot of memory. Your system has "
            "to be able to handle the memory demand for all of them at once. An additional "
            "problem is that the Checkmk helpers are initialized in parallel during startup "
            "of the Microcore, which may cause load peaks when having "
            "a lot of Checkmk helper processes configured.</p>"
        )

    def is_relevant(self) -> bool:
        return self._uses_microcore()

    def execute(self) -> Iterator[ACResult]:
        local_connection = LocalConnection()
        row = local_connection.query_row(
            "GET status\nColumns: helper_usage_checker average_latency_fetcher\n"
        )

        checker_usage_perc = 100 * row[0]
        fetcher_latency = row[1]

        usage_warn, usage_crit = 85, 95
        if checker_usage_perc >= usage_crit:
            cls: Type[ACResult] = ACResultCRIT
        elif checker_usage_perc >= usage_warn:
            cls = ACResultWARN
        else:
            cls = ACResultOK

        yield cls(
            _(
                "The current checker usage is %.2f%%. "
                "The checks have an average check latency of %.3fs."
            )
            % (checker_usage_perc, fetcher_latency)
        )

        # Only report this as warning in case the user increased the default helper configuration
        default_values = ABCConfigDomain.get_all_default_globals()
        if (
            self._get_effective_global_setting("cmc_checker_helpers")
            > default_values["cmc_checker_helpers"]
            and checker_usage_perc < 50
        ):
            yield ACResultWARN(
                _(
                    "The checker usage is below 50%, you may decrease the number of "
                    "checkers to reduce the memory consumption."
                )
            )


@ac_test_registry.register
class ACTestAlertHandlerEventTypes(ACTest):
    def category(self) -> str:
        return ACTestCategories.performance

    def title(self) -> str:
        return _("Alert handler: Don't handle all check executions")

    def help(self) -> str:
        return _(
            "In general it will result in a significantly increased load when alert handlers are "
            "configured to handle all check executions. It is highly recommended to "
            '<a href="wato.py?mode=edit_configvar&varname=alert_handler_event_types">disable '
            "this</a> in most cases."
        )

    def is_relevant(self) -> bool:
        return self._uses_microcore()

    def execute(self) -> Iterator[ACResult]:
        if "checkresult" in self._get_effective_global_setting("alert_handler_event_types"):
            yield ACResultCRIT(_("Alert handler are configured to handle all check execution."))
        else:
            yield ACResultOK(_("Alert handlers will handle state changes."))


@ac_test_registry.register
class ACTestGenericCheckHelperUsage(ACTest):
    def category(self) -> str:
        return ACTestCategories.performance

    def title(self) -> str:
        return _("Check helper usage")

    def help(self) -> str:
        return _(
            # xgettext: no-python-format
            "<p>The Checkmk Microcore uses generic check helper processes to execute "
            "the active check based services (e.g. check_http, check_...). There should "
            "always be enough helper processes to handle the configured checks.</p>"
            "<p>In case the helper pool is 100% used, checks will not be executed in "
            "time, the check latency will grow and the states are not up to date.</p>"
            "<p>Possible actions:<ul>"
            "<li>Check whether or not you can decrease check timeouts</li>"
            '<li>Check which checks / plugins are <a href="view.py?view_name=service_check_durations">consuming most helper process time</a></li>'
            '<li>Increase the <a href="wato.py?mode=edit_configvar&varname=cmc_check_helpers">number of check helpers</a></li>'
            "</ul>"
            "</p>"
        )

    def is_relevant(self) -> bool:
        return self._uses_microcore()

    def execute(self) -> Iterator[ACResult]:
        local_connection = LocalConnection()
        row = local_connection.query_row(
            "GET status\nColumns: helper_usage_generic average_latency_generic\n"
        )

        helper_usage_perc = 100 * row[0]
        check_latency_generic = row[1]

        usage_warn, usage_crit = 85, 95
        if helper_usage_perc >= usage_crit:
            cls: Type[ACResult] = ACResultCRIT
        elif helper_usage_perc >= usage_warn:
            cls = ACResultWARN
        else:
            cls = ACResultOK
        yield cls(_("The current check helper usage is %.2f%%") % helper_usage_perc)

        if check_latency_generic > 1:
            cls = ACResultCRIT
        else:
            cls = ACResultOK
        yield cls(
            _("The active check services have an average check latency of %.3fs.")
            % (check_latency_generic)
        )


@ac_test_registry.register
class ACTestSizeOfExtensions(ACTest):
    def category(self) -> str:
        return ACTestCategories.performance

    def title(self) -> str:
        return _("Size of extensions")

    def help(self) -> str:
        return _(
            "<p>In distributed WATO setups it is possible to synchronize the "
            "extensions (MKPs and files in <tt>~/local/</tt>) to the slave sites. "
            "These files are synchronized on every replication with a slave site and "
            "can possibly slow down the synchronization in case the files are large. "
            "You could either disable the MKP sync or check whether or not you need "
            "all the extensions.</p>"
        )

    def is_relevant(self) -> bool:
        return has_wato_slave_sites() and self._replicates_mkps()

    def _replicates_mkps(self):
        replicates_mkps = False
        for site in wato_slave_sites().values():
            if site.get("replicate_mkps"):
                replicates_mkps = True
                break

        if not replicates_mkps:
            return

    def execute(self) -> Iterator[ACResult]:
        size = self._size_of_extensions()
        if size > 100 * 1024 * 1024:
            cls: Type[ACResult] = ACResultCRIT
        else:
            cls = ACResultOK

        yield cls(_("Your extensions have a size of %s.") % cmk.utils.render.fmt_bytes(size))

    def _size_of_extensions(self):
        return int(
            subprocess.check_output(["du", "-sb", "%s/local" % cmk.utils.paths.omd_root]).split()[0]
        )


@ac_test_registry.register
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

    def execute(self) -> Iterator[ACResult]:
        errors = cmk.gui.utils.get_failed_plugins()
        if not errors:
            yield ACResultOK(_("No broken extensions were found."))

        for plugin_path, e in errors:
            yield ACResultCRIT(_('Loading "%s" failed: %s') % (plugin_path, e))


@ac_test_registry.register
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
        collection = watolib.SingleRulesetRecursively("special_agents:vsphere")
        collection.load()

        ruleset = collection.get("special_agents:vsphere")
        return ruleset.get_rules()

    def is_relevant(self) -> bool:
        return self._get_rules()

    def execute(self) -> Iterator[ACResult]:
        all_rules_ok = True
        for folder, rule_index, rule in self._get_rules():
            vsphere_queries_agent = rule.value.get("direct") in ["agent", "hostsystem_agent"]
            if vsphere_queries_agent:
                all_rules_ok = False
                yield ACResultCRIT(
                    _("Rule %d in Folder %s is affected") % (rule_index + 1, folder.title())
                )

        if all_rules_ok:
            yield ACResultOK(_("No configured rules are affected"))


@ac_test_registry.register
class ACTestRulebasedNotifications(ACTest):
    def category(self) -> str:
        return ACTestCategories.deprecations

    def title(self) -> str:
        return _("Flexible and plain email notifications")

    def help(self) -> str:
        return _(
            "Flexible and plain email notifications are considered deprecated in version 1.5.0 and "
            " will be removed in Checkmk version 1.6.0. Please consider to switch to rulebased "
            "notifications."
        )

    def is_relevant(self) -> bool:
        return True

    def execute(self) -> Iterator[ACResult]:
        if not rulebased_notifications_enabled():
            yield ACResultCRIT("Rulebased notifications are deactivated in the global settings")
        else:
            yield ACResultOK(_("Rulebased notifications are activated"))


def _site_is_using_livestatus_proxy(site_id):
    site_configs = SiteManagementFactory().factory().load_sites()
    return site_configs[site_id].get("proxy") is not None


@ac_test_registry.register
class ACTestUnexpectedAllowedIPRanges(ACTest):
    def category(self) -> str:
        return ACTestCategories.security

    def title(self) -> str:
        return _("Restricted address mismatch")

    def help(self) -> str:
        return _(
            "This check returns CRIT if the parameter <b>State in case of restricted address mismatch</b> "
            "in the ruleset <b>Status of the Checkmk services</b> is configured and differs from default "
            "state <b>WARN</b>. "
            "With the above setting you can overwrite the default service state. This will help "
            "you to reduce above warnings during the update process of your Checkmk sites "
            "and agents. "
            "We recommend to set this option only for the affected hosts as long as you "
            "monitor agents older than Checkmk 1.7. After updating them, you should change "
            "this setting back to it's original value. "
            "Background: With IP access lists you can control which servers are allowed to talk "
            "to these agents. Thus it's a security issue and should not be disabled or set to "
            "<b>OK</b> permanently."
        )

    def is_relevant(self) -> bool:
        return bool(self._get_rules())

    def execute(self) -> Iterator[ACResult]:
        rules = self._get_rules()
        if not bool(rules):
            yield ACResultOK(
                _("No ruleset <b>State in case of restricted address mismatch</b> is configured")
            )
            return

        for folder_title, rule_state in rules:
            yield ACResultCRIT("Rule in <b>%s</b> has value <b>%s</b>" % (folder_title, rule_state))

    def _get_rules(self):
        collection = watolib.SingleRulesetRecursively("check_mk_exit_status")
        collection.load()
        ruleset = collection.get("check_mk_exit_status")
        state_map = {0: "OK", 1: "WARN", 2: "CRIT", 3: "UNKNOWN"}
        return [
            (folder.title(), state_map[rule.value.get("restricted_address_mismatch", 1)])
            for folder, _rule_index, rule in ruleset.get_rules()
            if rule.value.get("restricted_address_mismatch") != "1"
        ]


@ac_test_registry.register
class ACTestCheckMKCheckerNumber(ACTest):
    def category(self) -> str:
        return ACTestCategories.performance

    def title(self) -> str:
        return _("Checkmk checker count")

    def help(self) -> str:
        return _(
            "The Checkmk Microcore uses Checkmk checker processes to process the results "
            "from the Checkmk fetchers. Since the checker processes are not IO bound, they are "
            "most effective when each checker gets a dedicated CPU. Configuring more checkers than "
            "the number of available CPUs has a negative effect, because it increases "
            "the amount of context switches."
        )

    def is_relevant(self) -> bool:
        return self._uses_microcore()

    def execute(self) -> Iterator[ACResult]:
        try:
            num_cpu = multiprocessing.cpu_count()
        except NotImplementedError:
            yield ACResultOK(
                _("Cannot test. Unable to determine the number of CPUs on target system.")
            )
            return

        if self._get_effective_global_setting("cmc_checker_helpers") > num_cpu:
            yield ACResultWARN(
                _(
                    "Configuring more checkers than the number of available CPUs (%d) have "
                    "a detrimental effect, since they are not IO bound."
                )
                % num_cpu
            )
            return

        yield ACResultOK(_("Number of Checkmk checkers is less than number of CPUs"))
