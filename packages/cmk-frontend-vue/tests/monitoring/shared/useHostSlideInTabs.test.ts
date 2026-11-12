/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { HOST_TAB_OVERVIEW } from '@/monitoring/shared/hostSlideInTabs'
import { useHostSlideInTabs } from '@/monitoring/shared/useHostSlideInTabs'

test('opens on the overview tab when asked to reveal the relations', () => {
  const tabs = useHostSlideInTabs()
  tabs.selectTab('services')

  tabs.open(true)

  expect(tabs.tabId.value).toBe(HOST_TAB_OVERVIEW)
})

test('asks again for the relations on every reveal of the same host', () => {
  const tabs = useHostSlideInTabs()

  tabs.open(true)
  const first = tabs.revealRelationsRequest.value
  tabs.open(true)

  expect(tabs.revealRelationsRequest.value).toBeGreaterThan(first)
})

test('keeps the tab and drops the reveal when opened without it', () => {
  const tabs = useHostSlideInTabs()
  tabs.open(true)
  tabs.selectTab('services')
  tabs.selectTab(HOST_TAB_OVERVIEW)

  tabs.open(false)

  expect([tabs.tabId.value, tabs.revealRelationsRequest.value]).toEqual([HOST_TAB_OVERVIEW, 0])
})

test('drops the reveal when the user leaves the overview tab', () => {
  const tabs = useHostSlideInTabs()
  tabs.open(true)

  tabs.selectTab('services')

  expect(tabs.revealRelationsRequest.value).toBe(0)
})
