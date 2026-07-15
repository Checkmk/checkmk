/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { render, screen } from '@testing-library/vue'
import { Response } from 'cmk-ui-library/components/CmkSuggestions/suggestions'
import { defineComponent, ref } from 'vue'

import GroupByKeyPill from '@/metric-backend/group-by/GroupByKeyPill.vue'
import type { GroupKey, GroupLevel } from '@/metric-backend/group-by/types'

const KEY_LEVELS: Record<string, GroupLevel> = {
  'service.name': 'resource',
  'http.route': 'datapoint'
}

function querySuggestions(query: string): Promise<Response> {
  const matches = Object.keys(KEY_LEVELS)
    .filter((k) => k.includes(query))
    .map((k) => ({ name: k, title: k }))
  return Promise.resolve(new Response(matches))
}

function renderPill(initial: Partial<GroupKey> = {}, editing = false) {
  const condition = ref<GroupKey>({ id: '1', level: 'resource', key: 'service.name', ...initial })
  const removed = ref(false)
  const keyUpdates: string[] = []
  const wrapper = defineComponent({
    components: { GroupByKeyPill },
    setup() {
      return {
        condition,
        editing,
        removed,
        querySuggestions,
        onUpdateLevel: (level: GroupLevel) => {
          condition.value = { ...condition.value, level }
        },
        onUpdateKey: (key: string) => {
          keyUpdates.push(key)
          condition.value = { ...condition.value, key }
        },
        onRemove: () => {
          removed.value = true
        }
      }
    },
    template: `
      <GroupByKeyPill
        :condition="condition"
        :editing="editing"
        removable
        :query-suggestions="querySuggestions"
        @update:level="onUpdateLevel"
        @update:key="onUpdateKey"
        @remove="onRemove"
      />
    `
  })
  render(wrapper)
  return { condition, removed, keyUpdates }
}

test('the read-only chip shows the bracketed level and the key', () => {
  renderPill()
  const chip = screen.getByRole('button', { name: /Edit group key/ })
  expect(chip).toHaveTextContent('[Resource]')
  expect(chip).toHaveTextContent('service.name')
})

test('selecting a suggested key emits a single update:key (level inference is the parent’s job)', async () => {
  const { condition, keyUpdates } = renderPill({ key: '' }, true)
  expect(screen.getByRole('combobox', { name: 'Attribute level' })).toBeVisible()

  // Let the auto-open (nextTick) settle so the click below cannot re-toggle the dropdown.
  await new Promise((resolve) => setTimeout(resolve, 0))
  const keyCombobox = screen.getByRole('combobox', { name: 'Attribute key' })
  if (keyCombobox.getAttribute('aria-expanded') !== 'true') {
    await userEvent.click(keyCombobox)
  }
  const filter = screen.getByRole('textbox', { name: 'filter' })
  await userEvent.clear(filter)
  await userEvent.type(filter, 'http.route')
  await userEvent.click(await screen.findByRole('option', { name: 'http.route' }))

  expect(condition.value.key).toBe('http.route')
  expect(keyUpdates).toEqual(['http.route'])
})

test('the remove button emits remove', async () => {
  const { removed } = renderPill()
  await userEvent.click(screen.getByRole('button', { name: 'Remove group key' }))
  expect(removed.value).toBe(true)
})
