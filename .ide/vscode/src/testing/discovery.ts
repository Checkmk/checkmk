/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { spawn } from 'child_process'
import * as fs from 'fs'
import * as path from 'path'
import * as vscode from 'vscode'

import { CC_TEST_RULE_REGEX } from './runners/cc'
import { PY_DOC_TEST_RULE_REGEX } from './runners/pydoctest'
import { PY_TEST_RULE_REGEX } from './runners/pytest'
import { RUST_TEST_RULE_REGEX } from './runners/rust'
import { VITEST_TEST_RULE_REGEX } from './runners/vitest'
import type { DiscoveredTarget, RuleKind } from './types'

const SKIP_DIR_NAMES = [
  '__pycache__',
  'qa-test-data',
  'typeshed',
  'data',
  'fixtures',
  'node_modules',
  '.venv',
  '.git',
  '.tox',
  '.pytest_cache',
  '.mypy_cache',
  '.ruff_cache'
]

export const DISCOVERY_ROOTS = ['tests', 'packages', 'non-free/packages', '.ide']

const RULE_DEFS: Array<{ regex: RegExp; kind: RuleKind }> = [
  { regex: PY_TEST_RULE_REGEX, kind: 'py_test' },
  { regex: PY_DOC_TEST_RULE_REGEX, kind: 'py_doc_test' },
  { regex: VITEST_TEST_RULE_REGEX, kind: 'vitest_test' },
  { regex: RUST_TEST_RULE_REGEX, kind: 'rust_test' },
  { regex: CC_TEST_RULE_REGEX, kind: 'cc_test' }
]

async function listBuildFilesViaFind(wsPath: string): Promise<string[]> {
  const existing = DISCOVERY_ROOTS.filter((r) => fs.existsSync(path.join(wsPath, r)))
  if (existing.length === 0) return []
  return new Promise((resolve, reject) => {
    const args: string[] = [...existing, '-mindepth', '1', '-type', 'd', '(']
    SKIP_DIR_NAMES.forEach((name, i) => {
      if (i > 0) args.push('-o')
      args.push('-name', name)
    })
    args.push('-o', '-name', 'bazel-*')
    args.push(')', '-prune')
    args.push(
      '-o',
      '-type',
      'f',
      '(',
      '-name',
      'BUILD',
      '-o',
      '-name',
      'BUILD.bazel',
      ')',
      '-print'
    )
    const child = spawn('find', args, { cwd: wsPath })
    let stdout = ''
    child.stdout.on('data', (d) => (stdout += d.toString()))
    child.on('error', reject)
    child.on('close', () =>
      resolve(
        stdout
          .split('\n')
          .filter(Boolean)
          .map((rel) => path.join(wsPath, rel))
      )
    )
  })
}

async function parseBuildForTargets(
  wsPath: string,
  buildPath: string
): Promise<DiscoveredTarget[]> {
  let content: string
  try {
    content = await fs.promises.readFile(buildPath, 'utf-8')
  } catch {
    return []
  }
  const pkg = path.relative(wsPath, path.dirname(buildPath))
  const out: DiscoveredTarget[] = []
  for (const { regex, kind } of RULE_DEFS) {
    regex.lastIndex = 0
    let m: RegExpExecArray | null
    while ((m = regex.exec(content)) !== null) {
      out.push({ label: `//${pkg}:${m[1]}`, kind })
    }
  }
  return out
}

export async function discoverTargetsFromFilesystem(wsPath: string): Promise<DiscoveredTarget[]> {
  const buildFiles = await listBuildFilesViaFind(wsPath)
  const lists = await Promise.all(buildFiles.map((bf) => parseBuildForTargets(wsPath, bf)))
  return lists.flat()
}

function topLevelGrouping(pkg: string): string {
  const parts = pkg.split('/')
  if (parts[0] === 'non-free' && parts[1] === 'packages') return 'non-free/packages'
  return parts[0]
}

function topLevelLabel(pkg: string): string {
  if (pkg === 'tests' || pkg.startsWith('tests/')) return path.basename(pkg)
  return pkg
}

export function populateRootPackages(
  controller: vscode.TestController,
  targets: DiscoveredTarget[],
  wsPath: string
): void {
  const topPkgs = new Set<string>()
  for (const t of targets) {
    const pkg = t.label.replace(/^\/\//, '').split(':')[0]
    topPkgs.add(topLevelGrouping(pkg))
  }
  const items: vscode.TestItem[] = []
  for (const pkg of Array.from(topPkgs).sort()) {
    const item = controller.createTestItem(
      `//${pkg}`,
      topLevelLabel(pkg),
      vscode.Uri.file(path.join(wsPath, pkg))
    )
    item.canResolveChildren = true
    items.push(item)
  }
  controller.items.replace(items)
}

export function populateFolderChildren(
  controller: vscode.TestController,
  folder: vscode.TestItem,
  targets: DiscoveredTarget[],
  wsPath: string,
  kindByLabel: Map<string, RuleKind>
): void {
  if (folder.children.size > 0) return
  const folderPkg = folder.id.replace(/^\/\//, '')
  const directSubPkgs = new Set<string>()
  const directTargets: DiscoveredTarget[] = []
  for (const t of targets) {
    const without = t.label.replace(/^\/\//, '')
    const idx = without.indexOf(':')
    if (idx < 0) continue
    const pkg = without.slice(0, idx)
    if (pkg === folderPkg) {
      directTargets.push(t)
    } else if (pkg.startsWith(folderPkg + '/')) {
      const next = pkg.slice(folderPkg.length + 1).split('/')[0]
      directSubPkgs.add(`${folderPkg}/${next}`)
    }
  }
  for (const subPkg of Array.from(directSubPkgs).sort()) {
    const sub = controller.createTestItem(
      `//${subPkg}`,
      path.basename(subPkg),
      vscode.Uri.file(path.join(wsPath, subPkg))
    )
    sub.canResolveChildren = true
    folder.children.add(sub)
  }
  for (const t of directTargets.sort((a, b) => a.label.localeCompare(b.label))) {
    const without = t.label.replace(/^\/\//, '')
    const colon = without.indexOf(':')
    const pkg = without.slice(0, colon)
    const name = without.slice(colon + 1)
    const buildFile = path.join(wsPath, pkg, 'BUILD')
    const targetUri = fs.existsSync(buildFile) ? vscode.Uri.file(buildFile) : undefined
    const targetItem = controller.createTestItem(t.label, name, targetUri)
    targetItem.canResolveChildren = true
    targetItem.description = t.kind
    folder.children.add(targetItem)
    kindByLabel.set(t.label, t.kind)
  }
}
