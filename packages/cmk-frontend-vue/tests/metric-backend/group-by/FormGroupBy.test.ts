/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { render, screen, waitFor, within } from '@testing-library/vue'
import { Response } from 'cmk-ui-library/components/CmkSuggestions/suggestions'
import { defineComponent, ref } from 'vue'

import FormGroupBy from '@/metric-backend/group-by/FormGroupBy.vue'
import type { AttributeKind, GroupByInputType, GroupByModel } from '@/metric-backend/group-by/types'

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

function resolveAttributeKind(key: string): AttributeKind | null {
  return KEY_ATTRIBUTE_KINDS[key] ?? null
}

function renderWidget(initial: Partial<GroupByModel> = {}, inputType: GroupByInputType = 'float') {
  const model = ref<GroupByModel>({ function: 'none', params: {}, keys: [], ...initial })
  const type = ref<GroupByInputType>(inputType)
  const wrapper = defineComponent({
    components: { FormGroupBy },
    setup() {
      return { model, type, querySuggestions, resolveAttributeKind }
    },
    template: `
      <div>
        <button type="button">outside</button>
        <FormGroupBy
          v-model="model"
          :input-type="type"
          :query-suggestions="querySuggestions"
          :resolve-attribute-kind="resolveAttributeKind"
        />
      </div>
    `
  })
  render(wrapper)
  return { model, type }
}

async function openPill(): Promise<void> {
  await userEvent.click(screen.getByRole('button', { name: /Edit group by/ }))
}

async function openFunctionDropdown(): Promise<void> {
  await openPill()
  await userEvent.click(screen.getByRole('combobox', { name: 'Grouping function' }))
}

test('the collapsed chip summarises the clause with the attribute kind shown dimmed', () => {
  renderWidget({
    function: 'avg',
    keys: [
      { id: '1', attributeKind: 'resource', attributeKey: 'service.name' },
      { id: '2', attributeKind: 'data_point', attributeKey: 'http.route' }
    ]
  })
  const chip = screen.getByRole('button', { name: /Edit group by/ })
  expect(chip).toHaveTextContent('avg by')
  const attributeKind = within(chip).getByText('[Resource]')
  expect(attributeKind).toHaveClass('metric-backend-form-group-by__segment--dimmed')
  expect(within(chip).getByText('service.name,')).toBeVisible()
  expect(within(chip).getByText('http.route')).toBeVisible()
})

test.each([
  { fn: 'none' as const, expanded: 'true' },
  { fn: 'avg' as const, expanded: 'false' }
])(
  'entering edit opens the function dropdown only when "no grouping" leaves nothing else to edit',
  async ({ fn, expanded }) => {
    renderWidget({ function: fn, keys: [] }, 'float')
    await openPill()
    await waitFor(() =>
      expect(screen.getByRole('combobox', { name: 'Grouping function' })).toHaveAttribute(
        'aria-expanded',
        expanded
      )
    )
  }
)

test.each([
  {
    inputType: 'float' as const,
    initial: { function: 'avg' as const },
    present: ['no grouping', 'avg by', 'count by'],
    absent: ['percentile by']
  },
  {
    inputType: 'histogram' as const,
    initial: { function: 'percentile' as const, params: { quantile: 0.95 } },
    present: ['percentile by', 'fraction below by'],
    absent: ['no grouping']
  }
])(
  'the $inputType input offers its own functions and hides the others',
  async ({ inputType, initial, present, absent }) => {
    renderWidget({ ...initial, keys: [] }, inputType)
    await openFunctionDropdown()

    for (const name of present) {
      expect(await screen.findByRole('option', { name })).toBeVisible()
    }
    for (const name of absent) {
      expect(screen.queryByRole('option', { name })).toBeNull()
    }
  }
)

test('picking a function leaves the group-by pill in edit mode', async () => {
  const { model } = renderWidget({ function: 'avg', keys: [] }, 'float')
  await openFunctionDropdown()

  await userEvent.click(await screen.findByRole('option', { name: 'count by' }))

  await waitFor(() => expect(model.value.function).toBe('count'))
  expect(screen.queryByRole('button', { name: /Edit group by/ })).toBeNull()
  expect(screen.getByRole('combobox', { name: 'Grouping function' })).toBeVisible()
})

test('switching the input type resets a now-invalid function to the new default', async () => {
  const { model, type } = renderWidget({ function: 'avg' }, 'float')

  type.value = 'histogram'
  await waitFor(() => expect(model.value.function).toBe('percentile'))
  expect(model.value.params.quantile).toBeDefined()
})

test('the percentile function shows a quantile input, other float functions show none', async () => {
  const { type } = renderWidget({ function: 'percentile', params: { quantile: 0.95 } }, 'histogram')
  await openPill()
  expect(screen.getByLabelText('Quantile (0 to 1)')).toBeVisible()

  type.value = 'float'
  await waitFor(() => expect(screen.queryByLabelText('Quantile (0 to 1)')).toBeNull())
})

test.each([
  {
    scenario: 'an out-of-order fraction pair',
    initial: {
      function: 'fraction_between' as const,
      params: { fractionLowerThreshold: 0.9, fractionUpperThreshold: 0.1 }
    },
    error: 'Lower threshold must be below the upper threshold'
  },
  {
    scenario: 'a missing fraction-below threshold',
    initial: { function: 'fraction_below' as const, params: {} },
    error: 'Enter a threshold'
  }
])('leaving with $scenario is vetoed and reveals the error', async ({ initial, error }) => {
  renderWidget({ ...initial, keys: [] }, 'histogram')
  await openPill()

  await userEvent.click(screen.getByRole('button', { name: 'outside' }))
  expect(screen.getByRole('combobox', { name: 'Grouping function' })).toBeVisible()
  expect(screen.getByText(error)).toBeVisible()
})

test('the "combine all series" placeholder shows for an active function with no keys and hides once a key is added', async () => {
  const { model } = renderWidget({ function: 'avg', keys: [] }, 'float')
  await openPill()
  expect(screen.getByText('nothing, combine all series into one')).toBeVisible()

  await userEvent.click(screen.getByRole('button', { name: 'Add group key' }))
  await waitFor(() => expect(model.value.keys).toHaveLength(1))
  expect(screen.queryByText('nothing, combine all series into one')).toBeNull()
})

test('"no grouping" removes the keys area but retains the keys in the model', async () => {
  const { model } = renderWidget(
    {
      function: 'none',
      keys: [{ id: '1', attributeKind: 'resource', attributeKey: 'service.name' }]
    },
    'float'
  )
  await openPill()
  expect(screen.queryByTestId('group-by-keys')).toBeNull()
  expect(screen.queryByRole('button', { name: /Edit group key/ })).toBeNull()
  expect(model.value.keys).toEqual([
    { id: '1', attributeKind: 'resource', attributeKey: 'service.name' }
  ])
})

test('the remove button on the collapsed pill resets the grouping to "no grouping"', async () => {
  const { model } = renderWidget({ function: 'avg', keys: [] }, 'float')

  await userEvent.click(screen.getByRole('button', { name: 'Remove grouping' }))

  await waitFor(() => expect(model.value.function).toBe('none'))
})

test('the remove button is hidden once the grouping is already "no grouping"', () => {
  renderWidget({ function: 'none', keys: [] }, 'float')
  expect(screen.queryByRole('button', { name: 'Remove grouping' })).toBeNull()
})

test('the remove button is hidden while the pill is being edited', async () => {
  renderWidget({ function: 'avg', keys: [] }, 'float')
  await openPill()

  expect(screen.queryByRole('button', { name: 'Remove grouping' })).toBeNull()
})

async function selectKey(value: string): Promise<void> {
  // Let the empty-key auto-open (nextTick) settle so the click cannot re-toggle it.
  await new Promise((resolve) => setTimeout(resolve, 0))
  const combos = screen.getAllByRole('combobox', { name: 'Attribute key' })
  const keyCombobox = combos[combos.length - 1]!
  if (keyCombobox.getAttribute('aria-expanded') !== 'true') {
    await userEvent.click(keyCombobox)
  }
  const filters = screen.getAllByRole('textbox', { name: 'filter' })
  const filter = filters[filters.length - 1]!
  await userEvent.clear(filter)
  await userEvent.type(filter, value)
  await userEvent.click(await screen.findByRole('option', { name: value }))
}

test('picking a key applies key and inferred attribute kind in one mutation (also for a second key)', async () => {
  // Two emits (key then attribute kind) would race and drop the key; a second key regressed this (CMK-36579).
  const { model } = renderWidget(
    {
      function: 'avg',
      keys: [{ id: 'k1', attributeKind: 'resource', attributeKey: 'service.name' }]
    },
    'float'
  )
  await openPill()

  await userEvent.click(screen.getByRole('button', { name: 'Add group key' }))
  await waitFor(() => expect(model.value.keys).toHaveLength(2))
  await selectKey('http.route')

  await waitFor(() => expect(model.value.keys[1]!.attributeKey).toBe('http.route'))
  expect(model.value.keys[1]!.attributeKind).toBe('data_point')
})

test('picking a key leaves the group-key pill in edit mode', async () => {
  const { model } = renderWidget({ function: 'avg', keys: [] }, 'float')
  await openPill()

  await userEvent.click(screen.getByRole('button', { name: 'Add group key' }))
  await waitFor(() => expect(model.value.keys).toHaveLength(1))
  await selectKey('service.name')

  await waitFor(() => expect(model.value.keys[0]!.attributeKey).toBe('service.name'))
  expect(screen.queryByRole('button', { name: /Edit group key/ })).toBeNull()
  expect(screen.getByRole('combobox', { name: 'Attribute key' })).toBeVisible()
})

test('entering edit with a single key opens that key pill for editing', async () => {
  renderWidget(
    {
      function: 'avg',
      keys: [{ id: 'k1', attributeKind: 'resource', attributeKey: 'service.name' }]
    },
    'float'
  )
  await openPill()
  await waitFor(() => expect(screen.getByRole('combobox', { name: 'Attribute key' })).toBeVisible())
})

test('entering edit with several keys leaves the key pills collapsed', async () => {
  renderWidget(
    {
      function: 'avg',
      keys: [
        { id: 'k1', attributeKind: 'resource', attributeKey: 'service.name' },
        { id: 'k2', attributeKind: 'data_point', attributeKey: 'http.route' }
      ]
    },
    'float'
  )
  await openPill()
  await new Promise((resolve) => setTimeout(resolve, 0))
  expect(screen.queryByRole('combobox', { name: 'Attribute key' })).toBeNull()
})

test('a committed key can be removed', async () => {
  const { model } = renderWidget(
    {
      function: 'avg',
      keys: [{ id: '1', attributeKind: 'resource', attributeKey: 'service.name' }]
    },
    'float'
  )
  await openPill()
  await userEvent.click(await screen.findByRole('button', { name: 'Remove group key' }))
  await waitFor(() => expect(model.value.keys).toHaveLength(0))
})

test('the collapsed chip is a tab stop wrapping the chip and the remove X, opening on Enter', async () => {
  renderWidget({ function: 'avg', keys: [] })

  await userEvent.tab()
  expect(document.activeElement).toBe(screen.getByRole('button', { name: 'outside' }))

  await userEvent.tab()
  const stop = within(document.activeElement as HTMLElement)
  expect(stop.getByRole('button', { name: /Edit group by/ })).toBeInTheDocument()
  expect(stop.getByRole('button', { name: 'Remove grouping' })).toBeInTheDocument()

  await userEvent.keyboard('{Enter}')
  expect(screen.getByRole('combobox', { name: 'Grouping function' })).toBeVisible()
})
