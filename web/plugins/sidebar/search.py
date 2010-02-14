#!/usr/bin/python

import views

def render_searchform():
    html.write('<script type="text/javascript" src="/check_mk/search.js"></script>')
    html.write('<div id="mk_side_search">')
    html.write('<input id="mk_side_search_field" type="text" name="search" />')
    html.write('</div>')
    html.write('<script type="text/javascript">')

    # Store (user) hosts in JS array
    data = html.live.query("GET hosts\nColumns: name alias\n")
    html.write('var aSearchHosts = %s;' % data)

    html.write('addField("mk_side_search_field");</script>')


    #data = html.live.query("GET %sgroups\nColumns: name alias\n" % what)
    #name_to_alias = dict(data)
    #groups = [(name_to_alias[name], name) for name in name_to_alias.keys()]
    #groups.sort() # sort by Alias!
    #for alias, name in groups:
        #target = views.get_context_link(html.req.user, "%sgroup" % what)
        #bulletlink(alias, target + "&%sgroup=%s" % (what, htmllib.urlencode(name)))

sidebar_snapins["search"] = {
    "title" : "Quicksearch",
    "render" : lambda: render_searchform()
}
