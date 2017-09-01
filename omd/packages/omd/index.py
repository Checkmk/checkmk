from mod_python import apache,util
import os, re

def site_name(req):
    return os.path.normpath(req.uri).split("/")[1]

def handler(req):
    req.content_type = "text/html; charset=UTF-8"
    req.header_sent = False
    req.myfile = req.uri.split("/")[-1][:-3]

    if req.myfile == "error":
        try:
            show_apache_log(req)
            return apache.OK
        except Exception, e:
            req.write("<html><body><h1>Internal Error</h1>Cannot output error log: %s</body></html>" % html_escape(e))
            return apache.OK

    # Redirect requests not asking for the error.py to the Check_MK GUI
    sitename = site_name(req)
    util.redirect(req, "/%s/check_mk/" % sitename)

    return apache.OK

def html_escape(value):
    return value.replace("&", "&amp;")\
                .replace('"', "&quot;")\
                .replace("<", "&lt;")\
                .replace(">", "&gt;")

def show_apache_log(req):
    log_path = '/omd/sites/%s/var/log/apache/error_log' % site_name(req)

    req.write("<html><head><style>\n")
    req.write("b.date { color: #888; font-weight: normal; }\n")
    req.write("b.level.error { color: #f00; }\n")
    req.write("b.level.notice { color: #8cc; }\n")
    req.write("b.level { color: #cc0; }\n")
    req.write("b.msg.error { background-color: #fcc; color: #c00; }\n")
    req.write("b.msg.warn { background-color: #ffc; color: #880; }\n")
    req.write("b.msg { font-weight: normal; }\n")
    req.write("b.msg b.line { background-color: #fdd; color: black; }\n")

    req.write("</style><body>\n")
    req.write("<h1>Internal Server Error</h1>")
    req.write("<p>An internal error occurred. Details can be found in the Apache error log")
    if not log_path:
        req.write(".")
    else:
        logfile = file(log_path)
        lines = logfile.readlines()
        if len(lines) > 30:
            lines = lines[-30:]

        req.write(" (%s). " % log_path)
        req.write("Here are the last couple of lines from that log file:</p>")
        req.write("<pre class=errorlog>\n")
        for line in lines:
            parts = line.split(']', 2)
            if len(parts) < 3:
                parts += [ "" ] * (3 - len(parts))
            date = parts[0].lstrip('[').strip()
            level = parts[1].strip().lstrip('[')
            message = parts[2].strip()
            message = re.sub("line ([0-9]+)", "line <b class=line>\\1</b>", message)
            req.write("<b class=date>%s</b> <b class=\"level %s\">%s</b> <b class=\"msg %s\">%s</b>\n" % 
                      (html_escape(date), html_escape(level), "%-7s" % html_escape(level),
                       html_escape(level), html_escape(message)))
        req.write("</pre>\n")
    req.write("</body></html>\n")

