$CMK_VERSION = "2.1.0p2"
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

Write-Host '<<<iis_app_pool_state:sep(124)>>>'
$AppPools = get-counter -Counter "\APP_POOL_WAS(*)\Current Application Pool State"
Foreach ($AppPool in $AppPools.CounterSamples){
   if ($AppPool.InstanceName -eq "_total") {
      continue
}
   Write-Host $AppPool.InstanceName"|"$AppPool.CookedValue
}
