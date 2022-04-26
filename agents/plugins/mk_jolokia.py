#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

__version__ = "2.1.0b7"

# this file has to work with both Python 2 and 3
# pylint: disable=super-with-arguments

import io
import os
import socket
import sys

# For Python 3 sys.stdout creates \r\n as newline for Windows.
# Checkmk can't handle this therefore we rewrite sys.stdout to a new_stdout function.
# If you want to use the old behaviour just use old_stdout.
if sys.version_info[0] >= 3:
    new_stdout = io.TextIOWrapper(
        sys.stdout.buffer, newline="\n", encoding=sys.stdout.encoding, errors=sys.stdout.errors
    )
    old_stdout, sys.stdout = sys.stdout, new_stdout

# Continue if typing cannot be imported, e.g. for running unit tests
try:
    from typing import Any, Callable, Dict, List, Optional, Tuple, Union
except ImportError:
    pass

if sys.version_info[0] >= 3:
    from urllib.parse import quote  # pylint: disable=import-error,no-name-in-module
else:
    from urllib2 import quote  # type: ignore[attr-defined] # pylint: disable=import-error

try:
    try:
        import simplejson as json
    except ImportError:
        import json  # type: ignore[no-redef]
except ImportError:
    sys.stdout.write(
        "<<<jolokia_info>>>\n"
        "Error: mk_jolokia requires either the json or simplejson library."
        " Please either use a Python version that contains the json library or install the"
        " simplejson library on the monitored system.\n"
    )
    sys.exit(1)

try:
    import requests
    from requests.auth import HTTPDigestAuth

    # These days urllib3 would be included directly, but we leave it as it is for the moment
    # for compatibility reasons - at least for the agent plugin here.
    from requests.packages import urllib3  # type: ignore[attr-defined]
except ImportError:
    sys.stdout.write(
        "<<<jolokia_info>>>\n"
        "Error: mk_jolokia requires the requests library."
        " Please install it on the monitored system.\n"
    )
    sys.exit(1)

VERBOSE = sys.argv.count("--verbose") + sys.argv.count("-v") + 2 * sys.argv.count("-vv")
DEBUG = sys.argv.count("--debug")

MBEAN_SECTIONS = {
    "jvm_threading": ("java.lang:type=Threading",),
    "jvm_memory": (
        "java.lang:type=Memory",
        "java.lang:name=*,type=MemoryPool",
    ),
    "jvm_runtime": ("java.lang:type=Runtime/Uptime,Name",),
    "jvm_garbagecollectors": (
        "java.lang:name=*,type=GarbageCollector/CollectionCount,CollectionTime,Name",
    ),
}  # type: Dict[str, Tuple[str, ...]]

MBEAN_SECTIONS_SPECIFIC = {
    "tomcat": {
        "jvm_threading": (
            "*:name=*,type=ThreadPool/maxThreads,currentThreadCount,currentThreadsBusy/",
        ),
    },
}

QUERY_SPECS_LEGACY = [
    (
        "net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics",
        "OffHeapHits",
        "",
        [],
        True,
    ),
    (
        "net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics",
        "OnDiskHits",
        "",
        [],
        True,
    ),
    (
        "net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics",
        "InMemoryHitPercentage",
        "",
        [],
        True,
    ),
    (
        "net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics",
        "CacheMisses",
        "",
        [],
        True,
    ),
    (
        "net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics",
        "OnDiskHitPercentage",
        "",
        [],
        True,
    ),
    (
        "net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics",
        "MemoryStoreObjectCount",
        "",
        [],
        True,
    ),
    (
        "net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics",
        "DiskStoreObjectCount",
        "",
        [],
        True,
    ),
    (
        "net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics",
        "CacheMissPercentage",
        "",
        [],
        True,
    ),
    (
        "net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics",
        "CacheHitPercentage",
        "",
        [],
        True,
    ),
    (
        "net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics",
        "OffHeapHitPercentage",
        "",
        [],
        True,
    ),
    (
        "net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics",
        "InMemoryMisses",
        "",
        [],
        True,
    ),
    (
        "net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics",
        "OffHeapStoreObjectCount",
        "",
        [],
        True,
    ),
    (
        "net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics",
        "WriterQueueLength",
        "",
        [],
        True,
    ),
    (
        "net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics",
        "WriterMaxQueueSize",
        "",
        [],
        True,
    ),
    (
        "net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics",
        "OffHeapMisses",
        "",
        [],
        True,
    ),
    (
        "net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics",
        "InMemoryHits",
        "",
        [],
        True,
    ),
    (
        "net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics",
        "AssociatedCacheName",
        "",
        [],
        True,
    ),
    (
        "net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics",
        "ObjectCount",
        "",
        [],
        True,
    ),
    (
        "net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics",
        "OnDiskMisses",
        "",
        [],
        True,
    ),
    (
        "net.sf.ehcache:CacheManager=CacheManagerApplication*,*,type=CacheStatistics",
        "CacheHits",
        "",
        [],
        True,
    ),
]  # type: List[Tuple[str, str, str, List, bool]]

QUERY_SPECS_SPECIFIC_LEGACY = {
    "weblogic": [
        ("*:*", "CompletedRequestCount", None, ["ServerRuntime"], False),
        ("*:*", "QueueLength", None, ["ServerRuntime"], False),
        ("*:*", "StandbyThreadCount", None, ["ServerRuntime"], False),
        ("*:*", "PendingUserRequestCount", None, ["ServerRuntime"], False),
        ("*:Name=ThreadPoolRuntime,*", "ExecuteThreadTotalCount", None, ["ServerRuntime"], False),
        ("*:*", "ExecuteThreadIdleCount", None, ["ServerRuntime"], False),
        ("*:*", "HoggingThreadCount", None, ["ServerRuntime"], False),
        (
            "*:Type=WebAppComponentRuntime,*",
            "OpenSessionsCurrentCount",
            None,
            ["ServerRuntime", "ApplicationRuntime"],
            False,
        ),
    ],
    "tomcat": [
        ("*:type=Manager,*", "activeSessions,maxActiveSessions", None, ["path", "context"], False),
        ("*:j2eeType=Servlet,name=default,*", "stateName", None, ["WebModule"], False),
        # Check not yet working
        ("*:j2eeType=Servlet,name=default,*", "requestCount", None, ["WebModule"], False),
        # too wide location for addressing the right info
        # ( "*:j2eeType=Servlet,*", "requestCount", None, [ "WebModule" ] , False),
    ],
    "jboss": [
        ("*:type=Manager,*", "activeSessions,maxActiveSessions", None, ["path", "context"], False),
    ],
}

AVAILABLE_PRODUCTS = sorted(
    set(QUERY_SPECS_SPECIFIC_LEGACY.keys()) | set(MBEAN_SECTIONS_SPECIFIC.keys())
)

# Default global configuration: key, value [, help]
DEFAULT_CONFIG_TUPLES = (
    ("protocol", "http", "Protocol to use (http/https)."),
    ("server", "localhost", "Host name or IP address of the Jolokia server."),
    ("port", 8080, "TCP Port of the Jolokia server."),
    ("suburi", "jolokia", "Path-component of the URI to query."),
    ("user", "monitoring", "Username to use for connecting."),
    ("password", None, "Password to use for connecting."),
    ("mode", "digest", 'Authentication mode. Can be "basic", "digest" or "https".'),
    ("instance", None, "Name of the instance in the monitoring. Defaults to port."),
    ("verify", None),
    ("client_cert", None, "Path to client cert for https authentication."),
    ("client_key", None, "Client cert secret for https authentication."),
    ("service_url", None),
    ("service_user", None),
    ("service_password", None),
    (
        "product",
        None,
        "Product description. Available: %s. If not provided,"
        " we try to detect the product from the jolokia info section."
        % ", ".join(AVAILABLE_PRODUCTS),
    ),
    ("timeout", 1.0, "Connection/read timeout for requests."),
    ("custom_vars", []),
    # List of instances to monitor. Each instance is a dict where
    # the global configuration values can be overridden.
    ("instances", [{}]),
)  # type: Tuple[Tuple[Union[Optional[str], float, List[Any]], ...], ...]


class SkipInstance(RuntimeError):
    pass


class SkipMBean(RuntimeError):
    pass


def get_default_config_dict():
    return {elem[0]: elem[1] for elem in DEFAULT_CONFIG_TUPLES}


def write_section(name, iterable):
    sys.stdout.write("<<<%s:sep(0)>>>\n" % name)
    for line in iterable:
        sys.stdout.write(chr(0).join(map(str, line)) + "\n")


def cached(function):
    cache = {}  # type: Dict[str, Callable]

    def cached_function(*args):
        key = repr(args)
        try:
            return cache[key]
        except KeyError:
            return cache.setdefault(key, function(*args))

    return cached_function


class JolokiaInstance(object):  # pylint: disable=useless-object-inheritance
    # use this to filter headers whien recording via vcr trace
    FILTER_SENSITIVE = {"filter_headers": [("authorization", "****")]}

    @staticmethod
    def _sanitize_config(config):
        instance = config.get("instance")
        err_msg = "%s in configuration"
        if instance:
            err_msg += " for %s" % instance

        required_keys = set(("protocol", "server", "port", "suburi", "timeout"))
        auth_mode = config.get("mode")
        if auth_mode in ("digest", "basic", "basic_preemtive"):
            required_keys |= set(("user", "password"))
        elif auth_mode == "https":
            required_keys |= set(("client_cert", "client_key"))
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
        self.post_config = {"ignoreErrors": "true"}
        self._session = self._initialize_http_session()

    def _get_base_url(self):
        return "%s://%s:%d/%s/" % (
            self._config["protocol"].strip("/"),
            self._config["server"].strip("/"),
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
        # Watch out: we must provide the verify keyword to every individual request call!
        # Else it will be overwritten by the REQUESTS_CA_BUNDLE env variable
        session.verify = self._config["verify"]
        if session.verify is False:
            urllib3.disable_warnings(category=urllib3.exceptions.InsecureRequestWarning)
        session.timeout = self._config["timeout"]  # type: ignore[attr-defined]

        auth_method = self._config.get("mode")
        if auth_method is None:
            return session

        # initialize authentication
        if auth_method == "https":
            session.cert = (
                self._config["client_cert"],
                self._config["client_key"],
            )
        elif auth_method == "digest":
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
        data["config"] = self.post_config
        return data

    def post(self, data):
        post_data = json.dumps(data)
        if VERBOSE:
            sys.stderr.write("\nDEBUG: POST data: %r\n" % post_data)
        try:
            # Watch out: we must provide the verify keyword to every individual request call!
            # Else it will be overwritten by the REQUESTS_CA_BUNDLE env variable
            raw_response = self._session.post(
                self.base_url, data=post_data, verify=self._session.verify
            )
        except requests.exceptions.ConnectionError:
            if DEBUG:
                raise
            raise SkipInstance("Cannot connect to server at %s" % self.base_url)
        except Exception as exc:
            if DEBUG:
                raise
            sys.stderr.write("ERROR: %s\n" % exc)
            raise SkipMBean(exc)

        return validate_response(raw_response)


def validate_response(raw):
    """return loaded response or raise exception"""
    if VERBOSE > 1:
        sys.stderr.write(
            "DEBUG: %r:\n"
            "DEBUG:   headers: %r\n"
            "DEBUG:   content: %r\n\n" % (raw, raw.headers, raw.content)
        )

    # check the status of the http server
    if not 200 <= raw.status_code < 300:
        sys.stderr.write("ERROR: HTTP STATUS: %d\n" % raw.status_code)
        # Unauthorized, Forbidden, Bad Gateway
        if raw.status_code in (401, 403, 502):
            raise SkipInstance("HTTP STATUS", raw.status_code)
        raise SkipMBean("HTTP STATUS", raw.status_code)

    response = raw.json()
    # check the status of the jolokia response
    if response.get("status") != 200:
        errmsg = response.get("error", "unkown error")
        sys.stderr.write("ERROR: JAVA: %s\n" % errmsg)
        raise SkipMBean("JAVA", errmsg)

    if "value" not in response:
        sys.stderr.write("ERROR: missing 'value': %r\n" % response)
        raise SkipMBean("ERROR", "missing 'value'")

    if VERBOSE:
        sys.stderr.write("\nDEBUG: RESPONSE: %r\n" % response)

    return response


def fetch_var(inst, function, path, use_target=False):
    data = inst.get_post_data(path, function, use_target=use_target)
    obj = inst.post(data)
    return obj["value"]


# convert single values into lists of items in
# case value is a 1-levelled or 2-levelled dict
def make_item_list(path, value, itemspec):
    if not isinstance(value, dict):
        if isinstance(value, str):
            value = value.replace(r"\/", "/")
        return [(path, value)]

    result = []
    for key, subvalue in value.items():
        # Handle filtering via itemspec
        miss = False
        while itemspec and "=" in itemspec[0]:
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
    comp_dict = dict(c.split("=") for c in components if c.count("=") == 1)

    item = ()  # type: Tuple[Any, ...]
    for pathkey in itemspec:
        if pathkey in comp_dict:
            right = comp_dict[pathkey]
            if "/" in right:
                right = "/" + right.split("/")[-1]
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
            instance_out = ",".join((inst.name,) + subinstance[:-1])
        elif inst_add is not None:
            instance_out = ",".join((inst.name, inst_add))
        else:
            instance_out = inst.name
        instance_out = instance_out.replace(" ", "_")

        if title:
            if subinstance:
                title_out = title + "." + subinstance[-1]
            else:
                title_out = title
        else:
            title_out = subinstance[-1]

        yield instance_out, title_out, value


@cached
def _get_queries(do_search, inst, itemspec, title, path, mbean):
    if not do_search:
        return [(mbean + "/" + path, title, itemspec)]

    try:
        value = fetch_var(inst, "search", mbean)
    except SkipMBean:
        if DEBUG:
            raise
        return []

    try:
        paths = make_item_list((), value, "")[0][1]
    except IndexError:
        return []

    return [("%s/%s" % (quote(mbean_exp), path), path, itemspec) for mbean_exp in paths]


def _process_queries(inst, queries):
    for mbean_path, title, itemspec in queries:
        try:
            for instance_out, title_out, value in fetch_metric(inst, mbean_path, title, itemspec):
                yield instance_out, title_out, value
        except (IOError, socket.timeout):
            raise SkipInstance()
        except SkipMBean:
            continue
        except Exception:
            if DEBUG:
                raise
            continue


def query_instance(inst):
    write_section("jolokia_info", generate_jolokia_info(inst))

    # now (after jolokia_info) we're sure about the product
    specs_specific = QUERY_SPECS_SPECIFIC_LEGACY.get(inst.product, [])
    write_section("jolokia_metrics", generate_values(inst, specs_specific))
    write_section("jolokia_metrics", generate_values(inst, QUERY_SPECS_LEGACY))

    sections_specific = MBEAN_SECTIONS_SPECIFIC.get(inst.product, {})
    for section_name, mbeans in sections_specific.items():
        write_section("jolokia_%s" % section_name, generate_json(inst, mbeans))
    for section_name, mbeans_tups in MBEAN_SECTIONS.items():
        write_section("jolokia_%s" % section_name, generate_json(inst, mbeans_tups))

    write_section("jolokia_generic", generate_values(inst, inst.custom_vars))


def generate_jolokia_info(inst):
    # Determine type of server
    try:
        data = fetch_var(inst, "version", "")
    except (SkipInstance, SkipMBean) as exc:
        yield inst.name, "ERROR", str(exc)
        raise SkipInstance(exc)

    info = data.get("info", {})
    version = info.get("version", "unknown")
    product = info.get("product", "unknown")
    if inst.product is not None:
        product = inst.product
    else:
        inst.product = product

    agentversion = data.get("agent", "unknown")
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


def generate_json(inst, mbeans):
    for mbean in mbeans:
        try:
            data = inst.get_post_data(mbean, "read", use_target=True)
            obj = inst.post(data)
            yield inst.name, mbean, json.dumps(obj["value"])
        except (IOError, socket.timeout):
            raise SkipInstance()
        except SkipMBean:
            pass
        except Exception:
            if DEBUG:
                raise


def yield_configured_instances(custom_config=None):
    custom_config = load_config(custom_config)

    # Generate list of instances to monitor. If the user has defined
    # instances in his configuration, we will use this (a list of dicts).
    individual_configs = custom_config.pop("instances", [{}])
    for cfg in individual_configs:
        keys = set(cfg.keys()) | set(custom_config.keys())
        conf_dict = dict((k, cfg.get(k, custom_config.get(k))) for k in keys)
        if VERBOSE:
            sys.stderr.write("DEBUG: configuration: %r\n" % conf_dict)
        yield conf_dict


def load_config(custom_config):
    if custom_config is None:
        custom_config = get_default_config_dict()

    conffile = os.path.join(os.getenv("MK_CONFDIR", "/etc/check_mk"), "jolokia.cfg")
    if os.path.exists(conffile):
        exec(open(conffile).read(), {}, custom_config)  # pylint:disable=consider-using-with
    return custom_config


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
