#!/usr/bin/python
# call using
# > py.test -s -k test_html_generator.py

# external imports
import re
import json
import traceback

# internal imports
from htmllib import html, RequestHandler
from htmllib import HTMLGenerator, OutputFunnel
from class_deprecated_renderer import DeprecatedRenderer

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


class RequestHandlerTester(RequestHandler):


    def get_unicode_input(self, varname, deflt):
        return self.var(varname, deflt)


    # Nonrandom transid generator
    def fresh_transid(self):
        transid = "%d/%d" % (1, 32)
        self.new_transids.append(transid)
        return transid


    def load_transids(self, lock=False):
        return ["1" , "2", "3/4"]
    #    raise NotImplementedError()


    def save_transids(self, used_ids):
        pass
    #    raise NotImplementedError()


#.
# A Class which can be used to simulate HTML generation in varios tests in tests/web/
class HTMLTester(RequestHandlerTester):

    def __init__(self):
        super(HTMLTester, self).__init__()
        self.written_text = ""


    def lowlevel_write(self, text):
        self.written_text += "%s" % text


    def detect_themed_image_path(self, img_path):
        return img_path


    def context_button_test(obj, title, url, icon=None, hot=False, id_=None, bestof=None, hover_title=None, fkey=None, id_in_best=False):
        obj.begin_context_buttons()
        obj.context_button(title, url, icon=icon, hot=hot, id=id_, bestof=bestof, hover_title=hover_title, fkey=fkey)
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


    def add_custom_style_sheet(self):
        #raise NotImplementedError()
        pass


    def css_filename_for_browser(self, css):
        #raise NotImplementedError()
        return "file/name/css_%s" % css


    def top_heading(self, title):
        self.top_heading_left(title)
        self.top_heading_right()


    def detect_icon_path(self, icon_name):
        return "test/%s.jpg" % icon_name


    def url_prefix(self):
        return "OMD"


    def get_button_counts(self):
        return {"1": 1, "2": 2, "3": 3,}


class Refactored_htmlTester(HTMLTester, html):

    def javascript_filename_for_browser(self, jsname):
        #raise NotImplementedError()
        return "js/file/name/js_%s.js" % jsname 


class HTMLOrigTester(HTMLTester, DeprecatedRenderer):

    def javascript_filename_for_browser(self, jsname):
        #raise NotImplementedError()
        return "file/name/js_%s" % jsname


class TableTester(Refactored_htmlTester):

    written_text = ''
    tag_counter  = 0

    def __init__(self):
        super(TableTester, self).__init__()
        self.myfile = "testfile"

    def lowlevel_write(self, text):
        indent = 1
        if re.match(r'.*\.close_\w+[(][)]', '\n'.join(traceback.format_stack()), re.DOTALL):
            self.tag_counter -= 1 if self.tag_counter > 0 else 0
            self.written_text += " " * indent * self.tag_counter + text
        elif re.match(r'.*\.open_\w+[(]', '\n'.join(traceback.format_stack()), re.DOTALL):
            self.written_text += " " * indent * self.tag_counter + text
            self.tag_counter += 1
        else:
            self.written_text += " " * indent * self.tag_counter + text + ''


