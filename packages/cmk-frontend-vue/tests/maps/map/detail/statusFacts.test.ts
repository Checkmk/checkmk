/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type usei18n from 'cmk-ui-library/lib/i18n'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { describe, expect, it } from 'vitest'

import {
  OVERDUE_GRACE_SECONDS,
  checkInfoRows,
  identityRows,
  severityKindOf,
  stateModifiers
} from '@/maps/map/detail/statusFacts'

import { aDetails, aState, anObject } from '../../support/fixtures'

type TranslateFn = ReturnType<typeof usei18n>['_t']

// Every assertion here is about which facts get stated, not about wording, so
// the translate is the identity -- with the interpolation the real one does,
// since some of the values under test are interpolated.
const _t: TranslateFn = (message: string, params?: Record<string, string | number>) =>
  untranslated(
    params ? message.replace(/%\{(\w+)\}/g, (_, key: string) => String(params[key])) : message
  )

const NOW_MS = 1_700_000_000_000
const NOW_SECONDS = NOW_MS / 1000

describe('severityKindOf', () => {
  it.each([
    ['CRITICAL', 'critical'],
    ['DOWN', 'critical'],
    ['UNREACHABLE', 'unreachable'],
    ['WARNING', 'warn'],
    ['UNKNOWN', 'warn'],
    ['OK', 'ok'],
    ['UP', 'ok']
  ])('reads %s as %s', (state, expected) => {
    expect(severityKindOf(aState({ object_id: 'o', type: 'host', state }))).toBe(expected)
  })

  it('reads an object with no state at all as pending', () => {
    expect(severityKindOf(undefined)).toBe('pending')
  })
})

describe('stateModifiers', () => {
  it('names every qualifier that is set, flapping included', () => {
    const modifiers = stateModifiers(
      aState({
        object_id: 'o',
        type: 'service',
        state: 'CRITICAL',
        acknowledged: true,
        in_downtime: true,
        stale: true,
        notifications_enabled: false
      }),
      aDetails({ type: 'service', host_name: 'web01', is_flapping: true })
    )
    expect(modifiers.map((modifier) => modifier.label)).toEqual([
      'ACK',
      'DOWNTIME',
      'STALE',
      'MUTED',
      'FLAPPING'
    ])
  })

  it('names none on a plain healthy object', () => {
    expect(stateModifiers(aState({ object_id: 'o', type: 'host', state: 'UP' }), null)).toEqual([])
  })
})

describe('identityRows', () => {
  it("links a service's host to the host's own status view", () => {
    const rows = identityRows(
      anObject({ id: 's1', type: 'service', host_name: 'web01', service_description: 'CPU' }),
      aState({ object_id: 's1', type: 'service', state: 'CRITICAL', site_id: 'heute' }),
      'CPU',
      'http://localhost/heute/check_mk/',
      _t
    )
    const host = rows.find((row) => row.label === 'Host')
    expect(host?.value).toBe('web01')
    expect(host?.href).toContain('view.py')
  })

  it("leaves out the alias when it only repeats the object's own name", () => {
    const rows = identityRows(
      anObject({ id: 'h1', type: 'host', host_name: 'web01' }),
      aState({ object_id: 'h1', type: 'host', state: 'UP', alias: 'web01' }),
      'web01',
      null,
      _t
    )
    expect(rows.map((row) => row.label)).not.toContain('Alias')
  })

  it("leaves out the site on a site's own drawer, where it is already the title", () => {
    const rows = identityRows(
      anObject({ id: 'site1', type: 'site', host_name: 'heute' }),
      aState({ object_id: 'site1', type: 'host', state: 'UP', site_id: 'heute' }),
      'heute',
      null,
      _t
    )
    expect(rows.map((row) => row.label)).not.toContain('Site')
  })
})

describe('checkInfoRows', () => {
  function rowsFor(state: Parameters<typeof checkInfoRows>[1]) {
    return checkInfoRows(
      anObject({ id: 's1', type: 'service', host_name: 'web01', service_description: 'CPU' }),
      state,
      null,
      NOW_MS,
      _t
    )
  }

  it('holds back "overdue" while the last check is still recent', () => {
    const rows = rowsFor(
      aState({
        object_id: 's1',
        type: 'service',
        state: 'OK',
        last_check: NOW_SECONDS - 5,
        next_check: NOW_SECONDS - 1
      })
    )
    expect(rows.find((row) => row.label === 'Next check')).toBeUndefined()
  })

  it('calls a check overdue once the check chain itself has stalled', () => {
    const rows = rowsFor(
      aState({
        object_id: 's1',
        type: 'service',
        state: 'OK',
        last_check: NOW_SECONDS - OVERDUE_GRACE_SECONDS - 1,
        next_check: NOW_SECONDS - 1
      })
    )
    const nextCheck = rows.find((row) => row.label === 'Next check')
    expect(nextCheck?.value).toContain('overdue')
    expect(nextCheck?.tone).toBe('warn')
  })

  it('tones a soft attempt, because the state may still settle', () => {
    const rows = rowsFor(
      aState({
        object_id: 's1',
        type: 'service',
        state: 'CRITICAL',
        current_attempt: 1,
        max_attempts: 3,
        state_type: 'SOFT'
      })
    )
    expect(rows[0]?.value).toBe('1/3 (soft)')
    expect(rows[0]?.tone).toBe('warn')
  })

  it('states no attempt count for an aggregator, which has no checks of its own', () => {
    const rows = checkInfoRows(
      anObject({ id: 'g1', type: 'hostgroup', group_name: 'linux' }),
      aState({
        object_id: 'g1',
        type: 'host',
        state: 'CRITICAL',
        current_attempt: 1,
        max_attempts: 3
      }),
      null,
      NOW_MS,
      _t
    )
    expect(rows.map((row) => row.label)).not.toContain('Attempt')
  })

  it('says when the service last was OK, so a long outage is visible', () => {
    const rows = checkInfoRows(
      anObject({ id: 's1', type: 'service', host_name: 'web01', service_description: 'CPU' }),
      aState({ object_id: 's1', type: 'service', state: 'CRITICAL' }),
      aDetails({ type: 'service', host_name: 'web01', last_time_ok: NOW_SECONDS - 3600 }),
      NOW_MS,
      _t
    )
    expect(rows.find((row) => row.label === 'Last OK')).toBeDefined()
  })
})
