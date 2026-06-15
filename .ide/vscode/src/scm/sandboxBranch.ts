/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as vscode from 'vscode'

import { log, notifyError } from '../core/log'
import { runCommand, waitForTask } from '../core/tasks'
import { currentBranch, gitAsync, isInternalCheckout, repoRoot } from './git'

const COMMON_BASES = ['master', '2.4.0', '2.3.0', '2.2.0']
const REMOTE_BRANCH_CAP = 100

type BranchInfo = {
  name: string
  hash: string
  when: string
  ts: number
  who: string
  upstream: string
  ahead: number
  behind: number
}

const REF_SEP = '<<CMK>>'

function parseTrack(track: string): { ahead: number; behind: number } {
  const ahead = /ahead (\d+)/.exec(track)?.[1]
  const behind = /behind (\d+)/.exec(track)?.[1]
  return { ahead: ahead ? parseInt(ahead, 10) : 0, behind: behind ? parseInt(behind, 10) : 0 }
}

function parseRefs(out: string): BranchInfo[] {
  return out
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [name, hash, when, ts, who, upstream, track] = line.split(REF_SEP)
      const { ahead, behind } = parseTrack(track ?? '')
      return {
        name: name ?? '',
        hash: hash ?? '',
        when: when ?? '',
        ts: ts ? parseInt(ts, 10) : 0,
        who: who ?? '',
        upstream: upstream ?? '',
        ahead,
        behind
      }
    })
    .filter((b) => b.name && !b.name.endsWith('/HEAD'))
}

function refsFormatArg(): string {
  const parts = [
    '%(refname:short)',
    '%(objectname:short)',
    '%(committerdate:relative)',
    '%(committerdate:unix)',
    '%(committername)',
    '%(upstream:short)',
    '%(upstream:track)'
  ]
  return `--format=${parts.join(REF_SEP)}`
}

async function listLocalBranches(cwd: string): Promise<BranchInfo[]> {
  const out = await gitAsync(cwd, [
    'for-each-ref',
    refsFormatArg(),
    '--sort=-committerdate',
    'refs/heads/'
  ])
  return parseRefs(out ?? '')
}

async function listRemoteBranches(cwd: string): Promise<BranchInfo[]> {
  const out = await gitAsync(cwd, [
    'for-each-ref',
    refsFormatArg(),
    '--sort=-committerdate',
    `--count=${REMOTE_BRANCH_CAP}`,
    'refs/remotes/'
  ])
  return parseRefs(out ?? '')
}

async function listRemoteBaseBranches(cwd: string): Promise<string[]> {
  const all = (await listRemoteBranches(cwd))
    .map((b) => b.name.replace(/^origin\//, ''))
    .filter((b) => b)
  const ordered: string[] = []
  for (const b of COMMON_BASES) if (all.includes(b)) ordered.push(b)
  for (const b of all) if (!ordered.includes(b)) ordered.push(b)
  return ordered
}

async function checkoutRef(ref: string): Promise<void> {
  try {
    const ext = vscode.extensions.getExtension('vscode.git')
    if (ext && !ext.isActive) await ext.activate()
    const api = ext?.exports.getAPI(1)
    const repo = api?.repositories?.[0]
    if (repo?.checkout) {
      await repo.checkout(ref)
      return
    }
  } catch (err) {
    log(`Git API checkout failed: ${(err as Error).message}; falling back to terminal`)
  }
  const cwd = repoRoot()
  if (!cwd) return
  const term = vscode.window.createTerminal({ name: `CMK: checkout ${ref}`, cwd })
  term.show()
  term.sendText(`git checkout ${ref}`)
}

async function pickBaseBranch(cwd: string): Promise<string | undefined> {
  const bases = await listRemoteBaseBranches(cwd)
  const items = bases.length > 0 ? bases : COMMON_BASES
  return vscode.window.showQuickPick(items, {
    title: 'CMK ▸ Create Sandbox Branch',
    placeHolder: 'Select base branch'
  })
}

async function promptTopic(base: string): Promise<string | undefined> {
  return vscode.window.showInputBox({
    title: `CMK ▸ Create Sandbox Branch (from ${base})`,
    prompt: 'Topic name (will become sandbox/<user>/<base>/<topic>)',
    placeHolder: 'my-feature',
    validateInput: (v) => {
      if (!v) return 'Topic name is required'
      if (!/^[A-Za-z0-9._/-]+$/.test(v))
        return 'Use letters, digits, dot, dash, underscore, slash only'
      return undefined
    }
  })
}

/** Force VS Code's git extension to re-read repository state. `git workon`
 *  switches HEAD outside the git API, so the SCM view can stay stale until the
 *  next manual refresh; calling `repo.status()` (or the `git.refresh` command
 *  as a fallback) brings it back in sync immediately. */
async function refreshScmView(cwd: string): Promise<void> {
  try {
    const ext = vscode.extensions.getExtension('vscode.git')
    if (ext && !ext.isActive) await ext.activate()
    const api = ext?.exports.getAPI(1)
    const repo =
      api?.repositories?.find((r: { rootUri: vscode.Uri }) => r.rootUri.fsPath === cwd) ??
      api?.repositories?.[0]
    if (repo?.status) {
      await repo.status()
      return
    }
  } catch (err) {
    log(`Git API refresh failed: ${(err as Error).message}; falling back to git.refresh`)
  }
  try {
    await vscode.commands.executeCommand('git.refresh')
  } catch {
    // ignore
  }
}

function runWorkonInTerminal(base: string, topic: string, cwd: string): void {
  const term = vscode.window.createTerminal({ name: `CMK: workon ${base}/${topic}`, cwd })
  term.show()
  term.sendText(`git workon ${base} ${topic}`)
}

/** Run `git workon` as an awaitable task so the SCM view can be refreshed once
 *  the branch switch finishes. Falls back to a plain terminal (no refresh) when
 *  the task cannot be launched. */
async function runWorkon(base: string, topic: string, cwd: string): Promise<void> {
  const execution = runCommand(`workon ${base}/${topic}`, `git workon ${base} ${topic}`)
  if (!execution) {
    runWorkonInTerminal(base, topic, cwd)
    return
  }
  const exitCode = await waitForTask(execution)
  if (exitCode === 0 || exitCode === undefined) await refreshScmView(cwd)
}

async function createSandboxBranch(): Promise<void> {
  const cwd = repoRoot()
  if (!cwd) {
    notifyError('CMK: No workspace folder found.')
    return
  }
  const base = await pickBaseBranch(cwd)
  if (!base) return
  const topic = await promptTopic(base)
  if (!topic) return
  log(`Create sandbox branch: base=${base} topic=${topic}`)
  await runWorkon(base, topic, cwd)
}

type Action = 'create-sandbox' | 'create-branch' | 'create-branch-from' | 'checkout'
type CheckoutItem = vscode.QuickPickItem & { action?: Action; ref?: string }

function syncBadge(b: BranchInfo): string {
  const parts: string[] = []
  if (b.behind > 0) parts.push(`↓${b.behind}`)
  if (b.ahead > 0) parts.push(`↑${b.ahead}`)
  return parts.join(' ')
}

function refDescription(b: BranchInfo, remoteByName: Map<string, string>): string {
  const baseHash = b.upstream ? remoteByName.get(b.upstream) : undefined
  return [syncBadge(b), baseHash ? `← ${baseHash}` : ''].filter(Boolean).join('  ')
}

function refDetail(b: BranchInfo): string {
  return [b.who, b.hash, b.when].filter(Boolean).join(' · ')
}

const CREATE_ITEMS: CheckoutItem[] = [
  { label: '$(plus) Create new branch...', action: 'create-branch' },
  { label: '$(plus) Create new branch from...', action: 'create-branch-from' },
  {
    label: '$(plus) Create Sandbox Branch...',
    description: 'via git workon',
    action: 'create-sandbox'
  }
]

function buildCheckoutItems(
  local: BranchInfo[],
  remote: BranchInfo[],
  current: string
): CheckoutItem[] {
  const remoteByName = new Map(remote.map((b) => [b.name, b.hash]))
  const items: CheckoutItem[] = [...CREATE_ITEMS]

  const localCurrent = current ? local.find((b) => b.name === current) : undefined
  const sortedLocal = [
    ...(localCurrent ? [localCurrent] : []),
    ...local.filter((b) => b.name !== current)
  ]
  if (sortedLocal.length > 0) {
    items.push({ label: 'branches', kind: vscode.QuickPickItemKind.Separator })
    for (const b of sortedLocal) {
      const prefix = b.name === current ? '$(check)' : '$(git-branch)'
      items.push({
        label: `${prefix} ${b.name}`,
        description: refDescription(b, remoteByName),
        detail: refDetail(b),
        action: 'checkout',
        ref: b.name
      })
    }
  }

  if (remote.length > 0) {
    items.push({ label: 'remote branches', kind: vscode.QuickPickItemKind.Separator })
    for (const b of remote) {
      items.push({
        label: `$(cloud) ${b.name}`,
        detail: refDetail(b),
        action: 'checkout',
        ref: b.name
      })
    }
  }
  return items
}

async function checkoutBranch(): Promise<void> {
  const cwd = repoRoot()
  if (!cwd) {
    notifyError('CMK: No workspace folder found.')
    return
  }

  // Open the QuickPick immediately with the create-branch options so the user
  // sees the UI before the git for-each-ref calls finish.
  const qp = vscode.window.createQuickPick<CheckoutItem>()
  qp.title = 'Select a ref to checkout'
  qp.matchOnDetail = true
  qp.busy = true
  qp.items = CREATE_ITEMS
  qp.show()

  const loadingPromise = Promise.all([
    listLocalBranches(cwd),
    listRemoteBranches(cwd),
    Promise.resolve(currentBranch(cwd))
  ]).then(([local, remote, current]) => {
    qp.items = buildCheckoutItems(local, remote, current)
    qp.busy = false
    return current
  })

  const pickedItem = await new Promise<CheckoutItem | undefined>((resolve) => {
    qp.onDidAccept(() => {
      const item = qp.selectedItems[0]
      qp.hide()
      resolve(item)
    })
    qp.onDidHide(() => resolve(undefined))
  })
  const current = await loadingPromise
  qp.dispose()
  if (!pickedItem) return

  switch (pickedItem.action) {
    case 'create-sandbox':
      await createSandboxBranch()
      return
    case 'create-branch':
      await vscode.commands.executeCommand('git.branch')
      return
    case 'create-branch-from':
      await vscode.commands.executeCommand('git.branchFrom')
      return
    case 'checkout':
      if (pickedItem.ref && pickedItem.ref !== current) await checkoutRef(pickedItem.ref)
      return
  }
}

function createCheckoutStatusBar(context: vscode.ExtensionContext): void {
  const item = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 1002)
  item.command = 'cmk.checkoutBranch'
  item.text = '$(git-branch)'
  item.tooltip = 'CMK ▸ Checkout branch (with sandbox option)'
  item.show()
  context.subscriptions.push(item)
}

export function registerSandboxBranch(context: vscode.ExtensionContext): void {
  context.subscriptions.push(
    vscode.commands.registerCommand('cmk.createSandboxBranch', createSandboxBranch),
    vscode.commands.registerCommand('cmk.checkoutBranch', checkoutBranch)
  )
  // The custom branch-checkout button drives the internal sandbox (git workon)
  // workflow, so only surface it on an internal checkout. Community clones use
  // VS Code's built-in SCM branch controls instead.
  const cwd = repoRoot()
  if (cwd && isInternalCheckout(cwd)) createCheckoutStatusBar(context)
}
