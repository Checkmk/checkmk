#!/usr/bin/python
#encoding: utf-8

#import config, defaults, livestatus, htmllib, time, os, re, pprint, time, copy
#import weblib, traceback
from lib import *
import views
#from pagefunctions import *

def mobile_html_head(title, read_code):
    html.write("""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
 <head>
  <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>%s</title>
  <link rel="stylesheet" type="text/css" href="jquery/jquery.mobile-1.0.css">
  <link rel="stylesheet" type="text/css" href="mobile.css">
  <script type='text/javascript' src='jquery/jquery-1.6.4.min.js'></script>
  <script type='text/javascript' src='jquery/jquery.mobile-1.0.min.js'></script>
  <script type='text/javascript'>
      $(document).ready(function() { %s });
  </script>
  
</head>
<body class=mobile>
""" % (title, read_code))

def mobile_html_foot():
    html.write("</body></html>\n")

def jqm_page_header(id, title):
    html.write(
        '<div data-role="page" id="%s">\n'
        '<div data-role="header"><h1>%s</h1></div>\n'
        '<div data-role="content">\n'
        % (id, title))

def jqm_page_footer(content=""):
    html.write(
        '</div>'
        '<div data-role="footer"><h4>%s</h4></div>\n'
        '</div>\n' % content)

def jqm_page_content(title, items):
    jqm_page_header("c", title)
    html.write(
        '<ul data-role="listview" data-inset="true">\n')
    for id, title in items:
        html.write('<li><a href="#%s">%s</a></li>\n' %
                (id, title))
    html.write("</ul>Hier kommt noch Text\n")
    jqm_page_footer()

def jqm_page(id, title, foot, content):
    jqm_page_header(id, title)
    html.write('<div data-role="content">%s</div>\n' % content)
    jqm_page_footer(foot)

def page_index():
    mobile_html_head("Check_MK Mobile interface","")
    views.load_views()
    items = []
    for id, view in html.available_views.items():
        if view.get("mobile"):
            items.append((id, view["title"]))
    jqm_page_content(_("Check_MK Mobile"), items)
    mobile_html_foot()

def page_view():

