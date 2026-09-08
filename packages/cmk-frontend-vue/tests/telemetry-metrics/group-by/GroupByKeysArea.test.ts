/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { render, screen, waitFor } from '@testing-library/vue'
import { Response } from 'cmk-ui-library/components/CmkSuggestions/suggestions'
import { untranslated } from 'cmk-ui-library/lib/i18n'
import { defineComponent, ref } from 'vue'

import type { KeySection } from '@/telemetry-metrics/attribute-kind'
import GroupByKeysArea from '@/telemetry-metrics/group-by/GroupByKeysArea.vue'
import type { AttributeKind, GroupKey } from '@/telemetry-metrics/group-by/types'

const KEY_KINDS: Record<string, AttributeKind> = {
  'service.name': 'resource',
  'http.route': 'data_point'
}

function querySuggestions(query: string): Promise<Response> {
  const sections: KeySection[] = Object.entries(KEY_KINDS)
    .filter(([key]) => key.includes(query))
    .map(([key, kind]) => ({
      title: untranslated(kind),
      suggestions: [{ name: key, title: untranslated(key) }],
      kind
    }))
  return Promise.resolve(new Response(sections))
}

function renderArea(initial: GroupKey[] = [], query = querySuggestions) {
  const keys = ref<GroupKey[]>(initial)
  render(
    defineComponent({
      components: { GroupByKeysArea },
      setup: () => ({ keys, querySuggestions: query }),
      template: `<GroupByKeysArea v-model="keys" :query-suggestions="querySuggestions" />`
    })
  )
  return { keys }
}

async function selectKey(value: string): Promise<void> {
  // Let the empty-key auto-open settle so the click cannot re-toggle it.
  await new Promise((resolve) => setTimeout(resolve, 0))
  const keyCombobox = screen.getByRole('combobox', { name: 'Attribute key' })
  if (keyCombobox.getAttribute('aria-expanded') !== 'true') {
    await userEvent.click(keyCombobox)
  }
  const filter = screen.getByRole('textbox', { name: 'filter' })
  await userEvent.clear(filter)
  await userEvent.type(filter, value)
  await userEvent.click(await screen.findByRole('option', { name: value }))
}

test('adding a key replaces the "combine all series" placeholder and takes the picked key\'s kind', async () => {
  const { keys } = renderArea()
  expect(screen.getByText('nothing, combine all series into one')).toBeVisible()

  await userEvent.click(screen.getByRole('button', { name: 'Add group key' }))
  await waitFor(() => expect(keys.value).toHaveLength(1))
  expect(screen.queryByText('nothing, combine all series into one')).toBeNull()

  await selectKey('http.route')

  await waitFor(() => expect(keys.value[0]!.attributeKey).toBe('http.route'))
  expect(keys.value[0]!.attributeKind).toBe('data_point')
})

test('picking a key offered under several kinds takes the kind of the picked section', async () => {
  const sections: KeySection[] = (['resource', 'data_point'] as const).map((kind) => ({
    title: untranslated(kind),
    suggestions: [{ name: 'service', title: untranslated('service') }],
    kind
  }))
  const { keys } = renderArea([], () => Promise.resolve(new Response(sections)))
  await userEvent.click(screen.getByRole('button', { name: 'Add group key' }))
  const options = await screen.findAllByRole('option', { name: 'service' })
  await userEvent.click(options[1]!)

  await waitFor(() =>
    expect(keys.value[0]).toMatchObject({ attributeKey: 'service', attributeKind: 'data_point' })
  )
})

test('a committed key can be removed', async () => {
  const { keys } = renderArea([
    { id: '1', attributeKind: 'resource', attributeKey: 'service.name' }
  ])
  await userEvent.click(await screen.findByRole('button', { name: 'Remove group key' }))
  await waitFor(() => expect(keys.value).toHaveLength(0))
})
