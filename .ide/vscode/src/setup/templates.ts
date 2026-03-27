/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as path from 'path'
import * as vscode from 'vscode'

import { loadConfig } from '../core/config'
import { notifyInfo } from '../core/log'

interface TemplateConfig {
  description: string
  targetDir: string
  files: Record<string, string>
}

interface SnippetConfig {
  body: string[]
  [key: string]: unknown
}

export function registerTemplates(context: vscode.ExtensionContext): void {
  const templates = loadConfig<Record<string, TemplateConfig>>('templates')

  context.subscriptions.push(
    vscode.commands.registerCommand('cmk.newFromTemplate', async () => {
      const items = Object.entries(templates).map(([name, t]) => ({
        label: `$(file-add) ${name}`,
        description: t.description,
        templateName: name
      }))

      const picked = await vscode.window.showQuickPick(items, {
        title: 'CMK ▸ New: Create from Template',
        placeHolder: 'Select a template'
      })

      if (!picked) return

      const template = templates[picked.templateName]
      const pluginName = await vscode.window.showInputBox({
        prompt: 'Plugin/component name (lowercase, underscores)',
        placeHolder: 'my_check_plugin',
        validateInput: (v) =>
          /^[a-z][a-z0-9_]*$/.test(v) ? null : 'Use lowercase letters, numbers, underscores'
      })

      if (!pluginName) return

      const wsPath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath
      if (!wsPath) return

      const targetDir = path.join(wsPath, template.targetDir.replace(/\$\{name\}/g, pluginName))

      await vscode.workspace.fs.createDirectory(vscode.Uri.file(targetDir))

      const snippets = loadConfig<Record<string, SnippetConfig>>('snippets')
      const createdFiles: string[] = []

      for (const [fileName, source] of Object.entries(template.files)) {
        const resolvedName = fileName.replace(/\$\{name\}/g, pluginName)
        const filePath = path.join(targetDir, resolvedName)

        let content = ''
        if (source.startsWith('snippets:')) {
          const snippetName = source.substring('snippets:'.length)
          const snippet = snippets[snippetName]
          if (snippet) {
            content = snippet.body
              .join('\n')
              .replace(/\$\{CURRENT_YEAR\}/g, new Date().getFullYear().toString())
              .replace(/\$\{1:[^}]*\}/g, pluginName)
              .replace(/\$\{2:[^}]*\}/g, 'Section')
              .replace(/\$\{3:[^}]*\}/g, '')
              .replace(
                /\$\{4:[^}]*\}/g,
                pluginName.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
              )
              .replace(/\$\{5:[^}]*\}/g, 'GENERAL')
              .replace(/\$\{6:[^}]*\}/g, 'Item')
              .replace(/\$\d/g, '')
          }
        }

        await vscode.workspace.fs.writeFile(vscode.Uri.file(filePath), Buffer.from(content, 'utf8'))
        createdFiles.push(filePath)
      }

      if (createdFiles.length > 0) {
        const doc = await vscode.workspace.openTextDocument(createdFiles[0])
        await vscode.window.showTextDocument(doc)
      }

      notifyInfo(
        `CMK: Created ${createdFiles.length} file(s) from ${picked.templateName}`,
        createdFiles.map((f) => path.basename(f)).join(', ')
      )
    })
  )
}
