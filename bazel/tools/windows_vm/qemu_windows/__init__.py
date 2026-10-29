# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Starts and drives the Windows test VMs under QEMU.

machine: the one QEMU command line, shared by everything that starts a VM.
qemu: one QEMU process and its QMP connection (qmp).
qga: the guest agent (qemu-ga), over the same protocol as QMP.
guest: commands and files in the guest, through its agent.
session: commands in the guest's autologon console session.
state: resuming a saved test VM.
host_cpu: whether the host CPU still matches a saved state's fingerprint.
console: PowerShell on the serial console, through Windows' SAC.
process: the setup of a program that runs a QEMU.
"""
