/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { render } from '@testing-library/vue'
import { defineComponent, nextTick, ref } from 'vue'

import { useGraphTimeRange } from '@/graphing/composables/useGraphTimeRange'
import type { RequestedTimeRange } from '@/graphing/types'

function mountComposable(initial: RequestedTimeRange) {
  const source = ref<RequestedTimeRange>({ ...initial })
  let api!: ReturnType<typeof useGraphTimeRange>
  render(
    defineComponent({
      setup() {
        api = useGraphTimeRange(() => source.value)
        return () => null
      }
    })
  )
  return { api, source }
}

test('initializes activeTimeRange from the getter', () => {
  const { api } = mountComposable({ start: 100, end: 200 })
  expect(api.activeTimeRange.value).toEqual({ start: 100, end: 200 })
})

test('setActiveTimeRange updates activeTimeRange immediately', () => {
  const { api } = mountComposable({ start: 100, end: 200 })
  api.setActiveTimeRange({ start: 300, end: 400 })
  expect(api.activeTimeRange.value).toEqual({ start: 300, end: 400 })
})

test('setActiveTimeRange copies the value so later mutations to the argument do not propagate', () => {
  const { api } = mountComposable({ start: 100, end: 200 })
  const newRange = { start: 300, end: 400 }
  api.setActiveTimeRange(newRange)
  newRange.start = 999
  expect(api.activeTimeRange.value.start).toBe(300)
})

test('activeTimeRange tracks the getter reactively when the source changes', async () => {
  const { api, source } = mountComposable({ start: 100, end: 200 })
  source.value = { start: 300, end: 400 }
  await nextTick()
  expect(api.activeTimeRange.value).toEqual({ start: 300, end: 400 })
})
