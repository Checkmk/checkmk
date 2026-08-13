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
import type { AttributeKind, GroupKey } from '@/metric-backend/group-by/types'

const KEY_ATTRIBUTE_KINDS: Record<string, AttributeKind> = {
  'service.name': 'resource',
  'http.route': 'data_point'
}

function querySuggestions(query: string): Promise<Response> {
  const matches = Object.keys(KEY_ATTRIBUTE_KINDS)
    .filter((k) => k.includes(query))
    .map((k) => ({ name: k, title: k }))
  return Promise.resolve(new Response(matches))
}

function renderPill(initial: Partial<GroupKey> = {}, editing = false, hideAttributeKind = false) {
  const condition = ref<GroupKey>({
    id: '1',
    attributeKind: 'resource',
    attributeKey: 'service.name',
    ...initial
  })
  const removed = ref(false)
  const keyUpdates: string[] = []
  const wrapper = defineComponent({
    components: { GroupByKeyPill },
    setup() {
      return {
        condition,
        editing,
        hideAttributeKind,
        removed,
        querySuggestions,
        onUpdateAttributeKind: (attributeKind: AttributeKind) => {
          condition.value = { ...condition.value, attributeKind }
        },
        onUpdateAttributeKey: (attributeKey: string) => {
          keyUpdates.push(attributeKey)
          condition.value = { ...condition.value, attributeKey }
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
        :hide-attribute-kind="hideAttributeKind"
        removable
        :query-suggestions="querySuggestions"
        @update:attribute-kind="onUpdateAttributeKind"
        @update:attribute-key="onUpdateAttributeKey"
        @remove="onRemove"
      />
    `
  })
  render(wrapper)
  return { condition, removed, keyUpdates }
}

test('the read-only chip shows the bracketed attribute kind and the key', () => {
  renderPill()
  const chip = screen.getByRole('button', { name: /Edit group key/ })
  expect(chip).toHaveTextContent('[Resource]')
  expect(chip).toHaveTextContent('service.name')
})

test('selecting a suggested key emits a single update:attributeKey (attribute-kind inference is the parent’s job)', async () => {
  const { condition, keyUpdates } = renderPill({ attributeKey: '' }, true)
  // The attribute-kind dropdown stays hidden until a key has been chosen.
  expect(screen.queryByRole('combobox', { name: 'Attribute kind' })).toBeNull()

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

  expect(condition.value.attributeKey).toBe('http.route')
  expect(keyUpdates).toEqual(['http.route'])
  expect(screen.getByRole('combobox', { name: 'Attribute kind' })).toBeVisible()
})

test('picking a key whose kind is unresolved reveals and auto-opens the attribute-kind dropdown', async () => {
  // Parent leaves the kind null (custom / ambiguous key the suggestions can't resolve).
  const { condition } = renderPill({ attributeKind: null, attributeKey: '' }, true)
  expect(screen.queryByRole('combobox', { name: 'Attribute kind' })).toBeNull()

  await new Promise((resolve) => setTimeout(resolve, 0))
  const keyCombobox = screen.getByRole('combobox', { name: 'Attribute key' })
  if (keyCombobox.getAttribute('aria-expanded') !== 'true') {
    await userEvent.click(keyCombobox)
  }
  const filter = screen.getByRole('textbox', { name: 'filter' })
  await userEvent.clear(filter)
  await userEvent.type(filter, 'http.route')
  await userEvent.click(await screen.findByRole('option', { name: 'http.route' }))

  expect(condition.value.attributeKind).toBeNull()
  const kindCombobox = await screen.findByRole('combobox', { name: 'Attribute kind' })
  expect(kindCombobox).toBeVisible()
  expect(kindCombobox).toHaveAttribute('aria-expanded', 'true')
})

test('hide-attribute-kind drops the kind dropdown even when a key is set', () => {
  renderPill({ attributeKey: 'service.name' }, true, true)
  expect(screen.queryByRole('combobox', { name: 'Attribute kind' })).toBeNull()
  expect(screen.getByRole('combobox', { name: 'Attribute key' })).toBeVisible()
})

test('the remove button emits remove', async () => {
  const { removed } = renderPill()
  await userEvent.click(screen.getByRole('button', { name: 'Remove group key' }))
  expect(removed.value).toBe(true)
})
