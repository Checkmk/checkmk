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

import config, re, pprint, time
import sites
import marshal
import md5
import copy
from lib import *
from log import logger
from cmk.regex import regex
import cmk
import multiprocessing

# Datastructures and functions needed before plugins can be loaded
loaded_with_language = False
compile_logger = logger.getChild("bi.compilation")

# Load all view plugins
def load_plugins(force):
    global loaded_with_language
    if loaded_with_language == current_language and not force:
        return

    config.declare_permission_section("bi", _("BI - Check_MK Business Intelligence"))
    config.declare_permission("bi.see_all",
        _("See all hosts and services"),
        _("With this permission set, the BI aggregation rules are applied to all "
        "hosts and services - not only those the user is a contact for. If you "
        "remove this permissions then the user will see incomplete aggregation "
        "trees with status based only on those items."),
        [ "admin", "guest" ])

    # This must be set after plugin loading to make broken plugins raise
    # exceptions all the time and not only the first time (when the plugins
    # are loaded).
    loaded_with_language = current_language

#      ____                _              _
#     / ___|___  _ __  ___| |_ __ _ _ __ | |_ ___
#    | |   / _ \| '_ \/ __| __/ _` | '_ \| __/ __|
#    | |__| (_) | | | \__ \ || (_| | | | | |_\__ \
#     \____\___/|_| |_|___/\__\__,_|_| |_|\__|___/
#

# type of rule parameters
SINGLE = 'single'
MULTIPLE = 'multi'

# possible aggregated states
MISSING = -2 # currently unused
PENDING = -1
OK = 0
WARN = 1
CRIT = 2
UNKNOWN = 3
UNAVAIL = 4

service_state_names = { OK:_("OK"), WARN:_("WARN"), CRIT:_("CRIT"), UNKNOWN:_("UNKNOWN"), PENDING:_("PENDING"), UNAVAIL:_("UNAVAILABLE")}
host_state_names = { 0:_("UP"), 1:_("DOWN"), 2:_("UNREACHABLE") }

AGGR_HOST  = 0
AGGR_MULTI = 1

# character that separates sites and hosts
SITE_SEP = '#'

#      ____                      _ _       _   _
#     / ___|___  _ __ ___  _ __ (_) | __ _| |_(_) ___  _ __
#    | |   / _ \| '_ ` _ \| '_ \| | |/ _` | __| |/ _ \| '_ \
#    | |__| (_) | | | | | | |_) | | | (_| | |_| | (_) | | | |
#     \____\___/|_| |_| |_| .__/|_|_|\__,_|\__|_|\___/|_| |_|
#                         |_|

# format of a node
# {
#     "type"     : NT_LEAF, NT_RULE, NT_REMAINING,
#     "reqhosts" : [ list of required hosts ],
#     "hidden"   : True if hidden
#
#     SPECIAL KEYS FOR NT_LEAF:
#     "host"     : host specification,
#     "service"  : service name, missing for leaf type HOST_STATE
#
#     SPECIAL KEYS FOR NT_RULE:
#     "title"    : title
#     "func"     : Name of aggregation function, e.g. "count!2!1"
#     "nodes"    : List of subnodes
# }

NT_LEAF = 1
NT_RULE = 2
NT_REMAINING = 3
NT_PLACEHOLDER = 4 # temporary dummy entry needed for REMAINING


# Global variables
g_cache = {}                  # per-user cache
g_bi_cache_manager    = None
g_bi_sitedata_manager = None
g_bi_job_manager      = None
g_services_items      = None

g_tree_cache = {}
g_config_information = None   # for invalidating cache after config change
did_compilation = False       # Is set to true if anything has been compiled


# Load the static configuration of all services and hosts (including tags)
# without state.
def load_services(only_hosts):
    global g_services, g_services_by_hostname
    g_services = {}
    g_services_by_hostname = {}

    # Create optional host filter
    filter_txt = 'Filter: custom_variable_names < _REALNAME\n' # drop summary hosts
    if only_hosts:
        # Only fetch the requested hosts
        host_filter = []
        for site, hostname in only_hosts:
            host_filter.append('Filter: name = %s\n' % hostname)
        filter_txt = ''.join(host_filter)
        filter_txt += "Or: %d\n" % len(host_filter)

    sites.live().set_prepend_site(True)
    sites.live().set_auth_domain('bi')

    data = sites.live().query(
        "GET hosts\n"
        +filter_txt+
        "Columns: name custom_variable_names custom_variable_values "
        "services childs parents alias\n"
        "Cache: reload\n"
    )
    sites.live().set_prepend_site(False)
    sites.live().set_auth_domain('read')

    for site, host, varnames, values, svcs, childs, parents, alias in data:
        vars = dict(zip(varnames, values))
        tags = vars.get("TAGS", "").split(" ")
        entry = (tags, svcs, childs, parents, alias)
        g_services[(site, host)] = entry
        g_services_by_hostname.setdefault(host, []).append((site, entry))

# Keep complete list of time stamps of configuration
# and start of each site. Unreachable sites are registered
# with 0.
def cache_needs_update():
    new_config_information = [tuple(config.modification_timestamps)]
    for site in sites.states().values():
        new_config_information.append(site.get("program_start", 0))

    if new_config_information != g_config_information:
        return new_config_information
    else:
        return False

def reset_cache_status():
    global did_compilation
    did_compilation = False
    global used_cache
    used_cache = False

# The sitestats are used to define the integrity of the currently used cache
# If file timestamps change -> Cache is invalid
# If there are more sites online than before -> Cache is invalid
# If there are less sites online than before -> No problem at all
def get_current_sitestats():
    # Filter relevant files which can affect the BI trees
    # Anything in ~/etc/check_mk/multisite.d/wato/, except bi.mk is irrelevant
    relevant_configuration_timestamps = []
    for entry in config.modification_timestamps:
        # ('/omd/sites/heute/etc/check_mk/multisite.d/wato/bi.mk', 1474548846.9708173)
        filename = os.path.basename(entry[0])
        if "multisite.d/wato/" in entry[0] and not filename == "bi.mk":
            continue
        else:
            relevant_configuration_timestamps.append(entry)

    current_world = {"timestamps":   relevant_configuration_timestamps,
                     "online_sites": set(),
                     "known_sites":  set()}

    # This request here is mandatory, since the sites.states() info might be outdated
    sites.live().set_prepend_site(True)
    result = sites.live().query("GET status\nColumns: program_start\nCache: reload")
    program_start_times = dict(result)
    sites.live().set_prepend_site(False)

    for site, values in sites.states().items():
        current_world["known_sites"].add((site, program_start_times.get(site, 0)))
        if values.get("state") == "online":
            current_world["online_sites"].add((site, program_start_times.get(site, 0)))

    return current_world

# TODO: do we need this?
def reused_compilation():
    return used_cache and not did_compilation

# Returns a sorted list of aggregation group names
def aggregation_groups():
    if config.bi_precompile_on_demand:
        migrate_bi_configuration() # convert bi_packs into legacy variables
        # on demand: show all configured groups
        group_names = set([])
        for aggr_def in config.aggregations + config.host_aggregations:
            if aggr_def[0].get("disabled"):
                continue

            if type(aggr_def[1]) == list:
                group_names.update(aggr_def[1])
            else:
                group_names.add(aggr_def[1])

        group_names = list(group_names)

    else:
        # classic mode: precompile all and display only groups with members
        compile_forest(config.user.id)
        group_names = list(set([ group for group, trees in g_tree_cache["forest"].items() if trees ]))

    return sorted(group_names, cmp = lambda a,b: cmp(a.lower(), b.lower()))

def log(*args):
    for idx, arg in enumerate(args):
        if type(arg) not in [ unicode, str ]:
            arg = pprint.pformat(arg)
        compile_logger.debug('BI: %s%s' % (idx > 5 and "\n" or "", arg))

def get_cache_dir():
    bi_cache_dir = cmk.paths.tmp_dir + "/bi_cache"
    try:
        os.makedirs(bi_cache_dir)
    except OSError, e:
        pass
    return bi_cache_dir


class JobWorker(object):
    def __init__(self):
        super(JobWorker, self).__init__()

    @staticmethod
    def run(jobs, site_data, mp_queue, mp_errors):
        new_data = {}
        for job in jobs:
            try:
                start_time = time.time()
                log("Compiling %r" % (job["id"],))
                new_data = JobWorker.compile_job(job["id"], job["info"], site_data)
                aggr_type, aggr_idx, groups = job["id"]
                log("Compilation finished %r - took %.3f sec" % (job["id"], time.time() - start_time))
            except Exception, e:
                log("MP-Worker Exception %s" % e)
                mp_errors.put("Aggregation error: %s" % e)
            finally:
                # Even in an error scenario we consider these hosts as compiled
                if job["id"][0] == AGGR_HOST:
                    new_data["compiled_hosts"] = job["info"]["queued_hosts"]

                mp_queue.put((job, new_data))


    # Does the compilation of one aggregation
    @staticmethod
    def compile_job(job, data, site_data):
        # This variable holds all newly found entries and is returned later on
        new_data = BICacheManager.empty_compiled_tree()
        aggr_type, aggr_idx, groups = job

        global g_services
        global g_services_items
        global g_services_by_hostname

        # Prepare service globals for this job
        if aggr_type == AGGR_MULTI:
            g_services             = site_data["services"]
            g_services_by_hostname = site_data["services_by_hostname"]
        else:
            # Single host aggregation. The data parameter contains the requested hosts
            g_services             = {}
            g_services_by_hostname = {}

            required_hosts = data["queued_hosts"]
            for key, values in site_data["services"].items():
                if key in required_hosts:
                    g_services[key] = values

            hostnames = map(lambda x: x[1], required_hosts)
            for key, values in site_data["services_by_hostname"].items():
                if key in hostnames:
                    g_services_by_hostname[key] = values

        g_services_items = g_services.items()

        log("Compiling aggregation %d/%d: %r with %d hosts" % (aggr_type, aggr_idx, groups, len(g_services_by_hostname)))
        enabled_aggregations = get_enabled_aggregations()

        # Check if the aggregation is still correct
        if aggr_idx >= len(enabled_aggregations):
            raise MKConfigError("Aggregation mismatch: Index error")

        aggr = enabled_aggregations[aggr_idx]
        if aggr[0] != aggr_type:
            raise MKConfigError("Aggregation type mismatch")

        aggr = aggr[1]
        aggr_groups = type(aggr[1]) == list and tuple(aggr[1]) or tuple([aggr[1]])
        if groups != aggr_groups:
            raise MKConfigError("Aggregation groups mismatch")

        aggr_options, aggr = aggr[0], aggr[1:]
        use_hard_states = aggr_options.get("hard_states")
        downtime_aggr_warn = aggr_options.get("downtime_aggr_warn")

        if len(aggr) < 3:
            raise MKConfigError(_("<h1>Invalid aggregation <tt>%s</tt></h1>"
                                  "Must have at least 3 entries (has %d)") % (aggr, len(aggr)))

        new_entries = compile_rule_node(aggr_type, aggr[1:], 0)

        for this_entry in new_entries:
            remove_empty_nodes(this_entry)
            this_entry["use_hard_states"] = use_hard_states
            this_entry["downtime_aggr_warn"] = downtime_aggr_warn

        new_entries = [ e for e in new_entries if len(e["nodes"]) > 0 ]

        # Generates a unique id for the given entry
        def get_hash(entry):
            return md5.md5(repr(entry) + repr(job)).hexdigest()

        for group in groups:
            new_entries_hash = map(get_hash, new_entries)
            if group not in new_data['forest']:
                new_data['forest'][group]     = new_entries
                new_data['forest_ref'][group] = new_entries_hash
            else:
                new_data['forest'][group]     += new_entries
                new_data['forest_ref'][group] += new_entries_hash

            # Update several global speed-up indices
            for aggr in new_entries:
                aggr_hash = get_hash(aggr)
                # There are better was to create the hash (frozenset(aggr.items()))
                new_data["aggr_ref"][aggr_hash] = aggr
                req_hosts = aggr["reqhosts"]

                # Aggregations by last part of title (assumed to be host name)
                name = aggr["title"].split()[-1]
                new_data["aggregations_by_hostname"].setdefault(name, []).append((group, aggr))
                new_data["aggregations_by_hostname_ref"].setdefault(name, []).append((group, aggr_hash))


                # All single-host aggregations looked up per host
                # Only process the aggregations of hosts which are mentioned in only_hosts
                if aggr_type == AGGR_HOST:
                    # In normal cases a host aggregation has only one req_hosts item, we could use
                    # index 0 here. But clusters (which are also allowed now) have all their nodes
                    # in the list of required nodes.
                    # Before the latest change this used the last item of the req_hosts. I think it
                    # would be better to register this for all hosts mentioned in req_hosts. Give it a try...
                    # ASSERT: len(req_hosts) == 1!
                    for host in req_hosts:
                        new_data["host_aggregations"].setdefault(host, []).append((group, aggr))
                        new_data["host_aggregations_ref"].setdefault(host, []).append((group, aggr_hash))

                # Also all other aggregations that contain exactly one hosts are considered to
                # be "single host aggregations"
                elif len(req_hosts) == 1:
                    new_data["host_aggregations"].setdefault(req_hosts[0], []).append((group, aggr))
                    new_data["host_aggregations_ref"].setdefault(req_hosts[0],[]).append((group, aggr_hash))

                # All aggregations containing a specific host
                for h in req_hosts:
                    new_data["affected_hosts"].setdefault(h, []).append((group, aggr))
                    new_data["affected_hosts_ref"].setdefault(h, []).append((group, aggr_hash))

                # All aggregations containing a specific service
                services = find_all_leaves(aggr)
                for s in services: # triples of site, host, service
                    new_data["affected_services"].setdefault(s, []).append((group, aggr))
                    new_data["affected_services_ref"].setdefault(s, []).append((group, aggr_hash))

        return new_data



# This class handles the fcntl-locking of one file
# There are multiple locking options:
# - shared access
# - exclusive access
# - blocking mode, waits for lock
# - nonblocking mode, tries to get lock
#   The has_lock(..) indicates if the locking attempt was successful
# Since this class has __enter__ and __exit__ functions its best use
# is in conjunction with a with-statement
class BILock(object):
    def __init__(self, filepath, shared = False, blocking = True):
        self._filepath = filepath
        self._blocking = blocking
        self._shared   = shared
        self._fd       = None

        super(BILock, self).__init__()


    def has_lock(self):
        return self._fd != None


    def __enter__(self):
        if not os.path.exists(self._filepath):
            file(self._filepath, "a+")

        lock_options = self._shared   and fcntl.LOCK_SH or fcntl.LOCK_EX
        lock_options = self._blocking and lock_options or (lock_options| fcntl.LOCK_NB)

        self._fd = os.open(self._filepath, os.O_RDONLY | os.O_CREAT, 0660)
        lock_info = []
        lock_info.append(self._shared and "SHARED" or "EXCLUSIVE")
        lock_info.append(self._blocking and "BLOCKING" or "NON-BLOCKING")
        log('BI: BILock %-2s %30s <<<%s>>>' % (self._fd, " ".join(lock_info), os.path.basename(self._filepath)))

        try:
            fcntl.flock(self._fd, lock_options)
        except IOError:
            # This should only happen with LOCK_NB
            log("Unable to get LOCK")
            os.close(self._fd)
            self._fd = None

        return self


    def __exit__(self, type, value, traceback):
        if self._fd:
            log('BI: BILock %-2s %30s <<<%s>>>' % ( self._fd, "RELEASE", os.path.basename(self._filepath)))
            fcntl.flock(self._fd, fcntl.LOCK_UN)
            os.close(self._fd)
            self._fd = None



def marshal_save_data(filepath, data):
    with file(filepath, "w") as the_file:
        marshal.dump(data, the_file)
        os.fsync(the_file.fileno())

def marshal_load_data(filepath):
    return marshal.load(file(filepath))



# This class allows you to load and save python data
# The data is always stored as marshaled data on disk
# This class also helps reducing diskio by keeping track
# if there is actually new data available on disk.
# When the disk data is unchanged it simply returns cached data
# Note  : Since the data is kept in cache it is not a good idea
#         to open huge files with it
# Note 2: Generally these files are never deleted, just overwritten
#         or truncated. This helps preserving any locked filedescriptor
class BICacheFile(object):
    def __init__(self, **kwargs):
        self._filepath            = kwargs.get("filepath")
        self._cached_data         = None
        self._filetime            = None

        try:
            file(self._filepath, "a")
        except IOError:
            pass

        super(BICacheFile, self).__init__()


    def clear_cache(self):
        log("Clearing caches %s" % self._filepath)
        self._cached_data = None


    def get_filepath(self):
        return self._filepath


    def has_new_data(self):
        try:
            filestats = os.stat(self._filepath)
            if filestats.st_size == 0:
                return False

            if not self._filetime:
                return True

            if self._filetime != filestats.st_mtime:
                return True

            return False

        except OSError:
            return False


    def load(self):
        try:
            filestats = os.stat(self._filepath)
            if filestats.st_size == 0:
                self._cached_data = None
                return None

            if (not self._filetime or self._filetime != filestats.st_mtime):
                with BILock(self._filepath, shared = True):
                    log("Loaded data from %s" % self._filepath)
                    self._cached_data = marshal_load_data(self._filepath)
                    self._filetime = filestats.st_mtime
            return self._cached_data
        except OSError:
            return None


    def save(self, data):
        with BILock(self._filepath):
            marshal_save_data(self._filepath, data)
            self._cached_data = data
            self._filetime = os.stat(self._filepath).st_mtime


    def truncate(self):
        log("Truncate %s" % self._filepath)
        with BILock(self._filepath):
            file(self._filepath, "w")
            self._cached_data = None
            self._filetime = os.stat(self._filepath).st_mtime



# This class contains all host and service data used for the compilation
# of an aggregation. It takes care of querying the data and tries to
# prevent reduntant livestatus calls by caching the data.
class BISitedataManager(object):
    def __init__(self):
        self._data_filepath_lock = "%s/bi_cache_data_LOCK" % get_cache_dir()

        self._reset_cached_data()

        # Housekeeping parameters
        self._clear_orphaned_caches_after  = 120 # Remove data files older than x seconds
        self._cache_update_interval        = 30  # Touch data files every x seconds when used

        super(BISitedataManager, self).__init__()


    def _reset_cached_data(self):
        # The actual processed data this class provides
        self._data             = {"services": {}, "services_by_hostname": {}}
        # Sites from which we have data
        self._have_sites       = set()
        # Cached all hosts info
        self._all_hosts_cached = None


    def discard_cached_data(self):
        self._reset_cached_data()


    def get_data(self):
        self._aquire_data()
        return self._data


    def get_all_hosts(self):
        self._aquire_data() # Updates the following value
        return self._all_hosts_cached


    def _get_sitedata_filepath(self, siteinfo):
        return "%s/bi_cache_data.%s.%s" % (get_cache_dir(), siteinfo[0], siteinfo[1])


    def _datafile_exists(self, siteinfo):
        filepath = self._get_sitedata_filepath(siteinfo)
        return os.path.exists(filepath) and os.stat(filepath).st_size > 0


    def _cleanup_orphaned_files(self):
        current_sitestats = get_current_sitestats()
        known_sites       = dict(current_sitestats.get("known_sites"))

        # Cleanup obsolete files
        for filename in os.listdir(get_cache_dir()):
            filepath = "%s/%s" % (get_cache_dir(), filename)
            if not filename.startswith("bi_cache_data."):
                continue

            try:
                rest, site, timestamp = filename.split(".", 2)
                timestamp = int(timestamp)

                if known_sites.get(site) == timestamp:
                    # Data still valid
                    continue

                # Delete obsolete data files older than 2 minutes
                if time.time() - os.stat(filepath).st_mtime > self._clear_orphaned_caches_after:
                    log("Cleanup orphaned file", filename)
                    os.unlink(filepath)
            except IndexError, IOError:
                try:
                    os.unlink(filepath)
                except:
                    pass


    def _query_data(self, only_sites):
        filter_txt = 'Filter: custom_variable_names < _REALNAME\n' # drop summary hosts
        try:
            sites.live().set_only_sites(only_sites)
            sites.live().set_prepend_site(True)
            sites.live().set_auth_domain('bi_all')

            data = sites.live().query(
                "GET hosts\n"
                +filter_txt+
                "Columns: name custom_variable_names custom_variable_values "
                "services childs parents alias\n"
                "Cache: reload\n"
            )
        finally:
            sites.live().set_auth_domain('read')
            sites.live().set_prepend_site(False)
            sites.live().set_only_sites(None)

        site_dict = {}
        for site, host, varnames, values, svcs, childs, parents, alias in data:
            vars = dict(zip(varnames, values))
            tags = vars.get("TAGS", "").split(" ")
            entry = (tags, svcs, childs, parents, alias)

            site_dict.setdefault(site, {"services": {}, "services_by_hostname": {}})
            site_dict[site]["services"][(site, host)] = entry
            site_dict[site]["services_by_hostname"].setdefault(host, []).append((site, entry))

        return site_dict


    def _get_missing_sites(self, online_sites):
        site_data_on_disk = set([])
        for siteinfo in online_sites:
            if self._datafile_exists(siteinfo):
                site_data_on_disk.add(siteinfo)
        return online_sites - site_data_on_disk


    def _absorb_sitedata(self, siteinfo, new_data):
        for key, values in new_data.items():
            self._data.setdefault(key, {})
            self._data[key].update(values)
        self._have_sites.add(siteinfo)
        log("Absorbed data %s/%s" % siteinfo)


    # Returns True if data was actuall queried
    def _query_missing_sitedata(self, online_sites):
        if not self._get_missing_sites(online_sites):
            return False

        with BILock(self._data_filepath_lock):
            # Only get the data if it is still not available..
            # An other lock might have taken care of
            missing_sites = self._get_missing_sites(online_sites)
            if missing_sites:
                cleanup_orphaned_files = True
                only_sites = [x[0] for x in missing_sites]
                new_data   = self._query_data(only_sites)

                sites_with_no_data = set(map(lambda x: x[0], missing_sites)) - set(new_data.keys())
                for site in sites_with_no_data:
                    new_data[site] = {}

                for site, sitedata in new_data.items():
                    # Write data to disk
                    siteinfo          = (site, dict(missing_sites).get(site))
                    sitedata_filepath = self._get_sitedata_filepath(siteinfo)
                    log("Saving datafile: %s" % os.path.basename(sitedata_filepath))
                    marshal_save_data(sitedata_filepath, sitedata)

                    # Add this data into the local cache, so there is no need
                    # to read it again from file in the following code block
                    if siteinfo not in self._have_sites:
                        self._absorb_sitedata(siteinfo, sitedata)
            return True


    def _read_missing_sitedata(self, online_sites):
        with BILock(self._data_filepath_lock, shared = True):
            for siteinfo in online_sites:
                if siteinfo in self._have_sites:
                    continue
                sitedata_filepath = self._get_sitedata_filepath(siteinfo)
                log("Loading datafile: %s" % os.path.basename(sitedata_filepath))
                site_data = marshal_load_data(sitedata_filepath)
                self._absorb_sitedata(siteinfo, site_data)

                # Touch this file to indicate it is still useful
                # Untouched data files older than 5 minutes will be removed by the cleanup function
                if time.time() - os.stat(sitedata_filepath).st_mtime > self._cache_update_interval:
                    try:
                        os.utime(sitedata_filepath, None)
                    except OSError:
                        pass


    # Returns True if new data was aquired
    def _aquire_data(self):
        online_sites = get_current_sitestats().get("online_sites")

        if online_sites == self._have_sites:
            return False

# TODO: check this, currently once read data is never discarded
#        if self._have_sites - online_sites:
#            # There is too much cached site data.
#            # Discard and reread cache. Can be optimized easily
#            self._reset_caches()

        # Query missing files returns True if it queried any data
        cleanup_orphaned_files = self._query_missing_sitedata(online_sites)

        self._read_missing_sitedata(online_sites)

        # The apache process which was responsible for the
        # data update also cleans up obsolete files
        if cleanup_orphaned_files:
            self._cleanup_orphaned_files()

        self._all_hosts_cached = set(self._data.get("services", {}).keys())

        return True



class BIJobManager(object):
    def __init__(self):
        super(BIJobManager, self).__init__()


    def _get_only_hosts_and_only_groups(self, aggr_ids, only_hosts, only_groups, all_hosts):
        all_groups = set([])
        for (aggr_type, idx, aggr_groups) in aggr_ids:
            all_groups.update(aggr_groups)

        if not only_hosts and not only_groups:
            # All aggregations
            required_hosts  = all_hosts
            required_groups = all_groups
        elif only_hosts and not only_groups:
            # All aggregations, Host aggregations not fully compiled
            required_hosts  = set(only_hosts)
            required_groups = all_groups
        elif not only_hosts and only_groups:
            # Aggregations filtered by group, all hosts
            required_hosts  = all_hosts
            required_groups = set(only_groups)
        else:
            # Explicit hosts and groups
            required_hosts  = set(only_hosts)
            required_groups = set(only_groups)

        return required_hosts, required_groups


    def get_missing_jobs(self, only_hosts, only_groups, all_hosts):
        jobs = {}
        aggr_ids = get_aggr_ids([AGGR_HOST, AGGR_MULTI])
        required_hosts, required_groups = self._get_only_hosts_and_only_groups(aggr_ids,
                                                                               only_hosts,
                                                                               only_groups,
                                                                               all_hosts)

        # Get involved aggregations and filter out already compiled aggregations
        compiled_trees = g_bi_cache_manager.get_compiled_trees()
        for aggr_id in aggr_ids:
            aggr_type, idx, aggr_groups = aggr_id

            # Filter out aggregations
            for group in required_groups:
                if group in aggr_groups:
                    break
            else:
                continue

            if aggr_type == AGGR_HOST:
                compiled_hosts = compiled_trees["compiled_host_aggr"].get(aggr_id, {}).get("compiled_hosts", set([]))
                missing_hosts  = required_hosts - compiled_hosts
                if missing_hosts:
                    jobs[aggr_id] = {"queued_hosts": missing_hosts}

            else:
                for group in required_groups:
                    if group in aggr_groups and aggr_id not in compiled_trees["compiled_multi_aggr"]:
                        jobs[aggr_id] = {"compiled": False}

        return jobs


    def _prepare_compilation(self, discard_old_cache=False):
        # Check if the currently known cache is worth keeping
        # The cache may have more, but not less than the required sites

        if discard_old_cache:
            log("#### CLEARING CACHEFILES ####")
            g_bi_cache_manager.truncate_cachefiles()  # Clears files
            g_bi_cache_manager.reset_cached_data() # Reset internal caches

        # Determine number of workers
        self._maximum_workers = multiprocessing.cpu_count()
        # Just in case the multiprocessing call is not working as intended
        if self._maximum_workers < 1:
            self._maximum_workers = 2

        # Multiprocessing queue for IPC
        self._mp_queue  = multiprocessing.Queue()
        self._mp_errors = multiprocessing.Queue()

        # Contains running worker jobs
        self._currently_compiling = []


    def _update_compilation_status(self):
        self._currently_compiling = [ t for t in self._currently_compiling if t.is_alive() ]

    def _is_compilation_finished(self):
        if not self._currently_compiling:
            log("Worker threads finished")
        return not self._currently_compiling


    def _start_workers(self):
        site_data = g_bi_sitedata_manager.get_data()
        import copy
        for x in range(self._maximum_workers):
            jobs = self._queued_jobs[x::self._maximum_workers]
            new_worker = multiprocessing.Process(target = JobWorker.run, args = [jobs, copy.deepcopy(site_data), self._mp_queue, self._mp_errors])
            new_worker.daemon = True
            self._currently_compiling.append(new_worker)
            self._currently_compiling[-1].start()
        self._queued_jobs = []


    def _reap_worker_results(self):
        results = []
        errors  = []
        while not self._mp_queue.empty():
            result = self._mp_queue.get()
            results.append(result)

        while not self._mp_errors.empty():
            error = self._mp_errors.get()
            errors.append(error)

        return results, errors


    def _merge_worker_results(self, results):
        if not results:
            return

        for job, new_data in results:
            g_bi_cache_manager._merge_compiled_data(job, new_data)

        g_bi_cache_manager.generate_cachefiles()


    def _compile_jobs_parallel(self):
        with BILock("%s/bi_cache_COMPILATION_LOCK" % get_cache_dir(), blocking = False) as compilation_lock:
            if not compilation_lock.has_lock():
                log("Did not get compilation lock")
                return False # Someone else is compiling


            # Check if the cache still requires a complete recompilation
            current_sitestats = get_current_sitestats()
            if g_bi_cache_manager.can_handle_sitestats(current_sitestats):
                g_bi_cache_manager.load_cachefile()
                return


            log("Do compilation, discarding old caches")
            self._queued_jobs = self._get_all_jobs()
            self._prepare_compilation(discard_old_cache = True)
            self._set_compilation_info(current_sitestats)

            error_info = ""
            self._start_workers()
            while True:
                if self._is_compilation_finished():
                    break

                self._update_compilation_status()

                # Collect results
                results, errors = self._reap_worker_results()
                error_info += "<br>".join(errors)

                # Update cache with new results
                self._merge_worker_results(results)


                # Allow the worker thread to compile their jobs
                time.sleep(0.2)

            try:
                check_title_uniqueness(g_bi_cache_manager.get_compiled_trees()["forest"])
            except MKConfigError, e:
                error_info += str(e)

            g_bi_cache_manager.get_compiled_trees()["compiled_all"] = True
            g_bi_cache_manager.generate_cachefiles(error_info = error_info)

        # Everything is compiled, clear cached data
        g_bi_sitedata_manager.discard_cached_data()
        g_bi_cache_manager.clear_cachefile_cache()
        return True # Did compilation


    def _get_all_jobs(self):
        jobs = []
        aggr_ids  = get_aggr_ids([AGGR_HOST, AGGR_MULTI])
        all_hosts = g_bi_sitedata_manager.get_all_hosts()

        for aggr_id in aggr_ids:
            aggr_type, idx, aggr_groups = aggr_id

            if aggr_type == AGGR_HOST:
                new_job = {"id": aggr_id, "info": {"queued_hosts": all_hosts}}
            else:
                new_job = {"id": aggr_id, "info": {"compiled": False}}
            jobs.append(new_job)

        return jobs


    # Returns True if compilation was done
    def compile_all_jobs(self):
        return self._compile_jobs_parallel()


    # Sets the information which is used during the compilation
    def _set_compilation_info(self, info):
        self._compilation_info = info


    # Returns the information which was using during the compilation
    def get_compilation_info(self):
        return self._compilation_info


class BICacheManager(object):
    def __init__(self):
        # Contains compiled trees
        self._bicache_file     = BICacheFile(filepath = "%s/bi_cache" % get_cache_dir())
        # Contains info about compiled trees (small file)
        self._bicacheinfo_file = BICacheFile(filepath = "%s_info" % self._bicache_file.get_filepath())
        self.reset_cached_data()

        super(BICacheManager, self).__init__()


    @staticmethod
    def empty_compiled_tree():
        return {
            "forest":                   {},
            "aggregations_by_hostname": {},
            "host_aggregations":        {},
            "affected_hosts":           {},
            "affected_services":        {},
            "compiled_host_aggr":       {},
            "compiled_multi_aggr":      {},

            # Parameters to slim the cache file
            "aggr_ref":                      {},
            "forest_ref":                    {},
            "aggregations_by_hostname_ref":  {},
            "host_aggregations_ref":         {},
            "affected_hosts_ref":            {},
            "affected_services_ref":         {},
        }


    # Resets everything the class knows of
    def reset_cached_data(self):
        # The actual compiled data
        self._compiled_trees = BICacheManager.empty_compiled_tree()
        self._bicache_file.clear_cache()
        self._bicacheinfo_file.clear_cache()


    # Clears just the cachefile cached data if it is no longer required (e.g. fully compiled)
    def clear_cachefile_cache(self):
        self._bicache_file.clear_cache()


    def get_error_info(self):
        cacheinfo_content = self.get_bicacheinfo()
        return (cacheinfo_content and cacheinfo_content.get("error_info", None)) or None


    def truncate_cachefiles(self):
        self._bicache_file.truncate()
        self._bicacheinfo_file.truncate()


    def get_online_sites(self):
        cacheinfo_content = self.get_bicacheinfo()
        return (cacheinfo_content and cacheinfo_content.get("compiled_sites", [])) or []


    def get_bicacheinfo(self):
        return self._bicacheinfo_file.load()


    def get_compiled_trees(self):
        return self._compiled_trees


    def can_handle_sitestats(self, new_sitestats):
        old_sitestats = self.get_bicacheinfo()

        if not old_sitestats:
            log("Old cache invalid: Old sitestats not available")
            return False

        # Check if the current online sites are at least a subset of the previously known
        # online sites. It doesn't matter if the world contains more information than we need
        if new_sitestats["online_sites"] - old_sitestats["compiled_sites"]:
            log("Old cache invalid: Cached aggregations were compiled for fewer sites, missing %r" % (
                new_sitestats["online_sites"] - old_sitestats["compiled_sites"]))
            return False

        if old_sitestats["compiled_sites"] - new_sitestats["online_sites"]:
            log("WORLD SHRINKS") # No problem at all

        if old_sitestats["timestamps"] != new_sitestats["timestamps"]:
            log("Old cache invalid: File timestamps differ")
            return False

        return True


    def load_cachefile(self, force_validation=False):
        log("--- Loading cachefile ---")
        if not self._bicache_file.has_new_data() and not force_validation:
            log("Not reading cachefile - does not have any new data")
            return True

        # Check if the file is worth loading
        # Invalidate known cache if the sitestats do not cope
        if not self.can_handle_sitestats(get_current_sitestats()):
            log("Load cachefile can not handle current sitestats - resetting known caches")
            self.reset_cached_data()
            return False

        if not self._bicache_file.has_new_data():
            log("Cachefile has no new data - Sitestats also valid")
            return True

        def reinstiate_references(cachefile_content):
            self._compiled_trees = cachefile_content
            self._compiled_trees["forest"] = {}

            for what in [ "aggregations_by_hostname", "host_aggregations", "affected_hosts", "affected_services" ]:
                self._compiled_trees[what] = {}
                for key, values in self._compiled_trees["%s_ref" % what].items():
                    self._compiled_trees[what].setdefault(key, [])
                    for value in values:
                        new_value = value
                        if type(value[1]) == str: # a reference
                            new_value = self._compiled_trees["aggr_ref"][value[1]]
                        self._compiled_trees[what][key].append((value[0], new_value))

            for key, values in self._compiled_trees["forest_ref"].items():
                self._compiled_trees["forest"][key] = []
                for aggr in values:
                    new_value = aggr
                    if type(aggr) == str:
                        new_value = self._compiled_trees["aggr_ref"][aggr]
                    self._compiled_trees["forest"][key].append(new_value)

        cachefile_content = self._bicache_file.load()
        if cachefile_content:
            reinstiate_references(cachefile_content)

        return True


    def generate_cachefiles(self, error_info=""):
        self._save_cacheinfofile(error_info = error_info)
        self._save_cachefile()


    def _save_cacheinfofile(self, error_info=""):
        old_compilation_info    = self.get_bicacheinfo()
        if not old_compilation_info:
            old_compiled_sites      = None
            old_compiled_timestamps = None
        else:
            old_compiled_sites      = old_compilation_info.get("compiled_sites")
            old_compiled_timestamps = old_compilation_info.get("timestamps")

        new_compilation_info    = g_bi_job_manager.get_compilation_info()
        new_compiled_timestamps = new_compilation_info.get("timestamps")
        # online_sites gets renamed to compiled_sites for the sake of clarity in the bicacheinfo file
        new_compiled_sites      = new_compilation_info.get("online_sites")

        # If timestamps differ the cache needs to be rewritten on the next update
        if old_compiled_timestamps and old_compiled_timestamps != new_compiled_timestamps:
            compiled_timestamps = []
        else:
            compiled_timestamps = new_compiled_timestamps

        # Make an intersection of the available sites
        if old_compiled_sites:
            compiled_sites = old_compiled_sites.intersection(new_compiled_sites)
        else:
            compiled_sites = new_compiled_sites

        content  = { "timestamps":          compiled_timestamps,
                     "compiled_sites":      compiled_sites,
                     "error_info":  error_info
                }

        self._bicacheinfo_file.save(content)


    def _save_cachefile(self):
        keys_for_cachefile = [
                              "aggr_ref",
                              "forest_ref",
                              "aggregations_by_hostname_ref",
                              "host_aggregations_ref",
                              "affected_hosts_ref",
                              "affected_services_ref",
                              "compiled_host_aggr",
                              "compiled_multi_aggr",
                              "compiled_all"
                              ]
        cache_to_dump = {}
        for what in keys_for_cachefile:
            cache_to_dump[what] = self._compiled_trees.get(what)

        start_time = time.time()
        self._bicache_file.save(cache_to_dump)
        log("SAVED CACHEFILE, took %.4f sec" % (time.time() - start_time))

    def get_compiled_all(self):
        info = self.get_compiled_trees()
        return (info and info.get("compiled_all", False)) or False


    def _merge_compiled_data(self, job, new_data):
        # Rendering related parameters
        for what in  [ "affected_hosts",
                       "affected_hosts_ref",
                       "aggregations_by_hostname",
                       "aggregations_by_hostname_ref",
                       "host_aggregations",
                       "host_aggregations_ref",
                       "affected_services",
                       "affected_services_ref",
                       "forest",
                       "forest_ref" ]:
            for key, values in new_data.get(what, {}).items():
                self._compiled_trees[what].setdefault(key, [])
                self._compiled_trees[what][key].extend(values)

        # Rendering related parameters
        for what in [ "aggr_ref" ]:
            self._compiled_trees[what].update(new_data.get(what, {}))

        # Cache related parameters
        job_id = job["id"]
        aggr_type, idx, aggr_groups = job_id

        if aggr_type == AGGR_HOST:
            self._compiled_trees["compiled_host_aggr"].setdefault(job_id, {"compiled_hosts": set([])})
            self._compiled_trees["compiled_host_aggr"][job_id]["compiled_hosts"].update(new_data["compiled_hosts"])
        else:
            self._compiled_trees["compiled_multi_aggr"].setdefault(job_id, {})
            self._compiled_trees["compiled_multi_aggr"][job_id]["compiled"] = True




def get_enabled_aggregations():
    result = []
    for aggr_type, what in [ (AGGR_MULTI, config.aggregations),
                             (AGGR_HOST, config.host_aggregations) ]:
        for aggr_def in sorted(what):
            if aggr_def[0].get("disabled"): # options field
                continue
            result.append((aggr_type, aggr_def))

    return result

def get_aggr_groups(aggr_def):
    if type(aggr_def[1]) != list:
        aggr_groups = [ aggr_def[1] ]
    else:
        aggr_groups = aggr_def[1]
    return aggr_groups

def get_aggr_ids(what = None): # AGGR_HOST / AGGR_MULTI
    if what is None:
        what = []
    result = []
    enabled_aggregations = get_enabled_aggregations()
    for idx, (aggr_type, aggr_def) in enumerate(enabled_aggregations):
        if aggr_type in what:
            aggr_groups = get_aggr_groups(aggr_def)
            result.append((aggr_type, idx, tuple(aggr_groups)))
    return result

def num_filelocks():
    return len(os.listdir("/proc/%s/fd" % os.getpid()))

def setup_bi_instances():
    # The Sitedata Manager holds all data queried from the sites
    ############################################################
    global g_bi_sitedata_manager
    if not g_bi_sitedata_manager:
        g_bi_sitedata_manager = BISitedataManager()

    # The Job Manager keeps track of the jobs
    #########################################
    global g_bi_job_manager
    if not g_bi_job_manager:
        g_bi_job_manager = BIJobManager()

    # The Cache Manager manages the compilation and validiation of trees
    ####################################################################
    global g_bi_cache_manager
    if not g_bi_cache_manager:
        g_bi_cache_manager = BICacheManager()

    # Throw away existing cache if it is no longer valid
    # Reasons
    # - BI configuration changes
    # - Core restarts
    # - More sites are online than the current cache knows of

    cache_is_valid = g_bi_cache_manager.load_cachefile(force_validation = True)

    if cache_is_valid and g_bi_cache_manager.get_error_info():
        raise MKConfigError(g_bi_cache_manager.get_error_info())

def compile_forest_improved(only_hosts=None, only_groups=None):
    log("###########################################################")
    log("Query only hosts: %d, only_groups: %d (%r)" % (len(only_hosts or []), len(only_groups or []), only_groups))
    log("Open filelocks :%d" % num_filelocks())

    setup_bi_instances()

    # TODO: can be removed soon
    global used_cache      # Boolean
    global did_compilation # Boolean
    did_compilation = False
    used_cache      = True

    try:
        if not get_enabled_aggregations():
            log("No aggregations activated")
            return

        while True:
            # Keep this compiled_all block here. If it is done later on, site data will be read..
            if g_bi_cache_manager.get_compiled_all():
                # Bonus! We do no longer need the host/service data if everthing is compiled. These frees lots of memory
                g_bi_sitedata_manager.discard_cached_data()
                g_bi_cache_manager.clear_cachefile_cache()
                log("Is fully compiled with %s" % \
                    ", ".join(map(lambda x: "%s/%s" % x, g_bi_cache_manager.get_online_sites())))
                return

            all_hosts = g_bi_sitedata_manager.get_all_hosts()
            jobs      = g_bi_job_manager.get_missing_jobs(only_hosts, only_groups, all_hosts)
            if not jobs:
                log("No jobs required")
                return

            did_compile = g_bi_job_manager.compile_all_jobs()

            # Hard working apache processes are allowed to continue
            if did_compile:
                did_compilation = True
                continue

            # Passive apache processes simply reload the cachefile (if applicable) and wait
            g_bi_cache_manager.load_cachefile()

            log("Wait for jobs to finish: %s" % len(jobs.keys()))
            time.sleep(1)

    except Exception, e:
        log("Exception in BI compilation main loop:")
        log_exception()
    finally:
        if g_bi_cache_manager.get_error_info():
            raise MKConfigError(g_bi_cache_manager.get_error_info())

        global g_tree_cache
        g_tree_cache = g_bi_cache_manager.get_compiled_trees()
        log("-- Finished --")



# Precompile the forest of BI rules. Forest? A collection of trees.
# The compiled forest does not contain any regular expressions anymore.
# Everything is resolved. Sites, hosts and services are hardcoded. The
# aggregation functions are still left as names. That way the forest
# printable (and storable in Python syntax to a file).
def compile_forest(user, only_hosts = None, only_groups = None):
    migrate_bi_configuration()

    if not config.bi_use_legacy_compilation:
        compile_forest_improved(only_hosts, only_groups)
        return

    global g_cache, g_tree_cache
    global used_cache, did_compilation

    new_config_information = cache_needs_update()
    if new_config_information:
        log("Configuration has changed. Forcing recompile.")
        g_cache = {}
        global g_config_information
        g_config_information = new_config_information

    # OPTIMIZE: All users that have the permissing bi.see_all
    # can use the same cache.
    if config.user.may("bi.see_all"):
        user = '<<<see_all>>>'

    def empty_user_cache():
        return {
            "forest" :                   {},
            "aggregations_by_hostname" : {},
            "host_aggregations" :        {},
            "affected_hosts" :           {},
            "affected_services":         {},
            "compiled_hosts" :           set([]),
            "compiled_groups" :          set([]),
            "compiled_all" :             False,
        }

    # Try to get data from per-user cache:
    # make sure, BI permissions have not changed since last time.
    # g_tree_cache is a global variable for all succeeding functions, so
    # that they do not need to check the user again
    cache = g_cache.get(user)
    if cache:
        g_tree_cache = cache
    else:
        # Initialize empty caching structure
        cache = empty_user_cache()
        g_tree_cache = cache

    if g_tree_cache["compiled_all"]:
        log('PID: %d - Already compiled everything' % os.getpid())
        used_cache = True
        return # In this case simply skip further compilations

    if not config.aggregations and not config.host_aggregations:
        return # nothing to do, BI not used

    # If we have previously only partly compiled and now there is no
    # filter, then throw away partly compiled data.
    if (cache["compiled_hosts"] or cache["compiled_groups"]) \
       and (not config.bi_precompile_on_demand \
       or (config.bi_precompile_on_demand and not only_groups and not only_hosts)):
        log("Invalidating incomplete cache, since we compile all now.")
        cache = empty_user_cache()
        g_tree_cache = cache

    # Reduces a list of hosts by the already compiled hosts
    def to_compile(objects, what):
        todo = []
        for obj in objects:
            if obj not in cache['compiled_' + what]:
                todo.append(obj)
        return todo

    if only_hosts and cache['compiled_hosts']:
        # if only hosts is given and there are already compiled hosts
        # check whether or not hosts are not compiled yet
        only_hosts = to_compile(only_hosts, 'hosts')
        if not only_hosts:
            log('PID: %d - All requested hosts have already been compiled' % os.getpid())
            used_cache = True
            return # Nothing to do - everything is cached

    if only_groups and cache['compiled_groups']:
        only_groups = to_compile(only_groups, 'groups')
        if not only_groups:
            log('PID: %d - All requested groups have already been compiled' % os.getpid())
            used_cache = True
            return # Nothing to do - everything is cached

    # Set a flag that anything has been compiled in this call
    did_compilation = True

    # Load all (needed) services
    # The only_hosts variable is only set in "precompile on demand" mode to filter out
    # the needed hosts/services if possible. It is used in the load_services() function
    # to reduce the amount of hosts/services. Reducing the host/services leads to faster
    # compilation.
    load_services(only_hosts)

    log("This request: User: %s, Only-Groups: %r, Only-Hosts: %s PID: %d"
        % (user, only_groups, only_hosts, os.getpid()))

    before   = time.time()
    num_new_host_aggrs  = 0
    num_new_multi_aggrs = 0

    aggr_list = [(AGGR_MULTI, config.aggregations), (AGGR_HOST, config.host_aggregations)]

    single_affected_hosts = []
    for aggr_type, aggregations in aggr_list:
        for aggr_def in aggregations:
            options = aggr_def[0]

            if options.get("disabled"):
                continue

            downtime_aggr_warn = options.get("downtime_aggr_warn", False)
            use_hard_states    = options.get("use_hard_states", False)

            if len(aggr_def) < 3:
                raise MKConfigError(_("<h1>Invalid aggregation <tt>%s</tt></h1>"
                                      "Must have at least 3 entries (has %d)") % (aggr_def, len(aggr_def)))

            if type(aggr_def[1]) == list:
                groups = aggr_def[1]
            else:
                groups = [ aggr_def[1] ]
            groups_set = set(groups)

            if only_groups and not groups_set.intersection(only_groups):
                log('Skip aggr (No group of the aggr has been requested: %r)' % groups)
                continue # skip not requested groups if filtered by groups

            if len(groups_set) == len(groups_set.intersection(cache['compiled_groups'])):
                log('Skip aggr (All groups have already been compiled')
                continue # skip if all groups have already been compiled

            new_entries = compile_rule_node(aggr_type, aggr_def[2:], 0)

            for this_entry in new_entries:
                remove_empty_nodes(this_entry)
                this_entry["use_hard_states"] = use_hard_states
                this_entry["downtime_aggr_warn"] = downtime_aggr_warn

            new_entries = [ e for e in new_entries if len(e["nodes"]) > 0 ]

            if aggr_type == AGGR_HOST:
                num_new_host_aggrs += len(new_entries)
            else:
                num_new_multi_aggrs += len(new_entries)

            # enter new aggregations into dictionary for these groups
            for group in groups:
                if group in cache['compiled_groups']:
                    log('Skip aggr (group %s already compiled)' % group)
                    continue # the group has already been compiled completely

                if group not in cache['forest']:
                    cache['forest'][group] = new_entries[:]
                else:
                    cache['forest'][group] += new_entries

                # Update several global speed-up indices
                for aggr in new_entries:
                    req_hosts = aggr["reqhosts"]

                    # Aggregations by last part of title (assumed to be host name)
                    name = aggr["title"].split()[-1]
                    cache["aggregations_by_hostname"].setdefault(name, []).append((group, aggr))

                    # All single-host aggregations looked up per host
                    # Only process the aggregations of hosts which are mentioned in only_hosts
                    if aggr_type == AGGR_HOST:
                        # In normal cases a host aggregation has only one req_hosts item, we could use
                        # index 0 here. But clusters (which are also allowed now) have all their nodes
                        # in the list of required nodes.
                        # Before the latest change this used the last item of the req_hosts. I think it
                        # would be better to register this for all hosts mentioned in req_hosts. Give it a try...
                        # ASSERT: len(req_hosts) == 1!
                        for host in req_hosts:
                            if not only_hosts or host in only_hosts:
                                cache["host_aggregations"].setdefault(host, []).append((group, aggr))

                                # construct a list of compiled single-host aggregations for cached registration
                                single_affected_hosts.append(host)

                    # Also all other aggregations that contain exactly one hosts are considered to
                    # be "single host aggregations"
                    elif len(req_hosts) == 1:
                        cache["host_aggregations"].setdefault(req_hosts[0], []).append((group, aggr))

                    # All aggregations containing a specific host
                    for h in req_hosts:
                        cache["affected_hosts"].setdefault(h, []).append((group, aggr))

                    # All aggregations containing a specific service
                    services = find_all_leaves(aggr)
                    for s in services: # triples of site, host, service
                        cache["affected_services"].setdefault(s, []).append((group, aggr))

    # Register compiled objects
    if only_hosts:
        cache['compiled_hosts'].update(single_affected_hosts)

    elif only_groups:
        cache['compiled_groups'].update(only_groups)
        cache['compiled_hosts'].update(single_affected_hosts)

    else:
        # The list of ALL hosts
        cache['compiled_hosts']  = set(g_services.keys())
        cache['compiled_groups'] = set(cache['forest'].keys())
        cache['compiled_all'] = True

    # Remember successful compile in cache
    g_cache[user] = cache

    check_title_uniqueness(cache["forest"])

    num_total_aggr = 0
    for grp, aggrs in cache['forest'].iteritems():
        num_total_aggr += len(aggrs)

    num_host_aggr = 0
    for grp, aggrs in cache['host_aggregations'].iteritems():
        num_host_aggr += len(aggrs)

    num_services = 0
    for key, val in g_services.iteritems():
        num_services += len(val[1])

    after = time.time()

    log("\nThis request:\n"
        "  User: %s, Only-Groups: %r, Only-Hosts: %s\n"
        "  PID: %d, Processed %d services on %d hosts in %.3f seconds.\n"
        "\n"
        "  %d compiled multi aggrs, %d compiled host aggrs, %d compiled groups\n"
        "Cache:\n"
        "  Everything compiled: %r\n"
        "  %d compiled multi aggrs, %d compiled host aggrs, %d compiled groups\n"
        "Config:\n"
        "  Multi-Aggregations: %d, Host-Aggregations: %d"
        % (
           user, only_groups, only_hosts,
           os.getpid(),
           num_services, len(g_services_by_hostname),
           after - before,

           num_new_multi_aggrs, num_new_host_aggrs,
           only_groups and len(only_groups) or 0,

           cache['compiled_all'],
           num_total_aggr - num_host_aggr,
           num_host_aggr,
           len(cache['compiled_groups']),
           len(config.aggregations),
           len(config.host_aggregations),
        ))


def check_title_uniqueness(forest):
    known_titles = set()
    for group, aggrs in forest.iteritems():
        for aggr in aggrs:
            title = aggr["title"]
            if title in known_titles:
                raise MKConfigError(_("Duplicate BI aggregation with the title \"<b>%s</b>\". "
                         "Please check your BI configuration and make sure that within each group no aggregation has "
                         "the same title as any other. Note: you can use arguments in the top level "
                         "aggregation rule, like <tt>Host $HOST$</tt>.") % (
                    html.attrencode(title)))
            else:
                known_titles.add(title)

# Execute an aggregation rule, but prepare arguments
# and iterate FOREACH first
def compile_rule_node(aggr_type, calllist, lvl):
    # Lookup rule source code
    rulename, arglist = calllist[-2:]
    what = calllist[0]
    if rulename not in config.aggregation_rules:
        raise MKConfigError(_("<h1>Invalid configuration in variable <tt>aggregations</tt></h1>"
                "There is no rule named <tt>%s</tt>. Available are: <tt>%s</tt>") %
                (rulename, "</tt>, <tt>".join(config.aggregation_rules.keys())))
    rule = config.aggregation_rules[rulename]
    if rule.get("disabled", False):
        return []

    # Execute FOREACH: iterate over matching hosts/services.
    # Create an argument list where $1$, $2$, ... are
    # substituted with matched strings for each match.
    if what in [
            config.FOREACH_HOST,
            config.FOREACH_CHILD,
            config.FOREACH_CHILD_WITH,
            config.FOREACH_PARENT,
            config.FOREACH_SERVICE ]:
        matches = find_matching_services(aggr_type, what, calllist[1:])
        new_elements = []
        handled_args = set() # avoid duplicate rule incarnations
        for (hostname, hostalias), matchgroups in matches:
            args = substitute_matches(arglist, hostname, hostalias, matchgroups)
            if tuple(args) not in handled_args:
                new_elements += compile_aggregation_rule(aggr_type, rule, args, lvl)
                handled_args.add(tuple(args))

        return new_elements

    else:
        return compile_aggregation_rule(aggr_type, rule, arglist, lvl)


def find_matching_services(aggr_type, what, calllist):
    if what == config.FOREACH_CHILD_WITH: # extract foreach child specific parameters
        required_child_tags = calllist[0]
        child_spec = calllist[1]
        calllist   = calllist[2:]

    # honor list of host tags preceding the host_re
    if type(calllist[0]) == list:
        required_tags = calllist[0]
        calllist = calllist[1:]
    else:
        required_tags = []

    if len(calllist) == 0:
        raise MKConfigError(_("Invalid syntax in FOREACH_..."))

    host_spec = calllist[0]
    if what in [ config.FOREACH_HOST, config.FOREACH_CHILD, config.FOREACH_CHILD_WITH, config.FOREACH_PARENT ]:
        service_re = config.HOST_STATE
    else:
        service_re = calllist[1]

    matches = set([])

    if type(host_spec) == tuple:
        host_spec, honor_site, entries = get_services_filtered_by_host_alias(host_spec)
    else:
        host_spec, honor_site, entries = get_services_filtered_by_host_name(host_spec)

    # TODO: Hier könnte man - wenn der Host bekannt ist, effektiver arbeiten, als komplett alles durchzugehen.
    for (site, hostname), (tags, services, childs, parents, alias) in entries:
        # Skip already compiled hosts
        if aggr_type == AGGR_HOST and (site, hostname) in g_tree_cache.get('compiled_hosts', []):
            continue

        host_matches = match_host(hostname, alias, host_spec,
                                  tags, required_tags, site, honor_site)
        list_of_matches = []
        if host_matches != None:
            if what == config.FOREACH_CHILD:
                list_of_matches = [ host_matches + (child_name,) for child_name in childs ]

            elif what == config.FOREACH_CHILD_WITH:
                for child_name in childs:
                    child_tags = g_services_by_hostname[child_name][0][1][0]
                    child_alias = g_services_by_hostname[child_name][0][1][4]
                    child_matches = match_host(child_name, child_alias, child_spec, child_tags,
                                               required_child_tags, site, honor_site)
                    if child_matches != None:
                        list_of_matches.append(host_matches + child_matches)

            elif what == config.FOREACH_PARENT:
                list_of_matches  = [ host_matches + (parent,) for parent in parents ]

            else:
                list_of_matches = [ host_matches ]

        for host_matches in list_of_matches:
            if service_re == config.HOST_STATE:
                matches.add(((hostname, alias), host_matches))
                continue

            for service in services:
                mo = (service_re, service)
                if mo in regex_svc_miss_cache:
                    continue

                if mo not in regex_svc_hit_cache:
                    m = regex(service_re).match(service)
                    if m:
                        regex_svc_hit_cache.add(mo)
                    else:
                        regex_svc_miss_cache.add(mo)
                        continue
                else:
                    m = regex(service_re).match(service)

                svc_matches = tuple(m.groups())
                matches.add(((hostname, alias), host_matches + svc_matches))

    return sorted(list(matches))


def get_services_filtered_by_host_alias(host_spec):
    honor_site = SITE_SEP in host_spec[1]
    if g_services_items:
        return host_spec, honor_site, g_services_items
    else:
        return host_spec, honor_site, g_services.items()


def get_services_filtered_by_host_name(host_re):
    honor_site = SITE_SEP in host_re

    if host_re.startswith("^(") and host_re.endswith(")$"):
        # Exact host match
        middle = host_re[2:-2]
        if middle in g_services_by_hostname:
            entries = [ ((e[0], host_re), e[1]) for e in g_services_by_hostname[middle] ]
            host_re = "(.*)"

    elif not honor_site and not '*' in host_re and not '$' in host_re \
         and not '|' in host_re and not '[' in host_re:
        # Exact host match
        entries = [ ((e[0], host_re), e[1]) for e in g_services_by_hostname.get(host_re, []) ]

    else:
        # All services
        if g_services_items:
            entries = g_services_items
        else:
            entries = g_services.items()

    return host_re, honor_site, entries


def do_match(reg, text):
    mo = regex(reg).match(text)
    if not mo:
        return None
    else:
        return tuple(mo.groups())



# Debugging function
def render_forest():
    for group, trees in g_tree_cache["forest"].items():
        html.write("<h2>%s</h2>" % group)
        for tree in trees:
            ascii = render_tree(tree)
            html.write("<pre>\n" + ascii + "<pre>\n")

# Debugging function
def render_tree(node, indent = ""):
    h = ""
    if node["type"] == NT_LEAF: # leaf node
        h += indent + "S/H/S: %s/%s/%s%s\n" % (node["host"][0], node["host"][1], node.get("service"),
                node.get("hidden") == True and " (hidden)" or "")
    else:
        h += indent + "Aggregation:\n"
        indent += "    "
        h += indent + "Description:  %s\n" % node["title"]
        h += indent + "Hidden:       %s\n" % (node.get("hidden") == True and "yes" or "no")
        h += indent + "Needed Hosts: %s\n" % " ".join([("%s/%s" % h_s) for h_s in node["reqhosts"]])
        h += indent + "Aggregation:  %s\n" % node["func"]
        h += indent + "Nodes:\n"
        for node in node["nodes"]:
            h += render_tree(node, indent + "  ")
        h += "\n"
    return h


# Compute dictionary of arguments from arglist and
# actual values
def make_arginfo(arglist, args):
    arginfo = {}
    for name, value in zip(arglist, args):
        if name[0] == 'a':
            expansion = SINGLE
            name = name[1:]
        elif name[-1] == 's':
            expansion = MULTIPLE
            name = name[:-1]
        else:
            raise MKConfigError(_("Invalid argument name %s. Must begin with 'a' or end with 's'.") % name)
        arginfo[name] = (expansion, value)
    return arginfo

def find_all_leaves(node):
    # leaf node
    if node["type"] == NT_LEAF:
        site, host = node["host"]
        return [ (site, host, node.get("service") ) ]

    # rule node
    elif node["type"] == NT_RULE:
        entries = []
        for n in node["nodes"]:
            entries += find_all_leaves(n)
        return entries

    # place holders
    else:
        return []

# Removes all empty nodes from the given rule tree
def remove_empty_nodes(node):
    if node["type"] != NT_RULE:
        # simply return leaf nodes without action
        return node
    else:
        subnodes = node["nodes"]
        # loop all subnodes recursing down to the lowest level
        for i in range(0, len(subnodes)):
            remove_empty_nodes(subnodes[i])
        # remove all subnode rules which have no subnodes
        for i in range(0, len(subnodes))[::-1]:
            if node_is_empty(subnodes[i]):
                del subnodes[i]

# Checks whether or not a rule node has no subnodes
def node_is_empty(node):
    if node["type"] != NT_RULE: # leaf node
        return False
    else:
        return len(node["nodes"]) == 0


# Precompile one aggregation rule. This outputs a list of trees.
# The length of this list is current either 0 or 1
def compile_aggregation_rule(aggr_type, rule, args, lvl):
    # When compiling root nodes we essentially create
    # complete top-level aggregations. In that case we
    # need to deal with REMAINING-entries
    if lvl == 0:
        # A global variable used for recursive function calls..
        global g_remaining_refs
        g_remaining_refs = []

        global g_compiled_services_leafes
        g_compiled_services_leafes = {}

    # Convert new dictionary style rule into old tuple based
    # format
    # TODO: O.o Remove this code, all of it...
    if type(rule) == dict:
        rule = (
            rule.get("title", _("Untitled BI rule")),
            rule.get("params", []),
            rule.get("aggregation", "worst"),
            rule.get("nodes", []),
            rule.get("state_messages")
        )

    if len(rule) != 5:
        raise MKConfigError(_("<b>Invalid BI aggregation rule</b>: "
                "Aggregation rules must contain four elements: description, argument list, "
                "aggregation function and list of nodes. Your rule has %d elements: "
                "<pre>%s</pre>") % (len(rule), pprint.pformat(rule)))

    if lvl == 50:
        raise MKConfigError(_("<b>BI depth limit reached</b>: "
                "The nesting level of aggregations is limited to 50. You either configured "
                "too many levels or built an infinite recursion. This happened in rule %s")
                  % pprint.pformat(rule))

    description, arglist, funcname, nodes, state_messages = rule

    # check arguments and convert into dictionary
    if len(arglist) != len(args):
        raise MKConfigError(_("<b>Invalid BI rule usage</b>: "
                "The rule '%s' needs %d arguments: <tt>%s</tt>. "
                "You've specified %d arguments: <tt>%s</tt>") % (
                    description, len(arglist), repr(arglist), len(args), repr(args)))

    arginfo = dict(zip(arglist, args))
    inst_description = subst_vars(description, arginfo)

    elements = []

    for node in nodes:
        # Handle HIDDEN nodes. There are compiled just as normal nodes, but
        # will not be visible in the tree view later (at least not per default).
        # The HIDDEN flag needs just to be packed into the compilation and not
        # further handled here.
        if node[0] == config.HIDDEN:
            hidden = True
            node = node[1:]
        else:
            hidden = False

        # Each node can return more than one incarnation (due to regexes in
        # leaf nodes and FOREACH in rule nodes)

        if node[1] in [ config.HOST_STATE, config.REMAINING ]:
            new_elements = compile_leaf_node(subst_vars(node[0], arginfo), node[1])
            new_new_elements = []
            for entry in new_elements:
                # Postpone: remember reference to list where we need to add
                # remaining services of host
                if entry["type"] == NT_REMAINING:
                    # create unique pointer which we find later
                    placeholder = {"type" : NT_PLACEHOLDER, "id" : str(len(g_remaining_refs)) }
                    g_remaining_refs.append((entry["host"], elements, placeholder))

                    new_new_elements.append(placeholder)
                else:
                    new_new_elements.append(entry)
            new_elements = new_new_elements

        elif type(node[-1]) != list:
            if node[0] in [
                    config.FOREACH_HOST,
                    config.FOREACH_CHILD,
                    config.FOREACH_PARENT,
                    config.FOREACH_SERVICE ]:
                # Handle case that leaf elements also need to be iterable via FOREACH_HOST
                # 1: config.FOREACH_HOST
                # 2: (['waage'], '(.*)')
                calllist = []
                for n in node[1:-2]:
                    if type(n) in [ str, unicode, list, tuple ]:
                        n = subst_vars(n, arginfo)
                    calllist.append(n)

                matches = find_matching_services(aggr_type, node[0], calllist)
                new_elements = []
                handled_args = set() # avoid duplicate rule incarnations
                for (hostname, hostalias), matchgroups in matches:
                    if tuple(args) + matchgroups not in handled_args:
                        new_elements += compile_leaf_node(substitute_matches(node[-2], hostname, hostalias, matchgroups),
                                                          substitute_matches(node[-1], hostname, hostalias, matchgroups))
                        handled_args.add(tuple(args) + matchgroups)

                host_name, service_description = node[-2:]
            else:
                # This is a plain leaf node with just host/service
                new_elements = compile_leaf_node(subst_vars(node[0], arginfo), subst_vars(node[1], arginfo))

        else:
            # substitute our arguments in rule arguments
            # rule_args:
            # ['$1$']
            # rule_parts:
            # (<class _mp_84b7bd024cff73bf04ba9045f980becb.FOREACH_HOST at 0x7f03600dc8d8>, ['waage'], '(.*)', 'host')
            rule_args = [ subst_vars(a, arginfo) for a in node[-1] ]
            rule_parts = tuple([ subst_vars(part, arginfo) for part in node[:-1] ])
            new_elements = compile_rule_node(aggr_type, rule_parts + (rule_args,), lvl + 1)

        if hidden:
            for element in new_elements:
                element["hidden"] = True

        elements += new_elements

    needed_hosts = set([])
    for element in elements:
        needed_hosts.update(element.get("reqhosts", []))

    aggregation = { "type"     : NT_RULE,
                    "reqhosts" : needed_hosts,
                    "title"    : inst_description,
                    "func"     : funcname,
                    "nodes"    : elements}

    if state_messages:
        aggregation["state_messages"] = state_messages

    # Handle REMAINING references, if we are a root node
    if lvl == 0:
        for hostspec, ref, placeholder in g_remaining_refs:
            new_entries = find_remaining_services(hostspec, aggregation)
            for entry in new_entries:
                aggregation['reqhosts'].update(entry['reqhosts'])
            where_to_put = ref.index(placeholder)
            ref[where_to_put:where_to_put+1] = new_entries

    aggregation['reqhosts'] = list(aggregation['reqhosts'])

    return [ aggregation ]


def find_remaining_services(hostspec, aggregation):
    tags, all_services, childs, parents, alias = g_services[hostspec]
    all_services = set(all_services)

    remaining = all_services - g_compiled_services_leafes.get(hostspec, set([]))
    g_compiled_services_leafes.get(hostspec, set([])).update(remaining)
    return [ {
        "type"     : NT_LEAF,
        "host"     : hostspec,
        "reqhosts" : [hostspec],
        "service"  : service,
        "title"    : "%s - %s" % (hostspec[1], service)}
        for service in remaining ]


# Helper function that finds all occurrances of a variable
# enclosed with $ and $. Returns a list of positions.
def find_variables(pattern, varname):
    found = []
    start = 0
    while True:
        pos = pattern.find('$' + varname + '$', start)
        if pos >= 0:
            found.append(pos)
            start = pos + 1
        else:
            return found


def subst_vars(pattern, arginfo):
    if type(pattern) == list:
        return [subst_vars(x, arginfo) for x in pattern ]
    elif type(pattern) == tuple:
        return tuple([subst_vars(x, arginfo) for x in pattern ])

    for name, value in arginfo.items():
        if type(pattern) in [ str, unicode ]:
            pattern = pattern.replace('$'+name+'$', value)
    return pattern


def substitute_matches(arg, hostname, hostalias, matchgroups):
    arginfo = dict([(str(n+1), x) for (n,x) in enumerate(matchgroups)])
    arginfo["HOSTNAME"]  = hostname
    arginfo["HOSTALIAS"] = hostalias

    return subst_vars(arg, arginfo)


def match_host_tags(have_tags, required_tags):
    for tag in required_tags:
        if tag.startswith('!'):
            negate = True
            tag = tag[1:]
        else:
            negate = False
        has_it = tag in have_tags
        if has_it == negate:
            return False
    return True


def match_host(hostname, hostalias, host_spec, tags, required_tags, site, honor_site):
    if not match_host_tags(tags, required_tags):
        return None

    if type(host_spec) != tuple: # matching by host name
        pattern  = host_spec
        to_match = hostname
    else:
        pattern = host_spec[1]
        to_match = hostalias

    if pattern == '(.*)':
        return (to_match, )
    else:
        # For regex to have '$' anchor for end. Users might be surprised
        # to get a prefix match on host names. This is almost never what
        # they want. For services this is useful, however.
        if pattern[-1] == "$":
            anchored = pattern
        else:
            anchored = pattern + "$"

        # In order to distinguish hosts with the same name on different
        # sites we prepend the site to the host name. If the host specification
        # does not contain the site separator - though - we ignore the site
        # an match the rule for all sites.
        if honor_site:
            return do_match(anchored, "%s%s%s" % (site, SITE_SEP, to_match))
        else:
            return do_match(anchored, to_match)


# dictionary with hosts and its compiled services
g_compiled_services_leafes = {}

regex_host_hit_cache   = set()
regex_host_miss_cache  = set()

regex_svc_hit_cache    = set()
regex_svc_miss_cache   = set()

def compile_leaf_node(host_re, service_re = config.HOST_STATE):
    found = []

    if host_re == "$1$":
        return found

    honor_site = SITE_SEP in host_re
    if not honor_site and not '*' in host_re and not '$' in host_re \
        and not '|' in host_re and '[' not in host_re:
        # Exact host match
        entries = [ ((e[0], host_re), e[1]) for e in g_services_by_hostname.get(host_re, []) ]

    else:
        if g_services_items:
            entries = g_services_items
        else:
            entries = g_services.items()

    # TODO: If we already know the host we deal with, we could avoid this loop
    for (site, hostname), (tags, services, childs, parents, alias) in entries:
        # For regex to have '$' anchor for end. Users might be surprised
        # to get a prefix match on host names. This is almost never what
        # they want. For services this is useful, however.
        if host_re[-1] == "$":
            anchored = host_re
        else:
            anchored = host_re + "$"

        # In order to distinguish hosts with the same name on different
        # sites we prepend the site to the host name. If the host specification
        # does not contain the site separator - though - we ignore the site
        # an match the rule for all sites.
        if honor_site:
            search_term = "%s%s%s" % (site, SITE_SEP, hostname)
        else:
            search_term = hostname


        cache_id = (anchored, search_term)
        if cache_id in regex_host_miss_cache:
            continue

        if cache_id not in regex_host_hit_cache:
            if regex(anchored).match(search_term):
                regex_host_hit_cache.add(cache_id)
            else:
                regex_host_miss_cache.add(cache_id)
                continue

        if service_re == config.HOST_STATE:
            found.append({"type"     : NT_LEAF,
                          "reqhosts" : [(site, hostname)],
                          "host"     : (site, hostname),
                          "title"    : hostname})

        elif service_re == config.REMAINING:
            found.append({"type"     : NT_REMAINING,
                          "reqhosts" : [(site, hostname)],
                          "host"     : (site, hostname)})
        else:
            for service in services:
                mo = (service_re, service)
                if mo in regex_svc_miss_cache:
                    continue

                if mo not in regex_svc_hit_cache:
                    if regex(service_re).match(service):
                        regex_svc_hit_cache.add(mo)
                    else:
                        regex_svc_miss_cache.add(mo)
                        continue

                found.append({"type"     : NT_LEAF,
                              "reqhosts" : [(site, hostname)],
                              "host"     : (site, hostname),
                              "service"  : service,
                              "title"    : "%s - %s" % (hostname, service)} )

    found.sort()

    for entry in found:
        if "service" in entry:
            g_compiled_services_leafes.setdefault(entry["host"], set([])).add(entry["service"])

    return found


#     _____                     _   _
#    | ____|_  _____  ___ _   _| |_(_) ___  _ __
#    |  _| \ \/ / _ \/ __| | | | __| |/ _ \| '_ \
#    | |___ >  <  __/ (__| |_| | |_| | (_) | | | |
#    |_____/_/\_\___|\___|\__,_|\__|_|\___/|_| |_|
#

#                  + services               + states
# multisite.d/*.mk =========> compiled tree ========> executed tree
#                   compile                 execute

# Format of executed tree:
# leaf: ( state, assumed_state, compiled_node )
# rule: ( state, assumed_state, compiled_node, nodes )

# Format of state and assumed_state:
# { "state" : OK, WARN ...
#   "output" : aggregated output or service output }


# Execution of the trees. Returns a tree object reflecting
# the states of all nodes
def execute_tree(tree, status_info = None):
    aggregation_options = {
        "use_hard_states"    : tree["use_hard_states"],
        "downtime_aggr_warn" : tree["downtime_aggr_warn"],
    }

    if status_info == None:
        required_hosts = tree["reqhosts"]
        status_info = get_status_info(required_hosts)
    return execute_node(tree, status_info, aggregation_options)


def execute_node(node, status_info, aggregation_options):
    if node["type"] == NT_LEAF:
        return execute_leaf_node(node, status_info, aggregation_options)
    else:
        return execute_rule_node(node, status_info, aggregation_options)


def execute_leaf_node(node, status_info, aggregation_options):

    site, host = node["host"]
    service = node.get("service")

    # Get current state of host and services
    status = status_info.get((site, host))
    if status == None:
        return ({
            "state"               : None,
            "output"              : _("Host %s not found") % host,
            "in_downtime"         : 0,
            "acknowledged"        : False,
            "in_service_period"   : True,
        }, None, node)
    host_state, host_hard_state, host_output, host_in_downtime, host_acknowledged, host_in_service_period, service_state = status

    # Get state assumption from user
    if service:
        key = (site, host, service)
    else:
        key = (site, host)
    state_assumption = g_assumptions.get(key)

    # assemble state
    if service:
        for entry in service_state: # list of all services of that host
            if entry[0] == service:
                if len(entry) < 10:
                    entry = entry + [ True ] # old versions of Livestatus do not send in_service_period
                state, has_been_checked, output, hard_state, attempt, max_attempts, downtime_depth, acknowledged, in_service_period = entry[1:10]
                if has_been_checked == 0:
                    output = _("This service has not been checked yet")
                    state = PENDING
                if aggregation_options["use_hard_states"]:
                    st = hard_state
                else:
                    st = state
                state = {
                    "state"             : st,
                    "output"            : output,
                    "in_downtime"       : downtime_depth > 0 and 2 or host_in_downtime != 0 and 1 or 0,
                    "acknowledged"      : not not acknowledged,
                    "in_service_period" : in_service_period,
                }
                if state_assumption != None:
                    assumed_state = {
                        "state"             : state_assumption,
                        "output"            : _("Assumed to be %s") % service_state_names[state_assumption],
                        "in_downtime"       : downtime_depth > 0 and 2 or host_in_downtime != 0 and 1 or 0,
                        "acknowledged"      : not not acknowledged,
                        "in_service_period" : in_service_period,
                    }

                else:
                    assumed_state = None
                return (state, assumed_state, node)

        return ({
                "state"             : None,
                "output"            : _("This host has no such service"),
                "in_downtime"       : host_in_downtime,
                "acknowledged"      : False,
                "in_service_period" : True,
            }, None, node)

    else:
        if aggregation_options["use_hard_states"]:
            st = host_hard_state
        else:
            st = host_state
        aggr_state = {0:OK, 1:CRIT, 2:UNKNOWN, -1:PENDING, None: None}[st]
        state = {
            "state"             : aggr_state,
            "output"            : host_output,
            "in_downtime"       : host_in_downtime,
            "acknowledged"      : host_acknowledged,
            "in_service_period" : host_in_service_period,
        }
        if state_assumption != None:
            assumed_state = {
                "state"             : state_assumption,
                "output"            : _("Assumed to be %s") % host_state_names[state_assumption],
                "in_downtime"       : host_in_downtime != 0,
                "acknowledged"      : host_acknowledged,
                "in_service_period" : host_in_service_period,
            }
        else:
            assumed_state = None
        return (state, assumed_state, node)


def execute_rule_node(node, status_info, aggregation_options):
    # get aggregation function
    funcspec = node["func"]
    parts = funcspec.split('!')
    funcname = parts[0]
    funcargs = parts[1:]
    func = config.aggregation_functions.get(funcname)
    if not func:
        raise MKConfigError(_("Undefined aggregation function '%s'. Available are: %s") %
                (funcname, ", ".join(config.aggregation_functions.keys())))

    # prepare information for aggregation function
    subtrees = []
    node_states = []
    assumed_states = []
    downtime_states = []
    service_period_states = []
    ack_states = [] # Needed for computing the acknowledgement of non-OK nodes
    one_assumption = False
    for n in node["nodes"]:
        result = execute_node(n, status_info, aggregation_options) # state, assumed_state, node [, subtrees]
        if result[0]["state"] == None: # Omit this node (used in availability for unmonitored things)
            continue
        subtrees.append(result)

        # Assume items in downtime as CRIT when computing downtime state
        downtime_states.append(({"state": result[0]["in_downtime"] != 0 and 2 or 0, "output" : ""}, result[2]))

        # Assume non-OK nodes that are acked as OK
        if result[0]["acknowledged"]:
            acked_state = 0
        else:
            acked_state = result[0]["state"]
        ack_states.append(({"state": acked_state, "output" : ""}, result[2]))

        # Assume items oo their service period as CRIT when computing in_service_period of aggregate
        service_period_states.append(({"state": (not result[0]["in_service_period"]) and 2 or 0, "output" : ""}, result[2]))

        node_states.append((result[0], result[2]))
        if result[1] != None:
            assumed_states.append((result[1], result[2]))
            one_assumption = True
        else:
            # no assumption, take real state into assumption array
            assumed_states.append(node_states[-1])

    if len(node_states) == 0:
        state = { "state": None, "output" : _("Not yet monitored") }
        downtime_state = state
    else:
        state = func(*([node_states] + funcargs))
        downtime_state = func(*([downtime_states] + funcargs))

    if aggregation_options["downtime_aggr_warn"]:
        state["in_downtime"] = downtime_state["state"] >= 1
    else:
        state["in_downtime"] = downtime_state["state"] >= 2

    # Compute acknowledgedment state
    if state["state"] > 0: # Non-OK-State -> compute acknowledgedment
        ack_state = func(*([ack_states] + funcargs))
        state["acknowledged"] = ack_state["state"] == 0 # would be OK if acked problems would be OK
    else:
        state["acknowledged"] = False

    # Compute service period state
    service_period_state = func(*([service_period_states] + funcargs))
    state["in_service_period"] = service_period_state["state"] < 2

    if one_assumption:
        assumed_state = func(*([assumed_states] + funcargs))
        assumed_state["in_downtime"] = state["in_downtime"]
        assumed_state["acknowledged"] = state["acknowledged"]
        assumed_state["in_service_period"] = state["in_service_period"]
    else:
        assumed_state = None
    return (state, assumed_state, node, subtrees)


# Get all status information we need for the aggregation from
# a known lists of lists (list of site/host pairs)
def get_status_info(required_hosts):
    # Query each site only for hosts that that site provides
    site_hosts = {}
    for site, host in required_hosts:
        hosts = site_hosts.get(site)
        if hosts == None:
            site_hosts[site] = [host]
        else:
            hosts.append(host)

    tuples = []
    for site, hosts in site_hosts.items():
        filter = ""
        for host in hosts:
            filter += "Filter: name = %s\n" % host
        if len(hosts) > 1:
            filter += "Or: %d\n" % len(hosts)
        sites.live().set_auth_domain('bi')
        sites.live().set_only_sites([site])
        data = sites.live().query(
                "GET hosts\n"
                "Columns: name state hard_state plugin_output scheduled_downtime_depth "
                "acknowledged in_service_period services_with_fullstate\n"
                + filter)
        sites.live().set_auth_domain('read')
        sites.live().set_only_sites(None)
        tuples += [((site, e[0]), e[1:]) for e in data]

    return dict(tuples)

# This variant of the function is configured not with a list of
# hosts but with a livestatus filter header and a list of columns
# that need to be fetched in any case
def get_status_info_filtered(filter_header, only_sites, limit, add_columns, precompile_on_demand, bygroup):
    columns = [ "name", "host_name", "state", "hard_state", "plugin_output", "scheduled_downtime_depth",
                "host_in_service_period", "acknowledged", "services_with_fullstate", "parents" ] + add_columns

    query = "GET hosts%s\n" % (bygroup and "bygroup" or "")
    query += "Columns: " + (" ".join(columns)) + "\n"
    query += filter_header

    sites.live().set_only_sites(only_sites)
    sites.live().set_prepend_site(True)
    sites.live().set_auth_domain('bi')

    data = sites.live().query(query)

    sites.live().set_prepend_site(False)
    sites.live().set_only_sites(None)
    sites.live().set_auth_domain('read')

    headers = [ "site" ] + columns
    hostnames = [ row[1] for row in data ]
    rows = [ dict(zip(headers, row)) for row in data]

    # on demand compile: if parents have been found, also fetch data of the parents.
    # This is needed to allow cluster hosts (which have the nodes as parents) in the
    # host_aggregation construct.
    if precompile_on_demand:
        parent_filter = []
        for row in rows:
            parent_filter += [ 'Filter: host_name = %s\n' % p for p in row["parents"] ]

        if parent_filter:
            parent_filter_txt  = ''.join(parent_filter)
            parent_filter_txt += 'Or: %d\n' % len(parent_filter)

            for row in get_status_info_filtered(parent_filter_txt, only_sites,
                                                limit, add_columns, False, bygroup):
                if row['name'] not in hostnames:
                    rows.append(row)

    return rows

#       _                      _____                 _   _
#      / \   __ _  __ _ _ __  |  ___|   _ _ __   ___| |_(_) ___  _ __  ___
#     / _ \ / _` |/ _` | '__| | |_ | | | | '_ \ / __| __| |/ _ \| '_ \/ __|
#    / ___ \ (_| | (_| | | _  |  _|| |_| | | | | (__| |_| | (_) | | | \__ \
#   /_/   \_\__, |\__, |_|(_) |_|   \__,_|_| |_|\___|\__|_|\___/|_| |_|___/
#           |___/ |___/

# API for aggregation functions
# it is called with at least one argument: a list of node infos.
# Each node info is a pair of the node state and the compiled node information.
# The node state is a dictionary with at least "state" and "output", where
# "state" is the Nagios state. It is allowed to place arbitrary additional
# information to the array, e.g. downtime & acknowledgement information.
# The compiled node information is a dictionary as created by the rule
# compiler. It contains "type" (NT_LEAF, NT_RULE), "reqhosts" and "title". For rule
# node it contains also "func". For leaf nodes it contains
# host" and (if not a host leaf) "service".
#
# The aggregation function must return one state dictionary containing
# at least "state" and "output".


# Function for sorting states. Pending should be slightly
# worst then OK. CRIT is worse than UNKNOWN.
def state_weight(s):
    if s == CRIT:
        return 10.0
    elif s == PENDING:
        return 0.5
    else:
        return float(s)

def x_best_state(l, x):
    ll = [ (state_weight(s), s) for s in l ]
    ll.sort()
    if x < 0:
        ll.reverse()
    n = abs(x)
    if len(ll) < n:
        n = len(ll)

    return ll[n-1][1]

def aggr_nth_state(nodelist, n, worst_state, ignore_states = None):
    states = [ i[0]["state"] for i in nodelist if not ignore_states or i[0]["state"] not in ignore_states ]
    # In case of the ignored states it might happen that the states list is empty. Use the
    # OK state in this case.
    if not states:
        state = OK
    else:
        state = x_best_state(states, n)

    # limit to worst state
    if state_weight(state) > state_weight(worst_state):
        state = worst_state

    return { "state" : state, "output" : "" }

def aggr_worst(nodes, n = 1, worst_state = CRIT, ignore_states = None):
    return aggr_nth_state(nodes, -int(n), int(worst_state), ignore_states)

def aggr_best(nodes, n = 1, worst_state = CRIT, ignore_states = None):
    return aggr_nth_state(nodes, int(n), int(worst_state), ignore_states)

config.aggregation_functions["worst"] = aggr_worst
config.aggregation_functions["best"]  = aggr_best

def aggr_countok_convert(num, count):
    if str(num)[-1] == "%":
        return int(num[:-1]) / 100.0 * count
    else:
        return int(num)

def aggr_countok(nodes, needed_for_ok=2, needed_for_warn=1):
    states = [ i[0]["state"] for i in nodes ]
    num_ok      = len([s for s in states if s == 0 ])
    num_nonok   = len([s for s in states if s > 0 ])
    num_pending = len(states) - num_ok - num_nonok
    num_nodes   = num_ok + num_nonok

    # We need to handle the special case "PENDING" separately.
    # Example: count is set to 50%. You have 10 nodes, all of
    # which are PENDING, then the outcome must be PENDING, not
    # CRIT.
    if num_nodes == 0: # All are pending
        return { "state": -1, "output": "" }

    # counts can be specified as integer (e.g. '2') or
    # as percentages (e.g. '70%').
    ok_count = aggr_countok_convert(needed_for_ok, num_nodes)
    warn_count = aggr_countok_convert(needed_for_warn, num_nodes)

    # Enough nodes are OK -> state is OK
    if num_ok >= ok_count:
        return { "state": 0, "output": "" }

    # Enough nodes OK in order to trigger warn level -> WARN
    elif num_ok >= warn_count:
        return { "state": 1, "output": "" }

    else:
        return { "state": 2, "output": "" }

config.aggregation_functions["count_ok"] = aggr_countok


def aggr_running_on(nodes, regex):
    first_check = nodes[0]

    # extract hostname we run on
    mo = re.match(regex, first_check[0]["output"])

    # if not found, then do normal aggregation with 'worst'
    if not mo or len(mo.groups()) == 0:
        state = config.aggregation_functions['worst'](nodes[1:])
        state["output"] += _(", running nowhere")
        return state

    running_on = mo.groups()[0]
    for state, node in nodes[1:]:
        for site, host in node["reqhosts"]:
            if host == running_on:
                state["output"] += _(", running on %s") % running_on
                return state

    # host we run on not found. Strange...
    return {"state": UNKNOWN, "output": _("running on unknown host '%s'") % running_on }

config.aggregation_functions['running_on'] = aggr_running_on


#      ____
#     |  _ \ __ _  __ _  ___  ___
#     | |_) / _` |/ _` |/ _ \/ __|
#     |  __/ (_| | (_| |  __/\__ \
#     |_|   \__,_|\__, |\___||___/
#                 |___/

# Just for debugging
def page_debug():
    compile_forest(config.user.id)

    html.header("BI Debug")
    render_forest()
    html.footer()


# Just for debugging, as well
def page_all():
    html.header("All")
    compile_forest(config.user.id)
    load_assumptions()
    for group, trees in g_tree_cache["forest"].items():
        html.write("<h2>%s</h2>" % group)
        for inst_args, tree in trees:
            state = execute_tree(tree)
            debug(state)
    html.footer()


def ajax_set_assumption():
    site = html.get_unicode_input("site")
    host = html.get_unicode_input("host")
    service = html.get_unicode_input("service")
    if service:
        key = (site, host, service)
    else:
        key = (site, host)
    state = html.var("state")
    load_assumptions()
    if state == 'none':
        del g_assumptions[key]
    else:
        g_assumptions[key] = int(state)
    save_assumptions()

def ajax_save_treestate():
    path_id = html.get_unicode_input("path")
    current_ex_level, path = path_id.split(":", 1)
    current_ex_level = int(current_ex_level)

    saved_ex_level = load_ex_level()

    if saved_ex_level != current_ex_level:
        html.set_tree_states('bi', {})
    html.set_tree_state('bi', path, html.var("state") == "open")
    html.save_tree_states()

    save_ex_level(current_ex_level)

def ajax_render_tree():
    aggr_group = html.get_unicode_input("group")
    reqhosts = [ tuple(sitehost.split('#')) for sitehost in html.var("reqhosts").split(',') ]
    aggr_title = html.get_unicode_input("title")
    omit_root = not not html.var("omit_root")
    boxes = not not html.var("boxes")
    only_problems = not not html.var("only_problems")

    # Make sure that BI aggregates are available
    if config.bi_precompile_on_demand:
        compile_forest(config.user.id, only_hosts = reqhosts, only_groups = [ aggr_group ])
    else:
        compile_forest(config.user.id)

    # Load current assumptions
    load_assumptions()

    # Now look for our aggregation
    if aggr_group not in g_tree_cache["forest"]:
        raise MKGeneralException(_("Unknown BI Aggregation group %s. Available are: %s") % (
            aggr_group, ", ".join(g_tree_cache["forest"].keys())))

    trees = g_tree_cache["forest"][aggr_group]
    for tree in trees:
        if tree["title"] == aggr_title:
            row = create_aggregation_row(tree)
            if row["aggr_state"]["state"] == None:
                continue # Not yet monitored, aggregation is not displayed
            row["aggr_group"] = aggr_group
            # ZUTUN: omit_root, boxes, only_problems has HTML-Variablen
            tdclass, htmlcode = render_tree_foldable(row, boxes=boxes, omit_root=omit_root,
                                             expansion_level=load_ex_level(), only_problems=only_problems, lazy=False)
            html.write(htmlcode)
            return

    raise MKGeneralException(_("Unknown BI Aggregation %s") % aggr_title)


def compute_output_message(effective_state, rule):
    output = []
    if effective_state["output"]:
        output.append(effective_state["output"])

    str_state = str(effective_state["state"])
    if str_state in rule.get("state_messages", {}):
        output.append(html.attrencode(rule["state_messages"][str_state]))

    return ", ".join(output)

def render_tree_json(row):
    expansion_level = int(html.var("expansion_level", 999))

    saved_expansion_level = load_ex_level()
    treestate = html.get_tree_states('bi')
    if expansion_level != saved_expansion_level:
        treestate = {}
        html.set_tree_states('bi', treestate)
        html.save_tree_states()


    def render_node_json(tree, show_host):
        is_leaf = len(tree) == 3
        if is_leaf:
            service = tree[2].get("service")
            if not service:
                title = _("Host status")
            else:
                title = service
        else:
            title = tree[2]["title"]

        json_node = {
            "title"             : title,
            # 2 -> This element is currently in a scheduled downtime
            # 1 -> One of the subelements is in a scheduled downtime
            "in_downtime"       : tree[0]["in_downtime"],
            "acknowledged"      : tree[0]["acknowledged"],
            "in_service_period" : tree[0]["in_service_period"],
        }

        # Check if we have an assumed state: comparing assumed state (tree[1]) with state (tree[0])
        if tree[1] and tree[0] != tree[1]:
            json_node["assumed"] = True
            effective_state = tree[1]
        else:
            json_node["assumed"] = False
            effective_state = tree[0]

        json_node["state"] = effective_state["state"]
        json_node["output"] = compute_output_message(effective_state, tree[2])
        return json_node


    def render_subtree_json(node, path, show_host):
        json_node = render_node_json(node, show_host)

        is_leaf = len(node) == 3
        is_next_level_open = len(path) <= expansion_level

        if not is_leaf and is_next_level_open:
            json_node["nodes"] = []
            for child_node in node[3]:
                if not child_node[2].get("hidden"):
                    new_path = path + [child_node[2]["title"]]
                    json_node["nodes"].append(render_subtree_json(child_node, new_path, show_host))

        return json_node

    root_node = row["aggr_treestate"]
    affected_hosts = row["aggr_hosts"]

    return "", render_subtree_json(root_node, [root_node[2]["title"]], len(affected_hosts) > 1)


def render_tree_foldable(row, boxes, omit_root, expansion_level, only_problems, lazy):
    saved_expansion_level = load_ex_level()
    treestate = html.get_tree_states('bi')
    if expansion_level != saved_expansion_level:
        treestate = {}
        html.set_tree_states('bi', treestate)
        html.save_tree_states()

    def render_subtree(tree, path, show_host):
        is_leaf = len(tree) == 3
        path_id = "/".join(path)
        is_open = treestate.get(path_id)
        if is_open == None:
            is_open = len(path) <= expansion_level

        # Make sure that in case of BI Boxes (omit root) the root level is *always* visible
        if not is_open and omit_root and len(path) == 1:
            is_open = True

        h = ""
        state = tree[0]
        omit_content = lazy and not is_open
        mousecode = 'onclick="bi_toggle_%s(this, %d);" ' % (boxes and "box" or "subtree", omit_content)

        # Variant: BI-Boxes
        if boxes:
            # Check if we have an assumed state: comparing assumed state (tree[1]) with state (tree[0])
            if tree[1] and tree[0] != tree[1]:
                addclass = " " + _("assumed")
                effective_state = tree[1]
            else:
                addclass = ""
                effective_state = tree[0]

            if is_leaf:
                leaf = "leaf"
                mc = ""
            else:
                leaf = "noleaf"
                mc = mousecode

            omit = omit_root and len(path) == 1
            if not omit:
                h += '<span id="%d:%s" %s class="bibox_box %s %s state state%s%s">' % (
                        expansion_level or 0, path_id, mc, leaf, is_open and "open" or "closed", effective_state["state"], addclass)
                if is_leaf:
                    h += aggr_render_leaf(tree, show_host, bare = True) # .replace(" ", "&nbsp;")
                else:
                    h += tree[2]["title"].replace(" ", "&nbsp;")
                h += '</span> '

            if not is_leaf and not omit_content:
                h += '<span class="bibox" style="%s">' % ((not is_open and not omit) and "display: none;" or "")
                parts = []
                for node in tree[3]:
                    new_path = path + [node[2]["title"]]
                    h += render_subtree(node, new_path, show_host)
                h += '</span>'
            return h

        # Variant: foldable trees
        else:
            if is_leaf: # leaf
                return aggr_render_leaf(tree, show_host, bare = boxes)

            h += '<span class=title>'
            is_empty = len(tree[3]) == 0
            if is_empty:
                mc = ''
            else:
                mc = mousecode

            css_class = "open" if is_open else "closed"

            h += aggr_render_node(tree, tree[2]["title"], show_host,
                                  mousecode=mc, img_class=css_class)
            if not is_empty:
                h += '<ul id="%d:%s" class="subtree %s">' % \
                        (expansion_level or 0, path_id, css_class)

                if not omit_content:
                    for node in tree[3]:
                        if not node[2].get("hidden"):
                            new_path = path + [node[2]["title"]]
                            h += '<li>' + render_subtree(node, new_path, show_host) + '</li>\n'
                h += '</ul>'
            return h + '</span>\n'

    tree = row["aggr_treestate"]
    if only_problems:
        tree = filter_tree_only_problems(tree)

    affected_hosts = row["aggr_hosts"]
    title = row["aggr_tree"]["title"]
    group = row["aggr_group"]
    url_id = html.urlencode_vars([
        ( "group", group ),
        ( "title", title ),
        ( "omit_root", omit_root and "yes" or ""),
        ( "boxes", boxes and "yes" or ""),
        ( "only_problems", only_problems and "yes" or ""),
        ( "reqhosts", ",".join('%s#%s' % sitehost for sitehost in affected_hosts) ),
    ])

    htmlcode = '<div id="%s" class=bi_tree_container>' % html.attrencode(url_id) + \
               render_subtree(tree, [tree[2]["title"]], len(affected_hosts) > 1) + \
               '</div>'
    return "aggrtree" + (boxes and "_box" or ""), htmlcode

def aggr_render_node(tree, title, show_host, mousecode=None, img_class=None):
    # Check if we have an assumed state: comparing assumed state (tree[1]) with state (tree[0])
    if tree[1] and tree[0] != tree[1]:
        addclass = " " + _("assumed")
        effective_state = tree[1]
    else:
        addclass = ""
        effective_state = tree[0]

    if tree[0]["in_downtime"] == 2:
        title = ('<img class="icon bi" src="images/icon_downtime.png" title="%s">' % \
            _("This element is currently in a scheduled downtime.")) + title
    elif tree[0]["in_downtime"] == 1:
        # only display host downtime if the service has no own downtime
        title = ('<img class="icon bi" src="images/icon_derived_downtime.png" title="%s">' % \
                 _("One of the subelements is in a scheduled downtime.")) + title

    if tree[0]["acknowledged"]:
        title = ('<img class="icon bi" src="images/icon_ack.png" title="%s">' % \
            _("This problem has been acknowledged.")) + title

    if not tree[0]["in_service_period"]:
        title = ('<img class="icon bi" src="images/icon_outof_serviceperiod.png" title="%s">' % \
            _("This element is currently not in its service period.")) + title


    h = '<span class="content state state%d%s">%s</span>\n' \
         % (effective_state["state"] if effective_state["state"] != None else -1, addclass, render_bi_state(effective_state["state"]))
    if mousecode:
        state_message = ""
        if str(effective_state["state"]) in tree[2].get("state_messages", {}):
            state_message = "<b class=bullet>&diams;</b>" + html.attrencode(tree[2]["state_messages"][str(effective_state["state"])])

        if img_class:
            h += '<img src="images/tree_black_closed.png" class="treeangle %s"%s>' % \
                                                                   (img_class, mousecode)
        h += '<span class="content name" %s>%s%s</span>' % (mousecode, title, state_message)
    else:
        h += title

    output = format_plugin_output(effective_state["output"])
    if output:
        output = "<b class=bullet>&diams;</b>" + output
    else:
        output = ""
    h += '<span class="content output">%s</span>\n' % output
    return h

def render_assume_icon(site, host, service):
    if service:
        key = (site, host, service)
    else:
        key = (site, host)
    ass = g_assumptions.get(key)
    # TODO: Non-Ascii-Characters do not work yet!
    mousecode = \
       u'onmouseover="this.style.cursor=\'pointer\';" ' \
       'onmouseout="this.style.cursor=\'auto\';" ' \
       'title="%s" ' \
       'onclick="toggle_assumption(this, \'%s\', \'%s\', \'%s\');" ' % \
         (_("Assume another state for this item (reload page to activate)"),
         # MIST: DAS HIER MUSS verfünftig für Javascript encodiert werden.
         # Das Ausgangsmaterial sind UTF-8 kodierte str-Objekte.
          site, host, service != None and service.replace('\\', '\\\\') or '')
    current = str(ass).lower()
    return u'<img state="%s" class=assumption %s src="images/assume_%s.png">\n' % (current, mousecode, current)

def aggr_render_leaf(tree, show_host, bare = False):
    site, host = tree[2]["host"]
    service = tree[2].get("service")
    if bare:
        content = u""
    else:
        content = u"" + render_assume_icon(site, host, service)

    # Four cases:
    # (1) zbghora17 . Host status   (show_host == True, service == None)
    # (2) zbghora17 . CPU load      (show_host == True, service != None)
    # (3) Host Status               (show_host == False, service == None)
    # (4) CPU load                  (show_host == False, service != None)

    if show_host or not service:
        host_url = html.makeuri_contextless([("view_name", "hoststatus"), ("site", site), ("host", host)], filename="view.py")

    if service:
        service_url = html.makeuri_contextless([("view_name", "service"), ("site", site), ("host", host), ("service", service)], filename="view.py")

    if show_host:
        content += '<a href="%s">%s</a><b class=bullet>&diams;</b>' % (host_url, host.replace(" ", "&nbsp;"))

    if not service:
        content += '<a href="%s">%s</a>' % (host_url, _("Host&nbsp;status"))
    else:
        content += '<a href="%s">%s</a>' % (service_url, service.replace(" ", "&nbsp;"))

    if bare:
        return content
    else:
        return aggr_render_node(tree, content, show_host)

def render_bi_state(state):
    return { PENDING: _("PD"),
             OK:      _("OK"),
             WARN:    _("WA"),
             CRIT:    _("CR"),
             UNKNOWN: _("UN"),
             MISSING: _("MI"),
             UNAVAIL: _("NA"),
    }.get(state, _("??"))


# Convert tree to tree contain only node in non-OK state
def filter_tree_only_problems(tree):
    state, assumed_state, node, subtrees = tree
    # remove subtrees in state OK
    new_subtrees = []
    for subtree in subtrees:
        effective_state = subtree[1] != None and subtree[1] or subtree[0]
        if effective_state["state"] not in [ OK, PENDING ]:
            if len(subtree) == 3:
                new_subtrees.append(subtree)
            else:
                new_subtrees.append(filter_tree_only_problems(subtree))

    return state, assumed_state, node, new_subtrees



#    ____        _
#   |  _ \  __ _| |_ __ _ ___  ___  _   _ _ __ ___ ___  ___
#   | | | |/ _` | __/ _` / __|/ _ \| | | | '__/ __/ _ \/ __|
#   | |_| | (_| | || (_| \__ \ (_) | |_| | | | (_|  __/\__ \
#   |____/ \__,_|\__\__,_|___/\___/ \__,_|_|  \___\___||___/
#

def create_aggregation_row(tree, status_info = None):
    tree_state = execute_tree(tree, status_info)

    # TODO: the tree state may include hosts the current user has
    #       no access to. Reason: The BI aggregation is always compiled
    #       with full host/service access.
    #       To fix this properly we need a list of all hosts/services
    #       available to this user

    state, assumed_state, node, subtrees = tree_state
    eff_state = state
    if assumed_state != None:
        eff_state = assumed_state

    output = compute_output_message(eff_state, node)

    return {
        "aggr_tree"            : tree,
        "aggr_treestate"       : tree_state,
        "aggr_state"           : state,          # state disregarding assumptions
        "aggr_assumed_state"   : assumed_state,  # is None, if there are no assumptions
        "aggr_effective_state" : eff_state,      # is assumed_state, if there are assumptions, else real state
        "aggr_name"            : node["title"],
        "aggr_output"          : output,
        "aggr_hosts"           : node["reqhosts"],
        "aggr_function"        : node["func"],
    }


def table(columns, add_headers, only_sites, limit, filters):
    load_assumptions() # user specific, always loaded
    # Hier müsste man jetzt die Filter kennen, damit man nicht sinnlos
    # alle Aggregationen berechnet.
    rows = []

    # Apply group filter. This is important for performance. We
    # must not compute any aggregations from other groups and filter
    # later out again.
    only_group = None
    only_service = None
    only_aggr_name = None

    for filter in filters:
        if filter.name == "aggr_group":
            val = filter.selected_group()
            if val:
                only_group = val
        elif filter.name == "aggr_service":
            only_service = filter.service_spec()
        elif filter.name == "aggr_name":
            only_aggr_name = filter.value().get("aggr_name")
        # TODO: can be further improved by filtering aggr_name_regex
        #       See BITextFilter(Filter): filter_table(self, rows)

    if config.bi_precompile_on_demand and only_group:
        # optimized mode: if aggregation group known only precompile this one
        compile_forest(config.user.id, only_groups = [ only_group ])
    else:
        # classic mode: precompile everything
        compile_forest(config.user.id)

    # TODO: Optimation of affected_hosts filter!
    if only_service:
        affected = g_tree_cache["affected_services"].get(only_service)
        if affected == None:
            items = []
        else:
            by_groups = {}
            for group, aggr in affected:
                entries = by_groups.get(group, [])
                entries.append(aggr)
                by_groups[group] = entries
            items = by_groups.items()
    else:
        items = g_tree_cache["forest"].items()


    online_sites = set(map(lambda x: x[0], get_current_sitestats()["online_sites"]))

    for group, trees in items:
        if only_group not in [ None, group ]:
            continue

        for tree in trees:
            if only_aggr_name and only_aggr_name != tree.get("title"):
                continue

            aggr_sites = set(x[0] for x in tree.get("reqhosts"))
            if not aggr_sites.intersection(online_sites):
                continue

            row = create_aggregation_row(tree)
            if row["aggr_state"]["state"] == None:
                continue # Not yet monitored, aggregation is not displayed

            row["aggr_group"] = group
            rows.append(row)
            if not html.check_limit(rows, limit):
                return rows

    return rows


# Table of all host aggregations, i.e. aggregations using data from exactly one host
def hostname_table(columns, add_headers, only_sites, limit, filters):
    return singlehost_table(columns, add_headers, only_sites, limit, filters, True, bygroup=False)

def hostname_by_group_table(columns, add_headers, only_sites, limit, filters):
    return singlehost_table(columns, add_headers, only_sites, limit, filters, True, bygroup=True)

def host_table(columns, add_headers, only_sites, limit, filters):
    return singlehost_table(columns, add_headers, only_sites, limit, filters, False, bygroup=False)

def singlehost_table(columns, add_headers, only_sites, limit, filters, joinbyname, bygroup):
    log("--------------------------------------------------------------------")
    log("* Starting to compute singlehost_table (joinbyname = %s)" % joinbyname)
    load_assumptions() # user specific, always loaded
    log("* Assumptions are loaded.")

    # Create livestatus filter for filtering out hosts. We can
    # simply use all those filters since we have a 1:n mapping between
    # hosts and host aggregations
    filter_code = ""
    for filt in filters:
        header = filt.filter("bi_host_aggregations")
        if not header.startswith("Sites:"):
            filter_code += header

    log("* Getting status information about hosts...")
    host_columns = filter(lambda c: c.startswith("host_"), columns)
    hostrows = get_status_info_filtered(filter_code, only_sites, limit, host_columns, config.bi_precompile_on_demand, bygroup)
    log("* Got %d host rows" % len(hostrows))

    # Apply aggregation group filter. This is important for performance. We
    # must not compute any aggregations from other aggregation groups and filter
    # them later out again.
    only_groups = None
    for filt in filters:
        if filt.name == "aggr_group":
            val = filt.selected_group()
            if val:
                only_groups = [ filt.selected_group() ]

    if config.bi_precompile_on_demand:
        log("* Compiling forest on demand...")
        compile_forest(config.user.id, only_groups = only_groups,
                       only_hosts = [ (h['site'], h['name']) for h in hostrows ])
    else:
        log("* Compiling forest...")
        compile_forest(config.user.id)

    # rows by site/host - needed for later cluster state gathering
    if config.bi_precompile_on_demand and not joinbyname:
        row_dict = dict([ ((r['site'], r['name']), r) for r in hostrows])

    rows = []
    # Now compute aggregations of these hosts
    log("* Assembling host rows...")

    # Special optimization for joinbyname
    if joinbyname:
        rows_by_host = {}
        for hostrow in hostrows:
            site = hostrow["site"]
            host = hostrow["name"]
            rows_by_host[(site, host)] = hostrow

    for hostrow in hostrows:
        site = hostrow["site"]
        host = hostrow["name"]
        # In case of joinbyname we deal with aggregations that bare the
        # name of one host, but might contain states of multiple hosts.
        # status_info cannot be filled from one row in that case. We
        # try to optimize by assuming that all data that we need is being
        # displayed in the same view and the information thus being present
        # in some of the other hostrows.
        if joinbyname:
            status_info = {}
            aggrs = g_tree_cache["aggregations_by_hostname"].get(host, [])
            # collect all the required host of all matching aggregations
            for a in aggrs:
                reqhosts = a[1]["reqhosts"]
                for sitehost in reqhosts:
                    if sitehost not in rows_by_host:
                        # This one is missing. Darn. Cancel it.
                        status_info = None
                        break
                    else:
                        row = rows_by_host[sitehost]
                        status_info[sitehost] = [
                             row["state"],
                             row["hard_state"],
                             row["plugin_output"],
                             hostrow["scheduled_downtime_depth"] > 0,
                             not not hostrow["acknowledged"],
                             hostrow["host_in_service_period"],
                             row["services_with_fullstate"] ]
                if status_info == None:
                    break
        else:
            aggrs = g_tree_cache["host_aggregations"].get((site, host), [])
            status_info = { (site, host) : [
                hostrow["state"],
                hostrow["hard_state"],
                hostrow["plugin_output"],
                hostrow["scheduled_downtime_depth"] > 0,
                not not hostrow["acknowledged"],
                hostrow["host_in_service_period"],
                hostrow["services_with_fullstate"] ] }

        for group, aggregation in aggrs:
            row = hostrow.copy()

            # on demand compile: host aggregations of clusters need data of several hosts.
            # It is not enough to only process the hostrow. The status_info construct must
            # also include the data of the other required hosts.
            if config.bi_precompile_on_demand and not joinbyname and len(aggregation['reqhosts']) > 1:
                status_info = {}
                for site, host in aggregation['reqhosts']:
                    this_row = row_dict.get((site, host))
                    if this_row:
                        status_info[(site, host)] = [
                            this_row['state'],
                            this_row['hard_state'],
                            this_row['plugin_output'],
                            this_row["scheduled_downtime_depth"] > 0,
                            not not this_row["acknowledged"],
                            this_row["host_in_service_period"],
                            this_row['services_with_fullstate'],
                        ]

            new_row = create_aggregation_row(aggregation, status_info)
            if new_row["aggr_state"]["state"] == None:
                continue # Not yet monitored, aggregation is not displayed

            row.update(new_row)
            row["aggr_group"] = group
            rows.append(row)
            if not html.check_limit(rows, limit):
                return rows


    log("* Assembled %d rows." % len(rows))
    return rows


#     _   _      _
#    | | | | ___| |_ __   ___ _ __ ___
#    | |_| |/ _ \ | '_ \ / _ \ '__/ __|
#    |  _  |  __/ | |_) |  __/ |  \__ \
#    |_| |_|\___|_| .__/ \___|_|  |___/
#                 |_|

def debug(x):
    import pprint
    p = pprint.pformat(x)
    html.write("<pre>%s</pre>\n" % p)

def load_assumptions():
    global g_assumptions
    g_assumptions = config.user.load_file("bi_assumptions", {})

def save_assumptions():
    config.user.save_file("bi_assumptions", g_assumptions)

def load_ex_level():
    return config.user.load_file("bi_treestate", (None, ))[0]

def save_ex_level(current_ex_level):
    config.user.save_file("bi_treestate", (current_ex_level, ))

def status_tree_depth(tree):
    if len(tree) == 3:
        return 1
    else:
        subtrees = tree[3]
        maxdepth = 0
        for node in subtrees:
            maxdepth = max(maxdepth, status_tree_depth(node))
        return maxdepth + 1

def is_part_of_aggregation(what, site, host, service):
    compile_forest(config.user.id)
    if what == "host":
        return (site, host) in g_tree_cache["affected_hosts"]
    else:
        return (site, host, service) in g_tree_cache["affected_services"]

def get_state_name(node):
    if node[1]['type'] == NT_LEAF:
        if 'service' in node[1]:
            return service_state_names[node[0]['state']]
        else:
            return host_state_names[node[0]['state']]
    else:
        return service_state_names[node[0]['state']]


def migrate_bi_configuration():
    def convert_aggregation(aggr_tuple):
        if type(aggr_tuple[0]) == dict:
            return aggr_tuple # already converted

        options = {}
        map_class_to_key = {
            config.DISABLED:     "disabled",
            config.HARD_STATES:  "hard_states",
            config.DT_AGGR_WARN: "downtime_aggr_warn",
        }
        for idx, token in enumerate(list(aggr_tuple)):
            if token in map_class_to_key:
                options[map_class_to_key[token]] = True
            else:
                aggr_tuple = aggr_tuple[idx:]
                break
        return (options,) + aggr_tuple

    if config.bi_packs:
        for pack in config.bi_packs.values():
            config.aggregations += map(convert_aggregation, pack["aggregations"])
            config.host_aggregations += map(convert_aggregation, pack["host_aggregations"])
            config.aggregation_rules.update(pack["rules"])
        config.bi_packs = {}
    else:
        if config.host_aggregations and type(config.host_aggregations[0]) != dict:
            config.host_aggregations = map(convert_aggregation, config.host_aggregations)
        if config.aggregations and type(config.aggregations[0]) != dict:
            config.aggregations = map(convert_aggregation, config.aggregations)

