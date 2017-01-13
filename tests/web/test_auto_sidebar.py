
#!/usr/bin/python
# call using
# > py.test -s -k test_html_generator.py

# enable imports from web directory
from testlib import cmk_path
import sys
sys.path.insert(0, "%s/web/htdocs" % cmk_path())

# external imports
import re
from bs4 import BeautifulSoup as bs

# internal imports
from classes import HTMLOrigTester, HTMLCheck_MKTester
from tools import compare_html, gentest, compare_and_empty

_ = lambda x: x

title = "title"
key = "key"
description = "description"
name = "name"
vp = "vp"
varprefix = "varprefix"
prefix = "prefix"
css = "css"
cls = "cls"
disp = "disp"
sel = "selected"
div_id = "div1"

_vertical = "vertical"
_delete_style = "filter"
_label = "label"
_empty_text = "empty text"
_no_elements_text = _empty_text
_columns = 5
_size = 10

select_func = "selector"
unselect_func = "unselector"
active_category = "active_category"
category_name = "active_category"
category_alias = "active_alias"

div_is_open = True
visible = True
oneline = True

mod = 2
nr = 1
indent = 10
display_off = "none"
display_on = "row"

url = "www.url.de"
toggle_url = url
refresh_url = url

classes = ["cls1", "cls2"]
#onclick = "onclick_code('<lol>');"
onclick = "onclick_code('lol');"
title   = "Title"
thclass = "th"
tdclass = "th"
content = "<tag> content </tag>"
tdattrs= "class='tdclass'"
is_open = True
option  = "option"
icon    = "icon"
value   = "Testvalue"
view    = {"name": "viewname"}
choices = ["c1", "c2"]
styles  = ["s1", "s2"]
headclass= "headc"
hidden  = True
id      = "id"
e       = "error"
query   = "Hallo Welt!"
version = "Version"
num_unacknowledged_werks = 10
msg = {"id": "4", "text": "Message"}

def test_0():
    old = HTMLOrigTester()
    new = HTMLCheck_MKTester()
    old.plug()
    new.plug()


    old.write('<div id="side_header">')
    old.write('<div id="side_fold"></div>')
    old.write('<a title="%s" target="main" href="%s">' %
    (_("Go to main overview"),
    old.attrencode("start_url" or url)))
    old.write('<img id="side_bg" src="images/sidebar_top.png">')
    old.write('<div id="side_version">'
    '<a href="version.py" target="main" title=\"%s\">%s<br>%s' %
    (_("Open release notes"), title, version))
    old.write("<span title=\"%s\" class=\"unack_werks\">%d</span>" %
    (_("%d unacknowledged incompatible werks") % num_unacknowledged_werks, num_unacknowledged_werks))
    old.write('</a></div>')
    old.write('</a></div>\n')
    old.write('<div class="popup_msg" id="message-%s">' % msg['id'])
    old.write('<a href="javascript:void(0)" class="close" onclick="message_close(\'%s\')">x</a>' % msg['id'])
    old.write(old.attrencode(msg['text']).replace('\n', '<br />\n'))
    old.write('</div>\n')
    new.open_div(id_="side_header")
    new.div('', id_="side_fold")
    new.open_a(href="start_url" or url,
    target="main", title=_("Go to main overview"))
    new.img(src="images/sidebar_top.png", id_="side_bg")
    new.open_div(id_="side_version")
    new.open_a(href="version.py", target="main", title=_("Open release notes"))
    new.write(title)
    new.br()
    new.write(version)
    new.span(num_unacknowledged_werks, class_="unack_werks",
    title=_("%d unacknowledged incompatible werks") % num_unacknowledged_werks)
    new.close_a()
    new.close_div()
    new.close_a()
    new.close_div()
    new.open_div(id_="message-%s" % msg['id'], class_=["popup_msg"])
    new.a("x", href="javascript:void(0)", class_=["close"], onclick="message_close(\'%s\')" % msg['id'])
    new.write_text(msg['text'].replace('\n', '<br/>\n'))
    new.close_div()



    compare_and_empty(old, new)


def test_1():
    old = HTMLOrigTester()
    new = HTMLCheck_MKTester()
    old.plug()
    new.plug()


    old.write('<div id="side_footer">')
    new.open_div(id_="side_footer")



    compare_and_empty(old, new)


def test_2():
    old = HTMLOrigTester()
    new = HTMLCheck_MKTester()
    old.plug()
    new.plug()


    old.write('<div id="messages" style="display:none;">')
    old.write('</div>')
    old.write("<div class=copyright>%s</div>\n" %
    _("&copy; <a target=\"_blank\" href=\"https://mathias-kettner.com\">Mathias Kettner</a>"))
    old.write('</div>')
    new.open_div(style="display:none;", id_="messages")
    new.close_div()
    new.open_div(class_=["copyright"])
    new.write(_("&copy; " + new.render_a("Mathias Kettner", target="_blank", href="https://mathias-kettner.com")))
    new.close_div()
    new.close_div()

    compare_and_empty(old, new)

    old.write('<div id="check_mk_sidebar">\n')
    new.open_div(id_="check_mk_sidebar")
    scrolling = ' class=scroll'
    old.write('<div id="side_content"%s>' % scrolling)
    new.open_div(class_="scroll", id_="side_content")
    old.write('</div>')
    old.write('</div>')
    new.close_div()
    new.close_div()


    print ""
    print (old.plugged_text)
    print (new.plugged_text)


    compare_and_empty(old, new)


def test_6():
    old = HTMLOrigTester()
    new = HTMLCheck_MKTester()
    old.plug()
    new.plug()


    old.write("<style>\n%s\n</style>\n" % styles)
    old.write("<div id=\"snapin_container_%s\" class=snapin>\n" % name)
    style = ' style="display:none"'
    old.write('<div class="head %s" ' % headclass)
    old.write("onmouseover=\"document.body.style.cursor='move';\" "
    "onmouseout=\"document.body.style.cursor='';\" "
    "onmousedown=\"snapinStartDrag(event)\" onmouseup=\"snapinStopDrag(event)\">")
    old.write(">")
    old.write('<div class="minisnapin">')
    old.write('</div>')
    old.write('<div class="closesnapin">')
    old.write('</div>')
    toggle_actions = " onclick=\"toggle_sidebar_snapin(this,'%s')\"" \
    " onmouseover=\"this.style.cursor='pointer'\"" \
    " onmouseout=\"this.style.cursor='auto'\"" % toggle_url
    old.write("<b class=heading%s>%s</b>" % (toggle_actions, title))
    old.write("</div>")
    old.write("<div id=\"snapin_%s\" class=content%s>\n" % (name, style))
    old.write('<script type="text/javascript">get_url("%s", updateContents, "snapin_%s")</script>' % (refresh_url, name))
    old.write('</div>\n')
    old.write('</div>')
    old.write("<div class=snapinexception>\n"
    "<h2>%s</h2>\n"
    "<p>%s</p></div>" % (_('Error'), e))
    new.open_style()
    new.write(styles)
    new.close_style()
    new.open_div(id_="snapin_container_%s" % name, class_="snapin")
    style = None
    style = "display:none"
    head_actions = { "onmouseover" : "document.body.style.cursor='move';",
    "onmouseout " : "document.body.style.cursor='';",
    "onmousedown" : "snapinStartDrag(event)",
    "onmouseup"   : "snapinStopDrag(event)"}
    new.open_div(class_=["head", headclass], **head_actions)
    new.open_div(class_="minisnapin")
    new.close_div()
    new.open_div(class_="closesnapin")
    new.close_div()
    toggle_actions = {}
    toggle_actions = {"onclick"    : "toggle_sidebar_snapin(this,'%s')" % toggle_url,
    "onmouseover": "this.style.cursor='pointer'",
    "onmouseout" : "this.style.cursor='auto'"}
    new.b(title, class_=["heading"], **toggle_actions)
    new.close_div()
    new.open_div(class_="content", id_="snapin_%s" % name, style=style)
    new.javascript("get_url(\"%s\", updateContents, \"snapin_%s\")" % (refresh_url, name))
    new.close_div()
    new.close_div()
    new.open_div(class_=["snapinexception"])
    new.h2(_('Error'))
    new.p(e)
    new.close_div()



    compare_and_empty(old, new)


def test_7():
    old = HTMLOrigTester()
    new = HTMLCheck_MKTester()
    old.plug()
    new.plug()


    old.write('<div class="add_snapin">\n')
    new.open_div(class_=["add_snapin"])



    compare_and_empty(old, new)


def test_8():
    old = HTMLOrigTester()
    new = HTMLCheck_MKTester()
    old.plug()
    new.plug()


    old.write('<div class=snapinadder '
    'onmouseover="this.style.cursor=\'pointer\';" '
    'onmousedown="window.location.href=\'%s\'; return false;">' % url)
    old.write("<div class=snapin_preview>")
    old.write("<div class=clickshield></div>")
    old.write("</div>")
    old.write("<div class=description>%s</div>" % (description))
    old.write("</div>")
    old.write("</div>\n")
    new.open_div(class_="snapinadder",
    onmouseover="this.style.cursor=\'pointer\';",
    onmousedown="window.location.href=\'%s\'; return false;" % url)
    new.open_div(class_=["snapin_preview"])
    new.div('', class_=["clickshield"])
    new.close_div()
    new.div(description, class_=["description"])
    new.close_div()
    new.close_div()



    compare_and_empty(old, new)


def test_9():
    old = HTMLOrigTester()
    new = HTMLCheck_MKTester()
    old.plug()
    new.plug()



    compare_and_empty(old, new)

