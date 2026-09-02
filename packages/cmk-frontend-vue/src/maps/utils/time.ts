/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Format `ts` (Unix seconds) as locale string, or '' if missing.
 */
export function formatTimestamp(ts: number | null | undefined): string {
  if (!ts) {
    return ''
  }
  return new Date(ts * 1000).toLocaleString()
}

/**
 * Render the elapsed time since `ts` as a compact string ("3h 12m", "45s").
 * Returns '' if `ts` is missing or in the future.
 */
export function formatRelativeDuration(ts: number | null | undefined, nowMs?: number): string {
  if (!ts) {
    return ''
  }
  const now = (nowMs ?? Date.now()) / 1000
  const s = Math.max(0, Math.floor(now - ts))
  return _formatSeconds(s)
}

/**
 * Render the time until `ts` as a compact string ("in 28s", "in 4m"). Returns
 * '' for past or missing timestamps.
 */
export function formatRelativeFuture(ts: number | null | undefined, nowMs?: number): string {
  if (!ts) {
    return ''
  }
  const now = (nowMs ?? Date.now()) / 1000
  const s = Math.floor(ts - now)
  if (s <= 0) {
    return ''
  }
  return _formatSeconds(s)
}

function _formatSeconds(s: number): string {
  if (s < 60) {
    return `${s}s`
  }
  const m = Math.floor(s / 60)
  if (m < 60) {
    return `${m}m ${s % 60}s`
  }
  const h = Math.floor(m / 60)
  if (h < 24) {
    return `${h}h ${m % 60}m`
  }
  const d = Math.floor(h / 24)
  return `${d}d ${h % 24}h`
}
