#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""msi-install-qemu: installs the built check_mk_agent.msi in a Windows test
VM, checks that the agent answers on 6556, uninstalls it and checks that it
is gone.

msiexec's machine installs need the guest's elevated session. Its install
and uninstall logs are collected for triage.

The guest gets msi_install_qemu_stage (BUILD) and runs msi-install-qemu.ps1;
see qemu_windows/tier.py for how.

Usage: msi_install_qemu.py <Product.wxs>
"""

import re
import sys
from pathlib import Path

from qemu_windows import tier


def main(argv: list[str]) -> int:
    (product_wxs,) = map(Path, argv)
    # Every build gets a new ProductCode (Product Id="*"); the UpgradeCode
    # is what identifies an installed agent of any build.
    if not (found := re.search(r'define ProductUpgradeCode = "([^"]*)"', product_wxs.read_text())):
        sys.stderr.write(f"error: no ProductUpgradeCode in {product_wxs}\n")
        return 1
    return tier.run(
        "msi",
        script="msi-install-qemu.ps1",
        args=["-ProductUpgradeCode", found[1]],
        collect=["install.log", "uninstall.log"],
    )


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
