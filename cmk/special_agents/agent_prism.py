#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import urllib2
from httplib import HTTPConnection, HTTPSConnection
import base64
import ssl
import csv
import sys
import os
import json

field_separator = "\t"
# set once parameters have been parsed
base_url = None


class HTTPSConfigurableConnection(HTTPSConnection):

    IGNORE = "__ignore"

    def __init__(self, host, ca_file=None):
        HTTPSConnection.__init__(self, host)
        self.__ca_file = ca_file

    def connect(self):
        if not self.__ca_file:
            HTTPSConnection.connect(self)
        else:
            HTTPConnection.connect(self)
            if self.__ca_file == HTTPSConfigurableConnection.IGNORE:
                self.sock = ssl.wrap_socket(self.sock, cert_reqs=ssl.CERT_NONE)
            else:
                self.sock = ssl.wrap_socket(self.sock,
                                            ca_certs=self.__ca_file,
                                            cert_reqs=ssl.CERT_REQUIRED)


class HTTPSAuthHandler(urllib2.HTTPSHandler):
    def __init__(self, ca_file):
        urllib2.HTTPSHandler.__init__(self)
        self.__ca_file = ca_file

    def https_open(self, req):
        return self.do_open(self.get_connection, req)

    def get_connection(self, host, timeout):
        return HTTPSConfigurableConnection(host, ca_file=self.__ca_file)


def flatten(d, separator="."):
    """
    recursively flatten dictionaries/lists. The result is a dictionary
    with no nested dicts or lists and each element is a path using the
    specified separator
    """
    def flatten_int(d, separator="."):
        result = []
        if isinstance(d, list):
            counter = 0
            for i in d:
                for k, v in flatten_int(i):
                    if k is not None:
                        k = "%d%s%s" % (counter, separator, k)
                    else:
                        k = counter
                    result.append((k, v))

                counter += 1
        elif isinstance(d, dict):
            for k, v in d.iteritems():
                for sub_k, sub_v in flatten_int(v):
                    if sub_k is not None:
                        sub_k = "%s%s%s" % (k, separator, sub_k)
                    else:
                        sub_k = k
                    result.append((sub_k, sub_v))
        else:
            result.append((None, d))
        return result

    return dict(flatten_int(d, separator))


def gen_headers(username, password):
    auth = base64.encodestring("%s:%s" % (username, password)).strip()

    return {'Authorization': "Basic " + auth}


def gen_csv_writer():
    return csv.writer(sys.stdout, delimiter=field_separator)


def write_title(section):
    sys.stdout.write("<<<prism_%s:sep(%d)>>>\n" % (section, ord(field_separator)))


def send_request(opener, path, headers, parameters=None):
    url = "%s/PrismGateway/services/rest/v1/%s/" % (base_url, path)
    if parameters is not None:
        url = "%s?%s" % (url, "&".join(["%s=%s" % par for par in parameters.iteritems()]))
    req = urllib2.Request(url, headers=headers)
    response = opener.open(req)
    res = response.read()
    # TODO: error handling
    return json.loads(res)


def output_containers(opener, headers):
    write_title("containers")
    obj = send_request(opener, "containers", headers)

    writer = gen_csv_writer()
    writer.writerow(["name", "usage", "capacity"])

    for entity in obj['entities']:
        writer.writerow([
            entity['name'], entity['usageStats']['storage.user_usage_bytes'],
            entity['usageStats']['storage.user_capacity_bytes']
        ])


def output_alerts(opener, headers):
    write_title("alerts")
    obj = send_request(opener,
                       "alerts",
                       headers,
                       parameters={
                           'resolved': "false",
                           'acknowledged': "false"
                       })

    writer = gen_csv_writer()
    writer.writerow(["timestamp", "message", "severity"])

    for entity in obj['entities']:
        # The message is stored as a pattern with placeholders, the
        # actual values are stored in context_values, the keys in
        # context_types
        context = zip(entity['contextTypes'], entity['contextValues'])
        # We have seen informational messages in format:
        # {dev_type} drive {dev_name} on host {ip_address} has the following problems: {err_msg}
        # In this case the keys have no values so we can not assign it to the message
        # To handle this, we output a message without assigning the keys
        try:
            message = entity['message'].format(**dict(context))
        except KeyError:
            message = entity['message']
        writer.writerow([entity['createdTimeStampInUsecs'], message, entity['severity']])


def output_cluster(opener, headers):
    write_title("info")
    obj = send_request(opener, "cluster", headers)

    writer = gen_csv_writer()
    writer.writerow(["name", "version"])
    writer.writerow([obj['name'], obj['version']])


def output_storage_pools(opener, headers):
    write_title("storage_pools")
    obj = send_request(opener, "storage_pools", headers)

    writer = gen_csv_writer()
    writer.writerow(["name", "usage", "capacity"])

    for entity in obj["entities"]:
        writer.writerow([
            entity["name"],
            entity["usageStats"]["storage.usage_bytes"],
            entity["usageStats"]["storage.capacity_bytes"],
        ])


def main():
    if os.path.basename(__file__) == "mk_prism.py":
        settings = {'port': 9440}
        cfg_path = os.path.join(os.getenv("MK_CONFDIR", "/etc/check_mk"), "prism.cfg")
        if os.path.isfile(cfg_path):
            exec (open(cfg_path).read(), settings, settings)
    else:
        from optparse import OptionParser
        parser = OptionParser()
        parser.add_option("--server", help="host to connect to")
        parser.add_option("--port", default=9440, type="int", help="tcp port")
        parser.add_option("--username", help="user account on prism")
        parser.add_option("--password", help="password for that account")
        options, _args = parser.parse_args()
        settings = vars(options)

    if (settings.get('server') is None or settings.get('username') is None or
            settings.get('password') is None):
        sys.stderr.write(
            'usage: agent_prism --server SERVER --username USER --password PASSWORD [--port PORT]\n'
        )
        sys.exit(1)

    req_headers = gen_headers(settings['username'], settings['password'])

    global base_url
    base_url = "https://%s:%d" % (settings['server'], settings['port'])

    opener = urllib2.build_opener(HTTPSAuthHandler(HTTPSConfigurableConnection.IGNORE))
    output_containers(opener, req_headers)
    output_alerts(opener, req_headers)
    output_cluster(opener, req_headers)
    output_storage_pools(opener, req_headers)
