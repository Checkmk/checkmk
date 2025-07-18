#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Check_MK Special agent to monitor JMX using Mbeans exposed by jolokia"""

import argparse
import sys

# TODO: is there a better way to do this?
import cmk.utils.paths
from cmk.special_agents.v0_unstable.misc import vcrtrace
from cmk.utils.password_store import replace_passwords

sys.path.append(str(cmk.utils.paths.local_agents_dir / "plugins"))
sys.path.append(str(cmk.utils.paths.agents_dir / "plugins"))
import mk_jolokia

__version__ = "2.5.0b1"

USER_AGENT = "checkmk-special-jolokia-" + __version__


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("-v", "--verbose", action="count", help="""Verbose mode""")
    parser.add_argument(
        "--debug", action="store_true", help="Debug mode: let python exceptions come through"
    )
    parser.add_argument(
        "--vcrtrace", action=vcrtrace(**mk_jolokia.JolokiaInstance.FILTER_SENSITIVE)
    )

    opts_with_help: list[tuple[str, str | None | float, str]] = [
        opt  # type: ignore[misc]
        for opt in mk_jolokia.DEFAULT_CONFIG_TUPLES
        if len(opt) == 3
    ]

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
        replace_passwords()
        sys_argv = sys.argv[1:]

    args = parse_arguments(sys_argv)
    config = mk_jolokia.get_default_config_dict()

    if args.no_cert_check:
        config["verify"] = False

    for key in config:
        if hasattr(args, key):
            config[key] = getattr(args, key)

    instance = mk_jolokia.JolokiaInstance(config, USER_AGENT)
    try:
        mk_jolokia.query_instance(instance)
    except mk_jolokia.SkipInstance:
        pass
