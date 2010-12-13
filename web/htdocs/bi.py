#!/usr/bin/python

import config, re
from lib import *

# Python 2.3 does not have 'set' in normal namespace.
# But it can be imported from 'sets'
try:
    set()
except NameError:
    from sets import Set as set


def aggr_worst(atoms):
    state = 0 
    problems = []
    for descr, s, hbc, output in atoms:
        if s != 0:
            problems.append(descr)

        if s == 2:
            state = 2
        elif state != 2:
            state = max(s, state)

    return state, ", ".join(problems)

aggregation_functions = {
    "worst" : aggr_worst,
}

regex_cache = {}
def regex(r):
    rx = regex_cache.get(r)
    if rx:
        return rx
    rx = re.compile(r)
    regex_cache[r] = rx
    return rx

ALL_HOSTS  = [ '@all' ]

def debug(x):
    import pprint
    p = pprint.pformat(x)
    html.write("<pre>%s</pre>\n" % p)


def host_table(h, columns, add_headers, only_sites, limit):
    global html
    html = h
    host_columns = filter(lambda c: c.startswith("host_"), columns)
    for c in [ "host_name", "host_custom_variable_names", "host_custom_variable_values", "host_services_with_info" ]:
        if c not in host_columns:
            host_columns.append(c)

    # First get information about hosts
    query = "GET hosts\n"
    query += "Columns: %s\n" % " ".join(host_columns)
    query += add_headers
    html.live.set_prepend_site(True)
    if limit != None:
        html.live.set_limit(limit + 1) # + 1: We need to know, if limit is exceeded
    if only_sites:
        html.live.set_only_sites(only_sites)

    host_data = html.live.query(query)

    html.live.set_only_sites(None)
    html.live.set_prepend_site(False)
    html.live.set_limit() # removes limit

    host_columns = ["site"] + host_columns

    rows = []
    for r in host_data:
        row = dict(zip(host_columns, r))
        rows += compute_host_aggregations(row)

# debug(rows)
    return columns, rows

def compute_host_aggregations(row):
    customvars = dict(zip(row["host_custom_variable_names"], row["host_custom_variable_values"]))
    tags = customvars.get("TAGS", "").split(" ")
    row["host_tags"] = tags

    instances = {}
    seen_services = set([])
    for entry in config.bi_host_aggregations:
        if len(entry) == 5:
            aggrname, ruletags, hostlist, svcmatch, aggrfunc = entry 
        elif len(entry) == 4:
            aggrname, hostlist, svcmatch, aggrfunc = entry
            ruletags = []
        else:
            raise MKConfigError("Invalid entry in bi_host_aggregations: %r" % entry)

        # Check if we need to apply the rule on this host
        if host_matches(row["host_name"], tags, hostlist, ruletags):
            r = regex(svcmatch)
            for svc_desc, svc_state, svc_hasbeenchecked, svc_output in row["host_services_with_info"]:
                # make sure that each service is only aggregated once
                matchobject = r.search(svc_desc)
                if matchobject:
                    if svc_desc in seen_services:
                        continue
                    else:
                        seen_services.add(svc_desc)
                    try:
                        item = matchobject.groups()[-1]
                        rulename = aggrname % item
                    except:
                        rulename = aggrname
                    atoms, func = instances.get(rulename, ([], None))
                    atoms.append((svc_desc, svc_state, svc_hasbeenchecked, svc_output))
                    instances[rulename] = atoms, aggrfunc

    newrows = []
    for name, (atoms, func) in instances.items():
        newrow = row.copy()
        newrow["aggr_name"] = name
        aggregate(newrow, func, atoms)
        newrows.append(newrow)

    return newrows 


def aggregate(row, func, atoms):
    descr = "%d entries" % len(atoms)
    if type(func) == type(lambda: None):
        function = func
    else:
        function = aggregation_functions.get(func)
        if not function:
            raise MKConfigError("Invalid aggregation function '%s'" % func)

    state, output = function(atoms)
    row["aggr_state"] = state
    row["aggr_output"] = output
    row["aggr_atoms"] = atoms

def host_matches(a,b,c,d):
    return True
