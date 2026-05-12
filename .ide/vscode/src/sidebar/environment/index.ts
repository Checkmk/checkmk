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
import { error, log } from '../../core/log'
import { safeExecAsync, shellExecAsync } from '../../core/shell'
import { getNonce, wrap } from '../html'
import type {
  EnvironmentInfo,
  OnboardingState,
  SectionContext,
  StateCache,
  WebviewMessage
} from '../types'
import sectionCss from './style.css'

const EMPTY_ENV: EnvironmentInfo = {
  python: '',
  pythonPath: '',
  node: '',
  pnpm: '',
  bazel: '',
  bazelisk: '',
  docker: '',
  gcc: '',
  pyenv: false,
  systemReady: false
}

let _envCache: { info: EnvironmentInfo; timestamp: number } | null = null
let _envFetchPromise: Promise<void> | null = null
let _onEnvRefresh: (() => void) | null = null
const ENV_CACHE_TTL = 5 * 60 * 1000

export function setEnvironmentRefreshCallback(cb: () => void): void {
  _onEnvRefresh = cb
}

export function invalidateEnvironmentCache(): void {
  _envCache = null
}

/** Sync entry point used during sidebar render. Returns cached info if fresh;
 *  otherwise returns the last value (or empty placeholders) and kicks off a
 *  background refresh that triggers the sidebar to re-render when done. */
export function getEnvironmentInfo(wsPath?: string): EnvironmentInfo {
  if (_envCache && Date.now() - _envCache.timestamp < ENV_CACHE_TTL) {
    return _envCache.info
  }
  void scheduleEnvironmentRefresh(wsPath)
  return _envCache?.info ?? EMPTY_ENV
}

async function scheduleEnvironmentRefresh(wsPath?: string): Promise<void> {
  if (_envFetchPromise) return _envFetchPromise
  _envFetchPromise = (async () => {
    try {
      const info = await fetchEnvironmentInfo(wsPath)
      _envCache = { info, timestamp: Date.now() }
      _onEnvRefresh?.()
    } catch (err) {
      error(`environment refresh failed: ${(err as Error).message}`)
    } finally {
      _envFetchPromise = null
    }
  })()
  return _envFetchPromise
}

async function fetchEnvironmentInfo(wsPath?: string): Promise<EnvironmentInfo> {
  const venvPython = wsPath ? path.join(wsPath, '.venv', 'bin', 'python') : ''
  const hasVenv = !!venvPython && fs.existsSync(venvPython)

  const pnpm = readPnpmVersion(wsPath)
  const bazel = readBazelVersion(wsPath)
  const pyenv = fs.existsSync(path.join(os.homedir(), '.pyenv', 'bin', 'pyenv'))

  const [pythonRaw, nodeRaw, bazeliskRaw, dockerRaw, gccRaw] = await Promise.all([
    hasVenv
      ? safeExecAsync(`"${venvPython}" --version`, { cwd: wsPath })
      : safeExecAsync('python3 --version', { cwd: wsPath }),
    safeExecAsync('node --version', { cwd: wsPath }),
    shellExecAsync('bazelisk version', { cwd: wsPath }),
    shellExecAsync('docker --version', { cwd: wsPath }),
    shellExecAsync('gcc --version', { cwd: wsPath })
  ])

  const env: EnvironmentInfo = { ...EMPTY_ENV }
  if (hasVenv) {
    env.python = pythonRaw.replace('Python ', '') + ' (venv)'
    env.pythonPath = path.join(wsPath!, '.venv')
  } else {
    env.python = pythonRaw ? `${pythonRaw.replace('Python ', '')} (system)` : 'not found'
  }
  env.node = nodeRaw.replace('v', '')
  env.pnpm = pnpm
  env.bazel = bazel
  const bazeliskMatch = bazeliskRaw.match(/Bazelisk version:\s*(\S+)/)
  env.bazelisk = bazeliskMatch ? bazeliskMatch[1] : 'not found'
  env.docker = dockerRaw.replace(/Docker version\s+/, '').replace(/,.*/, '') || 'not found'
  env.gcc = gccRaw.split('\n')[0].replace(/.*\)\s*/, '') || 'not found'
  env.pyenv = pyenv
  env.systemReady =
    env.bazel !== 'not found' && env.docker !== 'not found' && env.gcc !== 'not found' && env.pyenv
  return env
}

function readPnpmVersion(wsPath?: string): string {
  if (!wsPath) return 'not found'
  try {
    const jsModule = fs.readFileSync(
      path.join(wsPath, 'bazel', 'module', 'js.MODULE.bazel'),
      'utf-8'
    )
    const match = jsModule.match(/pnpm_version\s*=\s*"([^"]+)"/)
    return match ? `${match[1]} (Bazel)` : 'not found'
  } catch {
    return 'not found'
  }
}

function readBazelVersion(wsPath?: string): string {
  if (!wsPath) return 'not found'
  try {
    return fs.readFileSync(path.join(wsPath, '.bazelversion'), 'utf-8').trim()
  } catch {
    return 'not found'
  }
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
        // When the click came from an async button (e.g. build target), the
        // command spawns a CMK task and returns immediately. Skip the refresh
        // here so the spinner survives until onDidEndTaskProcess fires.
        if (!msg.deferRefresh) refreshAll()
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

  const envRows =
    `<div class="env-grid">` +
    [
      {
        label: 'Python',
        value: environment.python,
        detail: environment.pythonPath || '',
        action: 'exec',
        actionId: 'cmk.buildVenv',
        actionLabel: 'Rebuild',
        wide: true
      },
      { label: 'Node.js', value: environment.node || 'not found' },
      { label: 'pnpm', value: environment.pnpm || 'not found' },
      { label: 'Bazel', value: environment.bazel },
      { label: 'Bazelisk', value: environment.bazelisk },
      { label: 'Docker', value: environment.docker },
      { label: 'gcc', value: environment.gcc }
    ]
      .map(
        (r) => `
    <div class="env-row${'wide' in r && r.wide ? ' env-row-wide' : ''}">
      <span class="env-label">${r.label}</span>
      <span class="env-value">${r.value}${'detail' in r && r.detail ? ` <span class="env-detail" title="${r.detail}">${r.detail}</span>` : ''}</span>
      ${'action' in r && r.action ? `<button class="btn btn-small btn-icon" data-action="${r.action}" data-id="${r.actionId}" title="${r.actionLabel}"><span class="codicon codicon-sync"></span></button>` : ''}
    </div>`
      )
      .join('') +
    `</div>`

  const configCommands = new Set(['cmk.regenerateMypyConfig'])
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
      <button class="btn btn-small btn-icon" data-action="exec" data-async="true" data-id="${s.commandId}" title="${btnTitle}"><span class="codicon ${btnIcon}"></span></button>
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
