/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as vscode from 'vscode'

import { log, notifyError } from '../core/log'
import { safeExec } from '../core/shell'

const COMMON_BASES = ['master', '2.4.0', '2.3.0', '2.2.0']

function repoRoot(): string | undefined {
  return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
}

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

function refsFormat(): string {
  const parts = [
    '%(refname:short)',
    '%(objectname:short)',
    '%(committerdate:relative)',
    '%(committerdate:unix)',
    '%(committername)',
    '%(upstream:short)',
    '%(upstream:track)'
  ]
  return `'--format=${parts.join(REF_SEP)}'`
}

function listLocalBranches(cwd: string): BranchInfo[] {
  const out = safeExec(`git for-each-ref ${refsFormat()} refs/heads/`, { cwd })
  return parseRefs(out)
}

function listRemoteBranches(cwd: string): BranchInfo[] {
  const out = safeExec(`git for-each-ref ${refsFormat()} refs/remotes/`, { cwd })
  return parseRefs(out)
}

function listRemoteBaseBranches(cwd: string): string[] {
  const all = listRemoteBranches(cwd)
    .map((b) => b.name.replace(/^origin\//, ''))
    .filter((b) => b)
  const ordered: string[] = []
  for (const b of COMMON_BASES) if (all.includes(b)) ordered.push(b)
  for (const b of all) if (!ordered.includes(b)) ordered.push(b)
  return ordered
}

function currentBranch(cwd: string): string {
  return safeExec('git rev-parse --abbrev-ref HEAD', { cwd })
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
  const bases = listRemoteBaseBranches(cwd)
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

function runWorkonInTerminal(base: string, topic: string, cwd: string): void {
  const term = vscode.window.createTerminal({ name: `CMK: workon ${base}/${topic}`, cwd })
  term.show()
  term.sendText(`git workon ${base} ${topic}`)
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
  runWorkonInTerminal(base, topic, cwd)
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

async function checkoutBranch(): Promise<void> {
  const cwd = repoRoot()
  if (!cwd) {
    notifyError('CMK: No workspace folder found.')
    return
  }
  const local = listLocalBranches(cwd)
  const remote = listRemoteBranches(cwd)
  const current = currentBranch(cwd)
  const remoteByName = new Map(remote.map((b) => [b.name, b.hash]))

  const items: CheckoutItem[] = [
    { label: '$(plus) Create new branch...', action: 'create-branch' },
    { label: '$(plus) Create new branch from...', action: 'create-branch-from' },
    {
      label: '$(plus) Create Sandbox Branch...',
      description: 'via git workon',
      action: 'create-sandbox'
    }
  ]

  const localCurrent = current ? local.find((b) => b.name === current) : undefined
  const sortedLocal = [
    ...(localCurrent ? [localCurrent] : []),
    ...local.filter((b) => b.name !== current).sort((a, b) => b.ts - a.ts)
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

  const pick = await vscode.window.showQuickPick(items, {
    title: 'Select a ref to checkout',
    placeHolder: '',
    matchOnDetail: true
  })
  if (!pick) return

  switch (pick.action) {
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
      if (pick.ref && pick.ref !== current) await checkoutRef(pick.ref)
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
  createCheckoutStatusBar(context)
}
