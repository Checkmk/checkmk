/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
export interface PerfMetric {
  label: string
  value: number
  unit: string
  warn: number | null
  crit: number | null
  min: number | null
  max: number | null
}

// A quoted label (which may hold spaces and "=") with its value, or a
// whitespace-free part. Each alternative stops at the next quote or whitespace,
// so a long input is read once. Mirrors cmk/maps/shared/perfdata.py.
const PERF_TOKEN = /'[^']*'=\S*|\S+/g
const PERF_VALUE = /^(-?(?:\d+(?:\.\d*)?|\.\d+))([a-zA-Z%/]*)/

function labelAndValue(token: string): [string, string] | null {
  const end = token.startsWith("'") ? token.indexOf("'", 1) : -1
  if (end > 0 && token[end + 1] === '=') {
    return [token.slice(1, end), token.slice(end + 2)]
  }
  const eq = token.indexOf('=')
  return eq < 0 ? null : [token.slice(0, eq), token.slice(eq + 1)]
}

/**
 * Parse Nagios/Checkmk performance data string into structured metrics. An
 * entry without a label or a numeric value is left out.
 */
export function parsePerfData(raw: string): PerfMetric[] {
  const metrics: PerfMetric[] = []
  for (const token of raw.match(PERF_TOKEN) ?? []) {
    const parsed = labelAndValue(token)
    if (!parsed || !parsed[0]) {
      continue
    }
    const [label, rest] = parsed
    const [valStr = '', warnStr, critStr, minStr, maxStr] = rest.split(';')
    const [, num, unit = ''] = PERF_VALUE.exec(valStr) ?? []
    if (num === undefined) {
      continue
    }
    const toNum = (s?: string) => (s !== undefined && s !== '' ? parseFloat(s) : null)
    metrics.push({
      label,
      value: parseFloat(num),
      unit,
      warn: toNum(warnStr),
      crit: toNum(critStr),
      min: toNum(minStr),
      max: toNum(maxStr)
    })
  }
  return metrics
}

/** The metric of *label*, or the first metric when no label is asked for. */
export function getMetric(metrics: PerfMetric[], label?: string | null): PerfMetric | null {
  if (!label) {
    return metrics[0] ?? null
  }
  return metrics.find((m) => m.label === label) ?? null
}

/** Whether a percentage *readout* is meaningful: only with a real upper bound
 * (``max``) or a ``%`` unit. A ``crit`` is an alarm threshold, not a scale max. */
export function hasPercentScale(m: PerfMetric): boolean {
  return (m.max !== null && m.max > 0) || m.unit === '%'
}

/** Calculate utilization percentage (0–100) for a metric. */
export function utilPercent(m: PerfMetric): number {
  if (m.max !== null && m.max > 0) {
    return Math.min(100, Math.max(0, (m.value / m.max) * 100))
  }
  if (m.crit !== null && m.crit > 0) {
    return Math.min(100, Math.max(0, (m.value / m.crit) * 100))
  }
  if (m.unit === '%') {
    return Math.min(100, Math.max(0, m.value))
  }
  return 0
}

/** Trim trailing zeros after the decimal point only: "5.00" → "5", "5.10" → "5.1".
 * Integers pass through untouched ("250" must stay "250"). */
function trimFixed(s: string): string {
  return s.includes('.') ? s.replace(/0+$/, '').replace(/\.$/, '') : s
}

// Units that already carry a magnitude prefix — prepending an SI prefix would
// produce nonsense like "2.05 kMB" for 2048 MB.
const PREFIXED_UNIT = /^[KMGTP]i?B$/i

/** Format a metric value with an SI prefix: 8927830016 + "B" → "8.93 GB".
 * Percent values keep their plain form ("54%"). Time units are NOT special-
 * cased here — renderMetricValue routes them through the CMK TimeFormatter
 * before this heuristic ever sees them. */
export function fmtSI(value: number, unit: string): string {
  if (unit === '%') {
    return `${value.toFixed(0)}%`
  }
  if (PREFIXED_UNIT.test(unit)) {
    return `${trimFixed(value.toFixed(2))} ${unit}`
  }
  const av = Math.abs(value)
  let v = value
  let p = ''
  if (av >= 1e12) {
    v = value / 1e12
    p = 'T'
  } else if (av >= 1e9) {
    v = value / 1e9
    p = 'G'
  } else if (av >= 1e6) {
    v = value / 1e6
    p = 'M'
  } else if (av >= 1e3) {
    v = value / 1e3
    p = 'k'
  }
  const fixed = trimFixed(Math.abs(v) >= 100 ? v.toFixed(0) : v.toFixed(2))
  return unit ? `${fixed} ${p}${unit}` : p ? `${fixed}${p}` : fixed
}

/** Whether the metric carries any client-side scale a fill can be computed
 * from: a real max, a crit threshold (NagVis-style proportional fill) or a %
 * unit. Distinct from hasPercentScale, which gates the percent *readout*. */
export function hasFillScale(m: PerfMetric): boolean {
  return (m.max !== null && m.max > 0) || (m.crit !== null && m.crit > 0) || m.unit === '%'
}

/** Map utilization percentage to a color: green → amber → red. */
export function utilColor(pct: number): string {
  if (pct <= 50) {
    const t = pct / 50
    const r = Math.round(34 + (245 - 34) * t)
    const g = Math.round(197 + (158 - 197) * t)
    const b = Math.round(94 + (11 - 94) * t)
    return `rgb(${r},${g},${b})`
  } else {
    const t = (pct - 50) / 50
    const r = Math.round(245 + (239 - 245) * t)
    const g = Math.round(158 + (68 - 158) * t)
    const b = Math.round(11 + (68 - 11) * t)
    return `rgb(${r},${g},${b})`
  }
}
