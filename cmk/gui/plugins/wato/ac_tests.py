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

import abc
import subprocess

import requests
import urllib3  # type: ignore

from livestatus import LocalConnection
import cmk.gui.utils
import cmk.gui.userdb as userdb
import cmk.gui.watolib as watolib
import cmk.gui.config as config
import cmk.gui.plugins.userdb.htpasswd
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.exceptions import MKGeneralException
from cmk.gui.watolib.sites import SiteManagementFactory

from cmk.gui.plugins.wato import (
    ACTestCategories,
    ACTest,
    ac_test_registry,
    ACResultCRIT,
    ACResultWARN,
    ACResultOK,
    ConfigDomainOMD,
    SiteBackupJobs,
)

# Disable python warnings in background job output or logs like "Unverified
# HTTPS request is being made". We warn the user using analyze configuration.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@ac_test_registry.register
class ACTestPersistentConnections(ACTest):
    def category(self):
        return ACTestCategories.performance

    def title(self):
        return _("Persistent connections")

    def help(self):
        return _(
            "Persistent connections may be a configuration to improve the performance of the GUI, "
            "but be aware that you really need to tune your system to make it work properly. "
            "When you have enabled persistent connections, the single GUI pages may use already "
            "established connections of the apache process. This saves the time that is needed "
            "for establishing the Livestatus connections. But you need to be aware that each "
            "apache process that is running is keeping a persistent connection to each configured "
            "site via Livestatus open. This means you need to balance the maximum apache "
            "processes with the maximum parallel livestatus connections. Otherwise livestatus "
            "requests will be blocked by existing and possibly idle connections.")

    def is_relevant(self):
        # This check is only executed on the central instance of multisite setups
        return len(config.sitenames()) > 1

    def execute(self):
        for site_id in config.sitenames():
            site_config = config.site(site_id)
            for result in self._check_site(site_id, site_config):
                result.site_id = site_id
                yield result

    def _check_site(self, site_id, site_config):
        persist = site_config.get("persist", False)

        if persist and _site_is_using_livestatus_proxy(site_id):
            yield ACResultWARN(
                _("Persistent connections are nearly useless "
                  "with Livestatus Proxy Daemon. Better disable it."))

        elif persist:
            # TODO: At least for the local site we could calculate this.
            #       Or should we get the apache config from the remote site via automation?
            yield ACResultWARN(
                _("Either disable persistent connections or "
                  "carefully review maximum number of apache processes and "
                  "possible livestatus connections."))

        else:
            yield ACResultOK(_("Is not using persistent connections."))


@ac_test_registry.register
class ACTestLiveproxyd(ACTest):
    def category(self):
        return "performance"

    def title(self):
        return _("Use Livestatus Proxy Daemon")

    def help(self):
        return _(
            "The Livestatus Proxy Daemon is available with the Check_MK Enterprise Edition "
            "and improves the management of the inter site connections using livestatus. Using "
            "the Livestatus Proxy Daemon improves the responsiveness and performance of your "
            "GUI and will decrease resource usage.")

    def is_relevant(self):
        # This check is only executed on the central instance of multisite setups
        return len(config.sitenames()) > 1

    def execute(self):
        for site_id in config.sitenames():
            for result in self._check_site(site_id):
                result.site_id = site_id
                yield result

    def _check_site(self, site_id):
        if _site_is_using_livestatus_proxy(site_id):
            yield ACResultOK(_("Site is using the Livestatus Proxy Daemon"))

        elif not watolib.is_wato_slave_site():
            yield ACResultWARN(
                _("The Livestatus Proxy is not only good for slave sites, "
                  "enable it for your master site"))

        else:
            yield ACResultWARN(_("Use the Livestatus Proxy Daemon for your site"))


@ac_test_registry.register
class ACTestLivestatusUsage(ACTest):
    def category(self):
        return ACTestCategories.performance

    def title(self):
        return _("Livestatus usage")

    def help(self):
        return _("<p>Livestatus is used by several components, for example the GUI, to gather "
                 "information about the monitored objects from the monitoring core. It is "
                 "very important for the overall performance of the monitoring system that "
                 "livestatus is a reliable and performant.</p>"
                 "<p>There should always be enough free livestatus slots to serve new "
                 "incoming queries.</p>"
                 "<p>You should never reach a livestatus usage of 100% for a longer time. "
                 "Consider increasing number of parallel livestatus connections or track down "
                 "the clients to check whether or not you can reduce the usage somehow.</p>")

    def is_relevant(self):
        return True

    def execute(self):
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
            cls = ACResultCRIT
        elif usage_perc >= usage_warn:
            cls = ACResultWARN
        else:
            cls = ACResultOK

        yield cls(_("The current livestatus usage is %.2f%%") % usage_perc)
        yield cls(_("%d of %d connections used") % (active_connections, threads))

        # Only available with Microcore
        if overflows_rate is not None:
            yield cls(_("You have a connection overflow rate of %.2f/s") % overflows_rate)


@ac_test_registry.register
class ACTestTmpfs(ACTest):
    def category(self):
        return ACTestCategories.performance

    def title(self):
        return _("Temporary filesystem mounted")

    def help(self):
        return _("<p>By default each Check_MK site has it's own temporary filesystem "
                 "(a ramdisk) mounted to <tt>[SITE]/tmp</tt>. In case the mount is not "
                 "possible Check_MK starts without this temporary filesystem.</p>"
                 "<p>Even if this is possible, it is not recommended to use Check_MK this "
                 "way because it may reduce the overall performance of Check_MK.</p>")

    def is_relevant(self):
        return True

    def execute(self):
        if self._tmpfs_mounted(config.omd_site()):
            yield ACResultOK(_("The temporary filesystem is mounted"))
        else:
            yield ACResultWARN(
                _("The temporary filesystem is not mounted. Your installation "
                  "may work with degraded performance."))

    def _tmpfs_mounted(self, site_id):
        # Borrowed from omd binary
        #
        # Problem here: if /omd is a symbolic link somewhere else,
        # then in /proc/mounts the physical path will appear and be
        # different from tmp_path. We just check the suffix therefore.
        path_suffix = "sites/%s/tmp" % site_id
        for line in file("/proc/mounts"):
            try:
                _device, mp, fstype, _options, _dump, _fsck = line.split()
                if mp.endswith(path_suffix) and fstype == 'tmpfs':
                    return True
            except Exception:
                continue
        return False


@ac_test_registry.register
class ACTestLDAPSecured(ACTest):
    def category(self):
        return ACTestCategories.security

    def title(self):
        return _("Secure LDAP")

    def help(self):
        return _("When using the regular LDAP protocol all data transfered between the Check_MK "
                 "and LDAP servers is sent over the network in plain text (unencrypted). This also "
                 "includes the passwords users enter to authenticate with the LDAP Server. It is "
                 "highly recommended to enable SSL for securing the transported data.")

    # TODO: Only test master site?
    def is_relevant(self):
        return bool([c for _cid, c in userdb.active_connections() if c.type() == "ldap"])

    def execute(self):
        for connection_id, connection in userdb.active_connections():
            if connection.type() != "ldap":
                continue

            if connection.use_ssl():
                yield ACResultOK(_("%s: Uses SSL") % connection_id)

            else:
                yield ACResultWARN(
                    _("%s: Not using SSL. Consider enabling it in the "
                      "connection settings.") % connection_id)


@ac_test_registry.register
class ACTestLivestatusSecured(ACTest):
    def category(self):
        return ACTestCategories.security

    def title(self):
        return _("Livestatus encryption")

    def help(self):
        return _(
            "<p>In distributed setups Livestatus is used to transport the status information "
            "gathered in one site to the central site. Since Check_MK 1.6 it is natively "
            "possible and highly recommended to encrypt this Livestatus traffic.</p> "
            "<p>This can be enabled using the global setting "
            "<a href=\"wato.py?mode=edit_configvar&varname=site_livestatus_tcp\">Access to Livestatus via TCP</a>. Before enabling this you should ensure that all your Livestatus clients "
            "are able to handle the SSL encrypted Livestatus communication. Have a look at "
            "<a href=\"werk.py?werk=7017\">werk #7017</a> for further information.</p>")

    def is_relevant(self):
        cfg = ConfigDomainOMD().default_globals()
        return bool(cfg["site_livestatus_tcp"])

    def execute(self):
        cfg = ConfigDomainOMD().default_globals()
        if not cfg["site_livestatus_tcp"]:
            yield ACResultOK(_("Livestatus network traffic is encrypted"))
            return

        if not cfg["site_livestatus_tcp"]["tls"]:
            yield ACResultCRIT(_("Livestatus network traffic is unencrypted"))


@ac_test_registry.register
class ACTestNumberOfUsers(ACTest):
    def category(self):
        return ACTestCategories.performance

    def title(self):
        return _("Number of users")

    def help(self):
        return _("<p>Having a large number of users configured in Check_MK may decrease the "
                 "performance of the Web GUI.</p>"
                 "<p>It may be possible that you are using the LDAP sync to create the users. "
                 "Please review the filter configuration of the LDAP sync. Maybe you can "
                 "decrease the sync scope to get a smaller number of users.</p>")

    def is_relevant(self):
        return True

    def execute(self):
        users = userdb.load_users()
        num_users = len(users)
        user_warn_threshold = 500

        if num_users <= user_warn_threshold:
            yield ACResultOK(_("You have %d users configured") % num_users)
        else:
            yield ACResultWARN(
                _("You have %d users configured. Please review the number of "
                  "users you have configured in Check_MK.") % num_users)


@ac_test_registry.register
class ACTestHTTPSecured(ACTest):
    def category(self):
        return ACTestCategories.security

    def title(self):
        return _("Secure GUI (HTTP)")

    def help(self):
        return \
            _("When using the regular HTTP protocol all data transfered between the Check_MK "
              "and the clients using the GUI is sent over the network in plain text (unencrypted). "
              "This includes the passwords users enter to authenticate with Check_MK and other "
              "sensitive information. It is highly recommended to enable SSL for securing the "
              "transported data.") \
            + " " \
            + _("Please note that you have to set <tt>RequestHeader set X-Forwarded-Proto \"https\"</tt> in "
                "your system apache configuration to tell the Checkmk GUI about the SSL setup.")

    def is_relevant(self):
        return True

    def execute(self):
        if html.request.is_ssl_request:
            yield ACResultOK(_("Site is using HTTPS"))
        else:
            yield ACResultWARN(_("Site is using plain HTTP. Consider enabling HTTPS."))


@ac_test_registry.register
class ACTestOldDefaultCredentials(ACTest):
    def category(self):
        return ACTestCategories.security

    def title(self):
        return _("Default credentials")

    def help(self):
        return _("In versions prior to version 1.4.0 the first administrative user of the "
                 "site was named <tt>omdadmin</tt> with the standard password <tt>omd</tt>. "
                 "This test warns you in case the site uses these standard credentials. "
                 "It is highly recommended to change this password.")

    def is_relevant(self):
        return userdb.user_exists("omdadmin")

    def execute(self):
        if cmk.gui.plugins.userdb.htpasswd.HtpasswdUserConnector({}).check_credentials(
                "omdadmin", "omd") == "omdadmin":
            yield ACResultCRIT(
                _("Found <tt>omdadmin</tt> with default password. "
                  "It is highly recommended to change this password."))
        else:
            yield ACResultOK(_("Found <tt>omdadmin</tt> using custom password."))


@ac_test_registry.register
class ACTestBackupConfigured(ACTest):
    def category(self):
        return ACTestCategories.reliability

    def title(self):
        return _("Backup configured")

    def help(self):
        return _(
            "<p>You should have a backup configured for being able to restore your "
            "monitoring environment in case of a data loss.<br>"
            "In case you a using a virtual machine as Check_MK server and perform snapshot based "
            "backups, you should be safe.</p>"
            "<p>In case you are using a 3rd party backup solution the backed up data may not be "
            "reliably backed up or not up-to-date in the moment of the backup.</p>"
            "<p>It is recommended to use the Check_MK backup to create a backup of the runnning "
            "site to be sure that the data is consistent. If you need to, you can then use "
            "the 3rd party tool to archive the Check_MK backups.</p>")

    def is_relevant(self):
        return True

    def execute(self):
        jobs = SiteBackupJobs()
        if jobs.choices():
            yield ACResultOK(_("You have configured %d backup jobs") % len(jobs.choices()))
        else:
            yield ACResultWARN(_("There is no backup job configured"))


@ac_test_registry.register
class ACTestBackupNotEncryptedConfigured(ACTest):
    def category(self):
        return ACTestCategories.security

    def title(self):
        return _("Encrypt backups")

    def help(self):
        return _("Please check whether or not your backups are stored securely. In "
                 "case you are storing your backup on a storage system the storage may "
                 "already be secure enough without extra backup encryption. But in "
                 "some cases it may be a good idea to store the backup encrypted.")

    def is_relevant(self):
        return True

    def execute(self):
        jobs = SiteBackupJobs()
        for job in jobs.objects.itervalues():
            if job.is_encrypted():
                yield ACResultOK(_("The job \"%s\" is encrypted") % job.title())
            else:
                yield ACResultWARN(_("There job \"%s\" is not encrypted") % job.title())


class ACApacheTest(ACTest):
    """Abstract base class for apache related tests"""
    __metaclass__ = abc.ABCMeta

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
class ACTestApacheNumberOfProcesses(ACApacheTest):
    def category(self):
        return ACTestCategories.performance

    def title(self):
        return _("Apache number of processes")

    def help(self):
        return _(
            "<p>The apache has a number maximum processes it can start in case of high "
            "load situations. These apache processes may use a decent amount of memory, so "
            "you need to configure them in a way that you system can handle them without "
            "reaching out of memory situations.</p>"
            "<p>Please note that this value is only a rough estimation, because the memory "
            "usage of the apache processes may vary with the requests being processed.</p>"
            "<p>Possible actions:<ul>"
            "<li>Change the <a href=\"wato.py?mode=edit_configvar&varname=apache_process_tuning\">number of apache processes</a></li>"
            "</ul>"
            "</p>"
            "<p>Once you have verified your settings, you can acknowledge this test. The "
            "test will not automatically turn to OK, because it can not exactly estimate "
            "the required memory needed by the apache processes."
            "</p>")

    def is_relevant(self):
        return True

    def execute(self):
        process_limit = self._get_maximum_number_of_processes()
        average_process_size = self._get_average_process_size()

        estimated_memory_size = process_limit * (average_process_size * 1.2)

        yield ACResultWARN(
            _("The apache may start up to %d processes while the current "
              "average process size is %s. With this numbers the apache may "
              "use up to %s RAM. Please ensure that your system is able to "
              "handle this.") % (process_limit, cmk.utils.render.fmt_bytes(average_process_size),
                                 cmk.utils.render.fmt_bytes(estimated_memory_size)))

    def _get_average_process_size(self):
        try:
            ppid = int(open("%s/tmp/apache/run/apache.pid" % cmk.utils.paths.omd_root).read())
        except (IOError, ValueError):
            raise MKGeneralException(_("Failed to read the apache process ID"))

        sizes = []
        for pid in subprocess.check_output(["ps", "--ppid",
                                            "%d" % ppid, "h", "o", "pid"]).splitlines():
            sizes.append(self._get_process_size(pid))

        if not sizes:
            raise MKGeneralException(_("Failed to estimate the apache process size"))

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
        if parts[1] == "writable-private,":
            writable_private = parts[0]
        else:
            writable_private = parts[3]

        return int(writable_private[:-1]) * 1024.0


@ac_test_registry.register
class ACTestApacheProcessUsage(ACApacheTest):
    def category(self):
        return ACTestCategories.performance

    def title(self):
        return _("Apache process usage")

    def help(self):
        return _("The apache has a number maximum processes it can start in case of high "
                 "load situations. The usage of these processes should not be too high "
                 "in normal situations. Otherwise, if all processes are in use, the "
                 "users of the GUI might have to wait too long for a free process, which "
                 "would result in a slow GUI.")

    def is_relevant(self):
        return True

    def execute(self):
        total_slots = self._get_maximum_number_of_processes()
        open_slots = self._get_number_of_idle_processes()
        used_slots = total_slots - open_slots

        usage = float(used_slots) * 100 / total_slots

        usage_warn, usage_crit = 60, 90
        if usage >= usage_crit:
            cls = ACResultCRIT
        elif usage >= usage_warn:
            cls = ACResultWARN
        else:
            cls = ACResultOK

        yield cls(
            _("%d of %d the configured maximum of processes are started. This is a usage of %0.2f %%."
             ) % (used_slots, total_slots, usage))


@ac_test_registry.register
class ACTestCheckMKHelperUsage(ACTest):
    def category(self):
        return ACTestCategories.performance

    def title(self):
        return _("Check_MK helper usage")

    def help(self):
        return _(
            "<p>The Check_MK Microcore uses Check_MK helper processes to execute "
            "the Check_MK and Check_MK Discovery services of the hosts monitored "
            "with Check_MK. There should always be enough helper processes to handle "
            "the configured checks.</p>"
            "<p>In case the helper pool is 100% used, checks will not be executed in "
            "time, the check latency will grow and the states are not up to date.</p>"
            "<p>Possible actions:<ul>"
            "<li>Check whether or not you can decrease check timeouts</li>"
            "<li>Check which checks / plugins are <a href=\"view.py?view_name=service_check_durations\">consuming most helper process time</a></li>"
            "<li>Increase the <a href=\"wato.py?mode=edit_configvar&varname=cmc_cmk_helpers\">number of Check_MK helpers</a></li>"
            "</ul>"
            "</p>"
            "<p>But you need to be careful that you don't configure too many Check_MK "
            "check helpers, because they consume a lot of memory. Your system needs "
            "to be able to handle the memory demand for all of them at once. An additional "
            "problem is that the Check_MK helpers are initialized in parallel during startup "
            "of the Microcore, which may cause load peaks when having "
            "a lot of Check_MK helper processes configured.</p>")

    def is_relevant(self):
        return self._uses_microcore()

    def execute(self):
        local_connection = LocalConnection()
        row = local_connection.query_row(
            "GET status\nColumns: helper_usage_cmk average_latency_cmk\n")

        helper_usage_perc = 100 * row[0]
        check_latecy_cmk = row[1]

        usage_warn, usage_crit = 85, 95
        if helper_usage_perc >= usage_crit:
            cls = ACResultCRIT
        elif helper_usage_perc >= usage_warn:
            cls = ACResultWARN
        else:
            cls = ACResultOK

        yield cls(
            _("The current Check_MK helper usage is %.2f%%. The Check_MK services have an "
              "average check latency of %.3fs.") % (helper_usage_perc, check_latecy_cmk))

        # Only report this as warning in case the user increased the default helper configuration
        default_values = watolib.ConfigDomain().get_all_default_globals()
        if self._get_effective_global_setting(
                "cmc_cmk_helpers") > default_values["cmc_cmk_helpers"] and helper_usage_perc < 50:
            yield ACResultWARN(
                _("The helper usage is below 50%, you may decrease the number of "
                  "Check_MK helpers to reduce the memory consumption."))


@ac_test_registry.register
class ACTestAlertHandlerEventTypes(ACTest):
    def category(self):
        return ACTestCategories.performance

    def title(self):
        return _("Alert handler: Don't handle all check executions")

    def help(self):
        return _(
            "In general it will result in a significantly increased load when alert handlers are "
            "configured to handle all check executions. It is highly recommended to "
            "<a href=\"wato.py?mode=edit_configvar&varname=alert_handler_event_types\">disable "
            "this</a> in most cases.")

    def is_relevant(self):
        return self._uses_microcore()

    def execute(self):
        if "checkresult" in self._get_effective_global_setting("alert_handler_event_types"):
            yield ACResultCRIT(_("Alert handler are configured to handle all check execution."))
        else:
            yield ACResultOK(_("Alert handlers will handle state changes."))


@ac_test_registry.register
class ACTestGenericCheckHelperUsage(ACTest):
    def category(self):
        return ACTestCategories.performance

    def title(self):
        return _("Check helper usage")

    def help(self):
        return _(
            "<p>The Check_MK Microcore uses generic check helper processes to execute "
            "the active check based services (e.g. check_http, check_...). There should "
            "always be enough helper processes to handle the configured checks.</p>"
            "<p>In case the helper pool is 100% used, checks will not be executed in "
            "time, the check latency will grow and the states are not up to date.</p>"
            "<p>Possible actions:<ul>"
            "<li>Check whether or not you can decrease check timeouts</li>"
            "<li>Check which checks / plugins are <a href=\"view.py?view_name=service_check_durations\">consuming most helper process time</a></li>"
            "<li>Increase the <a href=\"wato.py?mode=edit_configvar&varname=cmc_check_helpers\">number of check helpers</a></li>"
            "</ul>"
            "</p>")

    def is_relevant(self):
        return self._uses_microcore()

    def execute(self):
        local_connection = LocalConnection()
        row = local_connection.query_row(
            "GET status\nColumns: helper_usage_generic average_latency_generic\n")

        helper_usage_perc = 100 * row[0]
        check_latency_generic = row[1]

        usage_warn, usage_crit = 85, 95
        if helper_usage_perc >= usage_crit:
            cls = ACResultCRIT
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
            _("The active check services have an average check latency of %.3fs.") %
            (check_latency_generic))


@ac_test_registry.register
class ACTestSizeOfExtensions(ACTest):
    def category(self):
        return ACTestCategories.performance

    def title(self):
        return _("Size of extensions")

    def help(self):
        return _("<p>In distributed WATO setups it is possible to synchronize the "
                 "extensions (MKPs and files in <tt>~/local/</tt>) to the slave sites. "
                 "These files are synchronized on every replication with a slave site and "
                 "can possibly slow down the synchronization in case the files are large. "
                 "You could either disable the MKP sync or check whether or not you need "
                 "all the extensions.</p>")

    def is_relevant(self):
        return config.has_wato_slave_sites() and self._replicates_mkps()

    def _replicates_mkps(self):
        replicates_mkps = False
        for site in config.wato_slave_sites().itervalues():
            if site.get("replicate_mkps"):
                replicates_mkps = True
                break

        if not replicates_mkps:
            return

    def execute(self):
        size = self._size_of_extensions()
        if size > 100 * 1024 * 1024:
            cls = ACResultCRIT
        else:
            cls = ACResultOK

        yield cls(_("Your extensions have a size of %s.") % cmk.utils.render.fmt_bytes(size))

    def _size_of_extensions(self):
        return int(
            subprocess.check_output(["du", "-sb",
                                     "%s/local" % cmk.utils.paths.omd_root]).split()[0])


@ac_test_registry.register
class ACTestBrokenGUIExtension(ACTest):
    def category(self):
        return ACTestCategories.deprecations

    def title(self):
        return _("Broken GUI extensions")

    def help(self):
        return _(
            "Since 1.6.0i1 broken GUI extensions don't block the whole GUI initialization anymore. "
            "Instead of this, the errors are logged in <tt>var/log/web.log</tt>. In addition to this, "
            "the errors are displayed here.")

    def is_relevant(self):
        return True

    def execute(self):
        errors = cmk.gui.utils.get_failed_plugins()
        if not errors:
            yield ACResultOK(_("No broken extensions were found."))

        for plugin_path, e in errors:
            yield ACResultCRIT(_("Loading \"%s\" failed: %s") % (plugin_path, e))


@ac_test_registry.register
class ACTestESXDatasources(ACTest):
    def category(self):
        return ACTestCategories.deprecations

    def title(self):
        return _("The Check_MK agent is queried via the ESX datasource program")

    def help(self):
        return _("The Check_MK agent is queried via the datasource program for ESX systems. "
                 "This is option will be deleted in a future release. Please configure the "
                 "host to contact the Check_MK agent and the configured datasource programs "
                 "instead.")

    def _get_rules(self):
        collection = watolib.SingleRulesetRecursively('special_agents:vsphere')
        collection.load()

        ruleset = collection.get('special_agents:vsphere')
        return ruleset.get_rules()

    def is_relevant(self):
        return self._get_rules()

    def execute(self):
        all_rules_ok = True
        for folder, rule_index, rule in self._get_rules():
            vsphere_queries_agent = (rule.value.get('direct') in ['agent', 'hostsystem_agent'])
            if vsphere_queries_agent:
                all_rules_ok = False
                yield ACResultCRIT(
                    _("Rule %d in Folder %s is affected") % (rule_index + 1, folder.title()))

        if all_rules_ok:
            yield ACResultOK(_("No configured rules are affected"))


@ac_test_registry.register
class ACTestRulebasedNotifications(ACTest):
    def category(self):
        return ACTestCategories.deprecations

    def title(self):
        return _("Flexible and plain email notifications")

    def help(self):
        return _(
            "Flexible and plain email notifications are considered deprecated in version 1.5.0 and "
            " will be removed in Check_MK version 1.6.0. Please consider to switch to rulebased "
            "notifications.")

    def is_relevant(self):
        return True

    def execute(self):
        settings = watolib.load_configuration_settings()
        if settings['enable_rulebased_notifications'] != True:
            yield ACResultCRIT('Rulebased notifications are deactivated in the global settings')
        else:
            yield ACResultOK(_("Rulebased notifications are activated"))


def _site_is_using_livestatus_proxy(site_id):
    site_configs = SiteManagementFactory().factory().load_sites()
    return site_configs[site_id].get("proxy") is not None
