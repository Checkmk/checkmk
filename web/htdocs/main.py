
def page_index(html):
    html.req.headers_out.add("Cache-Control", "max-age=7200, public");
    html.write("""
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Frameset//EN" "http://www.w3.org/TR/html4/frameset.dtd">
<html>
<head>
 <title>Check_MK Multisite</title>
 <link rel="shortcut icon" href="images/favicon.ico" type="image/ico">
</head>
<frameset cols="280,*" frameborder="0" framespacing="0" border="0">
    <frame src="side.py" name="side" noresize>
    <frame src="main.py" name="main" noresize>
</html>
""") 

def page_main(html):
    html.header("Check_MK Multisite")
    html.write("""
<p>Welcome to Check_MK Multisite - a new GUI for viewing status information
and controlling your monitoring system. Multisite is not just another GUI
for Nagios - it uses a completely new architecture and design scheme. It's
key benefits are:</p>
<ul>
<li>It is fast.</li>
<li>it is flexible.</li>
<li>It supports distributed monitoring.</li>
</ul>

<p>Multisite is completely based on
<a href="http://mathias-kettner.de/checkmk_livestatus.html">MK
Livestatus</a>, which is what makes it fast in the first place - especially
in huge installations with a large number of hosts and services. </p>

<p>User customizable <b>views</b> is what makes Multisite flexible. Customize
the builtin views or create completely own views in order to need your
demands.</p>

<p>Multisite supports distributed monitoring by allowing you to combine an
arbitrary number of Monitoring servers under a common visualisation layer,
without the need of a centralized data storage. No SQL database is needed.
No network traffic is generated due to the monitoring.</p>

<p>Please learn more about Multisite at its <a href="http://mathias-kettner.de/checkmk_multisite.html">Documentation home page</a>.</p>

""")
    html.footer()

# This function does nothing. The sites have already
# been reconfigured according to the variable _site_switch,
# because that variable is processed by connect_to_livestatus()
def ajax_switch_site(html):
    pass 
