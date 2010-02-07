#!/usr/bin/python

import check_mk, livestatus, htmllib, views
from lib import *

def page_views(html):
    authuser = html.req.user
    html.html_head("Check_MK Live Views")
    html.write("<body class=side>\n")
    html.heading("Views")
    views.load_views()
# html.write("<ul class=views>")
    for (user, name), view in views.multisite_views.items():
	if user == authuser or view["public"]:
	    html.write("<li class=view><a target=\"main\" class=view href=\"view.py?view_name=%s/%s\">%s</a></li>\n" % (user, name, htmllib.attrencode(view["title"])))

    def link(title, target):
	html.write("<li><a target=\"main\" class=link href=\"%s\">%s</a></li>" % (target, title))
    html.heading("Administration")
    link("Edit views", "/check_mk/edit_views.py")
    link("Multiadmin", "/check_mk/filter.py")
    html.write("</body>\n") 
    html.html_foot()
