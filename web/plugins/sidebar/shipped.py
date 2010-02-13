#!/usr/bin/python


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
    views.load_views()
    authuser = html.req.user
    for (user, name), view in views.multisite_views.items():
	if user == authuser or view["public"]:
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
    for alias, name in groups:
	bulletlink(alias, "views.py?view_name=%sgroup&%sgroup=%s" % (what, what, htmllib.urlencode(name)))

sidebar_snapins["hostgroups"] = {
    "title" : "Hostgroups",
    "render" : lambda: render_groups("host")
}
sidebar_snapins["servicegroups"] = {
    "title" : "Servicegroups",
    "render" : lambda: render_groups("service")
}


