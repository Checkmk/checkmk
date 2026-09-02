/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { getLocalTimeZone, now } from '@internationalized/date'
import { afterEach, expect, test, vi } from 'vitest'

import type { AcknowledgeValues } from '@/monitoring/shared/components/action/actions/AcknowledgeForm.vue'
import {
  type AcknowledgeDefaults,
  acknowledgeDefaults,
  createAcknowledgeAction
} from '@/monitoring/shared/components/action/actions/acknowledge'

const NO_LINKS = { presetsUrl: null, notificationRulesUrl: null }

afterEach(() => {
  vi.useRealTimers()
})

function action(defaults: AcknowledgeDefaults) {
  return createAcknowledgeAction<string>({
    targetKind: 'host',
    links: NO_LINKS,
    defaults,
    acknowledge: async () => 0,
    successMessage: () => 'done' as never
  })
}

test('the dialog starts from the option states the site configured', () => {
  const values = action({
    sticky: true,
    persistent: true,
    notify: false,
    expireSeconds: 3600
  }).defaultValues() as AcknowledgeValues

  expect(values.sticky).toBe(true)
  expect(values.persistent).toBe(true)
  expect(values.notify).toBe(false)
})

test('the expiry is prefilled at the configured offset, with the box left unticked', () => {
  const expireSeconds = 2 * 60 * 60
  const before = now(getLocalTimeZone())

  const values = action({
    sticky: false,
    persistent: false,
    notify: true,
    expireSeconds
  }).defaultValues() as AcknowledgeValues

  // Unticked, as the classic form leaves it - the prefill is only there for when it is ticked.
  expect(values.expireOnEnabled).toBe(false)
  expect(values.expireOn).not.toBeNull()
  const offsetSeconds = (values.expireOn!.toDate().getTime() - before.toDate().getTime()) / 1000
  expect(offsetSeconds).toBeGreaterThanOrEqual(expireSeconds - 5)
  expect(offsetSeconds).toBeLessThanOrEqual(expireSeconds + 5)
})

test('the offset is taken per open, so a pane opened later expires later', () => {
  const built = action({ sticky: false, persistent: false, notify: true, expireSeconds: 60 })

  vi.useFakeTimers()
  vi.setSystemTime(new Date('2026-09-02T10:00:00Z'))
  const first = built.defaultValues() as AcknowledgeValues
  vi.setSystemTime(new Date('2026-09-02T11:00:00Z'))
  const second = built.defaultValues() as AcknowledgeValues

  expect(second.expireOn!.toDate().getTime() - first.expireOn!.toDate().getTime()).toBe(60 * 60_000)
})

test('a page that sent no defaults falls back to what the classic form assumes', () => {
  expect(acknowledgeDefaults(undefined)).toEqual({
    sticky: false,
    persistent: false,
    notify: true,
    expireSeconds: 3600
  })
})

test('the payload is read as it arrives, snake_case and all', () => {
  expect(
    acknowledgeDefaults({ sticky: true, persistent: false, notify: false, expire_seconds: 7200 })
  ).toEqual({ sticky: true, persistent: false, notify: false, expireSeconds: 7200 })
})
