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

    html.write('mkSearchAddField("mk_side_search_field", "main", "%s");</script>' % check_mk.checkmk_web_uri)

sidebar_snapins["search"] = {
    "title" : "Quicksearch",
    "render" : render_searchform
}
