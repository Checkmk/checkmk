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
  .codicon-debug-stop::before { content: "\\ead7"; }
  .codicon-debug-restart::before { content: "\\ead2"; }
  .codicon-debug-disconnect::before { content: "\\ead0"; }
  .codicon-add::before { content: "\\ea60"; }
  .codicon-settings-gear::before { content: "\\eb51"; }
  .codicon-package::before { content: "\\eb29"; }
  .codicon-shield::before { content: "\\eb53"; }
  .codicon-tools::before { content: "\\eb6d"; }
  .codicon-sync::before { content: "\\ea77"; }
  .codicon-gear::before { content: "\\eaf8"; }
  .codicon-symbol-property::before { content: "\\eb65"; }
  .codicon-run-all::before { content: "\\eb9e"; }
  .codicon-empty-window::before { content: "\\eae4"; }
  .codicon-circle-slash::before { content: "\\eabd"; }
  .codicon-output::before { content: "\\eb9d"; }
  .codicon-file::before { content: "\\ea7b"; }
  .codicon-file-text::before { content: "\\ec5e"; }
  .codicon-history::before { content: "\\ea82"; }
  .codicon-pin::before { content: "\\eb2b"; }
  .codicon-pinned::before { content: "\\eba0"; }
  .codicon-remove::before { content: "\\eb3b"; }
  .codicon-list-selection::before { content: "\\eb85"; }
  .codicon-new-collection::before { content: "\\ec58"; }
  .codicon-check::before { content: "\\eab2"; }
  .codicon-close::before { content: "\\ea76"; }`
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
    const ASYNC_ACTIONS = new Set([
      'omd-site-action',
      'omd-service-action',
      'omd-install-devsite',
      'apply-setting',
      'apply-family-mismatches',
      'apply-all-mismatches',
      'toggle-profile',
    ]);
    if (ASYNC_ACTIONS.has(action)) {
      el.setAttribute('disabled', 'true');
      el.style.pointerEvents = 'none';
      el.style.opacity = '0.5';
      const icon = el.querySelector('.codicon');
      if (icon) {
        icon.className = 'spinner';
        icon.textContent = '\u21BB';
      } else {
        const sp = document.createElement('span');
        sp.className = 'spinner';
        sp.textContent = '\u21BB';
        sp.style.marginRight = '4px';
        el.prepend(sp);
      }
    }
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
      case 'omd-logs': vscode.postMessage({ type: 'omdLogs', site: el.dataset.site }); break;
      case 'omd-svc-logs': vscode.postMessage({ type: 'omdSvcLogs', site: el.dataset.site, service: el.dataset.service }); break;
      case 'omd-delete-site': vscode.postMessage({ type: 'omdDeleteSite', site: el.dataset.site }); break;
      case 'omd-create-site': vscode.postMessage({ type: 'omdCreateSite' }); break;
      case 'omd-install-devsite': vscode.postMessage({ type: 'omdInstallDevSite' }); break;
      case 'omd-proxy-start': vscode.postMessage({ type: 'omdProxyStart', site: el.dataset.site, service: el.dataset.service }); break;
      case 'omd-proxy-stop': vscode.postMessage({ type: 'omdProxyStop', site: el.dataset.site, service: el.dataset.service }); break;
      case 'omd-proxy-site': vscode.postMessage({ type: 'omdProxySite', site: el.dataset.site }); break;
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
      case 'mypy-add-baseline': vscode.postMessage({ type: 'mypyAddBaseline', target: el.dataset.target }); break;
      case 'mypy-remove-baseline': vscode.postMessage({ type: 'mypyRemoveBaseline', target: el.dataset.target }); break;
      case 'mypy-activate-target': vscode.postMessage({ type: 'mypyActivateTarget', target: el.dataset.target }); break;
      case 'mypy-deactivate-target': vscode.postMessage({ type: 'mypyDeactivateTarget', target: el.dataset.target }); break;
      case 'mypy-allocator-enable': vscode.postMessage({ type: 'mypyAllocatorEnable' }); break;
      case 'mypy-allocator-disable': vscode.postMessage({ type: 'mypyAllocatorDisable' }); break;
      case 'mypy-allocator-dismiss': vscode.postMessage({ type: 'mypyAllocatorDismiss' }); break;
      case 'mypy-allocator-reapply': vscode.postMessage({ type: 'mypyAllocatorReapply' }); break;
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
    '',
    `<div class="loader"><span class="spinner">&#8635;</span> Refreshing…</div>`
  )
}

export type StatusLevel = 'ok' | 'warn' | 'error'

export interface StatusRowButton {
  action: string
  icon: string
  title: string
  dataAttrs?: Record<string, string>
  commandId?: string
}

export interface StatusRowOpts {
  level: StatusLevel
  label: string
  state?: string
  buttons?: StatusRowButton[]
  /** When true, render a spinner in place of the level glyph. */
  spinner?: boolean
}

function buttonHtml(b: StatusRowButton): string {
  const data = [`data-action="${esc(b.action)}"`, `title="${esc(b.title)}"`]
  if (b.commandId) data.push(`data-id="${esc(b.commandId)}"`)
  for (const [k, v] of Object.entries(b.dataAttrs || {})) {
    data.push(`data-${esc(k)}="${esc(v)}"`)
  }
  return `<button class="btn btn-small btn-icon" ${data.join(' ')}><span class="codicon codicon-${esc(b.icon)}"></span></button>`
}

const LEVEL_ICON: Record<StatusLevel, string> = {
  ok: '&#10003;',
  warn: '&#9888;',
  error: '&#10007;'
}

/** Shared compact one-line status row used across IDE Health. */
export function renderStatusRow(opts: StatusRowOpts): string {
  const btns = (opts.buttons || []).map(buttonHtml).join('')
  const state = opts.state ? `<span class="status-row-state">${esc(opts.state)}</span>` : ''
  const icon = opts.spinner
    ? `<span class="spinner">&#8635;</span>`
    : `<span class="card-icon">${LEVEL_ICON[opts.level]}</span>`
  return `<div class="status-row ${opts.level}">
    ${icon}
    <span class="status-row-label">${esc(opts.label)}</span>
    ${state}
    ${btns}
  </div>`
}
