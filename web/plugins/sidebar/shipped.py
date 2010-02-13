#!/usr/bin/python


def render_adminlinks():
    bulletlink("Edit views", "edit_views.py")
    bulletlink("Multiadmin", "filter.py")
    bulletlink("Logwatch", "logwatch.py")
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

