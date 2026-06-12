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

function pill(
  id: string,
  connector: 'AND' | 'OR' | null,
  overrides: Partial<AttributeFilterModel[number]> = {}
): AttributeFilterModel[number] {
  return { id, attributeType: null, key: '', operator: 'eq', value: '', connector, ...overrides }
}

function makeModel(): AttributeFilterModel {
  return [
    pill('pill-a', null),
    pill('pill-b', 'OR', { attributeType: 'scope', key: 'otel.library.name' })
  ]
}

function singlePill(overrides: Partial<AttributeFilterModel[number]> = {}): AttributeFilterModel {
  return [pill('pill-a', null, { attributeType: 'resource', key: 'service.name', ...overrides })]
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
  // Let the empty-key auto-open (deferred to nextTick) settle so the click
  // below cannot toggle a just-opened dropdown closed again.
  await new Promise((resolve) => setTimeout(resolve, 0))
  const keyCombobox = within(pill).getByRole('combobox', { name: 'Attribute key' })
  if (keyCombobox.getAttribute('aria-expanded') !== 'true') {
    await userEvent.click(keyCombobox)
  }
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
  // Let any pending auto-open settle so the click below cannot toggle a
  // just-opened dropdown closed again.
  await new Promise((resolve) => setTimeout(resolve, 0))
  const typeCombobox = within(pill).getByRole('combobox', { name: 'Attribute type' })
  if (typeCombobox.getAttribute('aria-expanded') !== 'true') {
    await userEvent.click(typeCombobox)
  }
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

test('picking a key with a resolver hit auto-opens the value dropdown', async () => {
  renderForm(makeModel(), (key) => (key === 'http.method' ? 'datapoint' : null))
  const pillA = pillsInOrder()[0]!
  await pickKey(pillA, 'http.method')

  const valueCombobox = within(pillA).getByRole('combobox', { name: 'Attribute value' })
  await waitFor(() => {
    expect(valueCombobox.getAttribute('aria-expanded')).toBe('true')
  })
})

test('picking the type after a no-hit key auto-opens the value dropdown', async () => {
  renderForm(makeModel(), () => null)
  const pillA = pillsInOrder()[0]!
  await pickKey(pillA, 'foo.bar')
  await pickAttributeType(pillA, 'Resource')

  const valueCombobox = within(pillA).getByRole('combobox', { name: 'Attribute value' })
  await waitFor(() => {
    expect(valueCombobox.getAttribute('aria-expanded')).toBe('true')
  })
})

test('a newly added pill auto-opens the key dropdown', async () => {
  renderForm([])
  await userEvent.click(screen.getByRole('button', { name: 'Add condition' }))

  const keyCombobox = within(pillsInOrder()[0]!).getByRole('combobox', { name: 'Attribute key' })
  await waitFor(() => {
    expect(keyCombobox.getAttribute('aria-expanded')).toBe('true')
  })
})

test('editing an existing pill does not auto-open the key dropdown', async () => {
  renderForm(singlePill())
  const pill = pillsInOrder()[0]!
  await enterEditMode(pill)

  const keyCombobox = within(pill).getByRole('combobox', { name: 'Attribute key' })
  // Give the watcher's nextTick a chance to run; aria-expanded must stay 'false'.
  await new Promise((resolve) => setTimeout(resolve, 0))
  expect(keyCombobox.getAttribute('aria-expanded')).toBe('false')
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
    // 'Attribute type' is excluded: it is hidden while the key is empty.
    for (const label of ['Attribute key', 'Attribute operator', 'Attribute value']) {
      expect(field(pill, label)).not.toHaveClass(ERROR_CLASS)
    }
  })

  test('the type dropdown is hidden until a key is chosen', async () => {
    renderForm(makeModel())
    const pill = pillsInOrder()[0]!
    await enterEditMode(pill)
    expect(within(pill).queryByRole('combobox', { name: 'Attribute type' })).toBeNull()
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
    pill('pill-a', null, { attributeType: 'resource', key: 'service.name', value: 'foo' }),
    pill('pill-b', 'OR', { attributeType: 'scope', key: 'otel.library.name', value: 'bar' })
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
    pill('pill-a', null, { attributeType: 'scope', key: 'otel.library.name', value: 'foo' })
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

describe('Escape in edit mode', () => {
  function focusOperator(pill: HTMLElement): void {
    within(pill).getByRole('combobox', { name: 'Attribute operator' }).focus()
  }

  test('Escape on a valid editing pill commits and focuses the chip', async () => {
    renderForm([
      pill('pill-a', null, { attributeType: 'scope', key: 'otel.library.name', value: 'foo' })
    ])
    const pillA = pillsInOrder()[0]!
    await enterEditMode(pillA)
    focusOperator(pillA)

    await userEvent.keyboard('{Escape}')

    await waitFor(() => {
      expect(within(pillA).queryByRole('combobox', { name: 'Attribute operator' })).toBeNull()
    })
    await waitFor(() =>
      expect(within(pillA).getByRole('button', { name: /^Edit condition:/ })).toHaveFocus()
    )
  })

  test('Escape on an invalid editing pill keeps it open and reveals errors', async () => {
    renderForm(singlePill({ key: 'service.name', value: '' }))
    const pillA = pillsInOrder()[0]!
    await enterEditMode(pillA)
    focusOperator(pillA)

    await userEvent.keyboard('{Escape}')

    expect(within(pillA).getByRole('combobox', { name: 'Attribute operator' })).toBeInTheDocument()
    await waitFor(() => {
      expect(field(pillA, 'Attribute value')).toHaveClass(ERROR_CLASS)
    })
  })

  test('Escape with a dropdown open only closes the dropdown', async () => {
    renderForm([
      pill('pill-a', null, { attributeType: 'scope', key: 'otel.library.name', value: 'foo' })
    ])
    const pillA = pillsInOrder()[0]!
    await enterEditMode(pillA)
    const operatorCombobox = within(pillA).getByRole('combobox', { name: 'Attribute operator' })
    await userEvent.click(operatorCombobox)
    await waitFor(() => {
      expect(operatorCombobox).toHaveAttribute('aria-expanded', 'true')
    })

    await userEvent.keyboard('{Escape}')

    await waitFor(() => {
      expect(operatorCombobox).toHaveAttribute('aria-expanded', 'false')
    })
    expect(within(pillA).getByRole('combobox', { name: 'Attribute operator' })).toBeInTheDocument()
  })
})

describe('combined pill keyboard stop', () => {
  function chipOf(pill: HTMLElement): HTMLElement {
    return within(pill).getByRole('button', { name: /^Edit condition:/ })
  }

  test.skip('closed: tabbing into the pill lands on a single stop that wraps the chip and the remove X', async () => {
    renderForm(makeModel())
    const pillA = pillsInOrder()[0]!

    for (let i = 0; i < 20 && !pillA.contains(document.activeElement); i++) {
      await userEvent.tab()
    }

    const focused = document.activeElement as HTMLElement
    expect(pillA.contains(focused)).toBe(true)
    expect(within(focused).getByRole('button', { name: /^Edit condition:/ })).toBeInTheDocument()
    expect(within(focused).getByRole('button', { name: 'Remove condition' })).toBeInTheDocument()
  })

  test.skip('edit mode: tabbing forward eventually focuses the remove X on its own', async () => {
    renderForm(makeModel())
    const pillA = pillsInOrder()[0]!
    await enterEditMode(pillA)
    const removeX = within(pillA).getByRole('button', { name: 'Remove condition' })

    for (let i = 0; i < 20 && document.activeElement !== removeX; i++) {
      await userEvent.tab()
    }

    expect(document.activeElement).toBe(removeX)
  })

  test.skip.each([
    ['Backspace', '{Backspace}'],
    ['Delete', '{Delete}']
  ])('%s on a focused chip removes the pill', async (_name, key) => {
    const { model } = renderForm(makeModel())
    chipOf(pillsInOrder()[0]!).focus()

    await userEvent.keyboard(key)

    expect(model.value).toHaveLength(1)
    expect(model.value![0]!.id).toBe('pill-b')
  })

  test.skip.each([
    ['Space', ' '],
    ['Enter', '{Enter}']
  ])('%s on a focused chip enters edit mode', async (_name, key) => {
    renderForm(makeModel())
    const pillA = pillsInOrder()[0]!
    chipOf(pillA).focus()

    await userEvent.keyboard(key)

    expect(within(pillA).getByRole('combobox', { name: 'Attribute operator' })).toBeInTheDocument()
  })

  test.skip('Tab from a chip lands on the per-pill +, skipping the remove X', async () => {
    renderForm(makeModel())
    chipOf(pillsInOrder()[0]!).focus()

    await userEvent.tab()

    expect(
      screen.getByRole('button', { name: 'Add condition after previous condition' })
    ).toHaveFocus()
  })
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

test('connector renders as a toggle button between adjacent pills', () => {
  renderForm([
    pill('pill-a', null, { attributeType: 'resource', key: 'service.name', value: 'web-01' }),
    pill('pill-b', 'OR', {
      attributeType: 'scope',
      key: 'otel.library.name',
      operator: 'contains',
      value: 'api'
    })
  ])
  const connectors = screen.getAllByRole('button', {
    name: /^Toggle connector, currently /
  })
  expect(connectors).toHaveLength(1)
  expect(connectors[0]).toHaveTextContent('OR')
  expect(connectors[0]).toHaveAccessibleName('Toggle connector, currently OR')
})

test('clicking an OR connector flips it to AND', async () => {
  const { model } = renderForm([pill('pill-a', null), pill('pill-b', 'OR')])
  await userEvent.click(screen.getByRole('button', { name: 'Toggle connector, currently OR' }))

  expect(model.value![1]!.connector).toBe('AND')
  expect(screen.getByRole('button', { name: 'Toggle connector, currently AND' })).toHaveTextContent(
    'AND'
  )
})

test('clicking the connector twice returns it to OR', async () => {
  const { model } = renderForm([pill('pill-a', null), pill('pill-b', 'OR')])
  await userEvent.click(screen.getByRole('button', { name: /^Toggle connector, currently / }))
  await userEvent.click(screen.getByRole('button', { name: /^Toggle connector, currently / }))

  expect(model.value![1]!.connector).toBe('OR')
})

test('toggling one connector does not affect its neighbour', async () => {
  const { model } = renderForm([pill('pill-a', null), pill('pill-b', 'OR'), pill('pill-c', 'OR')])
  const [first, second] = screen.getAllByRole('button', {
    name: /^Toggle connector, currently /
  })
  await userEvent.click(first!)

  expect(model.value![1]!.connector).toBe('AND')
  expect(model.value![2]!.connector).toBe('OR')
  expect(second).toHaveAccessibleName('Toggle connector, currently OR')
})

test('head pill has no connector toggle button', () => {
  renderForm([pill('pill-a', null)])
  expect(screen.queryByRole('button', { name: /^Toggle connector, currently / })).toBeNull()
})

const GROUP_TESTID = 'attribute-filter-group'

test('two AND-joined pills render inside one bordered group', () => {
  renderForm([pill('pill-a', null), pill('pill-b', 'AND')])
  const groups = screen.getAllByTestId(GROUP_TESTID)
  expect(groups).toHaveLength(1)
  expect(within(groups[0]!).getAllByRole('group')).toHaveLength(2)
  expect(
    within(groups[0]!).getByRole('button', { name: 'Toggle connector, currently AND' })
  ).toBeInTheDocument()
})

test('OR splits the pills into two bordered groups with OR outside both', () => {
  renderForm([
    pill('pill-a', null),
    pill('pill-b', 'AND'),
    pill('pill-c', 'OR'),
    pill('pill-d', 'AND')
  ])
  const groups = screen.getAllByTestId(GROUP_TESTID)
  expect(groups).toHaveLength(2)
  expect(within(groups[0]!).getAllByRole('group')).toHaveLength(2)
  expect(within(groups[1]!).getAllByRole('group')).toHaveLength(2)
  expect(
    within(groups[0]!).queryByRole('button', { name: 'Toggle connector, currently OR' })
  ).toBeNull()
  expect(
    within(groups[1]!).queryByRole('button', { name: 'Toggle connector, currently OR' })
  ).toBeNull()
  expect(screen.getByRole('button', { name: 'Toggle connector, currently OR' })).toBeInTheDocument()
})

test('toggling AND to OR splits a 3-pill group into a pair and a lone pill', async () => {
  renderForm([pill('pill-a', null), pill('pill-b', 'AND'), pill('pill-c', 'AND')])
  expect(screen.getAllByTestId(GROUP_TESTID)).toHaveLength(1)
  const ands = screen.getAllByRole('button', { name: 'Toggle connector, currently AND' })
  expect(ands).toHaveLength(2)
  await userEvent.click(ands[1]!)

  const groups = screen.getAllByTestId(GROUP_TESTID)
  expect(groups).toHaveLength(1)
  expect(within(groups[0]!).getAllByRole('group')).toHaveLength(2)
  expect(pillsInOrder()).toHaveLength(3)
})

test('every pill in an AND group has a per-pill + that inserts an AND pill at that position', async () => {
  const { model } = renderForm([
    pill('pill-a', null, { attributeType: 'resource', key: 'service.name' }),
    pill('pill-b', 'AND', { attributeType: 'scope', key: 'otel.library.name' })
  ])
  await userEvent.click(screen.getByRole('button', { name: 'Add condition after service.name' }))

  expect(model.value).toHaveLength(3)
  expect(model.value!.map((c) => c.id)).toEqual(['pill-a', expect.any(String), 'pill-b'])
  expect(model.value![1]!.connector).toBe('AND')
  const groups = screen.getAllByTestId(GROUP_TESTID)
  expect(groups).toHaveLength(1)
  expect(within(groups[0]!).getAllByRole('group')).toHaveLength(3)
})

test('the after-group + starts a new OR clause that renders as a bare pill', async () => {
  const { model } = renderForm([
    pill('pill-a', null, { attributeType: 'resource', key: 'service.name' }),
    pill('pill-b', 'AND', { attributeType: 'scope', key: 'otel.library.name' })
  ])
  await userEvent.click(screen.getByRole('button', { name: 'Add condition after this group' }))

  expect(model.value).toHaveLength(3)
  expect(model.value![2]!.connector).toBe('OR')
  const groups = screen.getAllByTestId(GROUP_TESTID)
  expect(groups).toHaveLength(1)
  expect(within(groups[0]!).getAllByRole('group')).toHaveLength(2)
  expect(pillsInOrder()).toHaveLength(3)
})

test('the group X removes every pill in that AND group', async () => {
  const { model } = renderForm([pill('pill-a', null), pill('pill-b', 'AND')])
  await userEvent.click(screen.getByRole('button', { name: 'Remove group' }))

  expect(model.value).toEqual([])
  expect(screen.queryAllByTestId(GROUP_TESTID)).toHaveLength(0)
})

test('removing the first of two OR-joined groups rewrites the new head connector to null', async () => {
  const { model } = renderForm([
    pill('pill-a', null),
    pill('pill-b', 'AND'),
    pill('pill-c', 'OR'),
    pill('pill-d', 'AND')
  ])
  const removeButtons = screen.getAllByRole('button', { name: 'Remove group' })
  expect(removeButtons).toHaveLength(2)
  await userEvent.click(removeButtons[0]!)

  expect(model.value!.map((c) => c.id)).toEqual(['pill-c', 'pill-d'])
  expect(model.value![0]!.connector).toBeNull()
  expect(model.value![1]!.connector).toBe('AND')
})
