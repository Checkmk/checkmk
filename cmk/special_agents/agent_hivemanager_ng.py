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

from __future__ import print_function

import argparse
import sys
import traceback

import requests


def bail_out(message, debug=False):
    if debug:
        print('----------------------------------\n', file=sys.stderr, end='')
        print(traceback.format_exc(), file=sys.stderr, end='')
        print('==================================\n', file=sys.stderr)
    print('Error: %s\n' % message, file=sys.stderr)
    sys.exit(1)


class ArgParser(argparse.ArgumentParser):
    # Use custom behaviour on error
    def error(self, message):
        bail_out('Parsing the arguments failed - %s.' % message)


def parse_args():
    parser = ArgParser(description='Special agent to retrieve data from Aerohive HiveManagerNG')
    parser.add_argument('-d', '--debug', help='enable debugging', action='store_true')
    parser.add_argument('url', help='URL to Aerohive NG, e.g. https://cloud.aerohive.com')
    parser.add_argument('vhm_id', help='Numericl ID of the VHM e.g. 102')
    parser.add_argument('api_token', help='API Access Token')
    parser.add_argument('client_id', help='Client ID')
    parser.add_argument('client_secret', help='Client secret')
    parser.add_argument('redirect_url', help='Redirect URL')
    return parser.parse_args()


def main():
    args = parse_args()

    print("<<<hivemanager_ng_devices:sep(124)>>>")

    address = "%s/xapi/v1/monitor/devices" % args.url
    params = {
        'ownerId': args.vhm_id,
        'pageSize': 1000,  # the agent will deliver at most 1000 devices
    }
    headers = {
        "Authorization": "Bearer %s" % args.api_token,
        "X-AH-API-CLIENT-ID": args.client_id,
        "X-AH-API-CLIENT-SECRET": args.client_secret,
        "X-AH-API-CLIENT-REDIRECT-URI": args.redirect_url,
        "Content-Type": "application/json",
    }

    try:
        response = requests.get(address, headers=headers, params=params)
    except requests.RequestException as e:
        bail_out(
            'Request to the API failed. Please check your connection settings. '
            'A guide to setup the API can be found on the Aerohive homepage.', args.debug)

    try:
        json = response.json()
    except ValueError as e:
        bail_out(e.message, args.debug)

    if json['error']:
        bail_out(
            'Error in JSON response. Please check your connection settings. '
            'A guide to setup the API can be found on the Aerohive '
            'homepage.', args.debug)

    used = {
        'hostName',
        'connected',
        'activeClients',
        'ip',
        'serialId',
        'osVersion',
        'lastUpdated',
    }

    for device in json['data']:
        device_txt = "|".join(["%s::%s" % (k, v) for (k, v) in device.items() if k in used])
        print(device_txt)
