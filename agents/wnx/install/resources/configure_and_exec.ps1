# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Script to correctly configure defaults for other powershel scripts 

$executable = $args[0]
$OutputEncoding = [Console]::InputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
switch ( $args.count ) {
    0 {}
    1 { & "$executable" }
    2 { & "$executable" $args[1] }
    3 { & "$executable" $args[1] $args[2] }
    4 { & "$executable" $args[1] $args[2] $args[3] }
    default {}
}
