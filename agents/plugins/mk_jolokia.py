#!/usr/bin/env python
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

import os
import socket
import sys
import urllib2

try:
    try:
        from simplejson import json
    except ImportError:
        import json
except ImportError as import_error:
    sys.stdout.write(
        "<<<jolokia_info>>>\n"
        "Error: mk_jolokia requires either the json or simplejson library."
        " Please either use a Python version that contains the json library or install the"
        " simplejson library on the monitored system.")
    sys.exit(1)

try:
    import requests
    from requests.auth import HTTPDigestAuth
    from requests.packages import urllib3
except ImportError as import_error:
    sys.stdout.write("<<<jolokia_info>>>\n"
                     "Error: mk_jolokia requires the requests library."
                     " Please install it on the monitored system.")
    sys.exit(1)

VERBOSE = '--verbose' in sys.argv
DEBUG = '--debug' in sys.argv

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

# Default global configuration: key, value [, help]
DEFAULT_CONFIG_TUPLES = (
    ("protocol", "http", "Protocol to use (http/https)."),
    ("server", "localhost", "Host name or IP address of the Jolokia server."),
    ("port", 8080, "TCP Port of the Jolokia server."),
    ("suburi", "jolokia", "Path-component of the URI to query."),
    ("user", "monitoring", "Username to use for connecting."),
    ("password", None, "Password to use for connecting."),
    ("mode", "digest", "Authentication mode. Can be \"basic\", \"digest\" or \"https\"."),
    ("instance", None, "Name of the instance in the monitoring. Defaults to port."),
    ("verify", None),
    ("client_cert", None, "Path to client cert for https authentication."),
    ("client_key", None, "Client cert secret for https authentication."),
    ("service_url", None),
    ("service_user", None),
    ("service_password", None),
    ("product", None, "Product description. Available: %s" % \
                      ", ".join(QUERY_SPECS_SPECIFIC.keys())),
    ("timeout", 1.0, "Connection/read timeout for requests."),
    ("custom_vars", []),
    # List of instances to monitor. Each instance is a dict where
    # the global configuration values can be overridden.
    ("instances", [{}]),
)


class SkipInstance(RuntimeError):
    pass


class SkipMBean(RuntimeError):
    pass


def get_default_config_dict():
    return {t[0]: t[1] for t in DEFAULT_CONFIG_TUPLES}


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


class JolokiaInstance(object):
    @staticmethod
    def _sanitize_config(config):
        instance = config.get("instance")
        err_msg = "%s in configuration"
        if instance:
            err_msg += " for %s" % instance

        required_keys = {"protocol", "server", "port", "suburi", "timeout"}
        auth_mode = config.get("mode")
        if auth_mode in ("digest", "basic", "basic_preemtive"):
            required_keys |= {"user", "password"}
        elif auth_mode == "https":
            required_keys |= {"client_cert", "client_key"}
        if config.get("service_url") is not None and config.get("service_user") is not None:
            required_keys.add("service_password")
        missing_keys = required_keys - set(config.keys())
        if missing_keys:
            raise ValueError(err_msg % ("Missing key(s): %s" % ", ".join(sorted(missing_keys))))

        if not instance:
            instance = str(config["port"])
        config["instance"] = instance.replace(" ", "_")

        # port must be (or look like) an integer, timeout like float
        for key, type_ in (("port", int), ("timeout", float)):
            val = config[key]
            try:
                config[key] = type_(val)
            except ValueError:
                raise ValueError(err_msg % ("Invalid %s %r" % (key, val)))

        if config.get("server") == "use fqdn":
            config["server"] = socket.getfqdn()

        # if "verify" was not set to bool/string
        if config.get("verify") is None:
            # handle legacy "cert_path"
            cert_path = config.get("cert_path")
            if cert_path not in ("_default", None):
                # The '_default' was the default value
                # up to cmk version 1.5.0p8. It broke things.
                config["verify"] = cert_path
            else:
                # this is default, but be explicit
                config["verify"] = True

        return config

    def __init__(self, config):
        super(JolokiaInstance, self).__init__()
        self._config = self._sanitize_config(config)

        self.name = self._config["instance"]
        self.product = self._config.get("product")
        self.custom_vars = self._config.get("custom_vars", [])

        self.base_url = self._get_base_url()
        self.target = self._get_target()
        self._session = self._initialize_http_session()

    def _get_base_url(self):
        return "%s://%s:%d/%s/" % (
            self._config["protocol"].strip('/'),
            self._config["server"].strip('/'),
            self._config["port"],
            self._config["suburi"],
        )

    def _get_target(self):
        url = self._config.get("service_url")
        if url is None:
            return {}
        user = self._config.get("service_user")
        if user is None:
            return {"url": url}
        return {
            "url": url,
            "user": user,
            "password": self._config["service_password"],
        }

    def _initialize_http_session(self):
        session = requests.Session()
        session.verify = self._config["verify"]
        if session.verify is False:
            urllib3.disable_warnings(category=urllib3.exceptions.InsecureRequestWarning)
        session.timeout = self._config["timeout"]

        auth_method = self._config.get("mode")
        if auth_method is None:
            return session

        # initialize authentication
        if auth_method == "https":
            session.cert = (
                self._config["client_cert"],
                self._config["client_key"],
            )
        elif auth_method == 'digest':
            session.auth = HTTPDigestAuth(
                self._config["user"],
                self._config["password"],
            )
        elif auth_method in ("basic", "basic_preemptive"):
            session.auth = (
                self._config["user"],
                self._config["password"],
            )
        else:
            raise NotImplementedError("Authentication method %r" % auth_method)

        return session

    def get_post_data(self, path, function, use_target):
        segments = path.strip("/").split("/")
        # we may have one to three segments:
        data = dict(zip(("mbean", "attribute", "path"), segments))

        data["type"] = function
        if use_target and self.target:
            data["target"] = self.target
        return data

    def post(self, data):
        post_data = json.dumps(data)
        if VERBOSE:
            sys.stderr.write("DEBUG: POST data: %r\n" % post_data)
        try:
            raw_response = self._session.post(self.base_url, data=post_data)
        except () if DEBUG else Exception, exc:
            sys.stderr.write("ERROR: %s\n" % exc)
            raise SkipMBean(exc)

        if raw_response.status_code == 401:
            sys.stderr.write("ERROR: Unauthorized (authentication failed/missing)\n")
            raise SkipInstance("auth failed")
        elif raw_response.status_code != 200:
            sys.stderr.write('ERROR: Invalid response when posting %r\n' % post_data)
            raise SkipMBean("HTTP Error (%s)" % raw_response.status_code)

        response = raw_response.json()
        if VERBOSE:
            sys.stderr.write("DEBUG: Result: %r\n\n" % response)
        return response


def fetch_var(inst, function, path, use_target=False):
    data = inst.get_post_data(path, function, use_target=use_target)
    obj = inst.post(data)

    try:
        return obj['value']
    except KeyError:
        msg = "not found: %s" % path
        if VERBOSE:
            sys.stderr.write("ERROR: %s\n" % msg)
        raise SkipMBean(msg)


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
    values = fetch_var(inst, "read", path, use_target=True)
    item_list = make_item_list((), values, itemspec)

    for subinstance, value in item_list:
        if not subinstance and not title:
            sys.stderr.write("INTERNAL ERROR: %s\n" % value)
            continue

        if "threadStatus" in subinstance or "threadParam" in subinstance:
            continue

        if len(subinstance) > 1:
            item = ",".join((inst.name,) + subinstance[:-1])
        elif inst_add is not None:
            item = ",".join((inst.name, inst_add))
        else:
            item = inst.name

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

    value = fetch_var(inst, "search", mbean)
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
        except SkipMBean:
            continue
        except () if DEBUG else Exception:
            continue


def query_instance(inst):
    write_section('jolokia_info', generate_jolokia_info(inst))

    shipped_vars = QUERY_SPECS_GENERIC + QUERY_SPECS_SPECIFIC.get(inst.product, [])
    write_section('jolokia_metrics', generate_values(inst, shipped_vars))

    write_section('jolokia_generic', generate_values(inst, inst.custom_vars))


def generate_jolokia_info(inst):
    # Determine type of server
    try:
        data = fetch_var(inst, "version", "")
    except (SkipInstance, SkipMBean) as exc:
        yield inst.name, "ERROR", str(exc)
        raise SkipInstance(exc)

    info = data.get('info', {})
    version = info.get('version', "unknown")
    product = info.get('product', "unknown")
    if inst.product:
        product = inst.product

    agentversion = data.get('agent', "unknown")
    yield inst.name, product, version, agentversion


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


def yield_configured_instances(custom_config=None):

    if custom_config is None:
        custom_config = get_default_config_dict()

    conffile = os.path.join(os.getenv("MK_CONFDIR", "/etc/check_mk"), "jolokia.cfg")
    if os.path.exists(conffile):
        execfile(conffile, {}, custom_config)

    # Generate list of instances to monitor. If the user has defined
    # instances in his configuration, we will use this (a list of dicts).
    individual_configs = custom_config.pop("instances", [{}])
    for cfg in individual_configs:
        keys = set(cfg.keys() + custom_config.keys())
        conf_dict = {k: cfg.get(k, custom_config.get(k)) for k in keys}
        if VERBOSE:
            sys.stderr.write("DEBUG: configuration: %r\n" % conf_dict)
        yield conf_dict


def main(configs_iterable=None):
    if configs_iterable is None:
        configs_iterable = yield_configured_instances()

    for config in configs_iterable:
        instance = JolokiaInstance(config)
        try:
            query_instance(instance)
        except SkipInstance:
            pass


if __name__ == "__main__":
    main()
