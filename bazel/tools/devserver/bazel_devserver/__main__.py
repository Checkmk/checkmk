# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Run a dev server target and rebuild it whenever its sources change.

Unlike iBazel, this also picks up files added while it runs, and it stops the
dev server with SIGINT, which lets ``js_run_devserver`` remove its sandbox.

Options given to the outer bazel run apply only to building this tool; give
those for the dev server with --bazel_build_option.
"""

import argparse
import logging
import os
import signal
import sys
from collections.abc import Sequence
from pathlib import Path

from bazel_devserver.dev_server import DevServer
from bazel_devserver.errors import DevServerError

_STOP_SIGNALS = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)


def _absolute_label(label: str) -> str:
    if not label.startswith(("//", "@")):
        raise argparse.ArgumentTypeError(f"not an absolute label: {label}")
    return label


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="bazel run //bazel/tools/devserver --",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "target",
        type=_absolute_label,
        help="absolute label of a dev server target that speaks the iBazel protocol",
    )
    parser.add_argument("args", nargs="*", help="arguments for the dev server, after a --")
    parser.add_argument(
        "--bazel_startup_option",
        action="append",
        default=[],
        metavar="OPTION",
        help="startup option for every bazel command",
    )
    parser.add_argument(
        "--bazel_build_option",
        action="append",
        default=[],
        metavar="OPTION",
        help="option for every bazel build and run",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    logging.basicConfig(  # astrein: disable=logging-formatter
        format="devserver: %(message)s", level=logging.INFO
    )
    if not (workspace := os.environ.get("BUILD_WORKSPACE_DIRECTORY")):
        sys.exit("devserver: run it with bazel run")
    # SIGINT stops the dev server, even where it was ignored, as for background jobs of a shell
    for signum in _STOP_SIGNALS:
        signal.signal(signum, signal.default_int_handler)
    dev_server = DevServer(
        Path(workspace),
        args.target,
        args.args,
        startup_options=args.bazel_startup_option,
        build_options=args.bazel_build_option,
    )
    try:
        dev_server.start()
        return dev_server.wait()
    except DevServerError as e:
        sys.exit(f"devserver: {e}")
    except KeyboardInterrupt:
        return 0
    finally:
        for signum in _STOP_SIGNALS:
            signal.signal(signum, signal.SIG_IGN)
        dev_server.stop()


if __name__ == "__main__":
    sys.exit(main())
