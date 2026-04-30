/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as vscode from 'vscode'

import { error, log } from '../../core/log'
import { esc, getNonce } from '../../sidebar/html'

const EDITIONS = ['community', 'pro', 'ultimate', 'ultimatemt', 'cloud'] as const

interface ConfigState {
  edition: string
}

function readState(): ConfigState {
  const cfg = vscode.workspace.getConfiguration('cmk.bazelTests')
  return {
    edition: cfg.get<string>('edition') || 'pro'
  }
}

function renderHtml(state: ConfigState, nonce: string, cspSource: string): string {
  const editionOptions = EDITIONS.map(
    (e) => `<option value="${esc(e)}"${e === state.edition ? ' selected' : ''}>${esc(e)}</option>`
  ).join('')

  const body = `
  <div class="cfg-card">
    <div class="cfg-row">
      <label class="cfg-label" for="edition">Edition</label>
      <select id="edition" class="cfg-input">${editionOptions}</select>
    </div>
    <div class="cfg-hint">Passed to bazel as <code>--cmk_edition=&lt;edition&gt;</code>. Saved in <code>cmk.bazelTests.edition</code> workspace setting.</div>
  </div>`

  const css = `
  .cfg-card { display: flex; flex-direction: column; gap: 10px; padding: 12px 8px; }
  .cfg-row { display: flex; align-items: center; gap: 8px; }
  .cfg-label { min-width: 80px; font-weight: 600; color: var(--vscode-descriptionForeground); }
  .cfg-input {
    flex: 1; min-width: 0;
    padding: 4px 6px;
    background: var(--vscode-input-background);
    color: var(--vscode-input-foreground);
    border: 1px solid var(--vscode-input-border, transparent);
    border-radius: 2px;
    font: inherit;
  }
  .cfg-input:focus {
    outline: 1px solid var(--vscode-focusBorder);
    outline-offset: -1px;
  }
  .cfg-hint {
    font-size: 0.85em;
    color: var(--vscode-descriptionForeground);
    margin-top: 4px;
  }
  .cfg-hint code {
    background: var(--vscode-textBlockQuote-background);
    padding: 1px 4px;
    border-radius: 2px;
  }
  `

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${cspSource} 'nonce-${nonce}'; script-src 'nonce-${nonce}';">
<style nonce="${nonce}">
  body { font-family: var(--vscode-font-family); font-size: var(--vscode-font-size); color: var(--vscode-foreground); padding: 0; }
  ${css}
</style>
</head>
<body>
${body}
<script nonce="${nonce}">
  const vscode = acquireVsCodeApi();
  const editionEl = document.getElementById('edition');
  function commit() {
    vscode.postMessage({ type: 'apply', edition: editionEl.value });
  }
  editionEl.addEventListener('change', commit);
</script>
</body>
</html>`
}

class BazelTestsConfigViewProvider implements vscode.WebviewViewProvider {
  private _view?: vscode.WebviewView

  resolveWebviewView(webviewView: vscode.WebviewView): void {
    this._view = webviewView
    webviewView.webview.options = { enableScripts: true }
    this._render()

    webviewView.webview.onDidReceiveMessage((msg) => {
      if (msg?.type !== 'apply') return
      this._apply(msg.edition).catch((err) =>
        error(`Bazel test config apply failed: ${(err as Error).message}`)
      )
    })

    webviewView.onDidChangeVisibility(() => {
      if (webviewView.visible) this._render()
    })
  }

  refresh(): void {
    this._render()
  }

  private _render(): void {
    const view = this._view
    if (!view) return
    const nonce = getNonce()
    view.webview.html = renderHtml(readState(), nonce, view.webview.cspSource)
  }

  private async _apply(edition: string): Promise<void> {
    if (!EDITIONS.includes(edition as (typeof EDITIONS)[number])) return
    const cfg = vscode.workspace.getConfiguration('cmk.bazelTests')
    await cfg.update('edition', edition, vscode.ConfigurationTarget.Workspace)
    log(`Bazel test config applied: edition=${edition}`)
  }
}

export function registerBazelTestsConfigView(): vscode.Disposable[] {
  const provider = new BazelTestsConfigViewProvider()
  const disposables: vscode.Disposable[] = []
  disposables.push(
    vscode.window.registerWebviewViewProvider('cmk.bazelTests.config', provider, {
      webviewOptions: { retainContextWhenHidden: true }
    })
  )
  disposables.push(
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration('cmk.bazelTests')) provider.refresh()
    })
  )
  return disposables
}
