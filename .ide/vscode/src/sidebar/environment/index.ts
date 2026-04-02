/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as fs from 'fs'
import * as os from 'os'
import * as path from 'path'
import * as vscode from 'vscode'

import type { BuildStatus } from '../../build/buildStatus'
import { log } from '../../core/log'
import { safeExec, shellExec } from '../../core/shell'
import { getNonce, wrap } from '../html'
import type {
  EnvironmentInfo,
  OnboardingState,
  SectionContext,
  StateCache,
  WebviewMessage
} from '../types'
import sectionCss from './style.css'

let _envCache: { info: EnvironmentInfo; timestamp: number } | null = null
const ENV_CACHE_TTL = 5 * 60 * 1000

export function invalidateEnvironmentCache(): void {
  _envCache = null
}

export function getEnvironmentInfo(wsPath?: string): EnvironmentInfo {
  if (_envCache && Date.now() - _envCache.timestamp < ENV_CACHE_TTL) {
    return _envCache.info
  }
  const env: EnvironmentInfo = {
    python: '',
    pythonPath: '',
    node: '',
    bazel: '',
    bazelisk: '',
    docker: '',
    gcc: '',
    pyenv: false,
    systemReady: false
  }
  const venvPython = wsPath ? path.join(wsPath, '.venv', 'bin', 'python') : ''
  if (venvPython && fs.existsSync(venvPython)) {
    env.python =
      safeExec(`"${venvPython}" --version`, { cwd: wsPath }).replace('Python ', '') + ' (venv)'
    env.pythonPath = path.join(wsPath!, '.venv')
  } else {
    const sysPython = safeExec('python3 --version', { cwd: wsPath }).replace('Python ', '')
    env.python = sysPython ? `${sysPython} (system)` : 'not found'
    env.pythonPath = ''
  }
  env.node = safeExec('node --version', { cwd: wsPath }).replace('v', '')
  if (wsPath) {
    try {
      env.bazel = fs.readFileSync(path.join(wsPath, '.bazelversion'), 'utf-8').trim()
    } catch {
      env.bazel = 'not found'
    }
  } else {
    env.bazel = 'not found'
  }
  const bazeliskRaw = shellExec('bazelisk version', { cwd: wsPath })
  const bazeliskMatch = bazeliskRaw.match(/Bazelisk version:\s*(\S+)/)
  env.bazelisk = bazeliskMatch ? bazeliskMatch[1] : 'not found'
  env.docker =
    shellExec('docker --version', { cwd: wsPath })
      .replace(/Docker version\s+/, '')
      .replace(/,.*/, '') || 'not found'
  env.gcc =
    shellExec('gcc --version', { cwd: wsPath })
      .split('\n')[0]
      .replace(/.*\)\s*/, '') || 'not found'
  env.pyenv = fs.existsSync(path.join(os.homedir(), '.pyenv', 'bin', 'pyenv'))
  env.systemReady =
    env.bazel !== 'not found' && env.docker !== 'not found' && env.gcc !== 'not found' && env.pyenv
  _envCache = { info: env, timestamp: Date.now() }
  return env
}

export function getOnboardingState(
  environment: EnvironmentInfo,
  buildStatus: BuildStatus,
  context: vscode.ExtensionContext | null
): OnboardingState {
  const systemDone = environment.systemReady
  const venvDone = buildStatus.venv?.ok ?? false
  const ideDone = context
    ? (context.globalState.get('cmk.setupWizardDismissed', false) as boolean)
    : false

  let currentStep: string | null = null
  if (!systemDone) currentStep = 'system'
  else if (!venvDone) currentStep = 'venv'
  else if (!ideDone) currentStep = 'ide'

  return { systemDone, venvDone, ideDone, currentStep, allDone: currentStep === null }
}

export async function handleMessage(
  msg: WebviewMessage,
  { refreshAll }: SectionContext
): Promise<boolean> {
  switch (msg.type) {
    case 'executeCommand':
      log(`Execute command: ${msg.commandId}`)
      if (msg.commandId === 'cmk.disableExtension') {
        await vscode.commands.executeCommand('extension.open', 'ms-python.vscode-python-envs')
      } else {
        await vscode.commands.executeCommand(msg.commandId as string)
        refreshAll()
      }
      return true
    case 'runMakeSetup': {
      log('Run make setup')
      const term = vscode.window.createTerminal({ name: 'CMK: System Setup' })
      term.show()
      term.sendText('make setup')
      return true
    }
    case 'onboardingDismiss':
      return true
    default:
      return false
  }
}

export function render(state: StateCache, codiconUri?: vscode.Uri, cspSource?: string): string {
  const nonce = getNonce()
  const { buildStatus, environment, onboarding, onboardingDismissed } = state

  let onboardingHtml = ''
  if (onboarding && !onboarding.allDone && !onboardingDismissed) {
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
          <div class="step-label">${s.label}</div>
          ${isCurrent ? `<div class="step-desc">${s.description}</div>` : ''}
          ${actionBtn}
        </div>
      </div>`
      })
      .join('')

    onboardingHtml = `
      <div class="onboarding-banner">
        <div class="onboarding-header">
          <span class="onboarding-title">Getting Started</span>
          <button class="btn btn-small btn-icon" data-action="onboarding-dismiss" title="Dismiss">&#10005;</button>
        </div>
        ${stepHtml}
      </div>`
  }

  const envRows = [
    {
      label: 'Python',
      value: environment.python,
      detail: environment.pythonPath || '',
      action: 'exec',
      actionId: 'cmk.buildVenv',
      actionLabel: 'Rebuild'
    },
    { label: 'Node.js', value: environment.node || 'not found' },
    { label: 'Bazel', value: environment.bazel },
    { label: 'Bazelisk', value: environment.bazelisk },
    { label: 'Docker', value: environment.docker },
    { label: 'gcc', value: environment.gcc }
  ]
    .map(
      (r) => `
    <div class="env-row">
      <span class="env-label">${r.label}</span>
      <span class="env-value">${r.value}${'detail' in r && r.detail ? ` <span class="env-detail" title="${r.detail}">${r.detail}</span>` : ''}</span>
      ${'action' in r && r.action ? `<button class="btn btn-small btn-icon" data-action="${r.action}" data-id="${r.actionId}" title="${r.actionLabel}"><span class="codicon codicon-sync"></span></button>` : ''}
    </div>`
    )
    .join('')

  const configCommands = new Set(['cmk.regenerateMypyConfig', 'cmk.regeneratePrettierConfig'])
  const staleTargets = Object.values(buildStatus).filter((s) => !s.ok)
  const staleBanner =
    staleTargets.length > 0
      ? `<div class="banner banner-warn">
        <span>${staleTargets.length} build target(s) need updating: ${staleTargets.map((s) => s.label).join(', ')}</span>
        <button class="btn btn-small" data-action="exec" data-id="cmk.buildAllStale"><span class="codicon codicon-run-all"></span> Build All</button>
      </div>`
      : ''
  const buildCards = Object.entries(buildStatus)
    .map(([, s]) => {
      const icon = s.ok ? '&#10003;' : '&#10007;'
      const cls = s.ok ? 'ok' : 'stale'
      const isRegen = configCommands.has(s.commandId)
      const btnIcon = 'codicon-sync'
      const btnTitle = isRegen ? 'Regenerate' : 'Build'
      return `<div class="build-row ${cls}">
      <span class="card-icon">${icon}</span>
      <span class="build-name">${s.label}</span>
      <button class="btn btn-small btn-icon" data-action="exec" data-id="${s.commandId}" title="${btnTitle}"><span class="codicon ${btnIcon}"></span></button>
    </div>`
    })
    .join('')

  const divider = buildCards ? '<div class="section-divider"></div>' : ''

  return wrap(
    nonce,
    sectionCss,
    `${onboardingHtml}${envRows}${divider}${staleBanner}${buildCards}`,
    codiconUri,
    cspSource
  )
}
