/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { FAMILY_DISPLAY } from '../../core/constants'
import * as profileManager from '../../profiles/profileManager'
import type { StateCache } from '../types'

export type Severity = 'ok' | 'info' | 'warning' | 'critical'

const DISPLAY_TO_FAMILY = Object.fromEntries(Object.entries(FAMILY_DISPLAY).map(([k, v]) => [v, k]))
/** Families that map to user-toggleable profiles. Only these get filtered out when the profile is off. */
const PROFILE_FAMILIES = new Set(['python', 'frontend', 'rust', 'cpp'])

/** A single actionable issue. Both the Issues tree and the cockpit consume this. */
export interface Issue {
  /** Stable, machine-friendly key used as the TreeItem `id` (preserves selection across refreshes). */
  id: string
  domain:
    | 'build'
    | 'settings'
    | 'omd'
    | 'extension'
    | 'allocator'
    | 'mypy'
    | 'pylance'
    | 'pyEnvs'
    | 'config'
    | 'devSite'
    | 'version'
    | 'git'
    | 'benchmark'
    | 'dmypy'
    | 'bazelCache'
  severity: Exclude<Severity, 'ok'>
  /** Display label, domain-prefixed where ambiguous. */
  label: string
  /** Right-side description: "<state> · <action verb>". */
  description: string
  tooltip: string
  /** Codicon name (no `codicon-` prefix). */
  icon: string
  /** Primary command + args when the user clicks the row / chip. */
  command?: string
  commandArgs?: unknown[]
}

/** A single drill-down entry under a cockpit domain row (e.g. one stale build target). */
export interface DomainItem {
  /** Stable id for the per-item DOM node. */
  id: string
  /** Per-item severity (warning / critical). Used to color the row. */
  severity: Exclude<Severity, 'ok'>
  /** Primary text on the sub-row. */
  label: string
  /** Optional dim secondary text. */
  detail?: string
  /** Family tag rendered as a coloured pill (e.g. "Python" / "UI" / "Markdown"). */
  familyTag?: string
  /** Command + args executed when the per-item action button is clicked. */
  command?: string
  commandArgs?: unknown[]
  /** Button label, e.g. "Build" / "Apply" / "Restart". */
  actionLabel: string
  /** Optional secondary "dismiss this warning" command (renders an X icon next to the action). */
  dismissCommand?: string
  /** Tooltip for the dismiss icon. */
  dismissTitle?: string
}

/** Per-domain rollup used by the cockpit row. */
export interface DomainEntry {
  domain: 'builds' | 'settings' | 'omd' | 'health' | 'git'
  severity: Severity
  /** Status text (e.g. "3 stale", "all up to date", "5 drifted"). */
  badge: string
  /** Codicon shown on the row. */
  glyph: string
  /** Human-readable domain name (e.g. "Builds", "Settings"). */
  title: string
  /** Tooltip body lines (one per affected item). */
  tooltipLines: string[]
  /** Clicked while healthy → focus view. */
  focusViewId?: string
  /** Human-readable section name shown in the "open section" tooltip. Defaults to title. */
  focusViewName?: string
  /** Primary command for the row-level action button (when non-healthy). */
  command?: string
  commandArgs?: unknown[]
  /** Row-level action label (e.g. "Build all", "Apply all", "Restart"). */
  actionVerb?: string
  /** Per-item drill-down rows, capped. */
  items: DomainItem[]
  /** Total items (uncapped); used to render "… and N more". */
  totalItems: number
}

export interface DomainSummary {
  builds: DomainEntry
  settings: DomainEntry
  omd: DomainEntry
  health: DomainEntry
  git: DomainEntry
  overallSeverity: Severity
  totalIssues: number
}

const SEV_RANK: Record<Severity, number> = { ok: 0, info: 1, warning: 2, critical: 3 }

function maxSev(a: Severity, b: Severity): Severity {
  return SEV_RANK[a] >= SEV_RANK[b] ? a : b
}

/**
 * Walk the state cache and emit one Issue per actionable problem. Pure: returns
 * the same array shape regardless of when it runs. Used by both the Issues
 * tree view and (indirectly) the cockpit row.
 */
export function enumerateIssues(state: StateCache): Issue[] {
  const out: Issue[] = []
  const {
    buildStatus,
    settingsMismatches,
    extensionHealth,
    pythonEnvsActive,
    devSiteTools,
    versionMismatch,
    mypyTargets,
    allocator,
    pylanceHealth,
    configInWorkspace,
    omdSites
  } = state

  if (versionMismatch) {
    // Patch bumps are usually safe (fixes); minor/major can carry breaking
    // changes, surface them louder.
    const severity = versionGap(versionMismatch.installed, versionMismatch.workspace)
    out.push({
      id: 'version:cmk-extension',
      domain: 'version',
      severity,
      label: 'CMK Extension',
      description: `v${versionMismatch.installed} → v${versionMismatch.workspace} · Install`,
      tooltip: `Installed v${versionMismatch.installed} ≠ workspace v${versionMismatch.workspace}. Click to install.`,
      icon: 'extensions',
      command: 'cmk.rebuildExtension'
    })
  }

  // Build severity:
  //   - venv missing → critical (breaks mypy, Pylance, formatters)
  //   - other targets → warning
  for (const [key, s] of Object.entries(buildStatus)) {
    if (s.ok) continue
    const severity: 'critical' | 'warning' = key === 'venv' ? 'critical' : 'warning'
    out.push({
      id: `build:${key}`,
      domain: 'build',
      severity,
      label: `Build · ${s.label}`,
      description: 'needs building · Build',
      tooltip: `Click to build ${s.label}`,
      icon: 'tools',
      command: s.commandId
    })
  }

  // Settings severity:
  //   - drift on an active profile family → critical (user is actively working in that family and the IDE is misconfigured)
  //   - drift on an inactive profile family → warning (still surfaces, just not loud)
  //   - drift on a non-profile family (Markdown, Spelling, LLDB, Bazel, General) → warning
  const seenKeys = new Set<string>()
  for (const m of settingsMismatches) {
    if (seenKeys.has(m.key)) continue
    const family = DISPLAY_TO_FAMILY[m.family]
    if (!family) continue
    const isProfileFamily = PROFILE_FAMILIES.has(family)
    const profileActive = isProfileFamily && profileManager.isActive(family)
    seenKeys.add(m.key)
    const severity: 'critical' | 'warning' = profileActive ? 'critical' : 'warning'
    out.push({
      id: `settings:${m.key}`,
      domain: 'settings',
      severity,
      label: `Settings · ${m.key}`,
      description: `${m.family} · ${m.scope} · Apply`,
      tooltip: `Click to apply: ${m.key} = ${JSON.stringify(m.expected)}`,
      icon: 'settings-gear',
      command: 'cmk.applySetting',
      commandArgs: [m.key, m.expected, m.scope]
    })
  }

  // Required-extension severity: critical only when the family is active or
  // always-on (you actually depend on it right now); warning when the family
  // is a profile that's currently off (you've opted out of that workflow).
  for (const f of extensionHealth) {
    if (!f.required) continue
    const isProfileFamily = PROFILE_FAMILIES.has(f.name)
    const profileActive = !isProfileFamily || profileManager.isActive(f.name)
    const severity: 'critical' | 'warning' = profileActive ? 'critical' : 'warning'
    for (const e of f.extensions) {
      if (e.installed) continue
      out.push({
        id: `extension:${e.id}`,
        domain: 'extension',
        severity,
        label: `Extension · ${e.id}`,
        description: 'not installed · Install',
        tooltip: `Required extension ${e.id} is missing`,
        icon: 'extensions',
        command: 'workbench.extensions.search',
        commandArgs: [e.id]
      })
    }
  }

  if (pythonEnvsActive) {
    out.push({
      id: 'pyEnvs:active',
      domain: 'pyEnvs',
      severity: 'warning',
      label: 'Python Environments',
      description: 'high resource usage · Open',
      tooltip:
        'ms-python.vscode-python-envs continuously scans for interpreters. Click to open and disable.',
      icon: 'warning',
      command: 'extension.open',
      commandArgs: ['ms-python.vscode-python-envs']
    })
  }

  if (!configInWorkspace) {
    out.push({
      id: 'config:missing',
      domain: 'config',
      severity: 'warning',
      label: 'No config recommendations',
      description: 'evaluate independently',
      tooltip:
        'No workspace configuration files found in .ide/vscode/config/. Evaluate extensions and settings independently.',
      icon: 'warning'
    })
  }

  if (devSiteTools && !devSiteTools.installed) {
    out.push({
      id: 'devSite:missing',
      domain: 'devSite',
      severity: 'warning',
      label: 'cmk-dev-site',
      description: 'not installed · Install',
      tooltip: 'Click to install cmk-dev-site via pipx',
      icon: 'package',
      command: 'cmk.installDevSite'
    })
  }

  if (mypyTargets) {
    const stagedUnion = new Set<string>([
      ...mypyTargets.stagedActiveAdd,
      ...mypyTargets.stagedActiveRemove,
      ...mypyTargets.stagedBaselineAdd,
      ...mypyTargets.stagedBaselineRemove
    ])
    if (stagedUnion.size > 0) {
      out.push({
        id: 'mypy:staged',
        domain: 'mypy',
        severity: 'warning',
        label: 'Mypy targets',
        description: `${stagedUnion.size} pending · Apply`,
        tooltip: `Staged: ${[...stagedUnion].sort().join(', ')}\nClick to apply (restarts dmypy).`,
        icon: 'diff-added',
        command: 'cmk.mypy.applyStagedTargets'
      })
    }
    if (mypyTargets.dismissedPromptedTargets.length > 0) {
      const n = mypyTargets.dismissedPromptedTargets.length
      out.push({
        id: 'mypy:dismissed-prompts',
        domain: 'mypy',
        severity: 'info',
        label: 'Mypy prompts',
        description: `${n} dismissed · Review`,
        tooltip: `Prompted but not acted on: ${mypyTargets.dismissedPromptedTargets.join(', ')}\nClick to pick which targets to activate.`,
        icon: 'question',
        command: 'cmk.mypy.reviewDismissedPrompts'
      })
    }
  }

  if (allocator && mypyTargets?.pythonProfileActive) {
    if (allocator.mode === 'jemalloc') {
      const reasons: string[] = []
      if (!allocator.libraryAvailable) reasons.push('libjemalloc not found')
      if (!allocator.wrapperExists) reasons.push('wrapper missing')
      if (!allocator.dmypyExecutableMatches) reasons.push('dmypyExecutable mismatch')
      if (!allocator.runUsingInterpreterOff) reasons.push('runUsingActiveInterpreter still true')
      if (reasons.length > 0) {
        out.push({
          id: 'allocator:stale',
          domain: 'allocator',
          severity: 'warning',
          label: 'Mypy allocator',
          description: `${reasons.length} issue${reasons.length > 1 ? 's' : ''} · Reapply`,
          tooltip: `jemalloc configured but not active: ${reasons.join(', ')}. Click to re-run reconciliation.`,
          icon: 'warning',
          command: 'cmk.mypy.reapplyJemalloc'
        })
      }
    } else {
      const dismissed = !!allocator.recommendationDismissed
      out.push(
        allocator.libraryAvailable
          ? {
              id: 'allocator:recommend-enable',
              domain: 'allocator',
              severity: dismissed ? 'info' : 'warning',
              label: 'Mypy allocator',
              description: dismissed
                ? 'jemalloc available (dismissed) · Restore'
                : 'jemalloc available · Enable',
              tooltip: dismissed
                ? 'Cockpit recommendation is dismissed. Click to restore it.'
                : 'dmypy is on the default allocator. Switching to jemalloc caps long-running RSS growth.',
              icon: 'warning',
              command: dismissed
                ? 'cmk.cockpit.jemalloc.restoreRecommendation'
                : 'cmk.mypy.enableJemalloc'
            }
          : {
              id: 'allocator:recommend-install',
              domain: 'allocator',
              severity: dismissed ? 'info' : 'warning',
              label: 'Mypy allocator',
              description: dismissed
                ? 'libjemalloc missing (dismissed) · Restore'
                : 'libjemalloc missing · Install',
              tooltip: dismissed
                ? 'Cockpit recommendation is dismissed. Click to restore it.'
                : 'dmypy is on the default allocator. Install libjemalloc to cap long-running RSS growth.',
              icon: 'warning',
              command: dismissed
                ? 'cmk.cockpit.jemalloc.restoreRecommendation'
                : 'cmk.mypy.installJemalloc'
            }
      )
    }
  }

  if (mypyTargets?.pythonProfileActive && state.dmypyHealth?.stale) {
    out.push({
      id: 'dmypy:stale',
      domain: 'dmypy',
      severity: 'warning',
      label: 'dmypy daemon',
      description: 'config drifted · Restart',
      tooltip:
        '.vscode/.mypy.ini has been edited since the dmypy daemon started. Results may not reflect the on-disk config until the daemon is restarted.',
      icon: 'sync',
      command: 'cmk.mypy.restartDmypy'
    })
  }

  if (state.bazelCache?.overThreshold && state.bazelCache.sizeBytes !== null) {
    const sizeGiB = (state.bazelCache.sizeBytes / 1024 ** 3).toFixed(1)
    out.push({
      id: 'bazelCache:over-threshold',
      domain: 'bazelCache',
      severity: 'warning',
      label: 'Bazel disk cache',
      description: `${sizeGiB} GiB > ${state.bazelCache.thresholdGiB} GiB · Clean`,
      tooltip: `Bazel disk cache at ${state.bazelCache.cachePath} is ${sizeGiB} GiB (threshold ${state.bazelCache.thresholdGiB} GiB). Click to delete it; the next build will refill.`,
      icon: 'database',
      command: 'cmk.bazel.cleanDiskCache'
    })
  }

  if (state.startupRegression) {
    const r = state.startupRegression
    out.push({
      id: 'benchmark:startup-regression',
      domain: 'benchmark',
      severity: 'warning',
      label: 'Startup performance',
      description: `${r.ratio}× slower (${r.newMed}ms vs ${r.oldMed}ms) · View chart`,
      tooltip: `Recent CMK sidebar startup is materially slower than baseline (median ${r.newMed} ms vs ${r.oldMed} ms baseline). Click to open the startup benchmarks chart.`,
      icon: 'pulse',
      command: 'cmk.showStartupBenchmarks'
    })
  }

  if (pylanceHealth?.overThreshold && pylanceHealth.rssMiB !== null) {
    out.push({
      id: 'pylance:over-threshold',
      domain: 'pylance',
      severity: 'critical',
      label: 'Pylance memory',
      description: `${pylanceHealth.rssMiB} MiB > ${pylanceHealth.thresholdMiB} MiB · Restart`,
      tooltip:
        'Pylance language server RSS exceeded the configured threshold. Click to restart Pylance.',
      icon: 'warning',
      command: 'cmk.python.restartLanguageServer'
    })
  }

  // Pylance is required for active Python work; flag when the extension is
  // active but the process has gone away (crash), or when the user has the
  // Python profile on but the extension itself isn't active yet. Suppress
  // both warnings during the startup grace window — Pylance can take 20–30 s
  // to spin up and we don't want to call it "crashed" before it has tried.
  if (mypyTargets?.pythonProfileActive && pylanceHealth && !pylanceHealth.inStartupGrace) {
    if (!pylanceHealth.extensionActive) {
      out.push({
        id: 'pylance:extension-inactive',
        domain: 'pylance',
        severity: 'critical',
        label: 'Pylance extension',
        description: 'not active · Restart',
        tooltip:
          'Python profile is on but the ms-python.vscode-pylance extension is not active. Restart the language server.',
        icon: 'warning',
        command: 'cmk.python.restartLanguageServer'
      })
    } else if (pylanceHealth.monitored && pylanceHealth.pid === null) {
      out.push({
        id: 'pylance:no-process',
        domain: 'pylance',
        severity: 'critical',
        label: 'Pylance process',
        description: 'crashed (no process found) · Restart',
        tooltip:
          'Pylance was running and now has no detectable process — likely crashed. Click to restart.',
        icon: 'warning',
        command: 'cmk.python.restartLanguageServer'
      })
    }
  }

  // Git: pre-commit bypassed, pre-commit never installed, qa-test-data dirty.
  if (state.gitState?.preCommitMissing) {
    out.push({
      id: 'git:pre-commit-missing',
      domain: 'git',
      severity: 'info',
      label: 'Pre-commit hook',
      description: 'not installed · Install',
      tooltip:
        '.git/hooks/pre-commit is missing. Run `pre-commit install` to set it up so commits get linted and formatted before they land.',
      icon: 'info',
      command: 'cmk.installPreCommit'
    })
  }
  if (state.gitState?.preCommitSkipping) {
    const dismissed = !!state.gitState?.preCommitDismissed
    out.push({
      id: 'git:pre-commit-off',
      domain: 'git',
      severity: dismissed ? 'info' : 'warning',
      label: 'Pre-commit hook',
      description: dismissed ? 'bypassed (dismissed) · Restore' : 'bypassed · Re-enable',
      tooltip: dismissed
        ? 'Cockpit warning is dismissed for this workspace. Click to restore the warning.'
        : 'The pre-commit hook is disabled (.git/hooks/pre-commit moved aside). Click to re-enable.',
      icon: 'warning',
      command: dismissed ? 'cmk.cockpit.git.restorePreCommitWarning' : 'cmk.toggleSkipPreCommit'
    })
  }
  if (state.gitState?.qaTestDataDirty) {
    out.push({
      id: 'git:qa-test-data-dirty',
      domain: 'git',
      severity: 'warning',
      label: 'tests/qa-test-data',
      description: 'submodule dirty · Fix',
      tooltip:
        'tests/qa-test-data has uncommitted changes or its commit differs from the tracked gitlink. Click to reset it back to the tracked SHA (destructive).',
      icon: 'git-commit',
      command: 'cmk.fixQaTestDataSubmodule'
    })
  }

  // OMD: auth required → critical; any stopped site (without needing auth) → warning.
  if (omdSites && omdSites.length > 0) {
    const needsAuth = omdSites.some((s) => s.status.overall === -1)
    if (needsAuth) {
      out.push({
        id: 'omd:auth',
        domain: 'omd',
        severity: 'critical',
        label: 'OMD authentication',
        description: 'sudo required · Authenticate',
        tooltip:
          'OMD site status requires sudo. Click to open the YubiKey authentication terminal.',
        icon: 'shield',
        command: 'cmk.omdAuth'
      })
    } else {
      const stopped = omdSites.filter((s) => s.status.overall === 1)
      if (stopped.length > 0) {
        out.push({
          id: 'omd:stopped',
          domain: 'omd',
          severity: 'warning',
          label: 'OMD sites',
          description: `${stopped.length} stopped · Start`,
          tooltip: `Stopped: ${stopped.map((s) => s.name).join(', ')}. Click to pick one to start.`,
          icon: 'debug-stop',
          command: 'cmk.omdStart'
        })
      }
    }
  }

  return out
}

const ITEM_CAP = 8

/**
 * Roll up the issue list into per-domain summaries for the cockpit. Each entry
 * knows whether it's healthy, what to show, what to do, and lists up to
 * ITEM_CAP drill-down items for the per-row expansion.
 */
export function getDomainSummary(state: StateCache): DomainSummary {
  const issues = enumerateIssues(state)
  const byDomain = (preds: Issue['domain'][]) => issues.filter((i) => preds.includes(i.domain))

  // Builds — severity bubbles up from the per-target issues. venv missing is critical.
  const buildIssues = byDomain(['build'])
  const buildSeverity: Severity =
    buildIssues.length === 0
      ? 'ok'
      : buildIssues.some((i) => i.severity === 'critical')
        ? 'critical'
        : 'warning'
  const buildEntries = Object.entries(state.buildStatus || {})
  const staleBuilds = buildEntries.filter(([, s]) => !s.ok)
  const buildItems: DomainItem[] = staleBuilds.slice(0, ITEM_CAP).map(([key, s]) => ({
    id: `build:${key}`,
    severity: key === 'venv' ? 'critical' : 'warning',
    label: s.label,
    detail: key === 'venv' ? 'breaks mypy / Pylance' : 'needs building',
    command: s.commandId,
    actionLabel: 'Build'
  }))
  const builds: DomainEntry = {
    domain: 'builds',
    severity: buildSeverity,
    badge: staleBuilds.length > 0 ? `${staleBuilds.length} stale` : 'all up to date',
    glyph: 'tools',
    title: 'Builds',
    tooltipLines: staleBuilds.map(([, s]) => s.label),
    focusViewId: 'cmk.dashboard.environment.focus',
    focusViewName: 'Environment',
    command: staleBuilds.length > 0 ? 'cmk.buildAllStale' : undefined,
    actionVerb: staleBuilds.length > 0 ? 'Build all' : undefined,
    items: buildItems,
    totalItems: staleBuilds.length
  }

  // Settings — severity bubbles up: any active-profile-family drift makes the row critical.
  const settingsIssues = byDomain(['settings'])
  const settingsSeverity: Severity =
    settingsIssues.length === 0
      ? 'ok'
      : settingsIssues.some((i) => i.severity === 'critical')
        ? 'critical'
        : 'warning'
  const settingsItems: DomainItem[] = settingsIssues.slice(0, ITEM_CAP).map((i) => {
    // i.description is "<family> · <scope> · Apply" — split out family for the tag.
    const m = i.description.match(/^([^·]+) · ([^·]+) · /)
    return {
      id: i.id,
      severity: i.severity,
      label: i.label.replace(/^Settings · /, ''),
      detail: m ? m[2].trim() : i.description.replace(/ · Apply$/, ''),
      familyTag: m ? m[1].trim() : undefined,
      command: i.command,
      commandArgs: i.commandArgs,
      actionLabel: 'Apply'
    }
  })
  const settings: DomainEntry = {
    domain: 'settings',
    severity: settingsSeverity,
    badge: settingsIssues.length > 0 ? `${settingsIssues.length} drifted` : 'no drift',
    glyph: 'settings-gear',
    title: 'Settings',
    tooltipLines: settingsIssues.map((i) => i.label.replace(/^Settings · /, '')),
    focusViewId: 'cmk.dashboard.ideHealth.focus',
    focusViewName: 'IDE Health',
    actionVerb: settingsIssues.length > 0 ? 'Apply all' : undefined,
    items: settingsItems,
    totalItems: settingsIssues.length
  }

  // OMD — kept for Issues consumers; cockpit renderer ignores it.
  const omdSites = state.omdSites || []
  const auth = issues.find((i) => i.id === 'omd:auth')
  const stoppedIssue = issues.find((i) => i.id === 'omd:stopped')
  let omdSeverity: Severity = 'ok'
  let omdBadge: string
  if (auth) {
    omdSeverity = 'critical'
    omdBadge = 'sudo required'
  } else if (stoppedIssue) {
    omdSeverity = 'warning'
    const n = omdSites.filter((s) => s.status.overall === 1).length
    omdBadge = `${n} stopped`
  } else if (omdSites.length === 0) {
    omdBadge = 'no sites'
  } else {
    omdBadge = `${omdSites.length} running`
  }
  const omd: DomainEntry = {
    domain: 'omd',
    severity: omdSeverity,
    badge: omdBadge,
    glyph: 'server-environment',
    title: 'OMD',
    tooltipLines: omdSites.map((s) => s.name),
    focusViewId: 'cmk.dashboard.omd.focus',
    command: auth ? 'cmk.omdAuth' : stoppedIssue ? 'cmk.omdStart' : undefined,
    actionVerb: auth ? 'Authenticate' : stoppedIssue ? 'Start' : undefined,
    items: [],
    totalItems: 0
  }

  // Health — Pylance + allocator + mypy staged + pyEnvs, plus the previously
  // orphaned IDE-state floaters (version, extension, devSite, config).
  const healthIssues = byDomain([
    'pylance',
    'allocator',
    'mypy',
    'dmypy',
    'bazelCache',
    'benchmark',
    'pyEnvs',
    'version',
    'extension',
    'devSite',
    'config'
  ])
  let healthSeverity: Severity = 'ok'
  for (const i of healthIssues) healthSeverity = maxSev(healthSeverity, i.severity)
  const healthCritical = healthIssues.find((i) => i.severity === 'critical')
  const healthItems: DomainItem[] = healthIssues.slice(0, ITEM_CAP).map((i) => ({
    id: i.id,
    severity: i.severity,
    label: i.label,
    detail: i.description.replace(/ · \w+$/, ''),
    command: i.command,
    commandArgs: i.commandArgs,
    actionLabel: actionLabelFromDescription(i.description) ?? 'Fix',
    ...((i.id === 'allocator:recommend-enable' || i.id === 'allocator:recommend-install') &&
    i.severity !== 'info'
      ? {
          dismissCommand: 'cmk.cockpit.jemalloc.dismissRecommendation',
          dismissTitle: "Don't recommend jemalloc again"
        }
      : {}),
    ...(i.id === 'mypy:dismissed-prompts'
      ? {
          dismissCommand: 'cmk.mypy.clearDismissedPrompts',
          dismissTitle: 'Clear dismissed mypy prompts'
        }
      : {})
  }))
  const healthInfoOnly = healthIssues.filter((i) => i.severity !== 'info').length
  const health: DomainEntry = {
    domain: 'health',
    severity: healthSeverity,
    badge:
      healthSeverity === 'critical'
        ? `${healthInfoOnly} critical`
        : healthSeverity === 'warning'
          ? `${healthInfoOnly} warning${healthInfoOnly === 1 ? '' : 's'}`
          : healthSeverity === 'info'
            ? `${healthIssues.length} dismissed`
            : 'all green',
    glyph: 'pulse',
    title: 'Health',
    tooltipLines: healthIssues.map((i) => `${i.label} — ${i.description}`),
    focusViewId: 'cmk.dashboard.ideHealth.focus',
    focusViewName: 'IDE Health',
    command: healthCritical?.command ?? healthIssues[0]?.command,
    commandArgs: healthCritical?.commandArgs ?? healthIssues[0]?.commandArgs,
    actionVerb: healthCritical
      ? (actionLabelFromDescription(healthCritical.description) ?? 'Restart')
      : healthIssues[0]
        ? (actionLabelFromDescription(healthIssues[0].description) ?? 'Fix')
        : undefined,
    items: healthItems,
    totalItems: healthIssues.length
  }

  // Git — pre-commit hook + qa-test-data submodule.
  const gitIssues = byDomain(['git'])
  const gitSeverity: Severity = gitIssues.reduce<Severity>(
    (acc, i) => maxSev(acc, i.severity),
    'ok'
  )
  const gitItems: DomainItem[] = gitIssues.slice(0, ITEM_CAP).map((i) => ({
    id: i.id,
    severity: i.severity,
    label: i.label,
    detail: i.description.replace(/ · \w+$/, ''),
    command: i.command,
    commandArgs: i.commandArgs,
    actionLabel: actionLabelFromDescription(i.description) ?? 'Fix',
    // Dismiss-X is only meaningful while the item is active. Once dismissed
    // (severity=info), the action itself becomes "Restore" — no dismiss needed.
    ...(i.id === 'git:pre-commit-off' && i.severity !== 'info'
      ? {
          dismissCommand: 'cmk.cockpit.git.dismissPreCommit',
          dismissTitle: "Don't warn about this in this workspace"
        }
      : {})
  }))
  const git: DomainEntry = {
    domain: 'git',
    severity: gitSeverity,
    badge:
      gitIssues.length === 0
        ? 'clean'
        : gitSeverity === 'info'
          ? `${gitIssues.length} dismissed`
          : `${gitIssues.filter((i) => i.severity !== 'info').length} issue${gitIssues.filter((i) => i.severity !== 'info').length === 1 ? '' : 's'}`,
    glyph: 'source-control',
    title: 'Git',
    tooltipLines: gitIssues.map((i) => `${i.label} — ${i.description}`),
    focusViewId: 'workbench.scm.focus',
    focusViewName: 'Source Control',
    items: gitItems,
    totalItems: gitIssues.length
  }

  const overall = [builds, settings, omd, health, git].reduce<Severity>(
    (acc, d) => maxSev(acc, d.severity),
    'ok'
  )

  return {
    builds,
    settings,
    omd,
    health,
    git,
    overallSeverity: overall,
    totalIssues: issues.length
  }
}

/** Pull the trailing verb after the final " · " in an Issue description ("…· Restart" → "Restart"). */
function actionLabelFromDescription(description: string): string | undefined {
  const m = description.match(/·\s+([A-Z][a-zA-Z]+)\s*$/)
  return m ? m[1] : undefined
}

/** Classify an installed → workspace version diff as patch (warning) vs. minor/major (critical). */
function versionGap(installed: string, workspace: string): 'critical' | 'warning' {
  const parse = (v: string): [number, number, number] => {
    const m = v.match(/^(\d+)\.(\d+)\.(\d+)/)
    return m ? [Number(m[1]), Number(m[2]), Number(m[3])] : [0, 0, 0]
  }
  const [iMa, iMi] = parse(installed)
  const [wMa, wMi] = parse(workspace)
  return iMa !== wMa || iMi !== wMi ? 'critical' : 'warning'
}

const DOMAIN_RANK: Record<Issue['domain'], number> = {
  version: 0,
  extension: 1,
  build: 2,
  settings: 3,
  omd: 4,
  pylance: 5,
  allocator: 6,
  dmypy: 7,
  mypy: 8,
  benchmark: 9,
  bazelCache: 10,
  pyEnvs: 11,
  devSite: 12,
  config: 13,
  git: 14
}

/** Sort: critical first, then warning, then by domain rank, then alphabetical by label. */
export function sortIssues(issues: Issue[]): Issue[] {
  return [...issues].sort((a, b) => {
    const sev = SEV_RANK[b.severity] - SEV_RANK[a.severity]
    if (sev !== 0) return sev
    const dom = DOMAIN_RANK[a.domain] - DOMAIN_RANK[b.domain]
    if (dom !== 0) return dom
    return a.label.localeCompare(b.label)
  })
}

/** Build-target keys that "belong" to each profile (used by the Profiles section). */
const PROFILE_BUILD_KEYS: Record<string, string[]> = {
  python: ['venv', 'sharedTypingPy', 'mypyConfig'],
  frontend: ['sharedTypingTs', 'cmkFrontend', 'nodeModules'],
  rust: [],
  cpp: []
}

/** Display-family name (as set on SettingsMismatch.family) per profile. */
const PROFILE_TO_DISPLAY: Record<string, string> = {
  python: 'Python',
  frontend: 'UI',
  rust: 'Rust',
  cpp: 'C++'
}

/**
 * Aggregate the cockpit-severity for a given profile family by walking
 * settings + build issues attributable to that family. Health-domain issues
 * (Pylance, allocator, …) are intentionally NOT counted here — those are
 * tied to the workspace, not the profile toggle.
 */
export function getProfileSeverity(state: StateCache, family: string): Severity {
  const issues = enumerateIssues(state)
  const builds = new Set((PROFILE_BUILD_KEYS[family] || []).map((k) => `build:${k}`))
  const displayName = PROFILE_TO_DISPLAY[family]
  let sev: Severity = 'ok'
  for (const i of issues) {
    if (i.domain === 'build' && builds.has(i.id)) sev = maxSev(sev, i.severity)
    if (i.domain === 'settings' && displayName && i.description.startsWith(displayName + ' ·'))
      sev = maxSev(sev, i.severity)
  }
  return sev
}

/** "2 critical · 5 warning" or empty string when no issues. */
export function summaryHeader(issues: Issue[]): string {
  const c = issues.filter((i) => i.severity === 'critical').length
  const w = issues.filter((i) => i.severity === 'warning').length
  const parts: string[] = []
  if (c > 0) parts.push(`${c} critical`)
  if (w > 0) parts.push(`${w} warning`)
  return parts.join(' · ')
}
