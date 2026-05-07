/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as fs from 'fs'
import * as path from 'path'
import * as vscode from 'vscode'

import type { RuleKind } from './types'

export function fileItemId(targetId: string, relPath: string): string {
  return `${targetId}::F::${relPath}`
}

export function functionItemId(targetId: string, relPath: string, funcName: string): string {
  return `${fileItemId(targetId, relPath)}::${funcName}`
}

export function syntheticFolderId(targetId: string, relDir: string): string {
  return `${targetId}::D::${relDir}`
}

export function classifyItem(
  item: vscode.TestItem
): 'placeholder' | 'folder' | 'target' | 'file' | 'function' {
  if (item.id.startsWith('__cmk_bazel_')) return 'placeholder'
  if (item.id.includes('::F::')) {
    const parts = item.id.split('::F::')
    return parts[1].includes('::') ? 'function' : 'file'
  }
  if (item.id.includes('::D::')) return 'folder'
  if (item.id.includes(':')) return 'target'
  return 'folder'
}

export function findTargetAncestor(item: vscode.TestItem): vscode.TestItem | undefined {
  let cur: vscode.TestItem | undefined = item
  while (cur) {
    if (classifyItem(cur) === 'target') return cur
    cur = cur.parent
  }
  return undefined
}

export function targetSyntheticRoot(targetId: string, kind: RuleKind): string | undefined {
  const without = targetId.replace(/^\/\//, '')
  const colon = without.indexOf(':')
  if (colon < 0) return undefined
  const pkg = without.slice(0, colon)
  return kind === 'vitest_test' ? `${pkg}/tests` : pkg
}

export function getOrCreateSyntheticFolderChain(
  controller: vscode.TestController,
  targetItem: vscode.TestItem,
  wsPath: string,
  fileRelPath: string,
  kind: RuleKind
): vscode.TestItem {
  const root = targetSyntheticRoot(targetItem.id, kind)
  if (!root) return targetItem
  const fileDir = path.dirname(fileRelPath)
  if (fileDir !== root && !fileDir.startsWith(root + '/')) return targetItem
  const relFromRoot = path.relative(root, fileDir)
  if (!relFromRoot || relFromRoot === '.') return targetItem
  const segments = relFromRoot.split(path.sep)
  let current: vscode.TestItem = targetItem
  let cumulative = root
  for (const seg of segments) {
    cumulative = `${cumulative}/${seg}`
    const id = syntheticFolderId(targetItem.id, cumulative)
    let child = current.children.get(id)
    if (!child) {
      child = controller.createTestItem(id, seg, vscode.Uri.file(path.join(wsPath, cumulative)))
      current.children.add(child)
    }
    current = child
  }
  return current
}

export function getOrCreateFileItem(
  controller: vscode.TestController,
  targetItem: vscode.TestItem,
  parent: vscode.TestItem,
  wsPath: string,
  relPath: string
): vscode.TestItem {
  const id = fileItemId(targetItem.id, relPath)
  const existing = parent.children.get(id)
  if (existing) return existing
  const abs = path.join(wsPath, relPath)
  const uri = fs.existsSync(abs) ? vscode.Uri.file(abs) : undefined
  const fileItem = controller.createTestItem(id, path.basename(relPath), uri)
  if (parent === targetItem) {
    const dir = path.dirname(relPath)
    fileItem.description = dir === '.' ? '' : dir
  }
  parent.children.add(fileItem)
  return fileItem
}

export function getOrCreateFunctionItem(
  controller: vscode.TestController,
  fileItem: vscode.TestItem,
  fileAbsPath: string,
  funcName: string,
  line?: number,
  findLineFallback?: (filePath: string, name: string) => number | undefined
): vscode.TestItem {
  const targetId = fileItem.id.split('::F::')[0]
  const relPath = fileItem.id.split('::F::')[1]
  const id = functionItemId(targetId, relPath, funcName)
  const existing = fileItem.children.get(id)
  if (existing) return existing
  const uri = fs.existsSync(fileAbsPath) ? vscode.Uri.file(fileAbsPath) : undefined
  const funcItem = controller.createTestItem(id, funcName, uri)
  const ln = line !== undefined ? line : findLineFallback?.(fileAbsPath, funcName)
  if (ln !== undefined && ln >= 0) funcItem.range = new vscode.Range(ln, 0, ln, 0)
  fileItem.children.add(funcItem)
  return funcItem
}
