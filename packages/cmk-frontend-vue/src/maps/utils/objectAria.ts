/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
/**
 * Accessible names for monitored map objects. Every canvas (static, radar,
 * worldmap, flow, presentation) renders objects graphically — the aria-label
 * is the only thing that tells a screen-reader user what the object is and
 * which state it is in, so all canvases share this one builder.
 */
import type usei18n from 'cmk-ui-library/lib/i18n'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import type { TranslatedString } from 'cmk-ui-library/lib/i18nString'

import type { MapElement, MonitoringState } from '@/maps/types/api'

import { objectDisplayName } from './dropdownOptions'
import { VISUAL_ONLY_TYPES } from './naming'

/**
 * The ``_t`` a component hands to a helper. Gettext extraction only sees literal
 * ``_t('…')`` call sites, so a helper takes the translator rather than
 * translating a dynamic key itself.
 */
type TranslateFn = ReturnType<typeof usei18n>['_t']

export function stateAriaLabel(_t: TranslateFn, state: string | undefined): string {
  switch (state) {
    case 'UP':
      return _t('Up')
    case 'DOWN':
      return _t('Down')
    case 'UNREACHABLE':
      return _t('Unreachable')
    case 'OK':
      return _t('OK')
    case 'WARNING':
      return _t('Warning')
    case 'CRITICAL':
      return _t('Critical')
    case 'UNKNOWN':
      return _t('Unknown')
    case 'PENDING':
      return _t('Pending')
    case 'NO_PERMISSION':
      return _t('No permission')
    case 'NOT_FOUND':
      return _t('Not found')
    default:
      return _t('No state')
  }
}

const MONITORING_STATES: readonly MonitoringState[] = [
  'UP',
  'DOWN',
  'UNREACHABLE',
  'OK',
  'WARNING',
  'CRITICAL',
  'UNKNOWN',
  'PENDING',
  'NO_PERMISSION',
  'NOT_FOUND'
]

/** Translated word for a plain severity token (severity_counts keys, tree node
 *  states); unknown tokens pass through untouched so future additions degrade
 *  gracefully instead of crashing. */
export function stateWordFromToken(_t: TranslateFn, token: string): string {
  const known = MONITORING_STATES.find((s) => s === token)
  return known === undefined ? token : stateAriaLabel(_t, known)
}

/**
 * The short word Checkmk's monitoring pages write for a state on screen -- CRIT,
 * WARN, UNKN, UNREACH -- for a count or a caption. What a screen reader hears
 * stays the full word, from ``stateWordFromToken``.
 */
export function stateShortWordFromToken(_t: TranslateFn, token: string): TranslatedString {
  switch (token) {
    case 'CRITICAL':
      return _t('CRIT')
    case 'WARNING':
      return _t('WARN')
    case 'UNKNOWN':
      return _t('UNKN')
    case 'UNREACHABLE':
      return _t('UNREACH')
    case 'PENDING':
      return _t('PEND')
    default:
      return untranslated(token)
  }
}

/**
 * The word a state count bar writes for a state, as the monitoring pages'
 * ``ServiceSummaryBar`` and state filters do: UNKNOWN and PENDING in full.
 */
export function stateCountWordFromToken(_t: TranslateFn, token: string): TranslatedString {
  switch (token) {
    case 'OK':
      return _t('OK')
    case 'UP':
      return _t('UP')
    case 'DOWN':
      return _t('DOWN')
    case 'UNKNOWN':
      return _t('UNKNOWN')
    case 'PENDING':
      return _t('PENDING')
    default:
      return stateShortWordFromToken(_t, token)
  }
}

export function objectAriaLabel(
  _t: TranslateFn,
  object: MapElement,
  state: string | undefined,
  stale = false
): string {
  const name = objectDisplayName(object, _t)
  if (VISUAL_ONLY_TYPES.includes(object.type)) {
    return name
  }
  const label = `${name}, ${stateAriaLabel(_t, state)}`
  return stale ? `${label}, ${_t('stale')}` : label
}
