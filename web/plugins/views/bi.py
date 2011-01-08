import bi

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
        url = html.makeuri([("view_name", "host"), ("site", site), ("host", host)])
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


def render_bi_state(state):
    return { bi.OK:      "OK", 
             bi.WARN:    "WA",
             bi.CRIT:    "CR", 
             bi.UNKNOWN: "UN",
             bi.MISSING: "MI",
             bi.UNAVAIL: "NA",
    }[state]

def render_assume_icon(site, host, service):
    ass = bi.g_assumptions.get((site, host, service))
    mousecode = \
       'onmouseover="this.style.cursor=\'pointer\';" ' \
       'onmouseout="this.style.cursor=\'auto\';" ' \
       'title="Assume another state for this item" ' \
       'onclick="toggle_assumption(this, %s, %s, %s);" ' % \
         (repr(site), repr(str(host)), service == None and 'null' or repr(str(service)))
    current = str(ass).lower()
    return '<img state="%s" class=assumption %s src="images/assume_%s.png">' % (current, mousecode, current)

def aggr_render_leaf(tree):
    site, host = tree[4][0]
    service = tree[2]
    content = render_assume_icon(site, host, service) 
    # site fehlt!
    if service:
        url = html.makeuri([("view_name", "service"), ("site", site), ("host", host), ("service", service)])
    else:
        url = html.makeuri([("view_name", "hoststatus"), ("site", site), ("host", host)])
        service = "Host status"
    content += '<a href="%s">%s</a>' % (url, service)
    return '<div class="aggr leaf">' + aggr_render_node(tree, content, "") + '</div>'

def aggr_render_node(tree, title, mousecode):
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
    h = '<div style="float: left" class="content state state%d%s">%s</div>' \
         % (effective_state, addclass, render_bi_state(effective_state))
    h += '<div style="float: left;" %s class="content name">%s</div>' % (mousecode, title)
    output = tree[3]
    if output:
        output = "&nbsp;&diams; " + output
    else:
        output = "&nbsp;"
    h += '<div class="content output">%s</div>' % output
    return h


def paint_aggr_tree_foldable(row):
    only_problems = get_painter_option("aggr_onlyproblems") == "1"

    def render_subtree(tree, level=1):
        nodes = tree[6]
        is_leaf = nodes == None
        if is_leaf:
            return aggr_render_leaf(tree)
        else:
            mousecode = \
               'onmouseover="this.style.cursor=\'pointer\';" ' \
               'onmouseout="this.style.cursor=\'auto\';" ' \
               'onclick="toggle_subtree(this);" '
            h = '<div class="aggr tree">'
            h += aggr_render_node(tree, tree[2], mousecode)

            expansion_level = int(get_painter_option("aggr_expand"))
            if level > expansion_level:
                style = 'style="display: none" '
            else:
                style = ''
            h += '<div %sclass="subtree">' % style
            for node in tree[6]:
                if only_problems and node[0] == 0:
                    continue
                h += render_subtree(node, level + 1)
            return h + '</div></div>'

    tree = row["aggr_treestate"]
    return "", render_subtree(tree)


def paint_aggr_tree_ltr(row, mirror):
    # We need to know the depth of the tree

    def gen_table(tree, height):
        nodes = tree[6]
        is_leaf = nodes == None
        if is_leaf:
            return gen_leaf(tree, height)
        else:
            return gen_node(tree, height)

    def gen_leaf(tree, height):
        return [(aggr_render_leaf(tree), height, [])]

    def gen_node(tree, height):
        leaves = []
        for node in tree[6]:
            leaves += gen_table(node, height - 1)
        h = '<div class="aggr tree">' + aggr_render_node(tree, tree[2], '') + "</div>"
        leaves[0][2].append((len(leaves), h))
        return leaves

    tree = row["aggr_treestate"]
    depth = bi.status_tree_depth(tree)
    leaves = gen_table(tree, depth)
    h = '<table class="aggrtree">'
    odd = "odd"
    for code, colspan, parents in leaves:
        h += '<tr>\n'
        leaf_td = '<td class="leaf %s"' % odd
        odd = odd == "odd" and "even" or "odd"
        if colspan > 1:
            leaf_td += ' colspan=%d' % colspan
        leaf_td += '>%s</td>\n' % code

        tds = [leaf_td]
        for rowspan, c in parents:
            tds.append('<td class=node rowspan=%d>%s</td>\n' % (rowspan, c))
        if mirror:
            tds.reverse()
        h += "".join(tds)
        h += '</tr>\n'

    h += '</table>'
    return "", h

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
    "columns" : [ "aggr_treestate" ],
    "options" : [ "aggr_expand", "aggr_onlyproblems", "aggr_treetype" ],
    "paint"   : paint_aggregated_tree_state,
}

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
        Filter.__init__(self, self.column, "Affected hosts contain", "aggr", [self.column], [])

    def display(self):
        html.text_input(self.htmlvars[0])

    def heading_info(self, infoname):
        return html.var(self.htmlvars[0])

    def find_host(self, host, hostlist):
        for s, h in hostlist:
            if h == host:
                return True
        return False

    def filter_table(self, rows):
        val = html.var(self.htmlvars[0])
        if not val:
            return rows
        return [ row for row in rows if self.find_host(val, row["aggr_hosts"]) ]

declare_filter(130, BIHostFilter(), "Filter for all aggregations that base on status information of that host. Exact match (no regular expression)")

class BIStatusFilter(Filter):
    def __init__(self, what):
        title = (what.replace("_", " ") + " state").title()
        self.column = "aggr_" + what + "state"
        if what == "":
            self.code = 'r'
        else:
            self.code = what[0]
        self.prefix = "bi%ss" % self.code
        vars = [ self.prefix + str(x) for x in [ 0, 1, 2, 3 ] ]
        if self.code == 'a':
            vars.append(self.prefix + "n")
        Filter.__init__(self, self.column, title, "aggr", vars, [])

    def filter(self, tablename):
        return ""

    def display(self):
        if html.var("filled_in"):
            defval = "on"
        else:
            defval = "on"
        for varend, text in [('0', 'OK'), ('1', 'WARN'), ('2', 'CRIT'), ('3', 'UNKNOWN'), ('n', 'unset')]:
            if self.code != 'a' and varend == 'n':
                continue # no unset for read and effective state
            var = self.prefix + varend
            html.checkbox(var, defval)
            html.write(" %s " % text)

    def filter_table(self, rows):
        headers = []
        if html.var("filled_in"):
            defval = ""
        else:
            defval = "on"

        allowed_states = []
        for i in ['0','1','2','3','n']:
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


