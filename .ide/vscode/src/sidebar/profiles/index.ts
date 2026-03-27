/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { log } from '../../core/log'
import * as profileManager from '../../profiles/profileManager'
import { getNonce, wrap } from '../html'
import type { SectionContext, StateCache, WebviewMessage } from '../types'
import sectionCss from './style.css'

export async function handleMessage(
  msg: WebviewMessage,
  { refreshAll }: SectionContext
): Promise<boolean> {
  switch (msg.type) {
    case 'toggleProfile':
      log(`Toggle profile: ${msg.name}`)
      profileManager.setLoading(msg.name as string, true)
      refreshAll()
      await profileManager.toggle(msg.name as string)
      refreshAll()
      return true
    default:
      return false
  }
}

export function render(state: StateCache): string {
  const nonce = getNonce()
  const { profiles } = state

  const cards = profiles
    .map((p) => {
      if (p.loading) {
        return `<div class="card profile loading">
        <span class="card-icon spinner">&#8635;</span>
        <span class="card-label">${p.label} <i>(${p.fullName})</i></span>
        <span class="card-badge">…</span>
      </div>`
      }
      const cls = p.active ? 'active' : 'inactive'
      const icon = p.active ? '&#10003;' : '&#9675;'
      return `<div class="card profile ${cls}" data-action="toggle-profile" data-id="${p.name}">
      <span class="card-icon">${icon}</span>
      <span class="card-label">${p.label} <i>(${p.fullName})</i></span>
      <span class="card-badge">${p.active ? 'ON' : 'OFF'}</span>
    </div>`
    })
    .join('')

  return wrap(nonce, sectionCss, cards)
}
