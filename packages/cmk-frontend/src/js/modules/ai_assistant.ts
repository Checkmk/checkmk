/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

const OPEN_STORAGE_KEY = 'cmk-ai-assistant-open'
const PANEL_SIZE = '300px'

function isOpen(): boolean {
  return sessionStorage.getItem(OPEN_STORAGE_KEY) === 'true'
}

export function reserve_panel_space_before_first_paint() {
  try {
    if (!isOpen()) {
      return
    }
    document.documentElement.style.setProperty('--main-area-inset-right', PANEL_SIZE)
  } catch {
    return
  }
}
