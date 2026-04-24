/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as vscode from 'vscode'

import { error, log, notifyInfo } from '../core/log'

export interface SettingOverride {
  section: string
  key: string
  value: unknown
}

export interface OnDemandTool {
  id: string
  displayName: string
  featureSetting: string
  matchesFile: (doc: vscode.TextDocument) => boolean
  listenTestingView: boolean
  startupOverrides?: SettingOverride[]
  triggerOverrides: SettingOverride[]
  skipIfAlreadyManaged?: (wsFolder: vscode.WorkspaceFolder) => boolean
}

function isFeatureEnabled(setting: string, fallback: boolean): boolean {
  return vscode.workspace.getConfiguration().get<boolean>(setting, fallback) ?? fallback
}

async function applyOverride(wsFolder: vscode.WorkspaceFolder, o: SettingOverride): Promise<void> {
  await vscode.workspace
    .getConfiguration(o.section, wsFolder)
    .update(o.key, o.value, vscode.ConfigurationTarget.WorkspaceFolder)
}

async function applyOverrides(
  wsFolder: vscode.WorkspaceFolder,
  overrides: SettingOverride[]
): Promise<void> {
  for (const o of overrides) await applyOverride(wsFolder, o)
}

export function registerOnDemandTool(
  tool: OnDemandTool,
  defaultEnabled: boolean
): vscode.Disposable[] {
  if (!isFeatureEnabled(tool.featureSetting, defaultEnabled)) return []
  const wsFolder = vscode.workspace.workspaceFolders?.[0]
  if (!wsFolder) return []
  if (tool.skipIfAlreadyManaged?.(wsFolder)) return []

  let startupApplied = false
  if (tool.startupOverrides && tool.startupOverrides.length > 0) {
    applyOverrides(wsFolder, tool.startupOverrides)
      .then(() => {
        startupApplied = true
      })
      .catch((err) => error(`${tool.id}: startup overrides failed: ${(err as Error).message}`))
  }

  for (const editor of vscode.window.visibleTextEditors) {
    if (tool.matchesFile(editor.document)) {
      triggerTool(tool, wsFolder, `${tool.displayName} file already open on activation`).catch(
        (err) => error(`${tool.id}: trigger failed: ${(err as Error).message}`)
      )
      return []
    }
  }

  const disposables: vscode.Disposable[] = []
  let triggered = false

  const doTrigger = async (reason: string): Promise<void> => {
    if (triggered) return
    triggered = true
    try {
      await triggerTool(tool, wsFolder, reason)
    } catch (err) {
      error(`${tool.id}: trigger failed: ${(err as Error).message}`)
    }
    for (const d of disposables) d.dispose()
  }

  disposables.push(
    vscode.workspace.onDidOpenTextDocument((doc) => {
      if (tool.matchesFile(doc)) {
        doTrigger(`${tool.displayName} file opened`).catch(() => {})
      }
    }),
    {
      dispose: () => {
        if (!triggered && startupApplied && tool.startupOverrides) {
          const unsets: SettingOverride[] = tool.startupOverrides.map((o) => ({
            ...o,
            value: undefined
          }))
          applyOverrides(wsFolder, unsets).catch(() => {})
        }
      }
    }
  )

  if (tool.listenTestingView) {
    const controller = vscode.tests.createTestController(tool.id, `${tool.displayName} (on-demand)`)
    controller.resolveHandler = async () => {
      await doTrigger('Testing view opened')
      setTimeout(() => {
        vscode.commands.executeCommand('testing.refreshTests').then(undefined, () => {})
      }, 200)
    }
    disposables.push(controller)
  }

  return disposables
}

async function triggerTool(
  tool: OnDemandTool,
  wsFolder: vscode.WorkspaceFolder,
  reason: string
): Promise<void> {
  await applyOverrides(wsFolder, tool.triggerOverrides)
  log(`${tool.id} enabled on-demand (${reason})`)
  await notifyInfo(`CMK ▸ ${tool.displayName} started (${reason}).`)
}

const PYTHON_TEST_FILE = /(?:^|\/)test_[^/]+\.py$|_test\.py$|\/tests?\//
const VITEST_TEST_FILE = /\.(test|spec)\.(ts|tsx|mts|cts|js|jsx|mjs|cjs|vue)$/

export function registerPytestOnDemand(): vscode.Disposable[] {
  return registerOnDemandTool(
    {
      id: 'cmk.pytestOnDemand',
      displayName: 'pytest',
      featureSetting: 'cmk.python.testOnDemand',
      matchesFile: (doc) =>
        doc.languageId === 'python' &&
        doc.uri.scheme === 'file' &&
        PYTHON_TEST_FILE.test(doc.uri.fsPath),
      listenTestingView: true,
      triggerOverrides: [{ section: 'python.testing', key: 'pytestEnabled', value: true }],
      skipIfAlreadyManaged: (wsFolder) =>
        vscode.workspace
          .getConfiguration('python.testing', wsFolder)
          .get<boolean>('pytestEnabled', false) === true
    },
    true
  )
}

export function registerRuffOnDemand(): vscode.Disposable[] {
  return registerOnDemandTool(
    {
      id: 'cmk.ruffOnDemand',
      displayName: 'Ruff',
      featureSetting: 'cmk.ruff.testOnDemand',
      matchesFile: (doc) => doc.languageId === 'python' && doc.uri.scheme === 'file',
      listenTestingView: false,
      startupOverrides: [{ section: 'ruff', key: 'enable', value: false }],
      triggerOverrides: [{ section: 'ruff', key: 'enable', value: undefined }],
      skipIfAlreadyManaged: (wsFolder) =>
        vscode.workspace.getConfiguration('ruff', wsFolder).inspect('enable')
          ?.workspaceFolderValue !== undefined
    },
    false
  )
}

export function registerVitestOnDemand(): vscode.Disposable[] {
  return registerOnDemandTool(
    {
      id: 'cmk.vitestOnDemand',
      displayName: 'vitest',
      featureSetting: 'cmk.vitest.testOnDemand',
      matchesFile: (doc) => doc.uri.scheme === 'file' && VITEST_TEST_FILE.test(doc.uri.fsPath),
      listenTestingView: true,
      startupOverrides: [{ section: 'vitest', key: 'configSearchPatternExclude', value: '**/*' }],
      triggerOverrides: [
        { section: 'vitest', key: 'configSearchPatternExclude', value: undefined }
      ],
      skipIfAlreadyManaged: (wsFolder) =>
        vscode.workspace.getConfiguration('vitest', wsFolder).inspect('configSearchPatternExclude')
          ?.workspaceFolderValue !== undefined
    },
    false
  )
}
