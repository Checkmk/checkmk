# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Starts and drives the Windows test VMs under QEMU.

machine: the one QEMU command line, shared by everything that starts a VM.
qemu: one QEMU process and its QMP connection (qmp).
qga: the guest agent (qemu-ga), over the same protocol as QMP.
guest: commands and files in the guest, through its agent.
session: commands in the guest's autologon console session.
"""
