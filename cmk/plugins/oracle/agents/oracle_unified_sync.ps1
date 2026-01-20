# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

$CMK_VERSION = "2.6.0b1"

if (-not $env:MK_LIBDIR -or -not (Test-Path -Path $env:MK_LIBDIR -PathType Container)) {
    Write-Host "MK_LIBDIR is not set or not directory"
    exit 1
}

if (-not (Test-Path -Path (Join-Path $env:MK_LIBDIR 'mk-oracle.exe') -PathType Leaf)) {
    Write-Host "mk-oracle.exe in $env:MK_LIBDIR is not executable or not found"
    exit 1
}

if (-not $env:MK_CONFDIR -or -not (Test-Path -Path $env:MK_CONFDIR -PathType Container)) {
    Write-Host "MK_CONFDIR is not set or not directory"
    exit 1
}

if (-not (Test-Path -Path (Join-Path $env:MK_CONFDIR 'oracle.yml') -PathType Leaf)) {
    Write-Host "Configuration file oracle.yml not found in $env:MK_CONFDIR"
    exit 1
}

& $env:MK_PLUGINSDIR\packages\mk-oracle\mk-oracle.exe -c $env:MK_CONFDIR/oracle.yml --filter sync
