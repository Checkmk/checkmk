#!/usr/bin/python
# encoding: utf-8

import config, re, pprint
from lib import *

# Python 2.3 does not have 'set' in normal namespace.
# But it can be imported from 'sets'
try:
    set()
except NameError:
    from sets import Set as set

# ZWEITER VERSUCH, komplett von vorne

aggregation_rules = {}

aggregation_rules["HostRessources"] = (
    "Host Ressources", "worst", [ "HOST" ], [ 
        ( "Kernel",      [ "$HOST$" ]       ), 
        ( "Filesystems", [ "$HOST$" ]       ),
        ( "NIC",         [ "$HOST$", ".*" ] ),
    ]
)

aggregation_rules["Kernel"] = (
    "Kernel", [ "HOST" ], "worst", [ 
        ( "$HOST$", "Kernel" ), 
    ]
)

aggregation_rules["Filesystems"] = (
    "Filesystems", [ "HOST" ], "worst", [
        ( "$HOST$", "fs" ),
    ]
)

aggregation_rules["NIC"] = (
    "Network Interface $NIC$", ["HOST", "NIC"], "worst", [ 
        ( "$HOST$", "NIC ($NIC$) " )
    ]
)

aggregation_rules["OS"] = (
    "Operating System", [ "HOST" ], "worst", [
        ( "HostRessources", [ "$HOST$" ] ),
        ( "$HOST$", "Check_MK" ),
    ]
)

aggregations = [
 ( "OSses",   "OS",  [ '.*' ] ),
 ( "Network", "NIC", [ 'localhost', 'eth0' ] ),
]


aggregation_forest = {}


def load_services():
    global g_services
    g_services = {}
    data = html.live.query("GET hosts\nColumns: name custom_variable_names custom_variable_values services\n")
    for host, varnames, values, services in data:
        vars = dict(zip(varnames, values))
        tags = vars.get("TAGS", "").split(" ")
        g_services[host] = (tags, services)
        

def compile_forest():
    load_services()

    for group, rulename, args in aggregations:
        # Schwierigkeit hier: die args können reguläre Ausdrücke enthalten.
        rule = aggregation_rules[rulename]
        entries = aggregation_forest.get(group, [])
        entries += compile_aggregation(rule, args)
        aggregation_forest[group] = entries


def compile_aggregation(rule, args):
    description, arglist, func, nodes = rule
    arg = dict(zip(arglist, args))
    elements = []
    for node in nodes:
        # Each node can return more than one incarnation (due to regexes in 
        # the arguments)
        elements += aggregate_node(arg, node)
    return elements


def aggregate_node(arg, node):
    if type(node[1]) == str: # leaf node
        elements = aggregate_leaf_node(arg, node[0], node[1])
    else:
        elements = aggregate_inter_node(arg, node[0], node[1])
    return elements


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

def instantiate(pattern, arg):
    # Wir bekommen hier z.B. rein:
    # pattern = "Some $DB$ and some $PROC$"
    # arg = { "PROC": "[a-z].*", "DB": "X..",  }
    # Die Antwort ist:
    # return "Some (X..) and some ([a-z].*)", [ 'DB', 'PROC' ]
    # Bedenke: Eine Variable kann mehrfachersetzt werden.

    substed = []
    newpattern = pattern
    for k, v in arg.items():
        places = find_variables(pattern, v)
        for p in places:
            substed.append((p, v))
        newpattern = newpattern.replace('$'+k+'$', '('+v+')')
    substed.sort()
    return newpattern, [ v for (p,v) in substed ]

def do_match(reg, text):
    mo = regex(reg).match(text)
    if not mo:
        return None
    else:
        return list(mo.groups())


def aggregate_leaf_node(arg, host, service):
    debug("LEAF NODE: %s" % ((arg, host, service),))

    # replace placeholders in host and service with arg
    # service = 'NIC $NIC$ .*'
    host_re, host_vars = instantiate(host, arg)
    # service = 'NIC $NIC$ .*'
    service_re, service_vars = instantiate(service, arg)
    # service_re = (['NIC'], 'NIC (.*) .*')  # Liste von argumenten

    found = []

    for host, (tags, services) in g_services.items():
        # Tags vom Host prüfen (hier noch nicht in Konfiguration enthalten)
        instargs = do_match(host_re, host)
        if instargs:
            newarg = arg.copy()
            newarg.update(dict(zip(host_vars, instargs)))
            for service in services:
                instargs = do_match(service_re, service)
                if instargs != None:
                    newarg = arg.copy()
                    newarg.update(dict(zip(service_vars, instargs)))
                    found.append((host, service))

    # Jetzt in eine Liste umwandeln
    # return in_liste(found)
    debug("==> %s" % pprint.pformat(found))
    return found

def aggregate_inter_node(arg, rulename, args):
    rule = aggregation_rules[rulename]
    description, arglist, funcname, nodelist = rule
    elements = compile_aggregation(rule, args)
    debug("ARG: %s" % arg)
    debug("RULENAME: %s" % rulename)
    debug("ELEMENTS: %s" % elements)
    return []

regex_cache = {}
def regex(r):
    rx = regex_cache.get(r)
    if rx:
        return rx
    rx = re.compile(r)
    regex_cache[r] = rx
    return rx


def page_debug(h):
    global html
    html = h
    compile_forest()
    html.header("BI Debug")
    html.write("<pre>%s</pre>" % aggregation_forest)
    html.footer()


# So schaut ein vorkompiliertes Aggregat aus:
hirn = ( 
 "Names (Description)", 'worst', [
   # HIER KOMMEN DIE NODES
 ]
)
























# ==========================================================================

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


