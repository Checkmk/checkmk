/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as vscode from 'vscode'

import { log } from '../../core/log'
import { esc, getNonce, wrap } from '../html'
import type { SectionContext, StateCache, WebviewMessage } from '../types'
import { type DomainEntry, type DomainItem, type Severity, getDomainSummary } from './domainSummary'
import sectionCss from './style.css'

export async function handleMessage(msg: WebviewMessage, ctx: SectionContext): Promise<boolean> {
  switch (msg.type) {
    case 'overviewRowAction':
      return await handleRowAction(msg, ctx)
    case 'overviewItemAction':
      return await handleItemAction(msg, ctx)
    default:
      return false
  }
}

async function handleRowAction(msg: WebviewMessage, ctx: SectionContext): Promise<boolean> {
  const domain = msg.domain as DomainEntry['domain']
  const command = msg.command as string | undefined
  const args = (msg.commandArgs as unknown[]) || []

  // "Apply all" is a webview message owned by IDE Health, not a registered command.
  if (domain === 'settings') {
    log('Cockpit: applyAllMismatches')
    const { handleMessage: ideHealthHandle } = await import('../ideHealth/index')
    await ideHealthHandle({ type: 'applyAllMismatches' } as WebviewMessage, ctx)
    return true
  }
  if (command) {
    log(`Cockpit row action: ${command}`)
    await vscode.commands.executeCommand(command, ...args)
    ctx.refreshAll()
  }
  return true
}

async function handleItemAction(msg: WebviewMessage, ctx: SectionContext): Promise<boolean> {
  const command = msg.command as string | undefined
  const args = (msg.commandArgs as unknown[]) || []
  if (!command) return true
  log(`Cockpit item action: ${command}`)
  // applySetting is the only per-item command that goes via the IDE Health helper signature
  // [key, expected, scope]; vscode.commands.executeCommand passes them positionally and works.
  await vscode.commands.executeCommand(command, ...args)
  ctx.refreshAll()
  return true
}

export function render(state: StateCache, codiconUri?: vscode.Uri, cspSource?: string): string {
  const nonce = getNonce()
  const summary = getDomainSummary(state)
  // OMD intentionally omitted — it has its own dedicated section below.
  const rows = [summary.builds, summary.settings, summary.health, summary.git]

  const rowsHtml = rows.map(renderRow).join('')
  const onboardingHtml = renderOnboarding(state)

  return wrap(
    nonce,
    sectionCss,
    `<div class="cockpit">
      ${onboardingHtml}
      <div class="cockpit-rows">${rowsHtml}</div>
    </div>`,
    codiconUri,
    cspSource
  )
}

function renderOnboarding(state: StateCache): string {
  const { onboarding, onboardingDismissed } = state
  if (!onboarding || onboarding.allDone || onboardingDismissed) return ''
  const steps = [
    {
      key: 'system',
      label: 'System Setup',
      description: 'Install bazel, pyenv, docker, gcc via <code>make setup</code>',
      done: onboarding.systemDone,
      action: 'run-make-setup',
      actionLabel: '<span class="codicon codicon-play"></span> Run make setup',
      actionId: ''
    },
    {
      key: 'venv',
      label: 'Build .venv',
      description: 'Create the Python virtual environment',
      done: onboarding.venvDone,
      action: 'exec',
      actionLabel: '<span class="codicon codicon-wrench"></span> Build .venv',
      actionId: 'cmk.buildVenv'
    },
    {
      key: 'ide',
      label: 'IDE Setup',
      description: 'Install extensions and configure settings',
      done: onboarding.ideDone,
      action: 'exec',
      actionLabel: '<span class="codicon codicon-settings-gear"></span> Configure IDE',
      actionId: 'cmk.setupPicker'
    }
  ]
  const stepHtml = steps
    .map((s, i) => {
      const isCurrent = s.key === onboarding.currentStep
      const icon = s.done
        ? '<span class="step-icon done">&#10003;</span>'
        : `<span class="step-icon ${isCurrent ? 'current' : 'pending'}">${i + 1}</span>`
      const actionBtn = isCurrent
        ? `<button class="btn btn-small btn-ghost" data-action="${s.action}" data-id="${s.actionId}">${s.actionLabel}</button>`
        : ''
      return `<div class="onboarding-step ${s.done ? 'done' : ''} ${isCurrent ? 'current' : ''}">
        ${icon}
        <div class="step-body">
          <div class="step-label">${esc(s.label)}</div>
          ${isCurrent ? `<div class="step-desc">${s.description}</div>` : ''}
          ${actionBtn}
        </div>
      </div>`
    })
    .join('')
  return `<div class="onboarding-banner">
    <div class="onboarding-header">
      <span class="onboarding-title">Getting Started</span>
      <button class="btn btn-small btn-icon" data-action="onboarding-dismiss" title="Dismiss">&#10005;</button>
    </div>
    ${stepHtml}
  </div>`
}

function renderRow(d: DomainEntry): string {
  const sev: Severity = d.severity
  const hasItems = d.totalItems > 0
  const openByDefault = sev !== 'ok' && sev !== 'info' && hasItems
  const rowClass = `cockpit-row sev-${sev}${openByDefault ? ' open' : ''}${hasItems ? '' : ' no-items'}`
  const actionBtn =
    d.actionVerb && d.severity !== 'ok' && d.severity !== 'info'
      ? `<button class="btn btn-small cockpit-action"
                 data-action="overview-row-action"
                 data-domain="${esc(d.domain)}"
                 data-command="${esc(d.command ?? '')}"
                 data-command-args='${esc(JSON.stringify(d.commandArgs ?? []))}'>
          ${esc(d.actionVerb)}
        </button>`
      : ''
  const openBtn = d.focusViewId
    ? `<button class="btn btn-small btn-icon cockpit-open"
               data-action="exec"
               data-id="${esc(d.focusViewId)}"
               title="Open ${esc(d.focusViewName ?? d.title)}">
        <span class="codicon codicon-link-external"></span>
      </button>`
    : ''
  const chevron = hasItems
    ? `<span class="cockpit-chevron codicon codicon-chevron-right"></span>`
    : `<span class="cockpit-chevron-placeholder"></span>`
  const itemsHtml = hasItems
    ? `<div class="cockpit-items">${d.items.map(renderItem).join('')}
        ${
          d.totalItems > d.items.length
            ? `<div class="cockpit-item more">… and ${d.totalItems - d.items.length} more — open <a class="link" data-action="exec" data-id="cmk.dashboard.badge.focus">Issues</a></div>`
            : ''
        }
      </div>`
    : ''
  // Entire header toggles open/close (when there are items). The action buttons
  // stop propagation so they don't toggle while clicking.
  const headerAction = hasItems ? 'data-action="overview-row-toggle"' : ''
  return `<div class="${rowClass}">
    <div class="cockpit-row-header" ${headerAction}>
      <span class="cockpit-glyph codicon codicon-${esc(d.glyph)}"></span>
      <span class="cockpit-title">${esc(d.title)}</span>
      <span class="cockpit-badge">${esc(d.badge)}</span>
      ${actionBtn}
      ${openBtn}
      ${chevron}
    </div>
    ${itemsHtml}
  </div>`
}

function renderItem(item: DomainItem): string {
  const action =
    item.command !== undefined
      ? `<button class="btn btn-small btn-ghost cockpit-item-action"
                 data-action="overview-item-action"
                 data-command="${esc(item.command)}"
                 data-command-args='${esc(JSON.stringify(item.commandArgs ?? []))}'
                 title="${esc(item.label)}">
          ${esc(item.actionLabel)}
        </button>`
      : ''
  const dismiss = item.dismissCommand
    ? `<button class="btn btn-small btn-icon cockpit-item-dismiss"
               data-action="exec"
               data-id="${esc(item.dismissCommand)}"
               title="${esc(item.dismissTitle ?? 'Dismiss')}">
        <span class="codicon codicon-close"></span>
      </button>`
    : ''
  const familyTag = item.familyTag
    ? `<span class="cockpit-family-tag sev-${esc(item.severity)}">${esc(item.familyTag)}</span>`
    : ''
  const detail = item.detail ? `<span class="cockpit-item-detail">${esc(item.detail)}</span>` : ''
  return `<div class="cockpit-item sev-${esc(item.severity)}" data-id="${esc(item.id)}">
    <span class="cockpit-item-label">${esc(item.label)}</span>
    ${familyTag}
    ${detail}
    ${action}
    ${dismiss}
  </div>`
}
