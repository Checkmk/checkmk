#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Check_MK Special agent to monitor JMX using Mbeans exposed by jolokia
"""
import argparse
import os
import sys
from typing import List

# TODO: is there a better way to do this?
import cmk.utils.paths

from cmk.special_agents.utils import vcrtrace

sys.path.append(str(cmk.utils.paths.local_agents_dir / "plugins"))
sys.path.append(os.path.join(cmk.utils.paths.agents_dir, "plugins"))
import mk_jolokia  # type:ignore  # pylint: disable=import-error,wrong-import-order


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("-v", "--verbose", action="count", help="""Verbose mode""")
    parser.add_argument(
        "--debug", action="store_true", help="Debug mode: let python exceptions come through"
    )
    parser.add_argument(
        "--vcrtrace", action=vcrtrace(**mk_jolokia.JolokiaInstance.FILTER_SENSITIVE)
    )

    opts_with_help: List[List[str]] = []
    for opt in mk_jolokia.DEFAULT_CONFIG_TUPLES:
        if len(opt) == 3:
            opts_with_help.append([str(elem) for elem in opt])

    for key, default, help_str in opts_with_help:
        if default is not None:
            help_str += " Default: %s" % default

        parser.add_argument("--%s" % key, default=default, help=help_str)

    # now add some arguments we cannot define in the way above:
    parser.add_argument(
        "--no-cert-check",
        action="store_true",
        help="""Skip SSL certificate verification (not recommended)""",
    )

    return parser.parse_args(argv)


def main(sys_argv=None):
    if sys_argv is None:
        sys_argv = sys.argv[1:]

    args = parse_arguments(sys_argv)
    config = mk_jolokia.get_default_config_dict()

    if args.no_cert_check:
        config["verify"] = False

    for key in config:
        if hasattr(args, key):
            config[key] = getattr(args, key)

    instance = mk_jolokia.JolokiaInstance(config)
    try:
        mk_jolokia.query_instance(instance)
    except mk_jolokia.SkipInstance:
        pass
