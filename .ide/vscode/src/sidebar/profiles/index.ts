/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { log } from '../../core/log'
import * as profileManager from '../../profiles/profileManager'
import { getNonce, wrap } from '../html'
import { getProfileSeverity } from '../overview/domainSummary'
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
      // Severity from the cockpit's view: builds + settings drift attributable to this profile.
      const sev = getProfileSeverity(state, p.name)
      const active = p.active
      const sevClass = sev === 'critical' ? 'sev-critical' : sev === 'warning' ? 'sev-warning' : ''
      const cls = `${active ? 'active' : 'inactive'} ${sevClass}`.trim()
      const icon =
        sev === 'critical'
          ? '&#10007;'
          : sev === 'warning'
            ? '&#9888;'
            : active
              ? '&#10003;'
              : '&#9675;'
      const badge =
        sev === 'critical'
          ? active
            ? 'CRIT'
            : 'CRIT · OFF'
          : sev === 'warning'
            ? active
              ? 'WARN'
              : 'WARN · OFF'
            : active
              ? 'ON'
              : 'OFF'
      return `<div class="card profile ${cls}" data-action="toggle-profile" data-id="${p.name}">
      <span class="card-icon">${icon}</span>
      <span class="card-label">${p.label} <i>(${p.fullName})</i></span>
      <span class="card-badge">${badge}</span>
    </div>`
    })
    .join('')

  return wrap(nonce, sectionCss, cards)
}
