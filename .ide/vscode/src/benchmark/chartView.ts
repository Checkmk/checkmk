/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import * as vscode from 'vscode'

import { esc, getNonce, wrap } from '../sidebar/html'
import { type BenchmarkRun, getBenchmarkHistory } from './startup'

const WINDOW_SIZE = 50
const CHART_WIDTH = 760
const CHART_HEIGHT = 180
const STACKED_HEIGHT = 180

let _panel: vscode.WebviewPanel | undefined

export function openBenchmarkChart(context: vscode.ExtensionContext): void {
  if (_panel) {
    _panel.reveal()
    _panel.webview.html = renderChart(getBenchmarkHistory(context))
    return
  }
  _panel = vscode.window.createWebviewPanel(
    'cmk.benchmarkChart',
    'CMK Startup Benchmarks',
    vscode.ViewColumn.Active,
    { enableScripts: true, retainContextWhenHidden: true }
  )
  _panel.onDidDispose(() => {
    _panel = undefined
  })
  _panel.webview.onDidReceiveMessage((msg: { type?: string }) => {
    if (msg.type === 'refresh' && _panel) {
      _panel.webview.html = renderChart(getBenchmarkHistory(context))
    }
  })
  _panel.webview.html = renderChart(getBenchmarkHistory(context))
}

function renderChart(history: BenchmarkRun[]): string {
  const nonce = getNonce()
  if (history.length === 0) {
    return wrap(
      nonce,
      panelCss,
      `<div class="bench-empty">
         <h2>CMK Startup Benchmarks</h2>
         <p>No benchmark runs recorded yet. Enable <code>cmk.benchmarkStartup</code> in settings,
         then reload the window and open the sidebar.</p>
       </div>`
    )
  }

  const runs = history.slice(-WINDOW_SIZE)
  const phaseNames = collectPhaseNames(runs)
  const palette = makePalette(phaseNames)
  const maxTotal = Math.max(...runs.map((r) => r.totalMs), 1)

  const body = `
    <div class="bench-header">
      <h2>CMK Startup Benchmarks</h2>
      <div class="bench-meta">
        ${runs.length} of ${history.length} run${history.length === 1 ? '' : 's'} shown
        <button class="btn btn-small" data-action="refresh" title="Reload from workspace storage">
          <span class="codicon codicon-refresh"></span> Refresh
        </button>
      </div>
    </div>

    <section class="bench-section">
      <h3>Total startup time (ms)</h3>
      ${renderTotalChart(runs, maxTotal)}
    </section>

    <section class="bench-section">
      <h3>Per-phase breakdown</h3>
      ${renderLegend(phaseNames, palette)}
      ${renderStackedChart(runs, phaseNames, palette, maxTotal)}
    </section>

    <section class="bench-section">
      <h3>Phase statistics (across visible window)</h3>
      ${renderStatsTable(runs, phaseNames)}
    </section>

    <section class="bench-section">
      <h3>Latest run</h3>
      ${renderLatest(runs[runs.length - 1])}
    </section>
  `

  return wrap(nonce, panelCss, body)
}

function renderTotalChart(runs: BenchmarkRun[], maxTotal: number): string {
  const w = CHART_WIDTH
  const h = CHART_HEIGHT
  const padL = 36
  const padB = 18
  const padT = 6
  const padR = 6
  const plotW = w - padL - padR
  const plotH = h - padT - padB
  const barGap = 2
  const barW = Math.max(2, plotW / runs.length - barGap)
  const yMax = niceCeil(maxTotal)

  const bars = runs
    .map((r, i) => {
      const x = padL + i * (barW + barGap)
      const barH = (r.totalMs / yMax) * plotH
      const y = padT + plotH - barH
      return `<rect x="${x}" y="${y}" width="${barW}" height="${barH}" fill="var(--cmk-green)">
        <title>${esc(tooltip(r))}</title>
      </rect>`
    })
    .join('')

  const separators = renderSeparators(runs, padL, barW, barGap, padT, plotH)
  const yTicks = renderYTicks(yMax, padL, padT, plotW, plotH)

  return `<svg class="bench-svg" viewBox="0 0 ${w} ${h}" preserveAspectRatio="xMinYMin meet" role="img" aria-label="Total startup time per run">
    ${yTicks}
    ${separators}
    ${bars}
    <line x1="${padL}" y1="${padT + plotH}" x2="${padL + plotW}" y2="${padT + plotH}" class="axis"/>
    <line x1="${padL}" y1="${padT}" x2="${padL}" y2="${padT + plotH}" class="axis"/>
  </svg>`
}

function renderStackedChart(
  runs: BenchmarkRun[],
  phaseNames: string[],
  palette: Record<string, string>,
  maxTotal: number
): string {
  const w = CHART_WIDTH
  const h = STACKED_HEIGHT
  const padL = 36
  const padB = 18
  const padT = 6
  const padR = 6
  const plotW = w - padL - padR
  const plotH = h - padT - padB
  const barGap = 2
  const barW = Math.max(2, plotW / runs.length - barGap)
  const yMax = niceCeil(maxTotal)

  const bars = runs
    .map((r, i) => {
      const x = padL + i * (barW + barGap)
      let yCursor = padT + plotH
      const segs = phaseNames
        .map((p) => {
          const ms = r.phases[p] || 0
          if (ms <= 0) return ''
          const segH = (ms / yMax) * plotH
          yCursor -= segH
          return `<rect x="${x}" y="${yCursor}" width="${barW}" height="${segH}" fill="${palette[p]}">
            <title>${esc(`${p}: ${ms}ms\n${tooltip(r)}`)}</title>
          </rect>`
        })
        .join('')
      return segs
    })
    .join('')

  const separators = renderSeparators(runs, padL, barW, barGap, padT, plotH)
  const yTicks = renderYTicks(yMax, padL, padT, plotW, plotH)

  return `<svg class="bench-svg" viewBox="0 0 ${w} ${h}" preserveAspectRatio="xMinYMin meet" role="img" aria-label="Per-phase contribution per run">
    ${yTicks}
    ${separators}
    ${bars}
    <line x1="${padL}" y1="${padT + plotH}" x2="${padL + plotW}" y2="${padT + plotH}" class="axis"/>
    <line x1="${padL}" y1="${padT}" x2="${padL}" y2="${padT + plotH}" class="axis"/>
  </svg>`
}

function renderSeparators(
  runs: BenchmarkRun[],
  padL: number,
  barW: number,
  barGap: number,
  padT: number,
  plotH: number
): string {
  const lines: string[] = []
  for (let i = 1; i < runs.length; i++) {
    const prev = runs[i - 1]
    const cur = runs[i]
    const branchChange = prev.branch !== cur.branch
    const versionChange = prev.version !== cur.version
    if (!branchChange && !versionChange) continue
    const x = padL + i * (barW + barGap) - barGap / 2
    const cls = versionChange ? 'sep version' : 'sep branch'
    const titleText = versionChange
      ? `Version change: v${prev.version} → v${cur.version}`
      : `Branch change: ${prev.branch || '?'} → ${cur.branch || '?'}`
    lines.push(
      `<line x1="${x}" y1="${padT}" x2="${x}" y2="${padT + plotH}" class="${cls}"><title>${esc(titleText)}</title></line>`
    )
  }
  return lines.join('')
}

function renderYTicks(
  yMax: number,
  padL: number,
  padT: number,
  plotW: number,
  plotH: number
): string {
  const steps = 4
  const lines: string[] = []
  for (let i = 0; i <= steps; i++) {
    const v = (yMax * (steps - i)) / steps
    const y = padT + (i * plotH) / steps
    lines.push(`<line x1="${padL}" y1="${y}" x2="${padL + plotW}" y2="${y}" class="grid"/>`)
    lines.push(
      `<text x="${padL - 4}" y="${y + 3}" class="tick" text-anchor="end">${Math.round(v)}</text>`
    )
  }
  return lines.join('')
}

function renderLegend(phaseNames: string[], palette: Record<string, string>): string {
  return `<div class="bench-legend">
    ${phaseNames
      .map(
        (p) =>
          `<span class="bench-legend-item"><span class="swatch" style="background:${palette[p]}"></span>${esc(p)}</span>`
      )
      .join('')}
  </div>`
}

function renderStatsTable(runs: BenchmarkRun[], phaseNames: string[]): string {
  const rows = phaseNames
    .map((p) => {
      const vals = runs.map((r) => r.phases[p] || 0).filter((v) => v > 0)
      if (vals.length === 0) return ''
      const med = median(vals)
      const p95 = percentile(vals, 0.95)
      const max = Math.max(...vals)
      return `<tr>
        <td>${esc(p)}</td>
        <td class="num">${round(med)}</td>
        <td class="num">${round(p95)}</td>
        <td class="num">${round(max)}</td>
      </tr>`
    })
    .join('')

  const totals = runs.map((r) => r.totalMs)
  const totMed = median(totals)
  const totP95 = percentile(totals, 0.95)
  const totMax = Math.max(...totals)

  return `<table class="bench-table">
    <thead>
      <tr><th>Phase</th><th class="num">Median</th><th class="num">p95</th><th class="num">Max</th></tr>
    </thead>
    <tbody>
      ${rows}
      <tr class="bench-total-row">
        <td><strong>total</strong></td>
        <td class="num"><strong>${round(totMed)}</strong></td>
        <td class="num"><strong>${round(totP95)}</strong></td>
        <td class="num"><strong>${round(totMax)}</strong></td>
      </tr>
    </tbody>
  </table>`
}

function renderLatest(run: BenchmarkRun): string {
  const phases = Object.entries(run.phases).sort((a, b) => b[1] - a[1])
  return `<div class="bench-latest">
    <div><strong>${esc(new Date(run.ts).toLocaleString())}</strong> &middot;
      v${esc(run.version)} &middot;
      branch <code>${esc(run.branch || '?')}</code> &middot;
      total <strong>${run.totalMs}ms</strong></div>
    <ul>
      ${phases.map(([p, v]) => `<li><code>${esc(p)}</code> &mdash; ${v}ms</li>`).join('')}
    </ul>
  </div>`
}

function collectPhaseNames(runs: BenchmarkRun[]): string[] {
  const totals: Record<string, number> = {}
  for (const r of runs) {
    for (const [k, v] of Object.entries(r.phases)) totals[k] = (totals[k] || 0) + v
  }
  return Object.keys(totals).sort((a, b) => totals[b] - totals[a])
}

const PHASE_PALETTE = [
  '#15d1a0',
  '#e5a00d',
  '#5b9bd5',
  '#c878e0',
  '#e07050',
  '#9ed05a',
  '#d05a9e',
  '#5ad0c4',
  '#d0c45a',
  '#7a5ad0',
  '#5ad07a',
  '#d05a5a'
]

function makePalette(phaseNames: string[]): Record<string, string> {
  const out: Record<string, string> = {}
  phaseNames.forEach((p, i) => {
    out[p] = PHASE_PALETTE[i % PHASE_PALETTE.length]
  })
  return out
}

function median(values: number[]): number {
  if (values.length === 0) return 0
  const sorted = [...values].sort((a, b) => a - b)
  const mid = Math.floor(sorted.length / 2)
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2
}

function percentile(values: number[], p: number): number {
  if (values.length === 0) return 0
  const sorted = [...values].sort((a, b) => a - b)
  const idx = Math.min(sorted.length - 1, Math.floor(p * sorted.length))
  return sorted[idx]
}

function round(n: number, digits = 1): number {
  const f = 10 ** digits
  return Math.round(n * f) / f
}

function niceCeil(v: number): number {
  if (v <= 0) return 1
  const exp = Math.floor(Math.log10(v))
  const base = 10 ** exp
  const mantissa = v / base
  let nice: number
  if (mantissa <= 1) nice = 1
  else if (mantissa <= 2) nice = 2
  else if (mantissa <= 5) nice = 5
  else nice = 10
  return nice * base
}

function tooltip(r: BenchmarkRun): string {
  return `${new Date(r.ts).toLocaleString()}\nv${r.version} · ${r.branch || '?'}\ntotal: ${r.totalMs}ms`
}

const panelCss = `
.bench-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 12px;
}
.bench-header h2 { margin: 0; }
.bench-meta {
  color: var(--vscode-descriptionForeground);
  display: flex;
  align-items: center;
  gap: 12px;
}
.bench-section {
  margin-bottom: 20px;
  padding: 12px;
  border-radius: var(--radius);
  background: var(--vscode-editorWidget-background);
  border: 1px solid var(--vscode-editorWidget-border, transparent);
}
.bench-section h3 {
  margin: 0 0 8px;
  font-size: 0.95em;
  color: var(--vscode-descriptionForeground);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.bench-svg {
  width: 100%;
  height: auto;
  max-width: 760px;
  display: block;
}
.bench-svg .axis { stroke: var(--vscode-descriptionForeground); stroke-width: 0.5; }
.bench-svg .grid { stroke: var(--vscode-editorWidget-border, #444); stroke-width: 0.3; opacity: 0.4; }
.bench-svg .tick { fill: var(--vscode-descriptionForeground); font-size: 9px; font-family: var(--vscode-editor-font-family); }
.bench-svg .sep.branch { stroke: var(--cmk-yellow); stroke-width: 1; stroke-dasharray: 2 2; opacity: 0.7; }
.bench-svg .sep.version { stroke: var(--cmk-green); stroke-width: 1.2; opacity: 0.9; }
.bench-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 8px;
  font-size: 0.85em;
}
.bench-legend-item { display: inline-flex; align-items: center; gap: 5px; }
.swatch {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 2px;
}
.bench-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9em;
}
.bench-table th, .bench-table td {
  text-align: left;
  padding: 4px 8px;
  border-bottom: 1px solid var(--vscode-editorWidget-border, transparent);
}
.bench-table th.num, .bench-table td.num {
  text-align: right;
  font-family: var(--vscode-editor-font-family);
}
.bench-total-row td { border-top: 1px solid var(--vscode-descriptionForeground); }
.bench-latest ul { margin: 4px 0 0; padding-left: 18px; font-size: 0.9em; }
.bench-empty {
  padding: 20px;
  text-align: center;
  color: var(--vscode-descriptionForeground);
}
.bench-empty code, .bench-latest code {
  font-family: var(--vscode-editor-font-family);
  background: var(--vscode-textCodeBlock-background, rgba(255,255,255,0.04));
  padding: 1px 4px;
  border-radius: 2px;
}
`
