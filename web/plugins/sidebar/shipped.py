#!/usr/bin/python

import views

def render_adminlinks():
    bulletlink("Edit views",    "edit_views.py")
    bulletlink("Multiadmin",    "filter.py")
    bulletlink("Logwatch",      "logwatch.py")
    bulletlink("Documentation", "http://mathias-kettner.de/checkmk.html")

sidebar_snapins["admin"] = {
    "title" : "Administration",
    "render" : render_adminlinks
}

def render_views():
    views.load_views(override_builtins = html.req.user)
    authuser = html.req.user
    for (user, name), view in views.multisite_views.items():
	if not view["hidden"] and (user == authuser or view["public"]):
	    bulletlink(view["title"], "view.py?view_name=%s/%s" % (user, name))

sidebar_snapins["views"] = {
    "title" : "Views",
    "render" : render_views
}

def render_groups(what):
    data = html.live.query("GET %sgroups\nColumns: name alias\n" % what)
    name_to_alias = dict(data)
    groups = [(name_to_alias[name], name) for name in name_to_alias.keys()]
    groups.sort() # sort by Alias!
    target = views.get_context_link(html.req.user, "%sgroup" % what)
    for alias, name in groups:
	bulletlink(alias, target + "&%sgroup=%s" % (what, htmllib.urlencode(name)))

sidebar_snapins["hostgroups"] = {
    "title" : "Hostgroups",
    "render" : lambda: render_groups("host")
}
sidebar_snapins["servicegroups"] = {
    "title" : "Servicegroups",
    "render" : lambda: render_groups("service")
}

def render_hosts():
    hosts = html.live.query_column_unique("GET hosts\nColumns: name\n")
    hosts.sort()
    target = views.get_context_link(html.req.user, "host")
    for host in hosts:
	bulletlink(host, target + "&host=" + htmllib.urlencode(host))

sidebar_snapins["hosts"] = {
    "title" : "All hosts",
    "render" : render_hosts
}
    

def render_sitestatus():
    if check_mk.is_multisite():
	html.write("<table cellspacing=0 class=sitestate>")
	for sitename in check_mk.sites():
	    site = check_mk.site(sitename)
	    html.write("<tr><td class=left>%s</td>" % site["alias"])
	    state = html.site_status[sitename]["state"]
	    if state == "disabled":
		switch = "on"
	    else:
		switch = "off"
	    onclick = "switch_site('%s', '_site_switch=%s:%s')" % (check_mk.checkmk_web_uri, sitename, switch)
	    html.write("<td class=%s>" % state)
	    html.write("<a href=\"\" onclick=\"%s\">%s</a></td>" % (onclick, state[:3]))
	    html.write("</tr>\n")
	html.write("</table>\n")
    

if check_mk.is_multisite():
    sidebar_snapins["sitestatus"] = {
	"title" : "Site status",
	"hidetitle" : True,
	"render" : render_sitestatus
    }
