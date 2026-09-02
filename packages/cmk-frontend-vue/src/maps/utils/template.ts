/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type { MapElement as MapObject, ObjectState } from '@/maps/types/api'
import { getMapElementName } from '@/maps/utils/naming'
import { parsePerfData } from '@/maps/utils/perf'
import { formatRelativeDuration, formatRelativeFuture, formatTimestamp } from '@/maps/utils/time'

/**
 * Interpolate a template string with object and state data.
 *
 * Placeholders:
 *   {{name}}             – display name (label_text or host/service/group)
 *   {{type}}             – object type (host, service, …)
 *   {{state}}            – monitoring state (UP, DOWN, OK, WARNING, …)
 *   {{output}}           – plugin output (first line)
 *   {{long_output}}      – full plugin output including additional lines
 *   {{host}}             – hostname
 *   {{service}}          – service description
 *   {{group}}            – group name (hostgroup / servicegroup)
 *   {{address}}          – host IP address
 *   {{alias}}            – host alias / display name from monitoring core
 *   {{acknowledged}}     – 'true' / 'false'
 *   {{in_downtime}}      – 'true' / 'false'
 *   {{stale}}            – 'true' / 'false'
 *   {{state_type}}       – 'HARD' / 'SOFT'
 *   {{attempts}}         – 'current/max' check attempts (e.g. '2/3')
 *   {{last_check}}       – formatted timestamp of last check
 *   {{next_check}}       – formatted timestamp of next scheduled check
 *   {{next_check_in}}    – relative time until next check (e.g. 'in 28s')
 *   {{last_state_change}}– formatted timestamp of last state change
 *   {{state_duration}}   – time since last state change (e.g. '3h 12m')
 *   {{services_summary}} – host service counts (e.g. '12 OK · 2 WARN · 1 CRIT')
 *   {{perf_data}}        – raw performance data string
 *   {{metric}}           – value of first perf metric (or named one via {{metric:label}})
 *   {{metric_unit}}      – unit of first perf metric
 *   {{metric:LABEL}}     – value of the perf metric named LABEL
 */
export function interpolateTemplate(
  template: string,
  object: MapObject,
  state: ObjectState | undefined
): string {
  const displayName = getMapElementName(object) ?? ''

  const perfRaw = state?.perf_data ?? ''
  const metrics = parsePerfData(perfRaw)
  const firstMetric = metrics[0]

  const vars: Record<string, string> = {
    name: displayName,
    type: object.type,
    state: state?.state ?? '',
    output: state?.output?.split('\n')[0] ?? '',
    long_output: state?.output ?? '',
    host: object.host_name ?? '',
    service: object.service_description ?? '',
    group: object.group_name ?? '',
    address: state?.address ?? '',
    alias: state?.alias ?? '',
    acknowledged: state?.acknowledged ? 'true' : 'false',
    in_downtime: state?.in_downtime ? 'true' : 'false',
    stale: state?.stale ? 'true' : 'false',
    state_type: state?.state_type ?? '',
    attempts:
      state?.current_attempt && state?.max_attempts
        ? `${state.current_attempt}/${state.max_attempts}`
        : '',
    last_check: formatTimestamp(state?.last_check),
    next_check: formatTimestamp(state?.next_check),
    next_check_in: formatRelativeFuture(state?.next_check),
    last_state_change: formatTimestamp(state?.last_state_change),
    state_duration: formatRelativeDuration(state?.last_state_change),
    services_summary: formatServicesSummary(state?.services_summary),
    perf_data: perfRaw,
    metric: firstMetric ? String(firstMetric.value) + firstMetric.unit : '',
    metric_unit: firstMetric?.unit ?? ''
  }

  return template.replace(/\{\{(\w+(?::\w+)?)\}\}/g, (_, key: string) => {
    // {{metric:LABEL}} – look up a named perf metric
    if (key.startsWith('metric:')) {
      const label = key.slice(7)
      const m = metrics.find((x) => x.label === label)
      return m ? String(m.value) + m.unit : ''
    }
    return vars[key] ?? ''
  })
}

/** Resolve template priority: object → map globals → global settings */
export function resolveTemplate(
  objectTpl: string | null | undefined,
  mapTpl: string | null | undefined,
  globalTpl: string | null | undefined
): string | null {
  return objectTpl || mapTpl || globalTpl || null
}

/**
 * Compact dot-separated host service-state summary (e.g. "1 CRIT · 2 WARN · 12 OK").
 * Sorted severity-descending so the worst state is read first.
 */
export function formatServicesSummary(
  summary: ObjectState['services_summary'] | undefined
): string {
  if (!summary) {
    return ''
  }
  const parts: string[] = []
  if (summary.critical) {
    parts.push(`${summary.critical} CRIT`)
  }
  if (summary.unknown) {
    parts.push(`${summary.unknown} UNKN`)
  }
  if (summary.warning) {
    parts.push(`${summary.warning} WARN`)
  }
  if (summary.pending) {
    parts.push(`${summary.pending} PEND`)
  }
  if (summary.ok) {
    parts.push(`${summary.ok} OK`)
  }
  return parts.join(' · ')
}
