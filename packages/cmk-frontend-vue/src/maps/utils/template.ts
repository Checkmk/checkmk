/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { escapeHtml } from 'cmk-ui-library/lib/utils'

import type { MapElement as MapObject, ObjectState } from '@/maps/types/api'
import { PLACEHOLDER, getMapElementName } from '@/maps/utils/naming'
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
 *   {{map}}              – name of the linked map
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
 *   {{services_summary}} – service counts (e.g. '12 OK · 2 WARN · 1 CRIT')
 *   {{hosts_summary}}    – a group's host counts (e.g. '1 DOWN · 4 UP')
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
  // The template is authored markup, but the substituted values carry monitoring
  // data a monitored host controls (plugin output, alias, labels). Escape every
  // value so a host cannot inject markup of its own — the sanitizer that runs
  // afterwards is the second line of defense, not the first.
  return fillPlaceholders(template, object, state, escapeHtml)
}

/**
 * An object's label text with the placeholders of ``interpolateTemplate``
 * filled in, as plain text. ``{{name}}`` names the object, not the label.
 */
export function labelText(object: MapObject, state: ObjectState | undefined): string | null {
  const text = object.label?.text
  return text ? fillPlaceholders(text, { ...object, label: null }, state, (value) => value) : null
}

/** What an object is called: its label with the placeholders filled in, else its name. */
export function objectName(object: MapObject, state: ObjectState | undefined): string {
  return labelText(object, state) || (getMapElementName(object) ?? '')
}

function fillPlaceholders(
  template: string,
  object: MapObject,
  state: ObjectState | undefined,
  encode: (value: string) => string
): string {
  if (!PLACEHOLDER.test(template)) {
    return template
  }
  // Values are worked out on demand: a caption naming the host should not pay
  // for formatting timestamps and parsing perfdata on every state update.
  let parsedMetrics: ReturnType<typeof parsePerfData> | null = null
  const metrics = () => (parsedMetrics ??= parsePerfData(state?.perf_data ?? ''))
  const vars: Record<string, () => string> = {
    name: () => objectName(object, state),
    type: () => object.type,
    state: () => state?.state ?? '',
    output: () => state?.output?.split('\n')[0] ?? '',
    long_output: () => state?.output ?? '',
    host: () => object.host_name ?? '',
    service: () => object.service_description ?? '',
    group: () => object.group_name ?? '',
    map: () => object.map_name ?? '',
    address: () => state?.address ?? '',
    alias: () => state?.alias ?? '',
    acknowledged: () => (state?.acknowledged ? 'true' : 'false'),
    in_downtime: () => (state?.in_downtime ? 'true' : 'false'),
    stale: () => (state?.stale ? 'true' : 'false'),
    state_type: () => state?.state_type ?? '',
    attempts: () =>
      state?.current_attempt && state?.max_attempts
        ? `${state.current_attempt}/${state.max_attempts}`
        : '',
    last_check: () => formatTimestamp(state?.last_check),
    next_check: () => formatTimestamp(state?.next_check),
    next_check_in: () => formatRelativeFuture(state?.next_check),
    last_state_change: () => formatTimestamp(state?.last_state_change),
    state_duration: () => formatRelativeDuration(state?.last_state_change),
    services_summary: () => formatServicesSummary(state?.services_summary),
    hosts_summary: () => formatHostsSummary(state?.hosts_summary),
    perf_data: () => state?.perf_data ?? '',
    metric: () => {
      const first = metrics()[0]
      return first ? String(first.value) + first.unit : ''
    },
    metric_unit: () => metrics()[0]?.unit ?? ''
  }

  return template.replace(new RegExp(PLACEHOLDER, 'g'), (_, key: string) => {
    // {{metric:LABEL}} – look up a named perf metric
    if (key.startsWith('metric:')) {
      const label = key.slice(7)
      const m = metrics().find((x) => x.label === label)
      return m ? encode(String(m.value) + m.unit) : ''
    }
    return encode(vars[key]?.() ?? '')
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
  return [
    [summary.critical, 'CRIT'],
    [summary.unknown, 'UNKN'],
    [summary.warning, 'WARN'],
    [summary.pending, 'PEND'],
    [summary.ok, 'OK']
  ]
    .filter(([count]) => count)
    .map(([count, label]) => `${count} ${label}`)
    .join(' · ')
}

// The host counts sit in the same slots: UP=ok, DOWN=critical, UNREACHABLE=unknown.
export function formatHostsSummary(summary: ObjectState['hosts_summary'] | undefined): string {
  if (!summary) {
    return ''
  }
  return [
    [summary.critical, 'DOWN'],
    [summary.unknown, 'UNREACH'],
    [summary.pending, 'PEND'],
    [summary.ok, 'UP']
  ]
    .filter(([count]) => count)
    .map(([count, label]) => `${count} ${label}`)
    .join(' · ')
}
