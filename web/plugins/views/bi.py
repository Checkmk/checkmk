import bi

#     ____        _                                          
#    |  _ \  __ _| |_ __ _ ___  ___  _   _ _ __ ___ ___  ___ 
#    | | | |/ _` | __/ _` / __|/ _ \| | | | '__/ __/ _ \/ __|
#    | |_| | (_| | || (_| \__ \ (_) | |_| | | | (_|  __/\__ \
#    |____/ \__,_|\__\__,_|___/\___/ \__,_|_|  \___\___||___/
#                                                            


multisite_datasources["bi_aggregations"] = {
    "title"       : "BI Aggregations",
    "table"       : bi.table, 
    "infos"       : [ "aggr" ],
    "keys"        : [],
}

multisite_datasources["bi_host_aggregations"] = {
    "title"       : "BI Host Aggregations",
    "table"       : bi.host_table, 
    "infos"       : [ "host", "aggr" ],
    "keys"        : [],
}

#     ____       _       _                
#    |  _ \ __ _(_)_ __ | |_ ___ _ __ ___ 
#    | |_) / _` | | '_ \| __/ _ \ '__/ __|
#    |  __/ (_| | | | | | ||  __/ |  \__ \
#    |_|   \__,_|_|_| |_|\__\___|_|  |___/
#                                         

def paint_aggr_state_short(state, assumed = False):
    if state == None:
        return "", ""
    else:
        name = nagios_short_state_names[state]
        classes = "state svcstate state%s" % state
        if assumed:
            classes += " assumed"
        return classes, name

multisite_painters["aggr_state"] = {
    "title"   : "Aggregated state",
    "short"   : "State",
    "columns" : [ "aggr_effective_state" ],
    "paint"   : lambda row: paint_aggr_state_short(row["aggr_effective_state"], row["aggr_effective_state"] != row["aggr_state"])
}

multisite_painters["aggr_real_state"] = {
    "title"   : "Aggregated real state (never assumed)",
    "short"   : "R.State",
    "columns" : [ "aggr_state" ],
    "paint"   : lambda row: paint_aggr_state_short(row["aggr_state"])
}

multisite_painters["aggr_assumed_state"] = {
    "title"   : "Aggregated assumed state",
    "short"   : "Assumed",
    "columns" : [ "aggr_assumed_state" ],
    "paint"   : lambda row: paint_aggr_state_short(row["aggr_assumed_state"])
}


multisite_painters["aggr_group"] = {
    "title"   : "Aggregation group",
    "short"   : "Group",
    "columns" : [ "aggr_group" ],
    "paint"   : lambda row: ("", row["aggr_group"])
}

multisite_painters["aggr_name"] = {
    "title"   : "Aggregation name",
    "short"   : "Aggregation",
    "columns" : [ "aggr_name" ],
    "paint"   : lambda row: ("", row["aggr_name"])
}

multisite_painters["aggr_output"] = {
    "title"   : "Aggregation status output",
    "short"   : "Output",
    "columns" : [ "aggr_output" ],
    "paint"   : lambda row: ("", row["aggr_output"])
}

def paint_aggr_hosts(row):
    h = []
    for site, host in row["aggr_hosts"]:
        url = html.makeuri([("view_name", "aggr_host"), ("site", site), ("host", host)])
        h.append('<a href="%s">%s</a>' % (url, host))
    return "", " ".join(h)

multisite_painters["aggr_hosts"] = {
    "title"   : "Aggregation: affected hosts",
    "short"   : "Hosts",
    "columns" : [ "aggr_hosts" ],
    "paint"   : paint_aggr_hosts,
}


multisite_painter_options["aggr_expand"] = {
 "title"   : "Initial expansion of aggregations",
 "default" : "0",
 "values"  : [ ("0", "collapsed"), ("1", "first level"), ("2", "two levels"), ("3", "three levels"), ("999", "complete")]
}

multisite_painter_options["aggr_onlyproblems"] = {
 "title"   : "Show only problems",
 "default" : "0",
 "values"  : [ ("0", "show all"), ("1", "show only problems")]
}

multisite_painter_options["aggr_treetype"] = {
 "title"   : "Type of tree layout",
 "default" : "foldable",
 "values"  : [ ("foldable", "foldable"), ("bottom-up", "bottom up"), ("top-down", "top down")]
}

multisite_painter_options["aggr_wrap"] = {
 "title"   : "Handling of too long texts",
 "default" : "wrap",
 "values"  : [ ("wrap", "wrap"), ("nowrap", "don't wrap")]
}


def render_bi_state(state):
    return { bi.PENDING: "PD",
             bi.OK:      "OK", 
             bi.WARN:    "WA",
             bi.CRIT:    "CR", 
             bi.UNKNOWN: "UN",
             bi.MISSING: "MI",
             bi.UNAVAIL: "NA",
    }.get(state, "??")

def render_assume_icon(site, host, service):
    if service:
        key = (site, host, service)
    else:
        key = (site, host)
    ass = bi.g_assumptions.get(key)
    mousecode = \
       'onmouseover="this.style.cursor=\'pointer\';" ' \
       'onmouseout="this.style.cursor=\'auto\';" ' \
       'title="Assume another state for this item (reload page to activate)" ' \
       'onclick="toggle_assumption(this, %s, %s, %s);" ' % \
         (repr(site), repr(str(host)), service == None and 'null' or repr(str(service)))
    current = str(ass).lower()
    return '<img state="%s" class=assumption %s src="images/assume_%s.png">\n' % (current, mousecode, current)

def aggr_render_leaf(tree, show_host):
    site, host = tree[4][0]
    service = tree[2]
    content = render_assume_icon(site, host, service) 

    # Four cases:
    # (1) zbghora17 . Host status   (show_host == True, service == None)
    # (2) zbghora17 . CPU load      (show_host == True, service != None)
    # (3) Host Status               (show_host == False, service == None)
    # (4) CPU load                  (show_host == False, service != None)

    if show_host or not service:
        host_url = html.makeuri([("view_name", "hoststatus"), ("site", site), ("host", host)])

    if service:
        service_url = html.makeuri([("view_name", "service"), ("site", site), ("host", host), ("service", service)])

    if show_host:
        content += '<a href="%s">%s</a><b class=bullet>&diams;</b>' % (host_url, host)

    if not service:
        content += '<a href="%s">Host status</a>' % host_url
    else:
        content += '<a href="%s">%s</a>' % (service_url, service)

    return aggr_render_node(tree, content, None, show_host)

def aggr_render_node(tree, title, mousecode, show_host):
    state = tree[0]
    assumed_state = tree[1]
    if assumed_state != None:
        effective_state = assumed_state 
    else:
        effective_state = state

    if (effective_state != state):
        addclass = " assumed"
    else:
        addclass = ""
    h = '<span class="content state state%d%s">%s</span>\n' \
         % (effective_state, addclass, render_bi_state(effective_state))
    if mousecode:
        h += '<img class=opentree %s>' % mousecode
        h += '<span class="content name">%s</span>' % title
    else:
        h += title
    output = tree[3]
    if output:
        output = "<b class=bullet>&diams;</b>" + output
    else:
        output = ""
    h += '<span class="content output">%s</span>\n' % output
    return h

def filter_tree_only_problems(tree):

    def get_worst(subtree, worst = 0):
        nodes = subtree[6]
        if not nodes is None:
            work = nodes[:]
            for i, node in enumerate(work):
                # Go deep!
                my_worst = get_worst(node)[1]

                # Cleanup this node+below
                if my_worst == 0:
                    nodes.remove(node)

                # Add state of this node to summary state for nodes above
                if my_worst > worst:
                    worst = my_worst

        if subtree[0] > worst:
            worst = subtree[0]

        return nodes, worst

    tree = tree[:5] + (get_worst(tree), ) + tree[6:]

def paint_aggr_tree_foldable(row):
    saved_expansion_level, treestate = bi.load_treestate()
    expansion_level = int(get_painter_option("aggr_expand"))
    if expansion_level != saved_expansion_level:
        treestate = {}

    mousecode = \
       'onmouseover="this.style.cursor=\'pointer\';" ' \
       'onmouseout="this.style.cursor=\'auto\';" ' \
       'onclick="toggle_subtree(this);" ' 

    only_problems = get_painter_option("aggr_onlyproblems") == "1" 

    def render_subtree(tree, path, show_host):
        nodes = tree[6]
        if nodes == []:
            return ''
        if nodes == None:
            return aggr_render_leaf(tree, show_host)
        else:
            h = '<span class=title>'

            path_id = "/".join(path)
            is_open = treestate.get(path_id)
            if is_open == None:
                is_open = len(path) <= expansion_level

            if is_open:
                style = ''
                mc = mousecode + 'src="images/tree_open.png" '
            else:
                style = 'style="display: none" '
                mc = mousecode + 'src="images/tree_closed.png" '

            h += aggr_render_node(tree, tree[2], mc, show_host)
            h += '<ul id="%d:%s" %sclass="subtree">' % (expansion_level, path_id, style)

            for node in tree[6]:
                estate = node[1] != None and node[1] or node[0]
                if only_problems and estate == 0:
                    continue

                h += '<li>' + render_subtree(node, path + [node[2]], show_host) + '</li>\n'
            return h + '</ul></span>\n'

    tree = row["aggr_treestate"]
    if only_problems: 
        filter_tree_only_problems(tree)

    affected_hosts = row["aggr_hosts"]
    htmlcode = render_subtree(tree, [tree[2]], len(affected_hosts) > 1)
    return "aggrtree", htmlcode


def paint_aggr_tree_ltr(row, mirror):
    wrap          = get_painter_option("aggr_wrap")

    if wrap == "wrap":
        td = '<td'
    else:
        td = '<td style="white-space: nowrap;"'

    def gen_table(tree, height, show_host):
        nodes = tree[6]
        is_leaf = nodes == None
        if is_leaf:
            return gen_leaf(tree, height, show_host)
        else:
            return gen_node(tree, height, show_host)

    def gen_leaf(tree, height, show_host):
        return [(aggr_render_leaf(tree, show_host), height, [])]

    def gen_node(tree, height, show_host):
        leaves = []
        for node in tree[6]:
            leaves += gen_table(node, height - 1, show_host)
        h = '<div class="aggr tree">' + aggr_render_node(tree, tree[2], '', show_host) + "</div>"
        if leaves:
            leaves[0][2].append((len(leaves), h))
        return leaves

    tree = row["aggr_treestate"]
    if get_painter_option("aggr_onlyproblems") == "1":
        filter_tree_only_problems(tree)
    depth = bi.status_tree_depth(tree)
    leaves = gen_table(tree, depth, row["aggr_hosts"] > 1)
    h = '<table class="aggrtree">'
    odd = "odd"
    for code, colspan, parents in leaves:
        h += '<tr>\n'
        leaf_td = td + ' class="leaf %s"' % odd
        odd = odd == "odd" and "even" or "odd"
        if colspan > 1:
            leaf_td += ' colspan=%d' % colspan
        leaf_td += '>%s</td>\n' % code

        tds = [leaf_td]
        for rowspan, c in parents:
            tds.append(td + ' class=node rowspan=%d>%s</td>\n' % (rowspan, c))
        if mirror:
            tds.reverse()
        h += "".join(tds)
        h += '</tr>\n'

    h += '</table>'
    return "aggrtree", h

def paint_aggregated_tree_state(row):
    treetype = get_painter_option("aggr_treetype")
    if treetype == "foldable":
        return paint_aggr_tree_foldable(row)
    elif treetype == "bottom-up":
        return paint_aggr_tree_ltr(row, False)
    else:
        return paint_aggr_tree_ltr(row, True)

multisite_painters["aggr_treestate"] = {
    "title"   : "Aggregation: complete tree",
    "short"   : "Tree",
    "columns" : [ "aggr_treestate", "aggr_hosts" ],
    "options" : [ "aggr_expand", "aggr_onlyproblems", "aggr_treetype", "aggr_wrap" ],
    "paint"   : paint_aggregated_tree_state,
}


#     _____ _ _ _                
#    |  ___(_) | |_ ___ _ __ ___ 
#    | |_  | | | __/ _ \ '__/ __|
#    |  _| | | | ||  __/ |  \__ \
#    |_|   |_|_|\__\___|_|  |___/
#                                

class BIGroupFilter(Filter):
    def __init__(self):
        self.column = "aggr_group"
        Filter.__init__(self, self.column, "Aggregation group", "aggr", [self.column], [self.column])

    def variable_settings(self, row):
        return [ (self.htmlvars[0], row[self.column]) ]

    def display(self):
        bi.html = html
        bi.compile_forest()
        htmlvar = self.htmlvars[0]
        html.select(htmlvar, [(g,g) for g in bi.g_aggregation_forest.keys()])

    def selected_group(self):
        return html.var(self.htmlvars[0])

    def heading_info(self, infoname):
        return html.var(self.htmlvars[0])

declare_filter( 90,  BIGroupFilter())

class BITextFilter(Filter):
    def __init__(self, what):
        self.column = "aggr_" + what 
        Filter.__init__(self, self.column, "Aggregation " + what, "aggr", [self.column], [self.column])

    def variable_settings(self, row):
        return [ (self.htmlvars[0], row[self.column]) ]

    def display(self):
        html.text_input(self.htmlvars[0])

    def heading_info(self, infoname):
        return html.var(self.htmlvars[0])

    def filter_table(self, rows):
        val = html.var(self.htmlvars[0])
        if not val:
            return rows
        reg = re.compile(val.lower())
        return [ row for row in rows if reg.search(row[self.column].lower()) ]

declare_filter(120, BITextFilter("name"))
declare_filter(121, BITextFilter("output"))

class BIHostFilter(Filter):
    def __init__(self):
        self.column = "aggr_hosts"
        Filter.__init__(self, self.column, "Affected hosts contain", "aggr", ["site", "host"], [])

    def display(self):
        html.text_input(self.htmlvars[1])

    def heading_info(self, infoname):
        return html.var(self.htmlvars[1])

    def find_host(self, host, hostlist):
        for s, h in hostlist:
            if h == host:
                return True
        return False

    # Used for linking
    def variable_settings(self, row):
        return [ ("host", row["host_name"]), ("site", row["site"]) ]

    def filter_table(self, rows):
        val = html.var(self.htmlvars[1])
        if not val:
            return rows
        return [ row for row in rows if self.find_host(val, row["aggr_hosts"]) ]

declare_filter(130, BIHostFilter(), "Filter for all aggregations that base on status information of that host. Exact match (no regular expression)")

class BIServiceFilter(Filter):
    def __init__(self):
        Filter.__init__(self, "aggr_service", "Affected by service", "host", ["site", "host", "service"], [])

    def display(self):
        html.write("Host: ")
        html.text_input("host")
        html.write("Service: ")
        html.text_input("service")

    def heading_info(self, infoname):
        return html.var("host") + " / " + html.var("service")

    def service_spec(self):
        return html.var("site"), html.var("host"), html.var("service")

    # Used for linking
    def variable_settings(self, row):
        return [ ("site", row["site"]), ("host", row["host_name"]), ("service", row["service_description"]) ]

declare_filter(131, BIServiceFilter(), "Filter for all aggregations that are affected by one specific service on a specific host (no regular expression)")

class BIStatusFilter(Filter):
    def __init__(self, what):
        title = (what.replace("_", " ") + " state").title()
        self.column = "aggr_" + what + "state"
        if what == "":
            self.code = 'r'
        else:
            self.code = what[0]
        self.prefix = "bi%ss" % self.code
        vars = [ self.prefix + str(x) for x in [ -1, 0, 1, 2, 3 ] ]
        if self.code == 'a':
            vars.append(self.prefix + "n")
        Filter.__init__(self, self.column, title, "aggr", vars, [])

    def filter(self, tablename):
        return ""

    def display(self):
        if html.var("filled_in"):
            defval = ""
        else:
            defval = "on"
        for varend, text in [('0', 'OK'), ('1', 'WARN'), ('2', 'CRIT'), ('3', 'UNKNOWN'), ('-1', 'PENDING'), ('n', 'unset')]:
            if self.code != 'a' and varend == 'n':
                continue # no unset for read and effective state
            var = self.prefix + varend
            html.checkbox(var, defval)
            html.write(" %s " % text)

    def filter_table(self, rows):
        jeaders = []
        if html.var("filled_in"):
            defval = ""
        else:
            defval = "on"

        allowed_states = []
        for i in ['0','1','2','3','-1','n']:
            if html.var(self.prefix + i, defval) == "on":
                if i == 'n':
                    s = None
                else:
                    s = int(i)
                allowed_states.append(s)
        newrows = []
        for row in rows:
            if row[self.column] in allowed_states:
                newrows.append(row)
        return newrows

declare_filter(150,  BIStatusFilter(""))
declare_filter(151,  BIStatusFilter("effective_"))
declare_filter(152,  BIStatusFilter("assumed_"))


