#!/usr/bin/python
import livestatus


sites = {
  "muc" : {
	"socket"     : "unix:/var/run/nagios/rw/live",
	"alias"      : "Munich",
  },
  "sitea" : {
        "alias"      : "Augsburg",
        "socket"     : "tcp:sitea:6557",
        "nagios_url" : "/nagios/",
	"timeout"    : 2,
  },
  "siteb" : {
        "alias"      : "Berlin",
        "socket"     : "tcp:siteb:6557",
        "nagios_url" : "/nagios/",
	"timeout"    : 10,
  },
}

c = livestatus.MultiSiteConnection(sites)
c.set_prepend_site(True)
print c.query("GET hosts\nColumns: name state\n")
c.set_prepend_site(False)
print c.query("GET hosts\nColumns: name state\n")

# Beware: When doing stats, you need to aggregate yourself:
print sum(c.query_column("GET hosts\nStats: state >= 0\n"))

# Detect errors:
sites = {
  "muc" : {
	"socket"     : "unix:/var/run/nagios/rw/live",
	"alias"      : "Munich",
  },
  "sitea" : {
        "alias"      : "Augsburg",
        "socket"     : "tcp:sitea:6558", # BROKEN
        "nagios_url" : "/nagios/",
	"timeout"    : 2,
  },
  "siteb" : {
        "alias"      : "Berlin",
        "socket"     : "tcp:siteb:6557",
        "nagios_url" : "/nagios/",
	"timeout"    : 10,
  },
}

c = livestatus.MultiSiteConnection(sites)
for name, state in c.query("GET hosts\nColumns: name state\n"):
    print "%-15s: %d" % (name, state)
print "Dead sites:"
for sitename, info in c.dead_sites().items():
    print "%s: %s" % (sitename, info["exception"])
