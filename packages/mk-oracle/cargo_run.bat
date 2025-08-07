:: Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
:: This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
:: conditions defined in the file COPYING, which is part of this source code package.

::  imitates agent behavior: setup LD_LIBRARY_PATH to include the runtime library

@echo off
set "OLD_PATH=%PATH%"
set "PATH=%cd%\runtimes\oci_light_win_x64.zip;%PATH%"
cargo %*
set "PATH=%OLD_PATH%"

