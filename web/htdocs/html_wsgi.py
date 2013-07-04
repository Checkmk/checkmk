
from lib import *
from htmllib import html
import defaults_standalone as defaults


class html_wsgi(html):
    def __init__(self, environ):
        self.output = "" #Collector for the page output
        self.user = 'Test user'

        html.__init__(self)

    def lowlevel_write(self, text, flush = 0):
        self.output += text

    def var(self, varname, deflt = None):
        return varname

    def makeuri(self, addvars, remove_prefix = None, filename=None):
        return "TODO"

