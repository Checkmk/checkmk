/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { add_class, remove_class } from './utils'

const OPEN_STORAGE_KEY = 'cmk-ai-assistant-open'
const TRIGGER_ID = 'popup_trigger_main_menu_ai_assistant'

function isOpen(): boolean {
  return sessionStorage.getItem(OPEN_STORAGE_KEY) === 'true'
}

function updateTriggerState(open: boolean) {
  const trigger = document.getElementById(TRIGGER_ID)
  if (!trigger) return
  if (open) {
    add_class(trigger, 'active')
  } else {
    remove_class(trigger, 'active')
  }
}

export function toggle() {
  const open = !isOpen()
  sessionStorage.setItem(OPEN_STORAGE_KEY, JSON.stringify(open))
  updateTriggerState(open)
  // Placeholder until the AI assistant panel exists
  console.log(`AI assistant ${open ? 'shown' : 'hidden'}`)
}

export function initialize() {
  updateTriggerState(isOpen())
}
