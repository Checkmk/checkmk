/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * What the status tab states about an object, as plain functions over its state.
 *
 * The wording and the judgement calls live here rather than in the template:
 * which qualifiers a state carries, which identity facts are worth repeating
 * next to the title, and when a check counts as overdue. All of it is derived
 * -- nothing here fetches or holds state -- so each rule can be read and
 * tested on its own.
 */
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import type { MapElement, ObjectDetails, ObjectState } from '@/maps/types/api'
import type { TranslateFn } from '@/maps/utils/dropdownOptions'
import { buildCheckmkUrl } from '@/maps/utils/mapNavigation'
import { formatRelativeDuration, formatRelativeFuture } from '@/maps/utils/time'

/**
 * CMC reschedules checks sub-second, so `next_check` sits slightly behind "now"
 * between checks even on a healthy object. Only call a check overdue once the
 * LAST check is itself this stale -- otherwise every healthy object flickers
 * "overdue" once a second.
 */
export const OVERDUE_GRACE_SECONDS = 60

/** How loud the drawer reads: drives the accent and the severity bar. */
export type SeverityKind = 'critical' | 'unreachable' | 'warn' | 'ok' | 'pending'

export function severityKindOf(state: ObjectState | undefined): SeverityKind {
  switch (state?.state) {
    case 'CRITICAL':
    case 'DOWN':
      return 'critical'
    case 'UNREACHABLE':
      return 'unreachable'
    case 'WARNING':
    case 'UNKNOWN':
      return 'warn'
    case 'OK':
    case 'UP':
      return 'ok'
    default:
      return 'pending'
  }
}

const PROBLEM_STATES = new Set(['CRITICAL', 'WARNING', 'UNKNOWN', 'DOWN', 'UNREACHABLE'])

export function isProblemState(state: ObjectState | undefined): boolean {
  return state ? PROBLEM_STATES.has(state.state) : false
}

/** A qualifier on the state, rather than a state of its own. */
export interface StateModifier {
  label: string
  kind: 'ack' | 'downtime' | 'stale' | 'muted' | 'flapping'
}

export function stateModifiers(
  state: ObjectState | undefined,
  details: ObjectDetails | null
): StateModifier[] {
  if (!state) {
    return []
  }
  const modifiers: StateModifier[] = []
  if (state.acknowledged) {
    modifiers.push({ label: 'ACK', kind: 'ack' })
  }
  if (state.in_downtime) {
    modifiers.push({ label: 'DOWNTIME', kind: 'downtime' })
  }
  if (state.stale) {
    modifiers.push({ label: 'STALE', kind: 'stale' })
  }
  if (state.notifications_enabled === false) {
    modifiers.push({ label: 'MUTED', kind: 'muted' })
  }
  if (details?.is_flapping) {
    modifiers.push({ label: 'FLAPPING', kind: 'flapping' })
  }
  return modifiers
}

/** One label/value fact, as ``DetailMetaList`` renders it. */
export interface MetaRow {
  label: string
  value: string
  /** Worth a second look -- a soft attempt, a check outside its period. */
  tone?: 'warn' | undefined
  href?: string | null
}

/**
 * Who the object is: the facts that identify it beyond its title.
 *
 * A service names its host and links to the host's own status view, the way
 * Checkmk's own views do -- the operator arriving from a service problem
 * usually wants the host next.
 */
export function identityRows(
  object: MapElement | null,
  state: ObjectState | undefined,
  displayName: string,
  checkmkUrl: string | null | undefined,
  _t: TranslateFn
): MetaRow[] {
  if (!state) {
    return []
  }
  const rows: MetaRow[] = []
  if (state.alias && state.alias !== displayName) {
    rows.push({ label: 'Alias', value: state.alias })
  }
  if (state.address) {
    rows.push({ label: 'Address', value: state.address })
  }
  if (object?.type === 'service' && object.host_name) {
    rows.push({
      label: _t('Host'),
      value: object.host_name,
      href: buildCheckmkUrl(
        { ...object, type: 'host', service_description: null },
        checkmkUrl ?? null,
        state.site_id
      )
    })
  }
  // A site drawer's title is already the site name -- no point repeating it.
  if (state.site_id && object?.type !== 'site') {
    rows.push({ label: _t('Site'), value: state.site_id })
  }
  return rows
}

/** Aggregators have no check attempts of their own; "0/0" would only confuse. */
function isAggregator(object: MapElement | null): boolean {
  switch (object?.type) {
    case 'aggregation':
    case 'hostgroup':
    case 'servicegroup':
    case 'dyngroup':
      return true
    default:
      return false
  }
}

/**
 * How the check itself is doing: which attempt, when it last ran, when it runs
 * next, and -- while the object is not OK -- when it last was.
 */
export function checkInfoRows(
  object: MapElement | null,
  state: ObjectState | undefined,
  details: ObjectDetails | null,
  nowMs: number,
  _t: TranslateFn
): MetaRow[] {
  if (!state) {
    return []
  }
  const rows: MetaRow[] = []
  const nowSeconds = Math.floor(nowMs / 1000)

  if (
    !isAggregator(object) &&
    typeof state.current_attempt === 'number' &&
    typeof state.max_attempts === 'number'
  ) {
    const isSoft = state.state_type === 'SOFT' || state.state_type === 'soft'
    rows.push({
      label: _t('Attempt'),
      value: _t('%{current}/%{max} (%{type})', {
        current: state.current_attempt,
        max: state.max_attempts,
        type: isSoft ? _t('soft') : _t('hard')
      }),
      tone: isSoft ? 'warn' : undefined
    })
  }

  if (state.last_check && state.last_check > 0) {
    rows.push({
      label: _t('Last check'),
      value: _t('%{duration} ago', {
        duration: formatRelativeDuration(state.last_check, nowMs)
      })
    })
  } else if (state.last_check === 0) {
    rows.push({ label: _t('Last check'), value: _t('never') })
  }

  if (state.next_check && state.next_check > 0) {
    if (state.next_check < nowSeconds) {
      const sinceLastCheck =
        state.last_check && state.last_check > 0 ? nowSeconds - state.last_check : Infinity
      if (sinceLastCheck >= OVERDUE_GRACE_SECONDS) {
        rows.push({
          label: _t('Next check'),
          value: `${_t('overdue')} (${formatRelativeDuration(state.next_check, nowMs)})`,
          tone: 'warn'
        })
      }
    } else {
      rows.push({
        label: _t('Next check'),
        value: _t('in %{duration}', {
          // A check due sub-second from now formats to '' -- '<1s' keeps the
          // row from reading as a dangling "in ".
          duration: formatRelativeFuture(state.next_check, nowMs) || '<1s'
        })
      })
    }
  }

  // Service-only: lets the operator tell "broken for two days" from "just
  // flipped" without leaving the drawer.
  if (details?.last_time_ok && details.last_time_ok > 0 && state.state !== 'OK') {
    rows.push({
      label: _t('Last OK'),
      value: _t('%{duration} ago', {
        duration: formatRelativeDuration(details.last_time_ok, nowMs)
      })
    })
  }

  return rows
}

/** How long the object has been in this state, where that is known. */
export function sinceText(
  state: ObjectState | undefined,
  nowMs: number,
  _t: TranslateFn
): TranslatedString | null {
  const duration = formatRelativeDuration(state?.last_state_change, nowMs)
  return duration ? _t('since %{duration}', { duration }) : null
}
