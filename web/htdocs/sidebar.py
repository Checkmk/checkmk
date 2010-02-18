#!/usr/bin/python

import check_mk, livestatus, htmllib, views, pprint, os
from lib import *

sidebar_snapins = {}

snapins_dir = check_mk.web_dir + "/plugins/sidebar"
for fn in os.listdir(snapins_dir):
    if fn.endswith(".py"):
	execfile(snapins_dir + "/" + fn)

# Helper functions to be used by snapins
def link(text, target):
    if not target.startswith("http:"):
	target = check_mk.checkmk_web_uri + "/" + target 
    return "<a target=\"main\" class=link href=\"%s\">%s</a>" % (target, htmllib.attrencode(text))

def bulletlink(text, target):
    html.write("<li class=sidebar>" + link(text, target) + "</li>\n")

def nagioscgilink(text, target):
    html.write("<li class=sidebar><a target=\"main\" class=link href=\"%s/%s\">%s</a></li>" % \
	    (check_mk.nagios_cgi_url, target, htmllib.attrencode(text)))

def heading(text):
    html.write("<h3>%s</h3>\n" % htmllib.attrencode(text))

def load_user_config():
    user = html.req.user
    path = check_mk.multisite_config_dir + "/" + user + "/sidebar.mk"
    try:
	config = eval(file(path).read())
    except:
	config = check_mk.multiadmin_sidebar

    # Now make sure that all snapins are listed in the config
    # even if turned off.
    for name in sidebar_snapins.keys():
	found = False
	for n, u in config:
	    if n == name: found = True
	if not found:
	    config.append((name, "off"))
    return config

def save_user_config(config):
    user = html.req.user
    dir = check_mk.multisite_config_dir + "/" + user
    try:
	os.makedirs(dir)
    except:
	pass

    try:
	path = dir + "/sidebar.mk"
	file(path, "w").write(pprint.pformat(config) + "\n")
    except Exception, e:
	raise MKConfigError("Cannot save user configuration to <tt>%s</tt>: %s" % (path, e))
    
def page_sidebar(h):
    global html
    html = h
    views.html = h
    views.load_views()
    html.write("<div class=header><table><tr>"
		"<td class=title><a target=\"main\" href=\"http://mathias-kettner.de/check_mk.html\">Check_MK</a></td>"
		"<td class=logo><a target=\"_blank\" href=\"http://mathias-kettner.de\"><img border=0 src=\"%s/MK-mini-black.gif\"></a></td>"
		"</tr></table></div>\n" % \
	    check_mk.checkmk_web_uri)
    config = load_user_config()
    refresh_snapins = []
    for name, state in config:
	if not name in sidebar_snapins:
	   continue
	if state in [ "open", "closed" ]:
	   render_snapin(name, state)
	   refresh_time = sidebar_snapins.get(name).get("refresh", 0)
	   if refresh_time > 0:
	       refresh_snapins.append([name, refresh_time])
    html.write("<div class=footnote><a target=\"main\" href=\"%s/sidebar_config.py\">Configure sidebar</a></div>\n" % \
	    check_mk.checkmk_web_uri)
    html.write("<script language=\"javascript\">\n")
    html.write("var refresh_snapins = %r;\n" % refresh_snapins) 
    html.write("sidebar_scheduler();\n")
    html.write("</script>\n")

def render_snapin(name, state):
    snapin = sidebar_snapins.get(name)
    styles = snapin.get("styles")
    if styles: 
	html.write("<style>\n%s\n</style>\n" % styles)

    html.write("<div class=section>\n")
    if state == "closed":
	style = ' style="display:none"'
    else:
	style = ""
    if snapin.get("hidetitle") != True:
	url = check_mk.checkmk_web_uri + "/sidebar_openclose.py?name=%s&state=" % name
	html.write("<h2 onclick=\"toggle_sidebar_snapin(this,'%s')\" onmouseover=\"this.style.cursor='pointer'\" "
		   "onmouseout=\"this.style.cursor='auto'\">%s</h2>\n" % (url, snapin["title"]))
    html.write("<div id=\"snapin_%s\" class=content%s>\n" % (name, style))
    snapin["render"]()
    html.write("</div></div>\n")

def ajax_openclose(h):
    global html
    html = h

    config = load_user_config()
    new_config = []
    for name, usage in config:
	if html.var("name") == name:
	    usage = html.var("state")	
	new_config.append((name, usage))
    save_user_config(new_config)

def ajax_snapin(h):
    global html
    html = h
    snapin = sidebar_snapins.get(html.var("name"))
    if snapin:
        snapin["render"]()


def page_configure(h):
    global html
    html = h
    html.header("Configure Sidebar")

    config = load_user_config()
    changed = False

    if html.transaction_valid():
	# change states
	if html.var("_saved"):
	    new_config = []
	    n = 0
	    for name, usage in config:
		new_usage = html.var("snapin_%d" % n)
		if new_usage in ["off", "open", "closed"]:
		    usage = new_usage
		new_config.append((name, usage))
		n += 1
	    config = new_config
	    save_user_config(config)
	    changed = True

	# handle up and down
	n = 0
	for name, usage in config:
	    if html.var("snapin_up_%d" % n) == "UP": # Cannot be 0
		config = config[0:n-1] + [(name,usage)] + [config[n-1]] + config[n+1:]
		save_user_config(config)
		changed = True
		break
	    elif html.var("snapin_down_%d" % n) == "DOWN": # Cannot be last one
		config = config[0:n] + [config[n+1]] + [(name,usage)] + config[n+2:]
		save_user_config(config)
		changed = True
		break
	    n += 1
	
	# reload sidebar, if user changed something
	if changed:
	    html.javascript("parent.frames[0].location.reload();");


    html.begin_form("sidebarconfig")
    html.hidden_field("_saved", "yes")
    html.write("<p>Here you can configure, which snapins you want to see in your personal "
	    "sidebar and wether they are closed or opened at startup.</p>")
    html.write("<table class=sidebarconfig>\n"
	    "<tr><th>Snapin</th><th>Usage</th><th colspan=2>Move</th></tr>\n")

    n = 0
    for name, usage in config:
	if name not in sidebar_snapins: 
	    n += 1
	    continue
	snapin = sidebar_snapins[name]
	html.set_var("snapin_%d" % n, usage)
	html.write("<tr>\n")
	html.write("<td class=title>%s</td>\n" % snapin["title"])
	html.write("<td class=widget>")
	html.select("snapin_%d" % n, [("off", "off"), ("open", "open"), ("closed","closed")], None, "this.form.submit()")
	html.write("</td><td>")
	if n > 0:
	    html.button("snapin_up_%d" % n, "UP")
	html.write("</td><td>")
	if n < len(config) - 1:
	    html.button("snapin_down_%d" % n, "DOWN")
	html.write("</td></tr>\n")
	n += 1
    html.write("</table>\n")

    html.write("<p> In order "
	    "to integrate the Check_MK sidebar snapins into your sidebar, please "
	    "add the following to your Nagios' <tt>side.html</tt> or <tt>side.php</tt></p>\n")
    html.write("<pre>\n%s</pre>\n" % htmllib.attrencode('<div id="check_mk_sidebar"><script src="%s/sidebar.js"></script></div>' % check_mk.checkmk_web_uri))
    html.end_form()

    html.footer()
