/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as vscode from 'vscode'

import { type Playbook, type PlaybookSource, cmkUp } from '../../omd/cmkUp'
import { esc, getNonce, wrap } from '../html'
import type { StateCache, WebviewMessage } from '../types'
import sectionCss from './style.css'

const SOURCE_LABELS: Readonly<Record<PlaybookSource, string>> = {
  workspace: 'Workspace',
  directory: 'Playbook directories',
  shipped: 'Shipped examples'
}

const SEARCH_FIELD = `<input class="playbook-search" type="search" data-filter="shipped-playbooks" placeholder="Search examples…" aria-label="Search shipped examples">`

export async function handleMessage(msg: WebviewMessage): Promise<boolean> {
  switch (msg.type) {
    case 'playbookRun':
      await cmkUp.startRun(msg.target as string)
      return true
    case 'playbookDryRun':
      await cmkUp.startRun(msg.target as string, { keep: false, dryRun: true })
      return true
    case 'playbookOpen':
      await vscode.window.showTextDocument(vscode.Uri.file(msg.file as string))
      return true
    case 'playbookNew':
      await cmkUp.init()
      return true
    default:
      return false
  }
}

export function render(state: StateCache, codiconUri?: vscode.Uri, cspSource?: string): string {
  const nonce = getNonce()
  const newBtn = `<button class="btn btn-small" data-action="playbook-new"><span class="codicon codicon-add"></span> New Playbook</button>`

  if (!state.playbooksScanned && state.playbooks.length === 0) {
    return wrap(
      nonce,
      sectionCss,
      `<div class="playbook-empty">Scanning for playbooks…</div>`,
      codiconUri,
      cspSource
    )
  }

  if (state.playbooks.length === 0) {
    return wrap(
      nonce,
      sectionCss,
      `<div class="playbook-empty">No cmk-up playbooks found</div><div class="playbook-new">${newBtn}</div>`,
      codiconUri,
      cspSource
    )
  }

  const groups = (Object.keys(SOURCE_LABELS) as PlaybookSource[])
    .map((source) => {
      const rows = state.playbooks.filter((p) => p.source === source).map(renderRow)
      if (rows.length === 0) return ''
      const title = `<div class="playbook-group-title">${SOURCE_LABELS[source]}</div>`
      if (source !== 'shipped') return `<div class="playbook-group">${title}${rows.join('')}</div>`
      return `<div class="playbook-group" data-filter-scope>${title}${SEARCH_FIELD}${rows.join('')}<div class="playbook-empty" data-filter-empty hidden>No example matches</div></div>`
    })
    .join('')

  return wrap(nonce, sectionCss, groups, codiconUri, cspSource)
}

function renderRow(playbook: Playbook): string {
  const target = esc(playbook.target)
  const title = esc(playbook.source === 'shipped' ? playbook.name : playbook.file)
  const description = playbook.description
    ? `<span class="playbook-description">${esc(playbook.description)}</span>`
    : ''
  const search = esc(`${playbook.name} ${playbook.description}`.toLowerCase())
  return `<div class="playbook-row" title="${title}" data-search="${search}">
    <span class="codicon codicon-book playbook-icon"></span>
    <span class="playbook-text"><span class="playbook-name">${esc(playbook.name)}</span>${description}</span>
    <span class="playbook-actions">
      <button class="btn btn-small btn-icon" data-action="playbook-open" data-file="${esc(playbook.file)}" title="Open playbook"><span class="codicon codicon-go-to-file"></span></button>
      <button class="btn btn-small btn-icon" data-action="playbook-dry-run" data-target="${target}" title="Dry run (--dry-run)"><span class="codicon codicon-beaker"></span></button>
      <button class="btn btn-small btn-icon" data-action="playbook-run" data-target="${target}" title="Run playbook…"><span class="codicon codicon-play"></span></button>
    </span>
  </div>`
}
