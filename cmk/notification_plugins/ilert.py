# !/usr/bin/env python3
# iLert Check_MK Native Plugin
# -*- coding: utf-8; py-ident-offset: 4 -*-

# Copyright (c) 2013-2020, iLert GmbH. <support@ilert.com>
# All rights reserved.


import sys
import json
import argparse
import datetime
from http.client import responses
import requests

from cmk.notification_plugins import utils

PLUGIN_VERSION = "1.0"


def log(level, message):
    date = datetime.datetime.now().isoformat()
    sys.stdout.write("%s %s %s\n" % (date, level, message))


def send(endpoint, port, apikey, context):

    headers = {"Content-type": "application/json",
               "Accept": "application/json",
               "Agent": "checkmk/extension/%s" % PLUGIN_VERSION}

    url = "%s:%s/api/v1/events/checkmk-ext/%s" % (endpoint, port, apikey)

    try:
        response = requests.post(url,
                                 data=json.dumps(context),
                                 headers=headers,
                                 timeout=60)
    except requests.HTTPError as e:
        if e.code == 429:
            log("WARNING", "Too many requests, will try later. Server response: %s" % e.read())
            sys.exit(1)
        elif e.code in range(400,499):
            log("WARNING", "Event not accepted by iLert. Reason: %s" % e.read())
        elif e.code in range(500,599):
            log("WARNING", "Server error by iLert.\nError Code: %s, reason: %s, %s" % (
                e.code, e.reason, e.read()))
        else:
            log("ERROR",
                "Could not send event to iLert.\nError Code: %s, reason: %s, %s" % (e.code, e.reason, e.read()))
            sys.exit(1)
    except Exception as e:
        log("ERROR", "an unexpected error occurred. Please report a bug. Cause: %s %s" % (
            type(e), e.args))
        sys.exit(1)
    else:
        status_code = response.status_code
        status_readable = responses[status_code]
        status_text = response.json()
        sys.stderr.write(
            "IncidentKey: %s\n%s - %s" % (status_text['incidentKey'], status_code, status_readable))


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='send events from CheckMK to iLert')
    parser.add_argument('-a',
                        '--apikey',
                        help='API key for the alert source in iLert')
    parser.add_argument('-e',
                        '--endpoint',
                        default='https://api.ilert.com',
                        help='iLert API endpoint (default: %(default)s)')
    parser.add_argument('-p',
                        '--port',
                        type=int,
                        default=443,
                        help='endpoint port (default: %(default)s)')
    parser.add_argument('--version',
                        action='version',
                        version=PLUGIN_VERSION)
    parser.add_argument('payload',
                        nargs=argparse.REMAINDER,
                        help='event payload as key value pairs in the format key1=value1 key2=value2 ...')
    args = parser.parse_args(argv)

    context = utils.collect_context()

    if not args.apikey:
        try:
            apikey = utils.retrieve_from_passwordstore(context['PARAMETER_ILERT_API_KEY'])
        except ValueError:
            log("ERROR",
                "parameter apikey is required in save mode and must be provided either via command line or in the pager field of the contact definition in CheckMK")
            sys.exit(1)
    else:
        apikey = args.apikey

    send(args.endpoint, args.port, apikey, context)

    sys.exit(0)


if __name__ == '__main__':
    sys.exit(main())
