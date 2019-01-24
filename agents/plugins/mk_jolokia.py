#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import base64
import os
import socket
import ssl
import sys
import urllib2
import copy
from httplib import HTTPConnection, HTTPSConnection

try:
    from simplejson import json
except ImportError:
    try:
        import json
    except ImportError:
        sys.stdout.write("<<<jolokia_info>>>\n")
        sys.stdout.write("Error: Missing JSON library for Agent Plugin mk_jolokia\n")
        exit()

VERBOSE = '--verbose' in sys.argv
DEBUG = '--debug' in sys.argv

DEFAULT_CONFIG = {
    # Default global configuration values
    "protocol": "http",
    "server": "localhost",
    "port": 8080,
    "user": "monitoring",
    "password": None,
    "mode": "digest",
    "suburi": "jolokia",
    "instance": None,
    "cert_path": None,
    "client_cert": None,
    "client_key": None,
    "service_url": None,
    "service_user": None,
    "service_password": None,
    "product": None,
    "custom_vars": [],
    # List of instances to monitor. Each instance is a dict where
    # the global configuration values can be overridden.
    "instances": [{}],
}

QUERY_SPECS_GENERIC = [
    ("java.lang:type=Memory", "NonHeapMemoryUsage/used", "NonHeapMemoryUsage", [], False),
    ("java.lang:type=Memory", "NonHeapMemoryUsage/max", "NonHeapMemoryMax", [], False),
    ("java.lang:type=Memory", "HeapMemoryUsage/used", "HeapMemoryUsage", [], False),
    ("java.lang:type=Memory", "HeapMemoryUsage/max", "HeapMemoryMax", [], False),
    ("java.lang:type=Threading", "ThreadCount", "ThreadCount", [], False),
    ("java.lang:type=Threading", "DaemonThreadCount", "DeamonThreadCount", [], False),
    ("java.lang:type=Threading", "PeakThreadCount", "PeakThreadCount", [], False),
    ("java.lang:type=Threading", "TotalStartedThreadCount", "TotalStartedThreadCount", [], False),
    ("java.lang:type=Runtime", "Uptime", "Uptime", [], False),
    ("java.lang:type=GarbageCollector,name=*", "CollectionCount", "", [], False),
    ("java.lang:type=GarbageCollector,name=*", "CollectionTime", "", [], False),
    ("java.lang:name=CMS%20Perm%20Gen,type=MemoryPool", "Usage/used", "PermGenUsage", [], False),
    ("java.lang:name=CMS%20Perm%20Gen,type=MemoryPool", "Usage/max", "PermGenMax", [], False),
    ("net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics", "OffHeapHits",
     "", [], True),
    ("net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics", "OnDiskHits",
     "", [], True),
    ("net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics",
     "InMemoryHitPercentage", "", [], True),
    ("net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics", "CacheMisses",
     "", [], True),
    ("net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics",
     "OnDiskHitPercentage", "", [], True),
    ("net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics",
     "MemoryStoreObjectCount", "", [], True),
    ("net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics",
     "DiskStoreObjectCount", "", [], True),
    ("net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics",
     "CacheMissPercentage", "", [], True),
    ("net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics",
     "CacheHitPercentage", "", [], True),
    ("net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics",
     "OffHeapHitPercentage", "", [], True),
    ("net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics",
     "InMemoryMisses", "", [], True),
    ("net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics",
     "OffHeapStoreObjectCount", "", [], True),
    ("net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics",
     "WriterQueueLength", "", [], True),
    ("net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics",
     "WriterMaxQueueSize", "", [], True),
    ("net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics", "OffHeapMisses",
     "", [], True),
    ("net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics", "InMemoryHits",
     "", [], True),
    ("net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics",
     "AssociatedCacheName", "", [], True),
    ("net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics", "ObjectCount",
     "", [], True),
    ("net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics", "OnDiskMisses",
     "", [], True),
    ("net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics", "CacheHits", "",
     [], True),
]

QUERY_SPECS_SPECIFIC = {
    "weblogic": [
        ("*:*", "CompletedRequestCount", None, ["ServerRuntime"], False),
        ("*:*", "QueueLength", None, ["ServerRuntime"], False),
        ("*:*", "StandbyThreadCount", None, ["ServerRuntime"], False),
        ("*:*", "PendingUserRequestCount", None, ["ServerRuntime"], False),
        ("*:Name=ThreadPoolRuntime,*", "ExecuteThreadTotalCount", None, ["ServerRuntime"], False),
        ("*:*", "ExecuteThreadIdleCount", None, ["ServerRuntime"], False),
        ("*:*", "HoggingThreadCount", None, ["ServerRuntime"], False),
        ("*:Type=WebAppComponentRuntime,*", "OpenSessionsCurrentCount", None,
         ["ServerRuntime", "ApplicationRuntime"], False),
    ],
    "tomcat": [
        ("*:type=Manager,*", "activeSessions,maxActiveSessions", None, ["path", "context"], False),
        ("*:j2eeType=Servlet,name=default,*", "stateName", None, ["WebModule"], False),
        # Check not yet working
        ("*:j2eeType=Servlet,name=default,*", "requestCount", None, ["WebModule"], False),
        ("*:name=*,type=ThreadPool", "maxThreads", None, [], False),
        ("*:name=*,type=ThreadPool", "currentThreadCount", None, [], False),
        ("*:name=*,type=ThreadPool", "currentThreadsBusy", None, [], False),
        # too wide location for addressing the right info
        # ( "*:j2eeType=Servlet,*", "requestCount", None, [ "WebModule" ] , False),
    ],
    "jboss": [("*:type=Manager,*", "activeSessions,maxActiveSessions", None, ["path", "context"],
               False),],
}

#   ('*:j2eeType=WebModule,name=/--/localhost/-/%(app)s,*/state', None, [ "name" ]),
#   ('*:j2eeType=Servlet,WebModule=/--/localhost/-/%(app)s,name=%(servlet)s,*/requestCount',
#    None, [ "WebModule", "name" ]),
#   ("Catalina:J2EEApplication=none,J2EEServer=none,WebModule=*,j2eeType=Servlet,name=*",
#    None, [ "WebModule", "name" ]),

# We have to deal with socket timeouts. Python > 2.6
# supports timeout parameter for the urllib2.urlopen method
# but we are on a python 2.5 system here which seem to use the
# default socket timeout. We are local here so  set it to 1 second.
socket.setdefaulttimeout(1.0)


class SkipInstance(RuntimeError):
    pass


def write_section(name, iterable):
    sys.stdout.write('<<<%s:sep(0)>>>\n' % name)
    for line in iterable:
        sys.stdout.write(chr(0).join(map(str, line)) + '\n')


def cached(function):
    cache = {}

    def cached_function(*args):
        key = repr(args)
        try:
            return cache[key]
        except KeyError:
            return cache.setdefault(key, function(*args))

    return cached_function


def sanitize_config(config):

    instance = config.get("instance")
    err_msg = "%s in configuration"
    if instance:
        err_msg += " for %s" % instance

    required_keys = {"protocol", "server", "port", "suburi"}
    auth_mode = config.get("mode")
    if auth_mode in ("digest", "basic", "basic_preemtive"):
        required_keys |= {"user", "password"}
    elif auth_mode == "https":
        required_keys |= {"client_cert", "client_key"}
    if config.get("service_url") is not None and config.get("service_user") is not None:
        required_keys.add("service_password")
    missing_keys = required_keys - set(config.keys())
    if missing_keys:
        raise ValueError(err_msg % ("Missing keys " % ", ".join(missing_keys)))

    if not instance:
        config["instance"] = str(config["port"])
    config["instance"] = config["instance"].replace(" ", "_")

    # port must be (or look like) an integer
    try:
        config["port"] = int(config["port"])
    except ValueError:
        raise ValueError(err_msg % ("Invalid port %r" % config["port"]))

    if config.get("server") == "use fqdn":
        config["server"] = socket.getfqdn()

    return config


def _get_base_url(inst):
    return "%s://%s:%d/%s" % (
        inst["protocol"].strip('/'),
        inst["server"].strip('/'),
        inst["port"],
        inst["suburi"],
    )


def fetch_url(request_url, post_data=None):
    if VERBOSE:
        sys.stderr.write("DEBUG: Fetching: %s\n" % request_url)
    try:
        json_data = urllib2.urlopen(request_url, data=post_data).read()
        if VERBOSE:
            sys.stderr.write("DEBUG: Result: %s\n\n" % json_data)
    except () if DEBUG else Exception, exc:
        sys.stderr.write("ERROR: %s\n\n" % exc)
        return []
    return json_data


def _get_post_data(path, service_url, service_user, service_password, function):
    segments = path.strip("/").split("/")
    data = {"mbean": segments[0], "attribute": segments[1]}
    if len(segments) > 2:
        data["path"] = segments[2]
    data["type"] = function

    data["target"] = {"url": service_url}
    if service_user:
        data["target"]["user"] = service_user
        data["target"]["password"] = service_password

    return json.dumps(data)


def fetch_var(inst, path, service_url, service_user, service_password, function="read"):
    base_url = _get_base_url(inst)

    if service_url is not None:
        post_data = _get_post_data(path, service_url, service_user, service_password, function)
        json_data = fetch_url(base_url, post_data)
    else:
        request_url = "%s/%s/%s" % (base_url, function, path) if path else base_url + "/"
        json_data = fetch_url(request_url)

    try:
        obj = json.loads(json_data)
    except (ValueError, TypeError), exc:
        sys.stderr.write('ERROR: Invalid json code (%s)\n' % exc)
        sys.stderr.write('       Response %s\n' % json_data)
        return []

    if obj.get('status', 200) != 200:
        sys.stderr.write('ERROR: Invalid response when fetching url %s\n' % base_url)
        sys.stderr.write('       Response: %s\n' % json_data)
        return []

    # Only take the value of the object. If the value is an object
    # take the first items first value.
    # {'Catalina:host=localhost,path=\\/test,type=Manager': {'activeSessions': 0}}
    try:
        return obj['value']
    except KeyError:
        if VERBOSE:
            sys.stderr.write("ERROR: not found: %s\n" % path)
        return []


# convert single values into lists of items in
# case value is a 1-levelled or 2-levelled dict
def make_item_list(path, value, itemspec):
    if not isinstance(value, dict):
        if isinstance(value, str):
            value = value.replace(r'\/', '/')
        return [(path, value)]

    result = []
    for key, subvalue in value.items():
        # Handle filtering via itemspec
        miss = False
        while itemspec and '=' in itemspec[0]:
            if itemspec[0] not in key:
                miss = True
                break
            itemspec = itemspec[1:]
        if miss:
            continue
        item = extract_item(key, itemspec)
        if not item:
            item = (key,)
        result += make_item_list(path + item, subvalue, [])
    return result


# Example:
# key = 'Catalina:host=localhost,path=\\/,type=Manager'
# itemsepc = [ "path" ]
# --> "/"


def extract_item(key, itemspec):
    if not itemspec:
        return ()

    path = key.split(":", 1)[-1]
    components = path.split(",")
    comp_dict = dict(c.split('=') for c in components if c.count('=') == 1)

    item = ()
    for pathkey in itemspec:
        if pathkey in comp_dict:
            right = comp_dict[pathkey]
            if '/' in right:
                right = '/' + right.split('/')[-1]
            item = item + (right,)
    return item


def fetch_metric(inst, path, title, itemspec, inst_add=None):
    values = fetch_var(inst, path, inst["service_url"], inst["service_user"],
                       inst["service_password"])
    item_list = make_item_list((), values, itemspec)

    for subinstance, value in item_list:
        if not subinstance and not title:
            sys.stderr.write("INTERNAL ERROR: %s\n" % value)
            continue

        if "threadStatus" in subinstance or "threadParam" in subinstance:
            continue

        if len(subinstance) > 1:
            item = ",".join((inst["instance"],) + subinstance[:-1])
        elif inst_add is not None:
            item = ",".join((inst["instance"], inst_add))
        else:
            item = inst["instance"]
        if title:
            if subinstance:
                tit = title + "." + subinstance[-1]
            else:
                tit = title
        else:
            tit = subinstance[-1]

        yield (item.replace(" ", "_"), tit, value)


@cached
def _get_queries(do_search, inst, itemspec, title, path, mbean):
    if not do_search:
        return [(mbean + "/" + path, title, itemspec)]

    value = fetch_var(inst, mbean, None, None, None, function="search")
    try:
        paths = make_item_list((), value, "")[0][1]
    except IndexError:
        return []

    return [("%s/%s" % (urllib2.quote(mbean_exp), path), path, itemspec) for mbean_exp in paths]


def _process_queries(inst, queries):
    for mbean_path, title, itemspec in queries:
        try:
            for item, out_title, value in fetch_metric(inst, mbean_path, title, itemspec):
                yield item, out_title, value
        except (IOError, socket.timeout):
            raise SkipInstance()
        except () if DEBUG else Exception:
            continue


def query_instance(inst):
    try:
        prepare_http_opener(inst)
    except () if DEBUG else Exception, exc:
        sys.stderr.write("ERROR: %s\n" % exc)
        raise SkipInstance()

    write_section('jolokia_info', generate_jolokia_info(inst))

    shipped_vars = QUERY_SPECS_GENERIC + QUERY_SPECS_SPECIFIC.get(inst["product"], [])
    write_section('jolokia_metrics', generate_values(inst, shipped_vars))

    write_section('jolokia_generic', generate_values(inst, inst.get("custom_vars")))


class PreemptiveBasicAuthHandler(urllib2.HTTPBasicAuthHandler):
    """
    sends basic authentication with the first request,
    before the server even asks for it
    """

    def http_request(self, req):
        url = req.get_full_url()
        realm = None
        user, pwd = self.passwd.find_user_password(realm, url)
        if pwd:
            raw = "%s:%s" % (user, pwd)
            auth = 'Basic %s' % base64.b64encode(raw).strip()
            req.add_unredirected_header(self.auth_header, auth)
        return req

    https_request = http_request


class HTTPSValidatingConnection(HTTPSConnection):
    def __init__(self, host, ca_file, key_file, cert_file):
        HTTPSConnection.__init__(self, host, key_file=key_file, cert_file=cert_file)
        self.__ca_file = ca_file
        self.__key_file = key_file
        self.__cert_file = cert_file

    def connect(self):
        HTTPConnection.connect(self)
        if self.__ca_file:
            self.sock = ssl.wrap_socket(
                self.sock,
                keyfile=self.key_file,
                certfile=self.cert_file,
                ca_certs=self.__ca_file,
                cert_reqs=ssl.CERT_REQUIRED)
        else:
            self.sock = ssl.wrap_socket(
                self.sock,
                keyfile=self.key_file,
                certfile=self.cert_file,
                ca_certs=self.__ca_file,
                cert_reqs=ssl.CERT_NONE)


class HTTPSAuthHandler(urllib2.HTTPSHandler):
    def __init__(self, ca_file, key, cert):
        urllib2.HTTPSHandler.__init__(self)
        self.__ca_file = ca_file
        self.__key = key
        self.__cert = cert

    def https_open(self, req):
        # do_open expects a class as the first parameter but getConnection will act
        # as a facotry function
        return self.do_open(self.get_connection, req)

    def get_connection(self, host, _timeout):
        return HTTPSValidatingConnection(
            host, ca_file=self.__ca_file, key_file=self.__key, cert_file=self.__cert)


def prepare_http_opener(inst):
    # Prepare user/password authentication via HTTP Auth
    password_mngr = urllib2.HTTPPasswordMgrWithDefaultRealm()
    if inst.get("password"):
        password_mngr.add_password(None,
                                   "%s://%s:%d/" % (inst["protocol"], inst["server"], inst["port"]),
                                   inst["user"], inst["password"])

    handlers = []
    if inst["protocol"] == "https":
        if inst["mode"] == 'https' and (inst["client_key"] is None or inst["client_cert"] is None):
            raise ValueError("Missing client certificate for HTTPS authentication")
        handlers.append(
            HTTPSAuthHandler(inst["cert_path"], inst["client_key"], inst["client_cert"]))
    if inst["mode"] == 'digest':
        handlers.append(urllib2.HTTPDigestAuthHandler(password_mngr))
    elif inst["mode"] == "basic_preemptive":
        handlers.append(PreemptiveBasicAuthHandler(password_mngr))
    elif inst["mode"] == "basic" and inst["protocol"] != "https":
        handlers.append(urllib2.HTTPBasicAuthHandler(password_mngr))

    if handlers:
        opener = urllib2.build_opener(*handlers)
        urllib2.install_opener(opener)


def generate_jolokia_info(inst):
    # Determine type of server
    value = fetch_var(inst, "", None, None, None)
    server_info = make_item_list((), value, "")

    if not server_info:
        sys.stderr.write("%s ERROR: Empty server info\n" % (inst["instance"],))
        raise SkipInstance()

    info_dict = dict(server_info)
    version = info_dict.get(('info', 'version'), "unknown")
    product = info_dict.get(('info', 'product'), "unknown")
    if inst.get("product"):
        product = inst["product"]
    agentversion = info_dict.get(('agent',), "unknown")
    yield inst["instance"], product, version, agentversion


def generate_values(inst, var_list):
    for var in var_list:
        mbean, path, title, itemspec, do_search = var[:5]
        value_type = var[5] if len(var) >= 6 else None

        queries = _get_queries(do_search, inst, itemspec, title, path, mbean)

        for item, title, value in _process_queries(inst, queries):
            if value_type:
                yield item, title, value, value_type
            else:
                yield item, title, value


def yield_configured_instances():

    custom_config = copy.deepcopy(DEFAULT_CONFIG)

    conffile = os.path.join(os.getenv("MK_CONFDIR", "/etc/check_mk"), "jolokia.cfg")
    if os.path.exists(conffile):
        execfile(conffile, {}, custom_config)

    # Generate list of instances to monitor. If the user has defined
    # instances in his configuration, we will use this (a list of dicts).
    individual_configs = custom_config.pop("instances", [{}])
    for cfg in individual_configs:
        keys = set(cfg.keys() + custom_config.keys())
        yield {k: cfg.get(k, custom_config[k]) for k in keys}


def main(configs_iterable=None):
    if configs_iterable is None:
        configs_iterable = yield_configured_instances()

    for config in configs_iterable:
        instance = sanitize_config(config)
        try:
            query_instance(instance)
        except SkipInstance:
            pass


if __name__ == "__main__":
    main()
