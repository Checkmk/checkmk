#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""agent_jolokia

Checkmk special agent for monitoring JMX using Mbeans exposed by jolokia.
"""

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

import argparse
import sys
from contextlib import suppress

import cmk.utils.paths
from cmk.password_store.v1_unstable import parser_add_secret_option, resolve_secret_option
from cmk.server_side_programs.v1_unstable import vcrtrace

# TODO: is there a better way to do this?
# yes there is. Migrate bakery plugin; cleanup; problem goes away.
sys.path.append(str(cmk.utils.paths.local_agents_dir / "plugins"))
sys.path.append(str(cmk.utils.paths.agents_dir / "plugins"))
import mk_jolokia

__version__ = "2.6.0b1"

USER_AGENT = "checkmk-special-jolokia-" + __version__


def parse_arguments(argv):
    prog, description = __doc__.split("\n\n", maxsplit=1)
    parser = argparse.ArgumentParser(prog=prog, description=description)

    parser.add_argument("-v", "--verbose", action="count", help="""Verbose mode""")
    parser.add_argument(
        "--debug", action="store_true", help="Debug mode: let python exceptions come through"
    )
    parser.add_argument(
        "--vcrtrace",
        action=vcrtrace(filter_headers=mk_jolokia.JolokiaInstance.FILTER_HEADERS),
    )
    parser_add_secret_option(
        parser,
        long=f"--{mk_jolokia.PASSWORD_OPTION}",
        help="Password for authentication",
        required=False,
    )

    opts_with_help: list[tuple[str, str | None | float, str]] = [
        (key, default, help_[0])  # type: ignore[misc]
        for key, default, *help_ in mk_jolokia.DEFAULT_CONFIG_TUPLES
        if help_ and key != mk_jolokia.PASSWORD_OPTION
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
        sys_argv = sys.argv[1:]

    args = parse_arguments(sys_argv)
    config = mk_jolokia.get_default_config_dict()

    if args.no_cert_check:
        config["verify"] = False

    for key in config:
        if key == mk_jolokia.PASSWORD_OPTION:
            with suppress(TypeError):
                config[key] = resolve_secret_option(args, mk_jolokia.PASSWORD_OPTION).reveal()
        else:
            with suppress(AttributeError):
                config[key] = getattr(args, key)

    instance = mk_jolokia.JolokiaInstance(config, USER_AGENT)
    try:
        mk_jolokia.query_instance(instance)
    except mk_jolokia.SkipInstance:
        pass


if __name__ == "__main__":
    main(sys.argv[1:])
