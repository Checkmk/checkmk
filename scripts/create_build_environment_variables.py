#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

""" Creates sh/bash compatible lines to be sourced/evaled in order to set
enviroment variables with generic values.

Can be used to provide a system specific environment to be used as cache keys.

    NEW_ENV="$(create_build_environment_variables.py \
        env:PATH:"/opt/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
        pathhash:`which gcc` \
        pathhash:/usr/include \
        eval:"os-release-name":"cat /etc/os-release | grep PRETTY | cut -d '\"' -f2" \
    )"
    eval "$NEW_ENV"

will create something like this:

    # generated using create_build_environment_variables.py, don't modify directly
    export PATH="/opt/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    export SYSTEM_DIGEST="{
      'sha1sum:/usr/bin/gcc': '45e09f95d0ea3972a970324bab7ba532794591db',
      'sha1sum:/usr/include': 'b549c133b28035a22ffc2c202e621e630bf83dfc',
      'eval:os-release-name': 'Ubuntu 22.04.1 LTS'
    }"

The hash retrieved for an empty directory or non-existing files will be translated
to '--', in order make this fact visible.
"""

import json
import os
import sys
from subprocess import check_output, DEVNULL

assert sys.version_info.major == 3


def cmd_out(cmd, **args):
    return check_output(["sh", "-c", cmd], text=True, **args)


def main():
    print("# generated using create_build_environment_variables.py, don't modify directly")
    print(
        "\n".join(
            f'export {varname}="{value}"'
            for e in sys.argv[1:]
            for op, args in (e.split(":", 1),)
            if op == "env"
            for varname, value in (args.split(":", 1),)
        )
    )

    checksums = [
        (
            f"sha1sum:{path}",
            (
                cmd_out(
                    f"find $(realpath {path}) -type f -print0 | sort -z | xargs -0 sha1sum | sha1sum",
                    stderr=DEVNULL,
                )
                .split(" ", 1)[0]
                .replace("5cd337198ead0768975610a135e26257153198c7", "--")
                if os.path.exists(path)
                else "--"
            ),
        )
        for e in sys.argv[1:]
        for op, path in (e.split(":", 1),)
        if op == "pathhash"
    ]
    if checksums and all(v == "--" for k, v in checksums):
        raise RuntimeError(
            "All provided 'pathhash' items result in emtpy hashes."
            " This is considerd to be an error."
        )

    evals = [
        (f"eval:{name}", cmd_out(expr).strip())
        for e in sys.argv[1:]
        for op, args in (e.split(":", 1),)
        if op == "eval"
        for name, expr in (args.split(":", 1),)
    ]

    system_digest = json.dumps(dict(checksums + evals), indent=2).replace('"', "'")

    print(f'export SYSTEM_DIGEST="{system_digest}"')


if __name__ == "__main__":
    main()
