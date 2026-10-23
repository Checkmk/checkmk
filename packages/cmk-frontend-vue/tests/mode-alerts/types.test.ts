/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { expect, test } from 'vitest'

import {
  alertConditions,
  alertName,
  alertThresholds,
  emptyAlert,
  hasCompleteThresholds,
  hasThresholds,
  hasUnparsableRegex,
  servicePattern
} from '@/mode-alerts/types'

import { PREDICTION_PERIODS } from './thresholds-spec'

// The folder choice's option ids and the folder paths they stand for.
const FOLDERS = { '': '', web: 'linux/web' }

test('a broken regular expression is reported as unparsable', () => {
  expect(hasUnparsableRegex({ ...emptyAlert(), matchType: 'regex', servicePattern: '[' })).toBe(
    true
  )
})

test('a valid regular expression is accepted', () => {
  expect(
    hasUnparsableRegex({ ...emptyAlert(), matchType: 'regex', servicePattern: 'HTTP.*duration' })
  ).toBe(false)
})

test('a name that is not a regular expression is never reported as unparsable', () => {
  expect(hasUnparsableRegex({ ...emptyAlert(), matchType: 'exact', servicePattern: '[' })).toBe(
    false
  )
})

test('surrounding whitespace is not part of the alert name', () => {
  expect(alertName({ ...emptyAlert(), name: '  Latency too high  ' })).toBe('Latency too high')
})

test('surrounding whitespace is not part of the service name', () => {
  expect(servicePattern({ ...emptyAlert(), servicePattern: '  HTTP  ' })).toBe('HTTP')
})

test('a name of only whitespace counts as no name', () => {
  expect(alertName({ ...emptyAlert(), name: '   ' })).toBe('')
})

test('without further conditions an alert applies to the Main folder and everything below', () => {
  expect(alertConditions(emptyAlert(), FOLDERS)).toEqual({
    folder: '/',
    host_tags: [],
    host_label_groups: []
  })
})

test('a folder is sent as its path', () => {
  expect(alertConditions(emptyAlert({ folder_path: 'web' }), FOLDERS).folder).toBe('/linux/web')
})

test('an unknown folder option is refused rather than widened to the Main folder', () => {
  expect(() => alertConditions(emptyAlert({ folder_path: 'gone' }), FOLDERS)).toThrow()
})

test('each host tag operator is sent like the rule API expects it', () => {
  const conditions = alertConditions(
    emptyAlert({
      folder_path: '',
      host_tags: [
        { group_name: 'criticality', value: { oper_eq: 'prod' } },
        { group_name: 'networking', value: { oper_ne: 'wan' } },
        { group_name: 'agent', value: { oper_or: ['cmk-agent', 'all-agents'] } },
        { group_name: 'snmp_ds', value: { oper_nor: ['snmp-v1', 'snmp-v2'] } }
      ]
    }),
    FOLDERS
  )

  expect(conditions.host_tags).toEqual([
    { key: 'criticality', operator: 'is', value: 'prod' },
    { key: 'networking', operator: 'is_not', value: 'wan' },
    { key: 'agent', operator: 'one_of', value: ['cmk-agent', 'all-agents'] },
    { key: 'snmp_ds', operator: 'none_of', value: ['snmp-v1', 'snmp-v2'] }
  ])
})

test('host label groups are sent as they are', () => {
  const groups = [
    { operator: 'and' as const, label_group: [{ operator: 'and' as const, label: 'os:linux' }] },
    { operator: 'not' as const, label_group: [{ operator: 'or' as const, label: 'env:test' }] }
  ]

  expect(
    alertConditions(emptyAlert({ folder_path: '', host_label_groups: groups }), FOLDERS)
      .host_label_groups
  ).toEqual(groups)
})

test('explicit hosts select the listed hosts', () => {
  expect(
    alertConditions(
      emptyAlert({ folder_path: '', explicit_hosts: { value: ['web01', '~db'], negate: false } }),
      FOLDERS
    ).host_name
  ).toEqual({ match_on: ['web01', '~db'], operator: 'one_of' })
})

test('negated explicit hosts select all hosts but the listed ones', () => {
  expect(
    alertConditions(
      emptyAlert({ folder_path: '', explicit_hosts: { value: ['web01'], negate: true } }),
      FOLDERS
    ).host_name
  ).toEqual({ match_on: ['web01'], operator: 'none_of' })
})

test('a host label group without labels is left out, as the rule editor does', () => {
  const linux = {
    operator: 'and' as const,
    label_group: [{ operator: 'and' as const, label: 'os:linux' }]
  }

  expect(
    alertConditions(
      emptyAlert({
        folder_path: '',
        host_label_groups: [linux, { operator: 'or', label_group: [] }]
      }),
      FOLDERS
    ).host_label_groups
  ).toEqual([linux])
})

test('a host label group that becomes the first one does not widen to every host', () => {
  expect(
    alertConditions(
      emptyAlert({
        folder_path: '',
        host_label_groups: [
          { operator: 'and', label_group: [] },
          { operator: 'or', label_group: [{ operator: 'and', label: 'os:linux' }] }
        ]
      }),
      FOLDERS
    ).host_label_groups
  ).toEqual([{ operator: 'and', label_group: [{ operator: 'and', label: 'os:linux' }] }])
})

test('the empty entry the host list offers for typing is not sent', () => {
  expect(
    alertConditions(
      emptyAlert({ folder_path: '', explicit_hosts: { value: ['web01', ''], negate: false } }),
      FOLDERS
    ).host_name
  ).toEqual({ match_on: ['web01'], operator: 'one_of' })
})

const [WEEKDAY, , , MINUTE] = Object.keys(PREDICTION_PERIODS) as [string, string, string, string]

test('an alert without upper or lower levels has no thresholds', () => {
  expect(hasThresholds(emptyAlert())).toBe(false)
})

test('"No levels" counts as a threshold, as it overrides other rules', () => {
  expect(hasThresholds(emptyAlert(undefined, { lower_levels: ['no_levels', null] }))).toBe(true)
})

test('fixed levels are sent as their warning and critical levels', () => {
  const model = emptyAlert(undefined, {
    upper_levels: ['fixed', [80, 90]],
    lower_levels: ['fixed', [20, 10]]
  })

  expect(alertThresholds(model, PREDICTION_PERIODS)).toEqual({
    upper: { type: 'fixed', warn: 80, crit: 90 },
    lower: { type: 'fixed', warn: 20, crit: 10 }
  })
})

test('"No levels" is sent, a side left out is not', () => {
  const model = emptyAlert(undefined, { upper_levels: ['no_levels', null] })

  expect(alertThresholds(model, PREDICTION_PERIODS)).toEqual({ upper: { type: 'no_levels' } })
})

test('predictive levels are sent with the name of their period', () => {
  const model = emptyAlert(undefined, {
    upper_levels: [
      'predictive',
      { period: MINUTE, horizon: 7, levels: ['stdev', [2, 3]], bound: null }
    ]
  })

  expect(alertThresholds(model, PREDICTION_PERIODS)).toEqual({
    upper: {
      type: 'predictive',
      period: 'minute_of_hour',
      horizon_days: 7,
      difference: { type: 'stdev', warn: 2, crit: 3 }
    }
  })
})

test('the fixed limits of predictive levels are sent', () => {
  const model = emptyAlert(undefined, {
    lower_levels: [
      'predictive',
      { period: WEEKDAY, horizon: 90, levels: ['relative', [10, 20]], bound: [5, 2] }
    ]
  })

  expect(alertThresholds(model, PREDICTION_PERIODS).lower).toEqual({
    type: 'predictive',
    period: 'day_of_week',
    horizon_days: 90,
    difference: { type: 'relative', warn: 10, crit: 20 },
    fixed_limits: { warn: 5, crit: 2 }
  })
})

test('an unknown period option is refused', () => {
  const model = emptyAlert(undefined, {
    upper_levels: [
      'predictive',
      { period: 'unknown', horizon: 90, levels: ['absolute', [1, 2]], bound: null }
    ]
  })

  expect(() => alertThresholds(model, PREDICTION_PERIODS)).toThrow('unknown')
})

test('levels with all fields filled in are complete', () => {
  const model = emptyAlert(undefined, {
    upper_levels: ['fixed', [80, 90]],
    lower_levels: [
      'predictive',
      { period: WEEKDAY, horizon: 90, levels: ['absolute', [1, 2]], bound: [5, 2] }
    ]
  })

  expect(hasCompleteThresholds(model)).toBe(true)
})

test('"No levels" has nothing to fill in', () => {
  expect(hasCompleteThresholds(emptyAlert(undefined, { upper_levels: ['no_levels', null] }))).toBe(
    true
  )
})

test('an empty fixed level is incomplete', () => {
  expect(hasCompleteThresholds(emptyAlert(undefined, { upper_levels: ['fixed', [80, '']] }))).toBe(
    false
  )
})

test('an empty fixed limit of predictive levels is incomplete', () => {
  const model = emptyAlert(undefined, {
    lower_levels: [
      'predictive',
      { period: WEEKDAY, horizon: 90, levels: ['absolute', [1, 2]], bound: ['', 2] }
    ]
  })

  expect(hasCompleteThresholds(model)).toBe(false)
})
