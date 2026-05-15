/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { performance } from 'perf_hooks'
import * as vscode from 'vscode'

import { log, notifyInfo, warn } from '../core/log'
import { currentBranch } from '../scm/git'
import { openBenchmarkChart } from './chartView'

export const HISTORY_KEY = 'cmk.benchmark.startupHistory'
export const SNOOZE_KEY = 'cmk.benchmark.snoozeUntil'
export const SAMPLER_KEY = 'cmk.benchmark.sampler'
export const HISTORY_CAP = 100
export const REGRESSION_RATIO = 1.3
export const MIN_BASELINE_MS = 50
export const MIN_HISTORY_FOR_REGRESSION = 25
export const RECENT_WINDOW = 5
export const BASELINE_WINDOW = 20
export const SNOOZE_MS = 24 * 60 * 60 * 1000
export const SAMPLER_MAX = 50

export interface BenchmarkRun {
  ts: number
  /** cmk-vscode extension version (from package.json). */
  version: string
  /** VS Code application version at the time of the run. */
  vsCodeVersion?: string
  branch: string
  totalMs: number
  phases: Record<string, number>
}

export interface RegressionInfo {
  newMed: number
  oldMed: number
  ratio: number
}

export interface SamplerState {
  target: number
  completed: number
  startedAt: number
  /** First run index (in history) included in the sampler — used to compute the summary. */
  baselineLength: number
}

let _phases: Record<string, number> = {}
let _runDone = false
let _context: vscode.ExtensionContext | null = null

/** Returns true if the `cmk.benchmarkStartup` setting is on OR a sampler is active. */
export function isBenchmarkEnabled(): boolean {
  const settingOn = vscode.workspace.getConfiguration('cmk').get<boolean>('benchmarkStartup', false)
  if (settingOn) return true
  return _context ? getSamplerState(_context) !== null : false
}

/** Returns true if the buffer is currently accepting timings for this session's first run. */
function isCollecting(): boolean {
  return !_runDone && isBenchmarkEnabled()
}

/**
 * Time a synchronous fn and record its duration under `name`. No-op (just runs fn)
 * if benchmarking is disabled or the first run has already been flushed.
 */
export function time<T>(name: string, fn: () => T): T {
  if (!isCollecting()) return fn()
  const t0 = performance.now()
  try {
    return fn()
  } finally {
    const dt = performance.now() - t0
    _phases[name] = (_phases[name] || 0) + dt
  }
}

/**
 * Append the buffered phase timings as a new run to workspace history, then
 * check for a regression vs baseline. Idempotent within a session (subsequent
 * calls are no-ops). Drives the sampler state machine when one is active.
 */
export async function flushBenchmarkRun(context: vscode.ExtensionContext): Promise<void> {
  if (_runDone || !isBenchmarkEnabled()) return
  _runDone = true

  const phases = _phases
  _phases = {}

  const totalMs = Object.values(phases).reduce((sum, ms) => sum + ms, 0)
  if (totalMs <= 0) return

  const wsPath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
  const branch = wsPath ? currentBranch(wsPath) : ''
  const version = (context.extension.packageJSON.version as string) || '0.0.0'

  const run: BenchmarkRun = {
    ts: Date.now(),
    version,
    vsCodeVersion: vscode.version,
    branch,
    totalMs: round(totalMs),
    phases: roundPhases(phases)
  }

  const history = appendRun(getBenchmarkHistory(context), run)
  await context.workspaceState.update(HISTORY_KEY, history)

  log(
    `[benchmark] startup total=${run.totalMs}ms v${run.version} branch=${run.branch || '?'} ` +
      `phases={ ${Object.entries(run.phases)
        .sort((a, b) => b[1] - a[1])
        .map(([k, v]) => `${k}=${v}`)
        .join(', ')} }`
  )

  const sampler = getSamplerState(context)
  if (sampler) {
    await advanceSampler(context, sampler, history)
    return
  }

  const reg = detectRegression(history)
  if (reg && !isSnoozed(context)) {
    void notifyRegression(context, reg)
  }
}

/** Push run; trim to HISTORY_CAP. Pure (returns a new array). */
export function appendRun(history: BenchmarkRun[], run: BenchmarkRun): BenchmarkRun[] {
  const next = [...history, run]
  if (next.length > HISTORY_CAP) next.splice(0, next.length - HISTORY_CAP)
  return next
}

export function getBenchmarkHistory(context: vscode.ExtensionContext): BenchmarkRun[] {
  return context.workspaceState.get<BenchmarkRun[]>(HISTORY_KEY, [])
}

export function getSamplerState(context: vscode.ExtensionContext): SamplerState | null {
  return context.workspaceState.get<SamplerState | null>(SAMPLER_KEY, null) ?? null
}

async function setSamplerState(
  context: vscode.ExtensionContext,
  state: SamplerState | null
): Promise<void> {
  await context.workspaceState.update(SAMPLER_KEY, state)
}

/**
 * Compare median of the last RECENT_WINDOW runs to median of the BASELINE_WINDOW
 * runs immediately preceding them. Returns regression info if recent is materially
 * slower than baseline, else null.
 */
export function detectRegression(history: BenchmarkRun[]): RegressionInfo | null {
  if (history.length < MIN_HISTORY_FOR_REGRESSION) return null
  const recent = history.slice(-RECENT_WINDOW)
  const baselineStart = history.length - RECENT_WINDOW - BASELINE_WINDOW
  const baseline = history.slice(Math.max(0, baselineStart), history.length - RECENT_WINDOW)
  if (baseline.length < BASELINE_WINDOW) return null
  const newMed = median(recent.map((r) => r.totalMs))
  const oldMed = median(baseline.map((r) => r.totalMs))
  if (oldMed < MIN_BASELINE_MS) return null
  const ratio = newMed / oldMed
  if (ratio < REGRESSION_RATIO) return null
  return { newMed: round(newMed), oldMed: round(oldMed), ratio: round(ratio, 2) }
}

function isSnoozed(context: vscode.ExtensionContext): boolean {
  const until = context.workspaceState.get<number>(SNOOZE_KEY, 0)
  return Date.now() < until
}

async function snooze(context: vscode.ExtensionContext): Promise<void> {
  await context.workspaceState.update(SNOOZE_KEY, Date.now() + SNOOZE_MS)
}

async function notifyRegression(
  context: vscode.ExtensionContext,
  reg: RegressionInfo
): Promise<void> {
  await snooze(context)
  const msg = `CMK sidebar startup is ${reg.ratio}× slower than baseline (${reg.newMed}ms vs ${reg.oldMed}ms).`
  const choice = await vscode.window.showInformationMessage(
    msg,
    'View Benchmarks',
    'Snooze 24h',
    'Dismiss'
  )
  if (choice === 'View Benchmarks') {
    void openBenchmarkChart(context)
  }
}

async function advanceSampler(
  context: vscode.ExtensionContext,
  sampler: SamplerState,
  history: BenchmarkRun[]
): Promise<void> {
  const completed = sampler.completed + 1
  if (completed >= sampler.target) {
    await setSamplerState(context, null)
    const samples = history.slice(sampler.baselineLength)
    showSamplerSummary(context, samples, sampler.target)
    return
  }
  const next: SamplerState = { ...sampler, completed }
  await setSamplerState(context, next)
  log(`[benchmark] sampler ${completed}/${sampler.target} — reloading…`)
  // Tiny delay so the workspace-state write hits disk before the reload.
  setTimeout(() => {
    void vscode.commands.executeCommand('workbench.action.reloadWindow')
  }, 200)
}

function showSamplerSummary(
  context: vscode.ExtensionContext,
  samples: BenchmarkRun[],
  target: number
): void {
  if (samples.length === 0) {
    warn(`[benchmark] sampler finished but no samples recorded`)
    return
  }
  const totals = samples.map((r) => r.totalMs).sort((a, b) => a - b)
  const med = median(totals)
  const min = totals[0]
  const max = totals[totals.length - 1]
  const p95 = percentile(totals, 0.95)
  log(
    `[benchmark] sampler done — ${samples.length}/${target} samples · ` +
      `median=${round(med)}ms p95=${round(p95)}ms min=${min}ms max=${max}ms`
  )
  void vscode.window
    .showInformationMessage(
      `CMK sampler done — ${samples.length} samples · median ${round(med)}ms · p95 ${round(p95)}ms · min ${min}ms · max ${max}ms`,
      'View Chart',
      'Dismiss'
    )
    .then((choice) => {
      if (choice === 'View Chart') openBenchmarkChart(context)
    })
}

function median(values: number[]): number {
  if (values.length === 0) return 0
  const sorted = [...values].sort((a, b) => a - b)
  const mid = Math.floor(sorted.length / 2)
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2
}

function percentile(values: number[], p: number): number {
  if (values.length === 0) return 0
  const sorted = [...values].sort((a, b) => a - b)
  const idx = Math.min(sorted.length - 1, Math.floor(p * sorted.length))
  return sorted[idx]
}

function round(n: number, digits = 1): number {
  const f = 10 ** digits
  return Math.round(n * f) / f
}

function roundPhases(phases: Record<string, number>): Record<string, number> {
  const out: Record<string, number> = {}
  for (const [k, v] of Object.entries(phases)) out[k] = round(v)
  return out
}

/**
 * Registers benchmark commands and resumes any in-flight sampler.
 * If a sampler is active, force-reveals the sidebar so refreshStateCache
 * (and therefore flushBenchmarkRun) runs without waiting for the user to
 * open it.
 */
export function registerStartupBenchmarks(context: vscode.ExtensionContext): vscode.Disposable[] {
  _context = context

  // Resume sampler from prior reload, if any.
  const sampler = getSamplerState(context)
  if (sampler) {
    log(`[benchmark] resuming sampler ${sampler.completed}/${sampler.target}`)
    // Give the sidebar provider a moment to register, then force-reveal so the
    // first refresh fires and our flush executes.
    setTimeout(() => {
      void vscode.commands.executeCommand('cmk.dashboard.environment.focus')
    }, 200)
  }

  return [
    vscode.commands.registerCommand('cmk.showStartupBenchmarks', () => openBenchmarkChart(context)),
    vscode.commands.registerCommand('cmk.benchmarkRunSamples', () => runSamplesCommand(context)),
    vscode.commands.registerCommand('cmk.benchmarkCancelSamples', () =>
      cancelSamplesCommand(context)
    ),
    vscode.commands.registerCommand('cmk.benchmarkTrimRecent', () => trimRecentRunsCommand(context))
  ]
}

async function trimRecentRunsCommand(context: vscode.ExtensionContext): Promise<void> {
  const history = getBenchmarkHistory(context)
  if (history.length === 0) {
    notifyInfo('CMK: No benchmark runs recorded.')
    return
  }
  const answer = await vscode.window.showInputBox({
    prompt: `Trim the most recent N runs from history (1–${history.length})`,
    value: '5',
    validateInput: (v) => {
      const n = Number(v)
      if (!Number.isFinite(n) || !Number.isInteger(n)) return 'Enter an integer'
      if (n < 1 || n > history.length) return `Must be between 1 and ${history.length}`
      return null
    }
  })
  if (!answer) return
  const n = Number(answer)
  const trimmed = history.slice(0, history.length - n)
  await context.workspaceState.update(HISTORY_KEY, trimmed)
  log(`[benchmark] trimmed last ${n} run(s); ${trimmed.length} remain`)
  notifyInfo(`CMK: Dropped ${n} benchmark run${n === 1 ? '' : 's'}. ${trimmed.length} remain.`)
}

async function runSamplesCommand(context: vscode.ExtensionContext): Promise<void> {
  if (getSamplerState(context)) {
    const choice = await vscode.window.showWarningMessage(
      'A startup sampler is already running. Cancel it first?',
      'Cancel Sampler',
      'Keep Running'
    )
    if (choice === 'Cancel Sampler') await setSamplerState(context, null)
    return
  }

  const answer = await vscode.window.showInputBox({
    prompt: `How many startup samples? (1–${SAMPLER_MAX})`,
    value: '10',
    validateInput: (v) => {
      const n = Number(v)
      if (!Number.isFinite(n) || !Number.isInteger(n)) return 'Enter an integer'
      if (n < 1 || n > SAMPLER_MAX) return `Must be between 1 and ${SAMPLER_MAX}`
      return null
    }
  })
  if (!answer) return
  const target = Number(answer)

  const confirm = await vscode.window.showWarningMessage(
    `Reload this window ${target} times to collect startup samples? Save any unsaved work first.`,
    { modal: true },
    'Start'
  )
  if (confirm !== 'Start') return

  const history = getBenchmarkHistory(context)
  const state: SamplerState = {
    target,
    completed: 0,
    startedAt: Date.now(),
    baselineLength: history.length
  }
  await setSamplerState(context, state)
  notifyInfo(`CMK sampler started — collecting ${target} samples. Window will reload until done.`)
  // First reload kicks off sample #1.
  setTimeout(() => {
    void vscode.commands.executeCommand('workbench.action.reloadWindow')
  }, 400)
}

async function cancelSamplesCommand(context: vscode.ExtensionContext): Promise<void> {
  const sampler = getSamplerState(context)
  if (!sampler) {
    notifyInfo('CMK: No startup sampler is running.')
    return
  }
  await setSamplerState(context, null)
  notifyInfo(`CMK sampler cancelled at ${sampler.completed}/${sampler.target}.`)
}
