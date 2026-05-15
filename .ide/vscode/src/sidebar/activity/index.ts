/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as vscode from 'vscode'

import {
  type ActivityCategory,
  type ActivityEvent,
  clearActivityEvents,
  getActivityEvents,
  showOutputChannel
} from '../../core/log'
import { esc, getNonce, wrap } from '../html'
import type { SectionContext, StateCache, WebviewMessage } from '../types'
import sectionCss from './style.css'

const MAX_ROWS = 50

export async function handleMessage(msg: WebviewMessage, ctx: SectionContext): Promise<boolean> {
  switch (msg.type) {
    case 'activityClear':
      clearActivityEvents()
      ctx.refreshAll()
      return true
    case 'activityOpenOutput':
      showOutputChannel()
      return true
    default:
      return false
  }
}

export function render(_state: StateCache, codiconUri?: vscode.Uri, cspSource?: string): string {
  const nonce = getNonce()
  const events = getActivityEvents().slice(-MAX_ROWS).reverse()

  if (events.length === 0) {
    return wrap(
      nonce,
      sectionCss,
      `<div class="activity-empty">
        <span>No activity yet — actions will appear here as they happen.</span>
        <button class="btn btn-small" data-action="activity-open-output">
          <span class="codicon codicon-output"></span> Open CMK Output
        </button>
      </div>`,
      codiconUri,
      cspSource
    )
  }

  const header = `<div class="activity-header">
    <span class="activity-count">${events.length} recent event${events.length === 1 ? '' : 's'}</span>
    <span class="activity-actions">
      <button class="btn btn-small btn-icon" data-action="activity-open-output" title="Open CMK Output">
        <span class="codicon codicon-output"></span>
      </button>
      <button class="btn btn-small btn-icon" data-action="activity-clear" title="Clear (session only)">
        <span class="codicon codicon-trash"></span>
      </button>
    </span>
  </div>`

  const now = Date.now()
  const rows = events.map((e, i) => renderRow(e, now, i)).join('')

  return wrap(
    nonce,
    sectionCss,
    header + `<div class="activity-list">${rows}</div>`,
    codiconUri,
    cspSource
  )
}

const CATEGORY_GLYPH: Record<ActivityCategory, string> = {
  omd: 'server-environment',
  profile: 'symbol-property',
  command: 'play',
  benchmark: 'pulse',
  gerrit: 'cloud-upload',
  mypy: 'symbol-property',
  jemalloc: 'pulse',
  general: 'output'
}

function renderRow(e: ActivityEvent, now: number, idx: number): string {
  const dt = now - e.ts
  const rel = relativeTime(dt)
  const iso = new Date(e.ts).toISOString().replace('T', ' ').slice(0, 19)
  const levelClass = e.level === 'ERROR' ? 'err' : e.level === 'WARN' ? 'warn' : 'ok'
  const glyph = CATEGORY_GLYPH[e.category] || 'output'
  const copyText = `${iso} [${e.level}] ${e.message}`
  return `<div class="activity-row ${levelClass} cat-${e.category}" data-action="activity-toggle" data-idx="${idx}">
    <span class="activity-glyph"><span class="codicon codicon-${glyph}"></span></span>
    <span class="activity-msg" title="${esc(e.message)}">${esc(e.message)}</span>
    <span class="activity-time" title="${esc(iso)}">${esc(rel)}</span>
    <button class="btn btn-small btn-icon activity-copy" data-action="copy-setting" data-value="${esc(copyText)}" title="Copy entry">
      <span class="codicon codicon-copy"></span>
    </button>
  </div>`
}

function relativeTime(ms: number): string {
  if (ms < 5_000) return 'just now'
  if (ms < 60_000) return `${Math.floor(ms / 1000)}s`
  if (ms < 3_600_000) return `${Math.floor(ms / 60_000)}m`
  if (ms < 86_400_000) return `${Math.floor(ms / 3_600_000)}h`
  return `${Math.floor(ms / 86_400_000)}d`
}
