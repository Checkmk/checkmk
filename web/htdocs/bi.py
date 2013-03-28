#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import config, re, pprint, time
import weblib, htmllib
from lib import *


# Python 2.3 does not have 'set' in normal namespace.
# But it can be imported from 'sets'
try:
    set()
except NameError:
    from sets import Set as set

# Datastructures and functions needed before plugins can be loaded
loaded_with_language = False

# Load all view plugins
def load_plugins():
    global loaded_with_language
    if loaded_with_language == current_language:
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
MISSING = -2
PENDING = -1
OK = 0
WARN = 1
CRIT = 2
UNKNOWN = 3
UNAVAIL = 4

service_state_names = { OK:"OK", WARN:"WARN", CRIT:"CRIT", UNKNOWN:"UNKNOWN", PENDING:"PENDING", UNAVAIL:"UNAVAILABLE"}
host_state_names = { 0:"UP", 1:"DOWN", 2:"UNREACHABLE" }

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


# global variables
g_cache = {}                  # per-user cache
g_config_information = None   # for invalidating cache after config change
did_compilation = False       # Is set to true if anything has been compiled

# Load the static configuration of all services and hosts (including tags)
# without state.
def load_services(cache, only_hosts):
    global g_services, g_services_by_hostname
    g_services = {}
    g_services_by_hostname = {}

    # TODO: At the moment the data is always refetched. This could really
    # be optimized. Maybe create a cache which fetches data for the given
    # list of hosts, puts it to a cache and then only fetch the additionally
    # needed information which are not cached yet in future requests

    # Create optional host filter
    filter_txt = 'Filter: custom_variable_names < _REALNAME\n' # drop summary hosts
    if only_hosts:
        # Only fetch the requested hosts
        host_filter = []
        for site, hostname in only_hosts:
            host_filter.append('Filter: name = %s\n' % hostname)
        filter_txt = ''.join(host_filter)
        filter_txt += "Or: %d\n" % len(host_filter)

    html.live.set_prepend_site(True)
    html.live.set_auth_domain('bi')
    data = html.live.query("GET hosts\n"
                           +filter_txt+
                           "Columns: name custom_variable_names custom_variable_values services childs parents\n")
    html.live.set_prepend_site(False)
    html.live.set_auth_domain('read')

    for site, host, varnames, values, svcs, childs, parents in data:
        vars = dict(zip(varnames, values))
        tags = vars.get("TAGS", "").split(" ")
        entry = (tags, svcs, childs, parents)
        g_services[(site, host)] = entry
        g_services_by_hostname.setdefault(host, []).append((site, entry))

# Keep complete list of time stamps of configuration
# and start of each site. Unreachable sites are registered
# with 0.
def cache_needs_update():
    new_config_information = [tuple(config.modification_timestamps)]
    for site in html.site_status.values():
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

def reused_compilation():
    return used_cache and not did_compilation

# Returns a sorted list of aggregation group names
def aggregation_groups():
    if config.bi_precompile_on_demand:
        # on demand: show all configured groups
        group_names = set([])
        for a in config.aggregations + config.host_aggregations:
            if type(a[0]) == list:
                group_names.update(a[0])
            else:
                group_names.add(a[0])
        group_names = list(group_names)

    else:
        # classic mode: precompile all and display only groups with members
        compile_forest(config.user_id)
        group_names = list(set([ group for group, trees in g_user_cache["forest"].items() if trees ]))

    return sorted(group_names, cmp = lambda a,b: cmp(a.lower(), b.lower()))

def log(s):
    if compile_logging():
        file(config.bi_compile_log, "a").write(s)

# Precompile the forest of BI rules. Forest? A collection of trees.
# The compiled forest does not contain any regular expressions anymore.
# Everything is resolved. Sites, hosts and services are hardcoded. The
# aggregation functions are still left as names. That way the forest
# printable (and storable in Python syntax to a file).
def compile_forest(user, only_hosts = None, only_groups = None):
    global g_cache, g_user_cache
    global used_cache, did_compilation

    new_config_information = cache_needs_update()
    if new_config_information:
        log("Configuration has changed. Forcing recompile.\n")
        g_cache = {}
        global g_config_information
        g_config_information = new_config_information

    # OPTIMIZE: All users that have the permissing bi.see_all
    # can use the same cache.
    if config.may("bi.see_all"):
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
    # g_user_cache is a global variable for all succeeding functions, so
    # that they do not need to check the user again
    cache = g_cache.get(user)
    if cache:
        g_user_cache = cache
    else:
        # Initialize empty caching structure
        cache = empty_user_cache()
        g_user_cache = cache

    if g_user_cache["compiled_all"]:
        log('PID: %d - Already compiled everything\n' % os.getpid())
        used_cache = True
        return # In this case simply skip further compilations

    # If we have previously only partly compiled and now there is no
    # filter, then throw away partly compiled data.
    if (cache["compiled_hosts"] or cache["compiled_groups"]) \
       and (not config.bi_precompile_on_demand \
       or (config.bi_precompile_on_demand and not only_groups and not only_hosts)):
        log("Invalidating incomplete cache, since we compile all now.\n")
        cache = empty_user_cache()
        g_user_cache = cache

    # Reduces a list of hosts by the already compiled hosts
    def to_compile(objects, what):
        todo = []
        for obj in objects:
            if obj not in cache['compiled_' + what]:
                todo.append(obj)
        return todo

    if only_hosts and cache['compiled_hosts']:
        # if only hosts is given and there are already compiled hosts
        # check wether or not hosts are not compiled yet
        only_hosts = to_compile(only_hosts, 'hosts')
        if not only_hosts:
            log('PID: %d - All requested hosts have already been compiled\n' % os.getpid())
            used_cache = True
            return # Nothing to do - everything is cached

    if only_groups and cache['compiled_groups']:
        only_groups = to_compile(only_groups, 'groups')
        if not only_groups:
            log('PID: %d - All requested groups have already been compiled\n' % os.getpid())
            used_cache = True
            return # Nothing to do - everything is cached

    # Set a flag that anything has been compiled in this call
    did_compilation = True

    # Load all (needed) services
    # The only_hosts variable is only set in "precompile on demand" mode to filter out
    # the needed hosts/services if possible. It is used in the load_services() function
    # to reduce the amount of hosts/services. Reducing the host/services leads to faster
    # compilation.
    load_services(cache, only_hosts)

    log("This request: User: %s, Only-Groups: %r, Only-Hosts: %s PID: %d\n"
        % (user, only_groups, only_hosts, os.getpid()))

    if compile_logging():
        before   = time.time()
        num_new_host_aggrs  = 0
        num_new_multi_aggrs = 0

    # When only_hosts is given only use the single host aggregations for further processing.
    # The only_hosts variable is only populated for single host tables.
    if only_hosts:
        aggr_list = [(AGGR_HOST, config.host_aggregations)]
    else:
        aggr_list = [(AGGR_MULTI, config.aggregations), (AGGR_HOST, config.host_aggregations)]

    single_affected_hosts = []
    for aggr_type, aggregations in aggr_list:
        for entry in aggregations:
            if len(entry) < 3:
                raise MKConfigError(_("<h1>Invalid aggregation <tt>%s</tt>'</h1>"
                                      "Must have at least 3 entries (has %d)") % (entry, len(entry)))

            if type(entry[0]) == list:
                groups = entry[0]
            else:
                groups = [ entry[0] ]
            groups_set = set(groups)

            if only_groups and not groups_set.intersection(only_groups):
                log('Skip aggr (No group of the aggr has been requested: %r)\n' % groups)
                continue # skip not requested groups if filtered by groups

            if len(groups_set) == len(groups_set.intersection(cache['compiled_groups'])):
                log('Skip aggr (All groups have already been compiled\n')
                continue # skip if all groups have already been compiled

            new_entries = compile_rule_node(aggr_type, entry[1:], 0)

            for this_entry in new_entries:
                remove_empty_nodes(this_entry)

            new_entries = [ e for e in new_entries if len(e["nodes"]) > 0 ]

            if compile_logging():
                if aggr_type == AGGR_HOST:
                    num_new_host_aggrs += len(new_entries)
                else:
                    num_new_multi_aggrs += len(new_entries)

            # enter new aggregations into dictionary for these groups
            for group in groups:
                if group in cache['compiled_groups']:
                    log('Skip aggr (group %s already compiled)\n' % group)
                    continue # the group has already been compiled completely

                if group not in cache['forest']:
                    cache['forest'][group] = new_entries
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

    if compile_logging():
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

        log("This request:\n"
            "  User: %s, Only-Groups: %r, Only-Hosts: %s\n"
            "  PID: %d, Processed %d services on %d hosts in %.3f seconds.\n"
            "\n"
            "  %d compiled multi aggrs, %d compiled host aggrs, %d compiled groups\n"
            "Cache:\n"
            "  Everything compiled: %r\n"
            "  %d compiled multi aggrs, %d compiled host aggrs, %d compiled groups\n"
            "Config:\n"
            "  Multi-Aggregations: %d, Host-Aggregations: %d\n"
            "\n"
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

def compile_logging():
    return config.bi_compile_log is not None

# Execute an aggregation rule, but prepare arguments
# and iterate FOREACH first
def compile_rule_node(aggr_type, calllist, lvl):
    # Lookup rule source code
    rulename, arglist = calllist[-2:]
    what = calllist[0]
    if rulename not in config.aggregation_rules:
        raise MKConfigError(_("<h1>Invalid configuration in variable <tt>aggregations</tt></h1>"
                "There is no rule named <tt>%s</tt>. Available are: <tt>%s</tt>") %
                (rulename, "</tt>, </tt>".join(config.aggregation_rules.keys())))
    rule = config.aggregation_rules[rulename]

    # Execute FOREACH: iterate over matching hosts/services.
    # Create an argument list where $1$, $2$, ... are
    # substituted with matched strings for each match.
    if what in [
            config.FOREACH_HOST,
            config.FOREACH_CHILD,
            config.FOREACH_PARENT,
            config.FOREACH_SERVICE ]:
        matches = find_matching_services(aggr_type, what, calllist[1:])
        new_elements = []
	handled_args = set([]) # avoid duplicate rule incarnations
        for match in matches:
            args = [ substitute_matches(a, match) for a in arglist ]
	    if tuple(args) not in handled_args:
                new_elements += compile_aggregation_rule(aggr_type, rule, args, lvl)
		handled_args.add(tuple(args))
        return new_elements

    else:
        return compile_aggregation_rule(aggr_type, rule, arglist, lvl)


def find_matching_services(aggr_type, what, calllist):
    # honor list of host tags preceding the host_re
    if type(calllist[0]) == list:
        required_tags = calllist[0]
        calllist = calllist[1:]
    else:
        required_tags = []

    if len(calllist) == 0:
        raise MKConfigError(_("Invalid syntax in FOREACH_..."))

    host_re = calllist[0]
    if what in [ config.FOREACH_HOST, config.FOREACH_CHILD, config.FOREACH_PARENT ]:
        service_re = config.HOST_STATE
    else:
        service_re = calllist[1]

    matches = set([])
    honor_site = SITE_SEP in host_re

    if host_re.startswith("^(") and host_re.endswith(")$"):
        # Exact host match
        middle = host_re[2:-2]
        if middle in g_services_by_hostname:
            entries = [ ((e[0], host_re), e[1]) for e in g_services_by_hostname[middle] ]
            host_re = "(.*)"
    elif not honor_site and not '*' in host_re and not '$' in host_re and not '|' in host_re:
        # Exact host match
        entries = [ ((e[0], host_re), e[1]) for e in g_services_by_hostname.get(host_re, []) ]

    else:
        # All services
        entries = g_services.items()

    # TODO: Hier könnte man - wenn der Host bekannt ist, effektiver arbeiten, als
    # komplett alles durchzugehen.
    for (site, hostname), (tags, services, childs, parents) in entries:
        # Skip already compiled hosts
        if aggr_type == AGGR_HOST and (site, hostname) in g_user_cache['compiled_hosts']:
            continue

        host_matches = None
        if not match_host_tags(tags, required_tags):
            continue

        host_matches = None

        if host_re == '(.*)':
            host_matches = (hostname, )
        else:
            # For regex to have '$' anchor for end. Users might be surprised
            # to get a prefix match on host names. This is almost never what
            # they want. For services this is useful, however.
            if host_re.endswith("$"):
                anchored = host_re
            else:
                anchored = host_re + "$"

            # In order to distinguish hosts with the same name on different
            # sites we prepend the site to the host name. If the host specification
            # does not contain the site separator - though - we ignore the site
            # an match the rule for all sites.
            if honor_site:
                host_matches = do_match(anchored, "%s%s%s" % (site, SITE_SEP, hostname))
            else:
                host_matches = do_match(anchored, hostname)

        if host_matches != None:
            if what == config.FOREACH_CHILD:
                list_of_matches  = [ host_matches + (child,) for child in childs ]
            if what == config.FOREACH_PARENT:
                list_of_matches  = [ host_matches + (parent,) for parent in parents ]
            else:
                list_of_matches = [ host_matches ]

            for host_matches in list_of_matches:
                if service_re == config.HOST_STATE:
                    matches.add(host_matches)
                else:
                    for service in services:
                        mo = (service_re, service)
                        if mo in service_nomatch_cache:
                            continue
                        m = regex(service_re).match(service)
                        if m:
                            svc_matches = tuple(m.groups())
                            matches.add(host_matches + svc_matches)
                        else:
                            service_nomatch_cache.add(mo)

    matches = list(matches)
    matches.sort()
    return matches

def do_match(reg, text):
    mo = regex(reg).match(text)
    if not mo:
        return None
    else:
        return tuple(mo.groups())


def substitute_matches(arg, match):
    for n, m in enumerate(match):
        arg = arg.replace("$%d$" % (n+1), m)
    return arg


# Debugging function
def render_forest():
    for group, trees in g_user_cache["forest"].items():
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

# Checks wether or not a rule node has no subnodes
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
        global g_remaining_refs
        g_remaining_refs = []

    if len(rule) != 4:
        raise MKConfigError(_("<h3>Invalid aggregation rule</h1>"
                "Aggregation rules must contain four elements: description, argument list, "
                "aggregation function and list of nodes. Your rule has %d elements: "
                "<pre>%s</pre>") % (len(rule), pprint.pformat(rule)))

    if lvl == 50:
        raise MKConfigError(_("<h3>Depth limit reached</h3>"
                "The nesting level of aggregations is limited to 50. You either configured "
                "too many levels or built an infinite recursion. This happened in rule <pre>%s</pre>")
                  % pprint.pformat(rule))

    description, arglist, funcname, nodes = rule

    # check arguments and convert into dictionary
    if len(arglist) != len(args):
        raise MKConfigError(_("<h1>Invalid rule usage</h1>"
                "The rule '%s' needs %d arguments: <tt>%s</tt><br>"
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
                    if type(n) in [ str, unicode, list ]:
                        n = subst_vars(n, arginfo)
                    calllist.append(n)
                matches = find_matching_services(aggr_type, node[0], calllist)
                new_elements = []
		handled_args = set([]) # avoid duplicate rule incarnations
                for match in matches:
                    sub_arginfo = dict([(str(n+1), x) for (n,x) in enumerate(match)])
		    if tuple(args) + match not in handled_args:
                        new_elements += compile_leaf_node(subst_vars(node[-2], sub_arginfo), subst_vars(node[-1], sub_arginfo))
		        handled_args.add(tuple(args) + match)

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
    tags, all_services, childs, parents = g_services[hostspec]
    all_services = set(all_services)
    for site, host, service in find_all_leaves(aggregation):
        if (site, host) == hostspec:
            all_services.discard(service)
    remaining = list(all_services)
    remaining.sort()
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

# replace variables in a string
def subst_vars(pattern, arginfo):
    if type(pattern) == list:
        return [subst_vars(x, arginfo) for x in pattern ]

    for name, value in arginfo.items():
        if type(pattern) in [ str, unicode ]:
            pattern = pattern.replace('$'+name+'$', value)
    return pattern

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

def compile_leaf_node(host_re, service_re = config.HOST_STATE):
    found = []
    honor_site = SITE_SEP in host_re
    if not honor_site and not '*' in host_re and not '$' in host_re and not '|' in host_re:
        entries = [ ((e[0], host_re), e[1]) for e in g_services_by_hostname.get(host_re, []) ]

    else:
        entries = g_services.items()

    # TODO: If we already know the host we deal with, we could avoid this loop
    for (site, hostname), (tags, services, childs, parents) in entries:
        # If host ends with '|@all', we need to check host tags instead
        # of regexes.
        if host_re.endswith('|@all'):
            if not match_host_tags(host_re[:-5], tags):
                continue
        elif host_re != '@all':
            # For regex to have '$' anchor for end. Users might be surprised
            # to get a prefix match on host names. This is almost never what
            # they want. For services this is useful, however.
            if host_re.endswith("$"):
                anchored = host_re
            else:
                anchored = host_re + "$"

            # In order to distinguish hosts with the same name on different
            # sites we prepend the site to the host name. If the host specification
            # does not contain the site separator - though - we ignore the site
            # an match the rule for all sites.
            if honor_site:
                if not regex(anchored).match("%s%s%s" % (site, SITE_SEP, hostname)):
                    continue
            else:
                if not regex(anchored).match(hostname):
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
                # found.append({"type" : NT_LEAF,
                #               "reqhosts" : [(site, hostname)],
                #               "host" : (site, hostname),
                #               "service" : "FOO",
                #               "title" : "Foo bar",
                #               })
                # continue


                for service in services:
                    mo = (service_re, service)
                    if mo in service_nomatch_cache:
                        continue
                    m = regex(service_re).match(service)
                    if m:
                        found.append({"type"     : NT_LEAF,
                                      "reqhosts" : [(site, hostname)],
                                      "host"     : (site, hostname),
                                      "service"  : service,
                                      "title"    : "%s - %s" % (hostname, service)} )
                    else:
                        service_nomatch_cache.add(mo)

    found.sort()
    return found


service_nomatch_cache = set([])

regex_cache = {}
def regex(r):
    rx = regex_cache.get(r)
    if rx:
        return rx
    try:
        rx = re.compile(r)
    except Exception, e:
        raise MKConfigError(_("Invalid regular expression '%s': %s") % (r, e))
    regex_cache[r] = rx
    return rx




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
    if status_info == None:
        required_hosts = tree["reqhosts"]
        status_info = get_status_info(required_hosts)
    return execute_node(tree, status_info)

def execute_node(node, status_info):
    if node["type"] == NT_LEAF:
        return execute_leaf_node(node, status_info)
    else:
        return execute_rule_node(node, status_info)


def execute_leaf_node(node, status_info):

    site, host = node["host"]
    service = node.get("service")

    # Get current state of host and services
    status = status_info.get((site, host))
    if status == None:
        return ({ "state" : MISSING, "output" : _("Host %s not found") % host}, None, node)
    host_state, host_output, service_state = status

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
                state, has_been_checked, output = entry[1:]
                if has_been_checked == 0:
                    output = _("This service has not been checked yet")
                    state = PENDING
                state = {"state":state, "output":output}
                if state_assumption != None:
                    assumed_state = {"state":state_assumption,
                                     "output" : _("Assumed to be %s") % service_state_names[state_assumption]}
                else:
                    assumed_state = None
                return (state, assumed_state, node)

        return ({"state":MISSING, "output": _("This host has no such service")}, None, node)

    else:
        aggr_state = {0:OK, 1:CRIT, 2:UNKNOWN, -1:PENDING}[host_state]
        state = {"state":aggr_state, "output" : host_output}
        if state_assumption != None:
            assumed_state = {"state": state_assumption,
                             "output" : _("Assumed to be %s") % host_state_names[state_assumption]}
        else:
            assumed_state = None
        return (state, assumed_state, node)


def execute_rule_node(node, status_info):
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
    one_assumption = False
    for n in node["nodes"]:
        result = execute_node(n, status_info) # state, assumed_state, node [, subtrees]
        subtrees.append(result)

        node_states.append((result[0], result[2]))
        if result[1] != None:
            assumed_states.append((result[1], result[2]))
            one_assumption = True
        else:
            # no assumption, take real state into assumption array
            assumed_states.append(node_states[-1])

    state = func(*([node_states] + funcargs))
    if one_assumption:
        assumed_state = func(*([assumed_states] + funcargs))
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
        html.live.set_auth_domain('bi')
        data = html.live.query(
                "GET hosts\n"
                "Columns: name state plugin_output services_with_info\n"
                + filter)
        html.live.set_auth_domain('read')
        tuples += [((site, e[0]), e[1:]) for e in data]

    return dict(tuples)

# This variant of the function is configured not with a list of
# hosts but with a livestatus filter header and a list of columns
# that need to be fetched in any case
def get_status_info_filtered(filter_header, only_sites, limit, add_columns, fetch_parents = True):
    columns = [ "name", "state", "plugin_output", "services_with_info", "parents" ] + add_columns

    html.live.set_only_sites(only_sites)
    html.live.set_prepend_site(True)

    query = "GET hosts\n"
    query += "Columns: " + (" ".join(columns)) + "\n"
    query += filter_header


    if config.debug_livestatus_queries \
            and html.output_format == "html" and 'W' in html.display_options:
        html.write('<div class="livestatus message" onmouseover="this.style.display=\'none\';">'
                           '<tt>%s</tt></div>\n' % (query.replace('\n', '<br>\n')))

    html.live.set_only_sites(only_sites)
    html.live.set_prepend_site(True)

    html.live.set_auth_domain('bi')
    data = html.live.query(query)

    html.live.set_prepend_site(False)
    html.live.set_only_sites(None)
    html.live.set_auth_domain('read')

    headers = [ "site" ] + columns
    hostnames = [ row[1] for row in data ]
    rows = [ dict(zip(headers, row)) for row in data]

    # on demand compile: if parents have been found, also fetch data of the parents.
    # This is needed to allow cluster hosts (which have the nodes as parents) in the
    # host_aggregation construct.
    if fetch_parents:
        parent_filter = []
        for row in data:
            parent_filter += [ 'Filter: name = %s\n' % p for p in row[5] ]
        parent_filter_txt = ''.join(parent_filter)
        parent_filter_txt += 'Or: %d\n' % len(parent_filter)
        for row in  get_status_info_filtered(filter_header, only_sites, limit, add_columns, False):
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

def aggr_nth_state(nodelist, n, worst_state):
    states = [ i[0]["state"] for i in nodelist ]
    state = x_best_state(states, n)

    # limit to worst state
    if state_weight(state) > state_weight(worst_state):
        state = worst_state

    return { "state" : state, "output" : "" }

def aggr_worst(nodes, n = 1, worst_state = CRIT):
    return aggr_nth_state(nodes, -int(n), int(worst_state))

def aggr_best(nodes, n = 1, worst_state = CRIT):
    return aggr_nth_state(nodes, int(n), int(worst_state))

config.aggregation_functions["worst"] = aggr_worst
config.aggregation_functions["best"]  = aggr_best

def aggr_countok_convert(num, count):
    if str(num).endswith('%'):
        return int(num[:-1]) / 100.0 * count
    else:
        return int(num)

def aggr_countok(nodes, needed_for_ok=2, needed_for_warn=1):
    states = [ i[0]["state"] for i in nodes ]
    num_ok = len([s for s in states if s == 0 ])

    # counts can be specified as integer (e.g. '2') or
    # as percentages (e.g. '70%').


    if num_ok >= aggr_countok_convert(needed_for_ok, len(states)):
        return { "state" : 0, "output" : "" }
    elif num_ok >= aggr_countok_convert(needed_for_warn, len(states)):
        return { "state" : 1, "output" : "" }
    else:
        return { "state" : 2, "output" : "" }

config.aggregation_functions["count_ok"] = aggr_countok


import re

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
    compile_forest(config.user_id)

    html.header("BI Debug")
    render_forest()
    html.footer()


# Just for debugging, as well
def page_all():
    html.header("All")
    compile_forest(config.user_id)
    load_assumptions()
    for group, trees in g_user_cache["forest"].items():
        html.write("<h2>%s</h2>" % group)
        for inst_args, tree in trees:
            state = execute_tree(tree)
            debug(state)
    html.footer()


def ajax_set_assumption():
    site = html.var_utf8("site")
    host = html.var_utf8("host")
    service = html.var_utf8("service")
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
    path_id = html.var("path")
    current_ex_level, path = path_id.split(":", 1)
    current_ex_level = int(current_ex_level)

    saved_ex_level = load_ex_level()

    if saved_ex_level != current_ex_level:
        weblib.set_tree_states('bi', {})
    weblib.set_tree_state('bi', path, html.var("state") == "open")
    weblib.save_tree_states()

    save_ex_level(current_ex_level)

def ajax_render_tree():
    aggr_group = html.var("group")
    reqhosts = [ tuple(sitehost.split('#')) for sitehost in html.var("reqhosts").split(',') ]
    aggr_title = html.var("title")
    omit_root = not not html.var("omit_root")
    boxes = not not html.var("boxes")
    only_problems = not not html.var("only_problems")

    # Make sure that BI aggregates are available
    if config.bi_precompile_on_demand:
        compile_forest(config.user_id, only_hosts = reqhosts, only_groups = [ aggr_group ])
    else:
        compile_forest(config.user_id)

    # Load current assumptions
    load_assumptions()

    # Now look for our aggregation
    if aggr_group not in g_user_cache["forest"]:
        raise MKGeneralException(_("Unknown BI Aggregation group %s. Available are: %s") % (
            aggr_group, ", ".join(g_user_cache["forest"].keys())))

    trees = g_user_cache["forest"][aggr_group]
    for tree in trees:
        if tree["title"] == aggr_title:
            row = create_aggregation_row(tree)
            row["aggr_group"] = aggr_group
            # ZUTUN: omit_root, boxes, only_problems has HTML-Variablen
            tdclass, htmlcode = render_tree_foldable(row, boxes=boxes, omit_root=omit_root,
                                             expansion_level=load_ex_level(), only_problems=only_problems, lazy=False)
            html.write(htmlcode)
            return

    raise MKGeneralException(_("Unknown BI Aggregation %s") % aggr_title)



def render_tree_foldable(row, boxes, omit_root, expansion_level, only_problems, lazy):
    saved_expansion_level = load_ex_level()
    treestate = weblib.get_tree_states('bi')
    if expansion_level != saved_expansion_level:
        treestate = {}
        weblib.set_tree_states('bi', treestate)
        weblib.save_tree_states()

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
                style = ''
                mc = ''
            elif is_open:
                style = ''
                mc = mousecode + 'src="images/tree_black_90.png" '
            else:
                style = 'style="display: none" '
                mc = mousecode + 'src="images/tree_black_00.png" '

            h += aggr_render_node(tree, tree[2]["title"], mc, show_host)
            if not is_empty:
                h += '<ul id="%d:%s" %sclass="subtree">' % (expansion_level, path_id, style)
                if not omit_content:
                    for node in tree[3]:
                        estate = node[1] != None and node[1] or node[0]

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
    url_id = htmllib.urlencode_vars([
        ( "group", group ),
        ( "title", title ),
        ( "omit_root", omit_root and "yes" or ""),
        ( "boxes", boxes and "yes" or ""),
        ( "only_problems", only_problems and "yes" or ""),
        ( "reqhosts", ",".join('%s#%s' % sitehost for sitehost in affected_hosts) ),
    ])

    htmlcode = '<div id="%s" class=bi_tree_container>' % htmllib.attrencode(url_id) + \
               render_subtree(tree, [tree[2]["title"]], len(affected_hosts) > 1) + \
               '</div>'
    return "aggrtree" + (boxes and "_box" or ""), htmlcode

def aggr_render_node(tree, title, mousecode, show_host):
    # Check if we have an assumed state: comparing assumed state (tree[1]) with state (tree[0])
    if tree[1] and tree[0] != tree[1]:
        addclass = " " + _("assumed")
        effective_state = tree[1]
    else:
        addclass = ""
        effective_state = tree[0]

    h = '<span class="content state state%d%s">%s</span>\n' \
         % (effective_state["state"], addclass, render_bi_state(effective_state["state"]))
    if mousecode:
        h += '<img class=opentree %s>' % mousecode
        h += '<span class="content name" %s>%s</span>' % (mousecode, title)
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
          site, host, service != None and service or '')
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
        host_url = html.makeuri([("view_name", "hoststatus"), ("site", site), ("host", host)], filename="view.py")

    if service:
        service_url = html.makeuri([("view_name", "service"), ("site", site), ("host", host), ("service", service)], filename="view.py")

    if show_host:
        content += '<a href="%s">%s</a><b class=bullet>&diams;</b>' % (host_url, host.replace(" ", "&nbsp;"))

    if tree[1] and tree[0] != tree[1]:
        addclass = ' class="state assumed"'
    else:
        addclass = ""

    if not service:
        content += '<a href="%s"%s>%s</a>' % (host_url, addclass, _("Host&nbsp;status"))
    else:
        content += '<a href="%s"%s>%s</a>' % (service_url, addclass, service.replace(" ", "&nbsp;"))

    if bare:
        return content
    else:
        return aggr_render_node(tree, content, None, show_host)

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
    state, assumed_state, node, subtrees = tree_state
    eff_state = state
    if assumed_state != None:
        eff_state = assumed_state

    return {
        "aggr_tree"            : tree,
        "aggr_treestate"       : tree_state,
        "aggr_state"           : state,          # state disregarding assumptions
        "aggr_assumed_state"   : assumed_state,  # is None, if there are no assumptions
        "aggr_effective_state" : eff_state,      # is assumed_state, if there are assumptions, else real state
        "aggr_name"            : node["title"],
        "aggr_output"          : eff_state["output"],
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

    for filter in filters:
        if filter.name == "aggr_group":
            val = filter.selected_group()
            if val:
                only_group = val
        elif filter.name == "aggr_service":
            only_service = filter.service_spec()

    if config.bi_precompile_on_demand and only_group:
        # optimized mode: if aggregation group known only precompile this one
        compile_forest(config.user_id, only_groups = [ only_group ])
    else:
        # classic mode: precompile everything
        compile_forest(config.user_id)

    # TODO: Optimation of affected_hosts filter!

    if only_service:
        affected = g_user_cache["affected_services"].get(only_service)
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
        items = g_user_cache["forest"].items()

    for group, trees in items:
        if only_group not in [ None, group ]:
            continue

        for tree in trees:
            row = create_aggregation_row(tree)
            row["aggr_group"] = group
            rows.append(row)
            if not html.check_limit(rows, limit):
                return rows
    return rows


# Table of all host aggregations, i.e. aggregations using data from exactly one host
def hostname_table(columns, add_headers, only_sites, limit, filters):
    return singlehost_table(columns, add_headers, only_sites, limit, filters, True)

def host_table(columns, add_headers, only_sites, limit, filters):
    return singlehost_table(columns, add_headers, only_sites, limit, filters, False)

def singlehost_table(columns, add_headers, only_sites, limit, filters, joinbyname):
    log("--------------------------------------------------------------------\n")
    log("* Starting to compute singlehost_table (joinbyname = %s)\n" % joinbyname)
    load_assumptions() # user specific, always loaded
    log("* Assumptions are loaded.\n")

    # Create livestatus filter for filtering out hosts. We can
    # simply use all those filters since we have a 1:n mapping between
    # hosts and host aggregations
    filter_code = ""
    for filt in filters:
        header = filt.filter("bi_host_aggregations")
        if not header.startswith("Sites:"):
            filter_code += header

    log("* Getting status information about hosts...\n")
    host_columns = filter(lambda c: c.startswith("host_"), columns)
    hostrows = get_status_info_filtered(filter_code, only_sites, limit, host_columns, config.bi_precompile_on_demand)
    log("* Got %d host rows\n" % len(hostrows))

    # if limit:
    #     views.check_limit(hostrows, limit)

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
        log("* Compiling forest on demand...\n")
        compile_forest(config.user_id, only_groups = only_groups,
                       only_hosts = [ (h['site'], h['name']) for h in hostrows ])
    else:
        log("* Compiling forest...\n")
        compile_forest(config.user_id)

    # rows by site/host - needed for later cluster state gathering
    if config.bi_precompile_on_demand and not joinbyname:
        row_dict = dict([ ((r['site'], r['name']), r) for r in hostrows])

    rows = []
    # Now compute aggregations of these hosts
    log("* Assembling host rows...\n")

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
            aggrs = g_user_cache["aggregations_by_hostname"].get(host, [])
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
                             row["plugin_output"],
                             row["services_with_info"] ]
                if status_info == None:
                    break
        else:
            aggrs = g_user_cache["host_aggregations"].get((site, host), [])
            status_info = { (site, host) : [
                hostrow["state"],
                hostrow["plugin_output"],
                hostrow["services_with_info"] ] }

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
                            this_row['plugin_output'],
                            this_row['services_with_info'],
                        ]

            row.update(create_aggregation_row(aggregation, status_info))
            row["aggr_group"] = group
            rows.append(row)
            if not html.check_limit(rows, limit):
                return rows


    log("* Assembled %d rows.\n" % len(rows))
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
    g_assumptions = config.load_user_file("bi_assumptions", {})

def save_assumptions():
    config.save_user_file("bi_assumptions", g_assumptions)

def load_ex_level():
    return config.load_user_file("bi_treestate", (None, ))[0]

def save_ex_level(current_ex_level):
    config.save_user_file("bi_treestate", (current_ex_level, ))

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
    compile_forest(config.user_id)
    if what == "host":
        return (site, host) in g_user_cache["affected_hosts"]
    else:
        return (site, host, service) in g_user_cache["affected_services"]

def get_state_name(node):
    if node[1]['type'] == NT_LEAF:
        if 'service' in node[1]:
            return service_state_names[node[0]['state']]
        else:
            return host_state_names[node[0]['state']]
    else:
        return service_state_names[node[0]['state']]
