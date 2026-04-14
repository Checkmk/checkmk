/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as vscode from 'vscode'

import { loadConfig } from '../../core/config'

interface SnippetConfig {
  prefix: string
  body: string[]
  description: string
  scope: string
}

export function registerSnippets(): vscode.Disposable[] {
  const snippets = loadConfig<Record<string, SnippetConfig>>('snippets')

  const provider = vscode.languages.registerCompletionItemProvider(
    { language: 'python' },
    {
      provideCompletionItems() {
        return Object.entries(snippets)
          .filter(([, s]) => s.scope === 'python')
          .map(([name, s]) => {
            const item = new vscode.CompletionItem(s.prefix, vscode.CompletionItemKind.Snippet)
            item.insertText = new vscode.SnippetString(s.body.join('\n'))
            item.detail = name
            item.documentation = new vscode.MarkdownString(s.description)
            return item
          })
      }
    },
    'c'
  )

  return [provider]
}
