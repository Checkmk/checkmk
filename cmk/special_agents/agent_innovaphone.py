#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import print_function
import sys
import base64
import urllib2
import xml.etree.ElementTree as etree


def get_informations(credentials, name, xml_id, org_name):
    server, address, user, password = credentials
    data_url = "/LOG0/CNT/mod_cmd.xml?cmd=xml-count&x="
    address = "http://%s%s%s" % (server, data_url, xml_id)
    c = False
    for line in etree.parse(get_url(address, user, password)).getroot():
        for child in line:
            if child.get('c'):
                c = child.get('c')
    if c:
        print("<<<%s>>>" % name)
        print(org_name + " " + c)


def get_pri_channel(credentials, channel_name):
    server, address, user, password = credentials
    data_url = "/%s/mod_cmd.xml" % channel_name
    address = "http://%s%s" % (server, data_url)
    data = etree.parse(get_url(address, user, password)).getroot()
    link = data.get('link')
    physical = data.get('physical')
    if link != "Up" or physical != "Up":
        print("%s %s %s 0 0 0" % (channel_name, link, physical))
        return
    idle = 0
    total = 0
    for channel in data.findall('ch'):
        if channel.get('state') == 'Idle':
            idle += 1
        total += 1
    total -= 1
    print("%s %s %s %s %s" % (channel_name, link, physical, idle, total))


def get_licenses(credentials):
    server, address, user, password = credentials
    address = "http://%s/PBX0/ADMIN/mod_cmd_login.xml" % server
    data = etree.parse(get_url(address, user, password)).getroot()
    for child in data.findall('lic'):
        if child.get('name') == "Port":
            count = child.get('count')
            used = child.get('used')
            print(count, used)
            break


def get_url(address, user, password):
    request = urllib2.Request(address)
    base64string = base64.encodestring('%s:%s' % (user, password)).replace('\n', '')
    request.add_header("Authorization", "Basic %s" % base64string)
    return urllib2.urlopen(request)


def main(sys_argv=None):
    if sys_argv is None:
        sys_argv = sys.argv[1:]

    if len(sys.argv) != 3:
        sys.stderr.write("usage: agent_innovaphone HOST USER PASSWORD\n")
        return 1

    server = sys_argv[0]
    user = sys_argv[1]
    password = sys_argv[2]

    base_url = "/LOG0/CNT/mod_cmd.xml?cmd=xml-counts"
    counter_address = "http://%s%s" % (server, base_url)

    credentials = (server, counter_address, user, password)

    p = etree.parse(get_url(counter_address, user, password))
    root_data = p.getroot()

    informations = {}
    for entry in root_data:
        n = entry.get('n')
        x = entry.get('x')
        informations[n] = x

    s_prefix = "innovaphone_"
    for what in ["CPU", "MEM", "TEMP"]:
        if informations.get(what):
            section_name = s_prefix + what.lower()
            get_informations(credentials, section_name, informations[what], what)

    print("<<<%schannels>>>" % s_prefix)
    for channel_num in range(1, 5):
        get_pri_channel(credentials, 'PRI' + str(channel_num))

    print("<<<%slicenses>>>" % s_prefix)
    get_licenses(credentials)
