/**
 * Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */
import { userEvent } from '@testing-library/user-event'
import { render, screen, waitFor, within } from '@testing-library/vue'
import { defineComponent, ref } from 'vue'

import { Response } from '@/components/CmkSuggestions/suggestions'

import FormAttributeFilter from '@/metric-backend/attribute-filter/FormAttributeFilter.vue'
import { pillLabel } from '@/metric-backend/attribute-filter/pill-label'
import type { AttributeFilterModel, AttributeType } from '@/metric-backend/attribute-filter/types'

const KEY_SUGGESTIONS = [
  { name: 'http.method', title: 'http.method' },
  { name: 'service.name', title: 'service.name' },
  { name: 'foo.bar', title: 'foo.bar' }
]

function makeModel(): AttributeFilterModel {
  return [
    {
      id: 'pill-a',
      attributeType: null,
      key: '',
      operator: 'eq',
      value: '',
      connector: null
    },
    {
      id: 'pill-b',
      attributeType: 'scope',
      key: 'otel.library.name',
      operator: 'eq',
      value: '',
      connector: 'OR'
    }
  ]
}

function singlePill(overrides: Partial<AttributeFilterModel[number]> = {}): AttributeFilterModel {
  return [
    {
      id: 'pill-a',
      attributeType: 'resource',
      key: 'service.name',
      operator: 'eq',
      value: '',
      connector: null,
      ...overrides
    }
  ]
}

function querySuggestions(query: string): Promise<Response> {
  const lower = query.toLowerCase()
  return Promise.resolve(
    new Response(KEY_SUGGESTIONS.filter((s) => s.name.toLowerCase().includes(lower)))
  )
}

function echoQueryValueSuggestions(_: unknown, query: string): Promise<Response> {
  return Promise.resolve(new Response(query ? [{ name: query, title: query }] : []))
}

function renderForm(
  initial: AttributeFilterModel,
  resolve?: (key: string) => AttributeType
): { model: ReturnType<typeof ref<AttributeFilterModel>> } {
  const model = ref<AttributeFilterModel>(initial)
  const wrapperComponent = defineComponent({
    components: { FormAttributeFilter },
    setup() {
      return {
        model,
        querySuggestions,
        queryValueSuggestions: echoQueryValueSuggestions,
        resolveAttributeType: resolve
      }
    },
    template: `
      <FormAttributeFilter
        v-model="model"
        :query-suggestions="querySuggestions"
        :query-value-suggestions="queryValueSuggestions"
        :resolve-attribute-type="resolveAttributeType"
      />
    `
  })
  render(wrapperComponent)
  return { model }
}

function pillsInOrder(): HTMLElement[] {
  const outerGroup = screen.getByRole('group', { name: 'Attribute filter' })
  return within(outerGroup).getAllByRole('group')
}

async function enterEditMode(pill: HTMLElement): Promise<void> {
  const editButton = within(pill).queryByRole('button', { name: /^Edit condition:/ })
  if (editButton) {
    await userEvent.click(editButton)
  }
}

async function pickKey(pill: HTMLElement, name: string): Promise<void> {
  await enterEditMode(pill)
  const keyCombobox = within(pill).getByRole('combobox', { name: 'Attribute key' })
  await userEvent.click(keyCombobox)
  const filter = screen.getByRole('textbox', { name: 'filter' })
  // In callback-filtered mode the filter is pre-populated with the current
  // selection's title; clear it so the typed query starts from scratch.
  await userEvent.clear(filter)
  await userEvent.type(filter, name)
  await userEvent.click(await screen.findByRole('option', { name }))
}

async function pickOperator(pill: HTMLElement, phrase: string): Promise<void> {
  await enterEditMode(pill)
  const operatorCombobox = within(pill).getByRole('combobox', { name: 'Attribute operator' })
  await userEvent.click(operatorCombobox)
  await userEvent.click(await screen.findByRole('option', { name: phrase }))
}

async function pickAttributeType(pill: HTMLElement, label: string): Promise<void> {
  await enterEditMode(pill)
  const typeCombobox = within(pill).getByRole('combobox', { name: 'Attribute type' })
  await userEvent.click(typeCombobox)
  await userEvent.click(await screen.findByRole('option', { name: label }))
}

test('picking a known key applies key and inferred attributeType in one mutation', async () => {
  const { model } = renderForm(makeModel(), (key) => (key === 'http.method' ? 'datapoint' : null))
  // The pill emits only `update:key`; the parent owns the resolver and merges
  // the inferred attributeType into the same model mutation. A regression that
  // re-splits this into two sequential emits would let the second write
  // overwrite the first via `defineModel`'s deferred prop propagation.
  await pickKey(pillsInOrder()[0]!, 'http.method')

  expect(model.value![0]).toMatchObject({
    id: 'pill-a',
    key: 'http.method',
    attributeType: 'datapoint'
  })
  // Pill B must be untouched — guards against any cross-row contamination
  // that a sloppier identity strategy could introduce.
  expect(model.value![1]).toMatchObject({
    id: 'pill-b',
    key: 'otel.library.name',
    attributeType: 'scope'
  })
})

test('picking a key without a resolver hit preserves the existing attributeType', async () => {
  // Seed pill-a with a non-null attributeType so the assertion exercises the
  // "no inference → leave the type alone" path. A free-text key edit on a
  // resolver-less form must not silently wipe a user-picked type.
  const initial = makeModel()
  initial[0]!.attributeType = 'resource'
  initial[0]!.key = 'service.name'
  const { model } = renderForm(initial)
  await pickKey(pillsInOrder()[0]!, 'foo.bar')

  expect(model.value![0]).toMatchObject({ key: 'foo.bar', attributeType: 'resource' })
})

test('manual attributeType change persists on the targeted row', async () => {
  const { model } = renderForm(makeModel())
  await pickAttributeType(pillsInOrder()[1]!, 'Data point')

  expect(model.value![1]!.attributeType).toBe('datapoint')
  expect(model.value![0]!.attributeType).toBe(null)
})

test('manual operator change persists on the targeted row', async () => {
  const { model } = renderForm(makeModel())
  await pickOperator(pillsInOrder()[1]!, 'is not')

  expect(model.value![1]!.operator).toBe('neq')
  expect(model.value![0]!.operator).toBe('eq')
})

test('picking a key with no resolver hit auto-opens the type dropdown', async () => {
  renderForm(makeModel(), () => null)
  const pillA = pillsInOrder()[0]!
  await pickKey(pillA, 'foo.bar')

  const typeCombobox = within(pillA).getByRole('combobox', { name: 'Attribute type' })
  await waitFor(() => {
    expect(typeCombobox.getAttribute('aria-expanded')).toBe('true')
  })
})

test('picking a key with a resolver hit does not auto-open the type dropdown', async () => {
  renderForm(makeModel(), (key) => (key === 'http.method' ? 'datapoint' : null))
  const pillA = pillsInOrder()[0]!
  await pickKey(pillA, 'http.method')

  const typeCombobox = within(pillA).getByRole('combobox', { name: 'Attribute type' })
  // Give the watcher's nextTick a chance to run; aria-expanded must stay 'false'.
  await new Promise((resolve) => setTimeout(resolve, 0))
  expect(typeCombobox.getAttribute('aria-expanded')).toBe('false')
})

test('removing the head drops it by id, promotes the next row and nulls its connector', async () => {
  const { model } = renderForm(makeModel())
  const pillA = pillsInOrder()[0]!
  const pillALabel = pillLabel(makeModel()[0]!)
  await userEvent.click(within(pillA).getByRole('button', { name: 'Remove condition' }))

  expect(model.value).toHaveLength(1)
  expect(model.value![0]!.id).toBe('pill-b')
  expect(model.value![0]!.connector).toBe(null)
  // The removed pill must be gone from the DOM, not just from the model.
  expect(screen.queryByRole('group', { name: pillALabel })).toBeNull()
})

test('empty-state add button creates a single row with documented defaults', async () => {
  const { model } = renderForm([])
  await userEvent.click(screen.getByRole('button', { name: 'Add condition' }))

  expect(model.value).toHaveLength(1)
  expect(model.value![0]).toMatchObject({
    attributeType: null,
    key: '',
    operator: 'eq',
    value: '',
    connector: null
  })
  expect(model.value![0]!.id).toEqual(expect.any(String))
  expect(model.value![0]!.id.length).toBeGreaterThan(0)
})

test('per-pill add button inserts a fresh row at index + 1, leaving siblings intact', async () => {
  const { model } = renderForm(makeModel())
  await userEvent.click(
    screen.getByRole('button', { name: 'Add condition after previous condition' })
  )

  expect(model.value).toHaveLength(3)
  expect(model.value![0]!.id).toBe('pill-a')
  expect(model.value![2]!.id).toBe('pill-b')
  expect(model.value![1]).toMatchObject({
    attributeType: null,
    key: '',
    operator: 'eq',
    value: '',
    connector: 'OR'
  })
  expect(model.value![1]!.id).toEqual(expect.any(String))
  expect(model.value![1]!.id).not.toBe('pill-a')
  expect(model.value![1]!.id).not.toBe('pill-b')
})

test('value is preserved when switching between two comparison operators', async () => {
  const { model } = renderForm(singlePill({ operator: 'eq', value: 'foo' }))

  await pickOperator(pillsInOrder()[0]!, 'starts with')

  expect(model.value![0]).toMatchObject({ operator: 'starts_with', value: 'foo' })
  expect(screen.getByRole('combobox', { name: 'Attribute value' })).toHaveTextContent('foo')
})

test('value is cleared when switching to an existence operator and stays empty on return', async () => {
  const { model } = renderForm(singlePill({ operator: 'eq', value: 'foo' }))

  await pickOperator(pillsInOrder()[0]!, 'exists')

  expect(model.value![0]).toMatchObject({ operator: 'exists', value: '' })
  expect(screen.queryByRole('combobox', { name: 'Attribute value' })).toBeNull()

  await pickOperator(pillsInOrder()[0]!, 'is')

  expect(model.value![0]).toMatchObject({ operator: 'eq', value: '' })
})

test('switching from an existence operator to a value-taking operator auto-opens the value dropdown', async () => {
  renderForm(singlePill({ operator: 'exists', value: '' }))

  await pickOperator(pillsInOrder()[0]!, 'is')

  expect(screen.getByRole('combobox', { name: 'Attribute value' })).toHaveAttribute(
    'aria-expanded',
    'true'
  )
})

test('same-family swap with a populated value does not auto-open the value dropdown', async () => {
  renderForm(singlePill({ operator: 'eq', value: 'foo' }))

  await pickOperator(pillsInOrder()[0]!, 'starts with')

  expect(screen.getByRole('combobox', { name: 'Attribute value' })).toHaveAttribute(
    'aria-expanded',
    'false'
  )
})

test('same-family swap with an empty value auto-opens the value dropdown', async () => {
  renderForm(singlePill({ operator: 'eq', value: '' }))

  await pickOperator(pillsInOrder()[0]!, 'starts with')

  expect(screen.getByRole('combobox', { name: 'Attribute value' })).toHaveAttribute(
    'aria-expanded',
    'true'
  )
})

const ERROR_CLASS = 'cmk-dropdown__validation-error'

const FIELD_LABELS = ['Attribute type', 'Attribute key', 'Attribute operator', 'Attribute value']

function field(pill: HTMLElement, label: string): HTMLElement {
  return within(pill).getByRole('combobox', { name: label })
}

describe('pill required-field validation', () => {
  test('an unedited pill shows no validation errors', async () => {
    renderForm(makeModel())
    const pill = pillsInOrder()[0]!
    await enterEditMode(pill)
    for (const label of FIELD_LABELS) {
      expect(field(pill, label)).not.toHaveClass(ERROR_CLASS)
    }
  })

  test('the disabled type dropdown drops its required hint', async () => {
    renderForm(makeModel())
    const pill = pillsInOrder()[0]!
    await enterEditMode(pill)
    expect(field(pill, 'Attribute type')).not.toHaveTextContent('(required)')
  })

  test('a partly-filled but uncommitted pill flags nothing', async () => {
    renderForm(makeModel())
    const pill = pillsInOrder()[1]!
    await enterEditMode(pill)
    for (const label of FIELD_LABELS) {
      expect(field(pill, label)).not.toHaveClass(ERROR_CLASS)
      expect(field(pill, label)).not.toHaveTextContent('(required)')
    }
  })

  test('picking a key does not reveal validation on the still-empty type', async () => {
    const { model } = renderForm(makeModel(), () => null)
    await pickKey(pillsInOrder()[0]!, 'http.method')

    expect(model.value![0]!.key).toBe('http.method')
    const pill = pillsInOrder()[0]!
    for (const label of ['Attribute type', 'Attribute key']) {
      expect(field(pill, label)).not.toHaveClass(ERROR_CLASS)
      expect(field(pill, label)).not.toHaveTextContent('(required)')
    }
  })
})

test('preloaded pills start in read-only mode', () => {
  renderForm(makeModel())
  expect(screen.getAllByRole('button', { name: /^Edit condition:/ })).toHaveLength(2)
  expect(screen.queryByRole('combobox', { name: 'Attribute operator' })).toBeNull()
})

test('clicking a read-only pill opens it for editing', async () => {
  renderForm(makeModel())
  const pillB = pillsInOrder()[1]!
  await enterEditMode(pillB)

  expect(within(pillB).getByRole('combobox', { name: 'Attribute operator' })).toBeInTheDocument()
  const pillA = pillsInOrder()[0]!
  expect(within(pillA).queryByRole('button', { name: /^Edit condition:/ })).not.toBeNull()
})

test('opening a second pill closes the previously open one', async () => {
  renderForm([
    {
      id: 'pill-a',
      attributeType: 'resource',
      key: 'service.name',
      operator: 'eq',
      value: 'foo',
      connector: null
    },
    {
      id: 'pill-b',
      attributeType: 'scope',
      key: 'otel.library.name',
      operator: 'eq',
      value: 'bar',
      connector: 'OR'
    }
  ])
  await enterEditMode(pillsInOrder()[0]!)
  expect(
    within(pillsInOrder()[0]!).getByRole('combobox', { name: 'Attribute operator' })
  ).toBeInTheDocument()

  await enterEditMode(pillsInOrder()[1]!)
  expect(
    within(pillsInOrder()[1]!).getByRole('combobox', { name: 'Attribute operator' })
  ).toBeInTheDocument()
  expect(
    within(pillsInOrder()[0]!).queryByRole('combobox', { name: 'Attribute operator' })
  ).toBeNull()
})

test('removing the editing pill clears the editing state', async () => {
  const { model } = renderForm(makeModel())
  const pillA = pillsInOrder()[0]!
  await enterEditMode(pillA)
  await userEvent.click(within(pillA).getByRole('button', { name: 'Remove condition' }))

  expect(model.value).toHaveLength(1)
  const remaining = pillsInOrder()
  expect(remaining).toHaveLength(1)
  expect(within(remaining[0]!).queryByRole('button', { name: /^Edit condition:/ })).not.toBeNull()
  expect(within(remaining[0]!).queryByRole('combobox', { name: 'Attribute operator' })).toBeNull()
})

function dispatchOutsideClick(): void {
  document.body.dispatchEvent(new MouseEvent('click', { bubbles: true }))
}

test('click outside closes a fully-valid edit pill back to read-only', async () => {
  renderForm([
    {
      id: 'pill-a',
      attributeType: 'scope',
      key: 'otel.library.name',
      operator: 'eq',
      value: 'foo',
      connector: null
    }
  ])
  const pillA = pillsInOrder()[0]!
  await enterEditMode(pillA)
  expect(within(pillA).getByRole('combobox', { name: 'Attribute operator' })).toBeInTheDocument()

  dispatchOutsideClick()
  await waitFor(() => {
    expect(within(pillA).queryByRole('combobox', { name: 'Attribute operator' })).toBeNull()
  })
})

test('click outside on a partly-filled invalid pill keeps it open and reveals errors', async () => {
  renderForm(singlePill({ key: 'service.name', value: '' }))
  const pillA = pillsInOrder()[0]!
  await enterEditMode(pillA)
  // Before the commit attempt, no field is flagged.
  expect(field(pillA, 'Attribute value')).not.toHaveClass(ERROR_CLASS)

  dispatchOutsideClick()
  expect(within(pillA).getByRole('combobox', { name: 'Attribute operator' })).toBeInTheDocument()
  await waitFor(() => {
    expect(field(pillA, 'Attribute value')).toHaveClass(ERROR_CLASS)
  })
})

test('click outside on a pristine invalid pill keeps it open and reveals errors', async () => {
  renderForm(makeModel())
  const pillA = pillsInOrder()[0]!
  await enterEditMode(pillA)

  dispatchOutsideClick()
  expect(within(pillA).getByRole('combobox', { name: 'Attribute operator' })).toBeInTheDocument()
  await waitFor(() => {
    expect(field(pillA, 'Attribute key')).toHaveClass(ERROR_CLASS)
  })
  expect(field(pillA, 'Attribute value')).toHaveClass(ERROR_CLASS)
})

test("clicking another pill's chip while the editing pill is invalid is a no-op and reveals errors", async () => {
  renderForm(makeModel())
  const pillA = pillsInOrder()[0]!
  const pillB = pillsInOrder()[1]!
  await enterEditMode(pillA)

  const pillBEditButton = within(pillB).getByRole('button', { name: /^Edit condition:/ })
  await userEvent.click(pillBEditButton)

  expect(within(pillA).getByRole('combobox', { name: 'Attribute operator' })).toBeInTheDocument()
  expect(field(pillA, 'Attribute key')).toHaveClass(ERROR_CLASS)
  expect(field(pillA, 'Attribute value')).toHaveClass(ERROR_CLASS)
  expect(within(pillB).queryByRole('combobox', { name: 'Attribute operator' })).toBeNull()
  expect(within(pillB).queryByRole('button', { name: /^Edit condition:/ })).not.toBeNull()
})

test("newly added pill via '+' starts in edit mode", async () => {
  const { model } = renderForm(makeModel())
  await userEvent.click(
    screen.getByRole('button', { name: 'Add condition after previous condition' })
  )

  expect(model.value).toHaveLength(3)
  const pills = pillsInOrder()
  expect(pills).toHaveLength(3)
  expect(within(pills[0]!).queryByRole('button', { name: /^Edit condition:/ })).not.toBeNull()
  expect(
    within(pills[1]!).getByRole('combobox', { name: 'Attribute operator' })
  ).toBeInTheDocument()
  expect(within(pills[2]!).queryByRole('button', { name: /^Edit condition:/ })).not.toBeNull()
})

test("a freshly added pill via '+' does not display validation errors", async () => {
  renderForm(makeModel())
  await userEvent.click(
    screen.getByRole('button', { name: 'Add condition after previous condition' })
  )

  const freshPill = pillsInOrder()[1]!
  for (const label of ['Attribute key', 'Attribute operator', 'Attribute value']) {
    expect(field(freshPill, label)).not.toHaveClass(ERROR_CLASS)
    expect(field(freshPill, label)).not.toHaveTextContent('(required)')
  }
})

test('opening a sibling dropdown closes the previously-open one within the same pill', async () => {
  renderForm(singlePill({ key: 'service.name', value: 'foo' }))
  const pill = pillsInOrder()[0]!
  await enterEditMode(pill)

  const keyCombobox = within(pill).getByRole('combobox', { name: 'Attribute key' })
  const operatorCombobox = within(pill).getByRole('combobox', { name: 'Attribute operator' })

  await userEvent.click(keyCombobox)
  expect(keyCombobox).toHaveAttribute('aria-expanded', 'true')

  await userEvent.click(operatorCombobox)
  await waitFor(() => {
    expect(keyCombobox).toHaveAttribute('aria-expanded', 'false')
  })
  expect(operatorCombobox).toHaveAttribute('aria-expanded', 'true')
})

test('connector renders between adjacent pills', () => {
  renderForm([
    {
      id: 'pill-a',
      attributeType: 'resource',
      key: 'service.name',
      operator: 'eq',
      value: 'web-01',
      connector: null
    },
    {
      id: 'pill-b',
      attributeType: 'scope',
      key: 'otel.library.name',
      operator: 'contains',
      value: 'api',
      connector: 'OR'
    }
  ])
  const connectors = screen.getAllByLabelText('Connector')
  expect(connectors).toHaveLength(1)
  expect(connectors[0]).toHaveTextContent('OR')
})
