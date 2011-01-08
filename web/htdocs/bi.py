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



#      ____                      _ _       _   _             
#     / ___|___  _ __ ___  _ __ (_) | __ _| |_(_) ___  _ __  
#    | |   / _ \| '_ ` _ \| '_ \| | |/ _` | __| |/ _ \| '_ \ 
#    | |__| (_) | | | | | | |_) | | | (_| | |_| | (_) | | | |
#     \____\___/|_| |_| |_| .__/|_|_|\__,_|\__|_|\___/|_| |_|
#                         |_|                                


# Load the static configuration of all services and hosts (including tags)
# without state and store it in the global variable g_services.
def load_services():
    global g_services
    g_services = {}
    html.live.set_prepend_site(True)
    data = html.live.query("GET hosts\nColumns: name custom_variable_names custom_variable_values services\n")
    html.live.set_prepend_site(False)

    for site, host, varnames, values, services in data:
        vars = dict(zip(varnames, values))
        tags = vars.get("TAGS", "").split(" ")
        g_services[(site, host)] = (tags, services)
        

# Precompile the forest of BI rules. Forest? A collection of trees.
# The compiled forest does not contain any regular expressions anymore.
# Everything is resolved. Sites, hosts and services are hardcoded. The
# aggregation functions are still left as names. That way the forest
# printable (and storable in Python syntax to a file).
def compile_forest():
    global g_aggregation_forest
    g_aggregation_forest = {}

    load_services()
    for group, rulename, args in config.aggregations:
        args = compile_args(args)
        rule = config.aggregation_rules[rulename]
        # Compute new trees and add them to group
        entries = g_aggregation_forest.get(group, [])
        entries += compile_aggregation(rule, args)
        g_aggregation_forest[group] = entries

# Debugging function
def render_forest():
    for group, trees in g_aggregation_forest.items():
        html.write("<h2>%s</h2>" % group)
        for tree in trees:
            instargs, node = tree
            ascii = render_tree(node)
            html.write("<pre>\n" + ascii + "<pre>\n")

# Debugging function
def render_tree(node, indent = ""):
    h = ""
    if len(node) == 3: # leaf node
        h += indent + "S/H/S: %s/%s/%s\n" % (node[1][0], node[1][1], node[2])
    else:
        h += indent + "Aggregation:\n"
        indent += "    "
        h += indent + "Description:  %s\n" % node[1]
        h += indent + "Needed Hosts: %s\n" % " ".join([("%s/%s" % h_s) for h_s in node[0]])
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
        if node[1] == None or type(node[1]) == str: # leaf node
            elements += aggregate_leaf_node(arginfo, node[0], node[1])
        else:
            rule = config.aggregation_rules[node[0]]
            instargs = compile_args([ instantiate(arg, arginfo)[0] for arg in node[1] ])
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
        inst_description = subst_vars(description, inst)
        result.append((inst, (list(needed_hosts), inst_description, funcname, nodes)))
    return result


# Reduce [ [ 'linux', 'test' ], ALL_HOSTS, ... ] to [ 'linux|test|@all', ... ]
# Reduce [ [ 'xsrvab1', 'xsrvab2' ], ... ]       to [ 'xsrvab1|xsrvab2', ... ]
# Reduce [ [ ALL_HOSTS, ... ] ]                  to [ '.*', ... ]
def compile_args(args):
    newargs = []
    while len(args) > 0:
        if args[0] == config.ALL_HOSTS:
            newargs.append('.*')
        elif type(args[0]) == list and len(args) >= 2 and args[1] == config.ALL_HOSTS:
            newargs.append('|'.join(args[0] + config.ALL_HOSTS))
            args = args[1:]
        elif type(args[0]) == list:
            newargs.append('|'.join(args[0]))
        else:
            newargs.append(args[0])
        args = args[1:]
    return newargs


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
def subst_vars(pattern, arg):
    for name, value in arg.items():
        pattern = pattern.replace('$'+name+'$', value)
    return pattern

def instantiate(pattern, arginfo):
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

def match_host_tags(host, tags):
    required_tags = host.split('|')
    for tag in required_tags:
        if tag.startswith('!'):
            negate = True
            tag = tag[1:]
        else:
            negate = False
        has_it = tag in tags
        if has_it == negate:
            return False
    return True

def aggregate_leaf_node(arginfo, host, service):
    # replace placeholders in host and service with arg
    host_re, host_vars = instantiate(host, arginfo)
    if service != None:
        service_re, service_vars = instantiate(service, arginfo)

    found = []

    for (site, hostname), (tags, services) in g_services.items():
        # If host ends with '|@all', we need to check host tags instead
        # of regexes.
        if host_re.endswith('|@all'):
            if not match_host_tags(host_re[:-5], tags):
                continue
            host_instargs = []
        elif host_re.endswith('|@all)'):
            if not match_host_tags(host_re[1:-6], tags):
                continue
            host_instargs = [ hostname ]
        else:
            # in order to distinguish hosts with the same name on different
            # sites by prepending the site and a colon to the host name
            host_instargs = do_match(host_re, "%s:%s" % (site, hostname))

        if host_instargs != None:
            if service == None:
                newarg = dict(zip(host_vars, host_instargs))
                found.append((newarg, ([(site, hostname)], (site, hostname), service)))
            else:
                for service in services:
                    svc_instargs = do_match(service_re, service)
                    if svc_instargs != None:
                        newarg = dict(zip(host_vars, host_instargs))
                        newarg.update(dict(zip(service_vars, svc_instargs)))
                        found.append((newarg, ([(site, hostname)], (site, hostname), service)))

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



#     _____                     _   _             
#    | ____|_  _____  ___ _   _| |_(_) ___  _ __  
#    |  _| \ \/ / _ \/ __| | | | __| |/ _ \| '_ \ 
#    | |___ >  <  __/ (__| |_| | |_| | (_) | | | |
#    |_____/_/\_\___|\___|\__,_|\__|_|\___/|_| |_|
#                                                 

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
        data = html.live.query(
                "GET hosts\n"
                "Columns: name state plugin_output services_with_info\n"
                + filter)
        tuples += [((site, e[0]), e[1:]) for e in data]

    return dict(tuples)


# Execution of the trees. Returns a tree object reflecting
# the states of all nodes
def execute_tree(tree):
    required_hosts = tree[0]
    status_info = get_status_info(required_hosts)
    return execute_node(tree, status_info)

def execute_node(node, status_info):
    # Each returned node consists of
    # (state, assumed_state, name, output, required_hosts, funcname, subtrees)
    # For leaf-nodes, subtrees is None
    if len(node) == 3:
        return execute_leaf_node(node, status_info) + (node[0], None, None,)
    else:
        return execute_inter_node(node, status_info)


def execute_leaf_node(node, status_info):
    required_hosts, (site, host), service = node
    status = status_info.get((site, host))
    if status == None:
        return (MISSING, None, None, "Host %s not found" % host) 

    host_state, host_output, service_state = status
    assumed_state = g_assumptions.get((site, host, service))

    if service == None: # host state
        aggr_state = {0:OK, 1:CRIT, 2:UNKNOWN}[host_state]
        return (aggr_state, assumed_state, None, host_output)

    else:
        for entry in service_state:
            if entry[0] == service:
                state, has_been_checked, plugin_output = entry[1:]
                if has_been_checked == 0:
                    return (PENDING, assumed_state, service, "This service has not been checked yet")
                else:
                    return (state, assumed_state, service, plugin_output)
        return (MISSING, assumed_state, service, "This host has no such service")


def execute_inter_node(node, status_info):
    required_hosts, title, funcname, nodes = node
    func = config.aggregation_functions.get(funcname)
    if not func:
        raise MKConfigError("Undefined aggregation function '%s'. Available are: %s" % 
                (funcname, ", ".join(config.aggregation_functions.keys())))

    node_states = []
    assumed_node_states = []
    one_assumption = False
    for n in nodes:
        node_state = execute_node(n, status_info)
        node_states.append(node_state)
        assumed_state = node_state[1]
        if assumed_state != None:
            assumed_node_states.append((node_state[1],) + node_state[1:])
            one_assumption = True
        else:
            assumed_node_states.append(node_state)

    state, output = func(node_states)
    if one_assumption:
        assumed_state, output = func(assumed_node_states)
    else:
        assumed_state = None
    return (state, assumed_state, title, output, 
            required_hosts, funcname, node_states )
    

#       _                      _____                 _   _                 
#      / \   __ _  __ _ _ __  |  ___|   _ _ __   ___| |_(_) ___  _ __  ___ 
#     / _ \ / _` |/ _` | '__| | |_ | | | | '_ \ / __| __| |/ _ \| '_ \/ __|
#    / ___ \ (_| | (_| | | _  |  _|| |_| | | | | (__| |_| | (_) | | | \__ \
#   /_/   \_\__, |\__, |_|(_) |_|   \__,_|_| |_|\___|\__|_|\___/|_| |_|___/
#           |___/ |___/                                                    

def aggr_worst(nodes):
    state = 0 
    problems = []
    for node in nodes:
        s = node[0]
        if s != OK:
            problems.append(node[1])

        if s == CRIT:
            state = s
        else:
            state = max(s, state)

    if len(problems) > 0:
        return state, "%d problems" % len(problems)
    else:
        return state, ""

config.aggregation_functions["worst"] = aggr_worst

#      ____                       
#     |  _ \ __ _  __ _  ___  ___ 
#     | |_) / _` |/ _` |/ _ \/ __|
#     |  __/ (_| | (_| |  __/\__ \
#     |_|   \__,_|\__, |\___||___/
#                 |___/           

# Just for debugging
def page_debug(h):
    global html
    html = h
    compile_forest()
    
    html.header("BI Debug")
    render_forest()
    html.footer()


# Just for debugging, as well
def page_all(h):
    global html
    html = h
    html.header("All")
    compile_forest()
    load_assumptions()
    for group, trees in g_aggregation_forest.items():
        html.write("<h2>%s</h2>" % group)
        for inst_args, tree in trees:
            state = execute_tree(tree)
            debug(state)
    html.footer()


def ajax_set_assumption(h):
    global html
    html = h
    site = html.var("site")
    host = html.var("host")
    service = html.var("service")
    state = html.var("state")
    load_assumptions()
    if state == 'none':
        del g_assumptions[(site, host, service)]
    else:
        g_assumptions[(site, host, service)] = int(state)
    save_assumptions()


#    ____        _                                          
#   |  _ \  __ _| |_ __ _ ___  ___  _   _ _ __ ___ ___  ___ 
#   | | | |/ _` | __/ _` / __|/ _ \| | | | '__/ __/ _ \/ __|
#   | |_| | (_| | || (_| \__ \ (_) | |_| | | | (_|  __/\__ \
#   |____/ \__,_|\__\__,_|___/\___/ \__,_|_|  \___\___||___/
#                                                           

def create_aggregation_row(tree):
    state = execute_tree(tree)
    eff_state = state[0]
    if state[1] != None:
        eff_state = state[1]
    else:
        eff_state = state[0]
    return {
        "aggr_tree"            : tree,
        "aggr_treestate"       : state,
        "aggr_state"           : state[0],
        "aggr_assumed_state"   : state[1],
        "aggr_effective_state" : eff_state,
        "aggr_output"          : state[2],
        "aggr_name"            : state[3],
        "aggr_hosts"           : state[4],
        "aggr_function"        : state[5],
    }

def table(h, columns, add_headers, only_sites, limit, filters):
    global html
    html = h
    compile_forest()   # should be cached later
    load_assumptions() # user specific, always loaded
    # Hier müsste man jetzt die Filter kennen, damit man nicht sinnlos
    # alle Aggregationen berechnet.
    rows = []
    # Apply group filter. This is important for performance. We 
    # must not compute any aggregations from other groups and filter 
    # later out again.
    only_group = None
    for filter in filters:
        if filter.name == "aggr_group":
            only_group = filter.selected_group()
            break

    for group, trees in g_aggregation_forest.items():
        if only_group not in [ None, group ]:
            continue

        for inst_args, tree in trees:
            row = create_aggregation_row(tree)
            row["aggr_group"] = group
            rows.append(row)
    return rows
        

def host_table(h, columns, add_headers, only_sites, limit, filters):
    global html
    html = h
    compile_forest()   # should be cached later
    load_assumptions() # user specific, always loaded
    # Hier müsste man jetzt die Filter kennen, damit man nicht sinnlos
    # alle Aggregationen berechnet.

    # First compute list of hosts that have aggregations
    required_hosts = {}
    host_aggregations = {}
    for group, trees in g_aggregation_forest.items():
        for inst_args, tree in trees:
            req_hosts = tree[0]
            if len(req_hosts) != 1:
                continue
            site, host = req_hosts[0]
            hosts = required_hosts.get(site, None)
            if hosts != None:
                hosts.append(host)
            else:
                required_hosts[site] = [host]
            aggrs = host_aggregations.get((site, host), [])
            aggrs.append((group, tree))
            host_aggregations[(site, host)] = aggrs

    # Retrieve information about these hosts
    host_columns = filter(lambda c: c.startswith("host_"), columns)
    if "host_name" not in host_columns:
        host_columns.append("host_name")

    rows = []
    for site, hosts in required_hosts.iteritems():
        # Skip deselected sites
        if only_sites and site not in only_sites:
            continue

        query = "GET hosts\n"
        query += "Columns: %s\n" % " ".join(host_columns)

        # Fetch only hosts required for this query. This seems not
        # yet optimal. In some cases all or almost all hosts are
        # queried...
        for host in hosts:
            query += "Filter: name = %s\n" % host
        if len(required_hosts) > 1:
            query += "Or: %d\n" % len(hosts)

        query += add_headers
        html.live.set_only_sites([site])
        if limit != None:
            html.live.set_limit(limit + 1) # + 1: We need to know, if limit is exceeded
        if only_sites:
            html.live.set_only_sites(only_sites)

        host_data = html.live.query(query)
        for r in host_data:
            row = dict(host_columns, r)
            row['site'] = site
            host = row["host_name"]
            for group, tree in host_aggregations.get((site, host), []):
                row = row.copy()
                row.update(create_aggregation_row(tree))
                row["aggr_group"] = group
                rows.append(row)

    html.live.set_only_sites(None)
    html.live.set_limit() # removes limit

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

def status_tree_depth(tree):
    nodes = tree[6]
    if nodes == None:
        return 1
    else:
        maxdepth = 0
        for node in nodes:
            maxdepth = max(maxdepth, status_tree_depth(node))
        return maxdepth + 1

#     _____                 ____             
#    |  ___|__   ___       | __ )  __ _ _ __ 
#    | |_ / _ \ / _ \ _____|  _ \ / _` | '__|
#    |  _| (_) | (_) |_____| |_) | (_| | |   
#    |_|  \___/ \___/      |____/ \__,_|_|   
#                                            

# 
# 
# def compute_host_aggregations(row):
#     customvars = dict(zip(row["host_custom_variable_names"], row["host_custom_variable_values"]))
#     tags = customvars.get("TAGS", "").split(" ")
#     row["host_tags"] = tags
# 
#     instances = {}
#     seen_services = set([])
#     for entry in config.bi_host_aggregations:
#         if len(entry) == 5:
#             aggrname, ruletags, hostlist, svcmatch, aggrfunc = entry 
#         elif len(entry) == 4:
#             aggrname, hostlist, svcmatch, aggrfunc = entry
#             ruletags = []
#         else:
#             raise MKConfigError("Invalid entry in bi_host_aggregations: %r" % entry)
# 
#         # Check if we need to apply the rule on this host
#         if host_matches(row["host_name"], tags, hostlist, ruletags):
#             r = regex(svcmatch)
#             for svc_desc, svc_state, svc_hasbeenchecked, svc_output in row["host_services_with_info"]:
#                 # make sure that each service is only aggregated once
#                 matchobject = r.search(svc_desc)
#                 if matchobject:
#                     if svc_desc in seen_services:
#                         continue
#                     else:
#                         seen_services.add(svc_desc)
#                     try:
#                         item = matchobject.groups()[-1]
#                         rulename = aggrname % item
#                     except:
#                         rulename = aggrname
#                     atoms, func = instances.get(rulename, ([], None))
#                     atoms.append((svc_desc, svc_state, svc_hasbeenchecked, svc_output))
#                     instances[rulename] = atoms, aggrfunc
# 
#     newrows = []
#     for name, (atoms, func) in instances.items():
#         newrow = row.copy()
#         newrow["aggr_name"] = name
#         aggregate(newrow, func, atoms)
#         newrows.append(newrow)
# 
#     return newrows 
# 
# 
# def aggregate(row, func, atoms):
#     descr = "%d entries" % len(atoms)
#     if type(func) == type(lambda: None):
#         function = func
#     else:
#         function = aggregation_functions.get(func)
#         if not function:
#             raise MKConfigError("Invalid aggregation function '%s'" % func)
# 
#     state, output = function(atoms)
#     row["aggr_state"] = state
#     row["aggr_output"] = output
#     row["aggr_atoms"] = atoms
# 
# def host_matches(a,b,c,d):
#     return True
# 
# 
