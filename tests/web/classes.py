#!/usr/bin/python
# call using
# > py.test -s -k test_html_generator.py

# enable imports from web directory
from testlib import cmk_path
import sys
sys.path.insert(0, "%s/web/htdocs" % cmk_path())

# external imports
import re

# internal imports
from htmllib import html
from htmllib import HTMLGenerator, HTMLCheck_MK

# Hack to fix localized calls
try:
    _
except:
    _ = lambda x: x

#   .--Deprecated Renderer-------------------------------------------------.
#   |          ____                                _           _           |
#   |         |  _ \  ___ _ __  _ __ ___  ___ __ _| |_ ___  __| |          |
#   |         | | | |/ _ \ '_ \| '__/ _ \/ __/ _` | __/ _ \/ _` |          |
#   |         | |_| |  __/ |_) | | |  __/ (_| (_| | ||  __/ (_| |          |
#   |         |____/ \___| .__/|_|  \___|\___\__,_|\__\___|\__,_|          |
#   |                    |_|                                               |
#   |              ____                _                                   |
#   |             |  _ \ ___ _ __   __| | ___ _ __ ___ _ __                |
#   |             | |_) / _ \ '_ \ / _` |/ _ \ '__/ _ \ '__|               |
#   |             |  _ <  __/ | | | (_| |  __/ | |  __/ |                  |
#   |             |_| \_\___|_| |_|\__,_|\___|_|  \___|_|                  |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Rendering methods which are to be replaced by the new HTMLGenerator. |
#   | It borrows its write functionality from the OutputFunnel.            |
#   '----------------------------------------------------------------------'


class DeprecatedRenderer(object):


    def __init__(self):
        super(DeprecatedRenderer, self).__init__()

        self.header_sent = False
        self._default_stylesheets = ['check_mk', 'graphs']
        self._default_javascripts = [ "checkmk", "graphs" ]
        self.browser_reload = 0
        self.browser_redirect = ''
        self.render_headfoot = True
        self.output_format = "html"

        self.enable_debug = False
        self.screenshotmode = False
        self.help_visible = False

        self.body_classes = ['main']
        self.link_target = None


    def header(self, title='', **args):
        if self.output_format == "html":
            if not self.header_sent:
                self.body_start(title, **args)
                self.header_sent = True
                if self.render_headfoot:
                    self.top_heading(title)


    def body_start(self, title='', **args):
        self.html_head(title, **args)
        self.write('<body class="%s">' % self._get_body_css_classes())


    def _get_body_css_classes(self):
        body_classes = self.body_classes
        if self.screenshotmode:
            body_classes.append("screenshotmode")
        return " ".join(body_classes)


    #
    # Helper functions to be used by snapins
    #
    def url_prefix(self):
        raise NotImplementedError()


    def render_link(self, text, url, target="main", onclick = None):
        # Convert relative links into absolute links. We have three kinds
        # of possible links and we change only [3]
        # [1] protocol://hostname/url/link.py
        # [2] /absolute/link.py
        # [3] relative.py
        if not (":" in url[:10]) and not url.startswith("javascript") and url[0] != '/':
            url = self.url_prefix() + "check_mk/" + url
        onclick = onclick and (' onclick="%s"' % self.attrencode(onclick)) or ''
        return '<a onfocus="if (this.blur) this.blur();" target="%s" ' \
               'class=link href="%s"%s>%s</a>' % \
                (self.attrencode(target or ""), self.attrencode(url), onclick, self.attrencode(text))


    def link(self, text, url, target="main", onclick = None):
        self.write(self.render_link(text, url, target=target, onclick=onclick))


    def simplelink(self, text, url, target="main"):
        self.write(self.render_link(text, url, target) + "<br>\n")


    def bulletlink(self, text, url, target="main", onclick = None):
        self.write("<li class=sidebar>" + self.render_link(text, url, target, onclick) + "</li>\n")


    def iconlink(self, text, url, icon):
        linktext = self.render_icon(icon, cssclass="inline") \
                   + self.attrencode(text)
        self.write('<a target=main class="iconlink link" href="%s">%s</a><br>' % \
                (self.attrencode(url), linktext))


    def begin_footnote_links(self):
        self.write('<div class="footnotelink">')


    def end_footnote_links(self):
        self.write('</div>')


    def footnotelinks(self, links):
        self.begin_footnote_links()
        for text, target in links:
            self.write(self.render_link(text, target))
        self.end_footnote_links()


    def nagioscgilink(self, text, target):
        self.write("<li class=sidebar><a target=\"main\" class=link href=\"%snagios/cgi-bin/%s\">%s</a></li>" % \
                (self.url_prefix(), target, self.attrencode(text)))


    def add_custom_style_sheet(self):
        raise NotImplementedError()


    def css_filename_for_browser(self, css):
        raise NotImplementedError()


    def javascript_filename_for_browser(self, jsname):
        raise NotImplementedError()


    def html_foot(self):
        self.write("</html>\n")


    def top_heading(self, title):
        raise NotImplementedError()


    def top_heading_left(self, title):
        self.write('<table class=\"header\"><tr><td width="*" class=\"heading\">')
        self.write('<a href="#" onfocus="if (this.blur) this.blur();" '
                   'onclick="this.innerHTML=\'%s\'; document.location.reload();">%s</a></td>' %
                   (_("Reloading..."), self.attrencode(title)))


    def top_heading_right(self):
        cssclass = self.help_visible and "active" or "passive"
        self.icon_button(None, _("Toggle context help texts"), "help", id="helpbutton",
                         onclick="toggle_help()", style="display:none", ty="icon", cssclass=cssclass)

        self.write("%s</td></tr></table>" %
                   _("<a class=head_logo href=\"http://mathias-kettner.de\">"
                     "<img src=\"images/logo_cmk_small.png\"/></a>"))
        self.write("<hr class=\"header\">\n")
        if self.enable_debug:
            self._dump_get_vars()


    #
    # HTML form rendering
    #


    def detect_icon_path(self, icon_name):
        raise NotImplementedError()


    def icon(self, help, icon, **kwargs):

        # TODO:
        title = help

        self.write(self.render_icon(icon, title, **kwargs))


    def empty_icon(self):
        self.write(self.render_icon("images/trans.png"))


    def render_icon(self, icon_name, help="", middle=True, id=None, cssclass=None):

        #TODO
        title = help
        id_ = id

        align = middle and ' align=absmiddle' or ''
        title = title and ' title="%s"' % self.attrencode(title) or ""
        id_ = id_ and ' id="%s"' % id_ or ''
        cssclass = cssclass and (" " + cssclass) or ""

        if "/" in icon_name:
            icon_path = icon_name
        else:
            icon_path = self.detect_icon_path(icon_name)

        return '<img src="%s" class="icon%s"%s%s%s />' % (icon_path, cssclass, align, title, id_)



    def render_icon_button(self, url, help, icon, id="", onclick="",
                           style="", target="", cssclass="", ty="button"):

        # TODO:
        title = help
        id_ = id

        if id_:
            id_ = "id='%s' " % id_

        if onclick:
            onclick = 'onclick="%s" ' % onclick
            url = "javascript:void(0)"

        if style:
            style = 'style="%s" ' % style

        if target:
            target = 'target="%s" ' % target
        else:
            target = ""

        if cssclass:
            cssclass = 'class="%s" ' % cssclass

        # TODO: Can we clean this up and move all button_*.png to internal_icons/*.png?
        if ty == "button":
            icon = "images/button_" + icon + ".png"

        return '<a %s%s%s%s%sonfocus="if (this.blur) this.blur();" href="%s" title="%s">%s</a>' % \
                 (id_, onclick, style, target, cssclass, url, self.attrencode(title),
                  self.render_icon(icon, cssclass="iconbutton"))


    def icon_button(self, *args, **kwargs):
        self.write(self.render_icon_button(*args, **kwargs))



    # Only strip off some tags. We allow some simple tags like
    # <b>, <tt>, <i> to be part of the string. This is useful
    # for messages where we still want to have formating options.
    def permissive_attrencode(self, obj):
        msg = self.attrencode(obj)
        msg = re.sub(r'&lt;(/?)(h2|b|tt|i|br(?: /)?|pre|a|sup|p|li|ul|ol)&gt;', r'<\1\2>', msg)
        # Also repair link definitions
        return re.sub(r'&lt;a href=&quot;(.*?)&quot;&gt;', r'<a href="\1">', msg)


    # Encode HTML attributes: replace " with &quot;, also replace
    # < and >. This code is slow. Works on str and unicode without
    # changing the type. Also works on things that can be converted
    # with %s.
    def attrencode(self, value):
        ty = type(value)
        if ty == int:
            return str(value)
        elif isinstance(value, HTML):
            return value.value # This is HTML code which must not be escaped
        elif ty not in [str, unicode]: # also possible: type Exception!
            value = "%s" % value # Note: this allows Unicode. value might not have type str now

        return value.replace("&", "&amp;")\
                    .replace('"', "&quot;")\
                    .replace("<", "&lt;")\
                    .replace(">", "&gt;")


    #
    # HTML low level rendering and writing functions. Only put most basic function in
    # this section which are really creating only some simple tags.
    #

    def heading(self, text):
        self.write("<h2>%s</h2>\n" % text)


    def rule(self):
        self.write("<hr/>")


    def p(self, content):
        self.write("<p>%s</p>" % self.attrencode(content))


    def render_javascript(self, code):
        return "<script language=\"javascript\">\n%s\n</script>\n" % code


    def javascript(self, code):
        self.write(self.render_javascript(code))


    def javascript_file(self, name):
        self.write('<script type="text/javascript" src="js/%s.js">\n</script>\n' % name)


    def play_sound(self, url):
        self.write("<audio src=\"%s\" autoplay>\n" % self.attrencode(url))


    #
    # HTML - All the common and more complex HTML rendering methods
    #


    def default_html_headers(self):
        self.write('<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />\n')
        self.write('<meta http-equiv="X-UA-Compatible" content="IE=edge" />\n')
        self.write('<link rel="shortcut icon" href="images/favicon.ico" type="image/ico">\n')


    def html_head(self, title, javascripts = [], stylesheets = ["pages"], force=False):
        if not self.header_sent or force:
            self.write('<!DOCTYPE HTML>\n'
                       '<html><head>\n')

            self.default_html_headers()
            self.write('<title>')
            self.write(self.attrencode(title))
            #self.guitest_record_output("page_title", title)
            self.write('</title>\n')

            # If the variable _link_target is set, then all links in this page
            # should be targetted to the HTML frame named by _link_target. This
            # is e.g. useful in the dash-board
            if self.link_target:
                self.write('<base target="%s">\n' % self.attrencode(self.link_target))

            # Load all specified style sheets and all user style sheets in htdocs/css
            for css in self._default_stylesheets + stylesheets + [ 'ie' ]:
                fname = self.css_filename_for_browser(css)
                if fname == None:
                    continue

                if css == 'ie':
                    self.write('<!--[if IE]>\n')
                self.write('<link rel="stylesheet" type="text/css" href="%s" />\n' % fname)
                if css == 'ie':
                    self.write('<![endif]-->\n')

            self.add_custom_style_sheet()

            for js in self._default_javascripts + javascripts:
                filename_for_browser = self.javascript_filename_for_browser(js)
                if filename_for_browser:
                    self.javascript_file(filename_for_browser)

            if self.browser_reload != 0:
                if self.browser_redirect != '':
                    self.javascript('set_reload(%s, \'%s\')' % (self.browser_reload, self.browser_redirect))
                else:
                    self.javascript('set_reload(%s)' % (self.browser_reload))

            self.write("</head>\n")
            self.header_sent = True


#
# A Class which can be used to simulate HTML generation in varios tests in tests/web/
class HTMLTester(object):

    def __init__(self):
        super(HTMLTester, self).__init__()
        self.plugged_text = ''


    def write(self, text):
        self.plugged_text += "%s" % text


    def plug(self):
        self.plugged_text = ''


    def drain(self):
            t = self.plugged_text
            self.plugged_text = ''
            return t


class GeneratorTester(HTMLTester, HTMLGenerator):
    def __init__(self):
        super(GeneratorTester, self).__init__()
        HTMLTester.__init__(self)
        HTMLGenerator.__init__(self)


class HTMLCheck_MKTester(HTMLTester, HTMLCheck_MK):

    def __init__(self):
        super(HTMLCheck_MKTester, self).__init__()


    def add_custom_style_sheet(self):
        #raise NotImplementedError()
        pass


    def css_filename_for_browser(self, css):
        #raise NotImplementedError()
        return "file/name/css_%s" % css


    def javascript_filename_for_browser(self, jsname):
        #raise NotImplementedError()
        return "file/name/js_%s" % jsname 


    def top_heading(self, title):
        self.top_heading_left(title)
        self.top_heading_right()


    def detect_icon_path(self, icon_name):
        return "test/%s.jpg" % icon_name


    def url_prefix(self):
        return "OMD"


class HTMLOrigTester(HTMLTester, DeprecatedRenderer):


    def add_custom_style_sheet(self):
        #raise NotImplementedError()
        pass


    def css_filename_for_browser(self, css):
        #raise NotImplementedError()
        return "file/name/css_%s" % css


    def javascript_filename_for_browser(self, jsname):
        #raise NotImplementedError()
        return "file/name/js_%s" % jsname 


    def top_heading(self, title):
        self.top_heading_left(title)
        self.top_heading_right()


    def detect_icon_path(self, icon_name):
        return "test/%s.jpg" % icon_name


    def url_prefix(self):
        return "OMD"


