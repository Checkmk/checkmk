# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


class VmError(Exception):
    """A test VM that cannot be started or driven; the message says why.

    Where QEMU's own output explains it, the message ends with qemu.log.
    """
