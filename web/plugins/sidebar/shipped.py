#!/usr/bin/python

import views

# --------------------------------------------------------------
#       _       _           _       _ _       _        
#      / \   __| |_ __ ___ (_)_ __ | (_)_ __ | | _____ 
#     / _ \ / _` | '_ ` _ \| | '_ \| | | '_ \| |/ / __|
#    / ___ \ (_| | | | | | | | | | | | | | | |   <\__ \
#   /_/   \_\__,_|_| |_| |_|_|_| |_|_|_|_| |_|_|\_\___/
#                                                      
# --------------------------------------------------------------
def render_adminlinks():
    bulletlink("Edit views",    "edit_views.py")
    bulletlink("Multiadmin",    "filter.py")
    bulletlink("Logwatch",      "logwatch.py")
    bulletlink("Documentation", "http://mathias-kettner.de/checkmk.html")

sidebar_snapins["admin"] = {
    "title" : "Administration",
    "render" : render_adminlinks
}

# --------------------------------------------------------------
#   __     ___                   
#   \ \   / (_) _____      _____ 
#    \ \ / /| |/ _ \ \ /\ / / __|
#     \ V / | |  __/\ V  V /\__ \
#      \_/  |_|\___| \_/\_/ |___/
#                                
# --------------------------------------------------------------
def render_views():
    views.load_views(override_builtins = html.req.user)
    authuser = html.req.user
    s = [ (view["title"], user, name, view) for (user, name), view in views.multisite_views.items() ]
    s.sort()
    for title, user, name, view in s:
	if not view["hidden"] and (user == authuser or view["public"]):
	    bulletlink(title, "view.py?view_name=%s/%s" % (user, name))

sidebar_snapins["views"] = {
    "title" : "Views",
    "render" : render_views
}

# --------------------------------------------------------------
#    ____                  _                     __
#   / ___|  ___ _ ____   _(_) ___ ___           / /
#   \___ \ / _ \ '__\ \ / / |/ __/ _ \_____    / / 
#    ___) |  __/ |   \ V /| | (_|  __/_____|  / /  
#   |____/ \___|_|    \_/ |_|\___\___|       /_/   
#                                                  
#   _   _           _                                  
#  | | | | ___  ___| |_ __ _ _ __ ___  _   _ _ __  ___ 
#  | |_| |/ _ \/ __| __/ _` | '__/ _ \| | | | '_ \/ __|
#  |  _  | (_) \__ \ || (_| | | | (_) | |_| | |_) \__ \
#  |_| |_|\___/|___/\__\__, |_|  \___/ \__,_| .__/|___/
#                      |___/                |_|        
# --------------------------------------------------------------
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

# --------------------------------------------------------------
#    _   _           _       
#   | | | | ___  ___| |_ ___ 
#   | |_| |/ _ \/ __| __/ __|
#   |  _  | (_) \__ \ |_\__ \
#   |_| |_|\___/|___/\__|___/
#                            
# --------------------------------------------------------------
def render_hosts():
    html.live.set_prepend_site(True)
    hosts = html.live.query("GET hosts\nColumns: name\n")
    html.live.set_prepend_site(False)
    hosts.sort()
    target = views.get_context_link(html.req.user, "host")
    for site, host in hosts:
	bulletlink(host, target + ("&host=%s&site=%s" % (htmllib.urlencode(host), htmllib.urlencode(site))))

sidebar_snapins["hosts"] = {
    "title" : "All hosts",
    "render" : render_hosts
}
    

# --------------------------------------------------------------
#    ____  _ _            _        _             
#   / ___|(_) |_ ___  ___| |_ __ _| |_ _   _ ___ 
#   \___ \| | __/ _ \/ __| __/ _` | __| | | / __|
#    ___) | | ||  __/\__ \ || (_| | |_| |_| \__ \
#   |____/|_|\__\___||___/\__\__,_|\__|\__,_|___/
#                                                
# --------------------------------------------------------------
def render_sitestatus():
    if check_mk.is_multisite():
	html.write("<table cellspacing=0 class=sitestate>")
	for sitename in check_mk.sites():
	    site = check_mk.site(sitename)
	    html.write("<tr><td class=left>%s</td>" % link(site["alias"], "view.py?view_name=/sitehosts&site=%s" % sitename))
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
#	"hidetitle" : True,
	"render" : render_sitestatus
    }


# --------------------------------------------------------------
#    _____          _   _           _                             _               
#   |_   _|_ _  ___| |_(_) ___ __ _| |   _____   _____ _ ____   _(_) _____      __
#     | |/ _` |/ __| __| |/ __/ _` | |  / _ \ \ / / _ \ '__\ \ / / |/ _ \ \ /\ / /
#     | | (_| | (__| |_| | (_| (_| | | | (_) \ V /  __/ |   \ V /| |  __/\ V  V / 
#     |_|\__,_|\___|\__|_|\___\__,_|_|  \___/ \_/ \___|_|    \_/ |_|\___| \_/\_/  
#                                                                                 
# --------------------------------------------------------------
import time
def render_tactical_overview():
    html.write("HIRNIBALDi: %s" % time.time())
		    
sidebar_snapins["tactical_overview"] = {
    "title" : "Tactical Overview",
    "refresh" : 10,
    "render" : render_tactical_overview
}

def render_performance():
    data = html.live.query("GET status\nColumns: service_checks_rate host_checks_rate\n")
    for what, col in [("service", 0), ("host", 1)]:
	html.write("%schecks/sec: %.2f<br>" % (what, sum([row[col] for row in data])))
		    
sidebar_snapins["performance"] = {
    "title" : "Server performance",
    "refresh" : 5,
    "render" : render_performance
}

import time
def render_current_time():
    html.write("<div class=currenttime>%s</div>" % time.strftime("%H:%M:%S"))

sidebar_snapins["time"] = {
    "title" : "Current time",
    "refresh" : 1,
    "render" : render_current_time
}
