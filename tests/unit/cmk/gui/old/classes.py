#!/usr/bin/python
# call using
# > py.test -s -k test_html_generator.py

from werkzeug.test import create_environ
from werkzeug.wrappers import Response

from cmk.gui.http import Request
import cmk.gui.htmllib as htmllib

# A Class which can be used to simulate HTML generation in varios tests in tests/web/
class HTMLTester(htmllib.html):
    def __init__(self):
        environ = dict(create_environ(), REQUEST_URI='')
        super(HTMLTester, self).__init__(Request(environ), Response())


    def context_button_test(obj, title, url, icon=None, hot=False, id_=None, bestof=None, hover_title=None, id_in_best=False):
        obj.begin_context_buttons()
        obj.context_button(title, url, icon=icon, hot=hot, id_=id_, bestof=bestof, hover_title=hover_title)
        if id_in_best:
            obj.context_button_hidden = True
        obj.end_context_buttons()


    def unittesting_tester(self, arg1, arg2, **args):
        self.write("<html>")
        self.html_is_open = True
        if not self.header_sent:
            self.write("<header>")
            self.write("</header>")
            self.header_sent = True
        self.write("<body class=\"%s\">" % " ".join(self.body_classes))
        self.write("<div class=\"%s\">Content</div>" % " ".join(["content", arg1, arg2]))
        self.write("</body>")
        self.write("</html>")
        return True


    # only for test purposes
    def radiobuttons(self, **args):
        horizontal = args.pop("horizontal", False)
        values = args.pop("values", [])
        varnames = args.pop("varnames", [])
        self.begin_radio_group(horizontal)
        for n, v in zip(varnames, values):
            args["varname"] = n
            args["value"] = v
            self.radiobutton(**args)
        self.end_radio_group()


    def set_focus(self, varname):
        self.focus_object = (self.form_name, varname)


    # Needed if input elements are put into forms without the helper
    # functions of us. TODO: Should really be removed and cleaned up!
    def add_form_var(self, varname):
        self.form_vars.append(varname)


    def final_javascript(self, code):
        self.final_javascript_code += code + "\n"


    def _css_filename_for_browser(self, css):
        return "file/name/css_%s" % css


    def top_heading(self, title):
        self.top_heading_left(title)
        self.top_heading_right()


    def url_prefix(self):
        return "OMD"


    def get_button_counts(self):
        return {"1": 1, "2": 2, "3": 3,}


    def javascript_filename_for_browser(self, jsname):
        #raise NotImplementedError()
        return "js/file/name/js_%s.js" % jsname
