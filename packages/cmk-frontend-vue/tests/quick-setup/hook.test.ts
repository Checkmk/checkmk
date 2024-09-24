/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import useWizard from '@/quick-setup/components/quick-setup/useWizard'

test('Quick Setup hook initialization', async () => {
  let quickSetup = useWizard(3, 'guided')

  expect(quickSetup.stages.value).toBe(3)
  expect(quickSetup.stage.value).toBe(0)
  expect(quickSetup.mode.value).toBe('guided')

  quickSetup = useWizard(4, 'overview')
  expect(quickSetup.stages.value).toBe(4)
  expect(quickSetup.stage.value).toBe(0)
  expect(quickSetup.mode.value).toBe('overview')
})

test('Quick Setup hook switch display mode', async () => {
  const quickSetup = useWizard(3, 'guided')
  expect(quickSetup.mode.value).toBe('guided')

  quickSetup.setMode('overview')
  expect(quickSetup.mode.value).toBe('overview')

  quickSetup.setMode('overview')
  expect(quickSetup.mode.value).toBe('overview')

  quickSetup.toggleMode()
  expect(quickSetup.mode.value).toBe('guided')

  quickSetup.toggleMode()
  expect(quickSetup.mode.value).toBe('overview')
})

test('Quick Setup navigation', async () => {
  const quickSetup = useWizard(3, 'guided')

  expect(quickSetup.stage.value).toBe(0)

  quickSetup.next()
  expect(quickSetup.stage.value).toBe(1)

  quickSetup.prev()
  expect(quickSetup.stage.value).toBe(0)

  quickSetup.goto(2)
  expect(quickSetup.stage.value).toBe(2)

  quickSetup.next()
  expect(quickSetup.stage.value).toBe(2)

  quickSetup.rewind()
  expect(quickSetup.stage.value).toBe(0)
})
