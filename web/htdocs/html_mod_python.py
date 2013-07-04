from mod_python import Cookie, util, apache
from htmllib import html
import time

#TODO Dubpluicate code in htmllib.py


class html_mod_python(html):

    def __init__(self, req):

        # All URIs end in .py. We strip away the .py and get the
        # name of the page.
        req.myfile = req.uri.split("/")[-1][:-3]
        self.req = req
        html.__init__(self)
        self.user = req.user

    def set_cookie(self, varname, value, expires = None):
        c = Cookie.Cookie(varname, value, path = '/')
        if expires is not None:
            c.expires = expires

        if not self.req.headers_out.has_key("Set-Cookie"):
            self.req.headers_out.add("Cache-Control", 'no-cache="set-cookie"')
            self.req.err_headers_out.add("Cache-Control", 'no-cache="set-cookie"')

        self.req.headers_out.add("Set-Cookie", str(c))
        self.req.err_headers_out.add("Set-Cookie", str(c))

    def del_cookie(self, varname):
        self.set_cookie(varname, '', time.time() - 60)

    def read_cookies(self):
        self.req.cookies = Cookie.get_cookies(self.req)

    def read_get_vars(self):
        req = self.req
        req.vars = {}
        req.listvars = {} # for variables with more than one occurrance
        fields = util.FieldStorage(req, keep_blank_values = 1)
        for field in fields.list:
            varname = field.name
            value = field.value
            # Multiple occurrance of a variable? Store in extra list dict
            if varname in req.vars:
                if varname in req.listvars:
                    req.listvars[varname].append(value)
                else:
                    req.listvars[varname] = [ req.vars[varname], value ]
            # In the single-value-store the last occurrance of a variable
            # has precedence. That makes appending variables to the current
            # URL simpler.
            req.vars[varname] = value

    def has_var(self, varname):
        return varname in self.req.vars

    def lowlevel_write(self, text):
        if self.io_error:
            return

        try:
            if self.buffering:
                self.req.write(text, 0)
            else:
                self.req.write(text)
        except IOError, e:
            # Catch writing problems to client, prevent additional writes
            self.io_error = True
            self.log('%s' % e)

    def var(self, varname, deflt = None):
        return self.req.vars.get(varname, deflt)

    # [('varname1', value1), ('varname2', value2) ]
    def makeuri(self, addvars, remove_prefix = None, filename=None):
        new_vars = [ nv[0] for nv in addvars ]
        vars = [ (v, self.var(v))
                 for v in self.req.vars
                 if v[0] != "_" and v not in new_vars ]
        if remove_prefix != None:
            vars = [ i for i in vars if not i[0].startswith(remove_prefix) ]
        vars = vars + addvars
        if filename == None:
            filename = self.req.myfile + ".py"
        if vars:
            return filename + "?" + urlencode_vars(vars)
        else:
            return filename

