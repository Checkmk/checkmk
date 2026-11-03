/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import {
  abortrepeat,
  activate_tracking,
  clearData,
  nukeDataFromOrbit,
  repeat
} from './modules/tracking'

function help() {
  console.warn(`Available commands:
help()              - Show this help.
clearData()         - Clear all performance data for the current url.
nukeDataFromOrbit() - Clear all performance data for ALL(!) urls.
repeat(integer)     - Repeat the current page $integer times. First reload needs to be done manually.
                      After every reload, the counter is decreased by 1. Once it reaches 0, the
                      reloads will stop.
abortrepeat()       - Abort the current repeat cycle.
`)
}

const startTime = Date.now()

document.addEventListener('DOMContentLoaded', () => {
  const data = document.getElementById('cmk_tracking_data')
  if (!data) return
  const generationDuration = JSON.parse(data.textContent ?? '{}').generation_duration ?? 0
  const currentUrl = window.location.pathname + window.location.search
  activate_tracking(currentUrl, startTime, generationDuration)
})

const siteName = window.location.pathname.split('/')[1]
console.warn(
  'Tracking code enabled. See results at ' +
    window.location.origin +
    `/${siteName}/check_mk/gui_timings.py`
)

export const cmk_export = {
  help: help,
  clearData: clearData,
  nukeDataFromOrbit: nukeDataFromOrbit,
  repeat: repeat,
  abortrepeat: abortrepeat
}
