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

import config, defaults, livestatus, htmllib, views, pprint, os, copy
from lib import *

# Constants to be used in snapins
snapin_width = 230


# Datastructures and functions needed before plugins can be loaded
loaded_with_language = False
sidebar_snapins = {}

def load_plugins():
    global loaded_with_language
    if loaded_with_language == current_language:
        return
    loaded_with_language = current_language

    # Load all snapins
    global sidebar_snapins
    sidebar_snapins = {}
    load_web_plugins("sidebar", globals())

    # Declare permissions: each snapin creates one permission
    config.declare_permission_section("sidesnap", _("Sidebar snapins"))
    for name, snapin in sidebar_snapins.items():
        config.declare_permission("sidesnap.%s" % name,
            snapin["title"],
            snapin["description"],
            snapin["allowed"])

# Helper functions to be used by snapins
def link(text, target, frame="main"):
    # Convert relative links into absolute links. We have three kinds
    # of possible links and we change only [3]
    # [1] protocol://hostname/url/link.py
    # [2] /absolute/link.py
    # [3] relative.py
    if not (":" in target[:10]) and target[0] != '/':
        target = defaults.url_prefix + "check_mk/" + target
    return '<a onfocus="if (this.blur) this.blur();" target="%s" ' \
           'class=link href="%s">%s</a>' % (frame, target, htmllib.attrencode(text))

def simplelink(text, target, frame="main"):
    html.write(link(text, target, frame) + "<br>\n")

def bulletlink(text, target, frame="main"):
    html.write("<li class=sidebar>" + link(text, target, frame) + "</li>\n")

def iconlink(text, target, icon):
    linktext = '<img class=iconlink src="images/icon_%s.png">%s' % \
         ( icon, text )
    html.write('<a target=main class="iconlink link" href="%s">%s</a><br>' % \
            (target, linktext))

def footnotelinks(links):
    html.write("<div class=footnotelink>")
    for text, target in links:
        html.write(link(text, target))
    html.write("</div>\n")

def iconbutton(what, url, target="side", handler="", name="", css_class = ""):
    if target == "side":
        onclick = "onclick=\"get_url('%s', %s, '%s')\"" % \
                   (url, handler, name)
        href = "#"
        tg = ""
    else:
        onclick = ""
        href = "%scheck_mk/%s" % (defaults.url_prefix, url)
        tg = "target=%s" % target
    css_class = css_class and " " + css_class or ""
    html.write("<a href=\"%s\" %s %s><img class=\"iconbutton%s\" onmouseover=\"hilite_icon(this, 1)\" onmouseout=\"hilite_icon(this, 0)\" align=absmiddle src=\"%scheck_mk/images/button_%s_lo.png\"></a>\n " % (href, onclick, tg, css_class, defaults.url_prefix, what))

def nagioscgilink(text, target):
    html.write("<li class=sidebar><a target=\"main\" class=link href=\"%snagios/cgi-bin/%s\">%s</a></li>" % \
            (defaults.url_prefix, target, htmllib.attrencode(text)))

def heading(text):
    html.write("<h3>%s</h3>\n" % htmllib.attrencode(text))

def load_user_config():
    path = config.user_confdir + "/sidebar.mk"
    try:
        user_config = eval(file(path).read())
    except:
        user_config = config.sidebar

    # Remove entries the user is not allowed for or which have state "off" (from legacy version)
    return [ entry for entry in user_config if entry[1] != "off" and config.may("sidesnap." + entry[0])]

def save_user_config(user_config):
    if config.may("configure_sidebar"):
        config.save_user_file("sidebar", user_config)

def sidebar_head():
    html.write('<div id="side_header">'
               '<a title="%s" target="main" href="%s">'
               '<div id="side_version">%s</div>'
               '</a>'
               '</div>\n' % (_("Go to main overview"), config.start_url, defaults.check_mk_version))

def sidebar_foot():
    html.write('<div id="side_footer">')
    if config.may("configure_sidebar"):
        html.icon_button("sidebar_add_snapin.py", _("Add snapin to the sidebar"), "sidebar_addsnapin", 
                         target="main")
    if config.may("edit_profile") or config.may("change_password"):
        html.icon_button("user_profile.py", _("Edit your personal settings, change your password"), "sidebar_settings",
                         target="main")
        # html.write('<li><a class=profile target="main" href="user_profile.py" title="%s"></a></li>' % _('Edit user profile'))
    if config.may("logout"):
        html.icon_button("logout.py", _("Log out"), "sidebar_logout", target="_top")
        # html.write('<li><a class=logout target="_top" href="logout.py" title="%s"></a></li>' % _('Logout'))
    html.write('</ul>')
    html.write("<div class=copyright>%s</div>\n" % _("&copy; <a target=\"_blank\" href=\"http://mathias-kettner.de\">Mathias Kettner</a>"))
    html.write('</div>')

# Standalone sidebar
def page_side():
    if not config.may("see_sidebar"):
        return
    html.html_head(_("Check_MK Sidebar"), javascripts=["sidebar"], stylesheets=["sidebar", "status"])
    html.write('<body class="side" onload="initScrollPos(); setSidebarHeight();" onunload="storeScrollPos()">\n')
    html.write('<div id="check_mk_sidebar">\n')

    views.load_views()
    sidebar_head()
    user_config = load_user_config()
    refresh_snapins = []
    restart_snapins = []

    html.write('<div id="side_content">')
    for name, state in user_config:
        if not name in sidebar_snapins or not config.may("sidesnap." + name):
            continue
        refresh_url  = render_snapin(name, state)
        refresh_time = sidebar_snapins.get(name).get("refresh", 0)
        if refresh_time > 0:
            refresh_snapins.append([name, refresh_time, refresh_url])

        restart = sidebar_snapins.get(name, {}).get('restart', False)
        if restart:
            restart_snapins.append(name)
    html.write('</div>')
    sidebar_foot()
    html.write('</div>')

    html.write("<script language=\"javascript\">\n")
    if restart_snapins:
        html.write("sidebar_restart_time = %s\n" % time.time())
    html.write("registerEdgeListeners();\n")
    html.write("setSidebarHeight();\n")
    html.write("refresh_snapins = %r;\n" % refresh_snapins)
    html.write("restart_snapins = %r;\n" % restart_snapins)
    html.write("sidebar_scheduler();\n")
    html.write("window.onresize = function() { setSidebarHeight(); }\n")
    # html.write("window.onload = function() { setSidebarHeight(); }\n")
    html.write("</script>\n")

    # html.write("</div>\n")
    html.write("</body>\n</html>")

def render_snapin(name, state):
    snapin = sidebar_snapins.get(name)
    styles = snapin.get("styles")
    if styles:
        html.write("<style>\n%s\n</style>\n" % styles)

    html.write("<div id=\"snapin_container_%s\" class=snapin>\n" % name)
    if state == "closed":
        style = ' style="display:none"'
        headclass = "closed"
        minimaxi = "maxi"
    else:
        style = ""
        headclass = "open"
        minimaxi = "mini"
    toggle_url = "sidebar_openclose.py?name=%s&state=" % name

    html.write('<div class="head %s" ' % headclass)

    # If the user may modify the sidebar then add code for dragging the snapin
    if config.may("configure_sidebar"):
        html.write("onmouseover=\"document.body.style.cursor='move';\" "
                   "onmouseout=\"document.body.style.cursor='';\" "
                   "onmousedown=\"snapinStartDrag(event)\" onmouseup=\"snapinStopDrag(event)\">")
    else:
        html.write(">")


    # Icon for mini/maximizing, does not need permission
    html.write('<div class="minisnapin">')
    iconbutton(minimaxi + "snapin", None,
               "side", "toggle_sidebar_snapin(this, '%s')" % toggle_url, 'snapin_'+name)
    html.write('</div>')

    if config.may("configure_sidebar"):
        # Button for closing (removing) a snapin
        html.write('<div class="closesnapin">')
        iconbutton("closesnapin", "sidebar_openclose.py?name=%s&state=off" % name, 
                   "side", "removeSnapin", 'snapin_'+name)
        html.write('</div>')

    # The heading. A click on the heading mini/maximizes the snapin
    html.write("<b class=heading onclick=\"toggle_sidebar_snapin(this,'%s')\" "
               "onmouseover=\"this.style.cursor='pointer'\" "
               "onmouseout=\"this.style.cursor='auto'\">%s</b>" % (toggle_url, snapin["title"]))

    # End of header
    html.write("</div>")

    # Now comes the content
    html.write("<div id=\"snapin_%s\" class=content%s>\n" % (name, style))
    refresh_url = ''
    try:
        url = snapin["render"]()
        # Fetch the contents from an external URL. Don't render it on our own.
        if not url is None:
            refresh_url = url
            html.write('<script>get_url("%s", updateContents, "snapin_%s")</script>' % (refresh_url, name))
    except Exception, e:
        snapin_exception(e)
    html.write('</div><div class="foot"%s></div>\n' % style)
    html.write('</div>')
    return refresh_url

def snapin_exception(e):
    if config.debug:
        raise
    else:
        html.write("<div class=snapinexception>\n"
                "<h2>%s</h2>\n"
                "<p>%s</p></div>" % (_('Error'), e))

def ajax_nagios_restarted():
    # Tells the requestor the "since" time or the program start time
    # of the newest running instance depending on which is newer
    since = float(html.var('since', 0))
    newest = since
    for site in html.site_status.values():
        prog_start = site.get("program_start", 0)
        if prog_start > newest:
            newest = prog_start
    html.write(str(newest))

def ajax_openclose():
    config = load_user_config()
    new_config = []
    for name, usage in config:
        if html.var("name") == name:
            usage = html.var("state")
        if usage != "off":
            new_config.append((name, usage))
    save_user_config(new_config)

def ajax_snapin():
    snapname = html.var("name")
    if not config.may("sidesnap." + snapname):
        return
    snapin = sidebar_snapins.get(snapname)
    try:
        snapin["render"]()
    except Exception, e:
        snapin_exception(e)

def move_snapin():
    if not config.may("configure_sidebar"):
        return

    snapname_to_move = html.var("name")
    beforename = html.var("before")

    snapin_config = load_user_config()

    # Get current state of snaping being moved (open, closed)
    snap_to_move = None
    for name, state in snapin_config:
        if name == snapname_to_move:
            snap_to_move = name, state
    if not snap_to_move:
        return # snaping being moved not visible. Cannot be.

    # Build new config by removing snaping at current position
    # and add before "beforename" or as last if beforename is not set
    new_config = []
    for name, state in snapin_config:
        if name == snapname_to_move:
            continue # remove at this position
        elif name == beforename:
            new_config.append(snap_to_move)
        new_config.append( (name, state) )
    if not beforename: # insert as last
        new_config.append(snap_to_move)
    save_user_config(new_config)

def page_add_snapin():
    if not config.may("configure_sidebar"):
        raise MKGeneralException(_("You are not allowed to change the sidebar."))

    html.header(_("Available snapins"), stylesheets=["pages", "sidebar", "status"])
    used_snapins = [name for (name, state) in load_user_config()]

    addname = html.var("name")
    if addname in sidebar_snapins and addname not in used_snapins and html.check_transaction():
        user_config = load_user_config() + [(addname, "open")]
        save_user_config(user_config)
        used_snapins = [name for (name, state) in load_user_config()]
        html.reload_sidebar()

    names = sidebar_snapins.keys()
    names.sort()
    html.write('<div class="add_snapin">\n')
    for name in names:
        if name in used_snapins:
            continue
        if not config.may("sidesnap." + name):
            continue # not allowed for this user

        snapin = sidebar_snapins[name]
        title = snapin["title"]
        description = snapin.get("description", "")
        transid = html.fresh_transid()
        url = 'sidebar_add_snapin.py?name=%s&_transid=%s&pos=top' % (name, transid)
        html.write('<div class=snapinadder '
                   'onmouseover="this.style.cursor=\'pointer\';" '
                   'onmousedown="window.location.href=\'%s\'; return false;">' % url)

        html.write("<div class=snapin_preview>")
        html.write("<div class=clickshield></div>")
        render_snapin(name, "open")
        html.write("</div>")
        html.write("<div class=description>%s</div>" % (description))

        html.write("</div>")

    html.write("</div>\n")
    html.footer()

load_plugins()
