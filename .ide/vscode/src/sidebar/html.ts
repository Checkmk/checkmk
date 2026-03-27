/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as crypto from 'crypto'

import baseCss from './base.css'

export function esc(s: unknown): string {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

export function getNonce(): string {
  return crypto.randomBytes(16).toString('hex')
}

export function wrap(
  nonce: string,
  css: string,
  body: string,
  codiconUri?: unknown,
  cspSource?: string
): string {
  const fontSrc = codiconUri ? `font-src ${cspSource || codiconUri};` : ''
  const codiconCss = codiconUri
    ? `
  @font-face {
    font-family: 'codicon';
    src: url('${codiconUri}') format('truetype');
    font-weight: normal; font-style: normal;
  }
  .codicon {
    font: normal normal normal 16px/1 codicon;
    display: inline-block; text-decoration: none;
    text-rendering: auto; text-align: center;
    -webkit-font-smoothing: antialiased;
    user-select: none;
  }
  .codicon-terminal::before { content: "\\ea85"; }
  .codicon-link-external::before { content: "\\eb14"; }
  .codicon-trash::before { content: "\\ea81"; }
  .codicon-copy::before { content: "\\ebcc"; }
  .codicon-refresh::before { content: "\\eb37"; }
  .codicon-chevron-right::before { content: "\\eab6"; }
  .codicon-wrench::before { content: "\\eb6d"; }
  .codicon-play::before { content: "\\eb2c"; }
  .codicon-stop-circle::before { content: "\\eba5"; }
  .codicon-add::before { content: "\\ea60"; }`
    : ''
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'nonce-${nonce}'; script-src 'nonce-${nonce}'; ${fontSrc}">
<style nonce="${nonce}">
  ${codiconCss}
  ${baseCss}
  ${css}
</style>
</head>
<body>
${body}
<script nonce="${nonce}">
  const vscode = acquireVsCodeApi();
  document.addEventListener('click', (e) => {
    const el = e.target.closest('[data-action]');
    if (!el) return;
    e.stopPropagation();
    const action = el.dataset.action;
    const id = el.dataset.id;
    switch (action) {
      case 'exec': vscode.postMessage({ type: 'executeCommand', commandId: id }); break;
      case 'toggle-profile': vscode.postMessage({ type: 'toggleProfile', name: id }); break;
      case 'install-ext': vscode.postMessage({ type: 'installExtension', extensionId: id }); break;
      case 'toggle-accordion': {
        const container = el.closest('.ext-family,.omd-site');
        container.classList.toggle('open');
        const state = vscode.getState() || {};
        const open = state.openAccordions || {};
        const nameEl = container.querySelector('.ext-family-name,.omd-site-name');
        if (nameEl) {
          const key = nameEl.textContent.trim();
          open[key] = container.classList.contains('open');
          vscode.setState({ ...state, openAccordions: open });
        }
        break;
      }
      case 'refresh': vscode.postMessage({ type: 'refresh' }); break;
      case 'omd-site-action': vscode.postMessage({ type: 'omdSiteAction', action: el.dataset.omdAction, site: el.dataset.site }); break;
      case 'omd-service-action': vscode.postMessage({ type: 'omdServiceAction', action: el.dataset.omdAction, site: el.dataset.site, service: el.dataset.service }); break;
      case 'omd-open-browser': vscode.postMessage({ type: 'omdOpenBrowser', url: el.dataset.url }); break;
      case 'omd-auth': vscode.postMessage({ type: 'omdAuth' }); break;
      case 'omd-console': vscode.postMessage({ type: 'omdConsole', site: el.dataset.site }); break;
      case 'omd-delete-site': vscode.postMessage({ type: 'omdDeleteSite', site: el.dataset.site }); break;
      case 'omd-create-site': vscode.postMessage({ type: 'omdCreateSite' }); break;
      case 'omd-install-devsite': vscode.postMessage({ type: 'omdInstallDevSite' }); break;
      case 'copy-setting': {
        const text = el.dataset.value;
        navigator.clipboard.writeText(text);
        const icon = el.querySelector('.codicon');
        if (icon) { icon.style.color = 'var(--cmk-green)'; setTimeout(() => { icon.style.color = ''; }, 1200); }
        break;
      }
      case 'apply-all-mismatches': vscode.postMessage({ type: 'applyAllMismatches' }); break;
      case 'apply-family-mismatches': vscode.postMessage({ type: 'applyFamilyMismatches', family: el.dataset.family }); break;
      case 'run-make-setup': vscode.postMessage({ type: 'runMakeSetup' }); break;
      case 'onboarding-dismiss': vscode.postMessage({ type: 'onboardingDismiss' }); break;
      case 'apply-setting': {
        const setting = JSON.parse(el.dataset.setting);
        vscode.postMessage({ type: 'applySingleSetting', ...setting });
        break;
      }
    }
  });
  // Restore accordion open/close state
  const saved = vscode.getState();
  if (saved && saved.openAccordions) {
    document.querySelectorAll('.ext-family,.omd-site').forEach(el => {
      const nameEl = el.querySelector('.ext-family-name,.omd-site-name');
      if (nameEl && saved.openAccordions[nameEl.textContent.trim()]) {
        el.classList.add('open');
      }
    });
  }
</script>
</body></html>`
}

export function renderLoading(): string {
  const nonce = getNonce()
  return wrap(
    nonce,
    `
    @keyframes spin { to { transform: rotate(360deg); } }
    .loader { display: flex; align-items: center; gap: 8px; padding: 8px; font-size: 0.9em; color: var(--vscode-descriptionForeground); }
    .loader-icon { display: inline-block; animation: spin 0.8s linear infinite; }
  `,
    `<div class="loader"><span class="loader-icon">&#8635;</span> Refreshing…</div>`
  )
}
