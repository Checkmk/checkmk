#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
This program sets and removes downtimes on hosts and services
via command line. If you run this script from within an OMD
site then most options will be guessed automatically. Currently
the script only supports cookie based login - no HTTP basic
authentication.
---
Before you use this script, please read:
https://checkmk.de/cms_legacy_multisite_automation.html
---
You need to create an automation user - best with the name 'automation'
- and make sure that this user either has the admin role or is contact
for all relevant objects.
"""
import argparse
import datetime
import json
import logging
import os
import sys
import textwrap
import traceback
import urllib.request
from typing import List, Literal, NamedTuple, Optional

VERBOSITY = {
    0: logging.WARNING,
    1: logging.INFO,
    2: logging.DEBUG,
}


class ApiSettings(NamedTuple):
    API_URL: str
    USERNAME: str
    PASSWORD: str


DowntimeMode = Literal[
    "host",
    "service",
    "hostgroup",
    "servicegroup",
]  # yapf: disable


def _set_downtime(
    api: ApiSettings,
    mode: DowntimeMode,
    host_or_group: str,
    services: List[str],
    start_time: str,
    end_time: str,
    duration=None,
    comment=None,
):
    keys = {
        "downtime_type": mode,
        "start_time": start_time,
        "end_time": end_time,
        "comment": comment,
    }

    if duration:
        keys["duration"] = duration

    # Somewhat host specific. No need to introduce another concept to the user.
    if services and mode == "host":
        mode = "service"

    if mode == "host":
        keys["host_name"] = host_or_group
    elif mode == "service":
        keys.update(
            {
                "downtime_type": "service",
                "host_name": host_or_group,
                "service_descriptions": services,
            }
        )
    elif mode == "hostgroup":
        keys["hostgroup_name"] = host_or_group
    elif mode == "servicegroup":
        keys["servicegroup_name"] = host_or_group
    else:
        raise RuntimeError(f"Unsupported downtime mode: {mode!r}")

    request = urllib.request.Request(
        f"{api.API_URL}/domain-types/downtime/collections/{mode}",
        method="POST",
        headers={
            "Authorization": f"Bearer {api.USERNAME} {api.PASSWORD}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        data=json.dumps(keys).encode("utf-8"),
    )
    try:
        response = urllib.request.urlopen(request)
    except urllib.error.HTTPError as e:
        response_msg = f"{e.code}: {e.msg}"
    else:
        response_msg = f"{response.status}: {response.msg}"
    print(response_msg)


def _remove_downtime(
    api: ApiSettings,
    downtime_id=None,
    host=None,
    services=None,
):
    if downtime_id:
        keys = {
            "delete_type": "by_id",
            "downtime_id": downtime_id,
        }
    elif host and services:
        keys = {
            "delete_type": "params",
            "hostname": host,
            "services": services,
        }
    elif host:
        keys = {"delete_type": "params", "hostname": host}
    elif services:
        raise RuntimeError(
            f"Unsupported downtime remove action: host must be specified for {services}"
        )
    else:
        raise RuntimeError("Must specify")

    request = urllib.request.Request(
        f"{api.API_URL}/domain-types/downtime/actions/delete/invoke",
        method="POST",
        headers={
            "Authorization": f"Bearer {api.USERNAME} {api.PASSWORD}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        data=json.dumps(keys).encode("utf-8"),
    )
    try:
        response = urllib.request.urlopen(request)
    except urllib.error.HTTPError as e:
        response_msg = f"{e.code}: {e.msg}"
    else:
        response_msg = f"{response.status}: {response.msg}"
    print(response_msg)


class MultilineFormatter(argparse.HelpFormatter):
    """Wrap the text automatically, but allow to insert manual paragraph breaks."""

    def _fill_text(self, text, width, indent):
        text = self._whitespace_matcher.sub(" ", text).strip()
        paragraphs = text.split(" --- ")
        multiline_text = ""
        for paragraph in paragraphs:
            formatted_paragraph = (
                textwrap.fill(paragraph, width, initial_indent=indent, subsequent_indent=indent)
                + "\n\n"
            )
            multiline_text = multiline_text + formatted_paragraph
        return multiline_text


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=MultilineFormatter,
    )
    omd_root = os.getenv("OMD_ROOT")
    omd_site = os.getenv("OMD_SITE")
    parser.set_defaults(
        action="set",
        base_url=f"http://localhost/{omd_site}/check_mk/" if omd_site else None,
        comment="Automatic downtime",
        duration=None,
        host=None,
        mode="host",
        user="automation",
        verbosity=0,
    )
    parser.add_argument(
        "host",
        type=str,
        metavar="HOST_OR_GROUP",
        help="Can be a host, hostgroup or a servicegroup. See --mode for the master switch.",
    )
    parser.add_argument(
        "services",
        type=str,
        metavar="SERVICE",
        nargs="*",
        help="For servicegroups these options are ignored.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbosity",
        action="count",
        help="Show what's going on (specify multiple times for more verbose output)",
    )
    actions = parser.add_argument_group(
        description="The main actions:"
    ).add_mutually_exclusive_group()
    actions.add_argument(
        "-s",
        "--set",
        dest="action",
        action="store_const",
        const="set",
        help="Set downtime (this is the default)",
    )
    actions.add_argument(
        "-r",
        "--remove",
        dest="action",
        action="store_const",
        const="remove",
        help="Remove all downtimes from that host/service",
    )

    def iso_regex(arg_value):
        try:
            datetime.datetime.fromisoformat(arg_value.replace("Z", "+00:00"))
        except ValueError:
            raise RuntimeError("Invalid datetime specified: must conform to ISO 8601 format")
        return arg_value

    setting = parser.add_argument_group(description="When setting downtimes, these can be used:")
    setting.add_argument(
        "--start",
        dest="start_time",
        help="The start time of the downtime. Must conform to the "
        "ISO 8601 format: 2021-07-21T17:32:28Z",
        type=iso_regex,
    )
    setting.add_argument(
        "--end",
        dest="end_time",
        help="The end time of the downtime. Must conform to the "
        "ISO 8601 format: 2021-07-21T17:32:28Z",
        type=iso_regex,
    )
    setting.add_argument(
        "--mode",
        dest="mode",
        choices=["host", "hostgroup", "servicegroup"],
        help="How to interpret the HOST_OR_GROUP argument. (default: %(default)r)",
    )
    setting.add_argument(
        "-d",
        "--duration",
        type=int,
        help="Duration of the downtime in minutes (default: %(default)s)",
    )
    setting.add_argument(
        "-c", "--comment", type=str, help="Comment for the downtime (default: %(default)r)"
    )

    removing = parser.add_argument_group(description="When removing downtimes, these can be used:")
    removing.add_argument(
        "--id",
        dest="downtime_id",
        type=int,
        help="Remove a specific downtime using its id. This has priority over specified host name and services",
    )

    def api_url(value: str) -> Optional[str]:
        """Check for validity of the supplied API URL."""
        if not value.endswith("/check_mk"):
            return None
        return value

    parser.add_argument(
        "-U",
        "--url",
        type=api_url,
        dest="base_url",
        help="Base-URL of Multisite (default: guess local OMD site, fail if not possible).",
    )
    credentials = parser.add_argument_group(description="Credential options:")
    credentials.add_argument(
        "-u", "--user", type=str, help="Name of automation user (default: %(default)r)"
    )
    credentials.add_argument(
        "-S", "--secret", type=str, help="Automation secret (default: read from user settings)"
    )
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
    args = parser.parse_args()
    # More error handling.
    if args.base_url is None:
        parser.error(
            "-U, --url: Please give a valid URL. The automation URL must end with /check_mk/"
        )

    def _read_secret(username: str) -> str:
        with open(f"{omd_root or ''}/var/check_mk/web/{username}/automation.secret") as secret:
            return secret.read().strip()

    if not args.secret:
        try:
            # We try to figure the password out by ourselves.
            args.secret = _read_secret(args.user)
        except IOError:
            if args.verbosity > 0:
                traceback.print_exception(*sys.exc_info(), file=sys.stderr)
                print(file=sys.stderr)  # newline
            parser.error(
                f"-S, --secret: Cannot read automation secret (give -v for stacktrace). "
                f"Please specify the automation secret for the user '{args.user}'."
            )
    manage_downtime(args)


def _get_api_settings(username, secret, url) -> ApiSettings:
    api_url = f"{url}/api/1.0"
    return ApiSettings(
        API_URL=api_url,
        USERNAME=username,
        PASSWORD=secret,
    )


def manage_downtime(args: argparse.Namespace):
    logging.basicConfig(level=VERBOSITY[min(args.verbosity, 2)])
    api = _get_api_settings(args.user, args.secret, args.base_url)
    if args.action == "set":
        if not args.start_time or not args.end_time:
            raise RuntimeError(
                f"Time frame for downtime must be specified: both start and end times must be set"
            )
        output("Mode", "set downtime")
        output("Start time", f"{args.start_time}")
        output("End time", f"{args.end_time}")
        output("Duration", f"{args.duration} minutes")
    elif args.action == "remove":
        output("Mode", "remove downtimes")
    output("Host", args.host)
    if args.services:
        output("Services", " ".join(f'"{_service}"' for _service in args.services))
    output("Multisite-URL", args.base_url)
    output("User", args.user)
    output("Secret", args.secret or "(none specified)")
    if args.action == "set":
        _set_downtime(
            api,
            args.mode,
            args.host,
            args.services,
            args.start_time,
            args.end_time,
            duration=args.duration,
            comment=args.comment,
        )
    elif args.action == "remove":
        _remove_downtime(
            api,
            args.downtime_id,
            args.host,
            args.services,
        )
    else:
        raise RuntimeError(f"No action specified: must be --set or --remove")


def output(title: str, message: str, level: int = 1) -> str:
    """Give out some info.
    Examples:
    >>> output("Host", "foo", 0)
    'Host:           foo'
    >>> output("Duration", "foo", 0)
    'Duration:       foo'
    """
    msg = f"{title}:{' ' * (15 - len(title))}{message}"
    logging.log(VERBOSITY[level], msg)
    return msg


if __name__ == "__main__":
    main()
