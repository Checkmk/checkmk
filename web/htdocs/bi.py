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
SINGLE = 'single'
MULTIPLE = 'multi'

aggregation_rules = {}

aggregation_rules["HostRessources"] = (
    "Host Ressources", [ "aHOST" ], "worst", [ 
        ( "Kernel",      [ "$HOST$" ] ), 
        ( "Filesystems", [ "$HOST$" ] ),
        ( "Networking",  [ "$HOST$" ] ),
    ]
)

aggregation_rules["Database"] = (
    "Database $DB", [ "aDB", "HOSTs" ], "worst", [
        ( "proc_.*$DB$.*", "$HOST$" ),
        ( "LOG /var/ora/$DB$.log", "$HOST$" ),
    ]
)

aggregation_rules["Kernel"] = (
    "Kernel of $HOST$", [ "aHOST" ], "worst", [ 
        ( "$HOST$", "Kernel" ), 
    ]
)

aggregation_rules["Filesystems"] = (
    "Filesystems", [ "aHOST" ], "worst", [
        ( "$HOST$", "fs" ),
    ]
)

aggregation_rules["Networking"] = (
    "Networking", [ "aHOST" ], "worst", [
        ( "NIC", [ "$HOST$", ".*" ] )
    ]
)

aggregation_rules["NIC"] = (
    "Network Interface $NIC$", ["aHOST", "aNIC"], "worst", [ 
        ( "$HOST$", "NIC ($NIC$) " )
    ]
)

aggregation_rules["OS"] = (
    "Operating System", [ "aHOST" ], "worst", [
        ( "HostRessources", [ "$HOST$" ] ),
        ( "$HOST$", "Check_MK" ),
    ]
)

aggregation_rules["Check_MK"] = (
    "Check_MK", [ "HOSTs" ], "worst", [
        ( "$HOST$", "Check_MK$" ),
        ( "$HOST$", "Check_MK Inventory$" ),
    ]
)

aggregation_rules["GlobalService"] = (
    "$SERVICE$", [ "HOSTs", "aSERVICE" ], "worst", [
        ( "$HOST$", "$SERVICE$" )
    ]
)

aggregations = [
# ( "OSses",      "OS",            [ 'localhost' ] ),
 ( "OSses",      "HostRessources",            [ '.*' ] ),
# ( "Kernel",     "Kernel",        [ '.*' ] ),
# ( "Network",    "NIC",           [ 'localhost', 'eth0' ] ),
# ( "Monitoring", "Check_MK",      [ '.*' ] ), 
# ( "Monitoring", "GlobalService", [ '.*', 'Check.*' ] ),
]

# Ueberlegung: Wenn man als Hostname '.*' angibt (oder ALL_HOSTS und irgendwelche Tags),
# dann ist die Frage, *wo* genau das Ausmultipliziren stattfindet. So könnte die Regel
# ( "OSses",   "OS",  [ '.*' ] ) eigentlich das .* schon auf der höchsten Ebene auflösen
# und mehrere Aggegationen erzeugen. Wenn das .* ganz nach unten geht, wird nur eine
# einzige Aggregation erzeugt, welche die Daten von allen Hosts vereint.

# Alternativ könnte eine untere Regel irgendwie erzwingen, dass sie für jedes unterschiedliche
# Vorkommen des Musters separat erzeugt wird. Es ist ja so, dass von einer Blatt-Regel, die man
# mit Mustern aufruft, für jede Inkarnation die Instanziierung der Argumente hochgemeldet wird.


# Idee zur Syntax der Host-Tags:
# '.*|linux' ==> ['linux'], ALL_HOSTS

aggregation_forest = {}


# Load the static configuration of all services and hosts (including tags)
# without state and store it in the global variable g_services.
def load_services():
    global g_services
    g_services = {}
    data = html.live.query("GET hosts\nColumns: name custom_variable_names custom_variable_values services\n")
    for host, varnames, values, services in data:
        vars = dict(zip(varnames, values))
        tags = vars.get("TAGS", "").split(" ")
        g_services[host] = (tags, services)
        

# Precompile the forest of BI rules. Forest? A collection of trees.
# The compiled forest does not contain any regular expressions.
def compile_forest():
    load_services()
    for group, rulename, args in aggregations:
        rule = aggregation_rules[rulename]
        # Compute new trees and add them to group
        entries = aggregation_forest.get(group, [])
        entries += compile_aggregation(rule, args)
        aggregation_forest[group] = entries

    for group, trees in aggregation_forest.items():
        debug("GROUP %s" % group)
        for tree in trees:
            instargs, node = tree
            ascii = render_tree(node)
            html.write("<pre>\n" + ascii + "<pre>\n")

def render_tree(node, indent = ""):
    h = ""
    if len(node) == 3: # leaf node
        h += indent + "H/S: %s/%s\n" % (node[1], node[2])
    else:
        h += indent + "Aggregation:\n"
        indent += "    "
        h += indent + "Description:  %s\n" % node[1]
        h += indent + "Needed Hosts: %s\n" % " ".join(node[0])
        h += indent + "Aggregation:  %s\n" % node[2]
        h += indent + "Nodes:\n"
        for node in node[3]:
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
            raise MKConfigError("Invalid argument name %s. Must begin with 'a' or end with 's'." % name)
        arginfo[name] = (expansion, value)
    return arginfo


# Precompile one aggregation rule. This outputs a list of trees.
# This function is called recursively.
def compile_aggregation(rule, args):
    description, arglist, funcname, nodes = rule
    arginfo = make_arginfo(arglist, args)
    elements = []
    for node in nodes:
        # Each node can return more than one incarnation (due to regexes in 
        # the arguments)
        if type(node[1]) == str: # leaf node
            elements += aggregate_leaf_node(arginfo, node[0], node[1])
        else:
            rule = aggregation_rules[node[0]]
            instargs = [ instantiate(arg, arginfo)[0] for arg in node[1] ]
            elements += compile_aggregation(rule, instargs)

    # Now compile one or more rules from elements. We group
    # all elements into one rule together, that have the same
    # value for all SINGLE arguments
    groups = {}
    single_names = [ varname for (varname, (expansion, value)) in arginfo.items() if expansion == SINGLE ]
    for instargs, node in elements:
        key = tuple([ instargs[varname] for varname in single_names ])
        nodes = groups.get(key, [])
        nodes.append(node)
        groups[key] = nodes

    result = []
    for key, nodes in groups.items():
        needed_hosts = set([])
        for node in nodes:
            needed_hosts.update(node[0])
        inst = dict(zip(single_names, key))
        description = subst_vars(description, inst)
        result.append((inst, (list(needed_hosts), description, funcname, nodes)))
    return result

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

def subst_vars(pattern, arg):
    for name, value in arg.items():
        pattern = pattern.replace('$'+name+'$', value)
    return pattern

def instantiate(pattern, arginfo):
    # Wir bekommen hier z.B. rein:
    # pattern = "Some $DB$ and some $PROC$"
    # arginfo = { "PROC": (SINGLE, "[a-z].*"), "DB": (MULTIPLE, "X.."),  }
    # Die Antwort ist:
    # return "Some (X..) and some ([a-z].*)", [ 'DB', 'PROC' ]
    # Bedenke: Eine Variable kann mehrfach ersetzt werden.

    # Replace variables with values. Values are assumed to 
    # contain regular expressions and are put into brackets.
    # This allows us later to get the actual value when the regex
    # is matched against an actual host or service name.
    # Difficulty: when a variable appears twice, the second
    # occurrance must be a back reference to the first one. We
    # need to make sure, that both occurrances match the *same*
    # string. 

    # Example:
    # "some text $A$ other $B$ and $A$"
    # A = "a.*z", B => "hirn"
    # result: "some text (a.*z) other (hirn) and (\1)"
    substed = []
    newpattern = pattern

    first_places = []
    # Determine order of first occurrance of each variable
    for varname, (expansion, value) in arginfo.items():
        places = find_variables(pattern, varname)
        if len(places) > 0:
            first_places.append((places[0], varname))
    first_places.sort()
    varorder = [ varname for (place, varname) in first_places ]
    backrefs = {}
    for num, var in enumerate(varorder):
        backrefs[var] = num + 1
    
    # Replace variables
    for varname, (expansion, value) in arginfo.items():
        places = find_variables(pattern, varname)
        value = value.replace('$', '\001') # make $ invisible
        if len(places) > 0:
            for p in places:
                substed.append((p, varname))
            newpattern = newpattern.replace('$' + varname + '$', '(' + value + ')', 1)
            newpattern = newpattern.replace('$' + varname + '$', '(\\%d)' % backrefs[varname])
    substed.sort()
    newpattern = newpattern.replace('\001', '$')
    return newpattern, [ v for (p, v) in substed ]

            
def do_match(reg, text):
    mo = regex(reg).match(text)
    if not mo:
        return None
    else:
        return list(mo.groups())


def aggregate_leaf_node(arginfo, host, service):
    # replace placeholders in host and service with arg
    # service = 'NIC $NIC$ .*'
    host_re, host_vars = instantiate(host, arginfo)
    # service = 'NIC $NIC$ .*'
    service_re, service_vars = instantiate(service, arginfo)
    # service_re = (['NIC'], 'NIC (.*) .*')  # Liste von argumenten

    found = []

    for host, (tags, services) in g_services.items():
        # Tags vom Host prüfen (hier noch nicht in Konfiguration enthalten)
        host_instargs = do_match(host_re, host)
        if host_instargs:
            for service in services:
                svc_instargs = do_match(service_re, service)
                if svc_instargs != None:
                    newarg = {} # dict([ (k,v) for (k,(e,v)) in arginfo.items()])
                    newarg.update(dict(zip(host_vars, host_instargs)))
                    newarg.update(dict(zip(service_vars, svc_instargs)))
                    found.append((newarg, ([host], host, service)))

    # Jetzt in eine Liste umwandeln
    # return in_liste(found)
    return found

regex_cache = {}
def regex(r):
    rx = regex_cache.get(r)
    if rx:
        return rx
    try:
        rx = re.compile(r)
    except Exception, e:
        raise MKConfigError("Invalid regular expression '%s': %s" % (r, e))
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


