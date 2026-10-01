/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

const OPEN_STORAGE_KEY = 'cmk-ai-assistant-open'
const POSITION_STORAGE_KEY = 'cmk-ai-assistant-position'
const PANEL_SIZE = '300px'
const DOCK_POSITIONS = ['left', 'right', 'bottom']

function isOpen(): boolean {
  return sessionStorage.getItem(OPEN_STORAGE_KEY) === 'true'
}

function storedPosition(): string {
  const stored: unknown = JSON.parse(localStorage.getItem(POSITION_STORAGE_KEY) ?? 'null')
  return typeof stored === 'string' && DOCK_POSITIONS.includes(stored) ? stored : 'right'
}

export function reserve_panel_space_before_first_paint() {
  try {
    if (!isOpen()) {
      return
    }
    document.documentElement.style.setProperty(`--main-area-inset-${storedPosition()}`, PANEL_SIZE)
  } catch {
    return
  }
}
