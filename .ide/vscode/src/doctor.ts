/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as fs from 'fs'
import * as os from 'os'
import * as path from 'path'
import * as vscode from 'vscode'

import { availableEditions, effectiveEdition, isNonFreeAvailable } from './core/editions'
import { type ActivityEvent, getActivityEvents, log } from './core/log'
import { currentBranch, isInternalCheckout, repoRoot } from './scm/git'
import { getState } from './sidebar'
import {
  type Issue,
  enumerateIssues,
  sortIssues,
  summaryHeader
} from './sidebar/overview/domainSummary'
import type { StateCache } from './sidebar/types'

/** Stringify a setting value compactly; mark explicit `undefined` as unset. */
function j(value: unknown): string {
  if (value === undefined) return '(unset)'
  try {
    return JSON.stringify(value)
  } catch {
    return String(value)
  }
}

function tick(ok: boolean): string {
  return ok ? '✓' : '✗'
}

const OMD_OVERALL: Record<number, string> = {
  [-1]: 'unknown / needs auth',
  0: 'running',
  1: 'stopped',
  2: 'partial',
  3: 'disabled'
}

/** Inspect a single config key across scopes and render one bullet. */
function settingLine(key: string, folderUri?: vscode.Uri): string {
  const insp = vscode.workspace.getConfiguration(undefined, folderUri).inspect<unknown>(key)
  const scopes: string[] = []
  if (insp?.workspaceFolderValue !== undefined)
    scopes.push(`folder=${j(insp.workspaceFolderValue)}`)
  if (insp?.workspaceValue !== undefined) scopes.push(`workspace=${j(insp.workspaceValue)}`)
  if (insp?.globalValue !== undefined) scopes.push(`user=${j(insp.globalValue)}`)
  const effective =
    insp?.workspaceFolderValue ?? insp?.workspaceValue ?? insp?.globalValue ?? insp?.defaultValue
  const origin = scopes.length ? scopes.join(', ') : `default ${j(insp?.defaultValue)}`
  return `- \`${key}\` = ${j(effective)}  ·  ${origin}`
}

/** Pull the declared `cmk.*` config keys from the bundled package.json. */
function declaredCmkSettingKeys(context: vscode.ExtensionContext): string[] {
  const conf = context.extension.packageJSON?.contributes?.configuration
  const blocks = Array.isArray(conf) ? conf : conf ? [conf] : []
  const keys = new Set<string>()
  for (const block of blocks) {
    for (const key of Object.keys(block?.properties ?? {})) keys.add(key)
  }
  return [...keys].sort()
}

function workspaceVersion(root: string | undefined): string {
  if (!root) return '(no workspace)'
  try {
    const pkg = path.join(root, '.ide', 'vscode', 'package.json')
    return JSON.parse(fs.readFileSync(pkg, 'utf8')).version ?? '(unknown)'
  } catch {
    return '(unreadable)'
  }
}

function fmtEvent(e: ActivityEvent): string {
  const ts = new Date(e.ts).toISOString().slice(0, 19).replace('T', ' ')
  return `${ts}  ${e.level.padEnd(5)} [${e.category}] ${e.message}`
}

function issueLines(issues: Issue[]): string[] {
  if (issues.length === 0) return ['_No issues detected._']
  return issues.map(
    (i) =>
      `- **[${i.severity}]** ${i.label} — ${i.description}${i.tooltip ? `\n  - ${i.tooltip}` : ''}`
  )
}

/** Assemble the full Markdown diagnostics report. */
function buildReport(context: vscode.ExtensionContext, state: StateCache): string {
  const root = repoRoot()
  const folderUri = vscode.workspace.workspaceFolders?.[0]?.uri
  const issues = sortIssues(enumerateIssues(state))
  const env = state.environment
  const out: string[] = []
  const generated = new Date().toISOString()

  out.push('# CMK Diagnostics Report')
  out.push('')
  out.push(`_Generated ${generated}_`)
  out.push('')
  out.push(summaryHeader(issues))
  out.push('')

  out.push('## Overview')
  out.push('')
  out.push(`- Extension (installed): \`${context.extension.packageJSON.version}\``)
  out.push(`- Extension (workspace): \`${workspaceVersion(root)}\``)
  out.push(`- VS Code: \`${vscode.version}\``)
  out.push(
    `- Platform: \`${os.type()} ${os.release()} ${os.arch()}\` · Node \`${process.version}\``
  )
  out.push(`- Repo root: \`${root ?? '(not a git repo)'}\``)
  out.push(`- Branch: \`${root ? currentBranch(root) || '(detached?)' : '(n/a)'}\``)
  out.push(`- Internal checkout: ${root ? tick(isInternalCheckout(root)) : '(n/a)'}`)
  out.push(
    `- Edition: \`${effectiveEdition()}\` · non-free tree present: ${tick(isNonFreeAvailable())} · selectable: ${availableEditions().join(', ')}`
  )
  out.push(`- Config loaded from workspace: ${tick(state.configInWorkspace)}`)
  if (state.versionMismatch) {
    out.push(
      `- ⚠ Version mismatch: installed ${state.versionMismatch.installed} ≠ workspace ${state.versionMismatch.workspace}`
    )
  }
  out.push('')

  out.push(`## Issues (${issues.length})`)
  out.push('')
  out.push(...issueLines(issues))
  out.push('')

  out.push('## Environment')
  out.push('')
  out.push(`- System ready: ${tick(env.systemReady)}`)
  out.push(
    `- Python: \`${env.python || '?'}\` (\`${env.pythonPath || '?'}\`) · pyenv: ${tick(env.pyenv)}`
  )
  out.push(`- Node: \`${env.node || '?'}\` · pnpm: \`${env.pnpm || '?'}\``)
  out.push(`- Bazel: \`${env.bazel || '?'}\` · bazelisk: \`${env.bazelisk || '?'}\``)
  out.push(`- gcc: \`${env.gcc || '?'}\` · docker: \`${env.docker || '?'}\``)
  out.push(`- Python Environments extension active: ${tick(state.pythonEnvsActive)}`)
  out.push('')

  out.push('## Build status')
  out.push('')
  for (const [id, t] of Object.entries(state.buildStatus)) {
    out.push(`- ${tick(t.ok)} ${t.label} (\`${id}\`)${t.ok ? '' : ` → \`${t.commandId}\``}`)
  }
  out.push('')

  out.push('## Profiles')
  out.push('')
  for (const p of state.profiles) {
    const flags = [
      p.active ? 'active' : 'inactive',
      p.loading ? 'loading' : null,
      p.hasIssues ? 'has-issues' : null
    ]
      .filter(Boolean)
      .join(', ')
    out.push(`- ${p.label} (\`${p.name}\`): ${flags}`)
  }
  out.push('')

  out.push('## Health')
  out.push('')
  const dm = state.dmypyHealth
  out.push(`- dmypy: running ${tick(dm.running)}, stale ${tick(dm.stale)}`)
  const bc = state.bazelCache
  const cacheGiB = bc.sizeBytes == null ? '?' : (bc.sizeBytes / 1024 ** 3).toFixed(1)
  out.push(
    `- Bazel disk cache: ${cacheGiB} GiB / warn ${bc.thresholdGiB} GiB (over: ${tick(bc.overThreshold)}) · \`${bc.cachePath ?? '?'}\``
  )
  const al = state.allocator
  out.push(
    `- Allocator: ${al.mode} (lib available: ${tick(al.libraryAvailable)}, wrapper: ${tick(al.wrapperExists)}, dmypy matches: ${tick(al.dmypyExecutableMatches)})`
  )
  const pl = state.pylanceHealth
  out.push(
    `- Pylance: ${pl.monitored ? 'monitored' : 'not monitored'}, active ${tick(pl.extensionActive)}, RSS ${pl.rssMiB ?? '?'} MiB / warn ${pl.thresholdMiB} MiB (over: ${tick(pl.overThreshold)})`
  )
  const g = state.gitState
  out.push(
    `- Git: pre-commit skipping ${tick(g.preCommitSkipping)}, missing ${tick(g.preCommitMissing)}, qa-test-data dirty ${tick(g.qaTestDataDirty)}`
  )
  const mt = state.mypyTargets
  out.push(
    `- Mypy targets: enabled ${tick(mt.enabled)}, active ${mt.activeCount}/${mt.catalogSize}, staged +${mt.stagedActiveAdd.length}/-${mt.stagedActiveRemove.length}`
  )
  if (state.startupRegression) {
    const r = state.startupRegression
    out.push(
      `- ⚠ Startup regression: ${r.newMed.toFixed(0)} ms vs ${r.oldMed.toFixed(0)} ms (×${r.ratio.toFixed(2)})`
    )
  }
  out.push('')

  out.push('## OMD')
  out.push('')
  out.push(
    `- cmk-dev-site: installed ${tick(state.devSiteTools.installed)} \`${state.devSiteTools.installedVersion || '-'}\``
  )
  if (state.omdSites.length === 0) {
    out.push('- No OMD sites detected.')
  } else {
    for (const s of state.omdSites) {
      out.push(
        `- \`${s.name}\` — ${OMD_OVERALL[s.status.overall] ?? '?'} · v${s.version} · ${s.edition} · port ${s.port || '-'}`
      )
    }
  }
  if (state.activeProxies.length > 0) {
    out.push('- Active socket proxies:')
    for (const px of state.activeProxies) {
      out.push(`  - ${px.site}/${px.service} → :${px.port} (${px.ready ? 'ready' : 'starting'})`)
    }
  }
  out.push('')

  out.push('## CMK settings')
  out.push('')
  for (const key of declaredCmkSettingKeys(context)) {
    out.push(settingLine(key, folderUri))
  }
  out.push('')
  out.push('### Related VS Code settings')
  out.push('')
  for (const key of ['editor.formatOnSave', 'git.branchProtection', 'mypy-type-checker.args']) {
    out.push(settingLine(key, folderUri))
  }
  out.push('')

  out.push('## Managed setting mismatches')
  out.push('')
  if (state.settingsMismatches.length === 0) {
    out.push('_All managed settings match the expected values._')
  } else {
    for (const m of state.settingsMismatches) {
      out.push(
        `- \`${m.key}\` [${m.family}/${m.scope}] expected ${j(m.expected)}, actual ${j(m.actual)}`
      )
    }
  }
  out.push('')

  const events = getActivityEvents()
  out.push(`## Activity log (last ${Math.min(events.length, 100)} of ${events.length})`)
  out.push('')
  out.push('```text')
  out.push(...events.slice(-100).map(fmtEvent))
  out.push('```')
  out.push('')

  return out.join('\n')
}

export function registerDoctor(context: vscode.ExtensionContext): vscode.Disposable {
  return vscode.commands.registerCommand('cmk.collectDiagnostics', async () => {
    log('Collect diagnostics report')
    const report = buildReport(context, getState())
    await vscode.env.clipboard.writeText(report)
    const doc = await vscode.workspace.openTextDocument({ content: report, language: 'markdown' })
    await vscode.window.showTextDocument(doc, { preview: false })
    void vscode.window.showInformationMessage(
      'CMK: Diagnostics report generated and copied to clipboard.'
    )
  })
}
