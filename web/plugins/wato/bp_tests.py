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

import requests


class BPTestPersistentConnections(BPTest):
    def category(self):
        return BPTestCategories.performance


    def title(self):
        return _("Persistent connections")


    def help(self):
        return _("Persistent connections may be a configuration to improve the performance of the GUI, "
                 "but be aware that you really need to tune your system to make it work properly. "
                 "When you have enabled persistent connections, the single GUI pages may use already "
                 "established connections of the apache process. This saves the time that is needed "
                 "for establishing the Livestatus connections. But you need to be aware that each "
                 "apache process that is running is keeping a persistent connection to each configured "
                 "site via Livestatus open. This means you need to balance the maximum apache "
                 "processes with the maximum parallel livestatus connections. Otherwise livestatus "
                 "requests will be blocked by existing and possibly idle connections.")


    def is_relevant(self):
        return True


    def execute(self):
        site_id = config.omd_site()
        site_config = config.site(site_id)
        persist = site_config.get("persist", False)

        if persist and site_is_using_livestatus_proxy(site_id):
            yield BPResultWARN(
                _("Persistent connections are nearly useless "
                  "with Livestatus Proxy Daemon. Better disable it."))

        elif persist:
            # TODO: At least for the local site we could calculate this.
            #       Or should we get the apache config from the remote site via automation?
            yield BPResultWARN(
                _("Either disable persistent connections or "
                  "carefully review maximum number of apache processes and "
                  "possible livestatus connections."))

        else:
            yield BPResultOK(_("Is not using persistent connections."))



class BPTestLivestatusUsage(BPTest):
    def category(self):
        return BPTestCategories.performance


    def title(self):
        return _("Livestatus usage")


    def help(self):
        return _("You should never reach a livestatus usage of 100% for a longer time. "
            "consider increasing number of parallel livestatus connections or track down "
            "the clients to check whether or not you can reduce the usage somehow.")


    def is_relevant(self):
        return True


    def execute(self):
        sites.live().set_only_sites([config.omd_site()])
        try:
            site_status = sites.live().query_row(
                "GET status\n"
                "Columns: livestatus_usage livestatus_threads livestatus_active_connections livestatus_overflows_rate"
            )
        finally:
            sites.live().set_only_sites()

        usage, threads, active_connections, overflows_rate = site_status

        number_txt = "(%d of %d connections used)" % (active_connections, threads)
        if usage > 90:
            yield BPResultWARN(_("The usage is %0.2f%% (above %0.2f%%), check "
                "the usage over time and possibly adapt configuration%s") % number_txt)

        if overflows_rate > 1:
            yield BPResultCRIT(_("%0.2f/s overflows occured. "
                "Clients need to wait for connections%s") % number_txt)



class BPTestLDAPSecured(BPTest):
    def category(self):
        return BPTestCategories.security


    def title(self):
        return _("Secure LDAP")


    def help(self):
        return _("When using the regular LDAP protocol all data transfered between the Check_MK "
            "and LDAP servers is sent over the network in plain text (unencrypted). This also "
            "includes the passwords users enter to authenticate with the LDAP Server. It is "
            "highly recommended to enable SSL for securing the transported data.")


    # TODO: Only test master site?
    def is_relevant(self):
        return bool([ c for cid, c in userdb.active_connections() if c.type() == "ldap" ])


    def execute(self):
        for connection_id, connection in userdb.active_connections():
            if connection.type() != "ldap":
                continue

            if connection.use_ssl():
                yield BPResultOK(_("%s: Uses SSL") % connection_id)

            else:
                yield BPResultWARN(_("%s: Not using SSL. Consider enabling it in the "
                    "connection settings.") % connection_id)



class BPTestNumberOfUsers(BPTest):
    def category(self):
        return BPTestCategories.performance


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
            yield BPResultOK(_("You have %d users configured") % num_users)
        else:
            yield BPResultWARN(_("You have %d users configured. Please review the number of "
                                 "users you have configured in Check_MK.") % num_users)



class BPTestHTTPSecured(BPTest):
    def category(self):
        return BPTestCategories.security


    def title(self):
        return _("Secure GUI (HTTP)")


    def help(self):
        return _("When using the regular HTTP protocol all data transfered between the Check_MK "
            "and the clients using the GUI is sent over the network in plain text (unencrypted). "
            "This includes the passwords users enter to authenticate with Check_MK and other "
            "sensitive information. It is highly recommended to enable SSL for securing the "
            "transported data.")


    def is_relevant(self):
        return True


    def execute(self):
        if html.is_ssl_request():
            yield BPResultOK(_("Site is using HTTPS"))
        else:
            yield BPResultWARN(_("Site is using plain HTTP. Consider enabling HTTPS."))



class BPTestBackupConfigured(BPTest):
    def category(self):
        return BPTestCategories.reliability


    def title(self):
        return _("Backup configured")


    def help(self):
        return _("<p>You should have a backup configured for being able to restore your "
                 "monitoring environment in case of a data loss.<br>"
                 "In case you a using a virtual machine as Check_MK server and perform snapshot based "
                 "backups, you should be safe.</p>"
                 "<p>In case you are using a 3rd party backup solution the backed up data may not be "
                 "reliably backed up or not up-to-date in the moment of the backup.</p>"
                 "<p>It is recommended to use the Check_MK backup to create a backup of the runnning "
                 "site to be sure that the data is consistent. If you need to, you can then use "
                 "the 4rd party tool to archive the Check_MK backups.</p>"),


    def is_relevant(self):
        return True


    def execute(self):
        jobs = SiteBackupJobs()
        if jobs.choices():
            yield BPResultOK(_("You have configured %d backup jobs") % len(jobs.choices()))
        else:
            yield BPResultWARN(_("There is no backup job configured"))



class BPTestBackupNotEncryptedConfigured(BPTest):
    def category(self):
        return BPTestCategories.security


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
        for job_ident, job in jobs.objects.items():
            if job.is_encrypted():
                yield BPResultOK(_("The job \"%s\" is encrypted") % job.title())
            else:
                yield BPResultWARN(_("There job \"%s\" is not encrypted") % job.title())



# Abstract base class for apache related tests
class BPApacheTest(object):
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
        config = ConfigDomainOMD().default_globals()
        url = "http://127.0.0.1:%s/server-status?auto" % config["APACHE_TCP_PORT"]

        response = requests.get(url, headers={"Accept" : "text/plain"})
        return response.text



class BPTestApacheNumberOfProcesses(BPTest, BPApacheTest):
    def category(self):
        return BPTestCategories.performance


    def title(self):
        return _("Apache number of processes")


    def help(self):
        return _("<p>The apache has a number maximum processes it can start in case of high "
                 "load situations. These apache processes may use a decent amount of memory, so "
                 "you need to configure them in a way that you system can handle them without "
                 "reaching out of memory situations.</p>"
                 "<p>Please note that this value is only a rough estimation, because the memory "
                 "usage of the apache processes may vary with the requests being processed.</p>")


    def is_relevant(self):
        return True


    def execute(self):
        process_limit = self._get_maximum_number_of_processes()
        average_process_size = self._get_average_process_size()

        estimated_memory_size = process_limit * (average_process_size * 1.2)

        yield BPResultWARN(_("The apache may start up to %d processes while the current "
                             "average process size is %s. With this numbers the apache may "
                             "use up to %s RAM. Please ensure that your system is able to "
                             "handle this.") % (process_limit, cmk.render.bytes(average_process_size),
                                                cmk.render.bytes(estimated_memory_size)))


    def _get_average_process_size(self):
        try:
            ppid = int(open("%s/tmp/apache/run/apache.pid" % cmk.paths.omd_root).read())
        except IOError, ValueError:
            raise MKGeneralException(_("Failed to read the apache process ID"))

        sizes = []
        for pid in os.popen("ps --ppid %s h o pid" % ppid):
            summary_line = os.popen("pmap -d %d" % int(pid)).readlines()[-1]
            sizes.append(int(summary_line.split()[3][:-1])*1024.0)

        if not sizes:
            raise MKGeneralException(_("Failed to estimate the apache process size"))

        return sum(sizes) / float(len(sizes))



class BPTestApacheProcessUsage(BPTest, BPApacheTest):
    def category(self):
        return BPTestCategories.performance


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
        open_slots  = self._get_number_of_idle_processes()
        used_slots  = total_slots - open_slots

        usage = float(used_slots) * 100 / total_slots

        usage_warn, usage_crit = 60, 90
        if usage >= usage_crit:
            cls = BPResultCRIT
        elif usage >= usage_warn:
            cls = BPResultWARN
        else:
            cls = BPResultOK


        yield cls(_("%d of %d the configured maximum of processes are started. This is a usage of %0.2f %%.") %
                        (used_slots, total_slots, usage))



class BPTestLivestatusUsage(BPTest, BPApacheTest):
    def category(self):
        return BPTestCategories.performance


    def title(self):
        return _("Livestatus usage")


    def help(self):
        return _("<p>Livestatus is used by several components, for example the GUI, to gather "
                 "information about the monitored objects from the monitoring core. It is "
                 "very important for the overall performance of the monitoring system that "
                 "livestatus is a reliable and performant.</p>"
                 "<p>There should always be enough free livestatus slots to serve new "
                 "incoming queries.</p>")


    def is_relevant(self):
        return True


    def execute(self):
        local_connection = sites.livestatus.LocalConnection()
        row = local_connection.query_row(
            "GET status\nColumns: livestatus_usage livestatus_overflows_rate\n"
        )

        livestatus_usage_perc        = 100 * row[0]
        livestatus_overflows_per_sec = row[1]

        usage_warn, usage_crit = 80, 95
        if livestatus_usage_perc >= usage_crit:
            cls = BPResultCRIT
        elif livestatus_usage_perc >= usage_warn:
            cls = BPResultWARN
        else:
            cls = BPResultOK

        yield cls(_("The current livestatus usage is %.2f%%. You have a connection overflow "
                    "rate of %.2f/s.") % (livestatus_usage_perc, livestatus_overflows_per_sec))



class BPTestCheckMKHelperUsage(BPTest):
    def category(self):
        return BPTestCategories.performance


    def title(self):
        return _("Check_MK helper usage")


    def help(self):
        return _("<p>The Check_MK Microcore uses Check_MK helper processes to execute "
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
        return True


    def execute(self):
        local_connection = sites.livestatus.LocalConnection()
        row = local_connection.query_row(
            "GET status\nColumns: helper_usage_cmk average_latency_cmk\n"
        )

        helper_usage_perc = 100 * row[0]
        check_latecy_cmk  = row[1]

        usage_warn, usage_crit = 85, 95
        if helper_usage_perc >= usage_crit:
            cls = BPResultCRIT
        elif helper_usage_perc >= usage_warn:
            cls = BPResultWARN
        else:
            cls = BPResultOK

        yield cls(_("The current Check_MK helper usage is %.2f%%. The Check_MK services have an "
                    "average check latency of %.3fs.") % (helper_usage_perc, check_latecy_cmk))

        if helper_usage_perc < 50:
            yield BPResultWARN(_("The helper usage is below 50%, you may decrease the number of "
                                 "Check_MK helpers to reduce the memory consumption."))



class BPTestApacheNumberOfProcesses(BPTest, BPApacheTest):
    def category(self):
        return BPTestCategories.performance


    def title(self):
        return _("Apache number of processes")


    def help(self):
        return _("<p>The apache has a number maximum processes it can start in case of high "
                 "load situations. These apache processes may use a decent amount of memory, so "
                 "you need to configure them in a way that you system can handle them without "
                 "reaching out of memory situations.</p>"
                 "<p>Please note that this value is only a rough estimation, because the memory "
                 "usage of the apache processes may vary with the requests being processed.</p>")


    def is_relevant(self):
        return True


    def execute(self):
        process_limit = self._get_maximum_number_of_processes()
        average_process_size = self._get_average_process_size()

        estimated_memory_size = process_limit * (average_process_size * 1.2)

        yield BPResultWARN(_("The apache may start up to %d processes while the current "
                             "average process size is %s. With this numbers the apache may "
                             "use up to %s RAM. Please ensure that your system is able to "
                             "handle this.") % (process_limit, cmk.render.bytes(average_process_size),
                                                cmk.render.bytes(estimated_memory_size)))


    def _get_average_process_size(self):
        try:
            ppid = int(open("%s/tmp/apache/run/apache.pid" % cmk.paths.omd_root).read())
        except IOError, ValueError:
            raise MKGeneralException(_("Failed to read the apache process ID"))

        sizes = []
        for pid in os.popen("ps --ppid %s h o pid" % ppid):
            summary_line = os.popen("pmap -d %d" % int(pid)).readlines()[-1]
            sizes.append(int(summary_line.split()[3][:-1])*1024.0)

        if not sizes:
            raise MKGeneralException(_("Failed to estimate the apache process size"))

        return sum(sizes) / float(len(sizes))




class BPTestGenericCheckHelperUsage(BPTest):
    def category(self):
        return BPTestCategories.performance


    def title(self):
        return _("Check helper usage")


    def help(self):
        return _("<p>The Check_MK Microcore uses generic check helper processes to execute "
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
        return True


    def execute(self):
        local_connection = sites.livestatus.LocalConnection()
        row = local_connection.query_row(
            "GET status\nColumns: helper_usage_generic average_latency_generic\n"
        )

        helper_usage_perc = 100 * row[0]
        check_latency_generic  = row[1]

        usage_warn, usage_crit = 85, 95
        if helper_usage_perc >= usage_crit:
            cls = BPResultCRIT
        elif helper_usage_perc >= usage_warn:
            cls = BPResultWARN
        else:
            cls = BPResultOK
        yield cls(_("The current check helper usage is %.2f%%") % helper_usage_perc)

        if check_latency_generic > 1:
            cls = BPResultCRIT
        else:
            cls = BPResultOK
        yield cls(_("The active check services have an average check latency of %.3fs.") %
                                                                    (check_latency_generic))



class BPTestSizeOfExtensions(BPTest):
    def category(self):
        return BPTestCategories.performance


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
        return True
        return config.has_wato_slave_sites() and self._replicates_mkps()


    def _replicates_mkps(self):
        replicates_mkps = False
        for site_id, site in config.wato_slave_sites():
            if site.get("replicate_mkps"):
                replicates_mkps = True
                break

        if not replicates_mkps:
            return


    def execute(self):
        size = self._size_of_extensions()
        if size > 100*1024*1024:
            cls = BPResultCRIT
        else:
            cls = BPResultOK

        yield cls(_("Your extensions have a size of %s.") % cmk.render.bytes(size))


    def _size_of_extensions(self):
        return int(subprocess.check_output(["du", "-sb", "%s/local" % cmk.paths.omd_root]).split()[0])
