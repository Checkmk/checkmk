#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2012             mk@mathias-kettner.de |
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

import bi

#     ____        _
#    |  _ \  __ _| |_ __ _ ___  ___  _   _ _ __ ___ ___  ___
#    | | | |/ _` | __/ _` / __|/ _ \| | | | '__/ __/ _ \/ __|
#    | |_| | (_| | || (_| \__ \ (_) | |_| | | | (_|  __/\__ \
#    |____/ \__,_|\__\__,_|___/\___/ \__,_|_|  \___\___||___/
#


multisite_datasources["bi_aggregations"] = {
    "title"       : _("BI Aggregations"),
    "table"       : bi.table,
    "infos"       : [ "aggr" ],
    "keys"        : [],
    "idkeys"      : [ 'aggr_name' ],
}

multisite_datasources["bi_host_aggregations"] = {
    "title"       : _("BI Aggregations affected by one host"),
    "table"       : bi.host_table,
    "infos"       : [ "host", "aggr" ],
    "keys"        : [],
    "idkeys"      : [ 'aggr_name' ],
}

# Similar to host aggregations, but the name of the aggregation
# is used to join the host table rather then the affected host
multisite_datasources["bi_hostname_aggregations"] = {
    "title"       : _("BI Hostname Aggregations"),
    "table"       : bi.hostname_table,
    "infos"       : [ "host", "aggr" ],
    "keys"        : [],
    "idkeys"      : [ 'aggr_name' ],
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
        name = nagios_short_state_names[state["state"]]
        classes = "state svcstate state%s" % state["state"]
        if assumed:
            classes += " assumed"
        return classes, name

multisite_painters["aggr_state"] = {
    "title"   : _("Aggregated state"),
    "short"   : _("State"),
    "columns" : [ "aggr_effective_state" ],
    "paint"   : lambda row: paint_aggr_state_short(row["aggr_effective_state"], row["aggr_effective_state"] != row["aggr_state"])
}

multisite_painters["aggr_state_num"] = {
    "title"   : _("Aggregated state (number)"),
    "short"   : _("State"),
    "columns" : [ "aggr_effective_state" ],
    "paint"   : lambda row: ("", str(row["aggr_effective_state"]['state']))
}

multisite_painters["aggr_real_state"] = {
    "title"   : _("Aggregated real state (never assumed)"),
    "short"   : _("R.State"),
    "columns" : [ "aggr_state" ],
    "paint"   : lambda row: paint_aggr_state_short(row["aggr_state"])
}

multisite_painters["aggr_assumed_state"] = {
    "title"   : _("Aggregated assumed state"),
    "short"   : _("Assumed"),
    "columns" : [ "aggr_assumed_state" ],
    "paint"   : lambda row: paint_aggr_state_short(row["aggr_assumed_state"])
}


multisite_painters["aggr_group"] = {
    "title"   : _("Aggregation group"),
    "short"   : _("Group"),
    "columns" : [ "aggr_group" ],
    "paint"   : lambda row: ("", row["aggr_group"])
}

multisite_painters["aggr_name"] = {
    "title"   : _("Aggregation name"),
    "short"   : _("Aggregation"),
    "columns" : [ "aggr_name" ],
    "paint"   : lambda row: ("", row["aggr_name"])
}

multisite_painters["aggr_output"] = {
    "title"   : _("Aggregation status output"),
    "short"   : _("Output"),
    "columns" : [ "aggr_output" ],
    "paint"   : lambda row: ("", row["aggr_output"])
}

def paint_aggr_hosts(row, link_to_view):
    h = []
    for site, host in row["aggr_hosts"]:
        url = html.makeuri([("view_name", link_to_view), ("site", site), ("host", host)])
        h.append('<a href="%s">%s</a>' % (url, host))
    return "", " ".join(h)

multisite_painters["aggr_hosts"] = {
    "title"   : _("Aggregation: affected hosts"),
    "short"   : _("Hosts"),
    "columns" : [ "aggr_hosts" ],
    "paint"   : lambda row: paint_aggr_hosts(row, "aggr_host"),
}

multisite_painters["aggr_hosts_services"] = {
    "title"   : _("Aggregation: affected hosts (link to host page)"),
    "short"   : _("Hosts"),
    "columns" : [ "aggr_hosts" ],
    "paint"   : lambda row: paint_aggr_hosts(row, "host"),
}

multisite_painter_options["aggr_expand"] = {
 "title"   : _("Initial expansion of aggregations"),
 "default" : "0",
 "values"  : [ ("0", "collapsed"), ("1", "first level"), ("2", "two levels"), ("3", "three levels"), ("999", "complete")]
}

multisite_painter_options["aggr_onlyproblems"] = {
 "title"   : _("Show only problems"),
 "default" : "0",
 "values"  : [ ("0", "show all"), ("1", "show only problems")]
}

multisite_painter_options["aggr_treetype"] = {
 "title"   : _("Type of tree layout"),
 "default" : "foldable",
 "values"  : [ 
    ("foldable",     _("foldable")), 
    ("boxes",        _("boxes")),
    ("boxes-omit-root", _("boxes (omit root)")),
    ("bottom-up",    _("bottom up")), 
    ("top-down",     _("top down"))]
}

multisite_painter_options["aggr_wrap"] = {
 "title"   : _("Handling of too long texts"),
 "default" : "wrap",
 "values"  : [ ("wrap", "wrap"), ("nowrap", "don't wrap")]
}


def render_bi_state(state):
    return { bi.PENDING: _("PD"),
             bi.OK:      _("OK"),
             bi.WARN:    _("WA"),
             bi.CRIT:    _("CR"),
             bi.UNKNOWN: _("UN"),
             bi.MISSING: _("MI"),
             bi.UNAVAIL: _("NA"),
    }.get(state, _("??"))

def render_assume_icon(site, host, service):
    if service:
        key = (site, host, service)
    else:
        key = (site, host)
    ass = bi.g_assumptions.get(key)
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
        host_url = html.makeuri([("view_name", "hoststatus"), ("site", site), ("host", host)])

    if service:
        service_url = html.makeuri([("view_name", "service"), ("site", site), ("host", host), ("service", service)])

    if show_host:
        content += '<a href="%s">%s</a><b class=bullet>&diams;</b>' % (host_url, host.replace(" ", "&nbsp;"))

    if not service:
        content += '<a href="%s">%s</a>' % (host_url, _("Host&nbsp;status"))
    else:
        content += '<a href="%s">%s</a>' % (service_url, service.replace(" ", "&nbsp;"))

    if bare:
        return content
    else:
        return aggr_render_node(tree, content, None, show_host)

def aggr_render_node(tree, title, mousecode, show_host):
    state = tree[0]
    assumed_state = tree[1]
    if assumed_state != None:
        effective_state = assumed_state
    else:
        effective_state = state

    if (effective_state != state):
        addclass = " " + _("assumed")
    else:
        addclass = ""

    h = '<span class="content state state%d%s">%s</span>\n' \
         % (effective_state["state"], addclass, render_bi_state(effective_state["state"]))
    if mousecode:
        h += '<img class=opentree %s>' % mousecode
        h += '<span class="content name">%s</span>' % title
    else:
        h += title

    output = effective_state["output"]
    if output:
        output = "<b class=bullet>&diams;</b>" + output
    else:
        output = ""
    h += '<span class="content output">%s</span>\n' % output
    return h


# Convert tree to tree contain only node in non-OK state
def filter_tree_only_problems(tree):
    state, assumed_state, node, subtrees = tree
    # remove subtrees in state OK
    new_subtrees = []
    for subtree in subtrees:
        effective_state = subtree[1] != None and subtree[1] or subtree[0]
        if effective_state["state"] != bi.OK:
            if len(subtree) == 3:
                new_subtrees.append(subtree)
            else:
                new_subtrees.append(filter_tree_only_problems(subtree))

    return state, assumed_state, node, new_subtrees


def paint_aggr_tree_foldable(row, boxes, omit_root=True):
    saved_expansion_level = bi.load_ex_level()
    treestate = weblib.get_tree_states('bi')
    expansion_level = int(get_painter_option("aggr_expand"))
    if expansion_level != saved_expansion_level:
        treestate = {}
        weblib.set_tree_states('bi', treestate)
        weblib.save_tree_states()

    mousecode = \
       'onmouseover="this.style.cursor=\'pointer\';" ' \
       'onmouseout="this.style.cursor=\'auto\';" ' \
       'onclick="bi_toggle_%s(this);" ' % (boxes and "box" or "subtree")

    def render_subtree(tree, path, show_host):
        is_leaf = len(tree) == 3
        path_id = "/".join(path)
        is_open = treestate.get(path_id)
        if is_open == None:
            is_open = len(path) <= expansion_level

        h = ""
        
        state = tree[0]

        # Variant: BI-Boxes
        if boxes:
            if is_leaf:
                leaf = "leaf"
                mc = ""
            else:
                leaf = "noleaf"
                mc = mousecode

            omit = omit_root and len(path) == 1
            if not omit:
                h += '<span id="%d:%s" %s class="bibox_box %s %s state%s">' % (
                        expansion_level, path_id, mc, leaf, is_open and "open" or "closed", state["state"])
                if is_leaf:
                    h += aggr_render_leaf(tree, show_host, bare = True) # .replace(" ", "&nbsp;")
                else:
                    h += tree[2]["title"].replace(" ", "&nbsp;")
                h += '</span> '

            if not is_leaf:
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

                for node in tree[3]:
                    estate = node[1] != None and node[1] or node[0]

                    if not node[2].get("hidden"):
                        new_path = path + [node[2]["title"]]
                        h += '<li>' + render_subtree(node, new_path, show_host) + '</li>\n'
                h += '</ul>'
            return h + '</span>\n'

    tree = row["aggr_treestate"]
    if get_painter_option("aggr_onlyproblems") == "1":
        tree = filter_tree_only_problems(tree)

    affected_hosts = row["aggr_hosts"]
    htmlcode = render_subtree(tree, [tree[2]["title"]], len(affected_hosts) > 1)
    return "aggrtree" + (boxes and "_box" or ""), htmlcode


def paint_aggr_tree_ltr(row, mirror):
    wrap = get_painter_option("aggr_wrap")

    if wrap == "wrap":
        td = '<td'
    else:
        td = '<td style="white-space: nowrap;"'

    def gen_table(tree, height, show_host):
        if len(tree) == 3:
            return gen_leaf(tree, height, show_host)
        else:
            return gen_node(tree, height, show_host)

    def gen_leaf(tree, height, show_host):
        return [(aggr_render_leaf(tree, show_host), height, [])]

    def gen_node(tree, height, show_host):
        leaves = []
        for node in tree[3]:
            if not node[2].get("hidden"):
                leaves += gen_table(node, height - 1, show_host)
        h = '<div class="aggr tree">' + aggr_render_node(tree, tree[2]["title"], '', show_host) + "</div>"
        if leaves:
            leaves[0][2].append((len(leaves), h))
        return leaves

    tree = row["aggr_treestate"]
    if get_painter_option("aggr_onlyproblems") == "1":
        tree = filter_tree_only_problems(tree)
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
        return paint_aggr_tree_foldable(row, boxes = False, omit_root = False)
    elif treetype == "boxes":
        return paint_aggr_tree_foldable(row, boxes = True, omit_root = False)
    elif treetype == "boxes-omit-root":
        return paint_aggr_tree_foldable(row, boxes = True, omit_root = True)
    elif treetype == "bottom-up":
        return paint_aggr_tree_ltr(row, False)
    elif treetype == "top-down":
        return paint_aggr_tree_ltr(row, True)

multisite_painters["aggr_treestate"] = {
    "title"   : _("Aggregation: complete tree"),
    "short"   : _("Tree"),
    "columns" : [ "aggr_treestate", "aggr_hosts" ],
    "options" : [ "aggr_expand", "aggr_onlyproblems", "aggr_treetype", "aggr_wrap" ],
    "paint"   : paint_aggregated_tree_state,
}

multisite_painters["aggr_treestate_boxed"] = {
    "title"   : _("Aggregation: simplistic boxed layout"),
    "short"   : _("Tree"),
    "columns" : [ "aggr_treestate", "aggr_hosts" ],
    "paint"   : lambda row: paint_aggr_tree_foldable(row, boxes = True, omit_root = True),
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
        Filter.__init__(self, self.column, _("Aggregation group"), "aggr", [self.column], [self.column])

    def variable_settings(self, row):
        return [ (self.htmlvars[0], row[self.column]) ]

    def display(self):
        bi.compile_forest(config.user_id)
        htmlvar = self.htmlvars[0]
        html.select(htmlvar, [ ("", "") ] + [(g,g) for g in bi.g_user_cache["forest"].keys()])

    def selected_group(self):
        return html.var(self.htmlvars[0])

    def filter_table(self, rows):
        group = self.selected_group()
        if not group:
            return rows
        else:
            return [ row for row in rows if row[self.column] == group ]

    def heading_info(self, infoname):
        return html.var(self.htmlvars[0])

declare_filter( 90,  BIGroupFilter())

class BITextFilter(Filter):
    def __init__(self, what):
        self.column = "aggr_" + what
        label = ''
        if what == 'name':
            label = _('Aggregation name')
        elif what == 'output':
            label = _('Aggregation output')
        Filter.__init__(self, self.column, label, "aggr", [self.column], [self.column])

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
        Filter.__init__(self, self.column, _("Affected hosts contain"), "aggr", ["site", "host"], [])

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

declare_filter(130, BIHostFilter(), _("Filter for all aggregations that base on status information of that host. Exact match (no regular expression)"))

class BIServiceFilter(Filter):
    def __init__(self):
        Filter.__init__(self, "aggr_service", _("Affected by service"), "aggr", ["site", "host", "service"], [])

    def double_height(self):
        return True

    def display(self):
        html.write(_("Host") + ": ")
        html.text_input("host")
        html.write(_("Service") + ": ")
        html.text_input("service")

    def heading_info(self, infoname):
        return html.var_utf8("host") + " / " + html.var_utf8("service")

    def service_spec(self):
        return html.var_utf8("site"), html.var_utf8("host"), html.var_utf8("service")

    # Used for linking
    def variable_settings(self, row):
        return [ ("site", row["site"]), ("host", row["host_name"]), ("service", row["service_description"]) ]

declare_filter(131, BIServiceFilter(), _("Filter for all aggregations that are affected by one specific service on a specific host (no regular expression)"))

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

    def double_height(self):
        return self.column == "aggr_assumed_state"

    def display(self):
        if html.var("filled_in"):
            defval = ""
        else:
            defval = "on"
        for varend, text in [('0', 'OK'), ('1', 'WARN'), ('2', 'CRIT'), 
                             ('3', 'UNKN'), ('-1', 'PENDING'), ('n', _('no assumed state set'))]:
            if self.code != 'a' and varend == 'n':
                continue # no unset for read and effective state
            if varend == 'n':
                html.write("<br>")
            var = self.prefix + varend
            html.checkbox(var, defval, label = text)

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
            if row[self.column] != None:
                s = row[self.column]["state"]
            else:
                s = None
            if s in allowed_states:
                newrows.append(row)
        return newrows

declare_filter(150,  BIStatusFilter(""))
declare_filter(151,  BIStatusFilter("effective_"))
declare_filter(152,  BIStatusFilter("assumed_"))


