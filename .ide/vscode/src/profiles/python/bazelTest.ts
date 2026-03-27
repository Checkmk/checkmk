/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { execSync } from 'child_process'
import * as fs from 'fs'
import * as path from 'path'
import * as vscode from 'vscode'

import { shellEscape } from '../../core/config'
import { notifyError, notifyInfo, notifyWarn } from '../../core/log'
import { runCommand, waitForTask } from '../../core/tasks'

function getWorkspacePath(): string | undefined {
  return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
}

function findBazelTarget(filePath: string, wsPath: string): string | null {
  let dir = path.dirname(filePath)

  while (dir.startsWith(wsPath) && dir !== wsPath) {
    const buildFile = path.join(dir, 'BUILD')
    if (fs.existsSync(buildFile)) {
      const relDir = path.relative(wsPath, dir)
      const content = fs.readFileSync(buildFile, 'utf-8')

      const pyTestMatch = content.match(/py_test\s*\([^)]*name\s*=\s*"([^"]+)"/s)
      if (pyTestMatch) {
        return `//${relDir}:${pyTestMatch[1]}`
      }

      const nameMatch = content.match(/name\s*=\s*"([^"]+)"/)
      if (nameMatch) {
        return `//${relDir}:${nameMatch[1]}`
      }
    }
    dir = path.dirname(dir)
  }
  return null
}

function queryBazelTarget(filePath: string, wsPath: string): string | null {
  const relPath = path.relative(wsPath, filePath)
  try {
    const result = execSync(`bazel query 'attr(srcs, "${relPath}", //tests/...)' 2>/dev/null`, {
      cwd: wsPath,
      encoding: 'utf-8',
      timeout: 15000
    }).trim()
    const targets = result.split('\n').filter(Boolean)
    return targets[0] || null
  } catch {
    return null
  }
}

export function registerBazelTestRunner(context: vscode.ExtensionContext): vscode.Disposable[] {
  const disposables: vscode.Disposable[] = []

  disposables.push(
    vscode.commands.registerCommand('cmk.bazelTestFile', async () => {
      const editor = vscode.window.activeTextEditor
      if (!editor) {
        notifyWarn('CMK: No active editor.')
        return
      }

      const filePath = editor.document.uri.fsPath
      if (!filePath.endsWith('.py')) {
        notifyWarn('CMK: Not a Python file.')
        return
      }

      const wsPath = getWorkspacePath()
      if (!wsPath) return

      const relPath = path.relative(wsPath, filePath)
      const fileName = path.basename(filePath)

      let target = findBazelTarget(filePath, wsPath)
      if (!target) {
        notifyInfo('CMK: Querying Bazel for target (this may take a moment)...')
        target = queryBazelTarget(filePath, wsPath)
      }

      if (!target) {
        notifyError('CMK: Could not find a Bazel test target', relPath)
        return
      }

      const cmd = `bazel test ${shellEscape(target)} --test_arg=${shellEscape(relPath)}`

      const execution = await runCommand(`Test: ${fileName}`, cmd)
      if (!execution) return

      const exitCode = await waitForTask(execution)
      if (exitCode === 0) {
        notifyInfo(`CMK: Tests passed for ${fileName}`, target)
      } else {
        notifyError(`CMK: Tests failed for ${fileName}`, `${target} — exit code ${exitCode}`)
      }
    })
  )

  disposables.push(
    vscode.commands.registerCommand('cmk.bazelTestFunction', async () => {
      const editor = vscode.window.activeTextEditor
      if (!editor) {
        notifyWarn('CMK: No active editor.')
        return
      }

      const filePath = editor.document.uri.fsPath
      if (!filePath.endsWith('.py')) {
        notifyWarn('CMK: Not a Python file.')
        return
      }

      const wsPath = getWorkspacePath()
      if (!wsPath) return

      const relPath = path.relative(wsPath, filePath)

      const line = editor.selection.active.line
      const doc = editor.document
      let testName: string | null = null

      for (let i = line; i >= 0; i--) {
        const text = doc.lineAt(i).text
        const match = text.match(/^(?:async\s+)?def\s+(test_\w+)/)
        if (match) {
          testName = match[1]
          break
        }
        const classMatch = text.match(/^\s+(?:async\s+)?def\s+(test_\w+)/)
        if (classMatch) {
          testName = classMatch[1]
          break
        }
      }

      if (!testName) {
        notifyWarn('CMK: No test function found at or above cursor.')
        return
      }

      let target = findBazelTarget(filePath, wsPath)
      if (!target) {
        notifyInfo('CMK: Querying Bazel for target...')
        target = queryBazelTarget(filePath, wsPath)
      }

      if (!target) {
        notifyError('CMK: Could not find a Bazel test target', relPath)
        return
      }

      const cmd = `bazel test ${shellEscape(target)} --test_arg=${shellEscape(relPath)} --test_arg=-k --test_arg=${shellEscape(testName)}`

      const execution = await runCommand(`Test: ${testName}`, cmd)
      if (!execution) return

      const exitCode = await waitForTask(execution)
      if (exitCode === 0) {
        notifyInfo(`CMK: ${testName} passed`, target)
      } else {
        notifyError(`CMK: ${testName} failed`, `${target} — exit code ${exitCode}`)
      }
    })
  )

  return disposables
}
