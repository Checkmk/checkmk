#!/usr/bin/python

import check_mk, livestatus, htmllib, views
from lib import *

def link(text, target):
    if not target.startswith("http:"):
	target = check_mk.checkmk_web_uri + "/" + target 
    return "<a target=\"main\" class=link href=\"%s\">%s</a>" % (target, htmllib.attrencode(text))

def bulletlink(text, target):
    html.write("<li class=sidebar>" + link(text, target) + "</li>\n")

def sidebar(h):
    global html
    html = h
    html.write("<div class=header><table><tr>"
		"<td class=title><a target=\"main\" href=\"http://mathias-kettner.de/check_mk.html\">Check_MK</a></td>"
		"<td class=logo><a target=\"_blank\" href=\"http://mathias-kettner.de\"><img border=0 src=\"%s/MK-mini-black.gif\"></a></td>"
		"</tr></table></div>\n" % \
	    check_mk.checkmk_web_uri)
    render_adminlinks()
    render_views()


def render_adminlinks():
    html.write("<div class=section>\n")
    html.heading("Administration")
    bulletlink("Edit views", "edit_views.py")
    bulletlink("Multiadmin", "filter.py")
    bulletlink("Logwatch", "logwatch.py")
    bulletlink("Documentation", "http://mathias-kettner.de/checkmk.html")
    html.write("</div>\n")

def render_views():
    html.write("<div class=section>\n")
    html.heading("Views")
    views.load_views()
    authuser = html.req.user
    for (user, name), view in views.multisite_views.items():
	if user == authuser or view["public"]:
	    bulletlink(view["title"], "view.py?view_name=%s/%s" % (user, name))
    html.write("</div>\n")

