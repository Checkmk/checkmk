/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import type usei18n from 'cmk-ui-library/lib/i18n'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { describe, expect, it } from 'vitest'

import { activityCount, commentRows, downtimeRows } from '@/maps/map/detail/activityFacts'

import { aDetails } from '../../support/fixtures'

type TranslateFn = ReturnType<typeof usei18n>['_t']

const _t: TranslateFn = (message: string, params?: Record<string, string | number>) =>
  untranslated(
    params ? message.replace(/%\{(\w+)\}/g, (_, key: string) => String(params[key])) : message
  )

const NOW_MS = 1_700_000_000_000
const NOW_SECONDS = NOW_MS / 1000

describe('commentRows', () => {
  it('ages a comment against the drawer clock rather than reading its own', () => {
    const rows = commentRows(
      aDetails({
        type: 'service',
        host_name: 'web01',
        comments: [
          {
            id: 7,
            author: 'ops',
            comment: 'looking into it',
            entry_time: NOW_SECONDS - 120,
            expire_time: null
          }
        ]
      }),
      NOW_MS,
      _t
    )
    expect(rows[0]?.age).toBe('2m 0s ago')
    expect(rows[0]?.expires).toBeNull()
  })

  it('states when a comment goes away on its own', () => {
    const rows = commentRows(
      aDetails({
        type: 'service',
        host_name: 'web01',
        comments: [
          {
            id: 7,
            author: 'ops',
            comment: 'until the maintenance window',
            entry_time: NOW_SECONDS,
            expire_time: NOW_SECONDS + 3600
          }
        ]
      }),
      NOW_MS,
      _t
    )
    expect(rows[0]?.expires).toBe('in 1h 0m')
  })

  it('stands in for a comment nobody signed', () => {
    const rows = commentRows(
      aDetails({
        type: 'service',
        host_name: 'web01',
        comments: [{ id: 1, author: '', comment: 'x', entry_time: NOW_SECONDS, expire_time: null }]
      }),
      NOW_MS,
      _t
    )
    expect(rows[0]?.author).toBe('?')
  })
})

describe('downtimeRows', () => {
  it('carries whether the downtime is fixed, which is what FLEX marks', () => {
    const rows = downtimeRows(
      aDetails({
        type: 'host',
        host_name: 'web01',
        downtimes: [
          {
            id: 3,
            author: 'ops',
            comment: 'reboot',
            start_time: NOW_SECONDS,
            end_time: NOW_SECONDS + 7200,
            fixed: false
          }
        ]
      })
    )
    expect(rows[0]?.fixed).toBe(false)
    expect(rows[0]?.timeRange).toContain('→')
  })
})

describe('activityCount', () => {
  it('counts comments and downtimes together, since one tab holds both', () => {
    expect(
      activityCount(
        aDetails({
          type: 'host',
          host_name: 'web01',
          comments: [
            { id: 1, author: 'a', comment: 'x', entry_time: NOW_SECONDS, expire_time: null }
          ],
          downtimes: [
            {
              id: 2,
              author: 'a',
              comment: 'y',
              start_time: NOW_SECONDS,
              end_time: NOW_SECONDS + 1,
              fixed: true
            }
          ]
        })
      )
    ).toBe(2)
  })

  it('counts nothing before the details have arrived', () => {
    expect(activityCount(null)).toBe(0)
  })
})
