/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as os from 'os'
import * as path from 'path'
import * as vscode from 'vscode'

import { type Playbook, type PlaybookSource, cmkUp } from '../../omd/cmkUp'
import { esc, getNonce, wrap } from '../html'
import type { StateCache, WebviewMessage } from '../types'
import sectionCss from './style.css'

const SOURCE_ICONS: Readonly<Record<PlaybookSource, string>> = {
  workspace: 'book',
  directory: 'file-code',
  shipped: 'library'
}

const SEARCH_FIELD = `<input class="playbook-search" type="search" data-filter="playbooks" placeholder="Search local and shipped playbooks…" aria-label="Search local and shipped playbooks">`

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
    case 'playbookFolder':
      await cmkUp.revealDirectory(msg.dir as string)
      return true
    case 'playbookInstallCwz':
      await cmkUp.install()
      return true
    case 'playbookConfigure':
      await vscode.commands.executeCommand(
        'workbench.action.openSettings',
        'cmk.cmkUp.playbookDirectories'
      )
      return true
    default:
      return false
  }
}

export function render(state: StateCache, codiconUri?: vscode.Uri, cspSource?: string): string {
  const nonce = getNonce()
  const newBtn = `<button class="btn btn-small" data-action="playbook-new"><span class="codicon codicon-add"></span> New Playbook</button>`
  const of = (source: PlaybookSource) => state.playbooks.filter((p) => p.source === source)

  const workspace = of('workspace')
  const workspaceGroup = workspace.length
    ? `<div class="playbook-group"><div class="playbook-group-title">Workspace</div>${workspace.map(renderRow).join('')}</div>`
    : ''

  const local = of('directory')
  const localTitle = `<div class="playbook-group-title">Local playbooks<button class="btn btn-small btn-icon playbook-configure" data-action="playbook-configure" title="Configure playbook folders"><span class="codicon codicon-gear"></span></button></div>`
  const folders = state.playbookDirectories
    .map((dir) => {
      const rows = local.filter((p) => path.dirname(p.file) === dir).map(renderRow)
      const empty = rows.length
        ? ''
        : `<div class="playbook-empty">No playbooks in this folder yet</div>`
      return `${renderFolder(dir)}${rows.join('')}${empty}`
    })
    .join('')
  const localGroup = state.playbookDirectories.length
    ? `<div class="playbook-group">${localTitle}${folders}</div>`
    : ''

  const shipped = of('shipped')
  const shippedGroup = shipped.length
    ? `<div class="playbook-group"><div class="playbook-group-title">Shipped examples</div>${shipped.map(renderRow).join('')}</div>`
    : ''

  const banner =
    state.cwzInstalled === false
      ? `<div class="banner banner-info">
          <span>cmk-werk-zeug is not installed, so playbooks run through uvx — install it with pipx to run the installed cmk-up and get update notifications.</span>
          <button class="btn btn-small" data-action="playbook-install-cwz"><span class="codicon codicon-package"></span> Install</button>
        </div>`
      : ''

  const searchable =
    localGroup || shippedGroup
      ? `<div data-filter-scope>${SEARCH_FIELD}${localGroup}${shippedGroup}<div class="playbook-empty" data-filter-empty hidden>No playbook matches</div></div>`
      : ''
  const none = state.playbooks.length
    ? ''
    : state.playbooksScanned
      ? `<div class="playbook-empty">No cmk-up playbooks found</div><div class="playbook-new">${newBtn}</div>`
      : `<div class="playbook-empty">Scanning for playbooks…</div>`

  return wrap(
    nonce,
    sectionCss,
    `${banner}${workspaceGroup}${searchable}${none}`,
    codiconUri,
    cspSource
  )
}

function renderFolder(dir: string): string {
  const home = os.homedir()
  const shown = dir === home || dir.startsWith(`${home}/`) ? `~${dir.slice(home.length)}` : dir
  return `<div class="playbook-folder" title="${esc(dir)}">
    <span class="codicon codicon-folder playbook-icon"></span>
    <span class="playbook-folder-path">${esc(shown)}</span>
    <button class="btn btn-small btn-icon" data-action="playbook-folder" data-dir="${esc(dir)}" title="Reveal folder"><span class="codicon codicon-folder-opened"></span></button>
  </div>`
}

function renderRow(playbook: Playbook): string {
  const target = esc(playbook.target)
  const title = esc(playbook.source === 'shipped' ? playbook.name : playbook.file)
  const description = playbook.description
    ? `<span class="playbook-description">${esc(playbook.description)}</span>`
    : ''
  const search = esc(`${playbook.name} ${playbook.description}`.toLowerCase())
  return `<div class="playbook-row" title="${title}" data-search="${search}">
    <span class="codicon codicon-${SOURCE_ICONS[playbook.source]} playbook-icon"></span>
    <span class="playbook-text"><span class="playbook-name">${esc(playbook.name)}</span>${description}</span>
    <span class="playbook-actions">
      <button class="btn btn-small btn-icon" data-action="playbook-open" data-file="${esc(playbook.file)}" title="Open playbook"><span class="codicon codicon-go-to-file"></span></button>
      <button class="btn btn-small btn-icon" data-action="playbook-dry-run" data-target="${target}" title="Dry run (--dry-run)"><span class="codicon codicon-beaker"></span></button>
      <button class="btn btn-small btn-icon" data-action="playbook-run" data-target="${target}" title="Run playbook…"><span class="codicon codicon-play"></span></button>
    </span>
  </div>`
}
