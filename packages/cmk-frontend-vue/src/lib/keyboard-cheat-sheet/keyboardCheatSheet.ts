/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/** Mounts the keyboard cheat sheet (CMK-38372) once Alt+K, or a pin left from the last page, asks for it. */
import usei18n from 'cmk-ui-library/lib/i18n'
import { type KeyboardHelpKind, registerKeyboardHelp } from 'cmk-ui-library/lib/keyboardHelp'
import { createApp } from 'vue'

import { isCheatSheetVisible, subscribeCheatSheetVisible } from './cheatSheetKey'

/** Drop `'widget'` to hide the keys of the focused widgets. */
const KINDS: readonly KeyboardHelpKind[] = ['shortcut', 'widget', 'hint']

let requested = false

async function mount(): Promise<void> {
  const { _t } = usei18n()
  registerKeyboardHelp([
    {
      kind: 'shortcut',
      scope: _t('Keyboard'),
      combo: ['Alt', 'k'],
      description: _t('Show the cheat sheet and key hints, twice to pin')
    }
  ])
  const { default: sheet } = await import('./KeyboardCheatSheet.vue')
  const container = document.createElement('div')
  container.id = 'lib-keyboard-cheat-sheet-root'
  document.body.appendChild(container)
  createApp(sheet, { kinds: KINDS }).mount(container)
}

function mountOnce(): void {
  if (requested) {
    return
  }
  requested = true
  if (document.body) {
    void mount()
  } else {
    document.addEventListener('DOMContentLoaded', () => void mount(), { once: true })
  }
}

subscribeCheatSheetVisible((visible) => {
  if (visible) {
    mountOnce()
  }
})

if (isCheatSheetVisible()) {
  mountOnce()
}
